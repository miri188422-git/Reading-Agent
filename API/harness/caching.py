"""API harness: prompt caching. Decides where cache_control breakpoints go.

Breakpoints (3 of the 4 allowed):
  1. last tool schema      -> caches all tool definitions
  2. system prompt block   -> caches tools + system (identical every turn)
  3. last block of the last message -> within one turn, every tool-loop call
     re-reads everything before it

Works on copies: stored history never contains cache_control.
"""
import copy

from API.harness import say

FILE = "caching.py"
CC = {"type": "ephemeral"}


def apply(system: str, tools: list, messages: list):
    """Return (system_blocks, tools, messages) ready to send, with breakpoints set."""
    system_blocks = [{"type": "text", "text": system, "cache_control": CC}]

    tools = copy.deepcopy(tools)
    tools[-1]["cache_control"] = CC

    messages = copy.deepcopy(messages)
    last = messages[-1]
    if isinstance(last["content"], str):
        last["content"] = [{"type": "text", "text": last["content"], "cache_control": CC}]
    else:
        last["content"][-1]["cache_control"] = CC

    say(FILE, "set 3 cache breakpoints: last tool, system prompt, last message block")
    return system_blocks, tools, messages