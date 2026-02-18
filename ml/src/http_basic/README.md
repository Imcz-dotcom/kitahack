# HTTP Basic Inference (Full Guide)

This folder gives you a complete **train once, serve many times** flow:

1. Train model and save it to disk.
2. Start HTTP server (model is loaded once into memory).
3. Send requests from script/webcam/other app to get predictions.

---

## Folder contents

- `server.py` → backend HTTP server that performs model inference
- `client.py` → simple request example (sends dummy landmarks)
- `live_client.py` → webcam app (detects hand landmarks, sends to server, shows prediction)

---

## Prerequisites

- Python 3.8+
- Dependencies installed (from `ml/requirements.txt`)

From project root:

```bash
pip install -r ml/requirements.txt
```

---

## End-to-end quick start

### Step 1) Train model

```bash
python ml/src/train/train_model.py
```

Expected artifact:

```text
ml/models/hand_sign_model.keras
```

### Step 2) Start server

```bash
python ml/src/http_basic/server.py
```

Expected startup logs (example):

```text
✅ Model loaded from: .../ml/models/hand_sign_model.keras
📋 Classes: ['help', 'cannot', 'speak', 'hello']
Server running at http://127.0.0.1:8000
POST to /predict (or /endpoint) with {"landmarks": [...]} or GET /health
```

### Step 3A) Test with simple client

```bash
python ml/src/http_basic/client.py
```

### Step 3B) Test with webcam live client

```bash
python ml/src/http_basic/live_client.py
```

Press `Q` to quit webcam window.

---

## API reference

### Health check

- Method: `GET`
- URL: `http://127.0.0.1:8000/health`
- Purpose: verify server is alive and whether model is loaded

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
- URL (preferred): `http://127.0.0.1:8000/predict`
- Compatibility URL: `http://127.0.0.1:8000/endpoint`
- Header: `Content-Type: application/json`

Request body:

```json
{
  "landmarks": [0.0, 0.1, 0.2]
}
```

Input rules:

- `landmarks` must be a list of numbers
- Length can be:
  - `63` (one hand) → server auto-pads to `126`
  - `126` (full expected input)

Success response:

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

Common error responses:

- `400` invalid JSON or wrong landmark length/type
- `404` wrong route
- `503` model not loaded (usually missing model file)

---

## File-by-file explanation

## `server.py`

This is your inference backend.

### Configuration section

- `HOST` / `PORT`: server bind address (`127.0.0.1:8000`)
- `CLASSES`: fixed class labels returned in output
- `EXPECTED_LEN = 126`: model input size
- `MODEL_PATH`: absolute path to `ml/models/hand_sign_model.keras`
- `MODEL = None`: global variable to keep loaded model in memory

### `_load_model()`

- Checks if model file exists.
- If missing: prints warning and returns `None`.
- If found: loads TensorFlow model and prints loaded classes.

### `SimpleHandler._send_json()`

- Utility for consistent JSON responses.
- Sets status code, headers, and writes JSON bytes to client.

### `SimpleHandler.do_POST()`

Main prediction logic:

1. Accept route only if path is `/predict` or `/endpoint`.
2. Reject if model not loaded (`503`).
3. Parse incoming JSON body.
4. Validate `landmarks` format and numeric values.
5. Auto-pad if length is `63`.
6. Reject if final length is not `126`.
7. Run `MODEL.predict(...)`.
8. Return `label`, `confidence`, and per-class `scores`.

### `SimpleHandler.do_GET()`

- Supports only `/health` route.
- Returns model status + model path.

### `if __name__ == "__main__":`

- Loads model once.
- Starts HTTP server.
- Keeps server running with `serve_forever()`.

---

## `client.py`

This is the minimal non-webcam test client.

### What it does

1. Builds payload with `landmarks` (currently `[0.0] * 63`).
2. Sends `POST` request to server.
3. Prints HTTP status and raw JSON response.

### Why it is useful

- Fast endpoint smoke test (no camera needed).
- Good template for integrating from another Python service.

---

## `live_client.py`

This is a webcam + MediaPipe front-end that calls your HTTP backend.

### Configuration section

- `SERVER_URLS`: tries `/predict` first, then `/endpoint` fallback
- `HAND_LANDMARKER_MODEL`: uses `ml/models/hand_landmarker.task`
- `REQUEST_TIMEOUT_SEC`: HTTP timeout
- `REQUEST_INTERVAL_SEC`: throttle requests (avoid sending every frame)

### `call_predict(landmarks)`

- Sends landmarks to server as JSON.
- Parses label/confidence on success.
- Handles errors gracefully:
  - 404 fallback to next endpoint URL
  - network timeout/connection issues
  - parse errors
- Returns tuple: `(label, confidence, optional_error)`

### `check_server_health()`

- Calls `/health` once at startup.
- Prints server status to terminal.

### `main()` runtime loop

1. Starts MediaPipe hand detector.
2. Opens webcam.
3. For each frame:
   - detects hand landmarks
   - draws points on frame
   - flattens landmarks into list
   - sends request at controlled interval
   - overlays prediction text and error text
4. Quits on `Q`.

---

## Manual curl test

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"landmarks":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]}'
```

---

## Troubleshooting

### `server_error` on live client

Do restart in this exact order:

1. Stop old processes.
2. `python ml/src/http_basic/server.py`
3. `python ml/src/http_basic/live_client.py`

### `HTTP 404 Not Found`

- Usually means old server version or wrong endpoint.
- Current live client auto-fallbacks between `/predict` and `/endpoint`.

### `Model is not loaded` or `503`

- Train first: `python ml/src/train/train_model.py`
- Confirm file exists: `ml/models/hand_sign_model.keras`
- Restart server after training.

### Invalid landmark length

- Ensure request has exactly `63` or `126` numeric values.

---

## Important behavior notes

- Server does **not** retrain automatically.
- If you retrain model, restart server to load new weights.
- All prediction logic is centralized in backend (`server.py`), so other apps can reuse it through HTTP.
