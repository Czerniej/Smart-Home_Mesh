from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

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
    id: str
    name: str
    type: str
    topic: str

@app.get("/devices", summary="Pobiera listę urządzeń i ich aktualny stan")
def list_devices():
    """
    Zwraca listę wszystkich urządzeń wraz z ich aktualnym stanem.
    """
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System nie został poprawnie zainicjalizowany (DM).")
    return {"devices": device_manager_instance.get_devices_data()}

@app.post("/devices", summary="Dodaje nowe urządzenie do systemu")
def add_device(device: DeviceRegistrationModel):
    """
    Dodaje nowe urządzenie.
    """
    if(not device_manager_instance):
         raise HTTPException(status_code=503, detail="System nie został poprawnie zainicjalizowany.")
    
    if(device.type not in DEVICE_TYPE_MAPPING):
        raise HTTPException(status_code=400, detail=f"Nieznany typ urządzenia: {device.type}. Dostępne: {list(DEVICE_TYPE_MAPPING.keys())}")

    DeviceClass = DEVICE_TYPE_MAPPING[device.type]
    new_device = DeviceClass(
        device_id=device.id,
        name=device.name,
        topic=device.topic
    )

    device_manager_instance.add_device(new_device)
    
    logger.info(f"API: Zarejestrowano nowe urządzenie: {device.name} ({device.id})")
    return {"status": "success", "message": f"Urządzenie {device.name} dodane."}

@app.post("/devices/action", summary="Wykonuje akcję na urządzeniu")
def perform_action(request: ActionRequest):
    """
    Wysyła komendę sterującą do wskazanego urządzenia.
    """
    if(not device_manager_instance or not mqtt_client_instance):
         raise HTTPException(status_code=503, detail="System nie został poprawnie zainicjalizowany (MQTT/DM).")
    
    success = device_manager_instance.perform_action(
        mqtt_client_instance, 
        request.device_id, 
        request.action, 
        request.value
    )

    if(not success):
        raise HTTPException(status_code=404, detail=f"Urządzenie o ID {request.device_id} nie zostało znalezione.")
    
    logger.info(f"API: Wysłano akcję '{request.action}' do ID: {request.device_id}")
    return {"status": "success", "message": "Akcja wysłana"}

@app.get("/rules", summary="Pobiera listę wszystkich aktywnych reguł")
def list_rules():
    """
    Zwraca aktualną listę reguł automatyzacji.
    """
    if(not rules_engine_instance):
         raise HTTPException(status_code=503, detail="System nie został poprawnie zainicjalizowany (RE).")
    return {"rules": rules_engine_instance.get_rules()}


@app.post("/rules", summary="Dodaje nową regułę do systemu")
def add_rule(rule: RuleModel):
    """
    Dodaje nową regułę do RulesEngine i zapisuje ją do bazy danych.
    """
    if(not rules_engine_instance):
         raise HTTPException(status_code=503, detail="System nie został poprawnie zainicjalizowany (RE).")
    
    if(rules_engine_instance.add_rule(rule.model_dump())):
        logger.info(f"API: Dodano nową regułę ID: {rule.id}")
        return {"status": "success", "id": rule.id}
    else:
        raise HTTPException(status_code=409, detail=f"Reguła o ID {rule.id} już istnieje.")


@app.delete("/rules/{rule_id}", summary="Usuwa regułę na podstawie jej ID")
def delete_rule(rule_id: str):
    """
    Usuwa regułę o podanym unikalnym ID.
    """
    if(not rules_engine_instance):
         raise HTTPException(status_code=503, detail="System nie został poprawnie zainicjalizowany (RE).")
         
    if(rules_engine_instance.remove_rule(rule_id)):
        logger.info(f"API: Usunięto regułę ID: {rule_id}")
        return {"status": "success", "message": f"Reguła ID {rule_id} usunięta."}
    else:
        raise HTTPException(status_code=404, detail=f"Reguła o ID: {rule_id} nie została znaleziona.")