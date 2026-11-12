---
name: starter-weak-spots-2026-11-12
description: Starter pack's three weak designs diagnosed 11-12 — baseball rings = radial design ramp bands, turtle = stage-2 RAG merge at 26 dE00, monarch trims = borders_last moving white dots after black; all existing settings, no new flag, pack files unchanged pending Kent
metadata:
  type: project
---

Full record: `docs/starter-pack-weak-spots-2026-11-12.md`, renders in
`docs/renders/starter-weak-spots-2026-11-12/`. Main bdae1860, pack widths.

- **Baseball grey rings:** the radial branch of `design_ramp` passes on a real
  vignette (L* 96 -> 84) and stage 6 sews Skylight/Glacier bands. Fix: the
  existing `forced_class: "flat"` setting gives one white field and a whole seam
  line, at +3.8k stitches, +6 trims and preflight 88 -> 76. `design_ramp: false`
  is worse (it leaves a grey crescent).
- **Turtle shell:** the gradient-lane RAG merge (`MERGE_DELTAE00_THRESH` 26,
  pinned by DOCTRINE) chains shell, legs and head into one Caper region (79% of
  the area); every pair is 3-23 dE00. Flat + `max_colors: 15` reads right but
  takes 15 cones, +77% stitches and preflight F (the tongue folds into Cranberry).
- **Monarch 86 trims:** 68 hops lie on finished black, because `borders_last`
  moves the satin-classed white-dot layer after the black fill.
  `borders_last: false` gives 86 -> 64 with the render unchanged. Sewing white
  first with a `layer: -1` override takes the white trims 50 -> 4, but black
  then covers the dots, at +27% stitches: a stage-5/7 knock-out build, not built.

**Why:** a session asked to "fix the starter weak spots" would otherwise
retune the RAG threshold or the radial gate. DOCTRINE pins both.

**How to apply:** re-digitizing the shipped DSTs is Kent's call, sent to the
foreman 11-12. When it happens, record the settings in the manifest (it has no
field yet) and rerun `scripts/derive-starter-threads.mjs`. Related:
[[starter-pack-sourcing-2026-11-10]], [[trim-defects-4-6-2026-10-29]].
