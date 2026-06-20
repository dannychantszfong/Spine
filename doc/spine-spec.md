# Spine — Agent Backbone Specification

> **Working name: `spine`** (a backbone). Rename freely — the name appears only in
> the package path and a few imports.

Spine is a minimal, Python agent foundation. It is not a product and not a
framework. It is the smallest correct core you clone to build a real agent on
top of — a data-analysis agent, a writing agent, whatever comes next. The core
gives a language model four tools and a loop. Everything domain-specific is added
by the clone, not baked into the base.

This document is the spec **and** the orientation. Future-you reads this before
cloning. A coding agent working inside the repo reads this (and `CLAUDE.md` /
`AGENTS.md`) to learn the grain it's building with — what the foundation is, why
it's shaped this way, and where new capability attaches.

---

## 1. Philosophy

These are the principles. They are load-bearing — every later decision is
downstream of them.

**Tiny core, four primitives.** The model gets exactly four tools: `read`,
`write`, `edit`, `bash`. That is the whole backbone. We resist adding a fifth
until a real agent proves it cannot be served by the four.

**`bash` is the escape hatch.** The reason four tools is enough: anything without
a dedicated tool (grep, git, curl, run tests, move files, install a package) the
model does through the shell. `read`/`write`/`edit` exist only because those
operations benefit from being structured and safe rather than shelled out.

**Own the loop, rent the provider layer.** The agent loop is ~150–200 lines of
Python and is the thing you must understand line-by-line, so you write it
yourself. The multi-provider LLM normalization (Anthropic vs OpenAI vs Google) is
pure plumbing that churns constantly, so you rent it (`litellm`) and stay out of
SDK-maintenance hell.

**Seams over features.** We invest effort in *clean interfaces between layers*,
not in pre-built features. A good seam costs almost nothing today and lets heavy
machinery (orchestration, memory, RAG, a graph runtime) dock on later without a
rewrite. This is how we get most of the "future is easy" benefit without paying
the framework tax now.

**Build for optionality.** Adding is cheap; removing is expensive. A small core
you fully understand can grow into anything. A comprehensive framework you
committed to is painful to back out of. Because the future use cases are
genuinely unknown, the most valuable property of this foundation is that it
*doesn't foreclose* anything.

**Orchestration is recursion, not a layer.** An orchestrator is just an agent
whose tools are other agents. The base ships single-agent — it doesn't fold a
multi-agent subsystem into the core — but it keeps an agent able to satisfy the
tool interface, so the day you want nesting it's a ~20-line wrapper and not a new
architecture. (See §8 and the orchestration section in §9.)

**Security lives at the boundary.** The core has no permission system. It runs
with the permissions of whoever launched it. Isolation is achieved by
containerizing/sandboxing the whole process, not by in-core access control. We
*do* ship the hook points where a clone could add confirmation or an allowlist —
shipped permissive by default (see §6).

**Effort stance.** Minimal now, dock heavy stuff later. We build something in v1
only if it passes both tests: (a) *every* agent needs it regardless of domain,
and (b) it is genuinely hard to retrofit. Everything else waits for a real agent
to demand it.

---

## 2. Architecture — the seams

Four layers. Each has a narrow, explicit contract. Nothing reaches across a layer
it doesn't border.

```
┌─────────────────────────────────────────────────────────────┐
│  SKILLS / EXTENSIONS         (what a clone customizes)         │
│  extra tools · prompt overrides · skill dirs · hook impls     │
└───────────────────────────┬─────────────────────────────────┘
                            │  registers tools, hooks, prompts
┌───────────────────────────▼─────────────────────────────────┐
│  AGENT CORE                  (you own this)                    │
│  the loop · state · tool dispatch · arg validation · hooks    │
└──────────┬──────────────────────────────┬───────────────────┘
           │ calls tools                   │ calls provider
┌──────────▼──────────────┐   ┌────────────▼───────────────────┐
│  TOOLS                   │   │  PROVIDER LAYER  (rented)       │
│  read · write · edit ·   │   │  litellm wrapper: complete()    │
│  bash  (Tool protocol)   │   │  normalizes all LLM providers   │
└──────────────────────────┘   └────────────────────────────────┘
```

**Provider layer** — the only thing it exposes upward is one function:
`complete(model, messages, tools) -> response` returning normalized text plus any
tool calls. Streaming is optional and lives behind the same seam. Credentials
resolve from the environment. The agent core never imports a provider SDK
directly; if you ever swap `litellm` for raw SDKs, only this file changes.

**Agent core** — owns the turn lifecycle (§5), the conversation state, tool
dispatch, argument validation, and hook invocation. It knows nothing about *which*
model it is talking to and nothing about *what* a given tool does — tools are just
typed callables.

**Tools** — each is an object with `name`, a parameter schema, and an `execute()`.
That's the entire `Tool` protocol (§4, §8). The four built-ins implement it; so can
anything a clone adds; so can an agent.

