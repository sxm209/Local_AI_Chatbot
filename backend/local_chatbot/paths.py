from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "Local_Chatbot"
ENV_DATA_DIR = "LOCAL_CHATBOT_DATA_DIR"


def app_data_dir() -> Path:
    override = os.getenv(ENV_DATA_DIR)
    if override:
        root = Path(override).expanduser()
    else:
        try:
            from platformdirs import user_data_dir

            root = Path(user_data_dir(APP_NAME, appauthor=False))
        except Exception:
            root = Path.home() / "AppData" / "Local" / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def data_paths() -> dict[str, Path]:
    root = app_data_dir()
    paths = {
        "root": root,
        "db": root / "local_chatbot.sqlite3",
        "cache": root / "cache",
        "logs": root / "logs",
        "vectors": root / "vectors",
        "models": root / "models",
        "ocr": root / "ocr",
    }
    for key, path in paths.items():
        if key != "db":
            path.mkdir(parents=True, exist_ok=True)
    return paths
