import importlib.resources
from pathlib import Path
import click


def load_dataset(context: dict) -> None:
    click.echo("+ Loading dataset items...")

    dataset_list = []
    path = Path(importlib.resources.files("core")).parent / "data"
    for dataset in path.iterdir():
        if dataset.is_dir():
            dataset_list.append(dataset.name)
    context['dataset_count'] = len(dataset_list)
    click.echo(f"  + Found {context['dataset_count']} data directories")
    context['dataset'] = dataset_list
