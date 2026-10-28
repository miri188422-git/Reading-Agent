"""API harness: context-window management. Summarize the whole conversation past a threshold."""
import json

from API.harness import say

FILE = "compaction.py"

COMPACT_AT_TOKENS = 30_000  # context size of the last model call that triggers compaction

SUMMARY_SYSTEM = (
    "You compress a conversation between a user and a reading-list assistant into a short "
    "summary the assistant will continue from. Keep: the user's stated tastes and decisions, "
    "books discussed with their status and rating, requests still open, and the user's language. "
    "Drop greetings and chit-chat. Write plain text, under 250 words."
)


def transcript(messages: list) -> str:
    """Compact plain-text rendering of a conversation, including tool calls and results."""
    lines = []
    for m in messages:
        c = m["content"]
        if isinstance(c, str):
            lines.append(f'{m["role"]}: {c}')
            continue
        for b in c:
            t = b.get("type")
            if t == "text":
                lines.append(f'{m["role"]}: {b["text"]}')
            elif t == "tool_use":
                lines.append(f'tool call: {b["name"]}({json.dumps(b["input"], ensure_ascii=False)})')
            elif t == "tool_result":
                lines.append(f'tool result: {b["content"]}')
    return "\n".join(lines)


def maybe_compact(client, model: str, history, context_tokens: int, meter,
                  extra: dict | None = None, threshold: int = COMPACT_AT_TOKENS) -> bool:
    """If the last call's context was over the threshold, summarize and reset the live history."""
    if context_tokens < threshold:
        return False
    say(FILE, f"context {context_tokens} tokens >= {threshold}: summarizing {len(history.messages)} messages")
    resp = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": transcript(history.messages)}],
        **(extra or {}),
    )
    meter.add_call(resp.usage)  # the summary call is a real model call; it is counted and billed
    summary = "".join(b.text for b in resp.content if b.type == "text").strip()
    history.compact(summary)
    return True