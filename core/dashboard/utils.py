from core.utils import BenchmarkMetadata

from .models import DashboardRow, DashboardRun


def dashboard_run_from_metadata(index: int, meta: BenchmarkMetadata) -> DashboardRun:
    return DashboardRun(
        index=index,
        status=meta.status or "pending",
        scores=dict(meta.scores or {}),
        error=meta.error or "",
        chat_result=meta.chat_result,
        time_chat_start=meta.time_chat_start,
        time_chat_end=meta.time_chat_end,
        time_score_start=meta.time_score_start,
        time_score_end=meta.time_score_end,
    )


def row_from_raw_metadata(model: str, job_id: str, raw: dict) -> DashboardRow:
    """Build a DashboardRow including per-run entries; latest fields from last non-null run."""
    if "runs" not in raw:
        raise ValueError("metadata.json must include a top-level 'runs' array")
    raw_runs = raw["runs"]
    if not isinstance(raw_runs, list):
        raise ValueError("'runs' must be a JSON array")

    root = {k: v for k, v in raw.items() if k != "runs"}
    runs: list[DashboardRun | None] = []
    for i, slot in enumerate(raw_runs):
        if slot is None:
            runs.append(None)
        elif isinstance(slot, dict):
            merged = {**slot, **root}
            meta = BenchmarkMetadata.from_dict(merged)
            runs.append(dashboard_run_from_metadata(i, meta))
        else:
            runs.append(None)

    status, scores, chat_result, error = _derive_latest_fields(runs)
    summary = raw.get("summary", "") or ""

    return DashboardRow(
        model=model,
        job_id=job_id,
        summary=summary,
        runs=runs,
        status=status,
        scores=scores,
        chat_result=chat_result,
        error=error,
    )


def _derive_latest_fields(
    runs: list[DashboardRun | None],
) -> tuple[str, dict[str, float], object | None, str]:
    for r in reversed(runs):
        if r is not None:
            return (
                r.status,
                dict(r.scores),
                r.chat_result,
                r.error,
            )
    return "pending", {}, None, ""
