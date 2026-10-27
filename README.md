# Smart Home Mesh

A local home automation system built on a **Zigbee** mesh network. It runs entirely within the LAN, with no dependency on cloud services. This repository contains the software for the central unit (Raspberry Pi 4): a Python backend (FastAPI) with a rule engine and a web control panel.

The project was developed as part of the engineering thesis *"Design and implementation of an intelligent Smart Home system based on mesh network technology"* (AGH University of Krakow, Faculty of EAIiIB, Automatic Control and Robotics, 2026).

Firmware for the custom sensor node (ESP32-C6 + BME280): [Smart-Home_Sensor_ESP32-C6](https://github.com/Czerniej/Smart-Home_Sensor_ESP32-C6)

## Features

- **Device auto-discovery** – the device list is fetched from Zigbee2MQTT; the device type (`LightDevice`, `SocketDevice`, `SensorDevice`) is chosen automatically from the `exposes` field.
- **Device control** – on/off, brightness and color (lights).
- **Groups** – combine devices logically and control them with a single command.
- **Rule engine** – automations triggered by a device state change (operators `eq`, `neq`, `gt`, `lt`, `gte`, `lte`) or at a set time.
- **Pairing from the UI** – enables `permit_join` for 60 s.
- **Network map and logs** – view the mesh topology (LQI, node roles) and recent system events.
- **Persistence** – device registry, groups and rules are stored in SQLite; state is restored after a restart.

## Architecture

```
[Zigbee nodes] ──► [USB coordinator] ──► Zigbee2MQTT ──► Mosquitto ──► Python app ──► SQLite
                     (Sonoff CC2652P)                                    ▲
                                                                         │ REST API
                                                                  Web interface (SPA)
```

The application runs three threads: the MQTT network loop, the API server (Uvicorn), and a timer loop that checks scheduled rules every 60 s. Shared state is protected with `threading.Lock`.

## Repository structure

```
├── main.py               # entry point: initialization, MQTT message routing, thread startup
├── api.py                # REST API (FastAPI)
├── config.py             # configuration (broker, API port, paths)
├── logging_config.py     # logging to console and smart_home.log (5 MB rotation)
├── core/
│   ├── mqtt_client.py    # MQTT client (paho-mqtt)
│   ├── device_manager.py # in-memory device and group state
│   ├── devices_types.py  # BaseDevice and subclasses
│   ├── rule_engine.py    # automation rule engine
│   └── database.py       # SQLite access layer
├── frontend/             # SPA: HTML + Bootstrap 5 + Vanilla JS
├── tests/                # pytest tests (API, database, rule engine)
└── smarthome.service     # systemd unit
```

## Requirements

**Hardware**
- Raspberry Pi 4 (or another Linux machine)
- USB Zigbee coordinator, e.g. Sonoff Zigbee 3.0 USB Dongle Plus (CC2652P)
- Zigbee 3.0 compatible devices

**Software**
- Python 3.11
- [Eclipse Mosquitto](https://mosquitto.org/)
- [Zigbee2MQTT](https://www.zigbee2mqtt.io/)

## Installation

### 1. Mosquitto

Install the broker and create a user:

```bash
sudo apt install mosquitto mosquitto-clients
sudo mosquitto_passwd -c /etc/mosquitto/passwd <username>
```

In `/etc/mosquitto/mosquitto.conf` (or a file in `conf.d/`):

```
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
```

```bash
sudo systemctl enable --now mosquitto
```

### 2. Zigbee2MQTT

Install Zigbee2MQTT following the [documentation](https://www.zigbee2mqtt.io/guide/installation/). In `configuration.yaml`, set the coordinator's serial port and the broker credentials, and disable pairing by default:

```yaml
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://localhost:1883
  user: <username>
  password: <password>
serial:
  port: /dev/ttyUSB0
permit_join: false
```

To support the custom ESP32-C6 node, add an external converter for the `ESP32C6_BME280` model to Zigbee2MQTT (see the firmware repository for details).

### 3. Application

```bash
git clone https://github.com/Czerniej/Smart-Home_Mesh.git
cd Smart-Home_Mesh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

In `.env`, enter the MQTT broker credentials (the same as in step 1):

```
MQTT_USERNAME=<username>
MQTT_PASSWORD=<password>
```

Run:

```bash
python main.py
```

The panel is available at `http://localhost:8000` and the interactive API documentation at `http://localhost:8000/docs`.

> **Access from the local network:** by default the server listens only on `localhost`. To open the panel from other devices on the LAN, set `API_HOST = "0.0.0.0"` in `config.py`.

### 4. systemd service (optional)

`smarthome.service` assumes the `admin` user and the `/home/admin/Smart-Home_Mesh` directory — adjust the paths if needed.

```bash
sudo cp smarthome.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smarthome
journalctl -u smarthome -f
```

## Configuration

Main settings in `config.py`:

| Parameter | Default | Description |
|---|---|---|
| `BROKER_ADDRESS` / `BROKER_PORT` | `localhost` / `1883` | MQTT broker address |
| `MQTT_TOPIC_SUBSCRIBE` | `zigbee2mqtt/#` | subscribed topics |
| `API_HOST` / `API_PORT` | `localhost` / `8000` | HTTP server address |
| `DATABASE_FILE_PATH` | `data/smarthome.db` | SQLite database file (directory is created automatically) |
| `LOG_FILE_PATH` | `smart_home.log` | log file |
| `TIME_CHECK_INTERVAL_SECONDS` | `60` | scheduled rule check interval |

## REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/devices` | list devices |
| `POST` | `/devices` | register a device manually |
| `DELETE` | `/devices/{device_id}` | remove a device |
| `PUT` | `/devices/{device_id}/rename` | rename a device |
| `POST` | `/devices/action` | perform an action on a device or group |
| `GET` / `POST` | `/groups` | list / create groups |
| `DELETE` | `/groups/{group_id}` | delete a group |
| `POST` / `DELETE` | `/groups/{group_id}/devices/{device_id}` | add / remove a group member |
| `GET` / `POST` | `/rules` | list / add rules |
| `PUT` / `DELETE` | `/rules/{rule_id}` | update / delete a rule |
| `POST` | `/system/pairing/{true\|false}` | enable / disable pairing |
| `GET` | `/logs` | recent system logs |

Action example:

```json
POST /devices/action
{ "device_id": "0xa4c138...", "action": "turn_on" }
```

Available actions: `turn_on`, `turn_off` (sockets and lights), `set_brightness` (0–254), `set_color` (HEX, e.g. `"#ff8800"`).

### Rule format

Rule triggered by device state:

```json
{
  "id": "rule_1",
  "name": "Turn on the lamp after dark",
  "active": true,
  "trigger": { "device_id": "0x...sensor", "key": "illuminance", "operator": "lt", "value": 40 },
  "action":  { "device_id": "0x...socket", "command": "turn_on" }
}
```

Scheduled rule:

```json
{
  "id": "rule_2",
  "name": "Turn off at 23:00",
  "active": true,
  "trigger": { "type": "time", "time": "23:00" },
  "action":  { "device_id": "0x...socket", "command": "turn_off" }
}
```

A rule does not fire again while its condition stays true — it re-arms once the condition becomes false.

## Tests

The tests run without physical Zigbee hardware (components are mocked):

```bash
pytest -v
```

They cover the rule engine (all operators, rule state reset), API CRUD operations including error codes (404, 409, 422), and database persistence.

## Author

Konrad Czerniej — engineering thesis, AGH University of Krakow, 2026
