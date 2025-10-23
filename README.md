# CO₂ en aulas escolares para ventilación inteligente

Nombre: Ernesto Torres Pineda 

No. Control: 22211665

Fecha: 21/10/2025

## Descripción General

El sistema desarrollado permite **monitorear los niveles de dióxido de carbono (CO₂)** en un aula mediante sensores conectados a una **Raspberry Pi**, la cual envía los datos a través del protocolo **MQTT** hacia un servidor donde se almacenan en **InfluxDB** y se visualizan en **Grafana**.
Además, se implementa un mecanismo de **control de ventilación** que permite analizar el porcentaje de tiempo en que el ambiente se mantiene dentro de niveles saludables (<1000 ppm).

---

## Componentes del Sistema

* **Python** (para scripts de adquisición y publicación de datos).
* **Mosquitto (MQTT Broker)** para comunicación entre dispositivos.
* **InfluxDB** como base de datos de series temporales.
* **Grafana** para visualización de datos.
* **Tailscale** para comunicación segura entre nodos de red.

---

## Flujo de Datos

1. **Captura:** Sensor de CO₂ (simulación) → Raspberry Pi
2. **Publicación:** Python (Publisher) → MQTT Broker
3. **Recepción:** Python (Subscriber) → InfluxDB
4. **Visualización:** Grafana Dashboard


---

## 1. En el Raspberry Pi (Simulación del Sensor y Publicación MQTT)**

### Pasos

1. **Crear el script `co2.py`:**

   * Genera valores simulados de CO₂ (mayormente en rangos saludables: 400–1000 ppm).
   * Si el nivel supera 1000 ppm por más de 5 segundos seguidos, activa una bandera `fan = True`.
   * Envía los datos en formato JSON al broker MQTT (ubicado en AWS o tu PC).

2. **Configurar el broker MQTT:**

   * En el script, define la IP Tailscale del servidor o PC como `BROKER`.
   * Usa el puerto `1883` y un topic como `lab/sensors`.

   Para configurar el puerto se ejecuta el siguiente comando dentro del raspberry 
   
   ```bash
   sudo nano /etc/mosquitto/mosquitto.conf
   ```
    Dentro del archivo de configuracion se agregan las siguientes lineas
  
    ```bash
    listener 1883 0.0.0.0
    allow_anonymous true
    ```

    <img width="1055" height="594" alt="image" src="https://github.com/user-attachments/assets/9a3ded56-8c5e-4952-a3e7-dc8de7767115" />

    
4. **Ejecutar el script:**

   ```bash
   python3 co2_publisher.py
   ```

   * El script comenzará a publicar lecturas simuladas cada segundo.
   * Cuando el CO₂ se mantenga alto por más de 5 segundos, el valor de `fan` cambiará a `true`.

<img width="1033" height="567" alt="image" src="https://github.com/user-attachments/assets/0f9b6df9-15a6-403e-84bc-6e99f8537405" />


---

## 2. En la Máquina de AWS o PC con InfluxDB/Grafana (Recepción y Almacenamiento)**

### Pasos

1. **Crear el script `mqtt_to_influx.py`:**

   * Se suscribe al topic `lab/sensors`.
   * Recibe los mensajes JSON enviados por el Raspberry.
   * Inserta los datos en InfluxDB dentro del bucket correspondiente (por ejemplo, `aulas`).

2. **Configurar parámetros:**

   * `BROKER`: la IP Tailscale del Raspberry Pi.
   * `PORT`: 1883.
   * `TOPIC`: `"lab/sensors"`.
   * `TOKEN`: tu token de InfluxDB.
   * `ORG` y `BUCKET`: los mismos que configuraste en InfluxDB.

3. **Ejecutar el script:**

   ```bash
   python3 mqtt_to_influx.py
   ```

   * Si todo está correcto, verás en la terminal mensajes tipo:

     ```
     Stored: {'co2_ppm': 820, 'fan': False}
     ```
   * Esto confirma que los datos se están escribiendo en InfluxDB.

4. **Verificar almacenamiento en InfluxDB:**

   * Entra al panel web de InfluxDB (`http://localhost:8086`).
   * Abre **Data Explorer → aulas → co2_classroom**.
   * Ejecuta una consulta para confirmar que se registran los valores de `co2_ppm` y `fan`.

<img width="1068" height="644" alt="Screenshot 2025-10-21 113313" src="https://github.com/user-attachments/assets/27654bd4-5056-4d71-bf01-4f85cbd903bf" />

<img width="1919" height="919" alt="image" src="https://github.com/user-attachments/assets/025b2e9a-6751-4218-bfef-d9f266bfde2c" />

---
## 3. Creación de Paneles en Grafana

