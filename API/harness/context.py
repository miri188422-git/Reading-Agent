"""API harness: context engineering. What goes into each turn, and what does not.

Stable part  : SYSTEM_PROMPT (identical every turn, so it can be cached).
Per-turn part: a small <memory> block prepended to the current user message only.
               It is never written to history, so context does not pile up.
"""
from API.harness import memory, say

FILE = "context.py"

SYSTEM_PROMPT = """You are a personal reading-list assistant.
Tools: add_book, list_books, search_books (external catalog), save_preference.
Rules:
- Reply in the user's language. Keep answers short.
- When the user states a lasting taste or decision (likes/dislikes a genre, author or topic), call save_preference.
- When the user mentions reading, wanting to read, or rating a book, call add_book.
- Use search_books to find or recommend books; do not invent titles.
- The <memory> block lists saved facts relevant to this request. If the request contradicts a saved preference, say so explicitly and ask whether to proceed or update the preference. Do not silently ignore it.
- Do not repeat the memory block back to the user."""


def build_system() -> str:
    return SYSTEM_PROMPT


def build_turn_content(user_text: str) -> str:
    """The user message for this turn: a compact memory block plus the user's own words."""
    mem = memory.retrieve(user_text)
    lines = [mem["summary"]]
    if mem["preferences"]:
        lines.append("preferences: " + "; ".join(mem["preferences"]))
    if mem["books"]:
        lines.append("related books (title|author|status|rating):\n" + "\n".join(mem["books"]))
    block = "<memory>\n" + "\n".join(lines) + "\n</memory>"
    content = f"{block}\n\n{user_text}"
    say(FILE, f"built turn context: {len(block)} chars of memory + {len(user_text)} chars of user text")
    return content


def drop_old_thinking(messages: list, current_idx: int) -> list:
    """Thinking blocks are signed against the exact content before them. Finished
    turns were sent with a <memory> block that history does not store, so their
    signatures no longer match. Drop them; the current turn keeps its own."""
    out = []
    for i, m in enumerate(messages):
        c = m["content"]
        if i < current_idx and m["role"] == "assistant" and isinstance(c, list):
            kept = [b for b in c if b.get("type") not in ("thinking", "redacted_thinking")]
            if kept:
                m = {"role": m["role"], "content": kept}
        out.append(m)
    return out
