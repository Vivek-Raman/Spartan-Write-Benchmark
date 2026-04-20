import click


def collect_parameters(context: dict) -> None:
    """Prompt the CLI user for execution parameters and store in context['exec_params']."""
    click.echo("+ Execution parameters:")
    iterations = click.prompt("  Number of iterations", type=int, default=1)
    do_scoring_only = click.confirm("  Do scoring only (skip chat)?", default=False)

    context["exec_params"] = {
        "iterations": iterations,
        "do_scoring_only": do_scoring_only,
    }
