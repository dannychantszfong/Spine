# Working in this repo — keeping the grain

This repo is a clone of spine, a foundation meant to be **read** and **built on**.
As you grow it into your own agent, most changes land at the seams and the core
stays tiny and obvious — that's the grain worth keeping. The full reasoning lives
in [`CLAUDE.md`](CLAUDE.md), [`AGENTS.md`](AGENTS.md), and
[`doc/spine-spec.md`](doc/spine-spec.md). This file is the short checklist to run a
change against before you commit it.

## The grain — keep these unless you've deliberately decided otherwise

- [ ] **Still exactly four tools** — `read`, `write`, `edit`, `bash`. No fifth.
      New capability is a clone's tool or a `bash` invocation, not a core tool.
- [ ] **The loop is still hand-written** (`src/spine/agent.py`). No agent
      framework (LangChain / LangGraph) in the core.
- [ ] **The provider layer is still rented** — every LLM call goes through
      `provider.complete()`, and `litellm` is imported nowhere else (and lazily,
      so the core imports without it).
- [ ] **Tool args are Pydantic-validated before `execute()`**, and a validation
      failure is *returned to the model as a tool result*, never raised. The same
      goes for `edit`'s not-found / not-unique cases.
- [ ] **`edit` is still exact string replacement** with a uniqueness check. Not
      line-ranges. Not diffs. Zero or multiple matches return an error.
- [ ] **No permission system in the core.** Policy lives only in the
      `before_tool_call` hook, which ships permissive.
- [ ] **The `Tool` protocol stays agent-satisfiable** (`name`, `description`,
      Pydantic `parameters`, `execute() -> ToolResult`). Nothing should prevent an
      `Agent` from one day being wrapped as a `Tool`.
- [ ] **Still single-agent, unless you've chosen sub-agents on purpose.** The base
      ships one loop, one model, four tools. If your agent needs sub-agents, add
      them deliberately, following the orchestration section in `CLAUDE.md` /
      `AGENTS.md` (wrap an agent as a tool; decide nesting depth, budget, and who
      terminates) — a considered addition, not an accidental one.

## Style

- Python 3.12+. Type hints everywhere. Pydantic for schemas.
- Keep functions small and obvious; clarity over cleverness. No premature
  abstraction. If a reader can't hold a file in their head, it's too big.
- Match the surrounding code's comment density and naming. The module docstrings
  explain *why*; keep that voice.

## Before you commit

```bash
uv sync --extra dev      # first time only
ruff format              # format
ruff check               # lint
pytest                   # 16 tests, all offline (no API key needed)
```

- [ ] Tests pass, and new behavior has a test. The loop is tested with a **stubbed
      provider** (`tests/test_loop.py`) — never add a test that makes a real API
      call.
- [ ] `edit`'s match / no-match / multi-match branches stay covered if you touch
      it (`tests/test_tools.py`).
- [ ] Docs that name code stay true: if you move a symbol referenced by
      `doc/ARCHITECTURE.md` (it uses `file:line` links), update the reference.

## Adding capability the right way

You almost never need to touch the core. Add to the seams instead — there are
copy-pasteable recipes in [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md#6-the-seams--where-a-clone-docks-with-recipes):
a new tool, a policy hook, a prompt override, a skill, or a swapped provider. If
you find yourself editing `agent.py` to add a feature, stop and check whether a
hook or a tool would do it without enlarging the core.
