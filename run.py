import os, sys, threading
from dotenv import load_dotenv
load_dotenv()

PORT = int(os.getenv("PORT", os.getenv("FLASK_PORT", 5000)))
ENABLE_SIMULATOR = os.getenv("ENABLE_SIMULATOR", "true").lower() in ("1", "true", "yes", "on")
SIMULATOR_INTERVAL = float(os.getenv("SIMULATOR_INTERVAL", "2.0"))

# Check optional packages
try:
    import ultralytics
    has_model = True
except ImportError:
    has_model = False
    print("[WARNING] ultralytics not installed. Detector will run in MOCK MODE.")

try:
    import eventlet
    import eventlet.wsgi
    eventlet.monkey_patch()
except ImportError:
    print("[ERROR] eventlet not installed. Run: pip install eventlet")
    sys.exit(1)

from backend.app import app, socketio


def start_simulator():
    if not ENABLE_SIMULATOR:
        return

    from backend.simulator import run_simulator

    server = os.getenv("SIMULATOR_SERVER", f"http://127.0.0.1:{PORT}")
    thread = threading.Thread(
        target=run_simulator,
        args=(server, SIMULATOR_INTERVAL),
        daemon=True,
    )
    thread.start()

print("=" * 52)
print("  DroneEye AI Dashboard")
print(f"  Dashboard:      http://localhost:{PORT}")
print(f"  Sensor POST:    POST http://localhost:{PORT}/api/data")
print(f"  Camera stream:  http://localhost:{PORT}/api/stream")
print(f"  Status:         http://localhost:{PORT}/api/status")
print(f"  Simulator:      {'ON' if ENABLE_SIMULATOR else 'OFF'}")
if not has_model:
    print("  Detector:       MOCK MODE (no model loaded)")
print("  Press Ctrl+C to stop")
print("=" * 52)

start_simulator()
socketio.run(app, host="0.0.0.0", port=PORT, debug=False)
