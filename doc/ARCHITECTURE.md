# spine — Architecture walkthrough

This is the code-level companion to [`spine-spec.md`](spine-spec.md). The spec
explains *why* spine is shaped the way it is; this document traces *how the code
actually fits together* so you can read the whole thing in one sitting before you
clone it. Every reference is `file:line` and clickable.

The whole core is small enough to hold in your head: `agent.py` is ~150 lines,
each tool is ~60, and the provider wrapper is ~50. If a sentence here disagrees
with the code, the code wins — go read it.

---

## 1. The four layers, as files

The spec draws four layers (spec §2). Here is where each one lives:

```
SKILLS / EXTENSIONS   src/spine/skills.py · src/spine/hooks.py · prompts/system.md
        │  a clone registers tools, hooks, prompts here
AGENT CORE            src/spine/agent.py          ← you own this; the loop
        │  calls tools                    │  calls the provider
TOOLS                 src/spine/tools/    PROVIDER (rented)  src/spine/provider.py
  base.py  read.py write.py edit.py bash.py        litellm wrapper: complete()
```

- **Provider** (`provider.py`) — the only file that imports an LLM SDK, and it
  does so *lazily* (`provider.py:67`) so the rest of the core — and the whole test
  suite — imports and runs without `litellm` installed. Exposes one function
  upward: `complete(model, messages, tools) -> Completion`.
- **Agent core** (`agent.py`) — owns the turn lifecycle, conversation state, tool
  dispatch, argument validation, and hook invocation. Knows nothing about which
  model it talks to or what any tool does.
- **Tools** (`tools/`) — four objects satisfying the `Tool` protocol
  (`tools/base.py:34`). Pure functions of their validated args.
- **Skills / extensions** — the customization surface a clone touches; the layers
  below are touched rarely or never.

---

## 2. The data shapes that cross the seams

Four small types are the entire vocabulary passed between layers. Learn these and
the loop reads itself.

| Type | Defined in | What it is |
|---|---|---|
| `Completion` | `provider.py:32` | One assistant turn: `content: str \| None` + `tool_calls: list[ToolCall]`. `to_message()` renders it as an OpenAI-style assistant dict for the transcript. |
| `ToolCall` | `provider.py:23` | One requested invocation: `id`, `name`, and `arguments` **already parsed** to a dict. |
| `ToolResult` | `tools/base.py:18` | What a tool returns: `output: str` (what the model sees), `is_error: bool` (recoverable failure, still returned not raised), `terminate: bool` (the stop hint). |
| `BeforeToolCall` | `hooks.py:23` | A hook's pre-execution decision: allow (default), `blocked` + `message`, or replacement `args`. |

The transcript itself (`agent.messages`, `agent.py:56`) is a plain
`list[dict]` in OpenAI message format — `system`, `user`, `assistant` (possibly
with `tool_calls`), and `tool` (a result, keyed by `tool_call_id`). Nothing
proprietary lives in the transcript; the `terminate` hint is runtime-only and
never serialized.

---

## 3. One turn, traced through the code

`Agent.run()` (`agent.py:63`) is the entry point. It appends the user message,
fires `session_start`, and hands off to `_loop()` (`agent.py:93`) inside a
`try/finally` so `session_end` always runs.

`_loop()` is the lifecycle from spec §5. Each iteration:

1. **Call the model.** `self.complete(model, messages, tool_schemas)`
   (`agent.py:95`). `tool_schemas` (`agent.py:76`) renders the four tools as
   OpenAI function schemas straight from their Pydantic `parameters`
   (`model_json_schema()`), so the schema the model sees and the schema used to
   validate its reply are *the same object* — they cannot drift.
2. **Record the assistant turn.** `completion.to_message()` is appended to the
   transcript (`agent.py:96`).
3. **Done?** If there are no tool calls, return the text — the turn is over
   (`agent.py:99`).
4. **Otherwise, run every tool call.** For each, `_dispatch()` returns a
   `ToolResult`, which is appended as a `tool` message keyed by `call.id`
   (`agent.py:103`), and its `terminate` vote is collected.
5. **Batch terminate check.** If the batch is non-empty and *every* result voted
   to terminate, return (`agent.py:115`). Otherwise loop — the model now sees all
   the results and continues.
6. **Safety valve.** After `max_iterations` (default 50) the loop returns a
   "stopped" message instead of spinning forever (`agent.py:118`).

### Two concrete shapes of a turn

**Text-only (no tools):** `complete` → `Completion(content="...", tool_calls=[])`
→ step 3 returns immediately. One provider call, done.

**Tool-using:** `complete` → `Completion(content=None, tool_calls=[write(...)])`
→ step 4 runs `write`, appends its result → loop → `complete` sees the result →
`Completion(content="wrote the file")` → step 3 returns. Two provider calls.

Both shapes are exactly the tests in `tests/test_loop.py:35` and `:45`, driven by
a stub `complete` so no network is involved.

---

## 4. `_dispatch` — the safety-critical path

`_dispatch()` (`agent.py:125`) turns one `ToolCall` into one `ToolResult`. Its
defining property: **nothing in normal operation raises.** Every failure becomes a
`ToolResult` the model reads next turn, so the model self-corrects instead of the
process crashing. The order is fixed:

