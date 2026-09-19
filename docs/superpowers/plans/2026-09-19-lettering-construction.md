# Lettering construction — give a traced letter the font engine's rules (2026-09-19)

**Status:** decision document, Kent's ruling 2026-09-19 (trace + the font
engine's construction, in that order). Step 0 built and flipped ON the same
day (`cfg.satin_house_from_line`); step 1 BUILT the same day, OFF
(`cfg.satin_house_anchor`), measured below — the flip is Kent's. Review it
rests on: `docs/lettering-route-review-2026-09-19.md`.

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
   stems — BUILT 2026-09-19, `cfg.satin_house_anchor`, OFF (Kent's flip).**
   Found building step 0: when the doubled-angle vote passes on a
   diagonal-heavy word it returns a house pulled off the line by the
   diagonals — AMAZE 27°, NAVY 147°, ZANY 151°, VANE 160°, HOTEL 17° on the
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
   12–79° off the line; the anchor puts 15 of 19 anchored groups within 2°
   of it, the other four being the Fremont rope's twists (not letters,
   16°/19°) and two 1–2 mm screenshot groups (8°/10° of skeleton noise).
   Font words within 0.6° upright, within 2.5° turned 15° and 30°. Corpus
   cost: drone +167 stitches / +5 trims with its satin self-crossings
   496 → 430; enthusiast +16 / +2; everything else within ±24 stitches.
   **The look it exposes, for the flip:** THERMAL (drone, 7.6 mm) sewed at
   one accidental 108° lean everywhere (both families inside the fade),
   cross concentration 0.339; anchored at 0° its stems sew square and its
   bars take their own perpendicular under `_clamp_to_span` — the fonts'
   convention the 09-03 rule adopted — and the concentration reads 0.038.
   The pro sews one angle. Render
   `docs/renders/lettering-anchor-2026-09-19/drone_lettering_anchor_off_above_on_below.jpg`.
   Rejected on measurement: a kernel mode for the slant (jumps to the
   diagonals' peak: NAVY −19°, VANE +17°) and a straightness gate on the
   votes (VANE flips −11/−15/+16 across thresholds). Limits: a family with
   hardly a stem reads its diagonals' middle (ZANY −12°); a brush script
   with curves for stems reads near zero (montecarlo, pacificlo) where the
   eye sees a lean.
2. **One path per letter — Euler-walk stroke order.** Order the strokes of a
   text-cluster member so the existing unsewn-web travel always has a path:
   depth-first over the spine graph, travelling down unsewn spines and
   sewing back, like `satinfont.routeGlyph`. Target on the fixture: 35 → a
   handful of within-letter trims. No physical constant (nothing crosses
   bare fabric; every leg lies under a later column of the same shape).
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
