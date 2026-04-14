import json
from itertools import groupby
from pathlib import Path

from core.utils import load_all_rows

from .models import DashboardRow, DashboardRun, DashboardSummary


def _run_from_row(row: dict) -> DashboardRun | None:
    """Build a DashboardRun from a joined DB row, or None if no run data."""
    if row.get("run_index") is None:
        return None
    scores = row.get("scores") or {}
    if isinstance(scores, str):
        scores = json.loads(scores)
    chat_result = row.get("chat_result")
    if isinstance(chat_result, str):
        chat_result = json.loads(chat_result)
    return DashboardRun(
        index=row["run_index"],
        status=row.get("status") or "pending",
        scores=dict(scores),
        error=row.get("error") or "",
        chat_result=chat_result,
        time_chat_start=row.get("time_chat_start"),
        time_chat_end=row.get("time_chat_end"),
        time_score_start=row.get("time_score_start"),
        time_score_end=row.get("time_score_end"),
    )


def _derive_latest_fields(
    runs: list[DashboardRun | None],
) -> tuple[str, dict[str, float], object | None, str]:
    for r in reversed(runs):
        if r is not None:
            return r.status, dict(r.scores), r.chat_result, r.error
    return "pending", {}, None, ""


def load_dashboard(base_dir: Path) -> DashboardSummary:
    db_path = base_dir / "benchmark.db"
    rows: list[DashboardRow] = []

    if not db_path.exists():
        return DashboardSummary(
            base_dir=base_dir,
            total_jobs=0,
            completed_jobs=0,
            failed_jobs=0,
            pending_jobs=0,
            rows=[],
        )

    all_rows = load_all_rows(db_path)

    for (model, job_id), group in groupby(
        all_rows, key=lambda r: (r["model"], r["job_id"])
    ):
        group_list = list(group)
        summary = group_list[0].get("summary", "")
        runs: list[DashboardRun | None] = []
        for r in group_list:
            runs.append(_run_from_row(r))

        status, scores, chat_result, error = _derive_latest_fields(runs)
        rows.append(
            DashboardRow(
                model=model,
                job_id=job_id,
                summary=summary,
                runs=runs,
                status=status,
                scores=scores,
                chat_result=chat_result,
                error=error,
            )
        )

    rows.sort(key=lambda r: (r.model, r.job_id))

    completed_jobs = sum(1 for row in rows if row.status == "completed")
    failed_jobs = sum(1 for row in rows if row.status == "failed")
    pending_jobs = len(rows) - completed_jobs - failed_jobs

    return DashboardSummary(
        base_dir=base_dir,
        total_jobs=len(rows),
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        pending_jobs=pending_jobs,
        rows=rows,
    )
