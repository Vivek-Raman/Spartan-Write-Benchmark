import sys
from pathlib import Path

from streamlit.web import cli as stcli

from .loader import load_dashboard
from .models import DashboardRow, DashboardRun, DashboardSummary
from .render import render_dashboard

__all__ = [
    "DashboardRow",
    "DashboardRun",
    "DashboardSummary",
    "load_dashboard",
    "render_dashboard",
    "run_dashboard_app",
]


def main() -> None:
    """Entry point for the dashboard CLI (e.g. `dashboard` or `benchmark dashboard`)."""
    script_path = Path(__file__).resolve().parent / "app.py"
    sys.argv = [
        "streamlit", "run", str(script_path),
        "--server.headless", "true",
        "--", *sys.argv[1:]
    ]
    raise SystemExit(stcli.main())
