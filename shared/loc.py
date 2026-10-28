"""Lines-of-code counting, used for both harnesses so the comparison is fair.

A line counts if it is not blank and not a pure comment. Docstrings count as code lines.
"""
from pathlib import Path


def count_lines(path) -> int:
    text = Path(path).read_text(encoding="utf-8")
    return sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))


def count_dir(directory, pattern: str = "*.py") -> dict:
    """{file stem: lines, ..., 'total': lines} for every matching file in a directory."""
    counts = {p.stem: count_lines(p) for p in sorted(Path(directory).glob(pattern))}
    counts["total"] = sum(counts.values())
    return counts