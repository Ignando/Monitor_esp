from machine import ADC, Pin, I2S
import time
import math
import struct

# === MQ-2 Gas Sensor ===
MQ_PIN = 34
adc = ADC(Pin(MQ_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_10BIT)  # 0–1023

# === PIR Motion Sensor ===
PIR_PIN = 35
pir = Pin(PIR_PIN, Pin.IN)

# === Panic Button ===
PANIC_PIN = 13
panic_button = Pin(PANIC_PIN, Pin.IN, Pin.PULL_UP)

# === Reset Button ===
RESET_PIN = 4
reset_button = Pin(RESET_PIN, Pin.IN, Pin.PULL_UP)  # Pin 4, adjust as needed

# === I2S MEMS Microphone ===
SCK_PIN = 14
WS_PIN = 15
SD_PIN = 32
I2S_ID = 0
BUFFER_LEN = 1024
CALIBRATION_OFFSET = 110.8  # You can tweak for your mic

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

panic_active = False  # <--- Latches when panic is pressed, reset clears it

print("=== Motion, MQ-2, Mic, Panic, and Reset Button Test ===")
print("Wave your hand for motion, blow on MQ-2, make noise, or press the panic button.\nPress RESET (Pin 4) to clear panic state.\n")

while True:
    # PIR Motion
    motion = pir.value()
    print("Motion:", "Detected" if motion else "None", end=' | ')
    
    # MQ-2 Gas
    mq_value = adc.read()
    print("MQ-2:", mq_value, end=' | ')
    
    # INMP441 Microphone
    sound = calculate_decibels()
    print("Sound Level (dB SPL):", round(sound, 2) if sound is not None else "N/A", end=' | ')
    
    # Panic Button latch logic
    if panic_button.value() == 0:
        panic_active = True

    if reset_button.value() == 0:
        panic_active = False
        print("RESET BUTTON PRESSED! Panic cleared.", end=' | ')

    print("PANIC:", "ACTIVE" if panic_active else "Not active", end='')

    print()  # New line
    time.sleep(1)
