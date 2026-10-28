"""API version: builds the agent (harness + shared domain code) for the scenario runner."""
from API.harness.loop import Agent


def make_agent(session_id: str) -> Agent:
    """A fresh agent instance. State (history, books, preferences) is loaded from disk."""
    return Agent(session_id)