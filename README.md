# Sign SOS

Sign SOS is a multi-stack project that combines:

- A Flutter app scaffold (`lib/`, `android/`, `ios/`, etc.)
- A Python ML pipeline for hand-sign recognition (`ml/`)
- A Node.js TTS backend with API routes (`tts_server/`)

Main working flow:

1. Webcam captures hand landmarks (MediaPipe in Python)
2. TensorFlow model predicts sign label text (`help`, `cannot`, `speak`, `hello`)
3. When confidence reaches threshold (95%), Python client posts to backend:
	 - `POST /api/generate-audio` with `{ "text": "...", "userId": "..." }`
4. Backend generates audio and stores metadata (real server), or logs payload (post-test server)

---

## File-to-File Workflow (Who connects to what)

This section shows exactly how files communicate in this repo.

### A) Live prediction path (Python client -> Node API)

1. `ml/src/predict/live_predict.py`
	- Captures webcam frames (OpenCV)
	- Detects hand landmarks (MediaPipe)
	- Predicts label using `ml/models/hand_sign_model.keras`
2. Still in `live_predict.py`, `post_generate_audio(...)`
	- Sends `POST http://127.0.0.1:3000/api/generate-audio`
	- Body: `{ text, userId }`
3. Request is received by either:
	- `tts_server/server.posttest.js` (mock mode), or
	- `tts_server/server.js` (real mode)

### B) Real backend path (inside Node server)

When using `tts_server/server.js`:

1. `tts_server/server.js`
	- Mounts routes under `/api`
	- Connects to `routes/ttsRoute.js` and `routes/audioRoute.js`
2. `tts_server/routes/ttsRoute.js` (`POST /generate-audio`)
	- Calls `generateSpeech(text)` in `tts_server/services/ttsService.js`
	- Calls `uploadAudio(filePath)` and `saveMetadata(...)` in `tts_server/services/firebaseService.js`
3. `tts_server/services/ttsService.js`
	- Uses Google TTS, writes MP3 to `tts_server/temp/<uuid>.mp3`
4. `tts_server/services/firebaseService.js`
	- Uploads MP3 to Firebase Storage bucket
	- Saves record to Firestore collection `audioRecords`
5. `tts_server/config/firebase.js`
	- Creates and exports shared Firebase `db` + `bucket`

### C) Read records path

1. Client calls `GET /api/audio-records`
2. `tts_server/routes/audioRoute.js` reads `audioRecords` from Firestore (`db.collection(...).orderBy(...).get()`)
3. Returns JSON list to caller

### D) Current Flutter status

- `lib/main.dart` is currently Flutter default scaffold.
- Current end-to-end sign -> POST -> TTS pipeline is between:
  - `ml/src/predict/live_predict.py`
  - `tts_server/*`

### E) Quick connection map

```text
ml/src/predict/live_predict.py
  -> POST /api/generate-audio
	  -> tts_server/server.posttest.js (mock)
	  -> OR tts_server/server.js
			 -> routes/ttsRoute.js
				  -> services/ttsService.js
				  -> services/firebaseService.js
						 -> config/firebase.js
						 -> Firebase Storage + Firestore

GET /api/audio-records
  -> tts_server/server.js
		-> routes/audioRoute.js
			 -> config/firebase.js (db)
			 -> Firestore audioRecords
```

---

## Repository Structure

```text
kitahack/
├── lib/                         # Flutter app
├── ml/                          # Python ML training + live prediction
│   ├── models/
│   │   ├── hand_sign_model.keras
│   │   └── hand_landmarker.task
│   ├── src/
│   │   ├── predict/live_predict.py
│   │   └── ...
│   ├── requirements.txt
│   └── README.md
├── tts_server/                  # Node.js API backend
│   ├── server.js                # Real server (Firebase + Google TTS)
│   ├── server.posttest.js       # Local mock receiver for route testing
│   ├── routes/
│   │   ├── ttsRoute.js          # POST /api/generate-audio
│   │   └── audioRoute.js        # GET /api/audio-records
│   ├── services/
│   ├── config/
│   └── package.json
├── pubspec.yaml
└── README.md
```

---

## Tech Stack

- **ML / CV:** Python, TensorFlow, MediaPipe, OpenCV, NumPy
- **Backend API:** Node.js, Express, Firebase Admin, Google Cloud Text-to-Speech
- **Mobile scaffold:** Flutter (Dart)

---

## Architecture Diagram

<img width="1920" height="1080" alt="kitahack" src="https://github.com/user-attachments/assets/5fea22f0-98e0-4bb2-883f-eed24494627c" />

---

## API Contract (Backend)