**Skills / extensions** — the customization surface. A clone adds tools, overrides
the system prompt, points at skill directories, and supplies hook implementations
here. The three layers below are touched rarely or never.

---

## 3. Project structure

```
spine/                     # rename freely — this is your agent's repo
├── pyproject.toml
├── README.md              # orientation + how to run
├── CLAUDE.md              # always-on orientation + the bootstrap protocol
├── AGENTS.md              # the same, mirrored for coding agents in the repo (§9)
├── main.py                # runnable entry point (the repo is the agent)
├── src/
│   └── spine/
│       ├── __init__.py
│       ├── provider.py    # rented LLM layer: complete()
│       ├── agent.py       # Agent: the loop, state, dispatch, hooks
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py    # Tool protocol: name, schema, execute()
│       │   ├── read.py
│       │   ├── write.py
│       │   ├── edit.py
│       │   └── bash.py
│       ├── hooks.py       # hook types + default (permissive) implementations
│       ├── skills.py      # skill discovery/loading seam
│       └── prompts/
│           └── system.md  # base system prompt
├── skills/                # capability-as-documentation (discovered, run via bash)
└── tests/
```

---

## 4. The four tools

Tools are the surface the model acts through. Keep their schemas tight and their
error messages useful — a clear error is what lets the model self-correct.

### `read`
Read a file's contents. Returns the text, optionally with line numbers. Supports
`offset`/`limit` for large files so the model can page rather than blow the
context window. Reading enough surrounding context is what makes `edit` reliable.

Parameters: `path` (str), `offset` (int, optional), `limit` (int, optional).

