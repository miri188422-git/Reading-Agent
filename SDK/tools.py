
"""SDK tools: thin wrappers around shared domain tools.
# replaces: API/harness/tools.py
"""

from shared import tools as domain
from claude_agent_sdk import tool, create_sdk_mcp_server


@tool(
    "add_book",
    "Add a book to the reading list or update an existing book.",
    {
        "title": str,
        "author": str,
        "status": str,
        "rating": int,
        "genre": str,
    },
)
async def add_book(args: dict) -> dict:
    """# replaces: API/harness/tools.py — add_book dispatch"""
    try:
        result = domain.add_book(
            title=args["title"],
            author=args.get("author", ""),
            status=args.get("status", ""),
            rating=args.get("rating", 0),
            genre=args.get("genre", ""),
        )
        return {"content": [{"type": "text", "text": result}]}
    except domain.ToolError as exc:
        return {"content": [{"type": "text", "text": str(exc)}], "isError": True}


@tool(
    "list_books",
    "List books, optionally filtered by status or genre.",
    {"status": str, "genre": str, "limit": int},
)
async def list_books(args: dict) -> dict:
    """# replaces: API/harness/tools.py — list_books dispatch"""
    try:
        result = domain.list_books(
            status=args.get("status", ""),
            genre=args.get("genre", ""),
            limit=args.get("limit", 10),
        )
        return {"content": [{"type": "text", "text": result}]}
    except domain.ToolError as exc:
        return {"content": [{"type": "text", "text": str(exc)}], "isError": True}


@tool(
    "search_books",
    "Search the external book catalog by title, author, or genre.",
    {"query": str, "limit": int},
)
async def search_books(args: dict) -> dict:
    """# replaces: API/harness/tools.py — search_books dispatch"""
    try:
        result = domain.search_books(
            query=args["query"],
            limit=args.get("limit", 5),
        )
        return {"content": [{"type": "text", "text": result}]}
    except domain.ToolError as exc:
        return {"content": [{"type": "text", "text": str(exc)}], "isError": True}


@tool(
    "save_preference",
    "Save a lasting reading preference, such as liking or disliking a genre.",
    {"topic": str, "stance": str, "note": str},
)
async def save_preference(args: dict) -> dict:
    """# replaces: API/harness/tools.py — save_preference dispatch"""
    try:
        result = domain.save_preference(
            topic=args["topic"],
            stance=args["stance"],
            note=args.get("note", ""),
        )
        return {"content": [{"type": "text", "text": result}]}
    except domain.ToolError as exc:
        return {"content": [{"type": "text", "text": str(exc)}], "isError": True}


reading_server = create_sdk_mcp_server(
    name="reading",
    version="1.0.0",
    tools=[add_book, list_books, search_books, save_preference],
)
