import logging
import os 
import json
import threading

from .devices_types import LightDevice, SocketDevice, SensorDevice, BaseDevice 
from .database import DatabaseManager
import config 

logger = logging.getLogger(__name__)

DEVICE_TYPE_MAPPING = {
    "light": LightDevice,
    "socket": SocketDevice,
    "sensor": SensorDevice
}

class DeviceManager:
    """
    Zarządza listą urządzeń, ich stanami, oraz obsługuje ich wczytywanie/zapisywanie.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.devices: dict[str, BaseDevice] = {}
        self._lock = threading.Lock()
        self.db_manager = db_manager
        self.load_from_db()

    def add_device(self, device: BaseDevice):
        with self._lock:
            if(device.device_id in self.devices):
                logger.warning(f"Urządzenie o ID {device.device_id} już istnieje. Pominięto dodanie.")
                return
            
            self.devices[device.device_id] = device
        
        logger.info(f"Dodano urządzenie: {device.name} (ID: {device.device_id}, Topic: {device.topic})")
        self.save_device_to_db(device, save_config=True)

    def remove_device(self, device_id: str) -> bool:
        """
        Usuwa urządzenie z pamięci i z bazy danych.
        """
        db_success = self.db_manager.remove_device(device_id)
        with self._lock:
            if(device_id in self.devices):
                del self.devices[device_id]
                logger.info(f"Usunięto urządzenie: {device_id}")
                return True
        if(db_success):
            logger.info(f"Usunięto urządzenie (tylko z DB): {device_id}")
            return True
            
        logger.warning(f"Próba usunięcia nieistniejącego urządzenia: {device_id}")
        return False

    def get_device_by_topic(self, topic: str) -> BaseDevice | None:
        with self._lock:
            for device in self.devices.values():
                if(device.topic in topic): 
                    return device
        return None

    def update_device(self, topic: str, payload: dict):
        device = self.get_device_by_topic(topic)
        if(device):
            device.update_state(payload)
            self.save_device_to_db(device, save_config=False)
        else:
            logger.debug(f"Pominięto aktualizację: Nie znaleziono urządzenia dla topicu: {topic}")

    def perform_action(self, mqtt_client, device_id: str, action: str, value=None) -> bool:
        with self._lock:
            device = self.devices.get(device_id)

        if(device):
            device.perform_action(mqtt_client, action, value)
            return True
        else:
            logger.warning(f"Nie znaleziono urządzenia o ID: {device_id} do wykonania akcji '{action}'.")
            return False

    def load_from_db(self):
        devices_data = self.db_manager.get_all_devices_data()
        
        with self._lock:
            self.devices.clear()
            for d in devices_data:
                dtype = d.get("type")
                device_class = DEVICE_TYPE_MAPPING.get(dtype)
                
                if(device_class):
                    try:
                        device = device_class(
                            device_id=d["id"], 
                            name=d["name"], 
                            topic=d["topic"]
                        )
                        if(d.get("state")):
                            state_dict = json.loads(d["state"])
                            device.update_state(state_dict) 
                        self.devices[device.device_id] = device 
                    except KeyError as e:
                        logger.error(f"Błąd: Brakuje wymaganego pola {e} w konfiguracji urządzenia typu {dtype}.")
                    except json.JSONDecodeError as e:
                         logger.error(f"Błąd dekodowania stanu JSON dla urządzenia {d.get('name')}: {e}")
                else:
                    logger.warning(f"Nieznany typ urządzenia: {dtype}. Pomijam urządzenie {d.get('name', 'Brak nazwy')}.")
        
        logger.info(f"Wczytano i zainicjalizowano {len(self.devices)} urządzeń z bazy danych.")

    def save_device_to_db(self, device: BaseDevice, save_config: bool = False):
        device_data = {
            "id": device.device_id,
            "name": device.name,
            "topic": device.topic,
            "type": device.__class__.__name__.replace("Device", "").lower(),
        }
        self.db_manager.save_device_state(device.device_id, device.state, save_config=save_config, device_data=device_data)

    def get_devices_data(self) -> list[dict]:
        data = []
        with self._lock:
            devices_snapshot = list(self.devices.values())

        for device in devices_snapshot:
            data.append({
                "id": device.device_id,
                "name": device.name,
                "type": device.__class__.__name__.replace("Device", "").lower(),
                "topic": device.topic,
                "state": device.state
            })
        return data