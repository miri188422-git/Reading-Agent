import asyncio

from SDK.tools import add_book, list_books, save_preference
from shared import store


def test_sdk_tools_save_and_retrieve_data(tmp_path, monkeypatch):
    monkeypatch.setenv("READING_AGENT_DATA", str(tmp_path))

    added = asyncio.run(
        add_book.handler({"title": "Dune", "status": "done", "rating": 5})
    )
    assert "Dune" in added["content"][0]["text"]

    listed = asyncio.run(
        list_books.handler({"status": "done"})
    )
    assert "Dune" in listed["content"][0]["text"]

    saved = asyncio.run(
        save_preference.handler({
            "topic": "horror",
            "stance": "dislike",
            "note": "Prefers to avoid horror books",
        })
    )
    assert "saved" in saved["content"][0]["text"].lower()

    books = store.load("books", [])
    assert len(books) == 1
    assert books[0]["title"] == "Dune"
    assert books[0]["rating"] == 5

    preferences = store.load("preferences", {})
    assert preferences["horror"]["stance"] == "dislike"


def test_sdk_tool_reports_invalid_book_status(tmp_path, monkeypatch):
    monkeypatch.setenv("READING_AGENT_DATA", str(tmp_path))

    result = asyncio.run(
        add_book.handler({"title": "Example", "status": "invalid"})
    )

    assert result.get("isError") is True
    assert "status" in result["content"][0]["text"].lower()