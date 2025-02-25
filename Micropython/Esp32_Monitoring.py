import network
import time
import dht
import json
import ubinascii
import machine
import micropython
from machine import Pin, ADC
from umqtt.simple import MQTTClient

SSID = "Dharma 4"
PASSWORD = "0818881210"

FLASK_URL = "http://192.168.1.34:5000/sensor"

MQTT_BROKER = "industrial.api.ubidots.com"
MQTT_PORT = 1883
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode()
MQTT_USERNAME = "BBUS-rwpnZ3gR5zHDDAKXzEDPFqRQj4g4oQ"
MQTT_PASSWORD = ""
MQTT_TOPIC = f"/v1.6/devices/sensor_esp"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    print("\n📡 Menghubungkan ke WiFi...", end="")
    timeout = 10  
    while not wlan.isconnected() and timeout > 0:
        print(".", end="", flush=True)
        time.sleep(1)
        timeout -= 1

    if wlan.isconnected():
        print("\n✅ Terhubung ke WiFi:", wlan.ifconfig()[0])
        return True
    else:
        print("\n❌ Gagal terhubung ke WiFi. Periksa SSID/PASSWORD.")
        return False

while not connect_wifi():
    print("🔄 Mencoba kembali menyambungkan ke WiFi...")
    time.sleep(5)

print("\n⏳ Menunggu sensor siap...")
time.sleep(15)  

ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)

dht_sensor = dht.DHT11(Pin(4))
pir_sensor = Pin(12, Pin.IN)
total_gerakan = 0

TRIG = Pin(5, Pin.OUT)
ECHO = Pin(18, Pin.IN)

def connect_mqtt():
    client = MQTTClient(
        MQTT_CLIENT_ID,
        MQTT_BROKER,
        MQTT_PORT,
        MQTT_USERNAME,
        MQTT_PASSWORD
    )
    client.connect()
    print("\n✅ Terhubung ke MQTT Ubidots")
    return client

def get_ldr_value():
    return ldr.read()

def get_dht_data():
    try:
        dht_sensor.measure()
        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        return temperature, humidity
    except OSError:
        print("⚠️ ERROR: Gagal membaca sensor DHT11!")
        return None, None

def get_pir_value():
    global total_gerakan
    if pir_sensor.value() == 1:
        total_gerakan += 1
        return True  
    return False

def get_distance():
    TRIG.off()
    time.sleep_us(2)
    TRIG.on()
    time.sleep_us(10)
    TRIG.off()

    while ECHO.value() == 0:
        start = time.ticks_us()
    while ECHO.value() == 1:
        end = time.ticks_us()

    duration = end - start
    distance = (duration * 0.0343) / 2 
    return round(distance, 2)

# Fungsi Mengirim Data
def send_data():
    if not network.WLAN(network.STA_IF).isconnected():
        print("⚠️ Tidak ada koneksi WiFi. Mencoba menyambung kembali...")
        if not connect_wifi():
            return

    ldr_value = get_ldr_value()
    suhu, kelembaban = get_dht_data()
    jarak = get_distance()
    gerakan_terdeteksi = get_pir_value()

    if suhu is None or kelembaban is None:
        print("⚠️ Data tidak valid, tidak mengirim ke server.")
        return

    payload = {
        "ldr": {"value": ldr_value},
        "temperature": {"value": suhu},
        "humidity": {"value": kelembaban},
        "distance": {"value": jarak},  
        "motion": {"value": total_gerakan}
    }

    json_payload = json.dumps(payload)
    headers = {'Content-Type': 'application/json'}
    
    print("\n📡 Mengirim data ke server...")
    print("📊 Data Sensor:", json_payload)

    try:
        import urequests
        response = urequests.post(FLASK_URL, data=json_payload, headers=headers)
        if response.status_code in [200, 201]:
            print("✅ Data berhasil dikirim ke Flask API!")
        else:
            print(f"❌ Gagal mengirim ke Flask API, kode {response.status_code}")
        response.close()

    except Exception as e:
        print(f"⚠️ ERROR saat mengirim ke Flask API: {str(e)}")

    try:
        # Kirim ke Ubidots via MQTT
        mqtt_client = connect_mqtt()
        mqtt_client.publish(MQTT_TOPIC, json_payload)
        print("✅ Data berhasil dikirim ke Ubidots via MQTT!")
        mqtt_client.disconnect()

    except Exception as e:
        print(f"⚠️ ERROR saat mengirim ke Ubidots via MQTT: {str(e)}")


update_count = 0 

while True:
    update_count += 1

    if update_count % 5 == 0 or get_pir_value():
        send_data()
        update_count = 0  

    time.sleep(5) 