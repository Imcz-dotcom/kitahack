import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import json
import os
import zipfile
import time
import argparse
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS

# Resolve project paths from this file location so script works from any cwd.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
MODELS_DIR = os.path.join(ML_DIR, "models")
DATA_DIR = os.path.join(ML_DIR, "data", "raw")

# =========================
# CONFIG
# =========================
MODEL_PATH = os.path.join(MODELS_DIR, "hand_sign_model.keras")
EXPECTED_LEN = 63
HAND_LANDMARKER_MODEL = os.path.join(MODELS_DIR, "hand_landmarker.task")

# TTS Server config
GENERATE_AUDIO_URL = "http://127.0.0.1:3000/api/generate-audio"
USER_ID = "demo-user"
POST_CONFIDENCE_THRESHOLD = 95.0  # percentage
APPEND_CONFIDENCE_THRESHOLD = 60.0
STABLE_FRAMES_REQUIRED = 2
SEND_CONFIDENCE_THRESHOLD = 60.0
SEND_STABLE_FRAMES_REQUIRED = 1
APPEND_COOLDOWN_SECONDS = 0.8
WORD_SEPARATOR_LABEL = "ok"
SEND_TRIGGER_LABEL = "done"
SEPARATOR_CONFIDENCE_THRESHOLD = 35.0
SEPARATOR_STABLE_FRAMES_REQUIRED = 1
SEPARATOR_COOLDOWN_SECONDS = 0.6
SEND_COOLDOWN_SECONDS = 2.0
DONE_CONFIDENCE_THRESHOLD = 75.0
DONE_MIN_MARGIN = 12.0
# =========================

# Download MediaPipe hand landmarker model if not exists
if not os.path.exists(HAND_LANDMARKER_MODEL):
    print("📥 Downloading hand landmarker model...")
    os.makedirs(MODELS_DIR, exist_ok=True)
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, HAND_LANDMARKER_MODEL)
    print("✅ Download complete")

# Load trained model
model = tf.keras.models.load_model(MODEL_PATH)

labels_bytes = None
with zipfile.ZipFile(MODEL_PATH, mode="r") as zf:
    if "assets/hand_sign_labels.json" in zf.namelist():
        labels_bytes = zf.read("assets/hand_sign_labels.json")

if labels_bytes is not None:
    CLASSES = json.loads(labels_bytes.decode("utf-8"))
else:
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

print("✅ Model loaded")
print(f"📋 Classes: {CLASSES}")
if SEND_TRIGGER_LABEL not in CLASSES:
    print(
        f"⚠️ Send trigger '{SEND_TRIGGER_LABEL}' is not in classes. "
        "Add/collect/train a 'done' label to enable hands-free sending."
    )
else:
    print(f"✅ Send trigger active: {SEND_TRIGGER_LABEL}")

if WORD_SEPARATOR_LABEL and WORD_SEPARATOR_LABEL not in CLASSES:
    print(
        f"⚠️ Word separator '{WORD_SEPARATOR_LABEL}' is not in classes. "
        "Add/collect/train this label to insert spaces between words."
    )

# MediaPipe Hand Landmarker setup
base_options = python.BaseOptions(model_asset_path=HAND_LANDMARKER_MODEL)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.HandLandmarker.create_from_options(options)


