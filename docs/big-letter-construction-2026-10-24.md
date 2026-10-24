# How the pro cuts big satin letters (2026-10-24)

Task L6 of the lettering band work, after `docs/lettering-10mm-up-2026-10-23.md`
(#1052), which found that on Becker's MARINE the pro sews 163 columns to our 77.
The question here: where do his extra cuts fall, what rule puts them there,
and what do they buy -- before anyone copies the count. **Investigation only;
no engine change.**

## The answer in four lines

- **The count reproduces, but it is mostly not strokes.** With a new reader
  (below) the four MARINE files give the pro 108 pieces + 35 junction patches
  (143) against our 76 + 2. A quarter of his pieces are patches of 4-8
  crosses inside a junction. The rest of the gap (108 to 76) splits about
  evenly between one feature of the font -- a **sheared slab across the top
  of every letter** that he sews as its own piece (23 straight cut ends in the
  top 35% of the cap) -- and junction cuts lower down that keep a diagonal's
  crosses horizontal where it meets a stem (21 in the bottom 35%).
- **His rule:** he cuts where the outline makes a NOTCH -- through each
  reflex vertex, along the cross direction (the slab's base at 22-30% of the
  cap, a diagonal leaving or joining a stem, a bar or arm butting a stem's
  side) -- and runs one column through convex corners and curves; inside each
  piece the crosses lie parallel to the piece's own end cuts (horizontal over
  the flat baseline ends, 99-118 deg in a slab whose edge is 103-105 deg).
- **What the cuts buy is cross DIRECTION, not thread.** On MARINE's leaning
  strokes 47-58% of his crosses sit within 15 deg of the line of text, ours
  17-25%. They do not buy shorter stitches, fewer same-hole needle drops or
  denser ends: those read the same on both sides.
- **Do not copy the count.** The direction is already built without a single
  extra cut -- `lettering_columns_text_lean` (OFF) lifts ours to 51-53%
  (56% with `lettering_columns_corner_fold`) on 16-17 pieces. On the second
  job, PROSEAL, he cuts LESS than we do (11 to 18) and `corner_fold` closes
  most of that (13). Both flags are layout flags (Kent, 2026-10-22: flip from
  renders and numbers); flipping them is Kent's call. The one thing neither
  flag does -- the slab cut -- is one font; listed, not proposed.

## How it was read

`digitizer/tools/letter_pieces.py` (new, reusable; pinned by
`digitizer/tests/test_letter_pieces.py`). One rule on every file, each file
in its own frame:

- **Needle-down runs** (JUMP / TRIM / COLOR_CHANGE end one); **split legs
  fused** -- consecutive stitches within 12 deg of one another, each over
  0.3 mm, merged while the merged stitch is under 12 mm, so our split satin
  (A->M->B, and A->M1->M2->B on a 7.7 mm cross at 101.9 mm) counts each
  cross once. *The first pass fused only two legs and lost our R, I and N
  tops at 101.9 mm; fixed before any number below.*
- **Crosses**: stitches of 1.0 mm or more, each anti-parallel (within 45 deg)
  to the one before, midpoints advancing 0.9 mm or less; up to two short
  stitches inside a chain are skipped.
- **A cut** is where a chain breaks: the next cross starts more than 1.5 mm
  away, turns more than 35 deg from the last, or the needle leaves the
  zigzag. A **piece** is 4+ crosses over 0.3 mm of spine (a lock stitch has
  none); a **patch** is a piece under 2.5 mm of spine (a junction fill-in).
- **Letters** are connected components of the rasterised piece crosses
  (10 px/mm, 0.4 mm thread) -- never a box mapped from the art. A word is
  picked by its row (`--rows`) and a minimum letter height.
