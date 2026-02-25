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
APPEND_CONFIDENCE_THRESHOLD = 90.0
STABLE_FRAMES_REQUIRED = 4
SEND_CONFIDENCE_THRESHOLD = 80.0
SEND_STABLE_FRAMES_REQUIRED = 2
APPEND_COOLDOWN_SECONDS = 0.8
SEND_TRIGGER_LABEL = "ok"
SEND_COOLDOWN_SECONDS = 2.0
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
        "Add/collect/train an 'ok' label to enable hands-free sending."
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


# Open webcam
cap = cv2.VideoCapture(0)
print("🎥 Camera started. Press Q to quit.")

frame_count = 0
typed_text = ""
last_predicted_label = ""
stable_count = 0
last_appended_label = ""
last_append_time = 0.0
last_send_time = 0.0
last_committed_label = ""
hand_left_since_commit = True

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    frame_count += 1
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    
    # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    
    # Detect hands
    detection_result = detector.detect(mp_image)
    hand_detected = bool(detection_result.hand_landmarks)

    if not hand_detected:
        hand_left_since_commit = True
        last_predicted_label = ""
        stable_count = 0

    landmarks = []
    prediction_text = "No hands detected"
    color = (255, 255, 255)  # White

    if hand_detected:
        # Extract landmarks from one detected hand
        hand_landmarks = detection_result.hand_landmarks[0]
        for landmark in hand_landmarks:
            landmarks.extend([landmark.x, landmark.y, landmark.z])

        # Make prediction if we have correct number of landmarks
        if len(landmarks) == EXPECTED_LEN:
            X = np.array(landmarks, dtype=np.float32).reshape(1, -1)
            
            preds = model.predict(X, verbose=0)[0]
            class_id = np.argmax(preds)
            label = CLASSES[class_id]
            confidence = preds[class_id] * 100

            prediction_text = f"{label.upper()} ({confidence:.1f}%)"

            if label == last_predicted_label:
                stable_count += 1
            else:
                last_predicted_label = label
                stable_count = 1

            now = time.time()

            # Show 'ok' sign to send built text automatically
            if (
                label == SEND_TRIGGER_LABEL
                and confidence >= SEND_CONFIDENCE_THRESHOLD
                and stable_count >= SEND_STABLE_FRAMES_REQUIRED
                and (hand_left_since_commit or label != last_committed_label)
                and (now - last_send_time) >= SEND_COOLDOWN_SECONDS
            ):
                text_to_send = typed_text.strip()
                if text_to_send:
                    audio_url, post_err = post_generate_audio(text_to_send, USER_ID)
                    if post_err:
                        print(f"[POST FAILED] text=\"{text_to_send}\" error={post_err}")
                    else:
                        print(f"[POST OK] text=\"{text_to_send}\" audioUrl={audio_url}")
                        typed_text = ""
                else:
                    print("[POST SKIPPED] Text buffer is empty.")

                last_send_time = now
                last_committed_label = label
                hand_left_since_commit = False

            if (
                label != SEND_TRIGGER_LABEL
                and
                confidence >= APPEND_CONFIDENCE_THRESHOLD
                and stable_count >= STABLE_FRAMES_REQUIRED
                and (hand_left_since_commit or label != last_committed_label)
                and (label != last_appended_label or (now - last_append_time) >= APPEND_COOLDOWN_SECONDS)
            ):
                typed_text += label
                last_appended_label = label
                last_append_time = now
                last_committed_label = label
                hand_left_since_commit = False
                print(f"[APPEND] '{label}' -> \"{typed_text}\"")

            # Color based on confidence
            if confidence > 80:
                color = (0, 255, 0)  # Green
            elif confidence > 60:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 165, 255)  # Orange

        # Draw hand landmarks
        for landmark in hand_landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

    # Display prediction
    cv2.putText(
        frame,
        prediction_text,
        (10, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        color,
        3
    )

    cv2.putText(
        frame,
        f"Text: {typed_text if typed_text else '-'}",
        (10, 95),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "Show 'ok' to send  Q=quit",
        (10, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1
    )

    # Show frame info
    cv2.putText(
        frame,
        f"Frame: {frame_count}",
        (10, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1
    )

    # Display frame
    cv2.imshow("Hand Sign Recognition", frame)

    key = cv2.waitKey(1) & 0xFF

    # Quit on 'q'
    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("\n✅ Application closed")