class PredictionState:
    def __init__(self):
        self.typed_text = ""
        self.last_predicted_label = ""
        self.stable_count = 0
        self.last_appended_label = ""
        self.last_append_time = 0.0
        self.last_send_time = 0.0
        self.last_committed_label = ""
        self.hand_left_since_commit = True

    def update(self, label, confidence, hand_detected, margin=100.0):
        post_result = None

        if not hand_detected:
            self.hand_left_since_commit = True
            self.last_predicted_label = ""
            self.stable_count = 0
            return post_result

        if label == self.last_predicted_label:
            self.stable_count += 1
        else:
            self.last_predicted_label = label
            self.stable_count = 1

        now = time.time()

        if (
            label == SEND_TRIGGER_LABEL
            and confidence >= DONE_CONFIDENCE_THRESHOLD
            and margin >= DONE_MIN_MARGIN
            and self.stable_count >= SEND_STABLE_FRAMES_REQUIRED
            and (now - self.last_send_time) >= SEND_COOLDOWN_SECONDS
        ):
            text_to_send = self.typed_text.strip()
            if text_to_send:
                audio_url, post_err = post_generate_audio(text_to_send, USER_ID)
                if post_err:
                    print(f"[POST FAILED] text=\"{text_to_send}\" error={post_err}")
                    post_result = {
                        "action": "send",
                        "success": False,
                        "error": post_err,
                        "text": text_to_send,
                    }
                else:
                    print(f"[POST OK] text=\"{text_to_send}\" audioUrl={audio_url}")
                    post_result = {
                        "action": "send",
                        "success": True,
                        "audioUrl": audio_url,
                        "text": text_to_send,
                    }
                    self.typed_text = ""
            else:
                print("[POST SKIPPED] Text buffer is empty.")

            self.last_send_time = now
            self.last_committed_label = label
            self.hand_left_since_commit = False

        if (
            label == WORD_SEPARATOR_LABEL
            and confidence >= SEPARATOR_CONFIDENCE_THRESHOLD
            and self.stable_count >= SEPARATOR_STABLE_FRAMES_REQUIRED
            and self.typed_text
            and not self.typed_text.endswith(" ")
            and (now - self.last_append_time) >= SEPARATOR_COOLDOWN_SECONDS
        ):
            self.typed_text += " "
            self.last_appended_label = label
            self.last_append_time = now
            self.last_committed_label = label
            self.hand_left_since_commit = False
            print(f"[SPACE] '{label}' -> \"{self.typed_text}\"")
            post_result = {"action": "space", "text": self.typed_text}

        if (
            label != SEND_TRIGGER_LABEL
            and label != WORD_SEPARATOR_LABEL
            and confidence >= APPEND_CONFIDENCE_THRESHOLD
            and self.stable_count >= STABLE_FRAMES_REQUIRED
            and (self.hand_left_since_commit or label != self.last_committed_label)
            and (
                label != self.last_appended_label
                or (now - self.last_append_time) >= APPEND_COOLDOWN_SECONDS
            )
        ):
            self.typed_text += label
            self.last_appended_label = label
            self.last_append_time = now
            self.last_committed_label = label
            self.hand_left_since_commit = False
            print(f"[APPEND] '{label}' -> \"{self.typed_text}\"")

        return post_result


