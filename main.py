import signal
import sys
import time
import uvicorn
import logging
import threading
import os 
import json

from core.mqtt_client import MQTT_Client
from core.device_manager import DeviceManager
from core.rule_engine import RulesEngine
from core.database import DatabaseManager
from core.devices_types import SocketDevice, SensorDevice, LightDevice, CoverDevice, LockDevice, ThermostatDevice, ControllerDevice
from logging_config import setup_logging
import config
from api import app, setup_api 
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

device_manager: DeviceManager = None
rules_engine: RulesEngine = None
mqtt_client: MQTT_Client = None

def determine_device_type(definition: dict) -> type:
    """
    Analizuje definicję urządzenia z Zigbee2MQTT i zwraca odpowiednią klasę.
    """
    if(not definition or "exposes" not in definition):
        return SensorDevice

    exposes = definition.get("exposes", [])
    features = []

    for item in exposes:
        features.append(item.get("name", ""))
        features.append(item.get("type", ""))
        if item.get("features"):
            for sub in item.get("features"):
                features.append(sub.get("name", ""))

    features_set = set(features)

    if("cover" in features_set or "position" in features_set):
        return CoverDevice
    if("lock" in features_set and "lock_state" in features_set):
        return LockDevice
    if("climate" in features_set or "current_heating_setpoint" in features_set):
        return ThermostatDevice
    if("light" in features_set or "brightness" in features_set or "color_xy" in features_set):
        return LightDevice
    if("action" in features_set and "switch" not in features_set):
        return ControllerDevice
    if("switch" in features_set or "state" in features_set):
        return SocketDevice
    return SensorDevice

def on_message_callback(topic, payload):
    """
    Główny router wiadomości MQTT.
    """
    device = device_manager.get_device_by_topic(topic)
    if(device):
        logger.info(f"Odebrano dane z {device.name} ({device.device_id}).")
        device_manager.update_device(topic, payload)
        rules_engine.evaluate_state_change_rules(device.device_id) 
        return
    if(topic == "zigbee2mqtt/bridge/devices"):
        logger.info("Odebrano listę urządzeń z Zigbee2MQTT. Synchronizacja...")
        if(isinstance(payload, list)):
            for dev_data in payload:
                if(dev_data.get("type") == "Coordinator"):
                    continue
                ieee_address = dev_data.get("ieee_address")
                friendly_name = dev_data.get("friendly_name")
                definition = dev_data.get("definition")
                DeviceClass = determine_device_type(definition)
                new_device = DeviceClass(
                    device_id=ieee_address,
                    name=friendly_name,
                    topic=f"zigbee2mqtt/{friendly_name}"
                )
                device_manager.update_or_create_device(new_device)
        logger.info("Zakończono synchronizację urządzeń.")
    elif(topic == "zigbee2mqtt/bridge/event"):
        event_type = payload.get("type")
        if(event_type == "device_rename"):
            data = payload.get("data", {})
            old_name = data.get("from")
            new_name = data.get("to")
            logger.info(f"Wykryto zmianę nazwy w Z2M: {old_name} -> {new_name}. Żądam odświeżenia listy...")
            mqtt_client.publish("zigbee2mqtt/bridge/request/devices/get", {})

def run_api_server():
    logger.info(f"Uruchomienie serwera API na http://{config.API_HOST}:{config.API_PORT}")
    if(os.path.exists(config.FRONTEND_DIR)):
        app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
        logger.info(f"Serwowanie aplikacji webowej z: {config.FRONTEND_DIR}")
    else:
        logger.warning(f"Nie znaleziono folderu frontend w: {config.FRONTEND_DIR}")

    try:
        uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, log_level="info")
    except Exception as e:
        logger.critical(f"KRYTYCZNY BŁĄD uruchomienia serwera Uvicorn/FastAPI: {e}")
        shutdown()

def shutdown(signal_received=None, frame=None):
    logger.critical("Otrzymano sygnał zakończenia (SIGINT/SIGTERM). Zatrzymywanie systemu...")
    if(rules_engine):
        try:
            rules_engine.stop_time_loop()
        except Exception as e:
            logger.error(f"Błąd zatrzymywania pętli czasowej: {e}")
    if(mqtt_client):
        try:
            mqtt_client.disconnect()
        except Exception as e:
            logger.error(f"Błąd rozłączania MQTT: {e}")
    logger.info("Zamykanie procesów. System zatrzymany.")
    os._exit(0)

def check_and_create_data_dir():
    if(not os.path.exists(config.DATA_DIR)):
        os.makedirs(config.DATA_DIR)
        logger.info(f"Utworzono katalog danych: {config.DATA_DIR}")

if(__name__ == "__main__"):
    setup_logging()
    logger.info("Start systemu Smart Home")
    
    check_and_create_data_dir() 

    db_manager = DatabaseManager()
    
    mqtt_client = MQTT_Client() 
    device_manager = DeviceManager(db_manager=db_manager) 
    rules_engine = RulesEngine(db_manager=db_manager) 
    
    rules_engine.setup(device_manager, mqtt_client)
    mqtt_client.on_message_callback = on_message_callback

    rules_engine.start_time_loop()
    mqtt_client.connect(BROKER_ADDRESS=config.BROKER_ADDRESS, BROKER_PORT=config.BROKER_PORT)
    setup_api(device_manager, rules_engine, mqtt_client)
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("System działa. Oczekiwanie na wiadomości MQTT i połączenia API...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()