from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os, json, time, threading, datetime
from dotenv import load_dotenv
import cv2, numpy as np
load_dotenv()

try:
    from backend.detector import get_detector
    DETECTOR_AVAILABLE = True
except Exception:
    DETECTOR_AVAILABLE = False

app = Flask(__name__, static_folder='../dashboard', static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

# --- Global state -----------------------------------------------------------
latest_data = {
    "voltage": 0.0, "current": 0.0, "temperature": 0.0, "vibration": False,
    "lat": 0.0, "lng": 0.0, "timestamp": "", "connected": False,
}
latest_detection = {"label": "No Detection", "risk": "NONE", "confidence": 0.0, "timestamp": ""}
latest_frame = None          # bytes of latest annotated JPEG
data_lock = threading.Lock()
last_data_time = 0
alerts = []
start_time = time.time()
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN_SECONDS", 10))
last_alert_time = 0

# Load persisted alerts on startup
_alerts_path = os.path.join(os.path.dirname(__file__), "alerts", "alerts.json")
if os.path.exists(_alerts_path):
    try:
        with open(_alerts_path) as _f:
            alerts = json.load(_f)
    except Exception:
        alerts = []


# --- Routes -----------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory('../dashboard', 'index.html')


@app.route("/api/data", methods=["POST"])
def post_data():
    global last_data_time
    body = request.get_json(force=True, silent=True) or {}
    payload = {
        "voltage":     float(body.get("v", 0)),
        "current":     float(body.get("i", 0)),
        "temperature": float(body.get("t", 0)),
        "vibration":   bool(body.get("vib", 0)),
        "lat":         float(body.get("lat", 0)),
        "lng":         float(body.get("lng", 0)),
        "timestamp":   datetime.datetime.now().isoformat(),
        "connected":   True,
    }
    with data_lock:
        latest_data.update(payload)
    last_data_time = time.time()
    socketio.emit("sensor_update", latest_data)
    return jsonify({"status": "ok"})


@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(latest_data)


@app.route("/api/detection", methods=["GET"])
def get_detection():
    return jsonify(latest_detection)


@app.route("/api/simulate_detection", methods=["POST"])
def simulate_detection():
    global latest_detection
    body = request.get_json(force=True, silent=True) or {}
    with data_lock:
        latest_detection = {
            "label":      body.get("label", "Unknown"),
            "risk":       body.get("risk", "NONE"),
            "confidence": float(body.get("confidence", 0.0)),
            "timestamp":  datetime.datetime.now().isoformat(),
        }
    socketio.emit("detection_update", latest_detection)
    if latest_detection["risk"] in ("HIGH", "MEDIUM"):
        _check_alert()
    return jsonify({"status": "ok"})


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    return jsonify(alerts[:50])


@app.route("/api/alerts/clear", methods=["POST"])
def clear_alerts():
    alerts.clear()
    try:
        os.makedirs(os.path.dirname(_alerts_path), exist_ok=True)
        with open(_alerts_path, "w") as f:
            json.dump([], f)
    except Exception:
        pass
    return jsonify({"status": "cleared"})


@app.route("/api/stream")
def stream():
    def gen_frames():
        while True:
            frame = latest_frame
            if frame is not None:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            else:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + _offline_frame() + b"\r\n"
            time.sleep(0.1)
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/frame")
def frame():
    data = latest_frame if latest_frame is not None else _offline_frame()
    return Response(data, mimetype="image/jpeg")


@app.route("/api/status")
def status():
    esp32_connected = last_data_time > 0 and (time.time() - last_data_time) < 10
    return jsonify({
        "esp32_connected":  esp32_connected,
        "camera_online":    latest_frame is not None,
        "detector_loaded":  DETECTOR_AVAILABLE,
        "mock_mode":        not DETECTOR_AVAILABLE,
        "uptime_seconds":   int(time.time() - start_time),
        "alert_count":      len(alerts),
        "esp32_ip":         os.getenv("ESP32_IP", "not set"),
        "cam_ip":           os.getenv("ESP32_CAM_IP", "not set"),
    })


@app.route("/api/config", methods=["GET", "POST"])
def config():
    global ALERT_COOLDOWN

    if request.method == "GET":
        return jsonify(_current_config())

    body = request.get_json(force=True, silent=True) or {}
    old_cam_ip = os.getenv("ESP32_CAM_IP", "")

    if "esp32_ip" in body:
        os.environ["ESP32_IP"] = str(body["esp32_ip"])
    if "cam_ip" in body:
        os.environ["ESP32_CAM_IP"] = str(body["cam_ip"])
    if "threshold" in body:
        os.environ["DETECTION_CONFIDENCE_THRESHOLD"] = str(body["threshold"])
    if "cooldown" in body:
        ALERT_COOLDOWN = int(body["cooldown"])
        os.environ["ALERT_COOLDOWN_SECONDS"] = str(ALERT_COOLDOWN)

    new_cam_ip = os.getenv("ESP32_CAM_IP", "")
    if new_cam_ip != old_cam_ip:
        print(f"CAM IP updated to {new_cam_ip} — restart cam thread")

    return jsonify({"status": "applied", "values": _current_config()})


# --- SocketIO ---------------------------------------------------------------

@socketio.on("connect")
def handle_connect():
    emit("sensor_update", latest_data)
    emit("detection_update", latest_detection)


# --- Helpers ----------------------------------------------------------------

def _current_config():
    return {
        "esp32_ip": os.getenv("ESP32_IP", ""),
        "cam_ip": os.getenv("ESP32_CAM_IP", ""),
        "threshold": float(os.getenv("DETECTION_CONFIDENCE_THRESHOLD", "0.45")),
        "cooldown": int(os.getenv("ALERT_COOLDOWN_SECONDS", "10")),
    }


def _offline_frame():
    img = np.zeros((480, 640, 3), np.uint8)
    img[:] = (15, 25, 40)
    cv2.putText(img, "CAMERA OFFLINE", (155, 215),
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (60, 80, 100), 2)
    cv2.putText(img, "Check ESP32_CAM_IP in .env", (110, 265),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (45, 65, 85), 1)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def _check_alert():
    global last_alert_time
    if time.time() - last_alert_time < ALERT_COOLDOWN:
        return
    if latest_detection["risk"] not in ("HIGH", "MEDIUM"):
        return
    last_alert_time = time.time()
    alert = {
        "id":          len(alerts) + 1,
        "timestamp":   datetime.datetime.now().isoformat(),
        "risk":        latest_detection["risk"],
        "label":       latest_detection["label"],
        "confidence":  latest_detection["confidence"],
        "lat":         latest_data["lat"],
        "lng":         latest_data["lng"],
        "voltage":     latest_data["voltage"],
        "temperature": latest_data["temperature"],
    }
    alerts.insert(0, alert)
    if len(alerts) > 200:
        alerts.pop()
    try:
        os.makedirs(os.path.dirname(_alerts_path), exist_ok=True)
        with open(_alerts_path, "w") as f:
            json.dump(alerts, f)
    except Exception:
        pass
    socketio.emit("new_alert", alert)


# --- Background threads -----------------------------------------------------

def _connection_watchdog():
    while True:
        time.sleep(5)
        if last_data_time > 0 and (time.time() - last_data_time) > 10:
            with data_lock:
                latest_data["connected"] = False
            socketio.emit("connection_lost", {})


def _cam_thread():
    cam_ip = os.getenv("ESP32_CAM_IP", "")
    if not cam_ip:
        return
    url = f"http://{cam_ip}/stream"
    while True:
        try:
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                raise Exception("Cannot open stream")
            while True:
                ret, frame = cap.read()
                if not ret:
                    raise Exception("Frame read failed")
                _, buf = cv2.imencode(".jpg", frame)
                frame_bytes = buf.tobytes()
                global latest_frame, latest_detection
                if DETECTOR_AVAILABLE:
                    det = get_detector().detect(frame_bytes)
                    ann_bytes = get_detector().get_annotated_frame(frame_bytes, det)
                    with data_lock:
                        latest_frame = ann_bytes
                        latest_detection = det
                    socketio.emit("detection_update", det)
                    _check_alert()
                else:
                    with data_lock:
                        latest_frame = frame_bytes
        except Exception as e:
            print(f"[CAM] Error: {e}. Retrying in 3s...")
            time.sleep(3)


threading.Thread(target=_connection_watchdog, daemon=True).start()
threading.Thread(target=_cam_thread, daemon=True).start()