### `write`
Create a new file or overwrite an existing one with full contents. Prefer `edit`
for changes to existing files — `write` clobbers. (A clone may add a "refuse to
overwrite without confirmation" hook; the core does not.)

Parameters: `path` (str), `content` (str).

### `edit` — the one that matters
This is the tool whose design decides your reliability, so it gets the most words.

**Mechanic: exact string replacement.** The model supplies `old_string` (a unique
substring of the file, including enough surrounding context to be unambiguous) and
`new_string`. The core:

1. Reads the file.
2. Counts occurrences of `old_string`.
3. If **zero** matches → return an error telling the model the string wasn't found
   (it retries with corrected text).
4. If **more than one** match → return an error telling the model the string isn't
   unique and to add more surrounding context (it retries).
5. If **exactly one** match → replace and write.

This beats the alternatives for LLM use: line-range edits break because line
numbers drift between the model's read and its write; unified diffs frequently
fail to apply cleanly. Exact-match-with-uniqueness-check fails *loudly and
recoverably*, which is exactly what you want, because the error feeds straight
back to the model (§5).

Parameters: `path` (str), `old_string` (str), `new_string` (str).

### `bash`
Run a shell command; return stdout, stderr, and exit code. The escape hatch for
everything the other three don't cover. Runs with a timeout and truncates very
large output. Runs as the launching user — this is the security boundary called
out in §1 and §6.

Parameters: `command` (str), `timeout` (int, optional).

---

## 5. The agent loop

The turn lifecycle. This is the core you own.

```
loop:
    response = provider.complete(model, state.messages, tools)
    append assistant message to state

    if response has no tool calls:
        return            # the agent is done with this turn

    for each tool_call in response:
        validate tool_call.args against the tool's schema
        if invalid:
            result = validation error            # fed back to the model
        else:
            run before_tool_call hooks            # may block / modify (§6)
            result = tool.execute(args)
            run after_tool_call hooks             # may inspect / annotate
        append tool result to state

    if every tool result this batch signalled "terminate":
        return

    # otherwise: loop — the model sees the results and continues
```

Two details carry their weight:

- **Validation-error feedback.** Tool arguments are validated against the tool's
  schema (Pydantic) *before* execution. A failure isn't an exception — it's
  returned to the model as the tool result, so it self-corrects on the next pass.
  Same for the `edit` not-found / not-unique cases.
- **`terminate` hint.** A tool (or an `after_tool_call` hook) can signal the agent
  should stop after the current batch. It only takes effect if the whole batch
  agrees. This is runtime-only; the transcript stays standard LLM tool results.

---

## 6. Hooks

Hooks are the extension point that keeps the core at four tools. Instead of baking
features in, the core exposes points where a clone injects behavior.

- `before_tool_call(tool, args, ctx)` — runs before execution. Can **allow**,
  **block** (returns a message to the model instead of running), or **modify**
  args. This is where a clone would put a confirmation prompt, an allowlist, a
  `rm -rf` guard, or audit logging.
- `after_tool_call(tool, args, result, ctx)` — runs after execution. Inspect or
  annotate the result; can raise the `terminate` hint.
- session lifecycle (`session_start`, `session_end`) — for setup/teardown,
  registering tools at startup, loading skills.

**Default implementations ship permissive** — every `before_tool_call` returns
"allow." This is the deliberate "no permissions in core" stance: the *mechanism*
exists, the *policy* is empty, and any clone can tighten it without touching the
core.

---

## 7. Skills & extensions

How a clone adds capability without editing the core:

- **Add tools** — implement the `Tool` protocol and register at `session_start`.
- **Override prompts** — replace or extend `prompts/system.md`.
- **Skills** — CLI tools documented with a README the agent can read and invoke
  via `bash`. Capability-as-documentation rather than a heavyweight plugin
  protocol. A `skills/` directory is discovered and surfaced to the model.
- **Hooks** — supply `before`/`after` implementations for policy, logging, UI.

A data-analysis clone adds pandas/plotting skills and a tightened `bash` hook. A
writing clone adds a style-guide prompt and a couple of research tools. Neither
touches the loop or the four tools.

---

## 8. The Tool protocol (and why an agent is a tool)

Every tool is the same shape:

```python
class Tool(Protocol):
    name: str
    description: str
    parameters: type[BaseModel]          # Pydantic schema
    def execute(self, args) -> ToolResult: ...
```

That's the whole contract. The four built-ins satisfy it. Clone-added tools
satisfy it. And — critically — **an agent can satisfy it too**: wrap an `Agent`
so that `execute(args)` runs the agent's loop on `args["task"]` and returns its
final message as the `ToolResult`. The child runs its own loop with its own
message history and returns only a result to the parent — clean context
isolation, identical in shape to any other tool result.

We do not write that wrapper in v1. We only keep the protocol clean enough that it
*could* be written. That is the entire cost of leaving orchestration open.

---

## 9. Out of scope (deliberately) — and the orchestration switch

Things multi-agent/comprehensive systems eventually want, kept out of v1 on
purpose. Each notes how it docks later.

| Deferred capability | Why out now | How it docks later |
|---|---|---|
| MCP | Not every agent needs it; adds protocol surface | Add as a tool source or an extension |
| Memory / persistence | Domain-specific shape | Hook into state at `session_start`/`after_tool_call` |
| RAG / retrieval | Use-case-specific | Ship as a tool or skill |
| Graph orchestration (LangGraph) | A single 4-tool loop barely uses it | Wrap the loop as a graph node if a real branching/durable workflow appears |
| In-core permissions | Boundary handles it | Implement a `before_tool_call` hook |
| **Multi-agent orchestration** | Orchestration is recursion (§8) | **Wrap an agent as a tool (§8); add the rest as needed** |

### ⟶ THE ORCHESTRATION SECTION

The base ships **single-agent** — one loop, one model, four tools — because most
agents never need more and that's the right default. But orchestration is just
recursion (§8): an orchestrator is an agent whose tools are other agents. Because
the `Tool` protocol is kept agent-satisfiable, turning sub-agents *on* is an
addition, not a rewrite. Mirror this framing at the top of `AGENTS.md` so a coding
agent working in the repo has the same orientation.

```
# ════════════════════════════════════════════════════════════════
# ORCHESTRATION  ──  SHIPS SINGLE-AGENT, OPENS CLEANLY
# ════════════════════════════════════════════════════════════════
# Default (current): one loop, one model, four tools. Most agents stay
# here, and that's fine.
#
# If your agent needs sub-agents — a parent delegating to specialized
# children — add them like this:
#   1. Add agent_as_tool(agent) -> Tool   (~20 lines): execute() runs the
#      child agent's loop on args["task"], returns its final message.
#   2. Give a parent agent one or more child agents in its tool list.
#   3. Decide up front: which children earn their keep, how deep nesting
#      may go, the token/cost budget (each nested call burns a whole
#      conversation), and who signals termination.
#   4. Add parallel fan-out / shared state / handoff only when a real
#      workflow needs them — the minimum, not the set.
#
# Keep the Tool protocol (§8) agent-satisfiable so this stays a ~20-line
# wrapper rather than a new architecture.
# ════════════════════════════════════════════════════════════════
```

The point: single-agent is the default, not a locked door. When you need
multi-agent, the property you kept — an agent is a tool — is already the
construction plan.

---

## 10. Tech choices

| Concern | Choice | Note |
|---|---|---|
| Language | Python | — |
| Provider abstraction | `litellm` | Rented. The one place we don't roll our own. |
| Tool schemas / validation | Pydantic | Validate model args before execute; errors fed back |
| Agent loop | hand-written | ~150–200 lines; owned, not framed |
| Orchestration runtime | none in v1 | LangGraph optional later, per the switch |
| Permissions | none in core | Hook points shipped permissive |
| Isolation | external | Containerize/sandbox the whole process |

---

## 11. Cloning workflow

To build a new agent on Spine:

1. Clone the repo, rename the package.
2. Add domain tools under `tools/` (implement the `Tool` protocol) and register
   them at `session_start`.
3. Edit `prompts/system.md` for the domain.
4. Drop in skills (CLI tools + READMEs) under `skills/`.
5. Optionally tighten the `before_tool_call` hook (e.g., constrain `bash`).
6. Run.

The loop and the four tools stay untouched. That's the foundation working as
intended.
