from __future__ import annotations

import os

SERVICE = "Local_Chatbot"


def set_provider_secret(provider: str, secret: str) -> None:
    import keyring

    keyring.set_password(SERVICE, provider, secret)


def get_provider_secret(provider: str, env_name: str) -> str | None:
    env_value = os.getenv(env_name)
    if env_value:
        return env_value
    try:
        import keyring

        return keyring.get_password(SERVICE, provider)
    except Exception:
        return None
