# CLAUDE.md — spine

Spine is a minimal Python agent backbone: a language model, four tools, and a
loop. It is a foundation to be **cloned**, not a product. The authoritative
design rationale and full spec live in **`spine-spec.md`** — read it before any
structural change. This file is the short, always-on rule layer.

## Prime directives (do not violate without an explicit instruction to)

- Keep the core tiny. Capability belongs in a clone, not in the base.
- The model gets **exactly four tools**: `read`, `write`, `edit`, `bash`. Do not
  add a fifth. `bash` is the escape hatch for everything else.
- **Own the loop.** It is hand-written (~150–200 lines). Do not introduce an
  agent framework (LangChain / LangGraph) into the core.
- **Rent the provider layer.** All LLM calls go through `litellm` behind
  `provider.py`'s `complete()`. The core never imports a provider SDK directly.
- **Seams over features.** Invest in clean interfaces, not speculative capability.
- Tool args are **Pydantic-validated before `execute()`**; a validation failure is
  *returned to the model as the tool result*, never raised.

## Architecture (detail in `spine-spec.md` §2)

- `provider.py` — rented litellm wrapper: `complete(model, messages, tools)`
- `agent.py` — the loop, conversation state, tool dispatch, hooks
- `tools/` — `read`, `write`, `edit`, `bash`; each implements the `Tool` protocol
- `hooks.py` — `before`/`after_tool_call`, session lifecycle; **ships PERMISSIVE**
- `skills.py` — skill discovery/loading seam

## Tool invariants

- `edit` uses **exact string replacement**: `old_string` must match exactly once.
  Zero matches or multiple matches → return an error to the model so it retries.
  Never silently edit. Do **not** switch to line-ranges or diffs.
- `write` clobbers; prefer `edit` for existing files.
- `bash` runs as the launching user with a timeout. No in-core permission checks.

## Security

- No permission system in the core. Isolation is **external** (sandbox/container).
- The `before_tool_call` hook is the ONLY place policy may live, and it ships
  permissive. Do not bake allowlists or confirmations into the core itself.

## The Tool protocol must stay agent-satisfiable

- A `Tool` is: `name`, `description`, Pydantic `parameters`, `execute() -> result`.
- Never add anything that would prevent an `Agent` from being wrapped as a `Tool`.
  This is what keeps orchestration a ~20-line future wrapper instead of a rewrite.

## ⟶ ORCHESTRATION SWITCH — STATUS: DISABLED

```
WHILE DISABLED (current):
  - Spine is single-agent. One loop, one model, four tools.
  - DO NOT build a multi-agent subsystem.
  - DO NOT hand any agent another agent as a tool.
  - DO NOT add scheduling, inter-agent messaging, shared state,
    fan-out/fan-in, or supervisor/handoff protocols.
  - Keep the Tool protocol agent-satisfiable (see above).

TO ENABLE — change "STATUS: DISABLED" to "STATUS: ENABLED" above, then:
  1. Add agent_as_tool(agent) -> Tool (~20 lines): execute() runs the
     child agent's loop on args["task"], returns its final message.
  2. Give a parent agent one or more child agents in its tool list.
  3. Add deferred pieces (parallel, shared state, handoff) ONLY if a
     real workflow needs them — the minimum, not the set.
  4. Mind cost/latency: each nested agent call burns a full conversation.
```

## Build & test

- Install (incl. dev tools): `uv sync --extra dev`  (or `pip install -e ".[dev]"`)
- Test: `pytest`  — no API key needed; the loop test drives a stubbed provider,
  and `provider.py` imports `litellm` lazily so the suite runs offline.
- Run the example: `python examples/minimal_agent.py "<task>"`
  (needs a provider key in the env, e.g. `ANTHROPIC_API_KEY`; pick a model with
  `--model`). The default model is `anthropic/claude-opus-4-8`.
- Lint / format: `ruff check` / `ruff format`

## Style

- Python 3.12+. Type hints everywhere. Pydantic for schemas.
- This is a reference codebase meant to be **read**. Keep functions small and
  obvious; prefer clarity over cleverness. No premature abstraction.
