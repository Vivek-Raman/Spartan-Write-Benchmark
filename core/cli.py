import dotenv

dotenv.load_dotenv()

import importlib.resources
import os
from datetime import datetime, timezone
from pathlib import Path

import click

from core.bench import run_benchmarks
from core.utils import (
    collect_parameters,
    flush_model_data,
    flush_single_job,
    init_db,
    load_creds,
    locate_server,
)
from core.dataset import register_jobs, load_dataset
from core.dashboard import main as dashboard_main


def _resolve_bundled_job(data_root: Path, job: str) -> str:
    """Return canonical dataset directory name under data_root.

    Accepts a full directory name or a unique prefix (e.g. ``016`` for
    ``016-large-parse-image``).
    """
    exact = data_root / job
    if exact.is_dir():
        return job
    candidates = sorted(
        p.name
        for p in data_root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name.startswith(job)
    )
    if not candidates:
        raise click.ClickException(
            f"Unknown job {job!r}: no directory under bundled data ({data_root}) "
            "matches that name or prefix."
        )
    if len(candidates) > 1:
        raise click.ClickException(
            f"Job prefix {job!r} is ambiguous; matches: {', '.join(candidates)}"
        )
    return candidates[0]


@click.group(invoke_without_command=True)
@click.option(
    "--dir",
    type=click.Path(exists=True,
                    file_okay=False,
                    dir_okay=True,
                    resolve_path=True),
    default=None,
    help=
    "Directory to use for benchmarks. Defaults to ./result if not provided.",
)
@click.pass_context
def cli(ctx: click.Context, dir: str | None) -> None:
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["dir"] = dir if dir is not None else str(
        Path(os.getcwd()) / "result")
    click.echo(f"+ Using directory: {ctx.obj['dir']}")
    if ctx.invoked_subcommand is None:
        click.echo("")
        click.echo(ctx.get_help(), err=True)


@cli.command()
@click.option(
    "--model",
    type=str,
    required=True,
    help=
    "Model name to benchmark (e.g. gpt-4o). Results go under <dir>/<model>/data/.",
)
@click.option(
    "--scoring-only",
    is_flag=True,
    default=False,
    help="Re-score existing chat output only; skip chat and do not clear model results.",
)
@click.pass_context
def run(ctx: click.Context, model: str, scoring_only: bool) -> None:
    """Run benchmarks."""
    model_label = model.replace("/", "--")
    context = {}
    context["dir"] = Path(ctx.obj.get("dir"))
    context["model"] = model
    context["model_dir"] = context["dir"] / model_label
    context["session_id"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context["db_path"] = context["dir"] / "benchmark.db"
    init_db(context["db_path"])
    context["scoring_only"] = scoring_only
    collect_parameters(context)
    if not context.get("exec_params", {}).get("do_scoring_only"):
        flush_model_data(context["db_path"], model_label, context["model_dir"])
    locate_server(context)
    load_dataset(context)
    register_jobs(context)
    load_creds(context)
    run_benchmarks(context)


@cli.command("run-job")
@click.option(
    "--model",
    type=str,
    required=True,
    help=
    "Model name to benchmark (e.g. gpt-4o). Results go under <dir>/<model>/data/.",
)
@click.option(
    "--job",
    type=str,
    required=True,
    help=
    "Bundled dataset dir or unique prefix (e.g. 016 or 016-large-parse-image).",
)
@click.option(
    "--scoring-only",
    is_flag=True,
    default=False,
    help="Re-score existing chat output only; skip chat and do not clear this job's tree.",
)
@click.pass_context
def run_job(ctx: click.Context, model: str, job: str, scoring_only: bool) -> None:
    """Run a single benchmark job without clearing other jobs for this model."""
    data_root = Path(importlib.resources.files("core")).parent / "data"
    job = _resolve_bundled_job(data_root, job)

    model_label = model.replace("/", "--")
    context: dict = {}
    context["dir"] = Path(ctx.obj.get("dir"))
    context["model"] = model
    context["model_dir"] = context["dir"] / model_label
    context["session_id"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context["db_path"] = context["dir"] / "benchmark.db"
    init_db(context["db_path"])
    context["scoring_only"] = scoring_only
    collect_parameters(context)
    if not context.get("exec_params", {}).get("do_scoring_only"):
        flush_single_job(context["db_path"], model_label, job, context["model_dir"])
    locate_server(context)
    context["dataset"] = [job]
    context["dataset_count"] = 1
    register_jobs(context)
    load_creds(context)
    run_benchmarks(context)


@cli.command()
@click.pass_context
def dashboard(ctx: click.Context) -> None:
    """Serve the benchmark dashboard."""
    import sys
    sys.argv = [sys.argv[0], "--dir", str(ctx.obj.get("dir", os.getcwd()))]
    dashboard_main()


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
