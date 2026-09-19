# Lettering construction — give a traced letter the font engine's rules (2026-09-19)

**Status:** decision document, Kent's ruling 2026-09-19 (trace + the font
engine's construction, in that order). Step 0 built and flipped ON the same
day (`cfg.satin_house_from_line`); step 1 chosen next, the same day. Review it rests on:
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
   3 of the 22 lettering groups across the nine logos: the ENTHUSIAST
   wordmark (11 letters: doubled-angle nR² 0.9, four-fold 0.243) and two
   tiny groups on the phone screenshot. ENTHUSIAST's word: house None →
   179.9°, its satin runs' cross concentration **0.059 → 0.287**, stitches
   2,492 → 2,499, trims 24 → 25. Flipped ON 2026-09-19.
1. **Anchor the house to the line of text; read only the SLANT from the
   stems.** Found building step 0: when the doubled-angle vote passes on a
   diagonal-heavy word it returns a house pulled off the line by the
   diagonals — AMAZE 27°, NAVY 147°, ZANY 151°, VANE 160° on the font word;
   on real logos enthusiast's subline **130°**, fremont **97.9° / 162°**,
   bridge 45° / 16° — which is not the stems' perpendicular the rule names.
   And the vote's verdict sits on a knife edge: "MARINE" at 80 mm reads
   nR² 5.0 from the shipped binary's quantised rails and 11.2 from the
   source rails, 4.5 at 60 mm. The construction: for a group with a line,
   house = line + slant, slant read from the near-normal family only
   (strokes within the 30° cap of the line's normal), zero when that family
   is silent; the votes stay as the detector for a leaned script only.
   Changes every group a vote currently passes: measure the nine logos'
   groups before/after, render Becker, enthusiast, fremont.
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
