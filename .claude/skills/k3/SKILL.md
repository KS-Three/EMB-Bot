---
name: k3
description: Run as foreman for EMB-Bot — dispatch many cloud Claude sessions (Opus for hard work, Sonnet/Haiku for the rest), keep every PR moving to auto-merge, and spend as few foreman tokens as possible. Use when Kent says "K3", "be foreman", "release agents/workers", "more workers", "run the team", or asks to parallelise work across many sessions.
---

# K3 — foreman mode

The foreman does not write code. It picks work, launches sessions, keeps PRs green, and
asks Kent only what is genuinely his. Everything heavy happens in other sessions; the
foreman's own context stays small.

Distilled from the 2026-10-07/08 foreman run: ~80 cloud sessions, ~25 PRs merged in one
evening, CI cut from ~75 to ~17 minutes along the way. Every rule below is something that
run either got right or paid for.

## 1. Start

1. Read `CLAUDE.md`, the `ROADMAP.md` gates, `DOCTRINE.md`. Don't re-read them later — delegate.
2. Send ONE scout (Agent, `model: opus`, `run_in_background: false`) for a <400-word report:
   open PRs (state, CI, auto-merge), running sessions, top candidate work items with their
   gate, recent in-flight memory notes.
3. Put the choices to Kent with `AskUserQuestion` (what to dispatch, which OFF flags to
   flip). Flips, physical constants, scope and money are his; everything else is yours.
4. Write `FOREMAN_STATE.md` in the scratchpad (orders, rules, triggers, in-flight, pending
   decisions). Update it at milestones so a `/compact` or `/clear` costs nothing.

## 2. Where work runs

- **Real builds → cloud sessions** (`mcp__claude-code-remote__create_session`): own
  container, own cores, own branch. Never pile build agents into the foreman's container —
  it has 4 cores and one shared checkout.
- **Short checks → local Agent tool** (reviews, triage, sweeps, diagnosis). Any local agent
  that touches git MUST work in a fresh worktree under the scratchpad. A failed
  `git worktree add` followed by a `cd` that silently didn't happen once ran merges inside
  the foreman's own checkout — tell agents to verify `pwd` before any git write.
- **Model choice:** `claude-opus-5-5` for defects, engine/digitizer changes, CI design;
  `claude-sonnet-5-5` for tests, docs, small Studio fixes, reviews, stewards; `haiku` for
  pure plumbing (broadcasting a message, launching sessions from a list).
- A session can push ONLY to the branch it was created with. New work on a new branch =
  new session; don't re-task an old one onto another branch.

## 3. Launching cheaply

Don't hand-write 20 prompts. Write a task file once and let a Haiku agent create the
sessions:

```
PREAMBLE (prepend to every prompt verbatim):
<the standing rules — see templates.md>

TASKS (title | model | branch | task):
1 | Short title | claude-opus-5-5 | claude/some-branch | What to do, the done-test, what to exclude.
```

Then: Agent(model: haiku) → "read the file; for each line call create_session once (all in
one parallel batch, never without parameters) with title, source_url, outcome_branch,
model, tags ["embot-foreman"], prompt = preamble + 'Task: ' + task; report ids."

**Big waves (30+):** don't plan them yourself. One Opus agent reads ROADMAP/MASTER_SCOPE,
lists open PRs and remote branches, and writes the task file (unique unused branches,
~40/60 Opus/Sonnet split, no two tasks on one file, gates respected). Then split the launch
across two Haiku agents (lines 1–30, 31–60) so neither times out mid-batch.

Every task must: name what is already in flight so it isn't duplicated ("check open PRs
first"), fit the time left, and state its done-test (PR ready-for-review, auto-merge armed).

## 4. Standing rules every session gets (in the preamble)

- Don't edit MASTER_SCOPE.md / docs/scope-history.md / DOCTRINE.md / CLAUDE.md / COOKBOOK.md
  — only one named scope-refresh session and one COOKBOOK session do. Status goes in the
  PR body. (Shared docs caused nearly every merge conflict.)
- Don't run the full digitizer suite locally (45+ min on 4 cores); CI shards it. Run only
  touched tests.
- `git fetch origin main && git merge origin/main` before every push; never rebase.
- Ready-for-review PR, arm auto-merge while `mergeable_state` is `blocked`, never merge.
- Fix your own red CI. Never skip/xfail a test to get green.
- Quiet: message nobody unless blocked; ask Kent only for decisions that are his.

Sessions sometimes refuse new work "on a cross-session message alone". Answer by quoting
Kent's own words verbatim (e.g. "take care of the PRs yourself", "get more sessions
going") — that is the authority they're asking for. If Kent ruled directly in a session
(e.g. "Leave OFF, I'll look"), that ruling wins over the foreman.

## 5. Keeping PRs moving

- **Don't subscribe to every PR** — each subscription floods the foreman's context.
  Subscribe only to a handful you're personally driving.
- **Sweep with `send_later` every 30 min.** The message tells future-you to dispatch one
  Sonnet steward: arm/undraft every open PR, find dirty or truly red heads, map branch →
  owning session via `list_sessions`, message the owner, report only exceptions.
- **Auto-merge only.** The auto-mode classifier blocks hand merges ("Merge Without
  Review"). Arm while `blocked`; once a PR is `clean` it can't be armed and needs Kent's click.
- **Fake reds:** a `digitizer` red whose shards are all `cancelled` is a superseded run
  (concurrency cancel), not a failure. Check the head sha before acting on any red.
- **Two unrelated PRs red at once** → suspect shared infra (CI, main), diagnose once.
- **Main red for everyone** (e.g. a `test.fail()` guard that turns into an "unexpected
  pass" once the fix lands): fix it yourself in the one-line commit, in a PR you own that's
  already armed, run that one test locally, push. Don't wait for a lane whose PR bundles
  other work.
- **Disarm** auto-merge on a PR that would break `main` for others (e.g. a new test that
  fails every later PR) until its owner fixes it.
- **Support crew** for big queues: local Sonnet agents with roles REVIEWER / MEDIC
  (conflicts) / TRIAGE (CI logs) / SHEPHERD (orphaned PRs), each owning PR number mod N = K
  so none overlap; they push only to branches whose owner session is idle >20 min.

## 6. Throughput limits (say so when Kent asks for more)

CI concurrency is the real ceiling: each PR fans out ~9 jobs. Past ~40 open PRs, new
sessions mostly wait in the CI queue and re-merge main. Prefer "drain then refill":
re-task finished sessions, keep ~30 active, fix CI speed first (sharding paid for itself
in one evening). Offer Kent the choice with the trade-off; then do what he picks.

## 7. Talking to Kent

Quiet mode by default: report only decisions that are his, blockers, orphaned PRs, and
merges he'll see in the Studio. One line per routine notification, or nothing. Use
`AskUserQuestion` for every decision, with the cost and catch on each option. Keep a
running list of decisions waiting on him in `FOREMAN_STATE.md`.

See `templates.md` for the preamble, rules broadcast, support-crew brief and sweep message.
