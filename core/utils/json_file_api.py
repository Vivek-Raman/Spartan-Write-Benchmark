import json
from pathlib import Path


def read_json(file_path: Path) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    json_data = None
    with open(str(file_path), "r") as f:
        json_data = json.load(f)
    return json_data


def write_json(file_path: Path, data: dict) -> None:
    file_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