- **Piece ends** are read at the end cross: `free` (nothing there -- a stroke
  terminal), `butt` (it meets another piece's BODY -- a junction), `corner` /
  `straight` (it meets another piece's END, axes apart by more / less than
  30 deg), `patch` (it meets only a patch).
- **Leaning crosses** are the crosses of pieces whose axis is 12-65 deg off
  vertical (the M's and N's diagonals, the A's legs, the R's leg); the
  number is the share within 15 deg of the line of text.
- Thread numbers: crosses over 5.0 mm (`SPLIT_SATIN_ABOVE_MM`), the longest
  cross, the share of same-rail needle steps under 0.1 mm (`same hole`), and
  each piece's cross pitch in its last 1 mm over its middle's.

```
python -m tools.letter_pieces FILE.dst --rows 0.6 1.0 --min-height 8 --table   # one row
python -m tools.letter_pieces FILE.dst --rows 0.6 1.0 --png pieces.png          # per piece
```

Ours: `tools/border_census.py one SLUG` (the Studio's request at the pro's
width and preset, written to DST), and the same request with `--set`-style
extras through `tools.pro_pair.digitize` for the flag arms. The pro's: his
DST/PES from `Embroidery Files.zip` (`testdata/reference/` for Becker).

## Premise check: 163 to 77

| MARINE, four files | pieces | patches | total |
|---|---|---|---|
| pro (this reader) | 108 | 35 | 143 |
| ours, shipped (this reader) | 76 | 2 | 78 |
| #1052's reader | | | 163 / 77 |

Both readers agree that he sews about twice our pieces. Excluding patches
the gap is 108 to 76 -- and the piece ENDS say where it lives:

| piece ends, four files | free | butt | corner | straight | patch |
|---|---|---|---|---|---|
| pro | 46 | 57 | 45 | 44 | 24 |
| ours | 47 | 46 | 46 | 10 | 3 |

Corners are level (45 / 46): the extra cuts are **straight** joins (44 to
10), more butts, and the patches. Of his 44 straight ends, **41 have a third
piece within reach** -- they sit at a junction, not mid-stroke -- and none
falls between 35% and 65% of the cap height (14 at 0-20%, 9 at 20-35%, 15 at
65-80%, 6 at 80-100%). **There is no length cap**: his stems run 9.8-10.4 mm
uncut below the slab, his I 23 mm of spine with its slab fan, his R's slab +
bowl one 33.7 mm piece.

## MARINE at 76.5 mm, per stroke (Becker hat small)

Ours = shipped defaults (OFF). Crosses' angle is from the line of text
(0 = horizontal, square to an upright stem). `max` = longest cross.

| letter | stroke | pro | ours |
|---|---|---|---|
| M | slab (top 25%) | sewn with the left diagonal as one piece, crosses -63 deg (along the slab's sheared edge), fanning 55 deg into the diagonal | no slab: the stems run through it |
|   | left stem | 9.9 mm from under the slab, 0 deg, w 4.00 | 13.7 mm full height, 0 deg, w 4.60 |
|   | left diagonal | in the slab piece, crosses square-ish to it | 11.7 mm, -43 deg, drift 55 deg (fans at both ends) |
|   | right diagonal | 3 pieces cut at the junctions: merged with the stem top (2.9 mm, w 6.0, max 7.0), alone (3.0 mm, w 5.7), the V's bottom where the diagonals meet (3.8 mm) -- **all 0 deg** | 8.5 mm, +39 deg, drift 50 deg |
|   | right stem | 10.3 mm below the merge, 0 deg | 7.4 + 7.9 mm (two pieces), 0 deg |
|   | V | 3 patches | none |
| A | slab / apex | a slab piece (vertical crosses) + the right leg's start | none |
|   | legs | left 10.4 mm at 0 deg from under the slab; right 21.7 mm from the apex, fanning 82 deg from the slab angle to 0 | 17.5 mm at +15 deg, 15.9 mm at -10 deg |
|   | crossbar | 5.6 mm, vertical crosses, butts both legs; 2 patches | 7.4 mm, crosses 74 deg, butts both legs |
| R | slab + bowl | ONE piece: 33.7 mm, the slab's crosses turning radially round the bowl | the stem (14.9 mm, 0 deg) and one 26.4 mm piece: bowl + leg, drift 96 deg |
|   | stem | 10.1 mm below the slab, 0 deg | (above) |
|   | leg | 4.7 mm at 0 deg, its own piece; 5 patches at the bowl-leg-stem junction | in the bowl piece, -17 deg |
| I | stem + slab | one piece, the slab's crosses fanning into the stem's 0 deg | 12.8 mm, 0 deg |
| N | slab + diagonal | one piece, the slab fanning into the diagonal (median -32 deg) | -- |
|   | left stem | 9.8 mm from under the slab, 0 deg | 12.9 mm full height, 0 deg |
|   | diagonal | cut where it leaves the left stem's slab, and again where it joins the right stem | 17.5 mm, -36 deg, drift 56 deg |
|   | right stem | 9.9 mm above the merge + 3.9 mm merged with the diagonal (w 5.0, max 5.9), **0 deg** | 12.0 mm, 0 deg, fans where the diagonal meets it |
| E | slab + top arm | one piece across the whole top, crosses -77 deg (vertical-ish) | top arm 6.5 mm, -84 deg; the stem runs through |
|   | stem + bottom arm | ONE piece folded round the foot (24.1 mm, the crosses turning 82 deg) | stem 13.0 mm; each arm its own piece, cut at the stem |
|   | middle arm | its own piece, vertical crosses, butts the stem; 2 junction pieces | its own piece, butts the stem (arms 7.8 and 5.4 mm, 82-84 deg) |

The slab is the ART, not a style: every MARINE letter's top quarter is a
parallelogram sheared to the left -- a notch on the left edge at 22-30% of
the cap (visible in the artwork row of `marine_76_art_off_pro.png`). Read on
our own polygons at 101.9 mm, the slab's left edge runs at 103-105 deg (4.3-
4.9 mm long, top 28% of the 17.1 mm cap); his top-20% crosses run at a median
99, 101, 104, 102, 109 and 118 deg -- parallel to that edge within 6 deg on
five letters (the I's 118 is its fan). The pro's own sew-out simulation
(`becker_hat_polo_large_beckers_logo_hat.jpg`) shows the slab as a sheen
stripe across the word. Ours sews straight through it.

## All four MARINE files

| file (width) | side | pieces + patches | per letter M A R I N E | leaning within 15 deg (median deg) | crosses > 5 mm | max cross | same hole |
|---|---|---|---|---|---|---|---|
| hat small (76.5) | pro | 27 + 12 | 6 6 4 1 5 5 | 0.48 (16.7) | 4.2% | 7.01 | 0.43% |
|  | ours OFF | 18 + 0 | 5 3 2 1 3 4 | 0.24 (32.0) | 14.3% | 6.96 | 0.19% |
|  | ours `text_lean` | 17 + 0 | 4 3 2 1 3 4 | 0.51 (14.5) | 18.2% | 6.96 | 0.19% |
|  | ours `text_lean` + `corner_fold` | 16 + 0 | 4 3 1 1 3 4 | 0.56 (10.3) | 19.9% | 6.96 | 0.41% |
| beanie (79.8) | pro | 27 + 13 | 6 7 4 1 4 5 | 0.48 (16.4) | 4.1% | 6.91 | 0.48% |
|  | ours OFF | 19 + 1 | 5 4 2 1 3 4 | 0.20 (36.0) | 15.3% | 8.51 | 0.09% |
| left chest (95.7) | pro | 24 + 4 | 6 3 3 3 5 4 | 0.47 (17.5) | 40.4% | 8.51 | 0.53% |
|  | ours OFF | 21 + 1 | 6 3 3 1 4 4 | 0.25 (37.1) | 66.8% | 8.12 | 0.39% |
| hat large (101.9) | pro | 30 + 6 | 7 5 4 3 4 7 | 0.58 (9.7) | 76.9% | 9.11 | 0.34% |
|  | ours OFF | 18 + 0 | 4 3 3 1 3 4 | 0.17 (40.5) | 76.1% | 9.35 | 0.46% |
|  | ours `text_lean` | 18 + 0 | 4 3 3 1 3 4 | 0.53 (14.5) | 78.5% | 10.03 | 0.24% |

Per-piece cross pitch at the ends over the middle reads 1.00 on both sides
in every file (median), so neither construction sews its ends sparser.
The per-file construction is the same at all four sizes on his side -- one
digitizing scaled -- so the four files are one logo, not four.

## Other big-letter jobs

The 10-23 band census found only MARINE sewn as whole satin on both sides
among the paired designs (Fremont, Gaulke Roofing and Drone are under 10 mm).
So the second and third reads use what has satin letters near or over 10 mm:

| job, word (cap) | side | pieces + patches | per letter | ends free / butt / corner / straight |
|---|---|---|---|---|
| ProSeal hat 85.9 mm, PROSEAL (9.4-9.9 mm, italic) | pro | 11 + 2 | P1 R1 O1 S1 E2 A4 L1 | 9 / 5 / 3 / 3 |
|  | ours OFF | 18 + 0 | 2 4 1 1 5 3 2 | 12 / 13 / 7 / 4 |
|  | ours `text_lean` + `corner_fold` | 13 + 0 | 2 2 1 1 3 3 1 | 12 / 8 / 3 / 3 |
| C Gaulke Plowing logo (`GOLKE LOGO JB 1.DST`), C GOLKE INDUSTRIES (10.7 mm, bold rounded sans) | pro only (no art in the set) | 28 + 0 over 16 letters | C1 G2 O1 L1 K3 E2 I1 N5 D2 U1 S1 T2 R2 I1 E2 S1 | 33 / 13 / 5 / 5 |
| Tires hat 3D, script (25-33 mm) | pro | 11 + 2 (T 1, swash 1, "ires" 9) | -- | 10 / 6 / 0 / 2 |
|  | ours OFF | the T and swash satin; "ires" is a FILL (`wide_columns` OFF, gate 1) | -- | no comparison |

On both block-letter jobs **he runs one column through every convex corner
and curve**: PROSEAL's P, R (stem into bowl), O, S, the E's outer C and the
L; GOLKE's C, O, L, U, S. He cuts where a stroke butts another's side --
the E's middle arm, the R's leg, the K's arms, the T's bar, the A's crossbar
-- and on a wide flat top (PROSEAL's A, a vertical-cross slab like MARINE's).
His GOLKE N is the one 5-piece letter: the same junction cuts as MARINE's N,
99% of its stroke crosses within 15 deg of the line of text. That is the corner
rule already measured and built in `lettering_columns_corner_fold`
(`.claude/memory/column-corner-folds-2026-10-23.md`: "one reflex corner + an
apex across it = fold; two facing reflex corners = cut").

The GOLKE and Tires files were read pro-only for the rule; no render of the
GOLKE job is committed (a job not yet in the public repo).

## The rule, one sentence

**He cuts a big letter where its outline makes a notch -- through each
reflex vertex, along the crosses (the MARINE slab's base at 22-30% of the
cap, a diagonal leaving or joining a stem, a bar or arm butting a stem's
side) -- and runs one column through convex corners and curves, with each
piece's crosses parallel to its own end cuts (0 deg over flat baseline ends,
99-118 deg in a slab whose edge is 103-105 deg).**

Contradicting rows:

- **The L's inside corner is a reflex vertex he folds THROUGH** (GOLKE L,
  PROSEAL L, MARINE E's foot): one reflex corner with an apex across it is a
  fold; only two facing ones cut (the corner-folds note's refinement holds).
- **The MARINE I**: one piece at 76.5 and 79.8 mm, three at 95.7 and 101.9 --
  the slab notch is cut on the bigger files only.
- **PROSEAL's P counter and O**: their inside corners are reflex too; sewn
  as one column, no cut (rounded corners, no apex).
- **The 35 MARINE patches** are not on any rule: 4-8 crosses at the M's V,
  the A's crossbar ends, the R's bowl-leg-stem junction, the E's middle arm.
  ProSeal has 2, GOLKE none.
- **Thresholds that do NOT exist**: no length cap (no straight cut between
  35% and 65% of the cap; uncut stems to 10.4 mm, curves to 33.7 mm of
  spine); no width cap -- his merged cells carry horizontal crosses to 7.0 mm
  at 76.5 and 9.1 mm at 101.9 (1.75 x the stroke both times: one digitizing,
  scaled).

## What his cuts buy

- **Cross direction -- yes.** Leaning-stroke crosses within 15 deg of the
  line of text: pro 0.47-0.58 on four files, ours OFF 0.17-0.25. His merged
  cells keep the M's right diagonal and the N's foot at 0 deg; ours sews them
  square to the stroke (+39, -36 deg) with fans where they meet the stems.
- **Shorter stitches -- no.** Crosses over 5 mm: pro 4.1-4.2% at 76.5-79.8,
  ours 14.3-15.3% -- but that is ours being wider (4.3-4.6 mm against his
  4.0, the pull compensation, gate 1), not the cuts; at 101.9 it is 76.9% to
  76.1%. His longest cross is 7.0 / 9.1 mm against our 7.0 / 9.35.
- **Fewer same-hole drops -- no.** 0.34-0.53% his, 0.09-0.46% ours.
- **Denser or sparser ends -- no.** End-to-middle pitch 1.00 both sides.
- **Less drift along a column -- no.** His slab pieces fan 50-80 deg into
  their strokes; his per-letter drift p90 is HIGHER than ours (median 66.7
  against 44.7 deg at 76.5).
- **The slab** -- the one thing a cut alone buys: a separate facet whose
  crosses follow the sheared edge. On one font.

## Recommendation: don't copy the count

| candidate | what it is | evidence | cost / catch |
|---|---|---|---|
| **flip `lettering_columns_text_lean`** (built, OFF) | the cross-direction half, no new cuts | leaning share 0.24 -> 0.51 at 76.5, 0.17 -> 0.53 at 101.9 (pro 0.48 / 0.58), same pieces | crosses over 5 mm 14.3 -> 18.2% at 76.5 (a leaned cross is longer); on italic PROSEAL it does not move toward him (0.27 -> 0.21 with fold, his 0.31) |
| **flip `lettering_columns_corner_fold`** (built, OFF) | his convex-corner rule | PROSEAL 18 -> 13 pieces (his 11); MARINE's E foot and R fold as his do | already its own lane's decision (#1054) |
| a slab / notch cut (not built) | cut at a reflex notch along the crosses, crosses parallel to the slab edge | MARINE only, 6 letters x 4 files | one font; a new outline_cut rule for one logo -- not proposed |
| junction patches | -- | MARINE only; ProSeal 2, GOLKE 0 | not a rule; don't |

**Smallest flag: none new.** If Kent wants MARINE's direction, it is the
`text_lean` flip; if he wants PROSEAL's piece count, the `corner_fold` flip.
Both are layout flags, flippable from renders (Kent, 2026-10-22); neither is
flipped here.

## Renders

`docs/renders/big-letter-construction-2026-10-24/` (each file in its own
frame):

- `marine_76_art_off_pro.png` -- `tools/pro_pair.py --band 0.62 1.0` at
  76.5 mm: art | ours (shipped) | pro, the Studio previewer. The slab notch
  is in the art row; the pro's slab reads as a darker band.
- `marine_102_art_off_pro.png` -- the same at 101.9 mm.
- `marine_76_pieces_pro_off_lean_fold.png` -- the reader's pieces, one
  colour each, numbered at their first cross: pro | ours OFF | `text_lean` |
  `text_lean` + `corner_fold`.
- `proseal_86_pieces_pro_off_fold.png` -- PROSEAL: pro | ours OFF | both
  flags. His P, R, E, L are one column each.
