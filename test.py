from machine import Pin, ADC
import time

# === SETUP YOUR PINS ===
# Change these as needed
PANIC_BUTTON_PIN = 12
GAS_SENSOR_PIN = 34
PIR_SENSOR_PIN = 32

# === INIT SENSORS ===
panic_button = Pin(PANIC_BUTTON_PIN, Pin.IN, Pin.PULL_UP)  # Button, LOW when pressed
gas_sensor = ADC(Pin(GAS_SENSOR_PIN))
gas_sensor.atten(ADC.ATTN_11DB)  # 0-3.3V range
pir_sensor = Pin(PIR_SENSOR_PIN, Pin.IN)

print("=== Sensor Test Started ===")

while True:
    panic_state = 'PRESSED' if panic_button.value() == 0 else 'NOT PRESSED'
    gas_level = gas_sensor.read()  # 0-4095
    pir_state = 'MOTION' if pir_sensor.value() == 1 else 'NO MOTION'
    
    print("Panic Button:", panic_state, "| Gas Level:", gas_level, "| PIR:", pir_state)
    
    time.sleep(1)
