import logging
import os
from dotenv import load_dotenv

load_dotenv()

# --- Ustawienia MQTT ---
BROKER_ADDRESS = "localhost"
BROKER_PORT = 1883
MQTT_TOPIC_SUBSCRIBE = "zigbee2mqtt/#"

# --- Dane Logowania ---
MQTT_USERNAME = os.getenv("MQTT_USERNAME") 
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

# --- Ustawienia API/Servera ---
API_HOST = "localhost"
API_PORT = 8000
ALLOWED_ORIGINS = ["*"]

# --- Ścieżki do Plików Trwałych ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DATABASE_FILE_PATH = os.path.join(DATA_DIR, "smarthome.db")
LOG_FILE_PATH = os.path.join(BASE_DIR, "smart_home.log")

# --- Ustawienia Logiki i Wątków ---
TIME_CHECK_INTERVAL_SECONDS = 60