def predict_from_bgr(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    detection_result = detector.detect(mp_image)

    if not detection_result.hand_landmarks:
        return None, 0.0, 0, []

    hand_landmarks = detection_result.hand_landmarks[0]
    landmarks = []
    for landmark in hand_landmarks:
        landmarks.extend([landmark.x, landmark.y, landmark.z])

    if len(landmarks) != EXPECTED_LEN:
        return None, 0.0, len(detection_result.hand_landmarks), hand_landmarks

    X = np.array(landmarks, dtype=np.float32).reshape(1, -1)
    preds = model.predict(X, verbose=0)[0]
    sorted_idx = np.argsort(preds)[::-1]
    class_id = int(sorted_idx[0])
    second_id = int(sorted_idx[1]) if len(sorted_idx) > 1 else class_id
    label = CLASSES[class_id]
    second_label = CLASSES[second_id]
    confidence = float(preds[class_id] * 100)
    second_confidence = float(preds[second_id] * 100)
    margin = confidence - second_confidence
    return (
        label,
        confidence,
        len(detection_result.hand_landmarks),
        hand_landmarks,
        second_label,
        second_confidence,
        margin,
    )


def decode_base64_image(image_b64):
    image_bytes = base64.b64decode(image_b64)
    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode image")
    return frame

def post_generate_audio(text, user_id):
    """POST recognized text to /api/generate-audio. Returns (audioUrl, error)."""
    payload = json.dumps({"text": text, "userId": user_id}).encode("utf-8")
    req = urllib.request.Request(
        GENERATE_AUDIO_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("audioUrl"), None
    except Exception as exc:
        return None, str(exc)


def run_webcam_mode():
    state = PredictionState()

    cap = None
    for cam_index in [0, 1, 2]:
        test_cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if test_cap.isOpened():
            cap = test_cap
            print(f"🎥 Camera started on index {cam_index}. Press Q to quit.")
            break
        test_cap.release()

    if cap is None:
        raise RuntimeError("No available camera found. Close apps using camera and try again.")

    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        frame_count += 1
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        (
            label,
            confidence,
            hands_detected,
            hand_landmarks,
            second_label,
            second_confidence,
            margin,
        ) = predict_from_bgr(frame)
        hand_detected = hands_detected > 0

        prediction_text = "No hands detected"
        color = (255, 255, 255)

        if hand_detected and label is not None:
            if (
                label == SEND_TRIGGER_LABEL
                and second_label == WORD_SEPARATOR_LABEL
                and margin < DONE_MIN_MARGIN
            ):
                label = WORD_SEPARATOR_LABEL
                confidence = second_confidence
                margin = 100.0

            prediction_text = f"{label.upper()} ({confidence:.1f}%)"
            state.update(label, confidence, True, margin=margin)

            if confidence > 80:
                color = (0, 255, 0)
            elif confidence > 60:
                color = (0, 255, 255)
            else:
                color = (0, 165, 255)
        else:
            state.update("", 0.0, False)

        for landmark in hand_landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        cv2.putText(frame, prediction_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
        cv2.putText(
            frame,
            f"Text: {state.typed_text if state.typed_text else '-'}",
            (10, 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            "Show 'ok' for space, 'done' to send  Q=quit",
            (10, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"Frame: {frame_count}",
            (10, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        cv2.imshow("Hand Sign Recognition", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Application closed")


def run_server_mode(host, port):
    app = Flask(__name__)
    CORS(app)
    state = PredictionState()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "classes": CLASSES})

    @app.route("/predict", methods=["POST"])
    def predict():
        payload = request.get_json(force=True) or {}
        image_b64 = payload.get("image")

        if not image_b64:
            return jsonify({"error": "No image provided"}), 400

        try:
            frame = decode_base64_image(image_b64)
        except Exception as exc:
            return jsonify({"error": f"Failed to decode image: {exc}"}), 400

        (
            label,
            confidence,
            hands_detected,
            _,
            second_label,
            second_confidence,
            margin,
        ) = predict_from_bgr(frame)
        hand_detected = hands_detected > 0

        if (
            hand_detected
            and label == SEND_TRIGGER_LABEL
            and second_label == WORD_SEPARATOR_LABEL
            and margin < DONE_MIN_MARGIN
        ):
            label = WORD_SEPARATOR_LABEL
            confidence = second_confidence
            margin = 100.0

        response = {
            "label": label or "",
            "confidence": round(confidence, 1),
            "hands_detected": hands_detected,
            "text_buffer": state.typed_text,
        }

        if hand_detected and label is not None:
            post_result = state.update(label, confidence, True, margin=margin)
            response["text_buffer"] = state.typed_text
            if post_result is not None:
                response["post_result"] = post_result
        else:
            state.update("", 0.0, False)

        return jsonify(response)

    @app.route("/clear-buffer", methods=["POST"])
    def clear_buffer():
        state.typed_text = ""
        state.last_predicted_label = ""
        state.stable_count = 0
        state.last_appended_label = ""
        state.last_append_time = 0.0
        state.last_committed_label = ""
        state.hand_left_since_commit = True
        return jsonify({"success": True, "text_buffer": state.typed_text})

    print(f"🚀 live_predict server mode on http://{host}:{port}")
    print(f"📋 Classes: {CLASSES}")
    print(f"🔗 TTS endpoint: {GENERATE_AUDIO_URL}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Run as HTTP API for Flutter web camera frames")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    if args.server:
        run_server_mode(args.host, args.port)
    else:
        run_webcam_mode()
