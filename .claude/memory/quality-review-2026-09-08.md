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

## Plan A PR 2 — `cfg.keep_thin_strokes`, BUILT (PR #426)

Absorb by colour, not by adjacency, on the flat lane; DEFAULT OFF, byte-
identical off (shown against the pre-change tree on this machine, not
assumed). Scope-history's fourth 09-08 entry has the OFF → ON table.

- **Fremont forced flat: 135 → 3 lost thin strokes**, the 0.5–1.0 mm band
  from 97 of 110 lost to none, for 33 → 165 regions, +25% stitches, 71 → 81
  trims, same three colour blocks. That is the "completely lost" lettering.
- **The cost lands where there is no gain**: bridge (5 px/mm JPEG) +36
  regions and +23 trims for zero strokes; drone +77 trims for 22 strokes.
  Contrasting compression/gradient fragments that clear the floors — the
  population the chain rescue was gated off the photo lane for, arriving on
  the flat lane when a photo is FORCED there. A pixel-width floor like
  `thin_strokes._MIN_STROKE_PX` is the obvious guard; measure first.
- **The plan's teal-patch prediction was wrong by 0.19 mm** (1.19 mm, proxy
  2.38 mm ≥ 2.2): ON, whitebg's patch is kept as a 27-point run in its own
  thread. The rule stands; the test pins the measured pair.
- Scoped by CALL SITE: the photo segmenters omit `layer_lab` as they omit
  the chain rescue, so the flag is inert there until PR 3. Do not "fix" that
  by passing colours from the photo lane without measuring the fragment
  explosion first.
- `parse_flag` lives in `tools/thin_strokes.py`; all three instruments take
  `--flag NAME[=VALUE]`, so any config A/B is one command.

## Plan A PR 3 — the photo lane's thin population, BUILT (PR #427) — and a retraction

- **RETRACTED: the thin-stroke recall figures of PR 1 and PR 2.** The
  instrument tested width at the MEDIAN along the skeleton, and Fremont's
  white ground — one component whose skeleton threads the gaps between
  letters, median 1.32 mm, p90 3.77, max 7.41 — passed as a 1,758 mm
  stroke, sewn and "recalled". Fremont forced flat is **61.2% → 92.7%**, not
  86.1% → 97.3%; routed OFF is 84.8%, not 94.3%. Per-component lost counts
  and the sub-1.0 mm bands were never affected. The definition now lives in
  ONE place, `digitizer_core/thin_ink.iter_thin_components` (p90 width, 3 px
  floor, `RUN_MIN_LOOP_MM / 2`, one ground), shared by engine and instrument.
  **Rule: a median width along a skeleton is not "thin" — test p90.** A
  pierced-panel test pins it.
- **The photo lane's population** (`thin_ink.find_thin_ink`): flat quantiser
  over the foreground before SEEDS, strokes leave `base_valid`, come back as
  their own label block after the palette (the enclosed-population
  precedent). Routed Fremont **18 → 3** lost strokes, 84.8% → 92.5%, at FEWER
  stitches and trims (17,400 → 16,006; 114 → 66) — 138 strokes SEEDS
  shattered now chain as regions. Drone 29 → 2 lost, 51% → 96%, +59 trims.
- **The one-ground rule** (`THIN_INK_GROUND_SHARE` 0.75): the length gate
  does not separate a stroke from a posterised band; the two-pixel ring
  around a stroke is one label, a band's is two. 0.75 keeps Fremont's 162
  strokes whole; 0.9 costs 15 of them.
- **Photographs are NOT empty** at any share that keeps Fremont whole (owl
  199 mm, chrome 230 mm at 0.75), so the plan's "empty on photographs" is
  met by a GATE: the pipeline asks for the population on the `gradient`
  class only (`thin_population=` at the `photo_segment` call). Do not widen
  it to the photo classes without measuring what the owl's 199 mm are.
- Gaulke's roof line-art is "enclosed background" and outside both the
  absorb rule and the population; the instrument (full quantisation) counts
  it, the finder (enclosed excluded) does not — say which one you ran.

## Plan A PR 4 — `cfg.lettering_min_column_mm`, BUILT and MEASURED NEGATIVE (PR #428, 2026-09-09)

- The flag widens a door-1 cluster's regularized radius to half the sewn
  floor less the pull. **It does not change the tier**: stage 7 routes every
  auto-tier shape under `min_detail_mm²` to `run_outline` before satin is
  asked and classifies on the ARTWORK polygon, so a rescued glyph sews as the
  same bean run on a fatter outline. Fremont (keep_thin_strokes on): 10 of 32
  members widened, satin row byte-identical; ENTHUSIAST's subline legibility
  1.00 → 0.917. Default None; documented as a negative in config, plan §4d,
  DOCTRINE, scope-history 09-09.
- **What would deliver the column: a stage-7 tier rule** exempting a widened
  door-1 member from the area routing and classifying it on its compensated
  width. Reverses two deliberate decisions (area routing; artwork-polygon
  classification, which exists for towels) for lettering only — Kent's call.
- The shape-context gate refuses a deliberate doubling of a stroke by
  construction (five of five); it now applies to the median redraw only and
  the OCR gate judges the widening.
- Pulls: knits 0.3, patch canvas 0.2, terry 0.6 (the floor is swallowed on
  terry — nothing widens, correctly).
