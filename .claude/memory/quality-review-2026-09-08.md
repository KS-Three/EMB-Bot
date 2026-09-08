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

## PR 1 of the thin-stroke plan — BUILT the same day

`digitizer/tools/thin_strokes.py` and `digitizer/tools/legibility.py`, with
tests; baseline tables in scope-history 09-08 (second 09-08 entry). What
they said on first run:

- **The two lanes lose DIFFERENT bands, exactly as the plan's §3 predicted.**
  Fremont routed (gradient): strokes under 0.5 mm sew at 53% recall, the
  0.5–1.0 mm band at 90%. Fremont forced flat: the sub-0.5 band drops to
  26% and the 0.5–1.0 band to **51%** (97 of 110 strokes lost) — the
  small-shape absorb, not the superpixels. "Fix the lane" is wrong on its
  own; PR 2 (absorb by colour) and PR 3 (thin population) each own a band.
- **Gaulke is the standout and the lane is not why: its background is the
  BLACK FRAME.** 42 of 46 thin strokes lost on both lanes, lettering 0.32.
  The PNG is a white card in a black frame; `bg_mask` is 80% of the raster,
  `enclosed_mask` 16% of the design, so every black element inside the card
  is "enclosed background" and unstitched by default — the roof line-art
  reads 0%, the letters are bare holes in a fill. A product default, not a
  segmentation defect. First thing to look at before PR 2 claims gaulke.
- **Forced flat is better on drone (74 → 90%), bridge (79 → 98%) and
  golden_tee (81 → 89%)**, worse on Fremont and level on screenshot.
- **Legibility is a LOWER bound on lettering loss.** Fremont's THE reads
  1.00 at confidence 95 on a render that shows "T H C" (the E's middle arm
  never sews): tesseract's word model fills it in, and the best-over-variants
  read keeps the filled-in reading. In single-line mode with no
  preprocessing the confidence had caught it (80 → 40) — an earlier draft of
  this entry and the tool's docstring claimed the confidence drop as the
  detector; measured on the final code it is not. The thin-stroke
  instrument sees the arm directly: T 100%, H 82%, **E 74%**. Read both
  instruments; never quote a per-cluster 1.00 as "the glyphs sew".
- Fremont's tagline is not a text cluster, so legibility cannot see it at
  all; `thin_strokes` reads its 0.30 mm tan strokes at 68% and 0%.
- Traps the instruments needed: a webp's 2-px compression halo quantises to
  its own label and read as a 34.6 mm "stroke" 0.07 mm wide (hence
  `_MIN_STROKE_PX` 3, a PIXEL floor because the artefact is a raster one);
  the pipeline's default 12 colours is not what a customer gets — the
  corpus runs at the Studio's 6; ENTHUSIAST's render reads as nothing until
  the ink is thinned by ~0.25 mm; Becker's art is unreadable at 1.46 px/mm
  (a false zero without the confidence floor of 60) while its RENDER reads
  BECKER 96 / MARINE 95.
- `logo_drone_thermal_badge.png` is byte-identical to `drone_render.png`
  (blockcensus already knew); both tools run it once, checked by digest.

## Plan B PR 1 — the edge truth ladder, BUILT the same day

`digitizer/tools/edge_truth_ladder.py`, 10 tests; baseline in scope-history's
third 09-08 entry. The one thing to carry:

- **Two floors under a stage-4 polygon.** Below ~15 px/mm the deviation
  from the true curve is the PIXEL and falls with resolution. Above it the
  floor is the 0.2 mm Douglas-Peucker tolerance's chord sag and does NOT
  fall — the ribbon keeps 37 vertices and 0.065 mm spread from 400 to 1600
  px. A sub-pixel vertex fed to the same simplifier lands on the same floor.
  So the plan's acceptance criterion was restated (plan §5): ON at every rung
  ≤ OFF's 3200 rung; PR 2 alone should move only the 200/400 rungs; the
  ribbon cannot move before PR 3 (the refinement floor). Never quote
  "flat across the ladder" as the pass — OFF is already flat above 400 px.
- The existing `curve_turn_deg` refinement (ON by default, 15°, gated at
  20 px/mm) reaches only the 3200 rung: there it halves the ring's spread
  and leaves the circle alone (10° chords). `--flag curve_turn_deg=0` is its
  OFF arm.
- cv2 draws ROUND caps on thick polylines (the generator's docstring says
  square); pixel centres are integer coordinates; a disc covers r + 0.5.
- Trap: the hole's sign. Minus inside the truth's material, plus outside,
  for shell and hole alike — a first draft had holes inverted and a
  synthetic square-with-a-hole caught it.
