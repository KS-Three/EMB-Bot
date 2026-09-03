---
name: round-curves-2026-09-03
description: defect 22 ("this O is not round") built OFF as `curve_turn_deg` — a turn-per-vertex bound applied by re-reading each Douglas-Peucker edge against the raw arc and splitting at the arc MIDPOINT (max-deviation splitting re-picks staircase corners), floored at one pixel; Fremont's counter 9 → 33 vertices, 47° → 17°; found underneath it defect 25, fill stitches halved by float dust at the stitch-length threshold (8–10% of the stitches on whitebg, Fremont, sunset) — FIXED the same day on Kent's word (a micron of tolerance; whitebg −8%, Fremont −9%, sunset −10% stitches, nothing else moves; goldens re-pinned); near-floor lettering exempt from the refinement; the curve flip held
metadata:
  type: reference
---

Full record: `docs/round-curves-2026-09-03.md`.

## What worked and what did not

- **A turn bound inside Douglas-Peucker itself does not work on a raster.**
  Splitting at the max-deviation point with a tolerance near a pixel picks
  staircase corners; every prototype came back with 90° vertex turns on a
  circle. Split each DP edge at the arc's MIDPOINT instead, insert the mean
  of the raw points within ±2 px, floor the tolerance at 1 px. Straight
  edges never split (a rotated rectangle stays 4 vertices).
- **Resolution is the limit, not the tolerance.** At 31 px/mm (Fremont) a
  2.4 mm arc reads as a 24–33-gon with 17° turns; at 8–10 px/mm it can only
  reach 16–24 vertices with ±half-pixel jitter (ENTHUSIAST's roughness rose
  10.6 → 11.4 at 11 px/mm). Becker at 4 px/mm is byte-identical.
- **The flip drops hairline lettering.** Douglas-Peucker at 0.2 mm INFLATES
  a 2.6 mm letter by 14%; the honest polygon's ribbon width (0.47 → 0.38 mm)
  sits under the 0.5 mm minimum cross and the letter falls satin → fill
  (review finding). A design-level stitch delta cannot see a tier flip —
  the flip's evidence needs a per-shape `kind` diff. Scoping the refinement
  out of near-floor lettering vs routing it to a run tier is Kent's call.
- **Vertex mapping must walk both rings in lockstep**: a nearest-point map
  sends a hairline's return-leg vertices to their outbound twins.
- **Kent's rulings the same day:** fix the dust now (done: `SPLIT_TOLERANCE_MM`,
  whitebg 2162 → 1982, Fremont 6365 → 5789, sunset 11614 → 10416, no row or
  trim moves, whitebg/alpha goldens re-pinned with the pre-change tree),
  hold the curve flip, and exempt near-floor lettering (ribbon width within
  20% of the minimum cross) from the refinement.
- **FLIPPED ON 2026-09-03 (Kent), gated to four pixels of tolerance.**
  The per-shape tier diff found the 1-px floor reading raster texture at
  10–16 px/mm (rougher everywhere, two classifier tier flips via skeleton
  spurs); floors cost the O; `_CURVE_MIN_EPS_PX` = 4 keeps the O and leaves
  every golden byte-identical. `tools/curve_tiers.py`.
- **The guard is per ring (review of #328).** Shell-only gating skipped the
  letters and they still fell to fill: they are holes of the background,
  the holes were refined, stage 5 reshaped the letter against its hole.
  Every ring judged on its own; Fremont ON vs OFF 28/16 → 28/16 satin.
- **The 13% stitch swing was float dust, not the flag.** `split_long_moves`
  halves any fill step that measures 3.0000000000000004 — 576 of Fremont's
  2450 fill steps, 1198 on sunset (10% of the design). Instrument
  `tools/fill_dust.py`. Fix = a micron of tolerance; re-pins every fill
  golden, so it is paired with the curve flip for one re-pin round.

See also [[hotel-fremont-fine-details-2026-09-02]], [[stitch-angle-convention-2026-09-03]].