- Lesson, now in DOCTRINE: a change meant to move a shape's TIER must be
  built where the tier is chosen and measured on `sewn_tiers` / the satin
  row before it is called a sewing change.

## Plan A PR 5 — the tier rule for widened lettering, BUILT (2026-09-09, the PR after #428)

- Kent's pick after #428's negative. Two stages: stage 7 exempts a widened
  door-1 member (`stage5_overlap.widened_lettering`) from the sub-floor run
  routing and classifies/sews it on `PlannedRegion.polygon` (compensated),
  with a bean-run fallback when the satin tier declines; stage 5 skips the
  "never grow back over a colour already down" clip for the same population.
- **The stage-5 half was the one nobody named.** The rule passed on bars
  over bare background and sewed nothing on Fremont: every widened glyph
  reached the classifier 0.28 mm wide — the HOLE its ground was vectorized
  with, not the 0.6 mm widened polygon. Found by instrumenting the
  classifier's input. Lesson in DOCTRINE: measure the grown polygon, and test
  the fixture the feature is FOR (lettering on a ground).
- Fremont: 8 of 10 widened glyphs sew 169 columns at 0.91 mm median (pro
  0.82–0.90); the B (aspect) and one stroke (dt_irregular) fall back to runs.
  Routed legibility 0.551 → 0.577; stitches 16,006 → 15,823.
- ENTHUSIAST: 1.6 mm subline smears — 76 columns, median 0.63, p10 0.16,
  legibility 1.00 → 0.72. The floor needs a glyph-height gate (new constant,
  gate 1, Kent's) before it can be on. Flag stays None.
- `satin_columns.passes_from_plan(shape_ids=...)` reads one cluster's columns.
- **The review found the fourth decision: sew order.** Lettering thread
  first (largest-area-first when it holds the biggest shape) → the ground
  grew over the column, clipped only by the 0.4 mm artwork → 79% buried,
  instrument still said "column". Fixed in stage 5's layer unions
  (`sewn_footprint`: a widened member's column replaces its artwork in
  `earlier`/`later`/`covered_by`); test asserts the premise and the exposed
  width. Also `_comp_axis` → isotropic satin for widened members.
- **Rendered, and the numbers are not the verdict**: at 2.2 mm cap height
  the 1.0 mm column fills Fremont's counters (ON EST reads "OS"); the pro's
  file (not in the repo) was recorded legible at 0.82–0.90 on 09-03 — the
  crops put that to Kent with the height gate.
- Pre-existing, not this PR: `forced_class="photo_subject"` on the small
  synthetic bars fixture segfaults (exit 139) in
  `stage2_photo_segment._seeds_superpixels`; reproduced 2026-09-09.

## Plan B PR 2 — `cfg.subpixel_edges`, BUILT (2026-09-09)

- `digitizer_core/subpixel.py` + the hook in `stage4_vectorize.vectorize`
  (CHAIN_APPROX_NONE when on; Lab once per image; per ring the near-floor
  exemption is judged on the pixel-centre polygon BEFORE the vertices move;
  `meta["subpixel_accepted"]` share). Default OFF, byte-identical.
- **Estimator: area integral, not the 0.5 crossing** (±0.09 px interpolation
  bias vs −0.05..+0.01). Two passes (±1.5 then ±2.5 px; the enclosed white
  disc's label sits 1 px inside its edge). Isolated rejects (≤2) dropped
  before DP (inner corner pixels = inward spikes). Corners (±3-step chords
  turning ≥60°) read along each side and intersected, reach ≤ 0.75·√2.
- **Fixture traps**: the 4x fixtures are good to 1/8 px; cv2.circle at 4x
  puts the true radius ~0.1 px off `r + 0.5/S`; test on a 16x disc and on
  a straight edge at four phases. `_disc`/`_straight_edge` in
  `tests/test_subpixel_edges.py` carry the exact conventions.
- **Reading the result**: vertices on the edge (ladder `vertex_*` columns,
  added); the boundary offset gets worse on the circle (inscribed polygon,
  DP sag) — PR 3's floor, not a regression. DOCTRINE has the entry.
- Orange rectangle at 800 px: one corner 0.25 px short (its vertex max
  0.03 mm) — the only residual; not chased.

## Plan B PR 3 — the refinement floor and gate keyed to acceptance, BUILT (2026-09-09)

- `_refine_curves(accepted=...)`: per chord, ≥80% accepted raw points →
  floor 0.25 px (else 1.0); inserted vertex = the midpoint's own sub-pixel
  point when accepted; `_CURVE_MIN_PX_PER_MM` gate lifted when the flag is
  on. OFF path byte-identical (`accepted=None`).
- **Where it bites**: the 15° turn rule binds on large radii (r ≳ 117 px:
  the 15° chord is longer than 30 px, whose sag exceeds the pixel floor
  anyway), so the floor changes nothing there; on SMALL radii (the ring's
  7 mm hole, r = 30 px at 400) the pixel floor blocked the 15° polygon and
  the quarter-pixel floor allows it: 40 → 70 vertices, Hausdorff 0.285 →
  0.140 mm. The unit test uses a 30 px disc for exactly this reason (a 100
  px disc shows nothing).
- cv2.approxPolyDP is not eps-minimal: on a smooth 16x disc it returns the
  same 32-gon at eps 0.8, 1.0 and 1.5 — don't reason from eps to chord
  count.

