from types import SimpleNamespace as N

from API.harness.loop import Agent
from shared import store


def usage(i=100, cr=0, cw=0, o=50):
    return N(input_tokens=i, cache_read_input_tokens=cr,
             cache_creation_input_tokens=cw, output_tokens=o)


def text_resp(text):
    return N(content=[N(type="text", text=text)], stop_reason="end_turn", usage=usage())


def tool_resp(*calls):
    blocks = [N(type="tool_use", id=f"tu{i}", name=n, input=inp) for i, (n, inp) in enumerate(calls)]
    return N(content=blocks, stop_reason="tool_use", usage=usage())


class FakeClient:
    """Stands in for anthropic.Anthropic(): returns scripted responses, records requests."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = self  # so client.messages.create(...) works

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def test_tool_turn_saves_state_and_keeps_history_plain():
    client = FakeClient([
        tool_resp(("add_book", {"title": "Dune", "status": "done"})),
        text_resp("Added Dune."),
    ])
    agent = Agent("s1", client=client)
    out = agent.run_turn("I finished Dune")

    assert out["model_calls"] == 2
    assert out["tools"] == ["add_book"]
    assert store.load("books", [])[0]["title"] == "Dune"
    assert agent.history.messages[0]["content"] == "I finished Dune"  # no <memory> stored
    assert client.calls[0]["messages"][0]["content"][0]["text"].startswith("<memory>")
    assert client.calls[0]["extra_body"] == {"output_config": {"effort": "medium"}}
    assert "temperature" not in client.calls[0]


def test_all_tool_results_return_in_one_message_and_errors_are_flagged():
    client = FakeClient([
        tool_resp(("add_book", {"title": "A"}), ("add_book", {"title": "B", "status": "bad"})),
        text_resp("ok"),
    ])
    Agent("s1", client=client).run_turn("add two books")

    last = client.calls[1]["messages"][-1]
    assert last["role"] == "user"
    results = last["content"]
    assert [r["type"] for r in results] == ["tool_result", "tool_result"]
    assert "is_error" not in results[0]
    assert results[1]["is_error"] is True


def test_new_agent_instance_resumes_session_from_disk():
    Agent("s1", client=FakeClient([text_resp("hi")])).run_turn("hello")
    again = Agent("s1", client=FakeClient([text_resp("hi again")]))
    assert len(again.history.messages) == 2