from .tool_use import evaluate_tool_use
from .chat_duration import evaluate_chat_duration
from .token_use import evaluate_token_use
from core.utils import BenchmarkMetadata


def score_benchmark(context: dict, metadata: BenchmarkMetadata) -> None:
    metadata.scores = {}
    evaluate_tool_use(context, metadata)
    evaluate_chat_duration(context, metadata)
    evaluate_token_use(context, metadata)


__all__ = ["score_benchmark"]
