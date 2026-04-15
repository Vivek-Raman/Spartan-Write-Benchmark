from collections import defaultdict
from core.utils import BenchmarkMetadata


def evaluate_tool_use(context: dict, metadata: BenchmarkMetadata) -> None:
    tool_use_score: dict[str, int] = defaultdict(int)
    for message in metadata.chat_result["full_state"]["messages"]:
        if message["type"] == "tool":
            tool_use_score[message["name"]] += 1
    metadata.scores["tool_use"] = tool_use_score
