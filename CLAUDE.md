# CLAUDE.md — building on spine

This repo is a **clone of spine**: a minimal Python agent foundation — a language
model, four tools, and a loop. It is a starting point, not a product, and not
something to preserve. Working here, your job is to help grow this clone into a
**new agent** — the one the developer actually wants — building on the skeleton
rather than guarding it.

The full rationale lives in [`doc/spine-spec.md`](doc/spine-spec.md); a code-level
walkthrough is in [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md). This file is the
short, always-on orientation.

## Bootstrap protocol — do this first

On a fresh clone, before changing anything:

1. **Read the skeleton.** Understand what you're standing on — the loop
   (`src/spine/agent.py`), the four tools (`src/spine/tools/`), and the seams
   where capability attaches (hooks, skills, the system prompt). It's small on
   purpose; you can hold all of it in your head in one sitting.
2. **Ask the developer what they're building.** What agent is this becoming? What
   does it need to do, what tools / skills / knowledge does its domain require,
   what should it refuse? Don't assume — interview.
3. **Discuss the shape.** Talk it through before writing code: which capability is
   a tool, which is a skill, which is a prompt change, what policy the hook should
   enforce. Map it onto the seams below.
4. **Then grow the body.** Once you both know the shape, build it at the seams.
   The loop and the four tools usually stay as they are; the new agent is mostly
   new tools, new skills, a new prompt, and a tightened hook.

Don't spend effort preserving the name "spine" or defending the original
minimalism for its own sake. Preserve what's *useful* about the foundation — read
it, understand why it's shaped this way — then build forward.

## The grain — how the foundation is built, and why

Spine is deliberately minimal, and the minimalism is load-bearing. These are the
defaults to build *with*; each comes with its reason, so you know when it applies.

- **Four tools.** The model gets `read`, `write`, `edit`, and `bash`. `bash` is
  the escape hatch — grep, git, curl, tests, package installs all go through it,
  which is why four primitives cover so much. Reach for a fifth built-in only when
  a real need genuinely can't be served by the four; usually a *skill* (a CLI +
  README the agent runs via `bash`) is the lighter way to add capability.
- **Own the loop.** The agent loop (`src/spine/agent.py`, ~150 lines) is
  hand-written so you can read and trust every line. Keeping it framework-free (no
  LangChain / LangGraph in the core) is what keeps it that readable and lock-in-free.
- **Rent the provider.** All LLM calls go through `provider.py`'s `complete()`,
  which rents `litellm` for multi-provider normalization. Keeping provider SDKs
  out of the rest of the core means swapping or upgrading a provider touches one
  file.
- **Seams over features.** Capability attaches at clean interfaces — tools, hooks,
  skills, the prompt — rather than being baked into the core. A good seam costs
  almost nothing now and lets heavy machinery dock later without a rewrite.
- **Validate, don't crash.** Tool args are Pydantic-validated before `execute()`,
  and a validation failure is *returned to the model as the tool result*, not
  raised — so the agent self-corrects instead of dying.

Building along this grain keeps the agent readable, debuggable, and free of
framework lock-in. That's the recommendation. It isn't a cage — see below.

## Going against the grain — allowed, just know the cost

This foundation is built for simplicity, minimalism, and being ready to extend.
Going heavy cuts against that grain. You can still do it — it's the developer's
call — but be honest about the trade:

- Adding a fifth core tool, putting provider SDKs in the core, or growing the loop
  past what one person can hold in their head all erode the very property that
  makes this foundation worth using. Not forbidden; just not recommended, and
  worth a deliberate decision rather than a quiet drift.
- If the agent genuinely needs a heavy framework — LangChain, LangGraph, a full
  orchestration runtime — say so plainly, to the coding agent and the developer
  both: you are probably **better off starting fresh** with that framework than
  retrofitting it onto this foundation, which isn't designed to mesh with it.
  Bolting it on tends to give you the costs of both and the benefits of neither.

Compass, not cage: state the recommendation and the reason, then let the developer
decide.

## The map — where things live, what attaches where

```
src/spine/
  agent.py        # the loop, conversation state, tool dispatch, hooks — you own this
  provider.py     # rented litellm wrapper: complete(model, messages, tools)
  tools/          # read · write · edit · bash  (the four built-ins; Tool protocol in base.py)
  hooks.py        # before/after_tool_call + session lifecycle — ships PERMISSIVE
  skills.py       # skill discovery/loading seam
  prompts/system.md   # the base system prompt
main.py           # runnable entry point — the repo is the agent, so its entry lives at the root
skills/           # capability-as-documentation; `lines/` is a worked example
tests/
```

The seams a new agent attaches to:

- **Add a tool** — implement the `Tool` protocol (`tools/base.py`: `name`,
  `description`, Pydantic `parameters`, `execute() -> ToolResult`) and pass it to
  `Agent(tools=[...])`.
- **Add a skill** — drop a CLI + `README.md` under `skills/`; the agent discovers
  it and runs it via `bash`. No plugin protocol — that's the point.
- **Set policy** — tighten the `before_tool_call` hook (`hooks.py`). It ships
  permissive; this is the *only* place policy belongs (allowlists, confirmations,
  an `rm -rf` guard, audit logging). The core has no permission system on
  purpose — isolation is external (sandbox / container).
- **Change behavior or voice** — edit `prompts/system.md`, or pass `system_prompt=`.

`doc/ARCHITECTURE.md` has copy-pasteable recipes for each of these.

## Sub-agents (orchestration) — ships single-agent, opens cleanly

This foundation ships **single-agent**: one loop, one model, four tools. That's
the right default, and most agents never need more.

If the agent you're building genuinely needs **sub-agents** — a parent that hands
work to specialized children — the foundation is built to allow it without a
rewrite, because the `Tool` protocol is kept agent-satisfiable: an `Agent` can be
wrapped as a `Tool` whose `execute(args)` runs the child's loop on `args["task"]`
and returns its final message. The wrapper is ~20 lines.

Before you add it, decide a few things up front:

- **Which children, and why** — what specialized agents actually earn their keep.
- **Nesting depth** — how deep parent → child → grandchild is allowed to go.
- **Token / cost budget** — each nested agent call burns a whole conversation;
  watch cost and latency.
- **Who terminates** — how a child signals "done," and how the parent decides the
  overall task is complete.

Add only what a real workflow needs — start with `agent_as_tool`, and add parallel
fan-out / shared state / handoff later if and when they're actually required, not
speculatively.

## Style

- Python 3.12+. Type hints everywhere. Pydantic for schemas.
- This is a codebase meant to be **read**. Keep functions small and obvious;
  prefer clarity over cleverness. No premature abstraction.

## Build & run

- Install (incl. dev tools): `pip install -e ".[dev]"`  (or `uv sync --extra dev`)
- Run the agent: `python main.py "<task>"` — needs a provider key in the env (e.g.
  `ANTHROPIC_API_KEY`); pick a model with `--model`. The default model is
  `anthropic/claude-opus-4-8`.
- Test: `pytest` — no API key needed; the loop test drives a stubbed provider, and
  `provider.py` imports `litellm` lazily so the suite runs offline.
- Lint / format: `ruff check` / `ruff format`
