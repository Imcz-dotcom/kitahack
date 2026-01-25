import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os

# =========================
# CONFIG
# =========================
MODEL_PATH = "models/hand_sign_model.keras"
CLASSES = ["help", "cannot", "speak"]
EXPECTED_LEN = 126
HAND_LANDMARKER_MODEL = "hand_landmarker.task"
# =========================

# Download MediaPipe hand landmarker model if not exists
if not os.path.exists(HAND_LANDMARKER_MODEL):
    print("📥 Downloading hand landmarker model...")
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, HAND_LANDMARKER_MODEL)
    print("✅ Download complete")

# Load trained model
model = tf.keras.models.load_model(MODEL_PATH)
print("✅ Model loaded")
print(f"📋 Classes: {CLASSES}")

# MediaPipe Hand Landmarker setup
base_options = python.BaseOptions(model_asset_path=HAND_LANDMARKER_MODEL)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.HandLandmarker.create_from_options(options)

# Open webcam
cap = cv2.VideoCapture(0)
print("🎥 Camera started. Press Q to quit.")

frame_count = 0

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

    landmarks = []
    prediction_text = "No hands detected"
    color = (255, 255, 255)  # White

    if detection_result.hand_landmarks:
        # Extract landmarks from all detected hands
        for hand_landmarks in detection_result.hand_landmarks:
            for landmark in hand_landmarks:
                landmarks.extend([landmark.x, landmark.y, landmark.z])

        # Pad to 126 if only one hand
        if len(landmarks) == 63:
            landmarks.extend([0.0] * 63)

        # Make prediction if we have correct number of landmarks
        if len(landmarks) == EXPECTED_LEN:
            X = np.array(landmarks, dtype=np.float32).reshape(1, -1)
            
            preds = model.predict(X, verbose=0)[0]
            class_id = np.argmax(preds)
            label = CLASSES[class_id]
            confidence = preds[class_id] * 100

            prediction_text = f"{label.upper()} ({confidence:.1f}%)"
            
            # Color based on confidence
            if confidence > 80:
                color = (0, 255, 0)  # Green
            elif confidence > 60:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 165, 255)  # Orange

        # Draw hand landmarks
        for hand_landmarks in detection_result.hand_landmarks:
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

    # Quit on 'q'
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("\n✅ Application closed")
