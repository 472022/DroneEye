import datetime
import os
import random
import time

import cv2
import numpy as np

try:
    from ultralytics import YOLO

    ULTRALYTICS_OK = True
except ImportError:
    ULTRALYTICS_OK = False


RISK_HIGH = 0.75
RISK_MEDIUM = 0.45


class FaultDetector:
    def __init__(self, model_path=None, threshold=0.45):
        self.threshold = threshold
        self.mock_mode = True
        self.model = None

        if model_path and os.path.exists(model_path) and ULTRALYTICS_OK:
            try:
                self.model = YOLO(model_path)
                self.mock_mode = False
                print(f"[Detector] Model loaded: {model_path}")
            except Exception as e:
                print(f"[Detector] Failed to load model: {e}. Using MOCK MODE.")
        else:
            print("[Detector] No model found. Running in MOCK MODE.")

    def detect(self, frame_bytes: bytes) -> dict:
        ts = datetime.datetime.now().isoformat()

        if self.mock_mode:
            time.sleep(0.04)
            r = random.random()
            if r < 0.70:
                return {
                    "label": "No Fault Detected",
                    "risk": "NONE",
                    "confidence": 0.0,
                    "bbox": None,
                    "timestamp": ts,
                }
            if r < 0.90:
                conf = round(random.uniform(0.45, 0.74), 4)
                return {
                    "label": "Insulator Crack Detected",
                    "risk": "MEDIUM",
                    "confidence": conf,
                    "bbox": [0.3, 0.25, 0.65, 0.55],
                    "timestamp": ts,
                }

            conf = round(random.uniform(0.75, 0.97), 4)
            return {
                "label": "Insulator Crack Detected",
                "risk": "HIGH",
                "confidence": conf,
                "bbox": [0.28, 0.22, 0.68, 0.58],
                "timestamp": ts,
            }

        arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return {
                "label": "Decode Error",
                "risk": "NONE",
                "confidence": 0.0,
                "bbox": None,
                "timestamp": ts,
            }

        results = self.model(frame, verbose=False)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return {
                "label": "No Fault Detected",
                "risk": "NONE",
                "confidence": 0.0,
                "bbox": None,
                "timestamp": ts,
            }

        confs = boxes.conf.cpu().numpy()
        best = int(confs.argmax())
        conf = float(confs[best])
        if conf < self.threshold:
            return {
                "label": "No Fault Detected",
                "risk": "NONE",
                "confidence": conf,
                "bbox": None,
                "timestamp": ts,
            }

        cls = int(boxes.cls[best].cpu().numpy())
        label = self.model.names.get(cls, "Fault Detected")
        risk = "HIGH" if conf >= RISK_HIGH else "MEDIUM"
        xyxyn = boxes.xyxyn[best].cpu().numpy().tolist()

        return {
            "label": label,
            "risk": risk,
            "confidence": round(conf, 4),
            "bbox": xyxyn,
            "timestamp": ts,
        }

    def get_annotated_frame(self, frame_bytes: bytes, detection: dict) -> bytes:
        arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return frame_bytes

        h, w = frame.shape[:2]

        if detection["risk"] != "NONE" and detection.get("bbox"):
            x1, y1, x2, y2 = detection["bbox"]
            px1, py1, px2, py2 = int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)
            color = (0, 0, 220) if detection["risk"] == "HIGH" else (0, 140, 255)
            cv2.rectangle(frame, (px1, py1), (px2, py2), color, 3)

            label_text = f"{detection['label']} {detection['confidence'] * 100:.1f}%"
            (tw, th), _ = cv2.getTextSize(
                label_text,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                2,
            )
            cv2.rectangle(frame, (px1, py1 - th - 12), (px1 + tw + 8, py1), color, -1)
            cv2.putText(
                frame,
                label_text,
                (px1 + 4, py1 - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

        risk = detection["risk"]
        overlay_color = {
            "HIGH": (0, 0, 180),
            "MEDIUM": (0, 120, 210),
            "NONE": (0, 80, 30),
        }.get(risk, (0, 60, 30))
        cv2.rectangle(frame, (8, 8), (280, 52), overlay_color, -1)
        cv2.rectangle(frame, (8, 8), (280, 52), (80, 80, 80), 1)

        status_text = f"RISK: {risk}"
        conf_text = f"CONF: {detection['confidence'] * 100:.1f}%" if risk != "NONE" else "CONF: --"
        text_color = {
            "HIGH": (80, 80, 255),
            "MEDIUM": (80, 180, 255),
            "NONE": (80, 220, 80),
        }.get(risk, (180, 180, 180))

        cv2.putText(frame, status_text, (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, text_color, 2)
        cv2.putText(frame, conf_text, (160, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
        return buf.tobytes()


_instance = None


def get_detector():
    global _instance
    if _instance is None:
        path = os.getenv("MODEL_PATH", "backend/models/droneeye.pt")
        thr = float(os.getenv("DETECTION_CONFIDENCE_THRESHOLD", "0.45"))
        _instance = FaultDetector(path, thr)
    return _instance
