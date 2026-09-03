---
name: classifier-stability-2026-09-03
description: Kent's "classifier robust to boundary detail" item — MEASURED NEGATIVE, no engine change. 5 of 219 DT-judged verdicts flip under boundary detail, 4 on threshold edges; eight cures (spur pruning ×3, sewing spur rule, hybrid, raster smoothing ×2, regularity band) all leave 3–12 flips and change 2–48 shipped verdicts; pruning collapses a blob's spine into a "regular" one that walks into satin (no elongation guard on the ordinary path). Instrument `tools/ribbon_stability.py`; the working mitigation is `_CURVE_MIN_EPS_PX` (#330).
metadata:
  type: reference
---

# Classifier stability (2026-09-03)

Full record: `docs/classifier-stability-2026-09-03.md`.

- The spur-inflation diagnosis from the flip was the mechanism on ONE of
  five flips; the other four are threshold-edge shapes (cv 0.5, aspect 3,
  `explained` 0.80).
- Pruning spurs before measuring is wrong in principle here: a compact
  shape's spurs ARE its medial axis; pruned, `explained` explodes and cv
  drops, and the blob reads regular → satin via the path with no
  elongation guard.
- Smoothing the classifier's own raster is worse (the raster is ~8 px
  across the wall; 1–2 px is 12–25% of it); a band moves the knife edge.
- What would work is a different construction (a margin with memory, or a
  polygon-native width profile) — Kent's call. The corpus the thresholds
  were tuned on (`scratch_kent`, 15 designs) is not in a cloud checkout.
