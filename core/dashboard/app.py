import argparse
import sys
from pathlib import Path

from streamlit.runtime.scriptrunner import get_script_run_ctx

from core.dashboard.loader import load_dashboard
from core.dashboard.render import render_dashboard


def _parse_streamlit_script_args() -> dict[str, Path]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dir", default=".")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return {"path": Path(args.dir).resolve()}


def run_dashboard_app() -> None:
    script_args = _parse_streamlit_script_args()
    base_dir = script_args["path"]
    summary = load_dashboard(base_dir)
    render_dashboard(summary)


def _is_running_with_streamlit() -> bool:
    return get_script_run_ctx() is not None


if _is_running_with_streamlit():
    run_dashboard_app()
