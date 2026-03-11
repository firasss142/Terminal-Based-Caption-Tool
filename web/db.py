"""SQLite persistence layer for job history."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Docker/HuggingFace Spaces: /data is the persistent volume.
# Local dev: fall back to <project_root>/data/ when /data is not writable.
DB_PATH = Path(os.environ.get("DATA_DIR", "/data")) / "jobs.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name TEXT NOT NULL,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                srt_content TEXT NOT NULL
            )
        """)


def save_job(job_name: str, srt_content: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO jobs (job_name, srt_content, completed_at) VALUES (?, ?, ?)",
            (job_name, srt_content, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def list_jobs() -> list:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, job_name, status, created_at, completed_at "
            "FROM jobs ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_srt(job_id: int) -> str | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT srt_content FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return row[0] if row else None


def delete_job(job_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cur.rowcount > 0
