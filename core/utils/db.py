import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
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

CREATE TABLE IF NOT EXISTS run_tool_usage (
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    call_count INTEGER NOT NULL,
    PRIMARY KEY (run_id, tool_name)
);
"""


def _split_scores_and_tool_use(
    scores: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    """Return scores blob for the `runs.scores` column and per-tool counts."""
    if not scores:
        return None, {}
    raw = dict(scores)
    tu = raw.pop("tool_use", None)
    tool_use: dict[str, int] = {}
    if isinstance(tu, dict):
        for name, count in tu.items():
            try:
                n = int(count)
            except (TypeError, ValueError):
                continue
            if n > 0:
                tool_use[str(name)] = n
    rest = raw
    if not rest:
        return None, tool_use
    return rest, tool_use


def _replace_run_tool_usage(
    conn: sqlite3.Connection, run_id: int, tool_use: dict[str, int]
) -> None:
    conn.execute("DELETE FROM run_tool_usage WHERE run_id = ?", (run_id,))
    for tool_name, call_count in tool_use.items():
        conn.execute(
            """
            INSERT INTO run_tool_usage (run_id, tool_name, call_count)
            VALUES (?, ?, ?)
            """,
            (run_id, tool_name, call_count),
        )


def _tool_usage_by_run_id(
    conn: sqlite3.Connection, run_ids: list[int]
) -> dict[int, dict[str, int]]:
    if not run_ids:
        return {}
    placeholders = ",".join("?" * len(run_ids))
    rows = conn.execute(
        f"""
        SELECT run_id, tool_name, call_count
        FROM run_tool_usage
        WHERE run_id IN ({placeholders})
        """,
        run_ids,
    ).fetchall()
    out: dict[int, dict[str, int]] = defaultdict(dict)
    for r in rows:
        out[r["run_id"]][r["tool_name"]] = int(r["call_count"])
    return dict(out)


@contextmanager
def _connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    """Create the benchmark database and tables if they don't exist."""
    with _connection(db_path) as conn:
        conn.executescript(_SCHEMA)


def flush_model_data(db_path: Path, model: str, model_dir: Path) -> None:
    """Remove all DB rows and the on-disk directory for a model."""
    with _connection(db_path) as conn:
        conn.execute(
            "DELETE FROM runs WHERE job_id IN "
            "(SELECT id FROM jobs WHERE model = ?)",
            (model,),
        )
        conn.execute("DELETE FROM jobs WHERE model = ?", (model,))
        conn.commit()

    import shutil
    if model_dir.exists():
        shutil.rmtree(model_dir)


def upsert_job(db_path: Path, model: str, job_id: str, summary: str = "") -> int:
    """Insert or update a job row; return its row id."""
    with _connection(db_path) as conn:
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
    scores_blob, tool_use = _split_scores_and_tool_use(metadata.scores)
    with _connection(db_path) as conn:
        conn.execute("BEGIN")
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
                json.dumps(scores_blob) if scores_blob else None,
                json.dumps(metadata.extra) if metadata.extra else None,
            ),
        )
        run_row = conn.execute(
            "SELECT id FROM runs WHERE job_id = ? AND run_index = ?",
            (job_row_id, run_index),
        ).fetchone()
        if run_row is None:
            conn.rollback()
            raise RuntimeError(
                f"upsert_run: missing runs row for job_id={job_row_id} run_index={run_index}"
            )
        _replace_run_tool_usage(conn, int(run_row["id"]), tool_use)
        conn.commit()


def load_job_run(
    db_path: Path, model: str, job_id: str, run_index: int
) -> dict[str, Any] | None:
    """Load a single run as a dict compatible with BenchmarkMetadata.from_dict."""
    with _connection(db_path) as conn:
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
        d = _row_to_dict(row)
        run_id = d.get("id")
        if run_id is not None:
            tu_rows = conn.execute(
                "SELECT tool_name, call_count FROM run_tool_usage WHERE run_id = ?",
                (run_id,),
            ).fetchall()
            if tu_rows:
                tool_use = {t["tool_name"]: int(t["call_count"]) for t in tu_rows}
                scores = d.get("scores")
                if not isinstance(scores, dict):
                    scores = {}
                scores = dict(scores)
                scores["tool_use"] = tool_use
                d["scores"] = scores
        return d


def get_job_summary(db_path: Path, model: str, job_id: str) -> str:
    """Return the summary for a job, or empty string if not found."""
    with _connection(db_path) as conn:
        row = conn.execute(
            "SELECT summary FROM jobs WHERE model = ? AND job_id = ?",
            (model, job_id),
        ).fetchone()
        return row["summary"] if row else ""


def load_all_rows(db_path: Path) -> list[dict[str, Any]]:
    """Return all runs joined with their job info for the dashboard."""
    with _connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT j.model, j.job_id, j.summary, r.*
            FROM jobs j
            LEFT JOIN runs r ON r.job_id = j.id
            ORDER BY j.model, j.job_id, r.run_index
            """
        ).fetchall()
        result = [dict(r) for r in rows]
        run_ids = [r["id"] for r in result if r.get("id") is not None]
        by_run = _tool_usage_by_run_id(conn, run_ids)
        for r in result:
            rid = r.get("id")
            r["tool_use"] = dict(by_run.get(int(rid), {})) if rid is not None else {}
        return result


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a DB row into a flat dict, JSON-decoding stored blobs."""
    d = dict(row)
    for key in ("chat_result", "scores", "extra"):
        if d.get(key) is not None:
            d[key] = json.loads(d[key])
    return d