## Crear Panel de Serie Temporal (Time Series)

### Pasos

 En el menú lateral, selecciona **“Dashboards → New → New Dashboard”**.

 Haz clic en **“Add Visualization”**.

 Elige **InfluxDB** como fuente de datos.

 En el editor Flux, ingresa una consulta similar a:

   ```flux
   from(bucket: "aulas")
     |> range(start: -1h)
     |> filter(fn: (r) => r._measurement == "co2_classroom")
     |> filter(fn: (r) => r._field == "co2_ppm")
     |> filter(fn: (r) => r.ubicacion == "aula1")
   ```

 En el panel derecho:

   * **Visualization:** selecciona *Time series*.
   * **Unit:** selecciona *ppm* (partes por millón).
   * **Thresholds:** define colores, por ejemplo:

     * Verde: < 1000 ppm
     * Amarillo: 1000–1500 ppm
     * Rojo: > 1500 ppm

 Haz clic en **Apply** y nombra el panel como **“Niveles de CO₂ (ppm)”**.

<img width="1261" height="759" alt="Screenshot 2025-10-21 122248" src="https://github.com/user-attachments/assets/edcacf53-a71d-4e51-bd04-1c5bdc90dc6f" />

---

##  Crear Panel de Estado (Stat o Gauge)

### Pasos

En el editor, ingresa la siguiente consulta Flux:

   ```flux
   from(bucket: "aulas")
     |> range(start: -1h)
     |> filter(fn: (r) => r._measurement == "co2_classroom")
     |> filter(fn: (r) => r._field == "co2_ppm")
     |> filter(fn: (r) => r.ubicacion == "aula1")
     |> group()
     |> reduce(
         identity: {ok: 0.0, total: 0.0},
         fn: (accumulator, r) => ({
             ok: if r._value < 1000.0 then accumulator.ok + 1.0 else accumulator.ok,
             total: accumulator.total + 1.0
         })
     )
     |> map(fn: (r) => ({
         _value: (r.ok / r.total) * 100.0
     }))
     |> yield(name: "porcentaje_saludable")
   ```

En la configuración del panel:

   * **Visualization:** selecciona *Gauge* o *Stat*.
   * **Unit:** elige *percent (0–100)*.
   * **Thresholds:**

     * Verde: > 80% (ambiente saludable)
     * Amarillo: 50–80%
     * Rojo: < 50%

Asigna un título al panel, por ejemplo **“Porcentaje de tiempo con aire saludable”**.

 Haz clic en **Apply**.

<img width="1239" height="750" alt="Screenshot 2025-10-21 122258" src="https://github.com/user-attachments/assets/7cc67e4f-b191-43dd-aa62-f95f8a105942" />

---

## Creación del Panel de Ventilador Encendido (Tabla)

##  Escribir la Consulta Flux

1. En el editor de consultas, escribe:

   ```flux
   from(bucket: "aulas")
     |> range(start: -1h)
     |> filter(fn: (r) => r._measurement == "co2_classroom")
     |> filter(fn: (r) => r._field == "fan")
     |> filter(fn: (r) => r.ubicacion == "aula1")
     |> filter(fn: (r) => r._value == true)
     |> yield(name: "ventilador_encendido")
   ```

2. Ejecuta la consulta con **Run query**.

3. Verifica que aparecen solo los registros donde `_value` es **true**.

---

## 4. Configurar el Panel

1. En la parte derecha, selecciona **Visualization → Table**.

2. En **Columns**, conserva solo:

   * **_time** (momento en que se encendió el ventilador)
   * **_value** (estado: true)

3. Cambia el título del panel a:
   **“Registros de ventilador encendido”**

4. En la sección **Panel options**:

   * Activa la opción **“Show time”** si deseas ver la hora exacta.
   * Ajusta el **refresh rate** (por ejemplo, cada 5 segundos).
   * Opcional: cambia el formato de tiempo a *Local time (browser)*.

<img width="1236" height="777" alt="Screenshot 2025-10-21 122312" src="https://github.com/user-attachments/assets/e4abe09d-ecc5-4df0-bdb7-4dc318fb310b" />

---
## Resultados 

<img width="1582" height="644" alt="Screenshot 2025-10-21 113313" src="https://github.com/user-attachments/assets/f6d5d417-ba50-460d-92a6-33b660b50f21" />


<img width="1603" height="683" alt="Screenshot 2025-10-21 120616" src="https://github.com/user-attachments/assets/35fb408f-7dc2-4f8a-be64-3e1a243f7ce3" />

LOOM: https://www.loom.com/share/90c4db28799d4ef090638c4c3f86f66a?sid=ad3a1577-d4dc-4d11-8aaf-7fdcf2ceff82 

