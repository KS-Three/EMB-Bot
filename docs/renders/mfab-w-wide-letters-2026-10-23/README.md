# MFab's W of WELDING, and wide letters in the text tagger (2026-10-23)

`cfg.text_cluster_wide_letters`, built OFF. MFab hat at 104.9 mm
(`testdata/art/logo_mfab_hat.png`, the Studio's request through
`tools.pro_pair.digitize`), with the main checkout's rembg venv, so the
photo prep the product runs is the one measured here. A worktree without
that venv runs a different pipeline (`seeds-request-and-the-worktree-blind-spot-2026-09-22`):
there the W fails the same way but AND survives.

## Where the W drops out

| stage | what happens to the W | evidence |
|---|---|---|
| 1 photo prep | the W's right vertex and the E's foot meet through the keyline: the art leaves 2-3 anti-aliased px between them at 3.9 px/mm | `mfab_W_stages_off.png`, rows 1-2 |
| 2 SLIC merge / 3 masks | W and E are one black label, one mask | rows 3-5 |
| 4 vectorize | one region `S6ee94d7e`, 17.5 x 6.9 mm, aspect 2.55; an opening at r 0.03 mm already parts it in two, so the join is a touch, not a stroke | row 6 |
| 4 text tagger | letter door: `ASPECT_RATIO_MAX` 1.4 refuses it. No cluster, no `text_candidate`, no `lettering_group` | `textcluster._letter_candidates` |
| 7 | `columns.is_lettering` false: the satin ladder sews W+E as one shape, the tangle | `mfab_W_construction.png`, left |

Split off the E by hand, the W ALONE is still refused: its long lead-in
arm makes it 10.75 x 6.8 mm, aspect 1.58. Two conditions stacked.

Under the photo path the A and N of AND touch the same way (one region,
14.3 x 8.1 mm, aspect 1.76), which leaves the D short of a three-member
line: the whole word is untagged. (The 10-23 band captures, run
from a worktree without rembg, had AND separate.)

## The fix (ON)

1. `_neck_split`: a region the door refuses as too wide, beside a line it
   could join, is cut at every neck under a quarter of its own stroke
   (opening at `NECK_OPEN_FRAC` x the stroke half-width); the pieces tile
   it exactly and replace it only when every piece is tagged.
2. `_adopt_wide`: a glyph with aspect 1.4-1.8 (`WIDE_LETTER_ASPECT_MAX`,
   under the rescued fragments' lowest 1.78) joins a tagged line it links
   to; it never makes or bridges one.

## The W, OFF | ON | pro

`mfab_welding_off_on_pro.png`: art, ours OFF, ours ON, the pro's hat DST,
each in its own frame (crop 28-82 x 22-38 mm from each design's top-left).

`mfab_W_construction.png`, needle paths of the W only (ours: the W's own
runs, ties and splits stripped; the pro: his runs in the W's window), read
by `tools/column_harness.census`:

| arm | columns | butts | gaps | travel off the letter mm | trims in the W | stitches | median cross mm |
|---|---|---|---|---|---|---|---|
| OFF (W+E region, W window) | 8 | 10 | 1 | 67.5 | 0 | 263 | 1.80 |
| ON (the W) | 4 | 3 | 0 | 0.0 | 0 | 149 | 1.86 |
| pro | 7 | 0 | 0 | 0.0 | 0 | 154 | 1.71 |

OFF sews 343 mm of satin outside the merged polygon (+0.3 mm); ON the W
38 mm (its acute tips), the E none. The whole design: 11,605 stitches / 65
trims OFF, 11,375 / 62 ON.

## Who else hits it (sizes the fix)

Every paired job at the pro's width, OFF then ON, rembg on, the whole
design's stitch list md5'd (`[x, y, kind, jump, trim]` per point):

| job | width mm | text-tagged OFF / ON | split | adopted | letters newly tagged | stitches / trims OFF -> ON | md5 |
|---|---|---|---|---|---|---|---|
| Becker hat large | 101.9 | 11 / 11 | 0 | 0 | 0 | 9,411 / 28, same | identical |
| Hotel Fremont hat | 92.6 | 33 / 33 | 0 | 0 | 0 | 18,629 / 58, same | identical |
| Gaulke Roofing hat | 114.2 | 39 / 39 | 0 | 0 | 0 | 7,955 / 37, same | identical |
| Bridge hat | 63.3 | 0 / 0 | 0 | 0 | 0 | 10,156 / 48, same | identical |
| MFab left chest | 96.7 | 21 / 22 | 0 | 1 (the W, alone, aspect 1.49) | 1 | 11,917 / 74 -> 11,877 / 74 | moves |
| MFab hat | 104.9 | 10 / 16 | 2 (W+E, A+N) | 1 (the W, 1.58) | W, E, A, N, D (+ the wedge `Sb189ad6d` joins AND, as in the no-rembg capture) | 11,605 / 65 -> 11,375 / 62 | moves |

So the condition is MFab's lettering face, not a general one: six letters
over the two MFab files, none on the other four jobs. Bridge's script
stays untagged either way. Not this fix, a different condition: on MFab
LC the N of AND (`S81d1d4a6`, 6.25 x 7.9 mm, aspect 0.79) carries neither
tag -- it is 7.9 mm tall beside 6.25 mm letters, a height ratio of 0.79
against `LETTER_HEIGHT_RATIO` 0.8. WELDING's N and G there carry
`lettering_group` but no text cluster, so they reach the lane through the
house group already.
