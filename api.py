from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os

from core.device_manager import DeviceManager, DEVICE_TYPE_MAPPING
from core.rule_engine import RulesEngine
from core.mqtt_client import MQTT_Client  
import config

logger = logging.getLogger(__name__)

device_manager_instance: DeviceManager = None
rules_engine_instance: RulesEngine = None
mqtt_client_instance: MQTT_Client = None

app = FastAPI(title="Smart Home API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def setup_api(dm: DeviceManager, re: RulesEngine, mc: MQTT_Client):
    """
    Konfiguracja instancji menedżerów dla modułu API. 
    """
    global device_manager_instance, rules_engine_instance, mqtt_client_instance
    device_manager_instance = dm
    rules_engine_instance = re
    mqtt_client_instance = mc
    logger.info("API zostało skonfigurowane z instancjami menedżerów.")

class ActionRequest(BaseModel):
    """
    Model do sterowania urządzeniem.
    """
    device_id: str
    action: str
    value: Optional[Any] = None

class RuleModel(BaseModel):
    """
    Model dla pojedynczej reguły (używany do POST/PUT).
    """
    id: str
    name: str
    active: bool = True
    trigger: dict
    action: dict

class DeviceRegistrationModel(BaseModel):
    """
    Model dla rejestracji.
    """
    id: str
    name: str
    type: str
    topic: str

class GroupModel(BaseModel):
    """
    Model dla grupy.
    """
    id: str
    name: str
    members: List[str]

class RenameRequest(BaseModel):
    """
    Model dla zmiany nazwy.
    """
    new_name: str

@app.get("/devices", summary="Pobiera listę urządzeń")
def list_devices():
    """
    Zwraca listę wszystkich urządzeń wraz z ich aktualnym stanem.
    """
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    return {"devices": device_manager_instance.get_devices_data()}

@app.post("/devices", summary="Dodaje nowe urządzenie")
def add_device(device: DeviceRegistrationModel):
    """
    Dodaje nowe urządzenie.
    """
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    
    if(device.type not in DEVICE_TYPE_MAPPING):
        raise HTTPException(status_code=400, detail="Nieznany typ urządzenia.")

    DeviceClass = DEVICE_TYPE_MAPPING[device.type]
    new_device = DeviceClass(device_id=device.id, name=device.name, topic=device.topic)
    device_manager_instance.add_device(new_device)
    
    logger.info(f"API: Zarejestrowano nowe urządzenie: {device.name} ({device.id})")
    return {"status": "success", "message": f"Urządzenie {device.name} dodane."}

@app.delete("/devices/{device_id}", summary="Usuwa urządzenie")
def delete_device(device_id: str):
    """
    Usuwa urządzenie o podanym ID.
    """
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    if(device_manager_instance.remove_device(device_id)):
        logger.info(f"API: Usunięto urządzenie ID: {device_id}")
        return {"status": "success", "message": f"Urządzenie {device_id} usunięte."}
    raise HTTPException(status_code=404, detail="Urządzenie nie znalezione.")

@app.post("/devices/action", summary="Wykonuje akcję (urządzenie lub grupa)")
def perform_action(request: ActionRequest):
    """
    Wysyła komendę sterującą do wskazanego urządzenia.
    """
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    
    success = device_manager_instance.perform_action(
        mqtt_client_instance, request.device_id, request.action, request.value
    )
    if(not success):
        logger.warning(f"API: Nieudana próba akcji '{request.action}' na celu {request.device_id}")
        raise HTTPException(status_code=404, detail=f"Cel {request.device_id} nie znaleziony.")
    
    logger.info(f"API: Wysłano akcję '{request.action}' do celu: {request.device_id}")
    return {"status": "success"}

@app.get("/groups", summary="Pobiera listę grup")
def list_groups():
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    return {"groups": device_manager_instance.get_groups()}

@app.post("/groups", summary="Tworzy nową grupę")
def create_group(group: GroupModel):
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    device_manager_instance.create_group(group.id, group.name, group.members)
    
    logger.info(f"API: Utworzono grupę '{group.name}' (ID: {group.id})")
    return {"status": "success", "message": f"Grupa {group.name} utworzona."}

@app.delete("/groups/{group_id}", summary="Usuwa grupę")
def delete_group(group_id: str):
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    if(device_manager_instance.delete_group(group_id)):

        logger.info(f"API: Usunięto grupę ID: {group_id}")
        return {"status": "success", "message": "Grupa usunięta."}
    raise HTTPException(status_code=404, detail="Grupa nie znaleziona.")

@app.post("/groups/{group_id}/devices/{device_id}", summary="Dodaje urządzenie do grupy")
def add_device_to_group(group_id: str, device_id: str):
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    
    if(device_manager_instance.add_device_to_group(group_id, device_id)):
        logger.info(f"API: Dodano urządzenie {device_id} do grupy {group_id}")
        return {"status": "success", "message": "Urządzenie dodane do grupy."}
    
    raise HTTPException(status_code=404, detail="Grupa nie znaleziona lub błąd zapisu.")

@app.delete("/groups/{group_id}/devices/{device_id}", summary="Usuwa urządzenie z grupy")
def remove_device_from_group(group_id: str, device_id: str):
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    
    if(device_manager_instance.remove_device_from_group(group_id, device_id)):
        logger.info(f"API: Usunięto urządzenie {device_id} z grupy {group_id}")
        return {"status": "success", "message": "Urządzenie usunięte z grupy."}
    
    raise HTTPException(status_code=404, detail="Grupa nie znaleziona lub urządzenie nie było w grupie.")

@app.post("/system/pairing/{state}", summary="Włącza/Wyłącza parowanie")
def set_pairing(state: str):
    if(not mqtt_client_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    
    is_enabled = (state.lower() == "true")
    payload = {"permit_join": is_enabled}
    mqtt_client_instance.publish("zigbee2mqtt/bridge/request/permit_join", payload)
    
    logger.info(f"API: Zmieniono tryb parowania Zigbee na: {is_enabled}")
    return {"status": "success", "message": f"Parowanie ustawione na: {is_enabled}"}

@app.put("/devices/{device_id}/rename", summary="Zmienia nazwę urządzenia")
def rename_device(device_id: str, request: RenameRequest):
    if(not mqtt_client_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    
    payload = {"from": device_id, "to": request.new_name, "homeassistant_rename": False}
    mqtt_client_instance.publish("zigbee2mqtt/bridge/request/device/rename", payload)
    
    logger.info(f"API: Wysłano żądanie zmiany nazwy dla {device_id} na '{request.new_name}'")
    return {"status": "queued", "message": "Wysłano żądanie zmiany nazwy."}

@app.get("/rules", summary="Pobiera reguły")
def list_rules():
    """
    Zwraca aktualną listę reguł automatyzacji.
    """
    if(not rules_engine_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    return {"rules": rules_engine_instance.get_rules()}

@app.post("/rules", summary="Dodaje regułę")
def add_rule(rule: RuleModel):
    """
    Dodaje nową regułę do RulesEngine i zapisuje ją do bazy danych.
    """
    if(not rules_engine_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    if(rules_engine_instance.add_rule(rule.model_dump())):
        logger.info(f"API: Dodano nową regułę: {rule.name} (ID: {rule.id})")
        return {"status": "success", "id": rule.id}
    raise HTTPException(status_code=409, detail="Reguła już istnieje.")

@app.delete("/rules/{rule_id}", summary="Usuwa regułę")
def delete_rule(rule_id: str):
    """
    Usuwa regułę o podanym unikalnym ID.
    """
    if(not rules_engine_instance):
         raise HTTPException(status_code=503, detail="System niegotowy.")
    if(rules_engine_instance.remove_rule(rule_id)):
        logger.info(f"API: Usunięto regułę ID: {rule_id}")
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Reguła nie znaleziona.")

@app.get("/logs", summary="Pobiera ostatnie logi systemowe")
def get_system_logs(lines: int = 50):
    """
    Zwraca ostatnie N linii z pliku logów.
    """
    if(not os.path.exists(config.LOG_FILE_PATH)):
        return {"logs": ["Brak pliku logów."]}
    
    try:
        with open(config.LOG_FILE_PATH, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
            return {"logs": last_lines}
    except Exception as e:
        logger.error(f"Błąd odczytu logów: {e}")
        return {"logs": [f"Błąd odczytu logów: {str(e)}"]}