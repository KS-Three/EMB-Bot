---
name: layering-census-2026-10-26
description: W4-06 premise FALSE. The pro sews every piece inside an earlier colour's outline ON it (162/162, 28 DSTs), but that rule is already built (silhouette_underfill). No layering or colour order reaches our between-shape cuts, because 80 of 176 cross the ground their pieces sit on, which sews first.
metadata:
  type: project
---

2026-10-26, W4-06, branch `claude/layering-census-w4`. Tool
`digitizer/tools/layer_census.py` (+ `tests/test_layer_census.py`). New optional
split `between_walks.diagnose_plan(plan, regions=...)`: `off_on_ground_mm` /
`off_on_sibling_mm`. Doc `docs/layering-census-2026-10-26.md`. No engine change.

**His rule.** One reader, both DSTs. A piece inside an earlier colour's outline
(holes closed, ≥ 0.9) is sewn ON that colour: 162 of 162 on 20 of his 28
files, 0 knocked out. He also lays 57 pieces on earlier colours with no
outline holding them, and knocks 31 out (lettering, ProSeal, Tires). Kappa of
"inside ⇒ on" over 250 pieces: 0.41. The colour underneath is the largest or
the darkest. What it buys him is a ONE-PIECE ground: 0 trims on 15 of 20
files. Ground walks under later colours happen only on Drone (269 mm) and
Gaulke JB (92).

**Ours.** Main knocks out or half-covers 14 of Drone's 27 contained pieces.
`silhouette_underfill` (OFF) lays all 28 on the ground. Its plan trims: Drone
106→100, Fremont 32→27 (exposure down). MFab alone goes 54→83, with stitches
×2 and exposed 18.8→46.6 mm, which fails gate 3. Between-shape cuts (176 on
five hats) split as follows:

- 80 cross the cut colour's OWN ground (inside ⇒ on puts it under, so it
  sews first and is never "later");
- 78 cross bare fabric;
- 13 lie on their own colour only;
- 5 are held off by a sibling colour, the only ones a colour order could
  move.

A back-to-front prototype gave 106→105 / 32→33 / 20 / 54 / 34 trims and 0
routes. Its order was by containment depth, with one block per depth (the
revisits) and holes closed under later shapes. It was not kept; its diff is in
the side-session notes.

**Why:** a buried walk needs LATER thread over the whole route. The pro
crosses his finished ground ON work (Drone 480 mm), and gate 3 forbids that
here.
**How to apply:** do not build layering or revisits for trims. Quote the
ground/sibling split before proposing any order change. The residual gap is
lettering on bare fabric, fill sections ([[in-piece-cuts-2026-10-25]]) and
isolated pieces. Related: [[buried-walk-2026-10-26]],
[[silhouette-underfill-2026-10-24]], [[sequence-like-pro-2026-10-25]],
[[underfill-outer-rim-2026-10-25]].
