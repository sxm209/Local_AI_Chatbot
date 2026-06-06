from __future__ import annotations

import os
import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.responses import JSONResponse
from starlette.responses import Response


TOKEN_ENV = "LOCAL_CHATBOT_TOKEN"


def get_or_create_token() -> str:
    token = os.getenv(TOKEN_ENV)
    if token:
        return token
    token = secrets.token_urlsafe(32)
    os.environ[TOKEN_ENV] = token
    return token


async def token_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path in {"/", "/health"}:
        return await call_next(request)
    expected = get_or_create_token()
    supplied = request.headers.get("x-local-chatbot-token")
    if supplied != expected:
        return JSONResponse({"detail": "Invalid local API token"}, status_code=401)
    return await call_next(request)
