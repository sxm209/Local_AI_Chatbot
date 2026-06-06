from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Any

from .db import Database
from .embeddings import EmbeddingModel


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    document_title: str
    document_path: str
    text: str
    metadata: dict[str, Any]
    score: float


class VectorStore:
    def add_chunks(
        self, document_id: str, chunks: list[dict[str, Any]], model: EmbeddingModel
    ) -> int:
        raise NotImplementedError

    def search(
        self, query: str, model: EmbeddingModel, limit: int = 6, chat_id: str | None = None
    ) -> list[SearchResult]:
        raise NotImplementedError


class SQLiteVectorStore(VectorStore):
    def __init__(self, db: Database) -> None:
        self.db = db

    def add_chunks(
        self, document_id: str, chunks: list[dict[str, Any]], model: EmbeddingModel
    ) -> int:
        embeddings = model.embed([chunk["text"] for chunk in chunks])
        rows = []
        for ordinal, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "ordinal": ordinal,
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                    "embedding": embedding,
                }
            )
        self.db.insert_chunks(rows)
        return len(rows)

    def search(
        self, query: str, model: EmbeddingModel, limit: int = 6, chat_id: str | None = None
    ) -> list[SearchResult]:
        query_vector = model.embed([query])[0]
        scored: list[SearchResult] = []
        for row in self.db.all_chunks():
            if chat_id and row.get("chat_id") != chat_id:
                continue
            score = cosine_similarity(query_vector, row["embedding"])
            scored.append(
                SearchResult(
                    chunk_id=row["id"],
                    document_id=row["document_id"],
                    document_title=row["document_title"],
                    document_path=row["document_path"],
                    text=row["text"],
                    metadata=row["metadata"],
                    score=score,
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    if not size:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size])) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right[:size])) or 1.0
    return dot / (left_norm * right_norm)
