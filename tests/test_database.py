import pytest
from core.database import DatabaseManager

@pytest.fixture
def mem_db():
    """Tworzy instancję DatabaseManager używającą bazy w pamięci RAM dla każdego testu."""
    db = DatabaseManager(db_path=":memory:")
    yield db

# --- Testy dla Tabeli 'rules' ---

def test_add_and_get_rule(mem_db):
    """Testuje dodawanie i poprawne odczytywanie reguły z bazy."""
    rule_data = {
        "id": "test_rule_123", "name": "Testowa Reguła", "active": True,
        "trigger": {"device_id": "d1", "key": "k", "operator": "eq", "value": "v"},
        "action": {"device_id": "d2", "command": "c", "value": "v"}
    }
    mem_db.add_rule(rule_data)
    rules_from_db = mem_db.get_all_rules_data()

    assert len(rules_from_db) == 1
    retrieved_rule = rules_from_db[0]
    assert retrieved_rule["id"] == rule_data["id"]
    assert retrieved_rule["trigger"] == rule_data["trigger"] # Sprawdza deserializację JSON

def test_remove_existing_rule(mem_db):
    """Testuje usuwanie reguły, która istnieje w bazie."""
    rule_data = {"id": "r1", "name": "N", "active": True, "trigger": {}, "action": {}}
    mem_db.add_rule(rule_data)
    
    deleted = mem_db.remove_rule("r1")
    
    assert deleted is True
    assert len(mem_db.get_all_rules_data()) == 0

def test_remove_nonexistent_rule(mem_db):
    """Testuje próbę usunięcia reguły, która nie istnieje."""
    deleted = mem_db.remove_rule("nonexistent_id")
    assert deleted is False

# --- Testy dla Tabeli 'devices' ---

def test_save_new_device_with_config(mem_db):
    """Testuje zapis nowego urządzenia (operacja INSERT OR REPLACE)."""
    device_data = {"id": "light_1", "name": "Lampa Salon", "topic": "z/lampa", "type": "light"}
    initial_state = {"state": "ON", "brightness": 150}
    
    mem_db.save_device_state("light_1", initial_state, save_config=True, device_data=device_data)
    
    devices_from_db = mem_db.get_all_devices_data()
    assert len(devices_from_db) == 1
    device = devices_from_db[0]
    assert device["id"] == "light_1"
    assert device["name"] == "Lampa Salon"
    assert device["state"] == '{"state": "ON", "brightness": 150}' # Stan jest zapisywany jako JSON string

def test_update_existing_device_state_only(mem_db):
    """Testuje aktualizację TYLKO STANU istniejącego urządzenia (operacja UPDATE)."""
    device_data = {"id": "d1", "name": "Gniazdko", "topic": "T1", "type": "socket"}
    mem_db.save_device_state("d1", {"state": "OFF"}, save_config=True, device_data=device_data)

    mem_db.save_device_state("d1", {"state": "ON", "power": 12.5}, save_config=False)

    device = mem_db.get_all_devices_data()[0]
    assert device["name"] == "Gniazdko" # Konfiguracja nie powinna się zmienić
    assert device["state"] == '{"state": "ON", "power": 12.5}'