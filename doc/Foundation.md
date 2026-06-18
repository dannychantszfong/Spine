# FOUNDATION.md — spine as a backbone

This is the governance and self-audit doc for treating `spine` as the foundation
of future agent projects. It exists so that, at any point in the future, you can
hand a coding agent **this repo + your filled-in checklist** and ask: *"Have I
stayed true to the foundation, and what should I do next?"*

It has five parts:

- **A. The mental model** — the creed. What this project is and refuses to be.
- **B. The roadmap** — how the backbone is allowed to grow over time.
- **C. The drift checklist** — yes/no questions you answer; deviations flag a talk.
- **D. The decision gate** — the test to run on any "should I add X?" question.
- **E. Handoff** — how to use this doc with a future Claude.

---

## A. The mental model

Read this first. Everything else enforces it.

1. **Spine is a backbone, not a product.** Its job is to be cloned. Its value is
   what it *doesn't* contain.
2. **A language model, four tools, and a loop.** `read` / `write` / `edit` /
   `bash`. `bash` is the escape hatch that makes four enough.
3. **Own the loop, rent the provider.** The loop is yours to understand line by
   line. Provider normalization is plumbing you rent (`litellm`).
4. **Seams over features.** Effort goes into clean interfaces, not speculative
   capability. Heavy machinery docks onto seams later; it is not built early.
5. **Optionality is the asset.** Adding is cheap, removing is expensive. The base
   stays small so it forecloses nothing.
6. **Orchestration is recursion, not a layer.** An orchestrator is an agent whose
   tools are agents. Kept off behind a one-line switch.
7. **Security at the boundary.** No permissions in the core; isolation is external;
   the permissive hook is the only policy seam.
8. **The base grows from evidence, not speculation.** Something enters the base
   only after real clones prove it's universal and hard to retrofit.

If a change violates one of these, that's not automatically wrong — but it must be
a *conscious* exception, written down, not a quiet drift.

---

## B. The roadmap — how the backbone may grow

The base is allowed to evolve, but only along this path. Each stage has an exit
condition before the next begins.

**Stage 0 — Base exists.** `spine` itself: four tools, loop, hooks, spec,
`CLAUDE.md`. No clones yet. *Exit: the example agent runs and tests pass.*

**Stage 1 — First clone.** Clone for one real use case (e.g. a data-analysis
agent). All domain work — tools, prompts, skills, a tightened `bash` hook — lives
in the clone. The base is untouched. This stage is the real test of your seams:
if cloning felt painful, the seam is wrong — **fix the base, not the clone.**
*Exit: a working clone whose diff against the base is purely additive.*

**Stage 2 — Second clone + backflow.** A second, different clone (e.g. a writing
agent). Now you have evidence of what's *actually* common versus what only felt
common. Anything **two independent clones** both needed — and that passes the
decision gate (Part D) — may be promoted back into the base. This is where the
base earns its generality: from two data points, never from one guess.
*Exit: shared needs promoted; clones re-based cleanly on the improved core.*

**Stage 3 — Selective heavy machinery.** Only now, and only where demanded:
- A single clone needs durable/branching workflows → introduce LangGraph **in that
  clone**, not the base.
- Multiple clones need nesting → flip the orchestration switch and add
  `agent_as_tool` to the base.
- A clone needs memory/RAG/MCP → add it as a tool, skill, or hook in the clone
  first; promote only if a second clone needs it too.

**Stage 4 — Platform.** A shared skills library, a clone template
(cookiecutter-style), CI, versioned base releases. The base is now a stable
platform that clones track like a dependency.

**The one rule that governs all stages:** *promotion into the base requires
evidence from 2+ clones.* One clone needing something means it belongs in that
clone. Two clones needing the same thing is the signal it's foundational.

---

## C. The drift checklist

Answer each **yes / no**. The "Healthy" column is the answer that means you're on
the foundation. A deviation isn't a failure — it's a conversation to have (with
yourself or a future Claude). Date your answers so drift over time is visible.

> Answered on: `__________`   ·   Clones in existence: `__________`

### C1. Core minimalism

| # | Question | Healthy | Your answer |
|---|---|---|---|
| 1 | Does the model still have exactly four tools (read/write/edit/bash) in the **base**? | YES | |
| 2 | Is the agent loop still hand-written, with no agent framework imported into the core? | YES | |
| 3 | Do all LLM calls still go through the rented provider layer, with no provider SDK imported directly in the core? | YES | |
| 4 | Is the orchestration switch still DISABLED (no agent handed another agent as a tool in the base)? | YES* | |
| 5 | Is the core still free of a permission system, with `before_tool_call` shipped permissive? | YES | |

