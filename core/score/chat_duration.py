from datetime import datetime
from core.utils import BenchmarkMetadata


def evaluate_chat_duration(context: dict, metadata: BenchmarkMetadata) -> None:
    if metadata.time_chat_start and metadata.time_chat_end:
        chat_duration = _seconds_between(metadata.time_chat_start,
                                         metadata.time_chat_end)
        metadata.scores["chat_duration"] = chat_duration
    else:
        metadata.scores["chat_duration"] = -1


def _seconds_between(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None

    try:
        start_time = datetime.fromisoformat(start)
        end_time = datetime.fromisoformat(end)
    except ValueError:
        return None

    delta = end_time - start_time
    seconds = delta.total_seconds()
    if seconds < 0:
        return None
    return seconds
