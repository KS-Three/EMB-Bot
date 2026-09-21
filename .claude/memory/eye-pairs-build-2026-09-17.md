---
name: eye-pairs-build-2026-09-17
description: 2026-09-17 — the pipeline foundation review, and the eye-pairs picker built from it in one session; the worktree guard's command grammar, a preflight key that is a denominator, and why spiking the plan's APIs first meant zero surprises in the build
metadata:
  type: project
---

# The foundation review, and the eye-pairs build — 2026-09-17

Kent asked for the image-to-stitch flow end to end plus an adversarial
review of the foundation. Record: `docs/pipeline-flow-and-foundation-review-
2026-09-17.md` (11 concerns, ranked). He picked F4 — *the yardstick still
does not agree with his eye* — and the spec, plan and build followed in the
same session: `docs/superpowers/specs/2026-09-17-eye-pairs-design.md`,
`docs/superpowers/plans/2026-09-17-eye-pairs.md`, `digitizer/tools/eye_pairs/`.

## Kent's rulings (all 2026-09-17)

- A pair is **the same design digitized two ways** (shipped vs one arm),
  never two designs. Arms: the ten pending default-OFF flags plus the engine
  at `25da2fe` (main on 2026-08-27, his "60%" review). Picker: a **local
  page served by the tool**, picks appended to disk — not an Artifact.
  Verdict: **sign agreement primary** (pre-registered, chance-corrected),
  a fitted composite exploratory only and gated at 40 decided pairs.
- Built inline in a worktree, not by subagents ("the 09-16 fleet outran
  its budget"). All ten tasks landed; 63 new tests; full Windows suite
  **3 failed / 2535 passed in 56 min** — the three named goldens, on code
  the branch never touches.

## What to carry forward

- **The worktree-isolated Bash guard has a grammar.** It refuses heredocs,
  a quoted path as the command name, pipes with `${PIPESTATUS}`, and `;`
  chains as "too complex to verify it is not git". The form that passes:
  `cd "<abs worktree dir>" && PATH="/c/.../digitizer/.venv/Scripts:$PATH"
  python -m pytest ...` — plain command names, `&&` only, scripts in the
  scratchpad instead of heredocs. The Bash tool reports pytest's own exit
  code, so no `$?` is needed.
- **A worktree has no venv; the main checkout's interpreter resolves
  `digitizer_core` and `tools` to the WORKTREE when run from its
  `digitizer/`** (checked by realpath before trusting a single test). The
  venv is Python 3.14 on Kent's box.
- **`preflight` `uncovered_wanted_mm2` is a DENOMINATOR** (the area the
  design wants covered — 476.8 mm² on a tiny design graded A 100). The
  defect metric is `uncovered_total_mm2`. The spec had the wrong one
  scored "lower is better"; a two-second spike caught it.
- **On the 240×160 synthetic (rectangle + disc, 40 mm), `design_angle=True`
  is byte-identical to shipped and `fill_angle_deg=45.0` is not** — the
  pair that makes the identical-skip rule testable in 1.2 s.
- **`legibility.measure` raises `TesseractNotFoundError` here**; the
  feature reads `null` with the exception in `notes`.
- **The 08-27 ref arm is environment-confounded on photo-class fixtures**:
  its worktree has no `rembg_isolated/venv` while the main checkout does,
  so the old engine skips photo prep for an environment reason. `--reveal`
  marks those rows; do not read them as an engine difference.
- **The main checkout's branch was switched under this session** (a
  `claude/eye-pairs-review` branch appeared at my commit, 83 s before I
  looked). Another session was live in the same checkout. Never build in
  the main checkout; the lane directory is `.claude/worktrees/`.

## The practice that paid three times

Before writing the plan, every API the plan would quote was run once on a
tiny synthetic image in the scratchpad. That spike found the denominator
above, a contradiction in the spec (§0 said refusals are common-mode, §3.7
nulled them — resolved as flag-and-keep with a primary/secondary split),
and the tesseract exception. Then the plan's four engine-free modules were
extracted from the markdown and run: 46 passed, matching the counts the
plan stated. The build itself hit **zero** failing implementation runs.
Spend the spike; it is cheaper than one wrong step executed.

See [[kent-eye-vs-instruments-2026-08-27]] (the datum this instrument
exists for), [[worktree-venv-and-baselines]], [[instruments-that-underreport-2026-09-06]].
