from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from .secrets_store import get_provider_secret


PROVIDERS = {
    "openai": {
        "label": "OpenAI / ChatGPT",
        "env": "OPENAI_API_KEY",
        "auth_label": "OpenAI API key",
        "key_placeholder": "sk-...",
        "default_model": "gpt-4.1-mini",
        "docs_url": "https://platform.openai.com/api-keys",
        "warning": "May send selected prompt and retrieved source snippets to OpenAI.",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "env": "ANTHROPIC_API_KEY",
        "auth_label": "Anthropic API key",
        "key_placeholder": "sk-ant-...",
        "default_model": "claude-3-5-haiku-latest",
        "docs_url": "https://console.anthropic.com/settings/keys",
        "warning": "May send selected prompt and retrieved source snippets to Anthropic.",
    },
    "google": {
        "label": "Google Gemini",
        "env": "GOOGLE_API_KEY",
        "auth_label": "Gemini API key",
        "key_placeholder": "AIza...",
        "default_model": "gemini-1.5-flash",
        "docs_url": "https://aistudio.google.com/app/apikey",
        "warning": "May send selected prompt and retrieved source snippets to Google.",
    },
    "xai": {
        "label": "xAI Grok",
        "env": "XAI_API_KEY",
        "auth_label": "xAI API key",
        "key_placeholder": "xai-...",
        "default_model": "grok-2-latest",
        "docs_url": "https://console.x.ai/",
        "warning": "May send selected prompt and retrieved source snippets to xAI.",
    },
}


@dataclass(frozen=True)
class ProviderResult:
    text: str
    provider: str


def provider_catalog(configured: set[str] | None = None) -> list[dict[str, object]]:
    configured = configured or set()
    return [
        {
            "id": provider,
            "label": info["label"],
            "configured": provider in configured or bool(os.getenv(info["env"])),
            "privacy_warning": info["warning"],
            "auth_label": info["auth_label"],
            "key_placeholder": info["key_placeholder"],
            "default_model": info["default_model"],
            "docs_url": info["docs_url"],
        }
        for provider, info in PROVIDERS.items()
    ]


def generate_with_provider(provider: str, prompt: str, model: str | None = None) -> ProviderResult:
    if provider == "openai":
        return _openai(prompt, model or "gpt-4.1-mini")
    if provider == "anthropic":
        return _anthropic(prompt, model or "claude-3-5-haiku-latest")
    if provider == "google":
        return _google(prompt, model or "gemini-1.5-flash")
    if provider == "xai":
        return _xai(prompt, model or "grok-2-latest")
    raise ValueError(f"Unknown provider: {provider}")


def _api_key(provider: str) -> str:
    env = PROVIDERS[provider]["env"]
    key = get_provider_secret(provider, env)
    if not key:
        raise RuntimeError(f"{PROVIDERS[provider]['label']} is not configured. Set {env}.")
    return key


def _post_json(url: str, headers: dict[str, str], body: dict[str, object], timeout: float = 90) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _openai(prompt: str, model: str) -> ProviderResult:
    payload = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {_api_key('openai')}"},
        {"model": model, "messages": [{"role": "user", "content": prompt}]},
    )
    return ProviderResult(payload["choices"][0]["message"]["content"].strip(), "openai")


def _anthropic(prompt: str, model: str) -> ProviderResult:
    payload = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": _api_key("anthropic"),
            "anthropic-version": "2023-06-01",
        },
        {"model": model, "max_tokens": 1200, "messages": [{"role": "user", "content": prompt}]},
    )
    text = "".join(block.get("text", "") for block in payload.get("content", []))
    return ProviderResult(text.strip(), "anthropic")


def _google(prompt: str, model: str) -> ProviderResult:
    key = _api_key("google")
    payload = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        {},
        {"contents": [{"parts": [{"text": prompt}]}]},
    )
    parts = payload["candidates"][0]["content"]["parts"]
    return ProviderResult("".join(part.get("text", "") for part in parts).strip(), "google")


def _xai(prompt: str, model: str) -> ProviderResult:
    payload = _post_json(
        "https://api.x.ai/v1/chat/completions",
        {"Authorization": f"Bearer {_api_key('xai')}"},
        {"model": model, "messages": [{"role": "user", "content": prompt}]},
    )
    return ProviderResult(payload["choices"][0]["message"]["content"].strip(), "xai")
