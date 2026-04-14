from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class DashboardRun:
    """One benchmark iteration (metadata.json runs[i])."""

    index: int
    status: str
    scores: dict[str, float]
    error: str
    chat_result: Any | None
    time_chat_start: Optional[str] = None
    time_chat_end: Optional[str] = None
    time_score_start: Optional[str] = None
    time_score_end: Optional[str] = None


@dataclass
class DashboardRow:
    model: str
    job_id: str
    summary: str
    runs: list[DashboardRun | None]
    status: str
    scores: dict[str, float]
    chat_result: Any | None
    error: str

    def non_null_run_count(self) -> int:
        return sum(1 for r in self.runs if r is not None)


@dataclass
class DashboardSummary:
    base_dir: Path
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    rows: list[DashboardRow]
