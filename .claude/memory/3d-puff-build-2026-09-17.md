---
name: 3d-puff-build-2026-09-17
description: Kent moved 3D puff off the non-goal list on 2026-09-17 with nothing built; eight rulings, a design spec and a 12-agent research pass. PR 0 step-IR plumbing first; the Tajima same-needle halt test gates PR 1
metadata:
  type: project
---

Kent ruled 3D puff IN scope on 2026-09-17 after a brainstorming session. Nothing is
built. Spec: `docs/superpowers/specs/2026-09-17-3d-puff-design.md`; evidence:
`docs/puff-research-2026-09-17.md`. Both first landed on branch `claude/3d-puff`
(worktree `.claude/worktrees/3d-puff`).

The rulings that shape everything: Python digitizer only (service route); per shape,
from a canvas menu that mirrors `borderMenu.js`; one Wilcom compensation default
(push 0.35, no pull), chosen knowingly over a split the literature cannot settle;
refuse strokes outside 3.0–5.0 mm (5.0 is the engine's `SPLIT_SATIN_ABOVE_MM`, not
physics); multi-colour from the start; warn on every interior void, refuse none.

**Why:** most of puff already existed in pieces — the step/stop IR, arc-normalized
satin spacing, a perimeter bean emitter (`silhouette_cap`, default ON) — while the
2026-08-01 spec it was planned from was wrong in places that mattered: its "fatal"
3.0 constant was 5.0 when written, one citation was fabricated, and "end-caps are
the #1 engine change" was refuted 3/3.

**How to apply:** start at the spec's §12. PR 0 (~150 lines, step IR → service →
`pdfsheet.js`) is independent and also gives appliqué the operator sheet it has
never had. Do not start PR 1 before Kent's five-minute Tajima halt test. Mirror
`border`'s per-shape path, never appliqué's — `Region.meta["applique"]` is written by
nothing. Related: [[sew-out-accepted-as-is]], [[first-physical-sewout-2026-09-01]].
