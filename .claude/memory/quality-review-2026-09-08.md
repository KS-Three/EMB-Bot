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

## Plan B PR 4 — the flip, `subpixel_edges` default ON (2026-09-09, Kent's approval)

- Config default True; the tests that documented the OFF baseline pin
  `subpixel_edges=False` explicitly (the ladder's `rungs` fixture and
  ribbon test via `--flag subpixel_edges=false`; `test_subpixel_edges`'
  OFF arms).
- **Goldens are re-captured on ubuntu-latest, never here**: the remote
  container drifts on the photo lane (enthusiast, 20 coords). The
  temporary `.github/workflows/recapture-goldens.yml` (workflow_dispatch,
  `pre_ref` = the engine with the flag off) runs
  `recapture_flat_lane_key.py <key> --pre-change-tree` per key and pushes
  the JSON back to the branch; `tools/pushcomp_pins.py` prints the pushcomp
  tuples in both trees so the inline pins are re-pinned with the same proof.
  Remove the workflow with the commit that lands the goldens (the 08-17
  precedent).
- `curve_turn_deg` stays 15° (10° would meet the ladder criterion on the
  ring — Kent's), upscaled sources stay declined.
- **The flip's fallout — 21 red, 10 of them goldens/pins, the rest
  pixel-balanced mechanisms** (DOCTRINE 2026-09-09, "A default that moves
  every polygon by a pixel"): the "N" foot's `medial_axis` pinhole diamond
  (`_collapse_pinholes`; `thin()` is a no-op on it — tried), the ribbon
  head's taper-zone crowding (inserted stations now interpolated along
  each rail; no crowding unless the long rail would gap over two pitches),
  the unguarded-prune injection test pinned to `subpixel_edges=False`
  (probed 80–180 mm ON: the coincidence is gone), three pins re-pinned with
  their new numbers (whitebg vertices 117/128/141; the ramp's single-thread
  14.60 via cone 3830; the owl hoist on the old trace, ON plans no
  revisit). The `resolution_gated` fix in `_refine_curves` (unread chords
  under the 20 px/mm gate are not split) and preflight's `to_px` rounding
  (grader masks match `_region_footprint` again) landed in the same commit.
- **Goldens landed** (run 34310689566, 66 s): main b13517d reproduced
  whitebg/alpha/ribbon byte-for-byte on the runner first; whitebg 4558 →
  4550, alpha 4534 → 4576, ribbon 999 → 991 (its id moved); enthusiast
  refused (platform red, stays deselected); pushcomp re-pinned on three,
  towel left. **`workflow_dispatch` is a 404 on a workflow that exists only
  on a feature branch until something has run it** — a one-shot `push`
  trigger on the file's own path registered it.
- **The suite on the fixed tree found six more** (DOCTRINE's entry has
  them): the grader rounding moved two blocking thread-match findings on
  sub-2.1 mm² shapes (42 vs 57 scoreable px under the 50-px floor; a
  hairline fallback that fired at 0 px now sees 2) — re-pinned, flagged as
  a scorecard move for Kent; `loaded` is the plan's sewn blocks now (no
  severity moves on eight fixtures, better-spool naming back); the PLUS
  crossing decomposes 2 vs 3 across scales (adjacent 3-way nodes — the
  next mechanism, not built).

## Item 5 PR 1 — junction clustering in stage 6, BUILT (2026-09-09, Kent's pick after #432)

- `stage6_satin._cluster_junctions`: node-to-node edges ≤ max(3 px, 0.5 ×
  half_px) contracted onto the deepest-DT pixel, arms re-rooted by way of
  the stub pixels; loops returning to the cluster within 2× dropped too.
  Threshold read off `tools/junction_nodes.py` (bump 0.2–0.4, trough
  0.4–0.5, tail from 0.5). Bounded above by `_MIN_STROKE_HALFWIDTHS`.
- **The loop rule was found by the bracket-tab test**: stubs alone bared
  7 mm² at enthusiast 150's tab tip (a tiny loop made a cap a five-arm
  junction; the old stub carried the uncapped stroke 0.74 mm further).
- Footprint 14 × 2: interior over-wide 948 → 830, tail 107 → 121 (new caps'
  terminal fans), stitches +0.21%, trims −1, becker bare 16.0 → 9.0 (worst
  8.2 → 9.0, the K crotch — PR 2's), enthusiast 150 worst 4.5 → 1.2. No
  golden moved (flat-lane keys have no branch node) — no re-capture.
- Predictions missed and recorded in the plan's §4: becker's stroke and
  trim counts went UP by one each.
- Renders in `docs/renders/junction-clustering-2026-09-09/`.

## Item 4 — the wide-column policy, `cfg.wide_columns` BUILT, DEFAULT OFF (2026-09-09, Kent's pick after #433)

- 6.5 mm ceiling = the pro's MARINE p99 (crosses p50 4.8–4.9, p90 5.0–5.2,
  sewn WHOLE — rendered), threaded as one number (`machine.satin_ceiling_mm`)
  through all four load-bearing places; `_fold_caps` (0.7 × bend radius)
  is the overlap guard. Off byte-identical; no golden moves.
- **The 2026-09-02 premise moved**: the apex is 0 crossings at 5.0–8.0 mm
  with or without the guard. The guard is load-bearing on Becker's bends at
  80 mm only (coverage_max 7.07 → 5.08); swept 0.5/0.7/0.9.
