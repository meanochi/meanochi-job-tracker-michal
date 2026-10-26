"""Context window: once the conversation passes a token threshold, summarize ALL of it.

"Simple" compaction - the whole history becomes one summary message, and nothing older is
replayed. That is the shape that stays valid under Opus 5.5's preserved thinking (keeping a
verbatim tail of old turns would replay thinking blocks whose prefix changed).
It only runs at the start of a user turn, never in the middle of a tool round.
"""

from . import log

DEFAULT_THRESHOLD = 30_000  # tokens in the last request's prompt + its reply

SUMMARY_REQUEST = (
    "Summarize this conversation for your own future reference, so you can continue it "
    "without the earlier messages. Keep: the user's preferences and decisions (latest value "
    "wins), every application discussed with its current status, and open next steps. "
    "Plain text, under 200 words. Reply with the summary only and do not call any tools."
)


def should_compact(context_tokens: int, threshold: int) -> bool:
    if context_tokens > threshold:
        log(__file__, f"context {context_tokens} > threshold {threshold}: compacting")
        return True
    return False


def compact(call_model, history) -> str:
    """call_model(messages) -> response; it applies the same system/tools/caching as a normal call."""
    messages = history.messages() + [
        {"role": "user", "content": [{"type": "text", "text": SUMMARY_REQUEST}]}
    ]
    response = call_model(messages)
    summary = "".join(b.text for b in response.content if b.type == "text").strip()
    history.add_compaction(summary)
    log(__file__, f"summary: {len(summary)} chars replaces {len(messages) - 1} messages")
    return summary
