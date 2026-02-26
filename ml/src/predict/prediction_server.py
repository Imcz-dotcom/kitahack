"""
SignSOS Prediction Server
Flask API wrapping MediaPipe + TensorFlow sign language recognition.

Endpoints:
  GET  /health          → health check
  POST /predict         → accepts base64 image, returns {label, confidence}
  POST /predict-stream  → same but for continuous frames
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import base64
import os
import urllib.request
import json
import zipfile

# ─── Paths ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
MODELS_DIR = os.path.join(ML_DIR, "models")

MODEL_PATH = os.path.join(MODELS_DIR, "hand_sign_model.keras")
HAND_LANDMARKER_MODEL = os.path.join(MODELS_DIR, "hand_landmarker.task")

# ─── Config ──────────────────────────────────────────────
EXPECTED_LEN = 63  # 1 hand × 21 landmarks × 3 coords

# TTS Server
TTS_URL = "http://127.0.0.1:3000/api/generate-audio"
USER_ID = "demo-user"
CONFIDENCE_THRESHOLD = 85.0

# ─── Download landmarker model if needed ─────────────────
if not os.path.exists(HAND_LANDMARKER_MODEL):
    print("📥 Downloading hand landmarker model...")
    os.makedirs(MODELS_DIR, exist_ok=True)
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, HAND_LANDMARKER_MODEL)
    print("✅ Download complete")

# ─── Load ML models ──────────────────────────────────────
print("Loading TensorFlow model...")
model = tf.keras.models.load_model(MODEL_PATH)

# Load class labels dynamically from model's embedded labels
labels_bytes = None
with zipfile.ZipFile(MODEL_PATH, mode="r") as zf:
    if "assets/hand_sign_labels.json" in zf.namelist():
        labels_bytes = zf.read("assets/hand_sign_labels.json")

if labels_bytes is not None:
    CLASSES = json.loads(labels_bytes.decode("utf-8"))
else:
    DATA_DIR = os.path.join(ML_DIR, "data", "raw")
    if not os.path.isdir(DATA_DIR):
        raise FileNotFoundError(
            "Embedded labels not found in model and fallback data/raw directory is missing. "
            "Retrain model to embed labels."
        )
    CLASSES = sorted([
        name for name in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, name))
    ])
    print("⚠️ Embedded labels not found in model; using fallback labels from data/raw.")

if not isinstance(CLASSES, list) or not CLASSES:
    raise ValueError("Invalid embedded labels format in model.")

model_output_classes = int(model.output_shape[-1])
if len(CLASSES) != model_output_classes:
    raise ValueError(
        f"Class mismatch: model expects {model_output_classes} classes, "
        f"but loaded labels has {len(CLASSES)} classes. Retrain model."
    )

print(f"✅ Model loaded — classes: {CLASSES}")

print("Loading MediaPipe Hand Landmarker...")
base_options = python.BaseOptions(model_asset_path=HAND_LANDMARKER_MODEL)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
detector = vision.HandLandmarker.create_from_options(options)
print("✅ Hand Landmarker ready")

# ─── Flask app ───────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allow Flutter app to call this API

last_posted_label = ""


def decode_image(base64_str: str) -> np.ndarray:
    """Decode a base64 image string to a numpy BGR image."""
    img_bytes = base64.b64decode(base64_str)
    np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img


def predict_sign(image: np.ndarray) -> dict:
    """Run MediaPipe + TF prediction on a BGR image frame."""
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    detection_result = detector.detect(mp_image)

    if not detection_result.hand_landmarks:
        return {"label": None, "confidence": 0.0, "hands_detected": 0}

    # Extract landmarks from one detected hand
    landmarks = []
    hand_landmarks = detection_result.hand_landmarks[0]
    for lm in hand_landmarks:
        landmarks.extend([lm.x, lm.y, lm.z])

    if len(landmarks) != EXPECTED_LEN:
        return {"label": None, "confidence": 0.0, "hands_detected": len(detection_result.hand_landmarks)}

    X = np.array(landmarks, dtype=np.float32).reshape(1, -1)
    preds = model.predict(X, verbose=0)[0]
    class_id = int(np.argmax(preds))
    label = CLASSES[class_id]
    confidence = float(preds[class_id] * 100)

    return {
        "label": label,
        "confidence": round(confidence, 1),
        "hands_detected": len(detection_result.hand_landmarks),
    }


def post_tts(text: str):
    """Forward recognized text to the TTS server."""
    payload = json.dumps({"text": text, "userId": USER_ID}).encode("utf-8")
    req = urllib.request.Request(
        TTS_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("audioUrl"), None
    except Exception as exc:
        return None, str(exc)


# ─── Routes ──────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "classes": CLASSES})


@app.route("/predict", methods=["POST"])
def predict():
    """Accept a base64 image and return sign language prediction."""
    global last_posted_label

    data = request.get_json(force=True)
    image_b64 = data.get("image")

    if not image_b64:
        return jsonify({"error": "No image provided"}), 400

    try:
        image = decode_image(image_b64)
    except Exception as e:
        return jsonify({"error": f"Failed to decode image: {str(e)}"}), 400

    result = predict_sign(image)

    # Auto-post to TTS if high confidence and new label
    if (
        result["label"]
        and result["confidence"] >= CONFIDENCE_THRESHOLD
        and result["label"] != last_posted_label
    ):
        audio_url, err = post_tts(result["label"])
        if not err:
            last_posted_label = result["label"]
            result["audio_url"] = audio_url
            result["tts_sent"] = True
            print(f"[TTS] {result['label']} → {audio_url}")
        else:
            result["tts_sent"] = False
            print(f"[TTS FAILED] {err}")

    return jsonify(result)


# ─── Main ────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🚀 SignSOS Prediction Server starting on http://0.0.0.0:5000")
    print(f"   Classes: {CLASSES}")
    print(f"   TTS endpoint: {TTS_URL}")
    print(f"   Confidence threshold: {CONFIDENCE_THRESHOLD}%\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
