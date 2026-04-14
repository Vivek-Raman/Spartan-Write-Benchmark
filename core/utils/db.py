import json
import sqlite3
from pathlib import Path
from typing import Any

from .metadata import BenchmarkMetadata

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    job_id TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    UNIQUE(model, job_id)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    run_index INTEGER NOT NULL,
    run_workspace TEXT,
    model TEXT NOT NULL,
    session_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    time_chat_start TEXT,
    time_chat_end TEXT,
    time_score_start TEXT,
    time_score_end TEXT,
    chat_result TEXT,
    scores TEXT,
    extra TEXT,
    UNIQUE(job_id, run_index)
);
"""


def init_db(db_path: Path) -> None:
    """Create the benchmark database and tables if they don't exist."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.close()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def upsert_job(db_path: Path, model: str, job_id: str, summary: str = "") -> int:
    """Insert or update a job row; return its row id."""
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO jobs (model, job_id, summary) VALUES (?, ?, ?) "
            "ON CONFLICT(model, job_id) DO UPDATE SET summary = excluded.summary",
            (model, job_id, summary),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM jobs WHERE model = ? AND job_id = ?",
            (model, job_id),
        ).fetchone()
        return row["id"]
    finally:
        conn.close()


def upsert_run(
    db_path: Path,
    job_row_id: int,
    run_index: int,
    model: str,
    session_id: str,
    metadata: BenchmarkMetadata,
    run_workspace: str,
) -> None:
    """Insert or replace a run row from a BenchmarkMetadata instance."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO runs
                (job_id, run_index, run_workspace, model, session_id,
                 status, error,
                 time_chat_start, time_chat_end,
                 time_score_start, time_score_end,
                 chat_result, scores, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, run_index) DO UPDATE SET
                run_workspace = excluded.run_workspace,
                model = excluded.model,
                session_id = excluded.session_id,
                status = excluded.status,
                error = excluded.error,
                time_chat_start = excluded.time_chat_start,
                time_chat_end = excluded.time_chat_end,
                time_score_start = excluded.time_score_start,
                time_score_end = excluded.time_score_end,
                chat_result = excluded.chat_result,
                scores = excluded.scores,
                extra = excluded.extra
            """,
            (
                job_row_id,
                run_index,
                run_workspace,
                model,
                session_id,
                metadata.status,
                metadata.error,
                metadata.time_chat_start,
                metadata.time_chat_end,
                metadata.time_score_start,
                metadata.time_score_end,
                json.dumps(metadata.chat_result) if metadata.chat_result is not None else None,
                json.dumps(metadata.scores) if metadata.scores else None,
                json.dumps(metadata.extra) if metadata.extra else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_job_run(
    db_path: Path, model: str, job_id: str, run_index: int
) -> dict[str, Any] | None:
    """Load a single run as a dict compatible with BenchmarkMetadata.from_dict."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT j.summary, r.*
            FROM runs r
            JOIN jobs j ON j.id = r.job_id
            WHERE j.model = ? AND j.job_id = ? AND r.run_index = ?
            """,
            (model, job_id, run_index),
        ).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)
    finally:
        conn.close()


def get_job_summary(db_path: Path, model: str, job_id: str) -> str:
    """Return the summary for a job, or empty string if not found."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT summary FROM jobs WHERE model = ? AND job_id = ?",
            (model, job_id),
        ).fetchone()
        return row["summary"] if row else ""
    finally:
        conn.close()


def load_all_rows(db_path: Path) -> list[dict[str, Any]]:
    """Return all runs joined with their job info for the dashboard."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT j.model, j.job_id, j.summary, r.*
            FROM jobs j
            LEFT JOIN runs r ON r.job_id = j.id
            ORDER BY j.model, j.job_id, r.run_index
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a DB row into a flat dict, JSON-decoding stored blobs."""
    d = dict(row)
    for key in ("chat_result", "scores", "extra"):
        if d.get(key) is not None:
            d[key] = json.loads(d[key])
    return d
