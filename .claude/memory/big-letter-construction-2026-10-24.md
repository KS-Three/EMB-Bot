---
name: big-letter-construction-2026-10-24
description: The pro's "163 columns to our 77" on MARINE is 35 junction patches plus a sheared top SLAB in the font, not more cuts per stroke; he cuts through reflex notches along the crosses and folds convex corners; what the cuts buy is cross direction only, which `lettering_columns_text_lean` (OFF) already gives with no new cuts. Don't copy the count.
metadata:
  type: project
---

2026-10-24, task L6, lane `marine-construction-study-0bbf3d`. Doc
`docs/big-letter-construction-2026-10-24.md`, renders
`docs/renders/big-letter-construction-2026-10-24/`, reader
`digitizer/tools/letter_pieces.py` (pinned by `tests/test_letter_pieces.py`).
Investigation only, no engine change.

**Premise re-measured:** with one reader on both files, the four MARINE files
give him 108 pieces + 35 patches (143) to our 76 + 2 (78). Corner ends are
level (45 / 46); his extra cuts are STRAIGHT joins (44 to 10), 41 of 44 at a
junction, none between 35-65% of the cap -- **no length cap**, no width cap
(his merged cells carry 0-deg crosses to 1.75 x the stroke).

**The slab is the art:** every MARINE letter's top ~25% is a parallelogram
sheared left (left edge 103-105 deg on our polygons); he sews it as its own
piece with crosses 99-118 deg, parallel to that edge. The 146-px art hides it
until you look at the pro_pair art row.

**Rule:** cut through each reflex notch along the crosses (slab base, a
diagonal leaving/joining a stem, a bar butting a stem); run one column
through convex corners and curves; crosses parallel to the piece's end cuts.
PROSEAL (pro 11 pieces, ours 18, both flags 13) and GOLKE (28 over 16
letters, pro only) confirm the corner half -- the same rule as
[[column-corner-folds-2026-10-23]].

**What the cuts buy:** leaning-stroke crosses within 15 deg of the text line
0.47-0.58 his vs 0.17-0.25 ours; `text_lean` ON gives 0.51-0.53 with 16-18
pieces. NOT shorter stitches (gap is our wider pull, gate 1), NOT fewer
same-hole drops, NOT denser ends.

**Traps:** a split-satin fuser that merges only two legs drops 7.7 mm crosses
(A->M1->M2->B at 101.9 mm) and loses whole letters -- fuse while collinear.
Rasterising travel "bits" with the crosses joins neighbouring letters into
one component -- letters from piece crosses only.

Related: [[lettering-10mm-up-band-2026-10-23]], [[inside-stagger-2026-10-23]].
