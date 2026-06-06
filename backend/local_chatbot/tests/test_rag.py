from __future__ import annotations

from pathlib import Path

from local_chatbot.db import Database
from local_chatbot.embeddings import HashingEmbeddingModel
from local_chatbot.rag import RagService


class OfflineOllama:
    def generate(self, prompt: str, model: str) -> str:
        raise RuntimeError("Ollama unavailable in test")


def test_import_and_answer_with_citations(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_CHATBOT_DATA_DIR", str(tmp_path / "appdata"))
    source = tmp_path / "example.txt"
    source.write_text(
        "The Apollo project budget note says the launch window opens on Monday.",
        encoding="utf-8",
    )

    db = Database(tmp_path / "app.sqlite3")
    service = RagService(db=db, embedding_model=HashingEmbeddingModel(), ollama=OfflineOllama())

    imported = service.import_paths([str(source)])
    answer = service.answer(question="When does the launch window open?", provider="ollama")

    assert imported["count"] == 1
    assert answer["provider"] == "local-fallback"
    assert answer["citations"]
    assert answer["citations"][0]["title"] == "example.txt"
    assert "Monday" in answer["answer"]


def test_folder_import_records_single_folder_attachment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_CHATBOT_DATA_DIR", str(tmp_path / "appdata"))
    folder = tmp_path / "project"
    nested = folder / "nested"
    nested.mkdir(parents=True)
    (folder / "a.txt").write_text("Alpha project note", encoding="utf-8")
    (nested / "b.txt").write_text("Beta project note", encoding="utf-8")

    db = Database(tmp_path / "app.sqlite3")
    service = RagService(db=db, embedding_model=HashingEmbeddingModel(), ollama=OfflineOllama())
    chat = db.create_chat()

    result = service.import_paths([str(folder)], chat_id=chat["id"])
    attachments = db.list_attachments(chat["id"])

    assert result["count"] == 2
    assert len(attachments) == 1
    assert attachments[0]["kind"] == "folder"
    assert attachments[0]["label"] == "project"
    assert attachments[0]["file_count"] == 2
