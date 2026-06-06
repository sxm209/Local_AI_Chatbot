from __future__ import annotations

from pathlib import Path

from local_chatbot.db import Database
from local_chatbot.embeddings import HashingEmbeddingModel
from local_chatbot.vector_store import SQLiteVectorStore


def test_sqlite_vector_store_returns_relevant_chunk(tmp_path: Path) -> None:
    db = Database(tmp_path / "vectors.sqlite3")
    store = SQLiteVectorStore(db)
    model = HashingEmbeddingModel()
    doc_id = db.upsert_document(
        path=str(tmp_path / "notes.txt"),
        title="notes.txt",
        file_type="txt",
        sha256="abc",
        modified_at=1,
        status="indexed",
    )

    store.add_chunks(
        doc_id,
        [
            {"text": "invoice payment terms net thirty", "metadata": {"page": 1}},
            {"text": "garden herbs basil mint parsley", "metadata": {"page": 2}},
        ],
        model,
    )

    results = store.search("payment invoice", model, limit=1)

    assert results[0].metadata["page"] == 1
