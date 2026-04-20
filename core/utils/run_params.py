import click


def collect_parameters(context: dict) -> None:
    """Set execution parameters (non-interactive; iterations fixed at 3)."""
    scoring_only = bool(context.get("scoring_only", False))
    context["exec_params"] = {
        "iterations": 3,
        "do_scoring_only": scoring_only,
    }
    click.echo(
        f"+ Execution parameters: iterations=3, scoring_only={scoring_only}"
    )
