---
name: warn-sooner-small-files-handoff-2026-10-01
description: "HANDOFF — Kent said yes to warning sooner on small uploads (INPUT_LOW_RESOLUTION fires only under 4 px/mm); not started. Also the state of the work-grid flip PR #599 and what to do if its CI is red"
metadata:
  node_type: memory
  type: project
  originSessionId: 606ee7ba-4c24-446a-944b-282341bc71b2
  modified: 2026-10-01T22:19:16.259Z
---

**WITHDRAWN 2026-10-02 — do NOT build the warning.** Kent: "We shouldn't have to warn the user of anything. the tool needs the ability to identify the image it's being given and follow a path to produce the best output possible." PR #599 merged green the same day. Replaced by the bean-letters spec (a first mm-denomination spec was refuted the same day; the reasons are in the new one): `docs/superpowers/specs/2026-10-02-bean-letters-design.md` built OFF behind `cfg.bean_letter_max_stroke_mm` in PR KS-Three/EMB-Bot#601 (plan `docs/superpowers/plans/2026-10-02-bean-letters.md`); the flip is Kent's, on its renders. Everything below is history.

Session cleared 2026-10-01 with one approved task not started and one PR in flight.

**In flight: PR #599** (`claude/work-grid-on`, worktree
`.claude/worktrees/fine-detail-text`) — `work_px_per_mm` None → 8.0, Kent's
flip. Auto-merge armed. Local: 126 passed, only the 3 Windows goldens red.
Full suite was NOT run locally. **If CI `digitizer` is red:** a test outside
my list of 46 also sat on the old tracing grid — pin it the same way
(`tests/conftest.py`: `source_line_grid` fixture for a test that digitizes
itself; `work_px_per_mm=None` or `held_on_source_line()` inside a
module-scoped fixture or `lru_cache`d run, which a function fixture cannot
reach), push to the same branch.

**Approved, not started: warn sooner on small files.** Kent's ranking on the
pairs page was full-size file > finer grid > old grid on every logo, and the
5 px/mm files there lost to their full-size selves with no warning. His
words: "yes, warn sooner on small files."

**Why:** `stage1_prep` emits `INPUT_LOW_RESOLUTION` only when
`input_px_per_mm < cfg.min_px_per_mm` (4). Under the flip every source under
8 is enlarged, silently between 4 and 8.

**How to apply:**
- Branch from main AFTER #599 merges (it touches the same lines).
- Simplest form: warn whenever the working grid enlarges — compare against
  `work_grid_px_per_mm(cfg, design_class)` instead of `min_px_per_mm` in
  `stage1_prep.prep`. Payload key `min_px_per_mm` is what the Studio prints
  as "needs N" (`app/src/lib/digitizer.js`, `INPUT_LOW_RESOLUTION` text) —
  send the line actually used, and check the sentence still reads right
  ("about Nx wider").
- NOT decided, ask Kent with AskUserQuestion: the line (8 = everything
  enlarged, noisy on many uploads; 6 = where measured gain from more pixels
  was largest) and severity (it sits in the Studio's `ATTENTION_WARNINGS`).
  Measured: 5 px/mm sources clearly lose; 6.5 px/mm sources barely.
- Tests that pin today's behaviour: `tests/test_input_resolution_warning.py`,
  `tests/test_work_grid.py` (two tests assert "6 px/mm stays quiet"),
  `tests/test_crop_interactions.py`, `app/src/lib/digitizer.spec.js`.
- One heavy Python job at a time on this laptop; pytest `-n 4`, never auto.

Loose ends Kent knows about: stray `digitizer/_probe1.py` in that worktree
(guard hook blocks removal); `git fsck` commit-graph errors after the hard
power-off (`git commit-graph write` in the main checkout).

Related: [[fine-detail-work-grid-2026-09-30]], [[worktree-venv-and-baselines]].
