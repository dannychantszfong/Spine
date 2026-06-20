# AGENTS.md — for coding agents working in this repo

This repo is a **clone of spine**, a minimal agent foundation (a model, four
tools, a loop). Your job here is to help grow it into the **new agent** the
developer wants — building on the skeleton, not preserving "spine." The full rules
and reasoning are in [`CLAUDE.md`](CLAUDE.md) and
[`doc/spine-spec.md`](doc/spine-spec.md); this is the short mirror.

## First, on a fresh clone

1. **Read the skeleton** — the loop (`src/spine/agent.py`), the four tools
   (`src/spine/tools/`), and the seams (hooks, skills, the prompt). It's small;
   read all of it.
2. **Ask the developer what they're building** — what the agent does, what its
   domain needs, what it should refuse. Interview before you implement.
3. **Discuss the shape** — which need is a tool, which is a skill, which is a
   prompt change, which is a hook policy.
4. **Then build at the seams** — the loop and the four tools usually stay as they
   are.

## The grain (defaults to build with, and why)

- **Four tools** — `read`, `write`, `edit`, `bash`; `bash` is the escape hatch,
  which is why four is enough. Prefer a *skill* over a fifth core tool.
- **Own the loop** (`src/spine/agent.py`, ~150 lines) — hand-written and
  framework-free so every line is readable. No LangChain / LangGraph in the core.
- **Rent the provider** — LLM calls go through `provider.py`'s `complete()`
  (litellm); provider SDKs stay out of the rest of the core.
- **Validate, don't crash** — tool args are Pydantic-validated before `execute()`;
  a failure is returned to the model as the result, never raised.
- **Policy lives in one place** — the `before_tool_call` hook, shipped permissive.
  No permission system in the core; isolation is external.

These are the recommended grain — they keep the agent readable and lock-in-free.

## Going against the grain

It's the developer's call, not a prohibition — but be honest about the cost. A
fifth core tool, SDKs in the core, or a loop too big to hold in your head all
erode what makes this foundation useful. And if the agent genuinely needs a heavy
framework (LangChain / LangGraph / an orchestration runtime), say plainly that
starting fresh with that framework usually beats retrofitting it onto this one,
which isn't built to mesh with it. Compass, not cage.

## Sub-agents (orchestration)

Ships **single-agent** — the right default. If the new agent needs sub-agents, the
`Tool` protocol is kept agent-satisfiable so it opens without a rewrite: wrap an
`Agent` as a `Tool` whose `execute(args)` runs the child's loop on `args["task"]`
(~20 lines). Decide first: which children, nesting depth, token / cost budget, and
who signals termination. Add parallel fan-out / shared state / handoff only when a
real workflow needs them. Full how-to in [`CLAUDE.md`](CLAUDE.md).
