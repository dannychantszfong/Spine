# Changelog

All notable changes to spine are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

## [0.1.0] - 2026-06-19

Initial bootstrap — the smallest correct core: a language model, four tools, and
a loop. A foundation to be cloned, not a product.

### Added

- **Agent loop** (`src/spine/agent.py`) — hand-written turn lifecycle: call the
  model, dispatch tool calls, validate args, run hooks, feed results back. Owns
  conversation state and a `state` scratch space for extensions. `max_iterations`
  safety valve and a batch-unanimous `terminate` hint.
- **Four tools** (`src/spine/tools/`) — `read` (line-numbered, paged), `write`
  (clobbers, makes parent dirs), `edit` (exact string replacement with a
  uniqueness check), and `bash` (the escape hatch, with timeout and output
  truncation). All satisfy a single `Tool` protocol.
- **Provider layer** (`src/spine/provider.py`) — a rented `litellm` wrapper
  exposing one function, `complete(model, messages, tools)`, returning normalized
  `Completion` / `ToolCall` objects. `litellm` is imported lazily so the core and
  tests run without it.
- **Hooks** (`src/spine/hooks.py`) — `before`/`after_tool_call` plus session
  lifecycle, shipped permissive. The only seam where policy may live.
- **Skills seam** (`src/spine/skills.py`) — `discover_skills` /  `skills_prompt`
  for capability-as-documentation, with a sample skill under `skills/`.
- **Base system prompt** (`src/spine/prompts/system.md`).
- **Runnable example** (`examples/minimal_agent.py`) — a single agent wired to the
  four tools with a small CLI.
- **Tests** (`tests/`) — the four tools (including `edit`'s match / no-match /
  multi-match branches) and the loop driven by a stubbed provider (no API calls).
- **Docs** — `README.md`, `doc/spine-spec.md` (spec + rationale),
  `doc/ARCHITECTURE.md` (code-level walkthrough), `doc/claude.md` / `AGENTS.md`
  (always-on rules, incl. the orchestration switch), and `CONTRIBUTING.md`.

### Notes

- The orchestration switch ships **DISABLED**: spine is single-agent by design.
- No permission system in the core — isolation is external (sandbox/container).

[Unreleased]: https://example.com/spine/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/spine/releases/tag/v0.1.0
