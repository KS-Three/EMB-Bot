---
name: text-cluster-nest-guard-2026-10-27
description: `text_cluster_nest_guard` (OFF): the text tagger's `_drop_nested` ignores a frame candidate taller than 6x the pool's median glyph height; Bridge hat's wheel nested 8 of 15 letters away. Necessary, not sufficient (folds 2 -> 5 of his 35); rotation-aware aspect door is the next lane
metadata:
  type: project
---

Built 2026-10-27 on the director's call after the Bridge measure (`bridge-text-nested-2026-10-27`, `bridge-census-2026-10-27`).
`textcluster._drop_nested(cands, nest_guard)`, `NEST_FOOTPRINT_MAX_X = 6.0`, `cfg.text_cluster_nest_guard` (OFF), wired at
`pipeline.py` beside `wide_letters` / `part_touching`; the rescued round and the house-angle group (`_lettering_groups`) keep
today's drop. Tests `tests/test_text_cluster_nest_guard.py`; the field is in `tests/engine_2026_10_27.json`.

**Basis for 6.0:** the hat's wheel (62.6 x 55.1 mm) is 13.7x the pool's median candidate height (4.01 mm), the next tallest
candidate 1.9x, the left chest's tallest 2.7x (its wheel, 65.5 mm, is refused by the 60 mm door cap and nests nothing).

**Not sufficient:** the counterfactual read 0 -> 8 of 15 hat text pieces in the lane (the built flag leaves the house-angle
group's one piece out, so expect 7) and folds 2 -> 5 against his 35. The ring's left side stays out: letters rotated on the
ring read aspect 1.47-1.52 against the door's 1.4 and heights of 0.45-0.8 of their line. A rotation-aware aspect test is
the next lane, not built.

**Proof (2026-10-27, #1151).** Reach census, 14 pairs scored, OFF = ON on every pair: reach kappa 0.815 [0.626, 0.929]
(raw 0.922), detect kappa 0.623 [0.420, 0.885] (raw 0.818), 235 of 298 letters reach the lane, 147 false positives. Only
ProSeal hat (40.0 mm frame, 12.7x the pool median) and beanie (34.9 mm, 11.9x) have a frame besides Bridge hat; the other 12
re-tag nothing in the tagger replay (`nest_replay`: tags are the guard's only output), so they sew as OFF. Bridge hat with
the real flag: 0 -> 7 of 15 text pieces in the lane, folds 2 -> 5 (his 35), zones 0 -> 3 (his 37), stitches 9,419 -> 9,311;
Bridge LC byte-identical. **ProSeal's catch:** +12 (hat) / +11 (beanie) pieces tagged `text_candidate`, all ROUND (circularity
0.87-0.96, 1.7-3.5 mm, none labelled): the bubbles. DST byte-identical OFF vs ON, `is_lettering` unchanged, so nothing sews
differently; the cost is a false 'looks like text' tag (Studio badge, Convert to text). A roundness guard in the tagger door
is the unbuilt narrowing.

**How to apply:** this is a flag for Kent to flip from the reach census (`column_reach_census`, 13 pairs, OFF vs ON): read
reach kappa, false positives per pair, and any large field or ring that stops swallowing fragments.
Related: [[bridge-text-nested-2026-10-27]], [[column-reach-census-2026-10-25]].
