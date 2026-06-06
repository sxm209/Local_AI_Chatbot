from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .chunking import chunk_document
from .db import Database
from .embeddings import EmbeddingModel, load_embedding_model
from .ingestion import discover_files, extract_document
from .ollama import DEFAULT_MODEL, OllamaClient
from .providers import generate_with_provider
from .vector_store import SQLiteVectorStore, SearchResult
from .web_search import search_web

LOGGER = logging.getLogger(__name__)


class RagService:
    def __init__(
        self,
        db: Database | None = None,
        embedding_model: EmbeddingModel | None = None,
        ollama: OllamaClient | None = None,
    ) -> None:
        self.db = db or Database()
        self.embedding_model = embedding_model or load_embedding_model()
        self.vector_store = SQLiteVectorStore(self.db)
        self.ollama = ollama or OllamaClient()

    def import_paths(
        self,
        paths: list[str],
        recursive: bool = True,
        enable_ocr: bool = False,
        chat_id: str | None = None,
    ) -> dict[str, Any]:
        self.db.ensure_chat(chat_id)
        files, warnings = discover_files(paths, recursive=recursive)
        attachments = self._record_attachments(paths, files, chat_id=chat_id)
        imported: list[dict[str, Any]] = []
        failed: list[dict[str, str]] = list(warnings)

        for file_path in files:
            try:
                document = extract_document(file_path)
                if enable_ocr and not any(section.text.strip() for section in document.sections):
                    self.db.log_import_event(str(file_path), "warning", "OCR requested but not configured")

                doc_id = self.db.upsert_document(
                    chat_id=chat_id,
                    path=str(document.path),
                    title=document.title,
                    file_type=document.file_type,
                    sha256=document.sha256,
                    modified_at=document.modified_at,
                    status="indexed" if document.sections else "warning",
                    warning=document.warning,
                )
                chunks = [
                    {"text": chunk.text, "metadata": chunk.metadata}
                    for chunk in chunk_document(document)
                ]
                chunk_count = self.vector_store.add_chunks(doc_id, chunks, self.embedding_model)
                imported.append(
                    {
                        "id": doc_id,
                        "path": str(document.path),
                        "title": document.title,
                        "chunks": chunk_count,
                        "warning": document.warning,
                    }
                )
                self.db.log_import_event(str(file_path), "indexed", f"Indexed {chunk_count} chunks")
            except Exception as exc:
                LOGGER.info("import_failed path=%s error=%s", file_path, type(exc).__name__)
                failed.append({"path": str(file_path), "message": str(exc)})
                self.db.log_import_event(str(file_path), "failed", str(exc))

        for warning in warnings:
            self.db.log_import_event(warning["path"], "warning", warning["message"])

        return {
            "imported": imported,
            "failed": failed,
            "attachments": attachments,
            "count": len(imported),
        }

    def _record_attachments(
        self, raw_paths: list[str], files: list[Path], chat_id: str | None
    ) -> list[dict[str, Any]]:
        if not chat_id:
            return []
        normalized_files = {str(path.resolve()) for path in files}
        attachments: list[dict[str, Any]] = []
        for raw_path in raw_paths:
            path = Path(raw_path).expanduser().resolve()
            if path.is_dir():
                if path.exists():
                    file_count = sum(
                        1
                        for child in path.rglob("*")
                        if child.is_file() and str(child.resolve()) in normalized_files
                    )
                else:
                    file_count = 0
                kind = "folder"
            elif path.is_file():
                file_count = 1 if str(path) in normalized_files else 0
                kind = "file"
            else:
                continue
            attachment_id = self.db.upsert_attachment(
                chat_id=chat_id,
                kind=kind,
                label=path.name,
                path=str(path),
                file_count=file_count,
            )
            attachments.append(
                {
                    "id": attachment_id,
                    "chat_id": chat_id,
                    "kind": kind,
                    "label": path.name,
                    "path": str(path),
                    "file_count": file_count,
                }
            )
        return attachments

    def answer(
        self,
        *,
        question: str,
        chat_id: str | None = None,
        provider: str = "ollama",
        model: str | None = None,
        use_web: bool = False,
    ) -> dict[str, Any]:
        requested_chat_id = chat_id
        chat_id = chat_id or str(uuid.uuid4())
        self.db.ensure_chat(chat_id)
        self.db.save_message(chat_id, "user", question)
        results = self.vector_store.search(
            question, self.embedding_model, limit=6, chat_id=requested_chat_id
        )
        web_results = []
        web_warning = None
        try:
            if use_web:
                web_results = [asdict(item) for item in search_web(question, enabled=True)]
        except Exception as exc:
            web_warning = str(exc)
        citations = [_citation(result, index) for index, result in enumerate(results, start=1)]
        citations.extend(_web_citation(result, len(citations) + index) for index, result in enumerate(web_results, start=1))
        context = _format_context(results, web_results)
        prompt = _build_prompt(question, context, use_web=use_web, web_warning=web_warning)

        try:
            if provider == "ollama":
                text = self.ollama.generate(prompt, model=model or DEFAULT_MODEL)
                used_provider = "ollama"
            else:
                result = generate_with_provider(provider, prompt, model=model)
                text = result.text
                used_provider = result.provider
        except Exception as exc:
            LOGGER.info("generation_fallback provider=%s error=%s", provider, type(exc).__name__)
            text = _extractive_fallback(question, results, str(exc), web_warning=web_warning)
            used_provider = "local-fallback"
        if web_warning and used_provider != "local-fallback":
            text = f"{text}\n\nWeb search note: {web_warning}"

        self.db.save_message(chat_id, "assistant", text, citations)
        return {
            "chat_id": chat_id,
            "answer": text,
            "provider": used_provider,
            "citations": citations,
            "web_results": web_results,
            "web_warning": web_warning,
        }


