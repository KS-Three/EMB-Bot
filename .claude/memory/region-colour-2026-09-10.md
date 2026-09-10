---
name: region-colour-2026-09-10
description: "2026-09-10 — cfg.region_color built (mean/median/modal) after the colour flip exposed that stage 2 hands the palette a region's MEAN; the population is real logo art, both robust arms put Bridge Bar's disc back on 0501 Sun, and flip_sheet's --max-colors was a Windows-only no-op."
metadata:
  node_type: memory
  type: project
---

**Kent's pick after #444** (the item-9 flip), and it is the correction the
colour bundle's own test run left open, not a new idea:
[[quality-review-2026-09-08]] items 10–14 are still unstarted.

**The defect.** `stage2_photo_segment.segment` step 6 selects the palette
over ONE Lab per SLIC+RAG region, and that Lab was the region's MEAN. Bridge
Bar's yellow disc is (251, 235, 65), 1.0 ΔE00 from `0501` Sun; the mean is
(223, 220, 77) because the black lettering, the bird and the rope inside it
contribute anti-aliased edges and grey halos, so the palette picks `6031`
Limelight — 7.0 ΔE00 off a logo's MAIN colour. `bind_resnap_all_classes`
(ON since 2026-09-10) exposed it; the unbound re-snap used to correct it
from the source pixels.

**Built:** `cfg.region_color` = `"mean"` (DEFAULT, the shipped expression
byte for byte) | `"median"` | `"modal"`, one seam, `region_lab`. An ARM and
not a bool on purpose — a photo's ramp has no dominant colour and the mean
is defensible there.

**Three things worth not re-deriving:**

1. **The Weiszfeld singularity dodge is backwards here.** Dropping the points
   that sit ON the estimate — the textbook fix — hands a flat region's
   estimate to its halo: with 91% of a disc at its field colour the estimate
   landed **9.75 ΔE00** off it. Use a distance FLOOR. A region's own colour
   IS a pile of identical pixels.
2. **`flip_sheet --max-colors` was a no-op on Kent's box** until this branch:
   the option set a module global and the workers are spawned processes, so
   every row of a `--max-colors 6` pass ran at the engine's 12 and stamped
   `max_colors: null`. Fork platforms (cloud sessions) inherited it and were
   right by luck — which is why the item-8 sheet's two budget tables differ
   and its numbers stand. Read a stored row before trusting a sweep.
3. **Kent's console is cp1252**: a `Δ` in a tool's PRINTED output aborts the
   run with `UnicodeEncodeError`. Keep printed strings ASCII (`dE00`);
   docstrings and docs are fine. `tools/scope_budget.py` still trips on it —
   run it with `PYTHONIOENCODING=utf-8`.

**Measured, 26 fixtures at the Studio's 6 colours / 80 mm.** Census
(`tools/region_color_census.py`): regions where both robust arms name one
thread and the mean names another cover 63.1% of the phone screenshot's
area, 56.3% of Bridge Bar's, 25.2% of Golden Tee's, and **0% of seven
photo/ramp fixtures**; the flat lane has no such regions at all. Sheet:
`median` −2 blocks / −2 stops / +2,974 st; `modal` +1 block / +1 stop /
+2,269 st but Bridge Bar −768 st and **−28 trims** with Sun sewing again,
against Golden Tee 7 → 9 blocks. Cost is one generated scene
(`photo_scene_stub`, +3,381 st either way). Fremont, Becker and every flat
fixture byte-identical.

**Open:** which arm is the default — Kent's, on the renders
(`tools/region_color_renders.py`). Related: [[quality-review-2026-09-08]],
[[gradient-ruling-2026-09-04]], [[palette-mismatch-bounded-2026-09-07]].
