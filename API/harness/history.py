"""Conversation history: an append-only JSONL file per session.

Each line is one event:
  {"type": "system", "system": [...]}        the session's frozen system prompt (first line)
  {"type": "message", "message": {...}}      one user/assistant message, exactly as sent
  {"type": "compaction", "summary": "..."}   from here on, the summary replaces older messages

Nothing is ever rewritten, so a resumed session sends byte-identical history
(which keeps the prompt cache and Opus 5.5's preserved-thinking check happy).
"""

import json
from pathlib import Path

from . import log


class History:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []
        if path.exists():
            with path.open(encoding="utf-8") as f:
                self.events = [json.loads(line) for line in f if line.strip()]
        log(__file__, f"{path.name}: loaded {len(self.events)} events")

    def _write(self, event: dict) -> None:
        line = json.dumps(event, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        self.events.append(json.loads(line))  # keep the in-memory copy identical to the disk copy

    @property
    def system(self) -> list[dict] | None:
        return next((e["system"] for e in self.events if e["type"] == "system"), None)

    def set_system(self, system: list[dict]) -> None:
        self._write({"type": "system", "system": system})
        log(__file__, "saved frozen system prompt")

    def append(self, message: dict) -> None:
        self._write({"type": "message", "message": message})
        log(__file__, f"appended {message['role']} message ({len(self.messages())} in context)")

    def add_compaction(self, summary: str) -> None:
        self._write({"type": "compaction", "summary": summary})
        log(__file__, "appended compaction marker")

    def messages(self) -> list[dict]:
        """The messages to send: everything after the last compaction, led by its summary."""
        start, summary = 0, None
        for i, e in enumerate(self.events):
            if e["type"] == "compaction":
                start, summary = i + 1, e["summary"]
        msgs = [e["message"] for e in self.events[start:] if e["type"] == "message"]
        if summary is not None:
            text = f"<summary of earlier conversation>\n{summary}\n</summary of earlier conversation>"
            msgs.insert(0, {"role": "user", "content": [{"type": "text", "text": text}]})
        return msgs
