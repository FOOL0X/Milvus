import sqlite3
import json
import time
from pathlib import Path
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class SessionStore:
    def __init__(self):
        self._db_path = Path(settings.SESSION_DB_PATH)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id)
            """)
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN title TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            conn.commit()
        finally:
            conn.close()

    def create_session(self, session_id: str, title: str = "") -> str:
        now = time.time()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now, now),
            )
            conn.commit()
            return session_id
        finally:
            conn.close()

    def update_title(self, session_id: str, title: str):
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE sessions SET title = ? WHERE session_id = ?",
                (title, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_history(self, session_id: str) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in rows]
        finally:
            conn.close()

    def add_message(self, session_id: str, role: str, content: str):
        now = time.time()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
            conn.commit()
            self._trim_history(conn, session_id)
            conn.commit()
        finally:
            conn.close()

    def _trim_history(self, conn: sqlite3.Connection, session_id: str):
        max_history = settings.SESSION_MAX_HISTORY
        count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
        if count > max_history:
            conn.execute(
                """DELETE FROM messages WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM messages WHERE session_id = ?
                    ORDER BY id DESC LIMIT ?
                )""",
                (session_id, session_id, max_history),
            )

    def delete_session(self, session_id: str):
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def cleanup_expired(self):
        expire_seconds = settings.SESSION_EXPIRE_SECONDS
        cutoff = time.time() - expire_seconds
        conn = self._get_conn()
        try:
            expired = conn.execute(
                "SELECT session_id FROM sessions WHERE updated_at < ?",
                (cutoff,),
            ).fetchall()
            for row in expired:
                self.delete_session(row["session_id"])
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
        finally:
            conn.close()

    def list_sessions(self) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT session_id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()


session_store = SessionStore()
