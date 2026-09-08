---
name: quality-review-2026-09-08
description: 2026-09-08 — Kent asked for the 10-15 changes that most improve digitizing quality; fourteen ranked in docs/quality-review-2026-09-08.md, he picked 1+2 (real-logo lane + thin strokes) and 3 (sub-pixel edges). Three measurements under it — the curve gate reaches 2 of 29 fixtures; MARINE is tatami at 100 mm even with the per-stroke flag, refused by the 5 mm CAP not irregularity, and the 09-03 review's "2.6-3.2 mm strokes" were half-widths; the pro's sewn Becker files carry 7-23% of columns over 5 mm. The browser engine emits NO lock stitches.
metadata:
  type: reference
---

Read before proposing digitizing work, before quoting MARINE's stroke width,
and before touching `satin_per_stroke` or `SATIN_MAX_WIDTH_MM`.

## What was decided

Kent's picks from the ranked list: **start with items 1+2 together** (stop
routing anti-aliased flat logos through the superpixel lane, and keep thin
strokes and small lettering as strokes, widened to a sewable column) **and
item 3** (sub-pixel, anti-alias-aware boundary extraction in stage 4). Each
opens with a plan doc and an instrument PR before engine code. Item 1 touches
gate 2, and he chose it knowing that; the recalibration is on the real logos,
which now exist.

## What was measured, and what it corrects

- `_CURVE_MIN_PX_PER_MM` 20 admits only Fremont and Golden Tee at 80 mm.
  `logo_script_tires` misses at 19.8. The round-curves flip is inert on every
  design Kent called jagged. Do not quote defect 22 as fixed on real logos.
- **Becker @ 100 mm: every MARINE letter is refused by `dt_p90_cap`, not by
  irregularity, so `satin_per_stroke` cannot reach them** — it promotes three
  22–34 mm² shapes. The "segmentation, full stop" line in DOCTRINE is about
  the BECKER outline and the 80 mm case; for MARINE at 100 mm the cap binds.
  `docs/kent-review-2026-09-03.md`'s "2.6–3.2 mm strokes" is the HALF-width
  (skeleton DT p50 2.45–2.80, p90 2.71–3.55 → widths 5.4–7.1 mm). Same trap
  `textcluster.py`'s docstring names: `dist/scale` is a radius.
- The pro's large Becker files: p95 5.2–5.5, p99 6.1–6.4, max 8.5–9.1 mm,
  7–23% of crosses over 5.0. DOCTRINE's "do not raise the number" stands —
  both 2026-09-02 routes broke the overlap guard — and the build is that guard
  on local geometry (item 4). Sewn files are the evidence class that settled
  `FILL_ROW_MM`; whether they satisfy gate 1 for the ceiling is Kent's.
- **No lock stitches anywhere in the JS engine** (audit pass, re-verified):
  lettering, manual shapes, basic shapes and the flatten lane all cut with
  two unlocked ends. `tie_run` and its constants exist in Python. Cheapest
  real sew-out fix in the repo.

## Traps

- `stroke_verdicts.py` prints the classifier; `tools/sewn_tiers.py` (new)
  prints what the plan EMITS per shape. Use the second to claim a tier.
- A subagent audit and my own reading ranked the same six mechanisms at the
  top independently; where they differed (construction for item 3: smoothing
  the raw contour vs reading the anti-alias ramp) both are recorded in the
  doc and neither is decided.
