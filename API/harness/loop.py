"""API harness: the agent loop. Runs while stop_reason == "tool_use"."""
import anthropic

from API.harness import caching, compaction, context, say
from API.harness.history import History
from API.harness.tokens import TurnMeter, usage_to_dict
from API.harness.tools import SCHEMAS, run_tool_calls

FILE = "loop.py"
MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TOKENS = 8000  # thinking tokens are billed and counted as output
MAX_STEPS = 8      # safety cap on model calls inside one turn

# Effort is the only thinking control on Opus 5.5. Sent via extra_body so it works
# regardless of SDK version. No temperature/top_p/top_k are sent.
EXTRA = {"extra_body": {"output_config": {"effort": EFFORT}}}


class Agent:
    def __init__(self, session_id: str, client=None):
        self.client = client or anthropic.Anthropic()  # key comes from ANTHROPIC_API_KEY
        self.history = History(session_id)

    def _request_messages(self, turn_idx: int, augmented: str) -> list:
        """History as stored, except this turn's user message carries the <memory> block."""
        msgs = list(self.history.messages)
        msgs[turn_idx] = {"role": "user", "content": augmented}
        msgs = list(self.history.messages)
        msgs[turn_idx] = {"role": "user", "content": augmented}
        return context.drop_old_thinking(msgs, turn_idx)
        
    def run_turn(self, user_text: str) -> dict:
        meter = TurnMeter(MODEL)
        augmented = context.build_turn_content(user_text)
        self.history.append("user", user_text)  # stored plain: context does not pile up
        turn_idx = len(self.history.messages) - 1
        last_context = 0
        text = ""

        for step in range(1, MAX_STEPS + 1):
            system, tools, messages = caching.apply(
                context.build_system(), SCHEMAS, self._request_messages(turn_idx, augmented))
            say(FILE, f"model call {step}: {len(messages)} messages, effort={EFFORT}")
            resp = self.client.messages.create(
                model=MODEL, max_tokens=MAX_TOKENS, system=system,
                tools=tools, messages=messages, **EXTRA)
            meter.add_call(resp.usage)
            u = usage_to_dict(resp.usage)
            last_context = u["input"] + u["cache_read"] + u["cache_write"]
            self.history.append("assistant", resp.content)
            text = "".join(b.text for b in resp.content if b.type == "text")

            if resp.stop_reason != "tool_use":
                break
            meter.add_tools([b.name for b in resp.content if b.type == "tool_use"])
            results = run_tool_calls(resp.content)
            self.history.append("user", results)  # ALL tool_results in a single message
        else:
            say(FILE, f"stopped after {MAX_STEPS} model calls without a final answer")

        compaction.maybe_compact(self.client, MODEL, self.history, last_context, meter, extra=EXTRA)
        return {"text": text, **meter.finish()}