*\*NO is fine **if** you consciously flipped the switch at Stage 3. A NO that
surprises you is the alarm.*

### C2. Seam integrity

| # | Question | Healthy | Your answer |
|---|---|---|---|
| 6 | Is the agent core still ignorant of which provider/model it's talking to? | YES | |
| 7 | Are tools still ignorant of the loop (a tool is just name + schema + execute)? | YES | |
| 8 | Can you add a new tool **without editing `agent.py`**? | YES | |
| 9 | Is the Tool protocol still agent-satisfiable (nothing added that would block wrapping an Agent as a Tool)? | YES | |

### C3. Backbone discipline (the most important section)

| # | Question | Healthy | Your answer |
|---|---|---|---|
| 10 | Is the agent you're building a **clone** of the base, rather than edits made directly to the base repo? | YES | |
| 11 | Has domain-specific logic (analysis code, writing-style logic, etc.) stayed in the clone and **out** of the base? | YES | |
| 12 | If you re-cloned the base today, could you reapply this agent's changes cleanly (additive, not entangled with core edits)? | YES | |
| 13 | When the base improved, did you pull those improvements into existing clones (or can you, cleanly)? | YES | |

### C4. Change justification

| # | Question | Healthy | Your answer |
|---|---|---|---|
| 14 | For the most recent thing added to the **base**: did *every* agent need it regardless of domain? | YES | |
| 15 | …and was it genuinely hard to retrofit later? | YES | |
| 16 | Was each base addition demanded by a **real** agent in use, not added speculatively "just in case"? | YES | |

### C5. Reversibility & readability

| # | Question | Healthy | Your answer |
|---|---|---|---|
| 17 | Can you back out your three most recent base changes without a cascade? | YES | |
| 18 | Did any recent change **foreclose** a future option (made something hard that used to be easy)? | NO | |
| 19 | Is the base still small enough that a new person could read the whole core in one sitting? | YES | |

### C6. Hygiene

| # | Question | Healthy | Your answer |
|---|---|---|---|
| 20 | Does `CLAUDE.md` still match what the code actually does (no stale invariants)? | YES | |
| 21 | Does `spine-spec.md` still match reality (code hasn't drifted from the spec)? | YES | |
| 22 | Do tests still cover the four tools and the loop, including `edit`'s match / no-match / multi-match branches? | YES | |

**Reading your deviations:** A NO in **C3** is the loudest alarm — it usually
means the base and a clone have fused, and the foundation is eroding. A NO in
**C4** means something domain-specific or speculative crept into the base; it
probably belongs in a clone. A NO in **C1/C2** means an invariant broke; decide
whether it was deliberate (Stage 3) or accidental. A NO in **C5 #19** is the
canary — when the core stops being readable in one sitting, minimalism has already
slipped.

---

## D. The decision gate

Run this on *any* future "should I add X?" question. Stop at the first failure.

1. **Does every agent need X regardless of domain?** No → it goes in the clone.
   Stop.
2. **Is X hard to retrofit later?** No → defer it until a real agent demands it.
   Stop.
3. **Has a real agent actually demanded X?** No → defer (it's speculation). Stop.
4. **Does X keep the seams clean and the Tool protocol agent-satisfiable?** No →
   redesign X until it does.
5. **Do 2+ clones independently need X?** Only one → put it in that clone, not the
   base.

Only an X that clears all five belongs in the base.

---

## E. Handoff — using this doc with a future Claude

When you come back to this in three or six or twelve months, the workflow is:

1. Re-read **Part A** to reload the mental model.
2. Fill in the **Part C** checklist against the current state of the repo, dated.
3. Hand a coding agent the **repo link + your filled checklist** and a prompt like:

   > *Here's my agent backbone `spine` and my filled-in FOUNDATION checklist.
   > Audit it: cross-check my answers against the actual code, tell me where the
   > base has drifted from the mental model in Part A, which of my recent additions
   > belong in a clone instead of the base, and — given which roadmap stage (Part
   > B) I'm in — what the next 2–3 moves should be. Run anything I marked as a
   > deviation through the decision gate in Part D.*

A future Claude can then do something concrete rather than vague: it reads the
code, checks your YES/NO claims for honesty, names the specific files where
domain logic leaked, and points to the next roadmap stage. The checklist turns
"is my project healthy?" from a feeling into an inspection.

---

*Last reviewed: `__________`  ·  Base version/tag: `__________`*
