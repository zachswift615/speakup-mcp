"""SQLite history storage for SpeakUp messages."""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional


class HistoryStore:
    """Stores message history in SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".speakup" / "history.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                text TEXT NOT NULL,
                tone TEXT NOT NULL DEFAULT 'neutral',
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                played_at TIMESTAMP,
                duration_ms REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_created
            ON messages(created_at DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_status
            ON messages(status)
        """)
        conn.commit()

    def add_message(
        self,
        project: str,
        text: str,
        tone: str = "neutral"
    ) -> int:
        """Add a message to history. Returns message ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            INSERT INTO messages (project, text, tone, status)
            VALUES (?, ?, ?, 'queued')
            """,
            (project, text, tone)
        )
        conn.commit()
        return cursor.lastrowid

    def mark_playing(self, message_id: int) -> None:
        """Mark a message as currently playing."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE messages SET status = 'playing' WHERE id = ?",
            (message_id,)
        )
        conn.commit()

    def mark_played(self, message_id: int, duration_ms: float) -> None:
        """Mark a message as played."""
        conn = self._get_conn()
        conn.execute(
            """
            UPDATE messages
            SET status = 'played', played_at = ?, duration_ms = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), duration_ms, message_id)
        )
        conn.commit()

    def mark_skipped(self, message_id: int) -> None:
        """Mark a message as skipped (cleared from queue)."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE messages SET status = 'skipped' WHERE id = ?",
            (message_id,)
        )
        conn.commit()

    def mark_queued_as_skipped(self) -> int:
        """Mark all queued messages as skipped. Returns count."""
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE messages SET status = 'skipped' WHERE status = 'queued'"
        )
        conn.commit()
        return cursor.rowcount

    def get_recent(self, limit: int = 50) -> list[dict]:
        """Get recent messages."""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT id, project, text, tone, status, created_at, played_at, duration_ms
            FROM messages
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_queued(self) -> list[dict]:
        """Get all queued messages in order."""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT id, project, text, tone, status, created_at
            FROM messages
            WHERE status = 'queued'
            ORDER BY created_at ASC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_playing(self) -> Optional[dict]:
        """Get currently playing message, if any."""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT id, project, text, tone, status, created_at
            FROM messages
            WHERE status = 'playing'
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def cleanup_old(self, days: int = 7) -> int:
        """Delete messages older than N days. Returns count deleted."""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            DELETE FROM messages
            WHERE created_at < datetime('now', ?)
            """,
            (f"-{days} days",)
        )
        conn.commit()
        return cursor.rowcount
