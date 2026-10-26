"""Token usage and cost, per model call and per user turn."""

import time

from . import log

# claude-opus-5-5, USD per 1M tokens (cache write = 5-minute TTL)
PRICES = {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00}


def cost(usage: dict) -> float:
    return sum(usage[k] * PRICES[k] for k in PRICES) / 1_000_000


class TokenTracker:
    def __init__(self):
        self.last_context_tokens = 0  # size of the latest prompt + reply, for compaction
        self.turns: list[dict] = []
        self._turn: dict | None = None

    def start_turn(self) -> None:
        self._turn = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0,
                      "model_calls": 0, "tools": [], "_t0": time.perf_counter()}

    def record(self, api_usage) -> None:
        u = {
            "input": api_usage.input_tokens,
            "cache_read": api_usage.cache_read_input_tokens or 0,
            "cache_write": api_usage.cache_creation_input_tokens or 0,
            "output": api_usage.output_tokens,
        }
        for k, v in u.items():
            self._turn[k] += v
        self._turn["model_calls"] += 1
        self.last_context_tokens = sum(u.values())
        log(__file__, f"call {self._turn['model_calls']}: in={u['input']} cache_read={u['cache_read']} "
                      f"cache_write={u['cache_write']} out={u['output']} ${cost(u):.4f}")

    def add_tools(self, names: list[str]) -> None:
        self._turn["tools"].extend(names)

    def end_turn(self) -> dict:
        t = self._turn
        t["seconds"] = round(time.perf_counter() - t.pop("_t0"), 2)
        t["cost_usd"] = round(cost(t), 6)
        prompt = t["input"] + t["cache_read"] + t["cache_write"]
        t["cache_hit_pct"] = round(100 * t["cache_read"] / prompt, 1) if prompt else 0.0
        self.turns.append(t)
        log(__file__, f"turn total: {t['model_calls']} calls, cache hit {t['cache_hit_pct']}%, "
                      f"${t['cost_usd']:.4f}, {t['seconds']}s")
        self._turn = None
        return t
