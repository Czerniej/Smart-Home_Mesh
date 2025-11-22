import pytest
from fastapi.testclient import TestClient
from api import app, setup_api
from core.device_manager import DeviceManager
from core.rule_engine import RulesEngine
from core.mqtt_client import MQTT_Client
from core.database import DatabaseManager
import config
import os

# --- Konfiguracja Testowego API ---
# Ten kod jest uruchamiany RAZ, gdy pytest importuje ten plik.

TEST_DB_PATH = os.path.join(config.DATA_DIR, "test_smarthome.db")

# Usuwamy starą bazę testową na wypadek, gdyby istniała
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

# POPRAWKA: Tworzymy jedną instancję DB Managera dla wszystkich testów w tym pliku
test_db_manager = DatabaseManager(db_path=TEST_DB_PATH)

# POPRAWKA: Tworzymy instancje menedżerów w nowy, poprawny sposób, wstrzykując zależność
device_manager = DeviceManager(db_manager=test_db_manager)
rules_engine = RulesEngine(db_manager=test_db_manager)
mqtt_client = MQTT_Client()

# Konfigurujemy zależności między menedżerami
rules_engine.setup(device_manager, mqtt_client)

# Wstrzykujemy gotowe, skonfigurowane instancje do aplikacji FastAPI
setup_api(device_manager, rules_engine, mqtt_client)

# Tworzymy klienta testowego, który będzie używany przez wszystkie testy
client = TestClient(app)

# --- Testy Właściwe (te funkcje nie wymagają zmian) ---

def test_rules_crud_flow():
    """Testuje pełny cykl życia reguły przez API: CREATE, READ, DELETE."""
    rule_id = "api_test_rule"
    rule_payload = {
        "id": rule_id, "name": "Reguła z testu API", "active": True,
        "trigger": {"device_id": "d1", "key": "k", "operator": "eq", "value": "v"},
        "action": {"device_id": "d2", "command": "c"}
    }
    # CREATE
    response_create = client.post("/rules", json=rule_payload)
    assert response_create.status_code == 200
    # READ
    response_get = client.get("/rules")
    assert any(r["id"] == rule_id for r in response_get.json()["rules"])
    # DELETE
    response_delete = client.delete(f"/rules/{rule_id}")
    assert response_delete.status_code == 200
    # VERIFY
    response_get_after = client.get("/rules")
    assert not any(r["id"] == rule_id for r in response_get_after.json()["rules"])

def test_api_deleting_nonexistent_rule_returns_404():
    """Sprawdza, czy próba usunięcia nieistniejącej reguły zwraca błąd 404 (Not Found)."""
    response = client.delete("/rules/i_do_not_exist")
    assert response.status_code == 404

def test_api_adding_duplicate_rule_returns_409():
    """Sprawdza, czy próba dodania reguły o istniejącym ID zwraca błąd 409 (Conflict)."""
    rule_payload = { "id": "duplicate_rule", "name": "N", "trigger": {}, "action": {}}
    client.post("/rules", json=rule_payload)
    response2 = client.post("/rules", json=rule_payload)
    assert response2.status_code == 409
    client.delete("/rules/duplicate_rule") # Sprzątanie

def test_api_invalid_payload_returns_422():
    """Sprawdza, czy wysłanie niekompletnych danych (bez ID) zwraca błąd 422 (Unprocessable Entity)."""
    invalid_payload = {"name": "Reguła bez ID", "trigger": {}, "action": {}}
    response = client.post("/rules", json=invalid_payload)
    assert response.status_code == 422

def test_api_perform_action_on_nonexistent_device_returns_404():
    """Sprawdza, czy wykonanie akcji na nieistniejącym urządzeniu zwraca błąd 404."""
    action_payload = {"device_id": "ghost_device", "action": "turn_on"}
    response = client.post("/devices/action", json=action_payload)
    assert response.status_code == 404