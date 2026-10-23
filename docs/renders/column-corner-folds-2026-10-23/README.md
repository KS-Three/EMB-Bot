# Corner folds in the Column lane (2026-10-23)

`cfg.lettering_columns_corner_fold` (built OFF): one satin column folded
round an L-shaped corner the way the professional's files sew it, instead
of the outline cut there and two columns butted.

## What is here

- `<job>_<word>_off_fold_pro.jpg` — one sheet per 5-10 mm word, three
  panels: ours OFF | ours fold ON | the pro's hat DST, all as needle paths
  (ours: satin dark, travel red, underlay orange, artwork outline grey; the
  pro: 1 px lines, red needle dots). `tools/column_harness.py --job <job>
  --fold --out DIR`. 40 px/mm.
- `<corner>.png` — six corners cropped at 100 px/mm, before | after | pro:
  Drone E top-left, Drone C bottom-left, Drone P stem into bowl, MFab L
  foot, MFab E top-left, Fremont E arm tip into its serif. The pro's crop is
  the same corner of his letter, mapped by letter box.
- `table.md` — the census (one reader on ours and his) and the lane's own
  per-letter numbers for every arm.
- `pro_folds_<job>.json` — the pro's folds as `tools/pro_corner_folds.py`
  reads them (per fold: legs, sweep, inner-end spread, outer step and arc,
  the width either side).

## How the pro turns a corner (read on his DSTs, 57 folds)

At a lone concave corner with a convex apex across it his column keeps
going: the crosses pivot on the inside corner, their outer ends walk the
outline round the apex at the satin pitch (outer arc median 2.3-2.9 mm,
max 4.2: two sides of the corner square), the inner ends spread 0.6-0.7 mm
along the crosses (his short stitching, a progressive stagger), and the two
legs' sewn widths are within 1.1-1.2x of each other (median; max 1.3, one
1.7 on a serif). Fremont 25 folds (serif E arm tips, L feet, T bar ends),
Drone 13 (E, C, P, O corners), MFab 18 (E, L, D, G), Proseal 1 (the L).
He cuts where two concave corners face each other: a T junction, a slab
serif's root, an E's middle arm — `find_cuts`' "through" pairs.

## The census (the 5-10 mm band reader, both sides)

Columns: stitches of 0.5 mm or more, consecutive ones anti-parallel and
within 0.5-2x, up to two short stitches skipped, six crosses make a column
(a fold stays inside one column). Butt: a column end within 0.8 W of
another column's body away from that column's ends. Gap: the 0.4 mm thread
covers under 90% of a half-width disc at the meeting point. Travel: a
needle-down stitch with neither end on a letter. Trims: needle-up inside a
letter (the lane's jumps for ours). W: the word's median cross.

| word | arm | columns | butts | gaps | sewn width | travel on cloth | trims in letters | stitches |
|---|---|---|---|---|---|---|---|---|
| Fremont HOTEL FREMONT 92.5 | off | 67 | 6 | 0 | 1.40 | 0.0 | 0 | 1937 |
|  | fold | 57 | 7 | 0 | 1.40 | 0.0 | 0 | 1927 |
|  | pro | 63 | 35 | 0 | 1.43 | 0.0 | 3 | 2203 |
| Drone PRECISION 62.6 | off | 29 | 8 | 2 | 1.98 | 0.9 | 3 | 1096 |
|  | fold | 18 | 5 | 1 | 2.04 | 0.9 | 0 | 1150 |
|  | pro | 24 | 18 | 0 | 2.02 | 0.0 | 0 | 1129 |
| Proseal PROSEAL 85.9 | off | 18 | 6 | 0 | 2.92 | 0.0 | 2 | 1345 |
|  | fold | 15 | 5 | 0 | 2.95 | 0.0 | 1 | 1376 |
|  | pro | 19 | 8 | 0 | 2.94 | 0.0 | 0 | 1455 |
| MFab AND WELDING 104.9 | off | 32 | 6 | 0 | 1.70 | 0.0 | 0 | 1521 |
|  | fold | 24 | 5 | 0 | 1.74 | 0.0 | 0 | 1535 |
|  | pro | 35 | 4 | 0 | 1.55 | 0.0 | 2 | 1689 |
| **36 letters** | off | 146 | 26 | 2 | | 0.9 | 5 | 5899 |
|  | fold | 114 | 22 | 1 | | 0.9 | 1 | 5988 |
|  | pro | 141 | 65 | 0 | | 0.0 | 5 | 6476 |

This reader's butt count excludes an end that meets another column's END
(a mitre), which the 2026-10-23 band doc's did not — its 242 / 195 are not
comparable with these. The pro's 35 Fremont butts are his slab serifs,
which he sews as through-columns (arm over stem) and we cut the same way.

Per letter (the lane's own counters, `table.md`): Fremont E 6 -> 4, F 5
-> 4, L 4 -> 3, T 5 -> 3 columns; Drone P 4 -> 1, R 4 -> 3, E 4 -> 2, C 3
-> 1, S 5 -> 3, O 3 -> 1; MFab D 3 -> 1, L 2 -> 1, D 3 -> 1, N 3 -> 2, G 3
-> 1; Proseal E 4 -> 2, L 2 -> 1; the ~4 mm Fremont words 55 -> 55 (every
corner there is a slab-serif T junction, or a serif `_absorb_serifs`
already took). Ours has 36 letters in the census, not the band doc's 38:
MFab's W and E of WELDING did not come through the lane in this capture
(the W is the segmentation tangle the band doc names), so the MFab column
counts are not letter-for-letter with the pro's.
The legs' crosses are OFF's, station for station (the test asserts it on
the L); the word's median cross moves 0.00-0.06 mm because the corner's
crosses are longer, as the pro's are.

## What still cuts, and why

- T junctions (an E's middle arm, a slab serif's root, H / M / N / R):
  through pairs, cut and butted — as the pro does.
- A 7's elbow at 65 degrees interior (turn 115): past `FOLD_TURN_MAX_DEG`
  110, the corner-to-apex cross would be 1.86 W; no 7 in the four jobs, so
  the range is the pro's measured one, not a guess at acute corners.
- A corner where the two legs' widths differ by more than 1.6x
  (`FOLD_WIDTH_RATIO`); none in the band.
- Where the walk must END at the folded column's middle (an E whose next
  letter sits beside its stem) the Euler trail doubles a span as a routed
  under-path: Drone's E shows 3.7 -> 15.8 mm of in-letter travel (covered,
  needle-down, not on cloth) and no jump. The pro trims there instead.
