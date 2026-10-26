"""The API agent: wires the harness parts together. One Agent = one session."""

from datetime import datetime

import anthropic

from harness import caching, compaction, context, log, loop, tools
from harness.history import History
from harness.tokens import TokenTracker
from shared.jobs import data_dir

MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TOKENS = 16000


class Agent:
    def __init__(self, client=None, session_id: str | None = None,
                 compact_threshold: int = compaction.DEFAULT_THRESHOLD):
        self.client = client or anthropic.Anthropic()
        self.session_id = session_id or datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.compact_threshold = compact_threshold
        self.history = History(data_dir() / "sessions" / f"{self.session_id}.jsonl")
        self.tracker = TokenTracker()
        # A resumed session reuses its stored system prompt, so the prefix stays identical.
        if self.history.system is None:
            self.history.set_system(context.build_system())
        self.system = self.history.system
        log(__file__, f"session {self.session_id} ready")

    def _call_model(self, messages: list[dict]):
        system, messages = caching.apply(self.system, messages)
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=tools.SCHEMAS,
            messages=messages,
            output_config={"effort": EFFORT},
        )
        self.tracker.record(response.usage)
        return response

    def ask(self, user_text: str) -> dict:
        self.tracker.start_turn()
        if compaction.should_compact(self.tracker.last_context_tokens, self.compact_threshold):
            compaction.compact(self._call_model, self.history)
        first = not self.history.messages()  # memory goes into the session's first message only
        self.history.append(context.build_user_turn(user_text, first_in_session=first))
        reply = loop.run_turn(self._call_model, self.history, self.tracker)
        return {"reply": reply, **self.tracker.end_turn()}
