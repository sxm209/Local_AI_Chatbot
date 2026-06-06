from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__
from .db import Database
from .logging_config import configure_logging
from .ollama import OllamaClient, recommended_models
from .paths import data_paths
from .providers import provider_catalog
from .rag import RagService
from .security import token_middleware
from .secrets_store import set_provider_secret

configure_logging()

db = Database()
rag = RagService(db=db)
ollama = OllamaClient()

app = FastAPI(title="Local AI Chatbot Backend", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(token_middleware)


class ImportRequest(BaseModel):
    paths: list[str] = Field(min_length=1)
    recursive: bool = True
    enable_ocr: bool = False
    chat_id: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    chat_id: str | None = None
    provider: str = "ollama"
    model: str | None = None
    use_web: bool = False


class ApiKeyRequest(BaseModel):
    provider: str
    api_key: str = Field(min_length=1)
    configured: bool = True


class CreateChatRequest(BaseModel):
    title: str = "New chat"


class PullModelRequest(BaseModel):
    model: str = Field(min_length=1)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Local AI Chatbot", "version": __version__}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": __version__}


@app.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    status = ollama.status()
    paths = data_paths()
    return {
        "version": __version__,
        "backend": "running",
        "data_dir": str(paths["root"]),
        "database": str(paths["db"]),
        "ollama": status.__dict__,
        "recommended_models": recommended_models(),
        "embedding_model": rag.embedding_model.name,
        "web_search": {
            "configured": True,
            "provider": "DuckDuckGo",
            "requires_key": False,
        },
        "recent_import_events": db.recent_import_events(),
        "providers": provider_catalog({item["provider"] for item in db.provider_status()}),
        "redacted_env": {
            key: "***" for key in os.environ if key.endswith("_API_KEY") and os.environ.get(key)
        },
    }


@app.get("/setup/models")
def setup_models() -> dict[str, Any]:
    return {"ollama": ollama.status().__dict__, "recommended": recommended_models()}


@app.post("/ollama/pull")
def pull_ollama_model(request: PullModelRequest) -> dict[str, str]:
    return ollama.pull_model(request.model)


@app.get("/chats")
def chats() -> list[dict[str, Any]]:
    return db.list_chats()


@app.post("/chats")
def create_chat(request: CreateChatRequest) -> dict[str, Any]:
    return db.create_chat(request.title)


@app.get("/chats/{chat_id}/messages")
def chat_messages(chat_id: str) -> list[dict[str, Any]]:
    return db.list_messages(chat_id)


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: str) -> dict[str, bool]:
    db.delete_chat(chat_id)
    return {"deleted": True}


@app.delete("/chats/{chat_id}/empty")
def delete_empty_chat(chat_id: str) -> dict[str, bool]:
    return {"deleted": db.delete_empty_chat(chat_id)}


@app.get("/attachments")
def attachments(chat_id: str) -> list[dict[str, Any]]:
    return db.list_attachments(chat_id)


@app.post("/documents/import")
def import_documents(request: ImportRequest) -> dict[str, Any]:
    return rag.import_paths(
        request.paths,
        recursive=request.recursive,
        enable_ocr=request.enable_ocr,
        chat_id=request.chat_id,
    )


@app.get("/documents")
def documents(chat_id: str | None = None) -> list[dict[str, Any]]:
    return db.list_documents(chat_id=chat_id)


@app.delete("/documents/{document_id}")
def delete_document(document_id: str) -> dict[str, bool]:
    db.delete_document(document_id)
    return {"deleted": True}


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    return rag.answer(
        question=request.question,
        chat_id=request.chat_id,
        provider=request.provider,
        model=request.model,
        use_web=request.use_web,
    )


@app.get("/providers")
def providers() -> list[dict[str, object]]:
    return provider_catalog({item["provider"] for item in db.provider_status()})


@app.post("/providers/key")
def provider_key(request: ApiKeyRequest) -> dict[str, bool]:
    set_provider_secret(request.provider, request.api_key)
    db.set_api_key_ref(request.provider, "windows-credential-manager", request.configured)
    return {"saved": True}
