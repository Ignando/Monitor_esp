
from app.ota_updater import OTAUpdater
import app.wifimgr as wifimgr

wlan = wifimgr.get_connection()
if wlan is None:
    print("Could not initialize the network connection.")
    while True:
        pass
print("Connected to WiFi:", wlan.ifconfig())

def download_and_install_update_if_available():
    o = OTAUpdater('https://github.com/Ignando/Monitor_esp',
                   main_dir='app', module='')  # note: app = folder name
    o.install_update_if_available()

download_and_install_update_if_available()

import app.main 