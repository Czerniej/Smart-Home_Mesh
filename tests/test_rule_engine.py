import pytest
from core.rule_engine import RulesEngine
from core.devices_types import SensorDevice
from core.database import DatabaseManager

# --- Fakes ---
class FakeDeviceManager:
    def __init__(self):
        self.devices = {}
        self.action_performed = None

    def perform_action(self, mqtt_client, device_id, action, value):
        self.action_performed = {"device_id": device_id, "action": action, "value": value}

class FakeMqttClient:
    pass

# --- Fixture ---
@pytest.fixture
def clean_engine():
    """Zapewnia w pełni wyizolowaną instancję RulesEngine z bazą w pamięci."""
    mem_db = DatabaseManager(db_path=":memory:")
    engine = RulesEngine(db_manager=mem_db)
    engine.setup(FakeDeviceManager(), FakeMqttClient())
    yield engine

# --- Testy ---

@pytest.mark.parametrize("operator,current_value,rule_value,expected_trigger", [
    ("eq", "ON", "ON", True), ("eq", "ON", "OFF", False), ("neq", "ON", "OFF", True),
    ("gt", 25, 20, True), ("gt", 20, 20, False), ("lt", 15, 20, True),
    ("gte", 20, 20, True), ("lte", 19, 20, True),
])
def test_rule_operators(clean_engine, operator, current_value, rule_value, expected_trigger):
    engine = clean_engine
    sensor = SensorDevice(device_id="d1", name="N", topic="T")
    sensor.update_state({"value": current_value})
    engine.device_manager.devices["d1"] = sensor
    
    rule = {
        "id": "rule1", "name": "Test Rule",
        "trigger": {"device_id": "d1", "key": "value", "operator": operator, "value": rule_value},
        "action": {"device_id": "d2", "command": "c"}
    }
    
    assert engine.add_rule(rule) is True
    
    engine.evaluate_state_change_rules(device_id="d1")
    
    action_triggered = (engine.device_manager.action_performed is not None)
    assert action_triggered == expected_trigger

def test_rule_state_resets_when_condition_is_no_longer_met(clean_engine):
    engine = clean_engine
    sensor = SensorDevice(device_id="d1", name="N", topic="T")
    engine.device_manager.devices["d1"] = sensor
    
    rule = {
        "id": "rule1", "name": "Reset Rule",
        "trigger": {"device_id": "d1", "key": "temp", "operator": "gt", "value": 20},
        "action": {"device_id": "ac", "command": "on"}
    }
    engine.add_rule(rule)
    
    sensor.update_state({"temp": 25})
    engine.evaluate_state_change_rules(device_id="d1")
    assert engine.device_manager.action_performed is not None
    assert engine.rule_states["rule1"]["is_active"] is True

    engine.device_manager.action_performed = None
    sensor.update_state({"temp": 18})
    engine.evaluate_state_change_rules(device_id="d1")
    assert engine.device_manager.action_performed is None
    assert engine.rule_states["rule1"]["is_active"] is False

    sensor.update_state({"temp": 22})
    engine.evaluate_state_change_rules(device_id="d1")
    assert engine.device_manager.action_performed is not None

def test_rule_evaluation_for_nonexistent_device_or_key(clean_engine):
    engine = clean_engine
    rule = {"id": "rule1", "name": "Ghost Rule", "trigger": {"device_id": "ghost", "key": "val"}, "action": {}}
    engine.add_rule(rule)
    
    try:
        engine.evaluate_state_change_rules(device_id="ghost")
    except Exception as e:
        pytest.fail(f"Silnik reguł zgłosił nieoczekiwany wyjątek: {e}")