def _citation(result: SearchResult, index: int) -> dict[str, Any]:
    location = []
    for key in ("page", "sheet", "slide", "section"):
        if key in result.metadata:
            location.append(f"{key} {result.metadata[key]}")
    return {
        "id": index,
        "document_id": result.document_id,
        "title": result.document_title,
        "path": result.document_path,
        "location": ", ".join(location) or f"chunk {result.metadata.get('chunk', 0)}",
        "snippet": result.text[:360],
        "score": round(result.score, 4),
    }


def _web_citation(result: dict[str, str], index: int) -> dict[str, Any]:
    url = result.get("url", "")
    return {
        "id": index,
        "document_id": url,
        "title": result.get("title", "Web result"),
        "path": url,
        "location": "web result",
        "snippet": result.get("snippet", ""),
        "score": 0,
    }


def _format_context(results: list[SearchResult], web_results: list[dict[str, str]]) -> str:
    lines = []
    for index, result in enumerate(results, start=1):
        lines.append(f"[{index}] {Path(result.document_path).name} - {result.text}")
    start = len(results) + 1
    for index, result in enumerate(web_results, start=start):
        lines.append(
            f"[{index}] Web: {result.get('title', 'Untitled')} - "
            f"{result.get('snippet', '')} ({result.get('url', '')})"
        )
    return "\n\n".join(lines)


def _build_prompt(question: str, context: str, use_web: bool, web_warning: str | None = None) -> str:
    if use_web and web_warning:
        web_rule = f"Web search was requested but failed: {web_warning}"
    elif use_web:
        web_rule = "Web search is enabled. You may use supplied web results in addition to local context."
    else:
        web_rule = "Web search is disabled. Use only supplied local context."
    return f"""You are Local AI Chatbot, a local-first document assistant.
Answer only from the supplied context.
Include bracketed citation numbers like [1] for each factual claim.
If the context is insufficient, say what is missing.
{web_rule}

Context:
{context or "No local documents were retrieved."}

Question:
{question}
"""


def _extractive_fallback(
    question: str, results: list[SearchResult], error: str, web_warning: str | None = None
) -> str:
    web_note = f"\nWeb search note: {web_warning}" if web_warning else ""
    if not results:
        return (
            "I could not reach the selected AI model, and there are no indexed document matches yet. "
            f"Model error: {error}{web_note}"
        )
    snippets = []
    for index, result in enumerate(results[:3], start=1):
        snippets.append(f"[{index}] {result.text[:420]}")
    return (
        "I could not reach the selected AI model, so I am showing the most relevant local excerpts "
        "with citations instead.\n\n" + "\n\n".join(snippets) + web_note
    )
