from machine import I2S, Pin
import math
import time
import struct

# === I2S CONFIGURATION ===
SCK_PIN = 14
WS_PIN = 15
SD_PIN = 32
I2S_ID = 0
BUFFER_LEN = 1024

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
    return dbfs, dbspl

# === MAIN LOOP ===
print("Starting microphone monitor...")
while True:
    dbfs, dbspl = calculate_decibels()
    if dbfs is not None:
        print("Sound Level: {:.2f} dBFS ≈ {:.2f} dB SPL".format(dbfs, dbspl))
    else:
        print("No audio data received")
    time.sleep(1)
