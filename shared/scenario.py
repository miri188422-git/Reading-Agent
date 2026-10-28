"""Scenario runner and state-based checks. Shared by API/ and SDK/ so both are judged identically.

An "agent" is any object with run_turn(text) -> dict containing:
  text, input_tokens, cache_read_tokens, cache_write_tokens, output_tokens,
  cache_hit_pct, model_calls, tools, cost_usd, seconds
"""
import json
import os
import shutil
from pathlib import Path

from shared import store


def _book(title: str):
    t = title.strip().lower()
    return next((b for b in store.load("books", []) if b["title"].lower() == t), None)


def evaluate(check: dict, turns: list) -> dict:
    """Run one check against the saved state (and the turn records so far)."""
    kind = check["type"]
    if kind == "book":
        b = _book(check["title"])
        ok = b is not None and all(b.get(k) == check[k] for k in ("status", "rating") if k in check)
        detail = f'found status={b["status"]} rating={b["rating"]}' if b else "book not found"
    elif kind == "preference":
        p = store.load("preferences", {}).get(check["topic"].lower())
        ok = p is not None and p["stance"] == check["stance"]
        detail = f'stance={p["stance"]}' if p else "no preference saved"
    elif kind == "tool_used":
        used = (turns[check["turn"] - 1]["tools"] if "turn" in check
                else [t for x in turns for t in x["tools"]])
        ok = check["tool"] in used
        detail = f"tools={used}"
    elif kind == "reply_contains":
        reply = turns[check["turn"] - 1]["text"].lower()
        hits = [w for w in check["any"] if w.lower() in reply]
        ok = bool(hits)
        detail = f"matched {hits}" if hits else "no keyword in reply"
    else:
        raise ValueError(f"unknown check type '{kind}'")
    return {"name": check["name"], "type": kind, "passed": bool(ok), "detail": detail}


def _totals(turns: list) -> dict:
    s = lambda k: sum(t[k] for t in turns)
    total_in = s("input_tokens") + s("cache_read_tokens") + s("cache_write_tokens")

    return {
        "input_tokens": s("input_tokens"),
        "cache_read_tokens": s("cache_read_tokens"),
        "cache_write_tokens": s("cache_write_tokens"),
        "output_tokens": s("output_tokens"),
        "cache_hit_pct": round(100 * s("cache_read_tokens") / total_in, 1) if total_in else 0.0,
        "model_calls": s("model_calls"),
        "model_calls_measured": all(
            t.get("model_calls_measured", True) for t in turns
        ),
        "cost_usd": round(s("cost_usd"), 6),
        "seconds": round(s("seconds"), 2),
    }

def run_scenario(scenario_path, make_agent, out_path, label: str,
                 meta: dict | None = None, data_root="data") -> dict:
    scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))

    data = Path(data_root) / f"run-{label}"
    if data.exists():
        shutil.rmtree(data)  # every run starts from a clean state
    data.mkdir(parents=True)
    os.environ["READING_AGENT_DATA"] = str(data.resolve())

    turns, results = [], {}
    n = 0
    for session in scenario["sessions"]:
        agent = make_agent(f'{label}-{session["id"]}')  # new instance; state comes from disk
        print(f'[scenario.py] session {session["id"]}: new agent instance')
        for text in session["turns"]:
            n += 1
            print(f"[scenario.py] turn {n}: {text}")
            res = agent.run_turn(text)
            turns.append({"turn": n, "session": session["id"], "user": text, **res})
            for c in scenario["checks"]:
                if c.get("after_turn") == n:
                    results[c["name"]] = evaluate(c, turns)
    for c in scenario["checks"]:
        if "after_turn" not in c:
            results[c["name"]] = evaluate(c, turns)

    checks = [results[c["name"]] for c in scenario["checks"]]
    out = {
        "label": label,
        "scenario": scenario.get("name"),
        **(meta or {}),
        "turns": turns,
        "totals": _totals(turns),
        "checks": checks,
        "checks_passed": sum(c["passed"] for c in checks),
        "checks_total": len(checks),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f'[scenario.py] checks {out["checks_passed"]}/{out["checks_total"]}, '
          f'cost ${out["totals"]["cost_usd"]:.4f}, wrote {out_path}')
    return out