Mounted in `tts_server/server.js` under `/api`.

### 1) Generate Audio

- **Method:** `POST`
- **Route:** `/api/generate-audio`
- **Body:**

```json
{
	"text": "hello",
	"userId": "demo-user"
}
```

- **Success response:**

```json
{
	"success": true,
	"audioUrl": "https://..."
}
```

### 2) Audio Records

- **Method:** `GET`
- **Route:** `/api/audio-records`
- **Response:** JSON array of saved records

---

## Prerequisites

### General

- Windows/macOS/Linux
- Git

### Python side

- Python 3.10+ recommended
- Webcam access enabled

### Node side

- Node.js 18+ recommended
- npm

### Optional (real TTS server)

- Firebase service account JSON
- Google Cloud credentials for TTS

---

## Setup Instructions

## A) ML (Python)

From project root:

```powershell
cd ml
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If execution policy blocks activation on PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## B) TTS Server (Node)

From project root:

```powershell
cd tts_server
npm install
```

---

## Run Modes

You have **two backend modes**:

### Mode 1: Post-Test Mode (Recommended for integration debugging)

Use this when you only want to verify camera → text → POST route works.

```powershell
cd tts_server
node server.posttest.js
```

What it does:

- Exposes `POST /api/generate-audio`
- Logs received payload
- Returns mock `audioUrl`

### Mode 2: Real TTS Mode

Use this when Firebase + Google credentials are configured.

```powershell
cd tts_server
npm start
```

Notes:

- This mode depends on files/env used in `tts_server/config/firebase.js` and `tts_server/services/ttsService.js`
- Missing `serviceAccount.json` will prevent startup

---

## Run Live Hand-Sign Prediction + POST

From project root:

```powershell
cd ml
python src/predict/live_predict.py
```

Current behavior in `live_predict.py`:

- Opens webcam
- Detects landmarks via MediaPipe
- Predicts sign via TensorFlow model
- If confidence >= `95.0` and label changed, sends:
	- `POST http://127.0.0.1:3000/api/generate-audio`
	- body `{ "text": "<predicted_label>", "userId": "demo-user" }`

Press `q` to quit.

---

## Integration Test (Recommended)

1. **Terminal A**: Start receiver

```powershell
cd tts_server
node server.posttest.js
```

2. **Terminal B**: Run scanner

```powershell
cd ml
python src/predict/live_predict.py
```

3. Show gesture until confidence reaches threshold

4. Verify logs:

- Scanner terminal:
	- `[POST OK] text=hello confidence=100.0% audioUrl=...`
- Server terminal:
	- `[POST RECEIVED] text="hello" userId="demo-user"`

If scanner shows `[POST FAILED] ... WinError 10061`, server is not listening on port `3000`.

---

## Important Configuration Points

In `ml/src/predict/live_predict.py`:

- `GENERATE_AUDIO_URL` → backend URL
- `USER_ID` → currently `demo-user`
- `POST_CONFIDENCE_THRESHOLD` → currently `95.0`
- `CLASSES` → `help`, `cannot`, `speak`, `hello`

If your backend is on another host/port, update `GENERATE_AUDIO_URL`.

---

## Flutter App

Flutter project scaffold exists and can be run independently:

```powershell
flutter pub get
flutter run
```

Current ML + TTS integration demonstrated in this repository is done through Python (`ml/src/predict/live_predict.py`) and Node (`tts_server/`).

---

## Troubleshooting

### 1) `FileNotFoundError: models/hand_landmarker.task`

Run script from inside `ml/` so relative paths resolve:

```powershell
cd ml
python src/predict/live_predict.py
```

### 2) `WinError 10061` on POST

Backend for `http://127.0.0.1:3000` is not running. Start `node tts_server/server.posttest.js` (or real server).

### 3) `Cannot find module 'express'`

Install node packages in `tts_server`:

```powershell
cd tts_server
npm install
```

### 4) `Cannot find module './serviceAccount.json'`

You started real server mode without credentials. Use post-test mode first or configure Firebase credentials.

### 5) Camera not opening

- Close other camera apps
- Check OS camera permissions
- Try a different camera index in `cv2.VideoCapture(...)`

---

## Current Status Summary

- Hand-sign capture and text prediction are working
- Route posting logic from Python scanner is working
- Endpoint receive verification works in post-test mode
- Real TTS mode requires credential setup

---

## Suggested Next Improvements

- Move `USER_ID`, URL, and threshold to environment variables
- Add retry/backoff for POST failures
- Add timestamp/request-id in logs
- Add API health route in Node server
- Add end-to-end script to launch both services for local testing
