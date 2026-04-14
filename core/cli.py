import dotenv

dotenv.load_dotenv()

import os
from pathlib import Path
import click

from core.bench import run_benchmarks
from core.utils import locate_server, load_creds, collect_parameters, init_db
from core.dataset import clone_dataset, load_dataset
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
    "Directory to use for benchmarks. Defaults to current working directory.",
)
@click.pass_context
def cli(ctx: click.Context, dir: str | None) -> None:
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["dir"] = dir if dir is not None else os.getcwd()
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
    "--session-id",
    "session_id",
    type=str,
    required=True,
    help="Session ID passed to the server for this benchmark run (must be unique per run).",
)
@click.pass_context
def run(ctx: click.Context, model: str, session_id: str) -> None:
    """Run benchmarks."""
    context = {}
    context["dir"] = Path(ctx.obj.get("dir"))
    context["model"] = model
    context["model_dir"] = context["dir"] / model.replace("/", "--")
    context["session_id"] = session_id
    context["db_path"] = context["dir"] / "benchmark.db"
    init_db(context["db_path"])

    collect_parameters(context)
    locate_server(context)
    load_dataset(context)
    clone_dataset(context)
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
