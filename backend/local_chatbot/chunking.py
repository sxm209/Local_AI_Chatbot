from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ingestion import ExtractedDocument


@dataclass(frozen=True)
class Chunk:
    text: str
    metadata: dict[str, Any]


def chunk_document(document: ExtractedDocument, max_chars: int = 1400, overlap: int = 180) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in document.sections:
        text = " ".join(section.text.split())
        if not text:
            continue
        start = 0
        ordinal = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                metadata = {
                    **section.metadata,
                    "source": str(document.path),
                    "title": document.title,
                    "chunk": ordinal,
                }
                chunks.append(Chunk(text=chunk_text, metadata=metadata))
            if end == len(text):
                break
            start = max(0, end - overlap)
            ordinal += 1
    return chunks
