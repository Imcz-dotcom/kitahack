# HTTP Basic Inference (Detailed Guide)

This folder implements a simple and practical architecture:

1. Train your model once and save it to disk.
2. Start a backend server that loads the model into memory.
3. Use a webcam client to detect hand landmarks and request predictions over HTTP.

This keeps prediction logic in one place (the backend), so you can later replace the client with any app (mobile, web, another Python service) that sends the same request format.

---

## Quick summary

- Endpoint: `POST /predict`
- Health check: `GET /health`
- Main server: `server.py`
- Main client: `live_client.py`

---

## Folder contents

- `server.py`
  - Loads `ml/models/hand_sign_model.keras` once at startup.
  - Accepts landmarks JSON via HTTP.
  - Runs TensorFlow inference and returns class scores.

- `live_client.py`
  - Opens webcam.
  - Uses MediaPipe to detect hand landmarks.
  - Draws landmarks on frame.
  - Sends landmarks to server and overlays prediction text.

---

## End-to-end data flow

1. Camera frame is read by `live_client.py`.
2. MediaPipe extracts hand landmarks (`x, y, z` triples).
3. Landmarks are flattened to a numeric list.
4. Client sends `POST /predict` with JSON body.
5. `server.py` validates input and pads 63-length input to 126.
6. Server runs `model.predict(...)`.
7. Server returns `label`, `confidence`, and `scores`.
8. Client overlays result text on the webcam window.

---

## Prerequisites

- Python 3.8+
- Project dependencies installed:

```bash
pip install -r ml/requirements.txt
```

Required model files:

- `ml/models/hand_sign_model.keras` (trained classifier)
- `ml/models/hand_landmarker.task` (MediaPipe hand detector model)

---

## Run guide (recommended order)

### 1) Train and save your classifier model

From project root:

```bash
python ml/src/train/train_model.py
```

Expected artifact:

```text
ml/models/hand_sign_model.keras
```

### 2) Start inference server

```bash
python ml/src/http_basic/server.py
```

Expected startup logs (example):

```text
✅ Model loaded from: .../ml/models/hand_sign_model.keras
📋 Classes: ['help', 'cannot', 'speak', 'hello']
Server running at http://127.0.0.1:8000
POST to /predict with {"landmarks": [...]} or GET /health
```

### 3) Start live webcam client in a new terminal

```bash
python ml/src/http_basic/live_client.py
```

What you should see:

- A webcam window with landmark dots on your hand.
- Prediction label and confidence on top-left.
- Optional red error text below prediction if request fails.

Press `Q` to quit.

---

## API contract

### Health endpoint

- Method: `GET`
- URL: `http://127.0.0.1:8000/health`
- Purpose: quick server + model-load status check.

Example response:

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_path": ".../ml/models/hand_sign_model.keras"
}
```

### Prediction endpoint

- Method: `POST`
- URL: `http://127.0.0.1:8000/predict`
- Header: `Content-Type: application/json`

Request body:

```json
{
  "landmarks": [0.0, 0.1, 0.2]
}
```

Validation rules:

- `landmarks` must be a JSON array.
- Every value must be numeric.
- Allowed lengths:
  - `63` (one hand) → auto padded to `126`
  - `126` (full expected length)

Success response (example):

```json
{
  "label": "hello",
  "confidence": 0.57,
  "scores": {
    "help": 0.18,
    "cannot": 0.13,
    "speak": 0.10,
    "hello": 0.57
  }
}
```

Error responses:

- `400` invalid JSON, non-numeric data, or wrong length
- `404` wrong path
- `503` model not loaded

---

## Code walkthrough

## `server.py`

### Configuration constants

- `HOST`, `PORT`: bind address.
- `CLASSES`: output labels used to map logits/probabilities to names.
- `EXPECTED_LEN = 126`: model input feature length.
- `MODEL_PATH`: absolute path to trained `.keras` model.
- `MODEL`: global in-memory model object.

### `_load_model()`

- Checks model file existence.
- Loads TensorFlow model once.
- Returns `None` if missing so API can report `503` clearly.

### `SimpleHandler._send_json()`

- Shared utility to return JSON with status code and headers.

### `SimpleHandler.do_POST()`

Main inference path:

1. Ensure path is exactly `/predict`.
2. Ensure model is loaded.
3. Parse JSON body safely.
4. Validate `landmarks` type and values.
5. Pad 63-length input to 126.
6. Reject any other length.
7. Convert to `np.float32`, shape `(1, -1)`.
8. Run prediction and return structured JSON.

### `SimpleHandler.do_GET()`

- Returns health status only for `/health`.

### Entrypoint block

- Loads model.
- Starts `HTTPServer`.
- Runs forever.

## `live_client.py`

### Configuration constants

- `SERVER_URL`: `http://127.0.0.1:8000/predict`
- `HAND_LANDMARKER_MODEL`: MediaPipe model path
- `REQUEST_TIMEOUT_SEC`: HTTP timeout per request
- `REQUEST_INTERVAL_SEC`: throttle interval between requests

### `call_predict(landmarks)`

- Builds JSON payload.
- Sends POST request.
- Parses successful response to `(label, confidence)`.
- Converts server/network/parse failures to readable error text.

### `check_server_health()`

- Runs one startup check to show backend status before camera loop starts.

### `main()`

1. Initializes MediaPipe hand detector.
2. Opens webcam and frame loop.
3. Detects landmarks each frame.
4. Draws points and sends periodic HTTP prediction requests.
5. Overlays result and error text.
6. Stops on `Q`.

---

## Tuning options you can change later

In `live_client.py`:

- `REQUEST_INTERVAL_SEC`
  - Lower = faster updates, more server load.
  - Higher = less load, slower updates.

- `REQUEST_TIMEOUT_SEC`
  - Increase if your machine/server is slow.

In MediaPipe options:

- `min_hand_detection_confidence`
- `min_hand_presence_confidence`
- `min_tracking_confidence`

Increasing these can reduce false detections but may miss weak/fast hand poses.

---

## Troubleshooting

### `HTTP 404 Not Found`

- Ensure client URL is exactly `/predict`.
- Restart server to ensure latest code is running.

### `503 Model is not loaded`

- Train model first:

```bash
python ml/src/train/train_model.py
```

- Confirm file exists: `ml/models/hand_sign_model.keras`
- Restart server after training.

### `Invalid landmark length`

- Server accepts only 63 or 126 values.
- If custom client is used, confirm its feature vector shape.

### Webcam does not open

- Close apps using camera (Zoom/Meet/Teams).
- Verify webcam device permissions in Windows settings.

### Server timeout / network error

- Confirm server terminal is still running.
- Check health endpoint:

```text
http://127.0.0.1:8000/health
```

---

## Operational notes

- Server does not retrain model.
- If you retrain, restart server to load new weights.
- Keep backend as prediction source of truth; clients only capture/input data.
