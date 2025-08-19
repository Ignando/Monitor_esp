# /main.py  (top-level boot file)

import time
import app.wifimgr as wifimgr
from app.ota_updater import OTAUpdater

def wait_for_wifi(max_wait_s=None, retry_pause_s=2):
    """
    Keep trying the first saved profile until WiFi connects.
    - max_wait_s=None -> wait forever
    - returns wlan_sta if connected, else None (on timeout or bad password)
    """
    # Already connected?
    if wifimgr.wlan_sta.isconnected():
        return wifimgr.wlan_sta

    # Get first saved SSID/password from wifi.dat
    try:
        profiles = wifimgr.read_profiles()  # {ssid: password}
        ssid, password = next(iter(profiles.items()))
    except Exception as e:
        print("No WiFi profiles found:", e)
        return None

    start = time.ticks_ms()
    while True:
        ok = wifimgr.do_connect(ssid, password)  # your existing single-attempt (~20s)
        if ok and wifimgr.wlan_sta.isconnected():
            return wifimgr.wlan_sta

        # Stop on unrecoverable: wrong password
        st = wifimgr.wlan_sta.status()  # -3 = bad password
        if st == -3:
            print("Wrong password for '%s'; stop retrying." % ssid)
            # Optional AP fallback:
            # print("Starting AP portal for reconfiguration...")
            # wifimgr.start()
            return None

        # Timeout?
        if max_wait_s is not None:
            if time.ticks_diff(time.ticks_ms(), start) > max_wait_s * 1000:
                print("WiFi wait timed out after %ds" % max_wait_s)
                # Optional AP fallback:
                # print("Starting AP portal...")
                # wifimgr.start()
                return None

        time.sleep(retry_pause_s)

# ---- Boot sequence ----
print("Booting...")
wlan = wait_for_wifi(max_wait_s=None)  # None = wait forever for router to come up
if not (wlan and wlan.isconnected()):
    print("WiFi not connected; stopping boot.")
    raise SystemExit

print("Connected to WiFi:", wlan.ifconfig())

# (Optional but recommended) sync time for TLS
try:
    import ntptime; ntptime.settime()
except Exception as e:
    print("NTP sync failed:", e)

# OTA check
o = OTAUpdater('https://github.com/Ignando/Monitor_esp',
               main_dir='app', module='', secrets_file='config.py')
o.install_update_if_available()

# Hand over to your app
import app.main
