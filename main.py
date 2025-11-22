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
from core.database import DatabaseManager # Dodano ten import
from logging_config import setup_logging
import config
from api import app, setup_api 

logger = logging.getLogger(__name__)

# Globalne instancje
device_manager: DeviceManager = None
rules_engine: RulesEngine = None
mqtt_client: MQTT_Client = None

def on_message_callback(topic, payload):
    device = device_manager.get_device_by_topic(topic)
    if(device):
        logger.info(f"Odebrano dane z {device.name} ({device.device_id}). Aktualizacja stanu.")
        device_manager.update_device(topic, payload)
        rules_engine.evaluate_state_change_rules(device.device_id) 
    else:
        logger.debug(f"Odebrano wiadomość z nieznanego topicu: {topic}. Pominięto.")

def run_api_server():
    logger.info(f"Uruchomienie serwera API na http://{config.API_HOST}:{config.API_PORT}")
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

    # 1. INICJALIZACJA GLOBALNYCH OBIEKTÓW
    # Tworzymy jedną, centralną instancję DB Managera
    db_manager = DatabaseManager()
    
    mqtt_client = MQTT_Client() 
    # Przekazujemy db_manager do konstruktorów
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