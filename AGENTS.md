# AGENTS.md — directives for coding agents working in the spine repo

Read `doc/spine-spec.md` (the full spec/README) and `doc/claude.md` (the always-on
rule layer) before any structural change. The short version:

- The model gets **exactly four tools**: `read`, `write`, `edit`, `bash`. Do not
  add a fifth — `bash` is the escape hatch.
- **Own the loop** (`src/spine/agent.py`, ~150 lines). No agent framework
  (LangChain / LangGraph) in the core.
- **Rent the provider layer.** All LLM calls go through `src/spine/provider.py`'s
  `complete()`. The core never imports a provider SDK directly.
- Tool args are **Pydantic-validated before `execute()`**; a validation failure is
  returned to the model as the tool result, never raised.
- `edit` is **exact string replacement** with a uniqueness check. Zero or multiple
  matches return an error to the model. Never line-ranges or diffs.
- **No permission system in the core.** The `before_tool_call` hook is the only
  policy seam, and it ships permissive.
- Keep it small and readable. This is a reference codebase: clarity over cleverness.

```
# ════════════════════════════════════════════════════════════════
# ORCHESTRATION DIRECTIVE  ──  STATUS: DISABLED
# ════════════════════════════════════════════════════════════════
# WHILE DISABLED (current):
#   - Spine is single-agent. One loop, one model, four tools.
#   - DO NOT build a multi-agent subsystem.
#   - DO NOT hand any agent another agent as a tool.
#   - DO NOT add scheduling, inter-agent messaging, shared blackboard
#     state, fan-out/fan-in, or supervisor/handoff protocols.
#   - The Tool protocol (spec §8) MUST remain agent-satisfiable. Do not add
#     anything that would prevent an Agent from being wrapped as a Tool.
#
# TO ENABLE — change the line above to "STATUS: ENABLED" and then:
#   1. Add agent_as_tool(agent) -> Tool   (~20 lines): execute() runs the
#      child agent's loop on args["task"], returns its final message.
#   2. Give a parent agent one or more child agents in its tool list.
#   3. Only now consider the deferred pieces IF a real workflow needs them:
#      parallel fan-out, shared state, handoff. Add the minimum, not the set.
#   4. Budget awareness: each nested agent call burns a full conversation —
#      watch token cost and latency.
# ════════════════════════════════════════════════════════════════
```
