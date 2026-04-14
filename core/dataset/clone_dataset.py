import json
import shutil
import importlib.resources
from pathlib import Path
import click

from core.utils import upsert_job


def run_dir_for_index(index: int) -> str:
    return f"run-{index:03d}"


def _ignore_metadata_json(_src: str, names: list[str]) -> list[str]:
    return [n for n in names if n == "metadata.json"]


def prepare_run_workspaces(source: Path, job_root: Path, iterations: int) -> None:
    """Reset ``run-NNN`` trees under ``job_root`` from bundled ``source``, omitting metadata."""
    for i in range(iterations):
        dest = job_root / run_dir_for_index(i)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            dest,
            dirs_exist_ok=True,
            ignore=_ignore_metadata_json,
        )


def clone_dataset(context: dict) -> None:
    dataset_list = context["dataset"]
    db_path = context.get("db_path")
    model_label = context["model"].replace("/", "--")

    with click.progressbar(dataset_list,
                           length=len(dataset_list),
                           update_min_steps=1,
                           label='+ Cloning dataset...') as bar:
        for dataset in bar:
            source = Path(
                importlib.resources.files("core")).parent / "data" / dataset

            if db_path is not None:
                metadata_file = source / "metadata.json"
                summary = ""
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        summary = json.load(f).get("summary", "")
                upsert_job(db_path, model_label, dataset, summary)

    click.echo(f"+ Cloned {len(dataset_list)} items")
