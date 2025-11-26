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
        self.device_attributes: dict[str, list] = {}
        self.groups: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.db_manager = db_manager
        self.load_from_db()

    def add_device(self, device: BaseDevice):
        with self._lock:
            if(device.device_id in self.devices):
                logger.warning(f"Urządzenie o ID {device.device_id} już istnieje. Pominięto dodanie.")
                return
            self.devices[device.device_id] = device
            self.device_attributes[device.device_id] = []
        
        logger.info(f"Dodano urządzenie: {device.name} (ID: {device.device_id})")
        self.save_device_to_db(device, save_config=True)

    def remove_device(self, device_id: str) -> bool:
        """
        Usuwa urządzenie z pamięci i z bazy danych.
        """
        db_success = self.db_manager.remove_device(device_id)
        with self._lock:
            if(device_id in self.devices):
                del self.devices[device_id]
                self.device_attributes.pop(device_id, None)
                logger.info(f"Usunięto urządzenie: {device_id}")
                return True
        if(db_success):
            return True
        return False

    def get_device_by_topic(self, topic: str) -> BaseDevice | None:
        with self._lock:
            for device in self.devices.values():
                if(topic == device.topic or topic.startswith(device.topic + "/")): 
                    return device
        return None

    def update_device(self, topic: str, payload: dict):
        device = self.get_device_by_topic(topic)
        if(device):
            device.update_state(payload)
            self.save_device_to_db(device, save_config=False)
            self._update_known_attributes(device.device_id, payload)
        else:
            logger.debug(f"Pominięto aktualizację: Nie znaleziono urządzenia dla topicu: {topic}")

    def _update_known_attributes(self, device_id: str, payload: dict):
        """
        Sprawdza, czy w payloadzie są nowe klucze i zapisuje je w bazie.
        """
        with self._lock:
            current_attrs = set(self.device_attributes.get(device_id, []))
            new_keys = set(payload.keys())
            
            ignored_keys = {"linkquality", "last_seen", "update", "update_available"}
            new_keys = new_keys - ignored_keys

            if(not new_keys.issubset(current_attrs)):
                updated_attrs = list(current_attrs.union(new_keys))
                self.device_attributes[device_id] = updated_attrs
                self.db_manager.update_device_attributes(device_id, updated_attrs)
                logger.info(f"Zaktualizowano atrybuty dla {device_id}: {updated_attrs}")

    def create_group(self, group_id: str, name: str, members: list[str]):
        with self._lock:
            self.groups[group_id] = {"id": group_id, "name": name, "members": members}
        self.db_manager.add_group(group_id, name, members)
        logger.info(f"Utworzono grupę: {name} ({group_id}) z członkami: {members}")

    def delete_group(self, group_id: str) -> bool:
        success = self.db_manager.remove_group(group_id)
        with self._lock:
            if(group_id in self.groups):
                del self.groups[group_id]
                logger.info(f"Usunięto grupę: {group_id}")
                return True
        return success

    def get_groups(self) -> list[dict]:
        with self._lock:
            return list(self.groups.values())

    def perform_action(self, mqtt_client, target_id: str, action: str, value=None) -> bool:
        """
        Wykonuje akcję na urządzeniu LUB na grupie urządzeń.
        """
        with self._lock:
            group = self.groups.get(target_id)
        
        if(group):
            logger.info(f"Wykonywanie akcji grupowej na {target_id}...")
            members = group.get("members", [])
            for member_id in members:
                self.perform_action(mqtt_client, member_id, action, value)
            return True
        with self._lock:
            device = self.devices.get(target_id)

        if(device):
            device.perform_action(mqtt_client, action, value)
            return True

    def load_from_db(self):
        devices_data = self.db_manager.get_all_devices_data()
        
        with self._lock:
            self.devices.clear()
            self.device_attributes.clear()
            for d in devices_data:
                dtype = d.get("type")
                device_class = DEVICE_TYPE_MAPPING.get(dtype)
                
                if(device_class):
                    try:
                        device = device_class(device_id=d["id"], name=d["name"], topic=d["topic"])
                        if(d.get("state")):
                            device.update_state(json.loads(d["state"]))
                        self.devices[device.device_id] = device
                        self.device_attributes[device.device_id] = d.get("attributes", [])
                    except Exception as e:
                        logger.error(f"Błąd inicjalizacji urządzenia {d.get('id')}: {e}")

        groups_data = self.db_manager.get_all_groups()
        with self._lock:
            self.groups.clear()
            for g in groups_data:
                self.groups[g['id']] = g

        logger.info(f"Wczytano {len(self.devices)} urządzeń i {len(self.groups)} grup.")

    def save_device_to_db(self, device: BaseDevice, save_config: bool = False):
        device_data = {
            "id": device.device_id,
            "name": device.name,
            "topic": device.topic,
            "type": device.__class__.__name__.replace("Device", "").lower(),
            "attributes": self.device_attributes.get(device.device_id, [])
        }
        self.db_manager.save_device_state(device.device_id, device.state, save_config=save_config, device_data=device_data)

    def get_devices_data(self) -> list[dict]:
        data = []
        with self._lock:
            for device in self.devices.values():
                data.append({
                    "id": device.device_id,
                    "name": device.name,
                    "type": device.__class__.__name__.replace("Device", "").lower(),
                    "topic": device.topic,
                    "state": device.state,
                    "available_keys": self.device_attributes.get(device.device_id, [])
                })
        return data
    
    def add_device_to_group(self, group_id: str, device_id: str) -> bool:
        """
        Dodaje urządzenie do istniejącej grupy.
        """
        with self._lock:
            group = self.groups.get(group_id)
            if(not group):
                logger.warning(f"Próba dodania do nieistniejącej grupy: {group_id}")
                return False
            if(device_id not in group['members']):
                group['members'].append(device_id)
                logger.info(f"Dodano urządzenie {device_id} do grupy {group_id}")
                self.db_manager.add_group(group['id'], group['name'], group['members'])
                return True
            return True

    def remove_device_from_group(self, group_id: str, device_id: str) -> bool:
        """
        Usuwa urządzenie z grupy.
        """
        with self._lock:
            group = self.groups.get(group_id)
            if(not group): return False
            if(device_id in group['members']):
                group['members'].remove(device_id)
                logger.info(f"Usunięto urządzenie {device_id} z grupy {group_id}")
                self.db_manager.add_group(group['id'], group['name'], group['members'])
                return True
            return False