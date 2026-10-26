"""Prompt caching: where the cache_control breakpoints go (max 4 per request; we use 2).

The API renders tools -> system -> messages, and a cache hit needs an identical prefix.
  1. end of system   -> caches tools + system (frozen for the whole session)
  2. end of the last message -> the next call reads the whole conversation so far from cache
Markers go on copies only; the stored history never contains them.
Opus 5.5 caches prefixes of 512+ tokens; a cache read costs 0.05x a normal input token.
"""

import copy

from . import log

EPHEMERAL = {"type": "ephemeral"}  # 5-minute TTL


def apply(system: list[dict], messages: list[dict]) -> tuple[list[dict], list[dict]]:
    system = copy.deepcopy(system)
    system[-1]["cache_control"] = EPHEMERAL

    messages = list(messages)
    last = copy.deepcopy(messages[-1])
    if isinstance(last["content"], str):
        last["content"] = [{"type": "text", "text": last["content"]}]
    last["content"][-1]["cache_control"] = EPHEMERAL
    messages[-1] = last

    log(__file__, f"2 breakpoints: system, message #{len(messages)}")
    return system, messages