1. **Unknown tool?** → error result (`agent.py:133`).
2. **Validate args** against the tool's Pydantic schema (`agent.py:139`). A
   `ValidationError` becomes an error result (`agent.py:141`), *not* an exception —
   this is the "validation-error feedback" rule from spec §5.
3. **`before_tool_call` hook** (`agent.py:143`). If it blocks, return its message
   as an error result; if it supplies replacement `args`, swap them in.
4. **Execute** the tool (`agent.py:149`).
5. **`after_tool_call` hook** (`agent.py:150`) gets the last word — it can annotate
   the result or raise the `terminate` hint.

```
ToolCall ──► known? ──► validate args ──► before hook ──► execute ──► after hook ──► ToolResult
              │ no         │ invalid        │ blocked                     │
              ▼            ▼                ▼                            ▼
           error        error            error                  (annotated) result
```

Read `_dispatch` once and you understand spine's entire error and policy model.

---

## 5. `edit`, in detail

`edit` (`tools/edit.py`) is the tool whose design decides reliability, so it is
worth a paragraph of its own. The mechanic is **exact string replacement with a
uniqueness check** (`tools/edit.py:56`):

- **zero matches** → error: "not found, re-read and try again" (`edit.py:58`)
- **more than one match** → error: "not unique, add surrounding context", with the
  count (`edit.py:64`)
- **exactly one match** → replace and write (`edit.py:71`)

It deliberately is *not* line-ranges (line numbers drift between the model's read
and its write) and *not* diffs (they fail to apply cleanly). The failure modes are
loud and recoverable, and the error text feeds straight back to the model via
`_dispatch`. The three branches are pinned by tests at `tests/test_tools.py:68`,
`:80`, and `:94`. Do not switch the mechanic — see the invariant in
[`CLAUDE.md`](../CLAUDE.md) and the spec §4.

---

## 6. The seams — where a clone docks, with recipes

A clone customizes spine by touching the top layer only. Four extension points,
each with the minimum code:

### Add a tool (still four built-ins; this is a clone's fifth, not the core's)

Anything satisfying the `Tool` protocol (`tools/base.py:34`) works. Register it by
passing it to `Agent(tools=[...])`.

```python
from pydantic import BaseModel, Field
from spine import Agent, default_tools, ToolResult

class HttpGetParams(BaseModel):
    url: str = Field(description="URL to fetch.")

class HttpGet:
    name = "http_get"
    description = "Fetch a URL and return the body."
    parameters = HttpGetParams
    def execute(self, args: HttpGetParams) -> ToolResult:
        import urllib.request
        with urllib.request.urlopen(args.url) as r:   # noqa: S310
            return ToolResult(r.read().decode("utf-8", "replace"))

agent = Agent(model="anthropic/claude-opus-4-8", tools=[*default_tools(), HttpGet()])
```

### Tighten policy with a hook (the *only* place policy belongs)

Subclass `Hooks` (`hooks.py:37`) and override just what you need. The core ships
permissive; this is where a clone adds an allowlist, a confirmation, an `rm -rf`
guard, or audit logging.

```python
from spine.hooks import Hooks, BeforeToolCall

class GuardBash(Hooks):
    def before_tool_call(self, tool, args, agent) -> BeforeToolCall:
        if tool.name == "bash" and "rm -rf" in args.command:
            return BeforeToolCall(blocked=True, message="refused: destructive command")
        return BeforeToolCall()   # allow everything else

agent = Agent(model=..., tools=default_tools(), hooks=GuardBash())
```

`after_tool_call` can set `result.terminate = True` to stop the loop after the
current batch (see `tests/test_loop.py:143`).

### Override the prompt

Pass `system_prompt=...` to `Agent`, or edit `src/spine/prompts/system.md` (loaded
at `agent.py:29`) in the clone.

### Add skills (capability-as-documentation)

`discover_skills` (`skills.py:23`) finds subdirectories of a skills root that
contain a `README.md` and `skills_prompt` (`skills.py:43`) renders a catalogue for
the prompt. The agent reads a skill's README and runs it via `bash`. There is no
plugin protocol — that is the point.

### Swap the provider

Replace `litellm` inside `provider.complete` (`provider.py:57`), or pass any
`complete`-shaped callable as `Agent(complete=...)`. The signature is pinned as
`CompleteFn` (`agent.py:24`); the test stub (`tests/test_loop.py:18`) is the
reference implementation of that shape.

---

## 7. What is deliberately *not* here

Per spec §9, these are kept out of the base by design, each with a known docking
point: MCP, memory/persistence, RAG, graph orchestration, in-core permissions, and
multi-agent orchestration. The last one is the orchestration section in
[`CLAUDE.md`](../CLAUDE.md) and [`../AGENTS.md`](../AGENTS.md): the base ships
single-agent, and because the `Tool` protocol is kept agent-satisfiable
(`tools/base.py:34`), adding sub-agents later is a ~20-line wrapper, not a rewrite.
These all dock at the seams above rather than living in the core — that's the grain
to build with, not a wall.

---

## 8. Reading order

If you are new to the repo, read in this order:

1. [`spine-spec.md`](spine-spec.md) §1 — the philosophy (load-bearing).
2. `src/spine/agent.py` — top to bottom; it is the whole core.
3. `src/spine/tools/edit.py` — the tool that carries the most weight.
4. This document §3–§4 — to see the loop and dispatch traced in place.
5. `tests/test_loop.py` — the loop's behavior, pinned and offline.

Then clone it (spec §11) and build upward.
