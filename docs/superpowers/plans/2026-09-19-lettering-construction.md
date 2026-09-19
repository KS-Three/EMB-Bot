# Lettering construction — give a traced letter the font engine's rules (2026-09-19)

**Status:** decision document, Kent's ruling 2026-09-19 (trace + the font
engine's construction, in that order). Step 0 built and flipped ON the same
day (`cfg.satin_house_from_line`); step 1 BUILT, measured and FLIPPED ON
the same day too (`cfg.satin_house_anchor`, Kent's call over the THERMAL
render, keeping the fonts' bar rule); step 2 BUILT, measured and FLIPPED ON
the same day (`cfg.satin_stroke_order = "euler"`, Kent's call); step 3
chosen next. Review it rests on:
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
   at 80 mm across the nine logos the walk adds 1,064 mm of travel (1,530 → 2,594 mm) and **1.4 mm of new exposure** — exposed travel 244.7 → 246.1 mm, from gaulke (0.0 → 1.4 mm, worst leg 0.5 mm) and Bridge Bar (22.8 → 25.5) against Golden Tee's 2.3 → 0.4 and Fremont's 57.2 → 56.7; Becker, tires, ENTHUSIAST, drone and the screenshot within 0.3 mm; trims 587 → 471. The 245 mm that IS exposed is the nearest order's own (Becker's 22.9 mm leg, Fremont's 21.8, the screenshot's 26% of its travel) — a pre-existing finding this instrument is the first to read, not this step's. **Becker at 80 mm** (not its 100 mm corpus width, where 34.8 mm² both ways) reads `uncovered_total_mm2` 18.5 → 26.0 under the walk; diffed cell by cell, the six half-millimetre samples that flip sit at 0.26–0.32 units under the nearest order and 0.20–0.21 under the walk, on the seam between two of the MARINE band's columns, and what lifted them over the 0.25 floor was a 23-point travel leg the nearest order happened to route across the seam. The seam is bare of column thread under both orders — the decomposition's, step 3's — and the walk's legs run elsewhere; the columns' own points are identical either way (checked: `satin_shape` returns the same point set from either entry). Tests: `tests/test_stroke_order_euler.py` (10, on the
   committed fixture raster). Render: `docs/renders/lettering-euler-2026-09-19/`.
3. **Corners: rail-side pull compensation after decomposition
   (`satin_rail_comp`, built OFF; which skeleton is Kent's) and the cap-arm
   classifier for `_prune_spurs`** — the letterform study's mechanisms #1
   and #2. Measure by the bare corners the edge cap currently patches: the
   hook runs should go as the corners fill.
4. **Wide lettering: split, never fill.** Classify a text-cluster member per
   stroke (`satin_per_stroke`'s unit), lift the cap for lettering and let
   `split_satin` carry the width — but only once step 3 and the wide-stroke
   decomposition stop the self-crossings the cap arms showed (143 / 250).
   The pro sews 7-23% of Becker's columns over 5 mm; the browser engine
   splits, never fills (Kent, 2026-09-11).
5. **No edge cap on lettering** once step 3 covers the corners: a typed
   glyph gets none; today removing it would expose the bare corners it
   patches.

## Not this plan

Font identification (measured dead, review §2). Bring-your-own-font-file
(pays off only after steps 1-4). Anything that moves a fabric constant.
