import time
import random
import paho.mqtt.client as mqtt

BROKER = "100.95.5.22"  # IP de Tailscale de tu servidor AWS
PORT = 1883
TOPIC = "classroom/co2"

client = mqtt.Client()
client.connect(BROKER, PORT, 60)

# Parámetros del simulador
THRESHOLD = 1000          # ppm considerados altos
HIGH_DURATION = 5          # segundos de lectura alta para activar el ventilador
INTERVAL = 1               # segundos entre lecturas

high_counter = 0
fan_on = False

while True:
    # Generar CO2 simulado (mayoría de veces normal)
    if random.random() < 0.1:
        co2 = round(random.uniform(1100, 1800), 2)  # ocasional pico alto
    else:
        co2 = round(random.uniform(400, 800), 2)    # rango saludable

    # Verificar si está alto
    if co2 > THRESHOLD:
        high_counter += 1
    else:
        high_counter = 0
        fan_on = False  # se apaga automáticamente al volver a nivel normal

    # Si ha estado alto por 5 lecturas seguidas, activar ventilador
    if high_counter >= HIGH_DURATION:
        fan_on = True

    # Crear payload JSON
    payload = (
        f'{{"co2_ppm": {co2}, "fan": {"true" if fan_on else "false"}}}'
    )

    # Publicar al broker
    client.publish(TOPIC, payload)
    print(f"Sent: {payload}")

    time.sleep(INTERVAL)
