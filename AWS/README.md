# Visualizacion del script en la maquina AWS

```python
# mqtt_to_influx_co2.py
import json
from influxdb_client import InfluxDBClient, Point, WritePrecision
from paho.mqtt import client as mqtt_client

# -------- Configuración MQTT --------
BROKER = "100.91.71.85"   # IP Tailscale del Raspberry Pi (donde corre Mosquitto)
PORT = 1883
TOPIC = "classroom/co2"

# -------- Configuración InfluxDB --------
INFLUX_URL = "http://localhost:8086"  # Si InfluxDB corre localmente en AWS
TOKEN = "6w2VFxZwXybrGSptgZ2RPB4MkNRlQ8_Yibn__ryg4Rb9fPYyK-K6lkt5VRd3iHhqzqcvlZyCfjnOMlL0xJR_dA=="
ORG = "escuela"
BUCKET = "aulas"

# -------- Conexión a InfluxDB --------
influx = InfluxDBClient(url=INFLUX_URL, token=TOKEN, org=ORG)
write_api = influx.write_api()

# -------- Callback para manejar mensajes MQTT --------
def on_message(client, userdata, msg):
    try:
        # Decodificar y parsear JSON
        data = json.loads(msg.payload.decode())

        co2_ppm = float(data.get("co2_ppm", 0))
        fan_state = bool(data.get("fan", False))

        # Crear punto de medición para InfluxDB
        point = (
            Point("co2_classroom")
            .tag("ubicacion", "aula1")
            .field("co2_ppm", co2_ppm)
            .field("fan", fan_state)
            .time(write_precision=WritePrecision.NS)
        )

        # Escribir el punto en InfluxDB
        write_api.write(bucket=BUCKET, record=point)
        print(f"Stored -> CO2: {co2_ppm} ppm, Fan: {fan_state}")

    except Exception as e:
        print("Error:", e)

# -------- Conexión al broker MQTT --------
client = mqtt_client.Client()
client.connect(BROKER, PORT)
client.subscribe(TOPIC)
client.on_message = on_message

print(f"Conectado al broker {BROKER}:{PORT}, escuchando el tópico '{TOPIC}'...")
client.loop_forever()
```

