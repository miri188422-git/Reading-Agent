"""Domain tools for the reading agent. Shared by API/ and SDK/.

Every tool returns a short plain string (compact output = fewer tokens).
Failures raise ToolError; each harness decides how to report it to the model.
"""
import json
import re
from pathlib import Path

from shared import store
STATUSES = ("want", "reading", "done")
STANCES = ("like", "dislike")
CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"


class ToolError(Exception):
    """A problem the model can read and recover from."""


def _load_catalog() -> list:
    """The only external read (a file). Tests can replace this function."""
    try:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ToolError(f"catalog unavailable: {e.__class__.__name__}")


def _books() -> list:
    return store.load("books", [])


def _find(books: list, title: str):
    t = title.strip().lower()
    return next((b for b in books if b["title"].lower() == t), None)


def _line(b: dict) -> str:
    rating = b["rating"] if b.get("rating") else "-"
    return f'{b["id"]}|{b["title"]}|{b["author"] or "?"}|{b["status"]}|{rating}|{b.get("genre") or "-"}'


def add_book(title: str, author: str = "", status: str = "",
             rating: int = 0, genre: str = "") -> str:
    """Add a book, or update only the fields given if the title already exists."""
    if not title.strip():
        raise ToolError("title is required")
    if status and status not in STATUSES:
        raise ToolError(f"status must be one of {list(STATUSES)}, got '{status}'")
    if rating and not 1 <= rating <= 5:
        raise ToolError("rating must be 1-5")
    books = _books()
    b = _find(books, title)
    if b:
        if status:
            b["status"] = status
        if author:
            b["author"] = author
        if rating:
            b["rating"] = rating
        if genre:
            b["genre"] = genre.lower()
        store.save("books", books)
        return f"updated {_line(b)}"
    b = {"id": max((x["id"] for x in books), default=0) + 1,
         "title": title.strip(), "author": author, "status": status or "want",
         "rating": rating or None, "genre": genre.lower()}
    books.append(b)
    store.save("books", books)
    return f"added {_line(b)}"


def list_books(status: str = "", genre: str = "", limit: int = 10) -> str:
    """List books, optionally filtered. Format: id|title|author|status|rating|genre"""
    if status and status not in STATUSES:
        raise ToolError(f"status must be one of {list(STATUSES)}, got '{status}'")
    books = _books()
    if status:
        books = [b for b in books if b["status"] == status]
    if genre:
        books = [b for b in books if b.get("genre") == genre.lower()]
    if not books:
        return "no books"
    shown = books[:limit]
    out = "\n".join(_line(b) for b in shown)
    if len(books) > len(shown):
        out += f"\n(+{len(books) - len(shown)} more)"
    return out


def search_books(query: str, limit: int = 5) -> str:
    """EXTERNAL tool (file): search the book catalog by title, author or genre.
    Format: title|author|year|genre"""
    if not query.strip():
        raise ToolError("query is required")
    words = set(re.findall(r"\w+", query.lower()))
    scored = []
    for b in _load_catalog():
        tokens = set(re.findall(r"\w+", f'{b["title"]} {b["author"]} {b["genre"]}'.lower()))
        score = len(words & tokens)  # whole-word matches only
        if score:
            scored.append((score, b))
    if not scored:
        return "no results"
    scored.sort(key=lambda x: -x[0])
    return "\n".join(
        f'{b["title"]}|{b["author"]}|{b["year"]}|{b["genre"]}'
        for _, b in scored[:min(limit, 10)]
    )


def save_preference(topic: str, stance: str, note: str = "") -> str:
    """Remember a reading preference. One entry per topic; saving again overwrites."""
    if not topic.strip():
        raise ToolError("topic is required")
    if stance not in STANCES:
        raise ToolError(f"stance must be one of {list(STANCES)}, got '{stance}'")
    prefs = store.load("preferences", {})
    key = topic.strip().lower()
    prefs[key] = {"stance": stance, "note": note}
    store.save("preferences", prefs)
    return f"saved {stance} {key}"