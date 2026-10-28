import json

from shared import tools
from shared.scenario import evaluate, run_scenario
from shared import store


def metrics(**over):
    base = {"text": "", "input_tokens": 10, "cache_read_tokens": 0, "cache_write_tokens": 0,
            "output_tokens": 5, "cache_hit_pct": 0.0, "model_calls": 1, "tools": [],
            "cost_usd": 0.001, "seconds": 0.1}
    return {**base, **over}


def test_state_checks_pass_and_fail_on_saved_state():
    tools.add_book("Dune", status="done", rating=4)
    tools.save_preference("horror", "dislike")
    ok = evaluate({"name": "a", "type": "book", "title": "dune", "status": "done", "rating": 4}, [])
    bad_rating = evaluate({"name": "b", "type": "book", "title": "Dune", "rating": 5}, [])
    missing = evaluate({"name": "c", "type": "book", "title": "Nope"}, [])
    pref_ok = evaluate({"name": "d", "type": "preference", "topic": "Horror", "stance": "dislike"}, [])
    pref_bad = evaluate({"name": "e", "type": "preference", "topic": "horror", "stance": "like"}, [])
    assert [r["passed"] for r in (ok, bad_rating, missing, pref_ok, pref_bad)] == [True, False, False, True, False]


def test_tool_and_reply_checks_use_the_right_turn():
    turns = [metrics(tools=["search_books"], text="found it"),
             metrics(tools=[], text="You said you dislike horror")]
    assert evaluate({"name": "a", "type": "tool_used", "tool": "search_books", "turn": 1}, turns)["passed"]
    assert not evaluate({"name": "b", "type": "tool_used", "tool": "search_books", "turn": 2}, turns)["passed"]
    assert evaluate({"name": "c", "type": "reply_contains", "turn": 2, "any": ["dislike"]}, turns)["passed"]
    assert not evaluate({"name": "d", "type": "reply_contains", "turn": 1, "any": ["dislike"]}, turns)["passed"]


class ScriptedAgent:
    """Fake agent: writes state through the real tools, reports fixed metrics."""

    def __init__(self, session_id):
        self.session_id = session_id

    def run_turn(self, text):
        if text == "add":
            tools.add_book("Dune", status="done")
        return metrics(tools=["add_book"] if text == "add" else [])


SCENARIO = {
    "name": "t",
    "sessions": [{"id": "s1", "turns": ["add"]}, {"id": "s2", "turns": ["noop"]}],
    "checks": [
        {"name": "saved", "type": "book", "title": "Dune", "status": "done"},
        {"name": "early", "type": "book", "title": "Dune", "after_turn": 1},
    ],
}


def test_run_scenario_writes_results_with_checks_and_totals(tmp_path):
    sc = tmp_path / "scenario.json"
    sc.write_text(json.dumps(SCENARIO), encoding="utf-8")
    out_file = tmp_path / "results" / "x.json"
    out = run_scenario(sc, ScriptedAgent, out_file, "x", meta={"model": "m"}, data_root=tmp_path / "data")
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved["checks_passed"] == saved["checks_total"] == 2
    assert saved["model"] == "m"
    assert len(saved["turns"]) == 2
    assert saved["totals"]["model_calls_measured"] is True
    assert out["totals"]["cost_usd"] == 0.002


def test_run_scenario_starts_from_clean_state(tmp_path):
    stale = tmp_path / "data" / "run-x"
    stale.mkdir(parents=True)
    (stale / "books.json").write_text('[{"id": 9, "title": "Old", "author": "", "status": "done", "rating": null, "genre": ""}]')
    sc = tmp_path / "scenario.json"
    sc.write_text(json.dumps({"name": "t", "sessions": [{"id": "s1", "turns": ["noop"]}], "checks": []}))
    run_scenario(sc, ScriptedAgent, tmp_path / "o.json", "x", data_root=tmp_path / "data")
    assert store.load("books", []) == []
    
def test_totals_marks_model_calls_unmeasured_when_any_turn_is_unmeasured():
    from shared.scenario import _totals

    turns = [
        metrics(model_calls=2),
        metrics(model_calls=0, model_calls_measured=False),
    ]

    totals = _totals(turns)

    assert totals["model_calls"] == 2
    assert totals["model_calls_measured"] is False
