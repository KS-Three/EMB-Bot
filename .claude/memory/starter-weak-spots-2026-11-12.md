---
name: starter-weak-spots-2026-11-12
description: Starter pack weak spots 11-12 — baseball rings = radial ramp bands (flat, SHIPPED), turtle = stage-2 RAG merge (flat+15 not taken), monarch = borders_last after black (86 -> 67 at the pack's 90.0 mm; the 11-12 "drift" hold was a width mistake)
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

**Rulings (Kent 11-12):** "Baseball + monarch", then "Baseball only now". The
baseball was re-digitized flat and shipped (#1417); the manifest row carries
`digitize_config`. The turtle was not taken. The monarch was held for "main's
drift" (a lost orange stripe). **That was false.** The re-digitize used
target 90.5 (the manifest's DST `width_mm`), but the pack used 90.0. At 90.0,
main writes the shipped bytes, and `borders_last: false` keeps the stripe at
86 -> 67 trims (`docs/monarch-orange-drift-2026-11-12.md`). The baseball and
turtle "before" runs had the same 0.5 mm slip.

**How to apply:** a stitched DST comes out about 0.6% wider than its target.
So find the original target by matching the shipped DST's bytes past the
512-byte header before any re-digitize or "drift" claim. Then re-digitize with
`digitize_config`, run `app/scripts/derive-starter-threads.mjs` (needs
Chromium), and draw the new DST from the file. The monarch is size-fragile:
its stripe is lost at 90.5 even on ac3d77fa. Related:
[[starter-pack-sourcing-2026-11-10]], [[trim-defects-4-6-2026-10-29]].
