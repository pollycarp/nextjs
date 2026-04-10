"""
SQLite persistence layer — Phase 6.

Uses stdlib sqlite3 (no extra driver needed).
DB_PATH is module-level so tests can swap it to a temp file.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH: str = str(Path(__file__).parent.parent.parent / "data" / "research.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    tags        TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    doc_id      TEXT NOT NULL,
    filename    TEXT NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    page_count  INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'processed',
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    project_id TEXT,
    title      TEXT DEFAULT 'New Conversation',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_logs (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    query         TEXT NOT NULL,
    research_type TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.executescript(_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Projects ──────────────────────────────────────────────────────────────── #

def create_project(user_id: str, title: str, description: str = "", tags: str = "") -> dict:
    pid = str(uuid.uuid4())
    now = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?,?)",
            (pid, user_id, title, description, tags, now, now),
        )
    return {"id": pid, "user_id": user_id, "title": title, "description": description,
            "tags": tags, "created_at": now, "updated_at": now}


def get_projects(user_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM projects WHERE user_id=?", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def update_project(user_id: str, project_id: str, **fields) -> dict | None:
    allowed = {"title", "description", "tags"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return None
    set_clause = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [_now(), user_id, project_id]
    with _conn() as con:
        con.execute(
            f"UPDATE projects SET {set_clause}, updated_at=? WHERE user_id=? AND id=?",
            vals,
        )
        row = con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    return dict(row) if row else None


def delete_project(user_id: str, project_id: str) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM projects WHERE user_id=? AND id=?", (user_id, project_id))
    return cur.rowcount > 0


# ── Documents ─────────────────────────────────────────────────────────────── #

def save_document(user_id: str, doc_id: str, filename: str,
                  chunk_count: int, page_count: int, status: str = "processed") -> dict:
    did = str(uuid.uuid4())
    now = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
            (did, user_id, doc_id, filename, chunk_count, page_count, status, now),
        )
    return {"id": did, "user_id": user_id, "doc_id": doc_id, "filename": filename,
            "chunk_count": chunk_count, "page_count": page_count, "status": status, "created_at": now}


def get_documents(user_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM documents WHERE user_id=?", (user_id,)).fetchall()
    return [dict(r) for r in rows]


# ── Conversations ─────────────────────────────────────────────────────────── #

def create_conversation(user_id: str, project_id: str | None = None,
                        title: str = "New Conversation") -> dict:
    cid = str(uuid.uuid4())
    now = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO conversations VALUES (?,?,?,?,?)",
            (cid, user_id, project_id, title, now),
        )
    return {"id": cid, "user_id": user_id, "project_id": project_id, "title": title, "created_at": now}


def get_conversations(user_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM conversations WHERE user_id=?", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def save_message(conversation_id: str, role: str, content: str) -> dict:
    mid = str(uuid.uuid4())
    now = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO messages VALUES (?,?,?,?,?)",
            (mid, conversation_id, role, content, now),
        )
    return {"id": mid, "conversation_id": conversation_id, "role": role, "content": content, "created_at": now}


def get_messages(conversation_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at",
            (conversation_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Search logs / analytics ───────────────────────────────────────────────── #

def log_search(user_id: str, query: str, research_type: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO search_logs VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), user_id, query, research_type, _now()),
        )


def get_analytics(user_id: str) -> dict:
    with _conn() as con:
        search_count = con.execute(
            "SELECT COUNT(*) FROM search_logs WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        doc_count = con.execute(
            "SELECT COUNT(*) FROM documents WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        project_count = con.execute(
            "SELECT COUNT(*) FROM projects WHERE user_id=?", (user_id,)
        ).fetchone()[0]
    return {"search_count": search_count, "document_count": doc_count, "project_count": project_count}
