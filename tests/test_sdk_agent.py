from unittest.mock import patch

from SDK.agent import Agent


def test_sdk_agent_marks_model_call_count_as_unmeasured():
    agent = Agent("test-session")

    fake_result = {
        "text": "test",
        "input_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": 0,
        "cache_hit_pct": 0.0,
        "model_calls": 0,
        "model_calls_measured": False,
        "tools": [],
        "cost_usd": 0.0,
    }

    with patch.object(agent, "_query", return_value=fake_result):
        result = agent.run_turn("hello")

    assert result["model_calls"] == 0
    assert result["model_calls_measured"] is False