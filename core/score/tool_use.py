from core.utils import BenchmarkMetadata


def evaluate_tool_use(context: dict, metadata: BenchmarkMetadata) -> None:
    tool_use_score = 0
    for message in metadata.chat_result["messages"]:
        if message["type"] == "tool_call":
            tool_use_score += 1
    metadata.scores["tool_use"] = tool_use_score
