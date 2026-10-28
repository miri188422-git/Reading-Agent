"""API harness: memory. Where durable state lives and how the relevant part is retrieved.

Memory is two JSON files in the data dir, written by the domain tools:
  preferences.json  decisions and tastes   (save_preference)
  books.json        the reading list       (add_book)
This file is the read side: given a user request, return only what is relevant.
"""
import re

from shared import store

from API.harness import say

FILE = "memory.py"

STOP = {"a", "an", "the", "me", "my", "i", "to", "of", "and", "or", "is", "it", "in",
        "for", "on", "give", "recommend", "suggest", "book", "books", "read", "want"}


def _words(text: str) -> set:
    return set(re.findall(r"\w+", text.lower())) - STOP


def relevant_preferences(query: str, limit: int = 5) -> list:
    q = _words(query)
    hits = []
    for topic, p in store.load("preferences", {}).items():
        if q & _words(f"{topic} {p.get('note', '')}"):
            note = f" ({p['note']})" if p.get("note") else ""
            hits.append(f"{p['stance']} {topic}{note}")
    return hits[:limit]


def relevant_books(query: str, limit: int = 5) -> list:
    q = _words(query)
    scored = []
    for b in store.load("books", []):
        score = len(q & _words(f'{b["title"]} {b["author"]} {b.get("genre", "")} {b["status"]}'))
        if score:
            scored.append((score, b))
    scored.sort(key=lambda x: -x[0])
    return [f'{b["title"]}|{b["author"] or "?"}|{b["status"]}|{b["rating"] or "-"}'
            for _, b in scored[:limit]]


def summary() -> str:
    books = store.load("books", [])
    counts = {s: sum(b["status"] == s for b in books) for s in ("want", "reading", "done")}
    n_prefs = len(store.load("preferences", {}))
    return (f"list: {len(books)} books (want {counts['want']}, reading {counts['reading']}, "
            f"done {counts['done']}); {n_prefs} saved preferences")


def retrieve(query: str) -> dict:
    result = {
        "summary": summary(),
        "preferences": relevant_preferences(query),
        "books": relevant_books(query),
    }
    say(FILE, f"retrieved {len(result['preferences'])} preferences, {len(result['books'])} books for this turn")
    return result