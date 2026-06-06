from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.1:8b"


@dataclass(frozen=True)
class OllamaStatus:
    installed: bool
    running: bool
    models: list[str]
    error: str | None = None


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_URL, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def status(self) -> OllamaStatus:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            models = [item.get("name", "") for item in payload.get("models", []) if item.get("name")]
            return OllamaStatus(installed=True, running=True, models=models)
        except urllib.error.URLError as exc:
            return OllamaStatus(
                installed=False,
                running=False,
                models=[],
                error=f"Ollama is not reachable at {self.base_url}: {exc.reason}",
            )
        except Exception as exc:
            return OllamaStatus(installed=True, running=False, models=[], error=str(exc))

    def generate(self, prompt: str, model: str = DEFAULT_MODEL) -> str:
        body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("response", "").strip()

    def pull_model(self, model: str) -> dict[str, str]:
        model = model.strip()
        if not model:
            raise ValueError("Model name is required.")
        body = json.dumps({"name": model, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/pull",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=1200) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {"model": model, "status": payload.get("status", "success")}


def recommended_models() -> list[dict[str, str]]:
    return [
        {
            "name": DEFAULT_MODEL,
            "label": "Llama 3.1 8B",
            "description": "Balanced local chat model for modern consumer PCs.",
        },
        {
            "name": "qwen2.5:7b",
            "label": "Qwen 2.5 7B",
            "description": "Strong general-purpose model with modest hardware needs.",
        },
        {
            "name": "gemma2:2b",
            "label": "Gemma 2 2B",
            "description": "Smaller model for lower-memory machines.",
        },
    ]
