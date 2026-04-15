import dotenv

dotenv.load_dotenv()

import os
from datetime import datetime, timezone
from pathlib import Path

import click

from core.bench import run_benchmarks
from core.utils import (
    collect_parameters,
    flush_model_data,
    init_db,
    load_creds,
    locate_server,
)
from core.dataset import register_jobs, load_dataset
from core.dashboard import main as dashboard_main


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
@click.pass_context
def run(ctx: click.Context, model: str) -> None:
    """Run benchmarks."""
    model_label = model.replace("/", "--")
    context = {}
    context["dir"] = Path(ctx.obj.get("dir"))
    context["model"] = model
    context["model_dir"] = context["dir"] / model_label
    context["session_id"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context["db_path"] = context["dir"] / "benchmark.db"
    init_db(context["db_path"])
    collect_parameters(context)
    if not context.get("exec_params", {}).get("do_scoring_only"):
        flush_model_data(context["db_path"], model_label, context["model_dir"])
    locate_server(context)
    load_dataset(context)
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
