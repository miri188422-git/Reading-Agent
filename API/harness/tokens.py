"""API harness: token usage and cost, per model call and per turn."""
import time

from API.harness import say

FILE = "tokens.py"

# USD per 1M tokens. Verify against the official pricing page before the final run.
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_write": 5.00, "cache_read": 0.20},
}


def usage_to_dict(usage) -> dict:
    """Normalize an SDK usage object into the four numbers we track."""
    return {
        "input": getattr(usage, "input_tokens", 0) or 0,
        "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "output": getattr(usage, "output_tokens", 0) or 0,
    }


def cost_usd(tokens: dict, model: str) -> float:
    p = PRICES[model]
    return (tokens["input"] * p["input"]
            + tokens["output"] * p["output"]
            + tokens["cache_write"] * p["cache_write"]
            + tokens["cache_read"] * p["cache_read"]) / 1_000_000


class TurnMeter:
    """Collects everything about one user turn (one or more model calls)."""

    def __init__(self, model: str):
        self.model = model
        self.tokens = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
        self.calls = 0
        self.tools = []
        self._t0 = time.perf_counter()

    def add_call(self, usage) -> None:
        u = usage_to_dict(usage)
        for k, v in u.items():
            self.tokens[k] += v
        self.calls += 1
        say(FILE, f"call {self.calls}: in={u['input']} cache_read={u['cache_read']} "
                  f"cache_write={u['cache_write']} out={u['output']} (${cost_usd(u, self.model):.4f})")

    def add_tools(self, names) -> None:
        self.tools.extend(names)

    def finish(self) -> dict:
        t = self.tokens
        total_in = t["input"] + t["cache_read"] + t["cache_write"]
        result = {
            "input_tokens": t["input"],
            "cache_read_tokens": t["cache_read"],
            "cache_write_tokens": t["cache_write"],
            "output_tokens": t["output"],
            "cache_hit_pct": round(100 * t["cache_read"] / total_in, 1) if total_in else 0.0,
            "model_calls": self.calls,
            "tools": list(self.tools),
            "cost_usd": round(cost_usd(t, self.model), 6),
            "seconds": round(time.perf_counter() - self._t0, 2),
        }
        say(FILE, f"turn done: {self.calls} calls, ${result['cost_usd']:.4f}, {result['seconds']}s, "
                  f"cache hit {result['cache_hit_pct']}%")
        return result