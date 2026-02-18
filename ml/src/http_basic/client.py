"""Minimal client example that sends landmark data for prediction."""

import json
from urllib import request

URL = "http://127.0.0.1:8000/endpoint"


def main() -> None:
    # Example landmark payload.
    # Replace with real values from your MediaPipe pipeline.
    # 63 values (one hand) is supported and auto-padded by the server.
    payload = {
        "landmarks": [0.0] * 63,
    }

    req = request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req) as response:
        body = response.read().decode("utf-8")
        print("Status:", response.status)
        print("Response:", body)


if __name__ == "__main__":
    main()
