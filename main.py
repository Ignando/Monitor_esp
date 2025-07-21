from machine import ADC, Pin, I2S
import time
import math
import network
from umqtt.simple import MQTTClient
import ujson 
import struct

import wifimgr

wlan = wifimgr.get_connection()
if wlan is None:
    print("Could not initialize the network connection.")
    while True:
        pass
print("Connected to WiFi:", wlan.ifconfig())



# ========== CONFIG ==========


MQTT_BROKER = "datum.cedalo.cloud"
MQTT_PORT = 8883
CLIENT_ID = b"EDGE"
USERNAME = b"EdgePrototypeDevice01"
PASSWORD = b"s9HR6VIdn1Rh6dh5fF"
TOPIC = b"device/property/monitor"

PROPERTY_ID = "APT001"
COMPLEX_ID = "1"
wlan = network.WLAN(network.STA_IF)


# ========== GAS SENSOR SETUP ==========
MQ_PIN = 34
RL_VALUE = 5.0
RO_CLEAN_AIR_FACTOR = 9.83
CALIBRATION_SAMPLE_TIMES = 50
CALIBRATION_SAMPLE_INTERVAL = 0.5
READ_SAMPLE_TIMES = 5
READ_SAMPLE_INTERVAL = 0.05
LPGCurve = [2.3, 0.21, -0.47]
COCurve = [2.3, 0.72, -0.34]
SmokeCurve = [2.3, 0.53, -0.44]
Ro = 10.0

adc = ADC(Pin(MQ_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_10BIT)  

# ========== PIR SENSOR SETUP ==========
PIR_PIN = 35
pir = Pin(PIR_PIN, Pin.IN)

# === I2S CONFIGURATION ===
SCK_PIN = 14
WS_PIN = 15
SD_PIN = 32
I2S_ID = 0
BUFFER_LEN = 1024

PANIC_BUTTON_PIN = 12
panic_button = Pin(PANIC_BUTTON_PIN, Pin.IN, Pin.PULL_UP)


# === CALIBRATION OFFSET ===
CALIBRATION_OFFSET = 110.8  # Based on 70 dB SPL = -39.8 dBFS

# === SETUP I2S ===
audio_in = I2S(
    I2S_ID,
    sck=Pin(SCK_PIN),
    ws=Pin(WS_PIN),
    sd=Pin(SD_PIN),
    mode=I2S.RX,
    bits=16,
    format=I2S.MONO,
    rate=16000,
    ibuf=BUFFER_LEN * 2
)

def calculate_decibels():
    audio_samples = bytearray(BUFFER_LEN * 2)
    num_bytes_read = audio_in.readinto(audio_samples)

    if num_bytes_read <= 0:
        return None, None

    # Unpack bytearray into signed 16-bit integers
    samples = struct.unpack("<{}h".format(BUFFER_LEN), audio_samples)

    # Calculate RMS
    sum_squares = sum(sample ** 2 for sample in samples)
    rms = math.sqrt(sum_squares / len(samples))

    if rms == 0:
        dbfs = -100.0
    else:
        dbfs = 20 * math.log10(rms / 32768)

    dbspl = dbfs + CALIBRATION_OFFSET
    return dbspl


# ========== FUNCTIONS ==========

def MQResistanceCalculation(raw_adc):
    if raw_adc == 0:
        return 0
    return (RL_VALUE * (1023 - raw_adc) / raw_adc)

def MQCalibration():
    val = 0.0
    print("Calibrating MQ-2...")
    for _ in range(CALIBRATION_SAMPLE_TIMES):
        val += MQResistanceCalculation(adc.read())
        time.sleep(CALIBRATION_SAMPLE_INTERVAL)
    val = val / CALIBRATION_SAMPLE_TIMES
    val = val / RO_CLEAN_AIR_FACTOR
    print("Calibration done. Ro = {:.2f} kOhm".format(val))
    return val

def MQRead():
    rs = 0.0
    for _ in range(READ_SAMPLE_TIMES):
        rs += MQResistanceCalculation(adc.read())
        time.sleep(READ_SAMPLE_INTERVAL)
    rs = rs / READ_SAMPLE_TIMES
    return rs

def MQGetPercentage(rs_ro_ratio, pcurve):
    try:
        return pow(10, ((math.log(rs_ro_ratio)/math.log(10) - pcurve[1]) / pcurve[2]) + pcurve[0])
    except Exception as e:
        return 0

def MQGetGasPercentage(rs_ro_ratio, gas_id):
    if gas_id == 0:
        return MQGetPercentage(rs_ro_ratio, LPGCurve)
    elif gas_id == 1:
        return MQGetPercentage(rs_ro_ratio, COCurve)
    elif gas_id == 2:
        return MQGetPercentage(rs_ro_ratio, SmokeCurve)
    else:
        return 0

def connect_and_subscribe():
    global client
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT,
                            user=USERNAME, password=PASSWORD, ssl=True, ssl_params={})
        client.connect()
        print("Connected to MQTT broker!")
        return True
    except Exception as e:
        print("Failed to connect to MQTT broker. Retrying...", str(e))
        return False
    
def rssi_to_percent(rssi):
    if rssi is None:
        return 0
    if rssi <= -100:
        return 0
    elif rssi >= -50:
        return 100
    else:
        return int(2 * (rssi + 100))

def publish_data(lpg, co, smoke, motion, sound, panic):
    rssi = wlan.status('rssi')
    wifi_strength = rssi_to_percent(rssi)
    payload = ujson.dumps({
        "property_id": PROPERTY_ID,
        "complex_id": COMPLEX_ID,   
        "occupied": bool(motion),  
        "gas": {
            "lpg": float(lpg),
            "co": float(co),
            "smoke": float(smoke)
        },
        "motion_detected": bool(motion),
        "wifi_strength": wifi_strength,
        "sound_level" : sound,
        "panic": panic  
})
    try:
        client.publish(TOPIC, payload)
        print("Published:", payload)
        return True
    except Exception as e:
        print("Publish failed, reconnecting...", str(e))
        return False

# === MAIN ===


while not connect_and_subscribe():
    time.sleep(5)

Ro = MQCalibration()

while True:
    # Sensor readings
    rs = MQRead()
    rs_ro_ratio = rs / Ro if Ro else 0
    lpg = MQGetGasPercentage(rs_ro_ratio, 0)
    co = MQGetGasPercentage(rs_ro_ratio, 1)
    smoke = MQGetGasPercentage(rs_ro_ratio, 2)
    motion = pir.value()
    sound = calculate_decibels()
    panic = panic_button.value() == 0  # True if pressed (LOW)




    # Publish to MQTT, reconnect if needed
    if not publish_data(lpg, co, smoke, motion, sound, panic):
        while not connect_and_subscribe():
            time.sleep(5)

    time.sleep(60)  # send data once per minute (adjust for testing)
