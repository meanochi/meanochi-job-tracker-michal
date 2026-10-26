"""Shared test setup: offline, no API key, every test gets its own empty data directory.

FakeClient replays scripted responses built from real anthropic types, and records
every request so tests can check exactly what the harness sent.
"""

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from anthropic.types import TextBlock, ThinkingBlock, ToolUseBlock, Usage

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "API")]


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("JOB_TRACKER_DIR", str(tmp_path / "data"))
    return tmp_path / "data"


def text(t: str) -> TextBlock:
    return TextBlock(type="text", text=t)


def tool(id: str, name: str, **input) -> ToolUseBlock:
    return ToolUseBlock(type="tool_use", id=id, name=name, input=input)


def thinking(sig: str = "sig") -> ThinkingBlock:
    return ThinkingBlock(type="thinking", thinking="", signature=sig)


def response(stop_reason: str, *blocks, input=100, output=20, cache_read=0, cache_write=0):
    usage = Usage(input_tokens=input, output_tokens=output,
                  cache_read_input_tokens=cache_read, cache_creation_input_tokens=cache_write)
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks), usage=usage)


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[dict] = []
        self.messages = self  # so client.messages.create(...) works

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        if not self.responses:
            raise AssertionError("FakeClient ran out of scripted responses")
        return self.responses.pop(0)


def without_cache_control(obj):
    if isinstance(obj, dict):
        return {k: without_cache_control(v) for k, v in obj.items() if k != "cache_control"}
    if isinstance(obj, list):
        return [without_cache_control(x) for x in obj]
    return obj
