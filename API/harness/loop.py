"""The agent loop: call the model; while stop_reason == "tool_use", run the tools,
send ALL their results back in one user message, and call again."""

from . import log, tools

MAX_MODEL_CALLS = 12  # safety net against a runaway loop within one user turn


def run_turn(call_model, history, tracker) -> str:
    for _ in range(MAX_MODEL_CALLS):
        response = call_model(history.messages())
        log(__file__, f"stop_reason={response.stop_reason}")

        # Store the assistant turn exactly as received (thinking blocks included):
        # it must go back unchanged on every later request.
        content = [b.model_dump(mode="json", exclude_none=True) for b in response.content]
        history.append({"role": "assistant", "content": content})

        tool_uses = [b for b in content if b["type"] == "tool_use"]
        if response.stop_reason == "tool_use":
            tracker.add_tools([b["name"] for b in tool_uses])
            history.append({"role": "user", "content": tools.run_all(tool_uses)})
            continue

        if tool_uses:  # e.g. cut off by max_tokens: every tool_use still needs a tool_result
            history.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b["id"], "is_error": True,
                 "content": f"not executed: response stopped ({response.stop_reason})"}
                for b in tool_uses
            ]})
        if response.stop_reason == "refusal":
            return "(the model declined this request)"
        return "".join(b["text"] for b in content if b["type"] == "text")

    log(__file__, f"stopped after {MAX_MODEL_CALLS} model calls")
    return f"(stopped: more than {MAX_MODEL_CALLS} model calls in one turn)"
