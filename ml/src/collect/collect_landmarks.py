import cv2
import mediapipe as mp
import numpy as np
import os

# =========================
# CONFIG
# =========================
LABEL = "speak"          # change to: help / not_help
NUM_SAMPLES = 150       # recommended: 100–200
BASE_DIR = "data/raw"
SAVE_DIR = os.path.join(BASE_DIR, LABEL)
REQUIRED_HANDS = 1     
EXPECTED_LENGTH = REQUIRED_HANDS * 21 * 3   # 2 hands × 21 landmarks × 3 values
# =========================

# Create save directory safely (Windows-proof)
if not os.path.isdir(SAVE_DIR):
    os.makedirs(SAVE_DIR)

print(f"Saving samples to: {SAVE_DIR}")

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

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

    # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    landmarks = []

    # If hands detected, extract landmarks and draw them
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw hand landmarks on the frame
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )
            # Extract landmark coordinates
            for lm in hand_landmarks.landmark:
                landmarks.extend([lm.x, lm.y, lm.z])

        # Only save if BOTH hands are detected (required for "help" sign)
        if len(results.multi_hand_landmarks) == REQUIRED_HANDS and len(landmarks) == EXPECTED_LENGTH:
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
    if results.multi_hand_landmarks:
        num_hands = len(results.multi_hand_landmarks)
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
hands.close()

print("✅ Data collection complete.")
