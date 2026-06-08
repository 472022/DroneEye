import datetime
import math
import os
import random
import time

import requests


DEFAULT_SERVER = "http://localhost:5000"
DEFAULT_INTERVAL = 2.0


def make_sample(t):
    fault_active = (int(t) % 30) < 5

    if fault_active:
        v = 8.5 + random.uniform(-0.5, 0.5)
        i = 28.0 + random.uniform(-1.0, 1.0)
        temp = 78.0 + random.uniform(-2.0, 2.0)
        vib = 1
        det = {
            "label": "Insulator Crack Detected",
            "risk": "HIGH",
            "confidence": round(random.uniform(0.88, 0.97), 4),
        }
    else:
        v = 11.2 + math.sin(t / 10) * 0.4 + random.uniform(-0.1, 0.1)
        i = 18.5 + math.sin(t / 7) * 1.2 + random.uniform(-0.2, 0.2)
        temp = min(38.0 + t * 0.005 + random.uniform(-0.3, 0.3), 85.0)
        vib = 1 if random.random() < 0.05 else 0
        det = {"label": "No Fault Detected", "risk": "NONE", "confidence": 0.0}

    base_lat, base_lng = 18.5234, 73.8567
    lat = base_lat + math.sin(t / 20) * 0.0008
    lng = base_lng + math.cos(t / 20) * 0.0008

    payload = {
        "v": round(v, 3),
        "i": round(i, 3),
        "t": round(temp, 2),
        "vib": vib,
        "lat": round(lat, 6),
        "lng": round(lng, 6),
    }
    return payload, det, fault_active


def run_simulator(server=DEFAULT_SERVER, interval=DEFAULT_INTERVAL):
    t = 0
    print("DroneEye Simulator starting...")
    print(f"Sending to: {server}/api/data every {interval}s")
    print("Fault simulation: every 30 seconds for 5 seconds")

    while True:
        t += interval
        payload, det, fault_active = make_sample(t)

        try:
            requests.post(f"{server}/api/data", json=payload, timeout=3)
            requests.post(f"{server}/api/simulate_detection", json=det, timeout=3)
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            status = "FAULT!" if fault_active else "OK"
            print(
                f"[{ts}] {status:6s} "
                f"v={payload['v']:.2f}kV i={payload['i']:.2f}A "
                f"t={payload['t']:.1f}C vib={payload['vib']} risk={det['risk']}"
            )
        except requests.exceptions.RequestException:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] Cannot connect to {server} - is Flask running?")

        time.sleep(interval)


if __name__ == "__main__":
    server_url = os.getenv("SIMULATOR_SERVER", DEFAULT_SERVER)
    send_interval = float(os.getenv("SIMULATOR_INTERVAL", str(DEFAULT_INTERVAL)))
    print("Ctrl+C to stop\n")
    run_simulator(server_url, send_interval)
