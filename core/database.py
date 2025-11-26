import sqlite3
import logging
import json
import config
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Klasa odpowiedzialna za zarządzanie połączeniem SQLite i operacjami CRUD.
    """
    
    def __init__(self, db_path: str = config.DATABASE_FILE_PATH):
        self.db_path = db_path
        self._connection = None
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Pobiera lub tworzy połączenie z bazą danych.
        """
        if(self._connection is None):
            try:
                self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
                self._connection.row_factory = sqlite3.Row 
            except sqlite3.Error as e:
                logger.critical(f"KRYTYCZNY BŁĄD połączenia z bazą danych: {e}")
                raise
        return self._connection

    def _execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Wykonuje zapytanie i zwraca kursor.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Błąd wykonania zapytania: {query} z parametrami {params}. Błąd: {e}")
            raise
        return cursor

    def _initialize_db(self):
        """
        Tworzy tabele, jeśli nie istnieją.
        """
        logger.info(f"Inicjalizacja schematu bazy danych w pliku: {self.db_path}")
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                topic TEXT NOT NULL,
                type TEXT NOT NULL,
                state TEXT,
                attributes TEXT 
            );
        """)
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                active INTEGER NOT NULL,
                trigger TEXT NOT NULL,
                action TEXT NOT NULL
            );
        """)
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                members TEXT NOT NULL
            );
        """)

    def get_all_devices_data(self) -> List[Dict[str, Any]]:
        """
        Pobiera dane wszystkich urządzeń z bazy.
        """
        cursor = self._execute_query("SELECT * FROM devices;")
        devices = []
        for row in cursor.fetchall():
            d = dict(row)
            if(d.get('attributes')):
                try:
                    d['attributes'] = json.loads(d['attributes'])
                except:
                    d['attributes'] = []
            else:
                d['attributes'] = []
            devices.append(d)
        return devices

    def save_device_state(self, device_id: str, state: Dict[str, Any], save_config: bool = False, device_data: Optional[Dict] = None):
        """
        Aktualizuje stan (state) urządzenia w bazie danych.
        """
        state_json = json.dumps(state)
        
        if(save_config and device_data):
            attributes_json = json.dumps(device_data.get('attributes', []))
            self._execute_query("""
                INSERT OR REPLACE INTO devices (id, name, topic, type, state, attributes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (device_data['id'], device_data['name'], device_data['topic'], device_data['type'], state_json, attributes_json))
        else:
            self._execute_query("UPDATE devices SET state = ? WHERE id = ?", (state_json, device_id))

    def update_device_attributes(self, device_id: str, attributes: List[str]):
        """
        Aktualizuje listę dostępnych atrybutów dla urządzenia.
        """
        attr_json = json.dumps(attributes)
        self._execute_query("UPDATE devices SET attributes = ? WHERE id = ?", (attr_json, device_id))
    
    def remove_device(self, device_id: str) -> bool:
        """
        Usuwa urządzenie z bazy danych. Zwraca True, jeśli usunięto.
        """
        cursor = self._execute_query("DELETE FROM devices WHERE id = ?", (device_id,))
        return cursor.rowcount > 0

    def get_all_groups(self) -> List[Dict[str, Any]]:
        """
        Pobiera dane wszystkich grup z bazy.
        """
        cursor = self._execute_query("SELECT * FROM groups;")
        groups = []
        for row in cursor.fetchall():
            g = dict(row)
            g['members'] = json.loads(g['members'])
            groups.append(g)
        return groups

    def add_group(self, group_id: str, name: str, members: List[str]):
        """
        Dodaje nową grupę do bazy danych.
        """
        members_json = json.dumps(members)
        self._execute_query("""
            INSERT OR REPLACE INTO groups (id, name, members)
            VALUES (?, ?, ?)
        """, (group_id, name, members_json))

    def remove_group(self, group_id: str) -> bool:
        """
        Usuwa grupę z bazy danych. Zwraca True, jeśli usunięto.
        """
        cursor = self._execute_query("DELETE FROM groups WHERE id = ?", (group_id,))
        return cursor.rowcount > 0

    def get_all_rules_data(self) -> List[Dict[str, Any]]:
        """
        Pobiera wszystkie reguły z bazy.
        """
        cursor = self._execute_query("SELECT * FROM rules;")
        rules = []
        for row in cursor.fetchall():
            rule_dict = dict(row)
            rule_dict['trigger'] = json.loads(rule_dict['trigger'])
            rule_dict['action'] = json.loads(rule_dict['action'])
            rule_dict['active'] = bool(rule_dict['active'])
            rules.append(rule_dict)
        return rules

    def add_rule(self, rule: Dict[str, Any]):
        """
        Dodaje nową regułę do bazy danych.
        """
        trigger_json = json.dumps(rule['trigger'])
        action_json = json.dumps(rule['action'])
        active_int = 1 if rule.get('active', True) else 0

        self._execute_query("""
            INSERT INTO rules (id, name, active, trigger, action)
            VALUES (?, ?, ?, ?, ?)
        """, (rule['id'], rule['name'], active_int, trigger_json, action_json))

    def remove_rule(self, rule_id: str) -> bool:
        """
        Usuwa regułę na podstawie ID i zwraca True, jeśli rekord został usunięty.
        """
        cursor = self._execute_query("DELETE FROM rules WHERE id = ?", (rule_id,))
        return cursor.rowcount > 0
    
    def update_device_metadata(self, device_id: str, name: str, topic: str, dev_type: str):
        """
        Aktualizuje nazwę, temat MQTT oraz typ urządzenia.
        """
        self._execute_query("""
            UPDATE devices 
            SET name = ?, topic = ?, type = ? 
            WHERE id = ?
        """, (name, topic, dev_type, device_id))

        def update_group_name(self, group_id: str, new_name: str):
            """
            Aktualizuje nazwę istniejącej grupy.
            """
            self._execute_query("UPDATE groups SET name = ? WHERE id = ?", (new_name, group_id))