- **Our DT p90 over-reads bold letters by their junctions** (5.1–8.0 vs the
  pro's 4.8–5.0 stems): a junction-aware width statistic is PR 2.
- ON: exactly the band (MARINE letters, alpha/whitebg's `S09c5bd0d`,
  drone's `S0bae4b0d`); MARINE −13% stitches but 251 self-crossings at feet
  and junctions, +18 trims, drone wing 7 mm² bare. **Rendered before
  pricing** — the letters got worse. Ships OFF; item 5's next PR (serifs as
  columns, junction cover) is what makes the band worth flipping.
- `tools/wide_columns.py` (band table, `--compare`, `crossing_pairs`).

## Item 5, PR 2 — the census overturned the serif brief; the satin junction cover shipped (2026-09-09, Kent's pick after #434)

- `tools/letterforms.py` first: every column END (stroke or Goldman member,
  as `_satin_joined` sews them) — kind, reach, cap obliquity, flare along
  the cap face, seated crossing pairs split WITHIN a column vs BETWEEN
  columns; bare artwork per junction node.
- **The 251 "self-crossings" were mitres**: 0 within any column, 359
  between, all at two Goldman joins (the A's apex, the R's crossbar/leg
  join). Corpus: becker 80 0/716 (off 6/714), drone 0/486, enthusiast
  0/305, fremont 0/263. **The pro's sewn MARINE carries 2,593** within
  its own passes. `crossing_pairs` is a defect only WITHIN a column.
- **No serif in the feet**: the M's stems are a constant 5.35 mm chord to
  the baseline (146 × 91 px source — the font's foot serif is under a
  pixel). ENTHUSIAST's slab serifs already sew as Goldman members. The
  serif column was NOT built — no fixture defect, and synthetic evidence
  is barred.
- **Shipped: `cfg.satin_patch_junctions = "satin"`, DEFAULT OFF** — the
  grader's patches as satin columns along their long axis
  (`_principal_spine`), FIRST in the shape under the arms, each turned to
  end nearest the first run and joined by needle-down web travel; wider
  than the ceiling or degenerate → the tatami patch for that hole. Becker
  80: 9.0 → 0.0, B 76 → 88 at +122 st / +2 trims (tatami +297 / +3);
  fremont under `wide_columns` 128.2 → 13.0 for +10.6% (tatami 6.0 for
  +34.5%); over-fire at becker 100 wide (0.0 both ways, TRIM_HEAVY on +2
  trims, B 88 → 76 — the tatami's too). A second finder round: measured,
  no grader movement, dropped. Flip sheet, 26 fixtures @ 80 mm: the same
  4 moved and 2 grade-ups as the tatami at +313 st / +7 trims vs +733 / +9.
- Renders: `docs/renders/junction-cover-2026-09-09/`. Tests:
  `tests/test_junction_patch_flag.py` (14).
- PR 3 candidate: the junction BLOB as its own column with the arms
  ending on it (the pro's A apex), and a junction-aware width statistic.

## Item 5, PR 3 — measured out before engine code (2026-09-09, Kent's pick after #435)

- `tools/junction_blobs.py` (per junction: node radius vs arms' halves, arm
  count, merge decision per arm, the blob = medial balls bigger than the
  arms' own, layers / bare / seams inside it; per shape the arms-only p90)
  and `tools/pro_layers.py` (the pro's file in our frame: layers and thread
  inside our letters and blobs).
- **The pro stacks MORE at junctions than we do**: MARINE letters ours p95
  2.4–3.4 / max 3.8–5.2 vs the pro's 4.1–6.0 / 5.5–11.6; every blob the pro
  is above us; the pro sews MARINE with +58% thread (12,109 vs 7,642 mm)
  and +39% penetrations. #434's "clumps" are angle meetings over LESS
  thread. No column to add.
- **A bold letter at 17 mm is 45–90% junction ball**; the blob is a disc
  the size of the apex, not the pro's slab (which the font defines). The
  arms-only width statistic flips one verdict (the M 7.34 → 5.67) and reads
  drone's 9.4 mm wing as 1.08 — not a classifier input. DOCTRINE has both
  rules and a dated bracket on the earlier "junction-aware statistic" line.
- Open question for Kent: the density gap (+58% thread in lettering:
  spacing and underlay, Law 27/50, a sew-out question) vs items 6/7.

## Item 6 — `cfg.satin_rail_comp` BUILT, DEFAULT OFF (2026-09-09, Kent's pick after #436)

- The pull on the rails: stage 5 leaves satin-tier shapes on the artwork,
  `_rail_points` casts to the artwork edge and pushes each rail along its
  cross by `pull_comp_mm` (`_push_rails`, counter guard at `min_detail_mm`);
  caps end at the artwork, end cutback = push only; every field-fed
  threshold restated in sewn terms (`half_extra_mm` in `extract_strokes`,
  corridor cap, tuck, oversize, zigzag decision); the underlay runs to the
  caps; `poly_link` grown. Instrument `tools/rail_comp.py --compare`.
- Results (pique 0.3): IoU vs target ENTHUSIAST 0.876 → 0.897, drone
  0.797 → 0.838, Fremont 0.675 → 0.836, Becker 0.887 → 0.884; trims −4 /
  −13 / −1 / +4; stitches +3% / −1% / +1% / −9%; thread outside the
  artwork → 0. Predictions that failed: trims unchanged, stitches ±3%,
  byte-identical OFF (the tracer fix moved two fixtures).
- **Skeleton choice measured both ways**: artwork (shipped) vs grown-with-
  artwork-rails (drone 0.829, Fremont 0.813, Becker 34 trims / 3 strokes
  on the A vs 7). The growth had been smoothing the outline; the fidelity
  is mostly the rails. Kent's call — one line at `extract_strokes`.
- **Tracer defect found and fixed ON BY DEFAULT**: `_skeleton_edges`
  self-looped a junction clique and dead-ended on L-corner fillers,
  stranding chains into fragments that each sewed to both caps (the H:
  stem ×5, coverage 9.27). OFF cost: drone `S60de6f78` +2 st, ENTHUSIAST
  house angle 1.4445 → 1.4757° (+2 st over 11 shapes). The JS
  `skeletonEdges` still has it.
- Open: which skeleton; flip after a sew-out; the 2× pull meaning
  (Python per rail, JS total).

## Item 7 — `cfg.design_angle` BUILT, DEFAULT OFF (2026-09-09, Kent's pick after #438)

- Instrument `tools/design_direction.py` (`--pro` reads the sewn Becker
  files the scorecard's way). **The pro holds ONE fill angle at every size
  (20.5–20.6° in the slab, 12.6–14.2° in the small fills, three files at
  76.5 / 95.7 / 101.9 mm) regardless of aspect** → no per-shape override,
  no threshold. Ours at 95.7 mm: nine fills spread to R 0.15 (house 2°,
  derived fills 85–91°); `direction` 0.0 (raw 0.43).
- **No objective derives the pro's 20°**: the column objective summed over
  the design picks 90° (the slab: 50 columns at 90, 58 at 0, 202 at 22.5),
  the principal axis 0°, the house 2°, the trade 45°. The house is the
  constant-free nearest → the flag takes the house where the lettering's
  lines agree within the 30° cap, else the gradient lane's own shared
  angle where the design holds one, else the design-wide column objective
  (the per-shape one's 16 candidates plus the principal axis — the PCA
  candidate was missing at first and a lone fill moved for no reason).
- ON at 76.5 / 95.7 / 101.9 mm: spread → 1.0 / 0.999 / 0.995; `direction`
  0.388 / 0.0 / 0.0 → 0.41 / 0.289 / 0.249; stitches −1.5% / +4.2% / +6.3%
  (the slab's columns — the pro pays it too); trims 38→39, 27→22, 27→25.
  Forced flat 80 mm: Bridge Bar 15 fills 0.781 → 1.0 at −2.6% (39 satin
  leaned); gaulke +7.5% (ground leaves its own 0° for the house's 155°);
  Fremont +3.9%; Golden Tee −1.6%. Photo classes (rule 3, the objective): R 0.42–0.91 → 1.0 at −0.1% to +1.7% stitches, scene stub +7 trims. Corpus 80 mm: 19 of 26 move, −0.08% stitches, +1 trim — outside the photo fills it is satin leaning. Rule 2 (the lane's ramp angle) came from that sweep: white_icon's strokes at 0° against 134° rows.
- At 80 mm routed, every real logo takes the gradient lane (one angle
  already, no `stitch_shape` fill) — the review's Bridge Bar spread is a
  forced-flat population. Read a spread claim against the lane (DOCTRINE).
- The last ~20° is a taste constant — Kent's; photo classes not gated (no
  measured loss, no pro photo file); non-lettering satin leans as briefed.
- Wiring: `designangle.set_design_angle` after the house pass (stage-4
  polygon, since stage 5's `_comp_axis` reads the key); stage 7's
  `_fill_angle_for` (five sites, one precedence); satin's fallback before
  the per-stroke tangent. `tests/test_design_angle.py` (7). Byte-identical
  off on ten fixtures. Renders in `docs/renders/design-direction-2026-09-09/`.

## Next pick — item 8, the gradient-lane colour bundle (Kent, 2026-09-10 00:30Z)

Chosen right after PR #440 (item 7) opened with auto-merge armed. **Do not
push to `claude/emb-bot-quality-review-acwj61` until #440 merges** (a push
lands in it and re-runs the 30-minute digitizer job); then `git fetch
origin main && git merge --ff-only origin/main`. Item 8's brief (review
§8): the five built colour flags — `enforce_color_cap`,
`resnap_mask_matches_grader`, `revalidate_small_shapes`,
`bind_resnap_all_classes`, `dissolve_phantom_blends` — measured TOGETHER
as one set with a render sheet per fixture and one decision doc to default
them from; it must say which flags survive item 1 (the real-logo lane).
Their individual measurements: `docs/pending-flag-decisions-2026-09-06.md`;
`dissolve_phantom_blends` was banked OFF by Kent 2026-09-04 before the
page-mask bug was fixed — re-present, do not re-open.

## Item 8 — the colour bundle MEASURED (2026-09-10, PR #441)

- `tools/flip_sheet.py` grew the `color_cap` single, `colour4` (the four
  not ruled) / `colour5` (+ the ruled `dissolve_phantom_blends`) bundle
  arms, a `PROXIES` table (forced flat, OUTSIDE ARMS so `forced_class` is
  never a "single"), `--fixture`, `--max-colors`, and a stops column.
  Renderer takes repeated `--flag`.
- At the engine budget (12): `colour4` 9 moved, −22 cones/−22 stops/−22
  blocks, 3 grades up, none down; `colour5` 10 moved, −4,023 st, −77
  trims. NOT the sum of its rows (cap −18 + bind −17 → −22 together).
  chrome's D→C is the `mask_small` pair alone. At the Studio's 6: `colour4` −47 cones/−43 stops (every real logo lands ON the promised 6), `colour5` −4,509 st/−80 trims; one grade down, summit_badge (synthetic) F 16 → F 0, a new THREAD_MATCH_POOR block from the cap's merge.
- **The sheet's budget is 12; the Studio ships 6** — different questions
  for the cap (drone 23 → 6 at 6; 17 → 12 at 12). Every row now records
  its budget; one budget per `--out`.
- **Forced flat is NOT the item-1 answer the docstrings predicted**:
  `flat_colour5` −28 cones on five logos; Golden Tee sews 24 cones under
  12 forced flat — the re-snap escapes past the flat lane's hard cap too.
  Flat singles: the bind −26 cones, the cap −21 (drone, golden tee), the mask −4, the floor 0, the dissolve BYTE-IDENTICAL on all nine — item 1 retires only the dissolve.
- Forcing the flat lane on a PHOTOGRAPH costs ten minutes a fixture and
  answers nothing; `--fixture` exists so the proxy runs on logos only.
- Two self-kills from `pgrep -f`/`grep` patterns that matched my own
  shell: match with a bracketed literal (`flip_sheet[.]py`) and never put
  the restart command in the same call as the kill.
- Shipped as PR #441 (ready-for-review 03:18Z, auto-merge armed). Next: Kent's flip decision on the four not ruled (`colour4`) and his re-read of the halo render; then the next build pick.

## Kent's rulings 2026-09-10 03:30Z — flip the four as one set; item 9 next

- **Flip `colour4` ON by default** (`enforce_color_cap`,
  `resnap_mask_matches_grader`, `revalidate_small_shapes`,
  `bind_resnap_all_classes`) — one PR, AFTER #441 merges (auto-merge
  armed; no push to the branch until then). `dissolve_phantom_blends`
  stays OFF (his 2026-09-04 ruling stands). The flip moves goldens: the
  recapture is ubuntu CI only, never this box. Every "DEFAULT OFF" claim
  for the four in docs and docstrings must move with it (test_doc_claims).
- **Then item 9**: enclosed letter bodies decided by garment colour, not a
  global unstitched default (review §9).
- **Flip in progress (03:40Z, local, unpushed)**: the four defaults are True in config.py with docstrings; docs moved (MASTER_SCOPE defects 15/28/31, DOCTRINE 1443, scope/1, pending-flag-decisions, flip-sheet doc, decision sheet DECIDED, scope-history entry); flip_sheet.py has `off4`/`flat_off4` (the pre-flip engine). Pending: the pinned tests (`test_flag_defaults_off` ×2 → ON; the `_default_digest` vs explicit-False contracts in the bind/small/mask tests → default == explicit True), goldens only if the flat-lane/photo-lane/pushcomp runs move (the bundle left whitebg/alpha/ribbon untouched at 12, so probably none), full suite, then push after #441 merges (rebase the local commits onto origin/main first).
- **The flip's own test run found a loss the sheet understated (04:30Z)**:
  `test_bridge_bar_keeps_its_artwork` names `0501` Sun as artwork and lost
  it under the four. Measured: the Bridge Bar disc's pixels are
  (251, 235, 65), ΔE00 1.0 from Sun; the flipped engine sews the disc
  `6031` Limelight, 7.0 away, at 12 AND at 6 (the `_mc6` sheet's middle
  panel is lime where the left is yellow — I had written "a touch greener
  … the same logo" and Kent ruled on that). It is the BIND's price, not
  the cap's (`resnap_bind` alone drops Sun; `color_cap` alone keeps it).
  Mechanism: stage 2 hands the palette the disc REGION's mean,
  (223, 220, 77) — the black lettering, bird and rope inside it pull the
  mean 12 ΔE00 darker and greener through their anti-aliased edges — and
  the k-medoids palette rightly picks Limelight (2.5) for that mean; the
  unbound re-snap used to read the source pixels and correct it to Sun
  (double-loading Lemon beside it); the bind holds the palette's answer.
  Fix upstream: a robust region colour in stage 2 (median, or the mean
  over the region's modal pixels) — candidate next build; the decision
  sheet (status line, §2, §4, §5.3), MASTER_SCOPE's item-8 block and the
  flip PR body carry the correction. Shipped as ruled, flagged, not
  withheld (his 2026-09-04 ruling on arming).
- **Item 9 built in a scratch worktree while the flip's suite ran**
  (`scratchpad/item9-wt`, local branch `item9-wip`, cut from the flip
  commit) so the suite ran on an untouched tree; it lands on the lane by
  cherry-pick after the flip PR merges. The main venv's python imports the
  WORKTREE's package when cwd is the worktree's `digitizer/` (sys.path[0]
  beats the editable install's finder) — verified before trusting a run.
  The Studio's component specs cannot run there (vite refuses the
  symlinked node_modules outside the root: 13 files, "Cannot find module
  /@fs/…"); lib specs run fine; the full vitest runs on the main tree
  after the cherry-pick.
- **Shipped as PR #442 (05:05Z, ready-for-review, auto-merge armed at
  `blocked`, check-in at 06:06Z).** Full suite on the flipped tree: 3
  failed / 2,183 passed / 3 skipped / 7 xfailed in 29 min, the three being
  CI's platform reds. No golden moved. Nothing pushes to the lane until it
  merges; item 9 waits in the worktree.

## Item 9 — `cfg.enclosed_by_garment` BUILT, DEFAULT OFF (2026-09-10, Kent's pick after #441)

- The rule: a border-flood hole (colour KNOWN, `Prep.bg_rgb`) sews by
  default when ΔE00(hole, garment) > 10 (`DELTA_E_CLEARLY_DIFFERENT`,
  pinned); one verdict per design (`stage4_vectorize.garment_sews_enclosed`),
  read by the stitched seam AND the colour cap's ranking (a hole that will
  sew is sewn area — without that the cap merged whitebg's White into a
  kept cone because "holes buy no slot"). Alpha holes untouched. Override
  wins; `meta["enclosed_by_garment"]` survives the override so the panel
  can say why. Studio sends `project.fabricRgb` as `garment_rgb`.
- Measured at 12 / 80 mm: whitebg and Golden Tee sew their white holes
  white on Navy/Black (+571 st / 1 cone; +3,027 st / +7 tr / 1 cone) and
  are byte-identical on White/Natural (6.4 from Natural, under 10);
  gaulke's 46 black bodies sew on any light garment: +3,979 st and
  **+43 trims** (23 → 66), and they are the FRAGMENTS the vectorizer kept
  when they were holes — STEEL ROOFING & SUPPLY reads, GAULKE INDUSTRIES
  does not; `keep_thin_strokes` is the other half. Black: byte-identical.
- Threshold: at 5 Natural would sew white holes white on off-white (the
  08-15 verdict's "wrong" case); at 10 it never does. §5.1 is Kent's.
- **Shipped as PR #443 (05:58Z, ready-for-review, auto-merge armed).** Pushed
  after the changed-package tests, the Studio suite (1,094) and the doc
  checkers; the full digitizer suite was still running on the same tree
  (the first run, in the worktree, died silently at 32% with no traceback,
  no OOM and 15 GB free — cause unknown; restarted on the main tree). PR
  body carries Kent's three decisions; the AskUserQuestion follows.
  Full suite on the landed tree: 3 failed / 2,202 passed / 3 skipped / 7
  xfailed in 24 min — the three platform reds; PR body updated with it.

## Kent's rulings 2026-09-10 ~06:40Z — item 9 flipped ON; threshold 10; alpha holes stay toggled

- Answered the three-way AskUserQuestion with every recommended option:
  threshold 10, alpha holes to the review toggle, **flip ON now**. He said
  "in this PR" but #443 had auto-merged at 06:34Z while the question was
  open, so the flip is its own PR on the lane restarted from main (the
  merged-PR rule: never stack on merged history).
- The flip is one line + the pinned test + MASTER_SCOPE/plan §7/scope-history;
  `garment_rgb` appears in no other test and no golden names a garment, so
  nothing else moves. The e2e specs drive whitebg (6.4 from Natural, declines)
  and the alpha enthusiast logo (unknown colour, declines).
- **Shipped as PR #444 (12:56Z, ready-for-review, auto-merge armed at
  `blocked`, check-in scheduled ~60 min out).** The lane is restarted on
  main (1ed05ae, #443's merge) with the flip commit on top; this memory
  note is committed locally and pushes only after #444 merges (a push into
  an armed PR resets its checks).

## Next pick — the Bridge Bar yellow: a robust region colour in stage 2 (Kent, 2026-09-10 12:57Z)

- Chosen over item 1 (the real-logo lane), item 11 (legibility yardstick)
  and item 12 (fill travel under cover). Scope: stage 2 hands the palette
  each region's plain MEAN (`stage2_photo_segment.py`, the `region_labs`
  list before `select_palette`); a big region full of inclusions gets a
  colour no pixel carries (Bridge Bar's disc: (223, 220, 77) for pixels at
  (251, 235, 65), 12 ΔE00). Flag first, DEFAULT OFF, byte-identical off;
  measure on the flip sheet's 26 fixtures; the photo-lane snapshot golden
  pins stage 2, so a flip is a CI recapture.
- **Built (13:05Z):** the seam `_region_pixels_lab` + `_region_lab` (OFF ==
  the old mean byte for byte; the photo-lane and flat-lane goldens pass),
  `region_colour_candidates` (mean / median / modal mean),
  `cfg.robust_region_colour` DEFAULT OFF, `tools/region_colour.py`, the
  flip-sheet arm `region_colour`, 10 tests. **Census (20 lane fixtures, 422
  regions):** median moves 155 regions' spools, modal mean 169; 33 bimodal
  (26 on the screenshot); the real logos move most of their AREA (Bridge Bar
  66.5%, Golden Tee 54.4%, drone 66.8%), photos and ramps nothing. **The
  statistic is the modal mean**: on the disc, mean → Limelight, median →
  Lemon (2.1), modal mean → Sun (1.0). A per-channel median is a colour no
  pixel need carry. Next: the flip sheet `off` vs `region_colour` at 12 and
  6 (fresh caches `build/flip_sheet_rc*` — the item-8 caches' `off` rows are
  the PRE-flip engine), Bridge Bar / Golden Tee / drone renders, PR after
  #444 merges, then Kent: the flip (a photo-lane snapshot recapture on CI if
  any golden fixture moves).
- **#444 merged 13:41Z** (all four checks green at 13:40); the lane is
  rebased onto its merge (698ce03) with the region-colour commits on top,
  still unpushed until the flip sheet at 6 and the full suite are in.
- **Measured (13:45Z):** flip sheet `off` vs `region_colour`, fresh caches
  `build/flip_sheet_rc` (12) and `_mc6` (6): 11 move / 15 identical at
  both budgets. At 12 Bridge Bar 12 cones + a repeated 0108 (13 blocks) →
  11/11, disc → Sun, COLOR_STOPS_HEAVY gone, F 0 → F 4; screenshot 12 → 10
  cones; Golden Tee 11 → 12 cones but blocking 4 → 2; the photo-scene STUB
  +3,382 st / +29 tr (+1 spool, 21 → 31 regions). At 6: net −2 blocks / −2
  stops; Bridge Bar −768 st / −28 tr (7 → 6 blocks, the repeated cone) with
  +1 blocking thread; Golden Tee 9 → 7 blocks, −1 blocking; screenshot −1;
  drone +1. The Golden Tee render's "0015 → 3971" is the CAP remapping its
  unstitched holes at 12 (13 medoids for 12), not the region colour —
  invisible on fabric, and on navy item 9 keeps White. gaulke and Fremont
  byte-identical (their big regions are already pure).
- **Trap (13:55Z, DOCTRINE):** `run_preflight(image=<PIL RGB array>)` grades
  colours REVERSED (`_load` treats an ndarray as cv2's BGR); the scorecard
  and flip sheet pass the PATH. My first blocking-findings census read the
  disc as (63, 235, 251) and blocked Sun at 43.6 with a teal remedy. Also:
  two self-kills again — `pkill -f 'x[.]py'` in a call whose text ALSO
  names x.py elsewhere (sed/nohup) kills the shell (exit 144). Kill by PID,
  in its own call.
- **Full suite caught the seam (14:40Z): 12 failed** = 3 platform reds + 9
  from the OFF path — I had averaged Lab pixels where the engine averages
  RGB and converts once (`rgb_to_lab(mean)` ≠ `mean(rgb_to_lab)`). The
  photo-lane byte-identity golden (`test_photo_lane_byte_identical.py`,
  which I had NOT run — only the flat-lane and dispatch goldens) failed on
  drone, summit, the white-icon repro and the subject stub; three
  `test_thread_revalidate` facts, `test_bridge_bar_keeps_its_artwork` and
  `better_spool[bridge]` moved. Fixed: the seam passes RGB pixels and OFF is
  the old expression exactly; candidates' `mean` is that point. DOCTRINE
  entry. Every `off` row of both flip-sheet caches, the census and the
  renders' OFF panels were the wrong engine → recomputed before the PR.
- **Corrected census (exact OFF point):** median moves 146, modal mean 163
  of 422 (was 155/169 under the Lab mean); Bridge Bar 56.9% of area, Golden
  Tee 33.8%, drone 65.2%, screenshot 65.0%; 33 bimodal (27 screenshot).
  Renders re-made on the exact engine; the change lists are the same.
- **Exact-engine blocking census at 6 (15:25Z):** Bridge Bar 2 → 3 blocks,
  all shards, its 1,023 mm² disc off the list (Limelight warn 7.5 → nothing
  under Sun; the script was never a finding); Golden Tee 4 → 3, all shards
  (the Lab-mean OFF's "Black 40.4 on a red shard" and "153 mm² yellow-orange"
  were artefacts of the wrong OFF); screenshot 5 → 4, the 470 mm² ground
  off the list; drone 5 → 5 with the 211 mm² orange entering at Pumpkin 10.9
  (Fox Fire 3.5 by colour) — the one large shape that gets worse, a
  six-cone budget trade. Corpus block count level at both budgets.

## HANDOFF — region colour, where things stand (2026-09-10 ~15:35Z)

- **Lane `claude/emb-bot-quality-review-acwj61`: 11 local commits, UNPUSHED,
  on top of main 698ce03 (#444's merge).** All the region-colour work:
  seam + flag (DEFAULT OFF) + census tool + flip-sheet arm + 10 tests +
  renders + plan §0–§5 + MASTER_SCOPE (800) + scope-history + DOCTRINE (two
  entries) + memory. Working tree clean. Nothing is armed on the branch;
  pushing is safe once the suite is green.
- **Running:** the full digitizer suite on this tree —
  `/tmp/claude-0/-home-user-EMB-Bot/3f5c00bb-5357-55fc-9cff-fc33fcf55405/scratchpad/rc/full_suite2.txt`
  (started ~15:05Z; `EXIT` line when done). Green = exactly the three
  platform reds (`test_flat_lane_byte_identical[enthusiast]`,
  `test_stage2_photo_segment[enthusiast]`, `test_pushcomp[whitebg-towel]`).
  If the container restarted and the log has no EXIT: re-run
  `cd digitizer && .venv/bin/python -m pytest -q -n auto -p no:cacheprovider`.
- **Then, in order:** (1) fill `<<COUNTS>>` in
  `…/scratchpad/rc/pr_body.md` with the suite line (if the scratchpad is
  gone, the PR body is reconstructible from the plan's §2–§5 and the
  commit messages); (2) `git push -u origin claude/emb-bot-quality-review-acwj61`
  (retry 2/4/8/16); (3) PR ready-for-review, title "Region colour: a
  robust centre for the palette's per-region point, cfg.robust_region_colour
  (DEFAULT OFF)", body from pr_body.md + the footer; (4)
  `enable_pr_auto_merge` while `blocked`; (5) `subscribe_pr_activity`;
  (6) `send_later` ~60 min; (7) memory note; (8) AskUserQuestion — Kent's
  one decision: flip ON (recommended: the disc is the case it was built
  for; price = a synthetic stub's +3,382 stitches / +29 trims and drone's
  211 mm² orange one spool step at 6; catch = photo-lane snapshot golden
  recapture on ubuntu CI) or keep OFF as a measured instrument until
  item 1's lane decides where real logos go.
- Renders are in `docs/renders/region-colour-2026-09-10/` (committed).
- **Shipped as PR #445 (15:45Z, ready-for-review, auto-merge armed at
  `blocked`, subscribed, check-in ~60 min out).** Full suite on the pushed
  tree: 3 failed / 2,213 passed / 3 skipped / 7 xfailed in 46 min — the
  three platform reds; the photo-lane golden passes. The handoff section
  above is now history except the flip decision, which is Kent's
  (AskUserQuestion put at the end of this turn; he asked to clear after).

## Kent's ruling 2026-09-10 ~17:20Z — flip `robust_region_colour` ON in a follow-up PR

- **Ruled ON**, as a separate PR AFTER #445 merges (auto-merge armed; do
  not push to the lane until then — a push lands in #445 and resets its
  checks). He then cleared the context; this is the handoff.
- **The flip PR, in order:** (1) `git fetch origin main` and fast-forward /
  rebase the lane onto #445's merge; (2) `config.py`:
  `robust_region_colour: bool = True` + docstring "DEFAULT ON since
  2026-09-10 (Kent's ruling on the flip sheet and the Bridge Bar render;
  False is the pre-flip engine byte for byte)"; (3) tests:
  `test_default_off_and_the_radius…` → `_on_`; keep the OFF byte-identity
  test (explicit `robust_region_colour=False`) and the Bridge Bar pair;
  (4) **goldens move**: `testdata/photo_lane_segment_golden.json` on drone,
  summit_badge, repro_gradient_white_icon, photo_subject_stub (the four the
  Lab-mean cut failed on are the four whose stage-2 output the modal mean
  changes) — recapture on ubuntu CI ONLY (`recapture-goldens.yml`, the way
  the sub-pixel PR 4 did it, with the pre-change proof), never on this box;
  check `test_stage2_photo_segment`'s gradient golden and
  `test_flat_lane_byte_identical` too (flat lane should be untouched);
  (5) tests that document the OFF palette on Bridge Bar and friends may
  move (`test_thread_match_better_spool[bridge]`, `test_phantom_blend_photo`
  Bridge Bar pair, `test_thread_revalidate` ×3 — the ones the Lab-mean cut
  broke): restate on `robust_region_colour=False` where they document the
  pre-flip fact, as the colour-bundle flip did with PRE_FLIP; (6)
  `tools/flip_sheet.py`: the `region_colour` arm becomes inert against
  `off` — add an `off_rc` arm (`robust_region_colour: False`, the pre-flip
  engine) beside `off4`; (7) MASTER_SCOPE item-8/region-colour sentence,
  plan §5/§6, scope-history entry, `docs/scope/*` if any line says DEFAULT
  OFF for it (`tools/doc_claims.py` is STRICT on MASTER_SCOPE/DOCTRINE);
  (8) full suite (expect the three platform reds + the moved goldens until
  CI recaptures); PR ready-for-review, auto-merge, subscribe, send_later;
  (9) the next-build question: candidates item 1 (the real-logo lane),
  item 11 (legibility yardstick + un-clamped grade), item 12 (fill travel
  under cover), item 13 (photo detection from EXIF/face), item 14 (the
  edge-finish flags).

## 2026-09-10 ~18:15Z — #445 MERGED (auto-merge, 18:03Z); the flip PR in progress

- Lane rebased onto e0833d7 (#445's merge), the two memory commits pushed,
  the check-in trigger deleted.
- The flip PR, built on the recipe above: default True + docstring;
  `conftest.PRE_FLIP` carries `robust_region_colour: False` beside the
  bundle's four (every file that prices one colour flag alone stays on the
  engine its numbers were taken on — which is why the Lab-mean cut's
  failure list is NOT this flip's: those files were on the pre-flip engine
  already); `test_robust_region_colour` restated (default ON; the Bridge
  Bar pair pins default == ON arm and != OFF); `tools/flip_sheet.py`
  `off_rc` (the pre-flip engine; `region_colour` is inert against `off`
  now); `tools/recapture_photo_lane_key.py` (new, the photo-lane twin of
  the flat tool, with `--dry-run` for reading a footprint on a box that
  must not capture); the temporary `recapture-goldens.yml` (push-triggered
  by the push that brings it, commits the golden back, removed in the
  commit after). Docs carry placeholders for the moved keys, the workflow
  run, the restated tests and the suite line — filled from the suite and
  the run before committing (grep the angle-bracket markers out first).
- **19:11Z — commit `58a3255` pushed** (default True, PRE_FLIP, restated
  pins, `off_rc`, the recapture tool, the temporary workflow). Suite on
  the flipped default BEFORE the restatements: 25 failed / 2,191 passed —
  3 platform reds + 6 golden keys + 16 pre-flip pins (8 on PRE_FLIP, fixed
  by the conftest change alone; `test_thread_revalidate` ×4 and
  `test_rehome_resnapped` hold the flag False in their CFGs; drone's
  duplicate-cone fold holds it too and records the flipped numbers: +21
  stitches for −56 mm needle-up and −2 stops). All restated files re-run
  green. The recapture workflow is run **34518855051** (started 19:10:54Z);
  it commits the golden back to the lane — `git pull` after it, verify the
  photo-lane test locally, then commit 2: docs (MASTER_SCOPE / plan §6 /
  scope-history already carry the run id; the suite line is the one
  placeholder left), the test docstring note (applied), workflow removal,
  memory; then the PR. Full suite on the final tree running locally.
- **19:15Z — the golden landed: run 34518855051 succeeded in 4.5 min, every
  key passed the pre-change machine check, six re-written exactly as the
  local dry runs predicted, commit `27a7739` on the lane; the runner then
  ran both golden files green (13 passed, enthusiast deselected). Lane
  fast-forwarded; the workflow file removed for commit 2.

## 2026-09-10 ~20:05Z — the flip SHIPPED as PR #448 (ready-for-review; auto-merge armed after this push)

- `robust_region_colour` DEFAULT ON: commits `58a3255` (the flip, PRE_FLIP,
  the restated pins, `off_rc`, the recapture tool, the temporary workflow),
  `27a7739` (the runner's golden: six of seven keys, every key
  machine-checked on `e0833d7`, run 34518855051), `a28ef6a` (the docstring
  note, the workflow removed, docs). Suite on the final tree: 9 failed /
  2,207 passed — the three platform reds and the six keys against the OLD
  golden (that run started before the runner's commit landed); with the
  runner's golden the photo-lane file passes here (8 passed).
- Facts the next session should not re-derive: region_blobs moves at
  STAGE 2 (one medoid, 293 → 276, the base spool of a 656 mm² blob the
  tonal split sews as bands of its own) while its plan is byte-identical —
  a plan-level sheet cannot see a stage-2 move, the golden can; drone's
  duplicate-cone fold on the flipped engine is +21 stitches / −56 mm
  needle-up / −2 stops (the test holds the pre-flip engine and records
  this); `off_rc` == the #445 cache's `off` row byte for byte on Bridge Bar
  at 12; `tools/recapture_photo_lane_key.py --dry-run` reads a change's
  golden footprint on a box that must not capture.
- CI on #448: four jobs; `digitizer` expected green (its three deselects
  plus the runner's golden). Check-in scheduled ~60 min out; delete it
  once the PR merges, then `git fetch origin main` and fast-forward the
  lane before anything else is pushed.
- Next: Kent's next-build pick (AskUserQuestion at the end of this turn):
  item 11 (the legibility yardstick + un-clamped grade) recommended, item 1
  (the real-logo lane), item 12 (fill travel under cover), item 13 (photo
  detection from EXIF/face); items 10 (JS wide columns) and 14 (the
  edge-finish flags) named as the other live candidates.

## Kent's pick 2026-09-10 ~20:00Z — "Item 11 and 1"

- Both, in that order: item 11 (the legibility yardstick on the render +
  the un-clamped grade + THREAD_MATCH_POOR's area floor) first, so item 1
  (the real-logo lane) is judged by a grade that moves. Item 1 after.
- **Do not push to the lane until #448 merges** (auto-merge armed; the
  check-in trigger `trig_01LgZ1jn26VmztuYsiabsuZy` fires 20:56Z). Build
  locally; commits held.
- **20:43Z — #448 MERGED** (auto-merge; `digitizer` green in 46 min on the
  runner's golden). Check-in trigger deleted; lane fast-forwarded onto the
  merge. The push hold is lifted — item 11's commits can go up as they
  are ready.

## Item 11 in progress (2026-09-10 ~20:00Z →) — the legibility yardstick, the un-clamped score, the thread-match floor

- Plan `docs/superpowers/plans/2026-09-10-legibility-yardstick.md` (§0–§3
  written; §4 tables pending the runs; §5 Kent's two decisions: the
  LEGIBILITY thresholds/flip, and the gradient lane's yardstick).
- BUILT so far (uncommitted): `_THREAD_MATCH_MIN_PATCH_MM2` (= the
  uncovered sibling's 5.0 mm², ON; rows carry `footprint_mm2`, findings
  `worst_patch_mm2` / `sub_floor_count`, sub-floor offenders listed and
  flagged, a thread with only sub-floor offenders emits nothing);
  `digitizer_core/legibility.py` (the tool's measurement moved in, plus a
  `sewn` flag per cluster and `ART_MIN_LETTERS` = 3 — a one-letter OCR
  "truth" on the art side (Bridge Bar reads "X" at 77) judged a cluster at
  0.00); `tools/legibility.py` is now a CLI over it; preflight
  `LETTERING_ILLEGIBLE` behind `cfg.legibility_check` DEFAULT OFF, with
  PROVISIONAL `LEGIBILITY_BLOCK` 0.5 / `LEGIBILITY_WARN` 0.75 and
  `legibility_*` metrics (checked False when off / no image / no
  tesseract); flip sheet rows carry `raw_score` and read verdicts off it;
  scorecard prints raw beside score. Tests: `tests/test_legibility_check.py`
  (7; 38 with the wiring + legibility files, green).
- Measured: the read costs 3.7–16.8 s per design (24 tesseract calls per
  cluster) under load; Fremont's HOTEL FREMONT reads 0.74 today (banner
  noise on the ART side — under a 0.75 warn, a false positive to weigh).
- Running: `tools/thread_match_floor.py run` (the 0/2/5/10 sweep over the
  scorecard matrix → §4.1 and §4.3), `tools/legibility.py --corpus` at 6
  and 12 (→ §4.2), the preflight/thread-match test files against the floor
  (→ `test_thread_match_area_in_message.py` needs restating: gaulke's
  0.58 mm² shard no longer blocks — that is the point).
- Then: scorecard `diff` on this tree (attribute every mover since the
  09-04 baseline: the flips, then the floor), `capture`, docs (MASTER_SCOPE
  in place at 800), full suite, PR, AskUserQuestion for §5.
- **~21:40Z — item 11 measured and calibrated.** Floor sweep: 40 → 26
  blocks at 5 mm², gaulke D 46 → B 76, no design leaves the 0 floor (10 of
  52 on it, raw −140 .. −26). Legibility: the crops (kept in
  `docs/renders/legibility-2026-09-10/`) showed the similarity noisy in the
  middle (DRONE 0.22 readable under SPOTIFY 0.50 blobs; HOTEL FREMONT 0.74
  clean) → provisional warn-only under 0.5 (`LEGIBILITY_BLOCK` 0.0), the
  options for Kent in plan §5 (A warn-only / B 0.2+0.7 / C 0.5+0.75 / D
  off) plus the gradient-lane yardstick. DOCTRINE entry written. Tests
  restated: area-in-message (rewritten), enclosed-background and
  better-spool (unfloored helpers), raw depth −62, bimodal pin (footprint
  key — its edit still pending: the literal holds an expression). Docs:
  MASTER_SCOPE in place (800) and scope-history carry two angle-bracket
  placeholders (the recapture, the suite line) until the scorecard
  recapture and the full suite — grep them out before committing those two. Scorecard `diff` running for the attribution.
- **~22:00Z — commit `9f3d09c` pushed (item 11's code, tests, tools, plan,
  renders, DOCTRINE, COOKBOOK).** Scorecard diff vs the 09-04 baseline: 46
  of 52 pairs moved; attributed (this PR's floor on four fixtures exactly,
  the flips since 09-04 for the rest) and two grade drops BISECTED on
  main's first-parent history with a one-pair scorer in a scratch
  worktree: grass_macro B 76 → D 40 at #432 (subpixel flip; D 52 since
  #437) and Becker @ hat_front B 88 → 76 at #433 (junction clustering;
  hat_front only). Both left as a follow-up (plan §4.4; the task-card tool
  timed out twice, so the record is the plan + the recapture commit).
  Recapture running (`capture`, stamps `9f3d09c`); full suite running;
  commit 2 = baseline + MASTER_SCOPE + scope-history + plan §4.4 + memory,
  then the PR (body drafted in the scratchpad), auto-merge, subscribe,
  send_later, AskUserQuestion on plan §5 + item 1 next.
