from __future__ import annotations

import argparse
import json
import os
import socket

import uvicorn

from .security import get_or_create_token


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Local_Chatbot backend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.getenv("LOCAL_CHATBOT_PORT", "0") or 0))
    args = parser.parse_args()

    port = args.port or free_port()
    token = get_or_create_token()
    from .app import app

    print(json.dumps({"event": "ready", "host": args.host, "port": port, "token": token}), flush=True)
    uvicorn.run(app, host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()
