"""Claude Agent SDK wrapper.
# replaces: API/agent.py and API/harness/loop.py
"""
import asyncio
import time

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from SDK.tools import reading_server
from shared import store


MODEL = "claude-opus-5-5"
EFFORT = "medium"

SYSTEM_PROMPT = """You are a helpful personal reading-list assistant.

You can add and list books, search the book catalog, and remember reading
preferences using your tools.

Rules:
- Use tools to make changes; never claim a change succeeded unless the tool confirms it.
- Respect saved preferences.
- If a request conflicts with a saved preference, mention the conflict and ask
  whether the user wants to change that preference.
- If the user explicitly changes their mind, update the saved preference.
- Keep answers concise.
- Book statuses: want, reading, done.
"""


def build_memory() -> str:  # replaces: memory.py, context.py
    """Load persisted preferences and books for the current turn."""
    books = store.load("books", [])
    preferences = store.load("preferences", {})

    book_lines = [
        f'{b["title"]}: status={b["status"]}, rating={b.get("rating") or "-"}'
        for b in books[:30]
    ]
    preference_lines = [
        f'{topic}: {item["stance"]}'
        + (f' ({item["note"]})' if item.get("note") else "")
        for topic, item in preferences.items()
    ]

    sections = []
    if book_lines:
        sections.append("Saved books:\n" + "\n".join(book_lines))
    if preference_lines:
        sections.append("Saved preferences:\n" + "\n".join(preference_lines))

    return "\n\n".join(sections) or "No saved reading data yet."


class Agent:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.sdk_session_id = None

    def run_turn(self, user_text: str) -> dict:
        """Run one turn and return the metrics expected by the shared scenario."""
        started = time.perf_counter()
        prompt = (
            f"Current saved memory:\n{build_memory()}\n\n"
            f"User request:\n{user_text}"
        )

        result = asyncio.run(self._query(prompt))

        elapsed = time.perf_counter() - started
        return {
            "text": result["text"],
            "input_tokens": result["input_tokens"],
            "cache_read_tokens": result["cache_read_tokens"],
            "cache_write_tokens": result["cache_write_tokens"],
            "output_tokens": result["output_tokens"],
            "cache_hit_pct": result["cache_hit_pct"],
            "model_calls": result["model_calls"],
            "model_calls_measured": result["model_calls_measured"],
            "tools": result["tools"],
            "cost_usd": result["cost_usd"],
            "seconds": round(elapsed, 3),
        }

    async def _query(self, prompt: str) -> dict:
        options = ClaudeAgentOptions(
            model=MODEL,
            effort=EFFORT,
            system_prompt=SYSTEM_PROMPT,  # replaces: context.py (stable part)
            mcp_servers={"reading": reading_server},  # replaces: tools.py
            allowed_tools=[
                "mcp__reading__add_book",
                "mcp__reading__list_books",
                "mcp__reading__search_books",
                "mcp__reading__save_preference",
            ],
            tools=[],  # no built-in Claude Code tools, only our MCP tools
            strict_mcp_config=True,
            setting_sources=["project"],
            resume=self.sdk_session_id,  # replaces: history.py
        )

        text_parts = []
        tools_used = []
        seen_message_ids = set()
        unnamed_calls = 0
        input_tokens = 0
        cache_read_tokens = 0
        cache_write_tokens = 0
        output_tokens = 0
        cost_usd = 0.0
        final_result = ""

        # caching and compaction are automatic in Claude Code  # replaces: caching.py, compaction.py
        async for message in query(prompt=prompt, options=options):  # replaces: loop.py
            if isinstance(message, AssistantMessage):
                message_id = getattr(message, "message_id", None)
                if message_id is None:
                    unnamed_calls += 1
                else:
                    seen_message_ids.add(message_id)
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        name = block.name.split("__")[-1]
                        if name not in tools_used:
                            tools_used.append(name)

            elif isinstance(message, ResultMessage):
                self.sdk_session_id = message.session_id
                usage = message.usage or {}  # replaces: tokens.py
                input_tokens += usage.get("input_tokens", 0)
                cache_read_tokens += usage.get("cache_read_input_tokens", 0)
                cache_write_tokens += usage.get("cache_creation_input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)
                cost_usd += message.total_cost_usd or 0.0
                final_result = message.result or ""

        denominator = input_tokens + cache_read_tokens + cache_write_tokens
        cache_hit_pct = (
            round(cache_read_tokens / denominator * 100, 2)
            if denominator else 0.0
        )

        return {
            "text": final_result or "\n".join(text_parts).strip(),
            "input_tokens": input_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
            "output_tokens": output_tokens,
            "cache_hit_pct": cache_hit_pct,
            "model_calls": len(seen_message_ids) + unnamed_calls,
            "model_calls_measured": True,
            "tools": tools_used,
            "cost_usd": round(cost_usd, 6),
        }

