from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .paths import data_paths


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  chat_id TEXT,
  path TEXT NOT NULL,
  title TEXT NOT NULL,
  file_type TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  modified_at REAL NOT NULL,
  indexed_at REAL NOT NULL,
  status TEXT NOT NULL,
  warning TEXT,
  FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL,
  text TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  embedding_json TEXT NOT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE TABLE IF NOT EXISTS chats (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS attachments (
  id TEXT PRIMARY KEY,
  chat_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  label TEXT NOT NULL,
  path TEXT NOT NULL,
  file_count INTEGER NOT NULL,
  created_at REAL NOT NULL,
  FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_attachments_chat_path ON attachments(chat_id, path);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  chat_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  citations_json TEXT NOT NULL,
  created_at REAL NOT NULL,
  FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS api_keys (
  provider TEXT PRIMARY KEY,
  key_ref TEXT NOT NULL,
  configured INTEGER NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS import_events (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at REAL NOT NULL
);
"""


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or data_paths()["db"]
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute("DROP INDEX IF EXISTS idx_documents_path_sha")
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(documents)").fetchall()
            }
            if "chat_id" not in columns:
                conn.execute("ALTER TABLE documents ADD COLUMN chat_id TEXT")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_chat_path_sha
                ON documents(IFNULL(chat_id, ''), path, sha256)
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_chat ON documents(chat_id)")

    def set_setting(self, key: str, value: Any) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at
                """,
                (key, json.dumps(value), time.time()),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.connect() as conn:
            row = conn.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row["value_json"]) if row else default

    def upsert_document(
        self,
        *,
        path: str,
        title: str,
        file_type: str,
        sha256: str,
        modified_at: float,
        status: str,
        warning: str | None = None,
        chat_id: str | None = None,
    ) -> str:
        existing = self.find_document(path, sha256, chat_id)
        doc_id = existing["id"] if existing else str(uuid.uuid4())
        with self.connect() as conn:
            self.ensure_chat(chat_id, conn=conn)
            conn.execute(
                """
                INSERT INTO documents(id, chat_id, path, title, file_type, sha256, modified_at, indexed_at, status, warning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  chat_id=excluded.chat_id,
                  title=excluded.title,
                  modified_at=excluded.modified_at,
                  indexed_at=excluded.indexed_at,
                  status=excluded.status,
                  warning=excluded.warning
                """,
                (
                    doc_id,
                    chat_id,
                    path,
                    title,
                    file_type,
                    sha256,
                    modified_at,
                    time.time(),
                    status,
                    warning,
                ),
            )
            conn.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
        return doc_id

    def find_document(self, path: str, sha256: str, chat_id: str | None) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM documents
                WHERE path=? AND sha256=? AND IFNULL(chat_id, '')=IFNULL(?, '')
                """,
                (path, sha256, chat_id),
            ).fetchone()

    def list_documents(self, chat_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if chat_id:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE chat_id=? ORDER BY indexed_at DESC, title ASC",
                    (chat_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM documents ORDER BY indexed_at DESC, title ASC"
                ).fetchall()
        return [dict(row) for row in rows]

    def ensure_chat(self, chat_id: str | None, conn: sqlite3.Connection | None = None) -> str | None:
        if not chat_id:
            return None
        now = time.time()
        owns_conn = conn is None
        conn = conn or self.connect()
        try:
            conn.execute(
                """
                INSERT INTO chats(id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (chat_id, "New chat", now, now),
            )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn:
                conn.close()
        return chat_id

    def create_chat(self, title: str = "New chat") -> dict[str, Any]:
        chat_id = str(uuid.uuid4())
        now = time.time()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO chats(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (chat_id, title, now, now),
            )
        return {
            "id": chat_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "document_count": 0,
            "message_count": 0,
            "attachment_count": 0,
        }

    def list_chats(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*,
                  (SELECT COUNT(*) FROM documents d WHERE d.chat_id=c.id) AS document_count,
                  (SELECT COUNT(*) FROM messages m WHERE m.chat_id=c.id) AS message_count,
                  (SELECT COUNT(*) FROM attachments a WHERE a.chat_id=c.id) AS attachment_count
                FROM chats c
                ORDER BY c.updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_chat(self, chat_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM documents WHERE chat_id=?", (chat_id,))
            conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))

    def delete_empty_chat(self, chat_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM messages WHERE chat_id=?) AS message_count,
                  (SELECT COUNT(*) FROM documents WHERE chat_id=?) AS document_count,
                  (SELECT COUNT(*) FROM attachments WHERE chat_id=?) AS attachment_count
                """,
                (chat_id, chat_id, chat_id),
            ).fetchone()
            if not row or row["message_count"] or row["document_count"] or row["attachment_count"]:
                return False
            conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))
            return True

    def upsert_attachment(
        self, *, chat_id: str, kind: str, label: str, path: str, file_count: int
    ) -> str:
        attachment_id = str(uuid.uuid4())
        with self.connect() as conn:
            self.ensure_chat(chat_id, conn=conn)
            conn.execute(
                """
                INSERT INTO attachments(id, chat_id, kind, label, path, file_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, path) DO UPDATE SET
                  kind=excluded.kind,
                  label=excluded.label,
                  file_count=excluded.file_count,
                  created_at=excluded.created_at
                """,
                (attachment_id, chat_id, kind, label, path, file_count, time.time()),
            )
            row = conn.execute(
                "SELECT id FROM attachments WHERE chat_id=? AND path=?", (chat_id, path)
            ).fetchone()
        return row["id"] if row else attachment_id

    def list_attachments(self, chat_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, chat_id, kind, label, path, file_count, created_at
                FROM attachments
                WHERE chat_id=?
                ORDER BY created_at DESC, label ASC
                """,
                (chat_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_document(self, document_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM documents WHERE id=?", (document_id,))

    def insert_chunks(self, rows: Iterable[dict[str, Any]]) -> None:
        payload = [
            (
                row["id"],
                row["document_id"],
                row["ordinal"],
                row["text"],
                json.dumps(row["metadata"]),
                json.dumps(row["embedding"]),
            )
            for row in rows
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO chunks(id, document_id, ordinal, text, metadata_json, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                payload,
            )

    def all_chunks(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*, d.title AS document_title, d.path AS document_path, d.chat_id AS chat_id
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                """
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json"))
            item["embedding"] = json.loads(item.pop("embedding_json"))
            result.append(item)
        return result

    def save_message(
        self, chat_id: str, role: str, content: str, citations: list[dict[str, Any]] | None = None
    ) -> str:
        now = time.time()
        with self.connect() as conn:
            chat = conn.execute("SELECT id FROM chats WHERE id=?", (chat_id,)).fetchone()
            if not chat:
                conn.execute(
                    "INSERT INTO chats(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (chat_id, "New chat", now, now),
                )
            else:
                conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now, chat_id))
            if role == "user":
                current = conn.execute("SELECT title FROM chats WHERE id=?", (chat_id,)).fetchone()
                if current and current["title"] == "New chat":
                    title = content.strip().replace("\n", " ")[:44] or "New chat"
                    conn.execute("UPDATE chats SET title=? WHERE id=?", (title, chat_id))
            message_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO messages(id, chat_id, role, content, citations_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, chat_id, role, content, json.dumps(citations or []), now),
            )
        return message_id

    def list_messages(self, chat_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, chat_id, role, content, citations_json, created_at
                FROM messages
                WHERE chat_id=?
                ORDER BY created_at ASC
                """,
                (chat_id,),
            ).fetchall()
        messages = []
        for row in rows:
            item = dict(row)
            item["citations"] = json.loads(item.pop("citations_json"))
            messages.append(item)
        return messages

    def set_api_key_ref(self, provider: str, key_ref: str, configured: bool) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO api_keys(provider, key_ref, configured, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(provider) DO UPDATE SET
                  key_ref=excluded.key_ref,
                  configured=excluded.configured,
                  updated_at=excluded.updated_at
                """,
                (provider, key_ref, int(configured), time.time()),
            )

    def provider_status(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT provider, configured, updated_at FROM api_keys").fetchall()
        return [dict(row) for row in rows]

    def log_import_event(self, path: str, status: str, message: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO import_events(id, path, status, message, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), path, status, message, time.time()),
            )

    def recent_import_events(self, limit: int = 25) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT path, status, message, created_at FROM import_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
