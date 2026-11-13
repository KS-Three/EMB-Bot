---
name: starter-weak-spots-2026-11-12
description: Starter pack weak spots 11-12 — baseball rings = radial ramp bands (flat, SHIPPED), turtle = stage-2 RAG merge (flat+15 not taken), monarch = borders_last after black (86 -> 63; held, main drift lost an orange stripe)
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

**Ruling (Kent 11-12, "Baseball + monarch"):** the baseball was re-digitized with
flat and shipped; the manifest row now carries `digitize_config`. The turtle was
not taken. The monarch was held: on main its first orange stripe is lost
(-6.8% orange against the shipped file) with the setting either way, which is
drift since ac3d77fa, untraced.

**How to apply:** re-digitize a pack design with its `digitize_config`, then run
`app/scripts/derive-starter-threads.mjs` (needs Chromium), and draw the new DST
from the file before shipping it. That re-read is how the monarch drift showed. Related:
[[starter-pack-sourcing-2026-11-10]], [[trim-defects-4-6-2026-10-29]].
