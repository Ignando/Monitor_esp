# boot.py -- run on boot-up
# boot.py — runs on boot before main.py
import esp
esp.osdebug(None)  # Disable debug logs

import uos
import machine

# Optionally set up serial REPL
# machine.UART(0, baudrate=115200)

# This is a good place to mount SD cards, set up logging, etc.
