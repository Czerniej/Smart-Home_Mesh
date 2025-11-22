import json
import threading
import time
from datetime import datetime
import logging

import config 
from .database import DatabaseManager

logger = logging.getLogger(__name__)

class RulesEngine:
    """
    Moduł do zarządzania i wykonywania logiki automatyzacji (reguł).
    """
    def __init__(self, db_manager: DatabaseManager):
        self.rules: list[dict] = []
        self.rule_states: dict[str, dict] = {} 
        self.device_manager = None
        self.mqtt_client = None
        self.db_manager: DatabaseManager = db_manager
        self._time_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def setup(self, device_manager, mqtt_client):
        self.device_manager = device_manager
        self.mqtt_client = mqtt_client
        self.load_from_db()

    def load_from_db(self):
        with self._lock:
            try:
                self.rules = self.db_manager.get_all_rules_data()
                self.rule_states = {r['id']: {'last_triggered': datetime.min, 'is_active': False} for r in self.rules if 'id' in r}
                logger.info(f"Wczytano {len(self.rules)} reguł z bazy danych.")
            except Exception as e:
                logger.error(f"Błąd wczytywania reguł z bazy danych: {e}")

    def get_rules(self) -> list[dict]:
        with self._lock:
            return list(self.rules)

    def add_rule(self, rule: dict) -> bool:
        with self._lock:
            if(rule.get("id") in self.rule_states):
                 logger.warning(f"Reguła ID {rule.get('id')} już istnieje. Pominięto dodanie.")
                 return False
            try:
                self.db_manager.add_rule(rule)
                self.rules.append(rule)
                self.rule_states[rule['id']] = {'last_triggered': datetime.min, 'is_active': False}
                logger.info(f"Dodano regułę ID={rule.get('id')} do bazy danych.")
                return True
            except Exception as e:
                logger.error(f"Błąd dodawania reguły ID={rule.get('id')} do bazy: {e}")
                return False

    def remove_rule(self, rule_id: str) -> bool:
        deleted = self.db_manager.remove_rule(rule_id)
        if(deleted):
            with self._lock:
                self.rules = [r for r in self.rules if r.get("id") != rule_id]
                self.rule_states.pop(rule_id, None)
            logger.info(f"Usunięto regułę ID={rule_id} z bazy danych i pamięci.")
            return True
        return False

    def evaluate_state_change_rules(self, device_id: str):
        if(not self.device_manager):
            return

        with self._lock:
            rules_snapshot = list(self.rules)

        for rule in rules_snapshot:
            if(rule.get("active", True) and rule.get("trigger", {}).get("device_id") == device_id):
                if(self._check_condition(rule)):
                    self._handle_rule_trigger(rule)
                else:
                    with self._lock:
                        rule_id = rule.get('id')
                        if(rule_id in self.rule_states and self.rule_states[rule_id]['is_active']):
                             self.rule_states[rule_id]['is_active'] = False
                             logger.info(f"Reguła ID={rule_id} przestała być spełniona. Zresetowano stan.")
    
    def evaluate_time_rules(self, current_minute: str):
        with self._lock:
            rules_snapshot = list(self.rules)

        for rule in rules_snapshot:
            cond = rule.get("trigger", {})
            if(rule.get("active", True) and cond.get("type") == "time"):
                target_time = cond.get("time")
                rule_id = rule['id']
                with self._lock:
                    if(rule_id in self.rule_states and self.rule_states[rule_id]['last_triggered'].strftime("%H:%M") == current_minute):
                        logger.debug(f"Pominięto regułę czasową ID={rule_id}: już wyzwolona w tej minucie.")
                        continue
                if(target_time == current_minute):
                    logger.info(f"Reguła czasowa spełniona ID={rule_id} ({target_time})")
                    self._handle_rule_trigger(rule)

    def _check_condition(self, rule: dict) -> bool:
        trigger = rule.get("trigger", {})
        device_id = trigger.get("device_id")
        key = trigger.get("key")
        op = trigger.get("operator")
        val = trigger.get("value")
        device = self.device_manager.devices.get(device_id)

        if(not device or key not in device.state):
            return False

        current_value = device.state.get(key)
        rule_id = rule['id']
        
        with self._lock:
            is_already_active = (rule_id in self.rule_states and self.rule_states[rule_id]['is_active'])

        if(is_already_active):
            return False

        try:
            condition_met = False
            if(op == "eq"): condition_met = (current_value == val)
            elif(op == "neq"): condition_met = (current_value != val)
            elif(op == "gt"): condition_met = (current_value > val)
            elif(op == "lt"): condition_met = (current_value < val)
            elif(op == "gte"): condition_met = (current_value >= val)
            elif(op == "lte"): condition_met = (current_value <= val)
            return condition_met
        except (TypeError, ValueError) as e:
            logger.error(f"Błąd porównania wartości w regule ID={rule.get('id')}: {e}")
            return False

    def _handle_rule_trigger(self, rule: dict):
        rule_id = rule['id']
        with self._lock:
            if(rule_id not in self.rule_states):
                 self.rule_states[rule_id] = {'last_triggered': datetime.min, 'is_active': False}
            self.rule_states[rule_id]['last_triggered'] = datetime.now()
            self.rule_states[rule_id]['is_active'] = True
        
        action = rule.get("action")
        if(action):
            device_id = action.get("device_id")
            command = action.get("command")
            value = action.get("value")
            if(device_id and command and self.device_manager and self.mqtt_client):
                logger.info(f"Wykonuję akcję z reguły ID={rule_id} na {device_id}: {command} (value={value})")
                self.device_manager.perform_action(self.mqtt_client, device_id, command, value)
            else:
                logger.error(f"Błąd: Nie można wykonać akcji w regule ID={rule_id}.")

    def start_time_loop(self):
        if(self._time_thread and self._time_thread.is_alive()):
            return
        self._stop_event.clear()
        self._time_thread = threading.Thread(target=self._time_loop, daemon=True) 
        self._time_thread.start()
        logger.info("Uruchomiono wątek sprawdzania reguł czasowych.")

    def stop_time_loop(self):
        self._stop_event.set()
        if(self._time_thread and self._time_thread.is_alive()):
            self._time_thread.join(timeout=2) 
            logger.info("Zatrzymano wątek reguł czasowych.")

    def _time_loop(self):
        while(not self._stop_event.is_set()):
            now = datetime.now()
            current_minute = now.strftime("%H:%M")
            self.evaluate_time_rules(current_minute)
            time.sleep(config.TIME_CHECK_INTERVAL_SECONDS)