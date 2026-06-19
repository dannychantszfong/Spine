# spine

A minimal Python agent backbone: a language model, four tools, and a loop. It is
a foundation to be **cloned**, not a product. The full design rationale and spec
live in [`doc/spine-spec.md`](doc/spine-spec.md); a code-level walkthrough is in
[`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md); the always-on rules are in
[`CLAUDE.md`](CLAUDE.md) and [`AGENTS.md`](AGENTS.md).

## What's here

```
src/spine/
  provider.py     # rented litellm wrapper: complete(model, messages, tools)
  agent.py        # the loop, conversation state, tool dispatch, hooks
  tools/          # read · write · edit · bash  (the only four)
  hooks.py        # before/after_tool_call + session lifecycle; ships PERMISSIVE
  skills.py       # skill discovery/loading seam
  prompts/system.md
examples/minimal_agent.py
skills/           # capability-as-documentation; `lines/` is a worked example
tests/
```

The model gets exactly four tools — `read`, `write`, `edit`, `bash` — and `bash`
is the escape hatch for everything else. The loop is hand-written and ~150 lines;
read it top to bottom in `src/spine/agent.py`.

## Install

```bash
uv sync --extra dev          # or: pip install -e ".[dev]"
```

## Run the example

`litellm` reads provider credentials from the environment. For Anthropic:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python examples/minimal_agent.py "list the python files here and count their lines"
```

Pick any litellm-supported model with `--model`:

```bash
python examples/minimal_agent.py --model gpt-4o "summarize README.md"
```

## Run the tests

No API key needed — the loop test drives a stubbed provider, so nothing hits the
network.

```bash
pytest
```

## Cloning workflow

1. Clone the repo, rename the package.
2. Add domain tools under `src/spine/tools/` (implement the `Tool` protocol) and
   register them at `session_start`.
3. Edit `src/spine/prompts/system.md` for the domain.
4. Drop in skills (CLI tools + READMEs) under a `skills/` directory.
5. Optionally tighten the `before_tool_call` hook (e.g. constrain `bash`).
6. Run.

The loop and the four tools stay untouched. See `doc/spine-spec.md` §11, and
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the invariants to keep while you build.

## More

- [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md) — code-level walkthrough with the
  extension recipes (add a tool, a hook, a skill, swap the provider).
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — the checklist of invariants for changes.
- [`CHANGELOG.md`](CHANGELOG.md) — what shipped, per version.
- [`skills/`](skills/) — what a skill is, and a runnable `lines` example.
