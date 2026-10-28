"""API harness: conversation history, append-only JSONL on disk (one file per session).

Compaction is also append-only: a summary record marked "_compaction" is added,
and on load only the records from the last such marker onward are used.
"""
import json

from shared import store

from API.harness import say

FILE = "history.py"


def to_plain(content):
    """Turn SDK response blocks into plain dicts that are safe to store and resend."""
    if isinstance(content, str):
        return content
    out = []
    for b in content:
        if isinstance(b, dict):
            out.append(b)
        elif b.type == "text":
            out.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        else:  # e.g. thinking blocks: keep them exactly as the API returned them
            out.append(b.model_dump(exclude_none=True))
    return out


def _has_tool_use(msg: dict) -> bool:
    c = msg["content"]
    return msg["role"] == "assistant" and isinstance(c, list) and any(
        b.get("type") == "tool_use" for b in c
    )


class History:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.path = store.data_dir() / "history" / f"{session_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.messages = self._load()

    def _load(self) -> list:
        if not self.path.exists():
            say(FILE, f"new session '{self.session_id}'")
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        start = 0
        for i, r in enumerate(records):
            if r.get("_compaction"):
                start = i  # only the latest summary onward is live context
        msgs = [{"role": r["role"], "content": r["content"]} for r in records[start:]]
        if msgs and _has_tool_use(msgs[-1]):
            msgs.pop()  # dangling tool call from a crash; the file itself is untouched
            say(FILE, "dropped a dangling tool call from the end of the history")
        say(FILE, f"resumed session '{self.session_id}' with {len(msgs)} messages")
        return msgs

    def _write(self, record: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def append(self, role: str, content) -> dict:
        msg = {"role": role, "content": to_plain(content)}
        self._write(msg)
        self.messages.append(msg)
        say(FILE, f"appended {role} message ({len(self.messages)} total)")
        return msg

    def compact(self, summary: str) -> None:
        """Replace the live context with one summary message (the file is only appended to)."""
        msg = {"role": "user",
               "content": f"<conversation_summary>\n{summary}\n</conversation_summary>"}
        self._write({**msg, "_compaction": True})
        self.messages = [msg]
        say(FILE, "wrote compaction record; live context is now 1 message")