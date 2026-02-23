import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import os
import urllib.request

# =========================
# CONFIG
# =========================
LABEL = "hello"          # change to: help / not_help
NUM_SAMPLES = 150       # recommended: 100–200
BASE_DIR = "data/raw"
SAVE_DIR = os.path.join(BASE_DIR, LABEL)
REQUIRED_HANDS = 1     
EXPECTED_LENGTH = REQUIRED_HANDS * 21 * 3
HAND_LANDMARKER_MODEL = "models/hand_landmarker.task"
# =========================

# Create save directory safely (Windows-proof)
if not os.path.isdir(SAVE_DIR):
    os.makedirs(SAVE_DIR)

print(f"Saving samples to: {SAVE_DIR}")

# Download MediaPipe hand landmarker model if not exists
if not os.path.exists(HAND_LANDMARKER_MODEL):
    print("📥 Downloading hand landmarker model...")
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, HAND_LANDMARKER_MODEL)
    print("✅ Download complete")

# Initialize MediaPipe Hand Landmarker
base_options = python.BaseOptions(model_asset_path=HAND_LANDMARKER_MODEL)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7
)
detector = vision.HandLandmarker.create_from_options(options)

# Open webcam
cap = cv2.VideoCapture(0)
count = 0

print(f"Collecting '{LABEL}' samples...")

while cap.isOpened() and count < NUM_SAMPLES:
    ret, frame = cap.read()
    if not ret:
        break

    # Mirror image for natural interaction
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape

    # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    
    # Detect hands
    detection_result = detector.detect(mp_image)

    landmarks = []

    # If hands detected, extract landmarks and draw them
    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            # Draw hand landmarks on the frame
            for landmark in hand_landmarks:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
            
            # Extract landmark coordinates
            for lm in hand_landmarks:
                landmarks.extend([lm.x, lm.y, lm.z])

        # Only save if required number of hands are detected
        if len(detection_result.hand_landmarks) == REQUIRED_HANDS and len(landmarks) == EXPECTED_LENGTH:
            np.save(
                os.path.join(SAVE_DIR, f"{count}.npy"),
                np.array(landmarks, dtype=np.float32)
            )
            count += 1
            print(f"Saved {count}/{NUM_SAMPLES}")

    # Add text overlay with instructions and progress
    cv2.putText(frame, f"Collecting: {LABEL}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, f"Progress: {count}/{NUM_SAMPLES}", (10, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, "Press 'Q' to quit", (10, 110), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Show status based on hand detection
    if detection_result.hand_landmarks:
        num_hands = len(detection_result.hand_landmarks)
        cv2.putText(frame, f"Hands detected: {num_hands}", (10, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "No hands detected", (10, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Show camera window
    cv2.imshow("Collecting Hand Sign Data", frame)

    # Press Q to quit early
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()

print("✅ Data collection complete.")
