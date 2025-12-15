import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

class BaseDevice:
    """
    Klasa bazowa dla wszystkich urządzeń Smart Home.
    """
    def __init__(self, device_id: str, name: str, topic: str):
        self.device_id = device_id
        self.name = name
        self.topic = topic
        self.state: Dict[str, Any] = {"state": "UNKNOWN"} 

    def update_state(self, payload: dict):
        """
        Aktualizuje stan urządzenia na podstawie wiadomości z MQTT.
        """
        if(payload and isinstance(payload, dict)):
            self.state.update(payload)
            logger.info(f"[{self.__class__.__name__}] {self.name} ({self.device_id}): Zaktualizowano stan -> {self.state}")
        else:
            logger.warning(f"[{self.__class__.__name__}] {self.name}: Otrzymano pusty lub nieprawidłowy payload.")

    def perform_action(self, mqtt_client, action: str, value: Optional[Any] = None):
        """
        Wysyła akcję do urządzenia. Do zaimplementowania w klasach potomnych.
        """
        raise NotImplementedError("Metoda perform_action musi być zaimplementowana w typie urządzenia")

class LightDevice(BaseDevice):
    """
    Obsługa akcji dla żarówek (ON/OFF, jasność, kolor).
    """
    def perform_action(self, mqtt_client, action: str, value: Optional[Any] = None):
        payload = {}
        if(action == "turn_on"):
            payload["state"] = "ON"
        elif(action == "turn_off"):
            payload["state"] = "OFF"
        elif(action == "set_brightness"):
            try:
                level = int(value)
                payload["brightness"] = max(0, min(254, level))
            except (TypeError, ValueError):
                logger.error(f"[LightDevice] Błąd: Nieprawidłowa wartość jasności ({value}) dla urządzenia {self.name}.")
                return
        elif(action == "set_color"):
            if(isinstance(value, str)):
                payload["color"] = {"hex": value}
            else:
                logger.error(f"[LightDevice] Błąd: Wartość koloru musi być łańcuchem HEX dla urządzenia {self.name}.")
                return
        else:
            logger.warning(f"[LightDevice] Nieznana akcja: {action} dla urządzenia {self.name}.")
            return

        try:
            mqtt_client.publish(f"{self.topic}/set", payload)
            logger.info(f"[LightDevice] {self.name}: Akcja '{action}' wysłana -> {payload}")
        except Exception as e:
            logger.error(f"[LightDevice] Błąd publikacji MQTT dla {self.name}: {e}")

class SocketDevice(BaseDevice):
    """
    Obsługa akcji dla gniazdek (ON/OFF).
    """
    def perform_action(self, mqtt_client, action: str, value: Optional[Any] = None):
        if(action in ["turn_on", "turn_off"]):
            payload = {"state": "ON" if(action == "turn_on") else "OFF"}
            try:
                mqtt_client.publish(f"{self.topic}/set", payload)
                logger.info(f"[SocketDevice] {self.name}: Akcja '{action}' wysłana -> {payload}")
            except Exception as e:
                logger.error(f"[SocketDevice] Błąd publikacji MQTT dla {self.name}: {e}")
        else:
            logger.warning(f"[SocketDevice] Nieobsługiwana akcja dla gniazdka: {action}.")

class SensorDevice(BaseDevice):
    """
    Klasa dla czujników. Nie wykonuje akcji sterujących.
    """
    def perform_action(self, mqtt_client, action: str, value: Optional[Any] = None):
        logger.debug(f"[SensorDevice] {self.name}: Otrzymano żądanie akcji '{action}'. Ignorowanie, ponieważ to czujnik.")
        return
    
class CoverDevice(BaseDevice):
    """
    Obsługa rolet, żaluzji i silników zasłon.
    """
    def perform_action(self, mqtt_client, action: str, value: Optional[Any] = None):
        payload = {}
        if(action == "open"): 
            payload["state"] = "OPEN"
        elif(action == "close"): 
            payload["state"] = "CLOSE"
        elif(action == "stop"): 
            payload["state"] = "STOP"
        elif(action == "set_position"):
            try: 
                payload["position"] = max(0, min(100, int(value)))
            except: 
                pass
        if(payload):
            mqtt_client.publish(f"{self.topic}/set", payload)

class LockDevice(BaseDevice):
    """
    Obsługa inteligentnych zamków.
    """
    def perform_action(self, mqtt_client, action: str, value: Optional[Any] = None):
        payload = {}
        if(action == "lock"):
            payload["state"] = "LOCK"
        elif(action == "unlock"):
            payload["state"] = "UNLOCK"
        
        if(payload):
            mqtt_client.publish(f"{self.topic}/set", payload)

class ThermostatDevice(BaseDevice):
    """
    Obsługa głowic termostatycznych (TRV) i klimatyzacji.
    """
    def perform_action(self, mqtt_client, action: str, value: Optional[Any] = None):
        payload = {}
        if(action == "set_temperature"):
            try: payload["current_heating_setpoint"] = float(value)
            except: pass
        if(payload):
            mqtt_client.publish(f"{self.topic}/set", payload)

class ControllerDevice(BaseDevice):
    """
    Obsługa pilotów, przycisków ściennych i innych kontrolerów (Action only).
    """
    def perform_action(self, mqtt_client, action: str, value: Optional[Any] = None):
        pass