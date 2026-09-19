# Lettering construction — give a traced letter the font engine's rules (2026-09-19)

**Status:** decision document, Kent's ruling 2026-09-19 (trace + the font
engine's construction, in that order). Step 0 built and flipped ON the same
day (`cfg.satin_house_from_line`); step 1 BUILT, measured and FLIPPED ON
the same day too (`cfg.satin_house_anchor`, Kent's call over the THERMAL
render, keeping the fonts' bar rule); step 2 BUILT, measured and FLIPPED ON
the same day (`cfg.satin_stroke_order = "euler"`, Kent's call); step 3a
BUILT and FLIPPED ON the same day (`cfg.satin_corner_twigs`, Kent's call);
3b re-measured and its skeleton RULED (the artwork, Kent), its flip
waiting on a sew-out; step 4 BUILT OFF and measured the same day
(`cfg.satin_lettering_split`): the wide stems sew as columns and the R's
junction ball fans — KEPT OFF (Kent, 2026-09-19) until the bold-letter
junction construction exists; step 5 BUILT, measured and FLIPPED ON the
same day (`cfg.edge_cap_skip_lettering`, Kent's call: the fixture's trims
23 → 7 against the typed word's 3). Every step is built; next is a
sew-out sheet for the two flips cloth still owes (3b, and 5's check).
Review it rests on:
`docs/lettering-route-review-2026-09-19.md`.

**Yardstick.** The review's construction: a library font's own word — its
glyphs' satin columns as ribbon polygons, laid out with the font's advances —
sewn once through the font engine (`tools/run-lettering.mjs`) and once
rasterised at 12 px/mm and traced at Studio defaults. Same letterforms, so
every gap is construction. `manga_impact` "MARINE" at 80 mm: **font engine
1,782 stitches / 3 trims / 44 columns; traced 2,461 / 41 trims**, cross
angles at 0.23 concentration, 349 self-crossing pairs, four edge-cap hook
runs. Every step below is measured against that pair, on that fixture, plus
the nine `REAL_ART` logos' lettering groups. A step is done when it moves the
traced side toward the typed side without moving anything a vote or a
customer already had right.

## Where the 41 trims and the look come from (measured 2026-09-19)

| what | count | mechanism |
|---|---|---|
| trims inside one letter, stroke to stroke | 35 | stage 6 walks the unsewn skeleton web to the next stroke when a path exists (`_graph_travel`), but the stroke ORDER (longest-first, nearest-next) leaves no unsewn path once a few strokes are sewn; the font engine plans an Euler walk so every travel lies under a later column |
| edge-cap bean runs around the letters | 16 of the 41 (18 runs) | `__edge_cap__` is patching the corners the satin decomposition leaves bare — the hooks in the render are the cap doing its job on a defect upstream |
| cross angles scattered | concentration 0.23 | both house-angle votes refused the word; per-stroke tangents took over |
| at 127 mm, 14 of 15 letters tatami | 5 `dt_p90_cap`, 3 `dt_irregular` | the classifier judges the whole letter; lifting the cap alone (`satin_max_width_mm=10`, `wide_columns`) gives 7 satin / 8 fill with 143 self-crossings, and `satin_polygon_axis` on top 250 — the wide-stroke decomposition, not the cap, is the blocker |

## The steps, in the order they buy the most

0. **House angle, third reading — BUILT and FLIPPED ON the same day, Kent's call (`satin_house_from_line`).**
   A group both votes refuse takes the cross along its line of text (the
   stems' perpendicular for upright lettering — the adopted rule). Fires on
   3 of the 24 lettering groups across the nine logos: the ENTHUSIAST
   wordmark (11 letters: doubled-angle nR² 0.9, four-fold 0.243) and two
   tiny groups on the phone screenshot. ENTHUSIAST's word: house None →
   179.9°, its satin runs' cross concentration **0.059 → 0.287**, stitches
   2,492 → 2,499, trims 24 → 25. Flipped ON 2026-09-19.
1. **Anchor the house to the line of text; read only the SLANT from the
   stems — BUILT 2026-09-19, `cfg.satin_house_anchor`, and FLIPPED ON the
   same day (Kent, over the THERMAL render; the fonts' bar rule stands).**
   Found building step 0: when the doubled-angle vote passes on a
   diagonal-heavy word it returns a house pulled off the line by the
   diagonals — AMAZE 27°, NAVY 147°, ZANY 151°, VANE 160°, HOTEL 27° on the
   font word (HOTEL turned 20°: 45° off); on real logos enthusiast's subline
   **130°**, fremont **97.9° / 162°**, drone 115° / 108° — not the stems'
   perpendicular the rule names. And the vote's verdict sits on a knife
   edge: "MARINE" at 80 mm reads nR² 5.0 from the shipped binary's
   quantised rails and 11.2 from the source rails, 4.5 at 60 mm.
   The construction as built: for a group with a line, house = line + slant,
   slant = the length-weighted MEDIAN offset of the strokes within the 30°
   lean cap of the line's normal, on chains resampled at the four-fold
   reading's 4 px chord; a family under 10% of the skeleton is silent and
   the group goes to the votes as before, as does a group with no line.
   Not "votes as a script detector": every shipped font's lean fits the
   window (montecarlo's rails 26.6°), so a leaned script reads its own
   slant (mam_script "Marine" +15.4°, visibly right) and no detector was
   needed; a script leaned past 30° would go to the votes by silence.
   **Measured** (scope-history 2026-09-19, step 1): on the 24 real-logo
   groups the vote accepts 12 with a line and stems and puts 9 of them
   12–79° off the line. Output: drone's satin self-crossings **496 → 430**
   and Fremont's 87 → 66 at drone +167 stitches / +5 trims, enthusiast
   +16 / +2, everything else within ±24 stitches. Instrument check: the
   slant reads under 2° on 15 of the 19 anchored groups (all upright), the
   other four being the Fremont rope's twists (not letters, 16°/19°) and
   two 1–2 mm screenshot groups (8°/10° of skeleton noise); font words
   under 0.6° upright, under 2.5° turned 15° and 30°.
   **The look it exposes, for the flip:** THERMAL (drone, 7.6 mm) sewed at
   one accidental 108° lean everywhere (both families inside the fade);
   anchored at 0° its stems sew square and its bars take their own
   perpendicular under `_clamp_to_span` — the fonts' convention the 09-03
   rule adopted. The pro sews one angle. Measured with the committed
   instrument (`tools/satin_lean.py drone [--anchor]`, splits and ties
   stripped): THERMAL's cross concentration 0.319 → 0.248, AND DRONE's
   0.227 → 0.297, PRECISION's 0.170 → 0.178; over the word's 2,000 crosses
   the lean off each cross's own perpendicular p50 17.0° → 11.8°, crosses
   within 10° of the house 25% → 34%, bars at their own perpendicular
   (80–90°) 7% → 14%. (A scratch probe read 0.339 → 0.038 on THERMAL; it
   counted tie stitches and split penetrations as crosses and is
   withdrawn — which is why the instrument is committed.) Render
   `docs/renders/lettering-anchor-2026-09-19/drone_lettering_anchor_off_above_on_below.jpg`.
   Rejected on measurement: a kernel mode for the slant (jumps to the
   diagonals' peak: NAVY −19°, VANE +17°) and a straightness gate on the
   votes (VANE flips −11/−15/+16 across thresholds). Limits: a family with
   hardly a stem reads its diagonals' middle (ZANY −12°); a brush script
   with curves for stems reads near zero (montecarlo, pacificlo) where the
   eye sees a lean.
2. **One path per letter — Euler-walk stroke order. BUILT 2026-09-19,
   `cfg.satin_stroke_order = "euler"`, and FLIPPED ON the same day (Kent;
   "nearest" is the pre-flip order, byte for byte).** The font engine's `routeGlyph`
   construction on stage 6's own travel graph (`_euler_stroke_order`):
   Chinese-postman duplication where a dead end forces it, a Hierholzer
   trail, each stroke sewn at its LAST visit so every travel leg lies under
   a column sewn later; the existing `_graph_travel` then finds the unsewn
   path wherever no stroke crosses an interior junction (the review's
   finding: an H's or K's stem sews whole and can leave the needle at a
   dead end, which then trims as before — H, K, X, +, t and 179 of 600
   random webs; sewing per span would close it and is a decomposition
   question, Kent's). Three things the fixture taught, each measured before it
   was built: a stroke must be walked THROUGH (column in at the walk's
   arrival end, out the other; the underlay chained backwards from that
   entry — nearest-first orientation brought the pair back out where it
   went in, 8 of 18 within-letter trims); the 0.2 mm self-loop stubs of the
   graph builder must be skipped (they were setting orders and entries);
   and the cursor may snap to the nearest node it can still leave from
   (`snap_to_open`: a 2 mm column's caps end it nearer the junction it
   came from). It applies to EVERY satin shape, not only lettering — the
   travel web is the same object. **Fixture (MARINE 80 mm): 45 → 27
   trims, 2,564 → 2,482 stitches, 3 → 17 travel legs (117 mm),
   self-crossings and uncovered area unchanged**; the trims on lettering
   runs 26 → 8, of which 4 are cap-extension hops (underlay end to a
   3.2–3.4 mm cap-extended column start, over `TRIM_AT_MM` 3.0 — the
   nearest order pays them too) and 3 are between letters; the 18 edge-cap
   `run → run` trims are steps 3 and 5's. Nine logos: trims **592 → 486** across the nine (Becker 46 → 38, tires 11 → 8, ENTHUSIAST 27 → 19, Fremont 75 → 55, Bridge Bar 112 → 85, Golden Tee 66 → 45, gaulke 39 → 35, drone 144 → 132, the screenshot 72 → 69) at a net −19 stitches (−58 to +65 per logo), travel 1,478 → 2,934 mm, satin self-crossings, uncovered area and preflight warnings unchanged on every one.
   **Gate 3's instrument, `tools/travel_cover.py`**: every travel leg read
   against the thread sewn AFTER it (preflight's own ribbon rule);
   at 80 mm across the nine logos the walk adds 1,064 mm of travel (1,530 → 2,594 mm) and **1.4 mm of new exposure** — exposed travel 244.7 → 246.1 mm, from gaulke (0.0 → 1.4 mm, worst leg 0.5 mm) and Bridge Bar (22.8 → 25.5) against Golden Tee's 2.3 → 0.4 and Fremont's 57.2 → 56.7; Becker, tires, ENTHUSIAST, drone and the screenshot within 0.3 mm; trims 587 → 471. The 245 mm that IS exposed is the nearest order's own (Becker's 22.9 mm leg, Fremont's 21.8, the screenshot's 26% of its travel) — not this step's, and (corrected 2026-09-19, `tools/travel_legs.py`) not the first reading either: 97.7% of it is the FILL tier's column bridges lying on their own finished fill — defect 21's residual, which `tools/fill_bridges.py` read on 2026-09-11 — and none of it is on bare fabric (scope-history, "the exposed travel legs"). **Becker at 80 mm** (not its 100 mm corpus width, where 34.8 mm² both ways) reads `uncovered_total_mm2` 18.5 → 26.0 under the walk; diffed cell by cell, the six half-millimetre samples that flip sit at 0.26–0.32 units under the nearest order and 0.20–0.21 under the walk, on the seam between two of the MARINE band's columns, and what lifted them over the 0.25 floor was a 23-point travel leg the nearest order happened to route across the seam. The seam is bare of column thread under both orders — the decomposition's, step 3's — and the walk's legs run elsewhere; the columns' own points are identical either way (checked: `satin_shape` returns the same point set from either entry). Tests: `tests/test_stroke_order_euler.py` (10, on the
   committed fixture raster). Render: `docs/renders/lettering-euler-2026-09-19/`.
3. **Corners — the letterform study's mechanisms #1 and #2.**
   **3a, mechanism #2, BUILT 2026-09-19: `cfg.satin_corner_twigs`, and
   FLIPPED ON the same day (Kent, over the nine-logo numbers and the
   renders; False is the pre-flip pruner).** `_prune_spurs` erased a corner's twig and with
   it the junction's degree, so a letter's diagonal and stem welded into
   one column folding through the corner. The study's "cap-arm classifier
   on tip width" does not exist on this raster — a census of 739 spurs on
   five logos shows every spur over 0.5 mm ends at a 1 px distance
   transform, corner twig and cap arm alike — so the rule is by STRUCTURE:
   a node with two short free arms and a longer one is a cap (both arms
   go, whatever their exact length — the H defect's 0.027 mm survivor
   too); a node with one short free arm between two longer arms is a
   corner (the twig stays and holds the junction open). Fixture: satin
   self-crossing pairs **277 → 103**, stitches 2,480 → 2,192, trims 28 →
   23, uncovered 0.0 both ways; nine logos at corpus widths:
   self-crossings **1,813 → 1,004** (Fremont 66 → 13, gaulke 547 → 186,
   drone 430 → 264, the screenshot 271 → 141, Golden Tee 484 → 381), trims
   486 → 488, uncovered unchanged but Becker 34.8 → 35.5 mm², stitches
   +588 of which **Becker's band at 100 mm is +725** — three more strokes
   kept in the band, each with its own zigzag underlay (underlay 722 →
   1,361, satin flat), the one cost to name. `tools/letterforms.py` at
   80 mm: crossing pairs drone 388 → 275, Becker 382 → 156 (within a
   column 23 → 0), ENTHUSIAST 138 → 93 with its bare junction area 2.85 →
   0.0 mm². A synthetic N stops folding 90° through its corners; a
   45 × 4.5 mm bar's spine is straight either way.
   `tests/test_corner_twigs.py` (6). Renders:
   `docs/renders/lettering-corners-2026-09-19/`.
   **3b, mechanism #1: `satin_rail_comp`** (built OFF 2026-09-09) —
   re-measured on today's engine with steps 0–2 ON (`tools/rail_comp.py
   --compare`, 2026-09-19): thread-vs-target IoU Fremont 0.681 → **0.836**
   (score 76 → 88), ENTHUSIAST 0.875 → 0.900 (trims 21 → 17), drone 0.803
   → 0.826, Becker 0.896 → 0.898 (trims 38 → 30, uncovered 26.0 → 21.5),
   gaulke 0.828 → 0.837 (score 64 → 76), sunset 0.734 → 0.807; meadow
   0.811 → 0.779 with coverage_max 7.97 → 9.72 and +340 stitches — the one
   fixture it costs. Thread sewn outside the artwork 147–357 mm² → ≤ 8 on
   every lettering fixture. Of its two decisions (plan
   `2026-09-09-rail-side-pull-comp.md` §7), **the skeleton is RULED — the
   artwork, as shipped in the flag (Kent, 2026-09-19)**; the flip itself
   still waits on a sew-out, since where the pull lands is what the fabric
   answers to.
4. **Wide lettering: split, never fill — BUILT 2026-09-19,
   `cfg.satin_lettering_split`, DEFAULT OFF, and KEPT OFF the same day
   (Kent's call: the junction construction first; step 5 next).** Kent's
   2026-09-11 rule for the browser lettering engine (split ON, fill off),
   applied on the traced path. A text-cluster member is classified and
   sewn with NO width ceiling — `_satin_ceiling_for` answers (∞, the
   per-stroke rung on, the wide-column fold guard on) for a
   `text_candidate` and the design's (`satin_ceiling_mm`,
   `satin_per_stroke`, `wide_columns`) for every other shape, read by the
   borders-last predicate, the classifier call and `satin_shape` alike —
   so `classify_ribbon`'s width gates never send a letter to tatami and
   `split_satin` carries the width over `SPLIT_SATIN_ABOVE_MM` as it always
   did; the ribbon gates that are about SHAPE (aspect, irregularity,
   elongation) still apply, so a blob still fills. Nothing physical moves.
   **Fixture, MARINE traced at 127 mm**
   (`docs/renders/lettering-split-2026-09-19/`): the six text-cluster
   members (the M's two halves, the R, the I, the N's body, the E's stem —
   the A and the letters' inner fragments are not text candidates and
   fill either way) go fill 6 → satin 6, stitches **9,642 → 7,753**, trims
   31 → 47 (edge-cap runs 17 → 27), uncovered 0.0 both ways — and satin
   self-crossing pairs **0 → 311, every one of them in the R** (six
   strokes: bowl, stem and leg meeting in one junction ball), with a
   `DENSITY_EXTREME` finding (coverage_max 5.49 → 6.24). The render says
   the same: the M, I and N stems sew as clean wide columns; the R's ball
   fans. That is DOCTRINE 2026-09-09's limit — "a junction blob is not a
   column"; at 17 mm a bold letter has no arms to stand a junction
   against — reached by the flag, not made by it: it lifts the ceiling
   and builds no junction. **At 80 mm** (the review's fixture, all seven
   members satin either way): stitches 2,192 → **2,520**, the +328 being
   zigzag underlay 405 → 698 — the emitter withholds it under a column
   wider than the ceiling it was admitted at (its `oversize` check), and
   with no ceiling every wide stroke gets its underlay; trims 23 → 26,
   crossings 103 both ways, coverage_max 4.69 → 5.08. **Becker at
   100 mm**: stitches 12,037 → 9,056, trims 39 → 71, self-crossings 714 →
   1,260, uncovered 35.5 mm² both ways, coverage_max 4.91 → 6.68; composed
   with `satin_patch_junctions="satin"` the uncovered artwork reads
   **0.0** at 9,079 stitches / 75 trims (`TRIM_HEAVY` the one finding
   left); with `satin_polygon_axis="artwork"` instead, worse on every
   count (coverage_max 9.45, uncovered 48.2, `DENSITY_STACKED`). Nine
   logos at corpus widths: only Becker moves; the other eight are
   byte-identical in stitches, trims, crossings, uncovered area and
   warnings. So the flip is a choice between tatami letters (today) and
   split-satin letters whose junction balls fan, until the bold-letter
   junction construction exists (item 5 PR 3's finding: the pro stacks
   MORE layers at every junction). `tests/test_lettering_split.py` (7).
5. **No edge cap on lettering — BUILT 2026-09-19,
   `cfg.edge_cap_skip_lettering`, and FLIPPED ON the same day (Kent, over
   the fixture's trims, the render and the nine-logo sheet; False is the
   pre-flip cap byte for byte).** The
   design-silhouette cap (`cfg.edge_cap`, "bean") sews only the stretches
   of the outline nothing linear already covers, and on a satin-sewn
   letter that is exactly the bare corners and junction seams the satin
   decomposition leaves — so it was patching a defect upstream: on the
   80 mm fixture, **17 of the cap's 18 runs and 418 of its 457 stitches
   stood on the letters' outlines** (the review's "16 of the 41 trims").
   A typed glyph gets no cap. The construction: a text-cluster member
   that sewed SATIN hands its sewn polygon to the cap's `omit`
   (`_satin_lettering_cover`, read off the runs the design laid, never a
   verdict), so no cap sample stands on it — on bare fabric or as the edge
   of a hole in a fill; a member that sewed FILL keeps its cap, because a
   tatami letter's rows end in open air at its edge and that is the
   defect the cap exists for; everything else is capped as before. The
   bare corners a letter still has are now its own to show, and that is
   the measurement. **Fixture (MARINE 80 mm)**: stitches 2,192 → **1,774**,
   trims **23 → 7** (the typed word: 3), cap runs 18 → 1, cap stitches on
   satin letters 418 → 0, uncovered artwork 0.0 both ways (the worst bare
   patch 2.2 → 2.5 mm², under the finding's floor), `TRIM_HEAVY` gone;
   every run that is not the cap byte-identical. Becker at 80 mm: 6,588 →
   6,444, trims 43 → 36, uncovered 18.5 both ways. The 127 mm fixture and
   Becker at 100 mm, whose letters fill (step 4 OFF), byte-identical — the
   negative half of the rule. Nine logos at corpus widths: five move — ENTHUSIAST 2,478 → 2,442 stitches at trims 18 → 16, Golden
   Tee 6,969 → 6,945 / 44 → 43, gaulke 4,536 → 4,454 / 41 → 38, drone
   18,733 → 18,715 / 127 → 126, the screenshot 8,244 → 8,085 / 73 → 68;
   Becker (its letters fill at 100 mm), tires, Fremont and Bridge Bar
   byte-identical; trims 488 → 476 at −319 stitches, with uncovered area,
   self-crossings and warnings unchanged on every one.
   Render `docs/renders/lettering-edge-cap-2026-09-19/`. Found on the
   way, from the step 3a flip's full suite: the wide-column fold guard's
   load-bearing case on Becker at 80 mm (coverage_max 7.07 without it,
   2026-09-09) is gone under the corner rule — 4.67 without the guard,
   because the corners it capped a column folding through now sew as two
   columns meeting; the guard's code is unchanged and its case is pinned
   on the pruner it was read on. `tests/test_edge_cap_lettering.py` (10).

**The yardstick now.** Traced MARINE at 80 mm, steps 0–3a ON and 5 ON:
1,774 stitches / 7 trims against the font engine's 1,782 / 3. The stitch
count has crossed. The seven trims: the first needle-down, five hops
inside the word over `TRIM_AT_MM` (3.2–17.9 mm, stroke to stroke and
letter to letter — step 2's remainder), and one into the cap's last run,
on a non-text fragment.

## Not this plan

Font identification (measured dead, review §2). Bring-your-own-font-file
(pays off only after steps 1-4). Anything that moves a fabric constant.
