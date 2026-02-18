"""Minimal HTTP server that keeps your trained model ready for inference.

Flow:
1) Train and save model to models/hand_sign_model.keras
2) Start this server (it loads model once into memory)
3) Send HTTP requests with landmark data to get predictions
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import numpy as np
import tensorflow as tf

HOST = "127.0.0.1"
PORT = 8000
CLASSES = ["help", "cannot", "speak", "hello"]
EXPECTED_LEN = 126
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "hand_sign_model.keras"

# Keep model in memory so each request can use it directly.
MODEL = None


def _load_model() -> tf.keras.Model | None:
    """Load the trained model from disk, if available."""
    if not MODEL_PATH.exists():
        print(f"⚠️ Model file not found: {MODEL_PATH}")
        print("Run training first: python ml/src/train/train_model.py")
        return None

    loaded_model = tf.keras.models.load_model(MODEL_PATH)
    print(f"✅ Model loaded from: {MODEL_PATH}")
    print(f"📋 Classes: {CLASSES}")
    return loaded_model


class SimpleHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict) -> None:
        """Helper to send JSON responses with a status code."""
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_POST(self) -> None:
        """Handle POST prediction requests and return model prediction."""
        if self.path not in ("/endpoint", "/predict"):
            self._send_json(404, {"error": "Not Found"})
            return

        if MODEL is None:
            self._send_json(
                503,
                {
                    "error": "Model is not loaded",
                    "model_path": str(MODEL_PATH),
                    "hint": "Train first, then restart server",
                },
            )
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        # Expect: {"landmarks": [float, float, ...]}
        landmarks = body.get("landmarks")
        if not isinstance(landmarks, list):
            self._send_json(400, {"error": "'landmarks' must be a list of numbers"})
            return

        try:
            values = [float(value) for value in landmarks]
        except (TypeError, ValueError):
            self._send_json(400, {"error": "'landmarks' must contain only numeric values"})
            return

        # Match your existing training/predict shape:
        # - 63 values (one hand) -> pad to 126
        # - 126 values (two hands / padded feature length) -> use directly
        if len(values) == 63:
            values.extend([0.0] * 63)

        if len(values) != EXPECTED_LEN:
            self._send_json(
                400,
                {
                    "error": "Invalid landmark length",
                    "expected": [63, EXPECTED_LEN],
                    "received": len(values),
                },
            )
            return

        X = np.array(values, dtype=np.float32).reshape(1, -1)
        preds = MODEL.predict(X, verbose=0)[0]
        class_id = int(np.argmax(preds))
        confidence = float(preds[class_id])

        self._send_json(
            200,
            {
                "label": CLASSES[class_id],
                "confidence": confidence,
                "scores": {name: float(score) for name, score in zip(CLASSES, preds)},
            },
        )

    def do_GET(self) -> None:
        """Optional health check route."""
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "model_loaded": MODEL is not None,
                    "model_path": str(MODEL_PATH),
                },
            )
            return

        self._send_json(404, {"error": "Not Found"})


if __name__ == "__main__":
    MODEL = _load_model()
    server = HTTPServer((HOST, PORT), SimpleHandler)
    print(f"Server running at http://{HOST}:{PORT}")
    print("POST to /predict (or /endpoint) with {\"landmarks\": [...]} or GET /health")
    server.serve_forever()
