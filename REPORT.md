# Reading Agent: API vs SDK

## Project
A personal reading-list agent built twice:
- `API/`: a custom harness over the raw Anthropic Messages API (8 harness files, one per responsibility; every runtime action prints the file that performed it).
- `SDK/`: the same agent configured on the Claude Agent SDK. Claude Code runs the harness; each replaced file is marked `# replaces: <name>`.
- `shared/`: tools and data used by both versions.

**Agent features.** Tools: `add_book`, `list_books`, `search_books` (external: a local catalog file, `shared/catalog.json`, because the network I work on blocks web APIs), `save_preference`. Memory: books and preferences persist on disk between sessions. Context engineering: only a small `<memory>` block with relevant items is added to each turn. Token optimization: compact tool output and per-turn token/cost metering.

**Setup.** Same model and effort in both versions (`claude-opus-5-5`, medium), same scenario (`scenario.json`: 2 sessions, 7 turns, 8 pass/fail checks, most on persisted state), each run started from clean data. Session 2 is a fresh agent instance that loads state from disk. Offline tests (mocked client, no key): 12 passing.

## Results (one run per configuration)

| | API | SDK (default tools) | SDK (`tools=[]`) |
|---|---:|---:|---:|
| Checks passed | 8/8 | 8/8 | 8/8 |
| Model calls | 14 | 16 | 14 |
| Input tokens (uncached) | 42 | 48 | 38 |
| Cache read tokens | 17,583 | 334,383 | 31,451 |
| Cache write tokens | 3,839 | 11,652 | 5,435 |
| Output tokens | 1,424 | 1,916 | 1,609 |
| Cache hit % | 81.9 | 96.6 | 85.2 |
| Cost (USD) | 0.051 | 0.386 | 0.155 |
| Time (s) | 27.6 | 51.4 | 51.0 |
| Avg context per model call (tokens) | ~1,500 | ~21,700 | ~2,600 |

Raw files: `results/api.json`, `results/sdk_default_tools.json`, `results/sdk.json` (the final SDK version, with the restricted tool list). SDK cost is the `total_cost_usd` reported by the SDK.

## Lines of code per harness part

Counted with the same function for both versions (`shared/loc.py`: non-blank, non-comment lines).

| Harness part | API file | API lines | SDK equivalent |
|---|---|---:|---|
| Agent loop | loop.py | 51 | `query()` loop in `SDK/agent.py` |
| Tools | tools.py | 94 | `SDK/tools.py` (80 lines, `@tool` + MCP server) |
| History | history.py | 66 | `resume=` (one line) |
| Memory | memory.py | 46 | `build_memory()` in `SDK/agent.py` |
| Context | context.py | 43 | `system_prompt=` and the memory block in `SDK/agent.py` |
| Compaction | compaction.py | 45 | automatic (0) |
| Caching | caching.py | 25 | automatic (0) |
| Tokens | tokens.py | 55 | reading `ResultMessage.usage` in `SDK/agent.py` |
| `__init__.py` | | 3 | |
| **Total harness** | | **428** | **220** (`agent.py` 140 + `tools.py` 80) |

`SDK/main.py` is 42 lines of run code and is not part of the harness comparison. Roughly half the code is gone in the SDK version, mostly the loop, history, compaction, caching and token accounting. The tools themselves barely shrank (94 vs 80), because the domain logic is the same.

## Where the SDK used more or fewer tokens, and why

- **More, in total, in every configuration.** With default settings the SDK sent about 21,700 tokens of context per model call, versus about 1,500 in the API version. The SDK loads Claude Code's own system prompt and all of its built-in tool definitions into every call, which my agent never uses. These are cached (hit rate 96.6%), so the cost is paid mostly as cache reads, but the total was still 7.5x the API cost.
- **Restricting the tool list helped a lot.** Adding `tools=[]` (together with `strict_mcp_config=True` and my own system prompt) cut cost by 60% ($0.386 to $0.155) and context per call by about 88%. The remaining gap to the API version (about 3x in cost) is likely the SDK's own system prompt and orchestration overhead; I did not measure that directly.
- **Output tokens were also higher in the SDK** (1,609 to 1,916 vs 1,424), probably because replies are slightly more verbose and the model's habits differ with a different prompt. This is a small effect.
- **Context pruning.** In the API version the `<memory>` block is added only to the current turn and never stored, so context does not pile up. In my SDK version the memory block is part of the prompt and `resume=` keeps it in the session history, so old blocks accumulate. This did not matter in a 7-turn scenario, but it would in a long one.
- **Caching.** The API version's first turn read 1,158 cached tokens because a previous failed run had warmed the cache minutes earlier, so its hit rate is a little flattering.

## What I controlled in the API and lost in the SDK

- Exactly what enters each turn (context.py), what is stored in history, and where cache breakpoints go.
- Per-call visibility: the API version logs tokens and cost for every model call; the SDK gives me only one aggregate `ResultMessage` per turn, so I measured model calls by counting distinct assistant messages.
- Compaction threshold and strategy, and how tool errors return to the model (`is_error`).
- Cost: the same agent was 3x to 7.5x more expensive in the SDK, and slower per turn (the SDK starts Claude Code for each query).

A real bug showed why control matters: the first real API run failed on turn 2 with a thinking-block signature error. Thinking blocks are signed against the content before them, and I had sent turn 1 with a `<memory>` block that history does not store. The offline tests could not catch this because the mock client does not validate signatures. The fix was to drop thinking blocks of finished turns when building each request (`drop_old_thinking` in `context.py`). In the SDK this class of problem does not exist, because Claude Code manages the history itself.

## Which version I would choose

For this agent, a personal tool used occasionally, I would choose the **SDK with the restricted tool list**. It needs half the code, has no loop, history, caching or compaction code to maintain or debug, and about $0.15 per 7-turn scenario is acceptable for personal use. I would choose the **API version** if cost or latency mattered (it was about 3x cheaper and about 2x faster here), if many users shared the agent, or if I needed per-call control of context.

## Limitations

- One run per configuration, so cost and timing are indicative, not statistically established.
- An earlier SDK run (7/8 checks, $0.63) was discarded because my SDK wrapper did not record tool calls; the failed check was a measurement bug, not an agent failure. It was fixed before the runs reported here.
- The external tool is a local catalog file, not a live web API.
- The SDK cost is the SDK's reported figure and may not match actual billing on a login-based plan.
