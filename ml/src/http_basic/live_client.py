"""Live webcam client: detect hand landmarks and call HTTP prediction endpoint."""

import json
import time
from urllib import request, error

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

SERVER_URL = "http://127.0.0.1:8000/predict"
HAND_LANDMARKER_MODEL = "ml/models/hand_landmarker.task"
REQUEST_TIMEOUT_SEC = 10.0
REQUEST_INTERVAL_SEC = 0.25


def call_predict(landmarks: list[float]) -> tuple[str, float, str | None]:
    """Send landmarks to server and return (label, confidence, optional_error)."""
    payload = {"landmarks": landmarks}

    req = request.Request(
        SERVER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as response:
            body = json.loads(response.read().decode("utf-8"))
            label = str(body.get("label", "unknown"))
            confidence = float(body.get("confidence", 0.0))
            return label, confidence, None
    except error.HTTPError as exc:
        detail = "http_error"
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
            detail = str(error_body.get("error", detail))
        except (ValueError, json.JSONDecodeError):
            pass
        return "server_error", 0.0, f"HTTP {exc.code}: {detail}"
    except (error.URLError, TimeoutError) as exc:
        return "server_error", 0.0, f"Network error: {exc.reason if hasattr(exc, 'reason') else str(exc)}"
    except (ValueError, json.JSONDecodeError) as exc:
        return "server_error", 0.0, f"Parse error: {exc}"


def check_server_health() -> None:
    """Quick startup check so users can see server status immediately."""
    health_url = "http://127.0.0.1:8000/health"
    try:
        with request.urlopen(health_url, timeout=REQUEST_TIMEOUT_SEC) as response:
            body = json.loads(response.read().decode("utf-8"))
            print("Server health:", body)
    except Exception as exc:
        print("Could not reach server health endpoint:", exc)


def main() -> None:
    check_server_health()

    # Setup MediaPipe hand detector.
    base_options = python.BaseOptions(model_asset_path=HAND_LANDMARKER_MODEL)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open webcam")
        return

    print("Live client started. Press Q to quit.")
    last_request_time = 0.0
    last_label = "waiting"
    last_confidence = 0.0
    last_error: str | None = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        detection_result = detector.detect(mp_image)

        prediction_text = "No hands detected"
        color = (255, 255, 255)

        if detection_result.hand_landmarks:
            landmarks: list[float] = []

            # Draw landmarks and flatten coordinates.
            for hand_landmarks in detection_result.hand_landmarks:
                for landmark in hand_landmarks:
                    landmarks.extend([float(landmark.x), float(landmark.y), float(landmark.z)])
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    cv2.circle(frame, (x, y), 4, (0, 255, 0), -1)

            # Server supports 63 or 126 values.
            if len(landmarks) in (63, 126):
                now = time.monotonic()
                if now - last_request_time >= REQUEST_INTERVAL_SEC:
                    last_label, last_confidence, last_error = call_predict(landmarks)
                    last_request_time = now

                prediction_text = f"{last_label.upper()} ({last_confidence * 100:.1f}%)"

                if last_label == "server_error":
                    color = (0, 0, 255)
                elif last_confidence > 0.8:
                    color = (0, 255, 0)
                elif last_confidence > 0.6:
                    color = (0, 255, 255)
                else:
                    color = (0, 165, 255)
            else:
                prediction_text = f"Invalid landmarks: {len(landmarks)}"
                color = (0, 0, 255)

        cv2.putText(
            frame,
            prediction_text,
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            color,
            2,
        )
        cv2.putText(
            frame,
            "Press Q to quit",
            (10, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
        )

        if last_error:
            cv2.putText(
                frame,
                last_error[:80],
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
            )

        cv2.imshow("HTTP Live Hand Prediction", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
