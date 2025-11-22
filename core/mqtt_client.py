import paho.mqtt.client as mqtt
import json
import logging
import sys
import time

import config 

logger = logging.getLogger(__name__)

class MQTT_Client:
    """
    Klient MQTT do komunikacji z brokerem Mosquitto.
    """
    def __init__(self, on_message_callback=None):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
        self.on_message_callback = on_message_callback
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False

    def connect(self, BROKER_ADDRESS: str = config.BROKER_ADDRESS, BROKER_PORT: int = config.BROKER_PORT):
        """
        Próbuje połączyć się z brokerem i uruchamia pętlę w tle.
        """
        if(config.MQTT_USERNAME and config.MQTT_PASSWORD):
            self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
            logger.info(f"Skonfigurowano autoryzację MQTT dla użytkownika: {config.MQTT_USERNAME}")

        logger.info(f"Próba połączenia z brokerem {BROKER_ADDRESS}:{BROKER_PORT}...")
        try:
            self.client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
            self.client.loop_start() 
        except Exception as e:
            logger.critical(f"KRYTYCZNY BŁĄD łączenia z brokerem MQTT: {e}. Zamykanie systemu.")
            sys.exit(1)

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Callback wywoływany po próbie połączenia.
        """
        if(rc == 0):
            self.connected = True
            logger.info("Połączenie MQTT nawiązane pomyślnie.")
            self.client.subscribe(config.MQTT_TOPIC_SUBSCRIBE)
            logger.info(f"Zasubskrybowano temat: {config.MQTT_TOPIC_SUBSCRIBE}")
        else:
            self.connected = False
            if(rc == 4):
                logger.error("Błąd MQTT (rc=4): Zły login lub hasło.")
            elif(rc == 5):
                logger.error("Błąd MQTT (rc=5): Brak autoryzacji.")
            else:
                logger.error(f"Połączenie MQTT nieudane. Kod błędu (rc) = {rc}.")

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        """
        Callback wywoływany po rozłączeniu.
        """
        self.connected = False
        if(rc != 0):
            logger.warning(f"Klient MQTT został nieoczekiwanie rozłączony. Kod: {rc}. Próba ponownego połączenia...")
        else:
            logger.info("Klient MQTT rozłączony pomyślnie.")

    def on_message(self, client, userdata, msg):
        """
        Callback wywołyany po odebraniu wiadomości.
        """
        try:
            payload = json.loads(msg.payload.decode('utf-8')) 
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning(f"Błąd dekodowania JSON lub kodowania dla topicu: {msg.topic}. Pominięto.")
            return
        if(self.on_message_callback):
            self.on_message_callback(msg.topic, payload)
        else:
             logger.debug(f"Odebrano wiadomość, ale brak przypisanego callbacka: {msg.topic}")

    def publish(self, topic: str, payload: dict | str):
        """
        Publikuje wiadomość na brokerze.
        """
        if(not self.connected):
            logger.warning(f"Próba publikacji na {topic} przy braku połączenia MQTT. Pominięto.")
            return
        try:
            if(isinstance(payload, dict)):
                payload_str = json.dumps(payload) 
            elif(isinstance(payload, str)):
                 payload_str = payload
            else:
                 logger.error(f"Nieznany typ payloadu do publikacji: {type(payload)}.")
                 return
            self.client.publish(topic, payload_str)
            logger.info(f"Wysłano: {topic} -> {payload_str}")
        except Exception as e:
            logger.error(f"Błąd publikacji MQTT na {topic}: {e}")

    def disconnect(self):
        """
        Rozłącza klienta MQTT i zatrzymuje pętlę.
        """
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Rozłączono klienta MQTT.")
        except Exception as e:
            logger.error(f"Błąd podczas rozłączania MQTT: {e}")