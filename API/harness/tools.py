"""API harness: tool schemas, dispatch, and error reporting to the model."""
from shared import tools as domain
from shared.tools import ToolError

from API.harness import say

FILE = "tools.py"
MAX_RESULT_CHARS = 2000  # hard cap so one tool call can never blow up the context

SCHEMAS = [
    {
        "name": "add_book",
        "description": "Add a book to the reading list, or update only the given fields if the title already exists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "author": {"type": "string"},
                "status": {"type": "string", "enum": ["want", "reading", "done"]},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                "genre": {"type": "string"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_books",
        "description": "List books on the reading list. Rows: id|title|author|status|rating|genre.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["want", "reading", "done"]},
                "genre": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
        },
    },
    {
        "name": "search_books",
        "description": "Search the external book catalog by title, author or genre. Rows: title|author|year|genre.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_preference",
        "description": "Remember a reading preference or decision (e.g. dislikes horror). Saving the same topic again overwrites it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "stance": {"type": "string", "enum": ["like", "dislike"]},
                "note": {"type": "string"},
            },
            "required": ["topic", "stance"],
        },
    },
]

DISPATCH = {
    "add_book": domain.add_book,
    "list_books": domain.list_books,
    "search_books": domain.search_books,
    "save_preference": domain.save_preference,
}


def run_tool_calls(content) -> list[dict]:
    """Run every tool_use block of one model response.

    Returns all tool_result blocks together, so the caller can send them
    back in a single user message.
    """
    results = []
    for block in content:
        if block.type != "tool_use":
            continue
        fn = DISPATCH.get(block.name)
        is_error = False
        if fn is None:
            out, is_error = f"unknown tool '{block.name}'", True
        else:
            try:
                out = fn(**block.input)
            except ToolError as e:
                out, is_error = str(e), True
            except TypeError as e:  # wrong or missing arguments
                out, is_error = f"bad arguments: {e}", True
        if len(out) > MAX_RESULT_CHARS:
            out = out[:MAX_RESULT_CHARS] + "\n(truncated)"
        say(FILE, f"{block.name}({block.input}) -> {'ERROR ' if is_error else ''}{len(out)} chars")
        result = {"type": "tool_result", "tool_use_id": block.id, "content": out}
        if is_error:
            result["is_error"] = True
        results.append(result)
    return results