from machine import ADC, Pin, I2S
import time
import math
import struct

# ========== CONFIG & PINS ==========
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

PIR_PIN = 35
pir = Pin(PIR_PIN, Pin.IN)

SCK_PIN = 14
WS_PIN = 15
SD_PIN = 32
I2S_ID = 0
BUFFER_LEN = 1024

RESET_BUTTON_PIN = 27
reset_button = Pin(RESET_BUTTON_PIN, Pin.IN, Pin.PULL_UP)

PANIC_BUTTON_PIN = 12
panic_button = Pin(PANIC_BUTTON_PIN, Pin.IN, Pin.PULL_UP)

CALIBRATION_OFFSET = 110.8  # For sound sensor

MOTION_STICKY_SECONDS = 10
SMOKE_STICKY_SECONDS = 30
SMOKE_THRESHOLD = 600      # Set as needed

last_motion_time = 0
last_smoke_time = 0
panic_active = False

# === I2S AUDIO SETUP ===
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
        return None
    samples = struct.unpack("<{}h".format(BUFFER_LEN), audio_samples)
    sum_squares = sum(sample ** 2 for sample in samples)
    rms = math.sqrt(sum_squares / len(samples))
    dbfs = 20 * math.log10(rms / 32768) if rms > 0 else -100.0
    dbspl = dbfs + CALIBRATION_OFFSET
    return dbspl

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

# === MAIN ===

Ro = MQCalibration()

print("=== Sensor Self-Test Starting ===")
print("Press PANIC or RESET buttons to test their latching logic.")
print("Wave your hand for motion or blow smoke for the MQ2 test.\n")

while True:
    now = time.time()

    # Panic Button
    if panic_button.value() == 0:
        panic_active = True

    # Motion (PIR)
    if pir.value():
        last_motion_time = now
    motion_sticky = (now - last_motion_time) < MOTION_STICKY_SECONDS

    # Gas/Smoke
    rs = MQRead()
    rs_ro_ratio = rs / Ro if Ro else 0
    lpg = MQGetGasPercentage(rs_ro_ratio, 0)
    co = MQGetGasPercentage(rs_ro_ratio, 1)
    smoke = MQGetGasPercentage(rs_ro_ratio, 2)
    if smoke > SMOKE_THRESHOLD:
        last_smoke_time = now
    smoke_sticky = (now - last_smoke_time) < SMOKE_STICKY_SECONDS

    # Sound
    sound = calculate_decibels()

    # Reset Button
    if reset_button.value() == 0:
        print("Reset button pressed! Clearing latches.")
        panic_active = False
        last_motion_time = 0
        last_smoke_time = 0

    # PRINT ALL VALUES (for testing)
    print("=" * 40)
    print("Panic Button Latch :", panic_active)
    print("Motion Sticky      :", motion_sticky, "| PIR Raw:", pir.value())
    print("Smoke Sticky       :", smoke_sticky,  "| Smoke Raw:", smoke)
    print("LPG Value          :", lpg,  "| CO Value:", co)
    print("Sound Level (dB)   :", sound if sound is not None else "N/A")
    print("Reset Button       :", "Pressed" if reset_button.value() == 0 else "Not Pressed")
    print("=" * 40)
    time.sleep(2)  # 2s for easier reading, change as needed
