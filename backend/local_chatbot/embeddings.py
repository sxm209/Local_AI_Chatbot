from __future__ import annotations

import hashlib
import math
import re

TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")


class EmbeddingModel:
    name = "hashing-local"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class HashingEmbeddingModel(EmbeddingModel):
    """Deterministic local embedding fallback that needs no model download."""

    name = "hashing-local"

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimensions
            sign = 1.0 if value & 1 else -1.0
            vector[index] += sign
        length = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [item / length for item in vector]


def load_embedding_model(prefer_fastembed: bool = True) -> EmbeddingModel:
    if prefer_fastembed:
        try:
            from fastembed import TextEmbedding

            class FastEmbedModel(EmbeddingModel):
                name = "BAAI/bge-small-en-v1.5"

                def __init__(self) -> None:
                    self._model = TextEmbedding(model_name=self.name)

                def embed(self, texts: list[str]) -> list[list[float]]:
                    return [list(vector) for vector in self._model.embed(texts)]

            return FastEmbedModel()
        except Exception:
            pass
    return HashingEmbeddingModel()
