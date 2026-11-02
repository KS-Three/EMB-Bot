---
name: agents-cheap-models-2026-11-02
description: Kent 2026-11-02 "don't release fable agents, we should be saving on usage" — sessions and subagents a Fable director starts run on Sonnet (Haiku for read-only); never Fable, Opus only when Kent names it for a task
metadata:
  type: feedback
---

**Kent, 2026-11-02, mid-turn while a Fable session had two worker sessions
out:** "Also, make sure you don't release fable agents, we should be saving
on usage."

**Why:** a session started from a Fable session inherits Fable unless the
start passes `model`, and so does every `Agent` call that leaves `model`
unset (a `fork` subagent always inherits). The nightly-tripwire session
started that morning had inherited Fable for build work a Sonnet does as
well; it was switched mid-task with `set_session_model` to
`claude-sonnet-5-5`. The silent-fallback Studio session, started with
`model: sonnet`, shipped its PR on Sonnet. Usage, not capability, is the
reason: Kent pays for every spawned turn, and a director's value is the
dispatch and the judgement, not re-running the worker's model.

**How to apply:**

- Every `start_session` passes `model`: `claude-sonnet-5-5` for build,
  measure and fix work; `claude-haiku-5-5` for read-only, mechanical or
  census-table work. Every `Agent` call passes `model: "sonnet"` or
  `"haiku"`; where a `fork` would be used (it inherits Fable), either hand
  the work to a fresh agent with a model set or do it inline.
- A Fable session that is already running a worker on Fable switches it with
  `set_session_model` rather than letting it finish on Fable.
- Opus is not banned by this ruling but is not the default either: use it
  only when Kent names it for a task. The K3 foreman skill's "Opus for hard
  work, Sonnet/Haiku for the rest" stays as written for the foreman; a Fable
  director reads it as "Sonnet unless Kent says otherwise".
- This does not change which model Kent picks for the director itself; that
  is his menu, not a session's call.

Related: [[questions-roll-up-to-director-2026-10-27]] (the worker-to-director
protocol these sessions run under), [[next-work-from-main-not-handoffs]].
