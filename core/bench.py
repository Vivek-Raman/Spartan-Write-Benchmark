import asyncio
import importlib.resources
import time
from datetime import datetime, timezone
from pathlib import Path

import click

from core.dataset import (
    prepare_run_workspaces,
    prepare_single_run_workspace,
    run_dir_for_index,
)
from core.score import score_benchmark
from core.utils import (
    BenchmarkMetadata,
    do_chat,
    get_job_summary,
    load_job_run,
    upsert_job,
    upsert_run,
)

_MAX_BENCHMARK_ATTEMPTS = 3
_RETRY_SLEEP_SEC = 60


def run_benchmarks(context: dict) -> None:
    params = context.get("exec_params", {})
    iterations = params.get("iterations", 1)
    do_scoring_only = params.get("do_scoring_only", False)

    with click.progressbar(context["dataset"],
                           length=context["dataset_count"],
                           update_min_steps=1,
                           label='+ Running benchmarks...') as bar:
        for dir_name in bar:
            click.echo("")  # new line
            data_dir = context["model_dir"] / "data" / dir_name
            source = Path(importlib.resources.files("core")).parent / "data" / dir_name
            prepare_run_workspaces(source, data_dir, iterations)
            for run_index in range(iterations):
                for attempt in range(1, _MAX_BENCHMARK_ATTEMPTS + 1):
                    if attempt > 1:
                        click.echo(
                            f"    + Attempt {attempt}/{_MAX_BENCHMARK_ATTEMPTS} "
                            f"after {_RETRY_SLEEP_SEC}s sleep..."
                        )
                        time.sleep(_RETRY_SLEEP_SEC)
                        if not do_scoring_only:
                            prepare_single_run_workspace(source, data_dir, run_index)
                    ok = asyncio.run(
                        _do_benchmark(context, data_dir, dir_name, run_index)
                    )
                    if ok:
                        break
    click.echo(
        "+ Benchmarking complete. Please run the dashboard to view the results."
    )


def _metadata_for_run(
    context: dict, job_id: str, run_index: int, summary: str, do_scoring_only: bool
) -> BenchmarkMetadata:
    """Build a BenchmarkMetadata instance for this execution (fresh chat or scoring-only)."""
    if do_scoring_only:
        model_label = context["model"].replace("/", "--")
        existing = load_job_run(
            context["db_path"], model_label, job_id, run_index
        )
        if existing is None:
            raise ValueError(
                f"Scoring-only requires an existing run for {job_id} run_index={run_index}"
            )
        return BenchmarkMetadata.from_dict(existing)
    return BenchmarkMetadata(summary=summary)


async def _do_benchmark(
    context: dict, data_dir: Path, job_id: str, run_index: int
) -> bool:
    params = context.get("exec_params", {})
    do_scoring_only = params.get("do_scoring_only", False)

    model = context["model"]
    db_path = context["db_path"]
    model_label = model.replace("/", "--")

    summary = get_job_summary(db_path, model_label, job_id)
    job_row_id = upsert_job(db_path, model_label, job_id, summary)
    metadata = _metadata_for_run(context, job_id, run_index, summary, do_scoring_only)
    click.echo(f"  + Test: {summary}")

    run_workspace = data_dir / run_dir_for_index(run_index)

    try:
        if not do_scoring_only:
            prompt = (run_workspace / "prompt.txt").read_text().strip()
            metadata.time_chat_start = _get_timestamp()
            metadata.chat_result = do_chat(
                context, str(run_workspace.resolve()), prompt, run_index
            )
            metadata.time_chat_end = _get_timestamp()

        metadata.time_score_start = _get_timestamp()
        score_benchmark(context, metadata)
        metadata.time_score_end = _get_timestamp()
        metadata.status = "completed"
    except Exception as e:
        click.echo(f"    + Error: {e}")
        metadata.error = str(e)
        metadata.status = "failed"
    finally:
        upsert_run(
            db_path,
            job_row_id,
            run_index,
            model_label,
            context.get("session_id", ""),
            metadata,
            run_dir_for_index(run_index),
        )
    return metadata.status == "completed"


def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
