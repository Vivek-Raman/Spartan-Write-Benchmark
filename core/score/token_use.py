from core.utils import BenchmarkMetadata


def evaluate_token_use(context: dict, metadata: BenchmarkMetadata) -> None:
    """
    Aggregate token usage from AI messages in the chat result and store it on
    ``metadata.scores``.

    Extracts fields from:
        metadata.chat_result["full_state"]["messages"][...]["usage_metadata"]

    For all messages where ``type == "ai"`` it sums:
    - input_tokens
    - reasoning tokens from output_token_details["reasoning"]
    - output_tokens (excluding reasoning tokens)
    """

    chat_result = metadata.chat_result or {}
    full_state = chat_result.get("full_state") or {}
    messages = full_state.get("messages") or []

    total_input_tokens = 0
    total_output_tokens = 0
    total_reasoning_tokens = 0

    for message in messages:
        if message.get("type") != "ai":
            continue

        usage = message.get("usage_metadata") or {}
        input_tokens = usage.get("input_tokens") or 0
        output_tokens = usage.get("output_tokens") or 0

        output_details = usage.get("output_token_details") or {}
        reasoning_tokens = output_details.get("reasoning") or 0

        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        total_reasoning_tokens += reasoning_tokens

    metadata.scores["input_tokens"] = total_input_tokens
    metadata.scores["reasoning_tokens"] = total_reasoning_tokens
    metadata.scores["output_tokens"] = total_output_tokens
