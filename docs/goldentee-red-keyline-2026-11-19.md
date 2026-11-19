# Golden Tee red keyline: measured, and `keyline_under_face` (built OFF, not clearly better) (2026-11-19)

**Not a flip candidate (director, 2026-11-19): ON erases the outline the art draws; left OFF, no thin-red variant to be built.**

Prime-grader `L_goldentee_hat`, after #1681: GOLF and the big GT still read red-edged, "not as flat as a professional's".
Hat at 74.9 mm, `hat_front`, main `e4b0428e`.

## Measured (numbers only)

| | red keyline (Burnt Orange 1312) |
|---|---|
| ART, mean width 2A/P | 0.37-0.48 mm on the long bands; 0.13-0.2 mm on the small ones |
| OURS, sewn | every band is satin (underlay + satin), cross median 1.2-1.3 mm, thinnest 0.95-1.2 |
| excess | about art + 0.8 mm = `SATIN_MIN_CROSS_MM` / `OUTLINE` floor plus pull 0.4 (**gate 1, untouched**) |
| order | LAST block (layer 5, after gold 3 and pumpkin 4), because `borders_last` puts satin layers after fills |
| PRO (7 colour blocks, DST) | GT outline satin median cross **1.70 mm**, sewn after its fill face; grey 1.36; GOLF one satin colour at 2.72 mm with **no separate keyline in GOLF** |

So width is not where we differ: the pro's GT keyline is wider than ours. The difference is that ours rings GOLF in red sewn
over the gold. No hairline route applies (no red ring is under the 0.6 mm hairline gate; `bevel_ring_fold` stays OFF).

## Built: `cfg.keyline_under_face` (default False; OFF byte-identical)

`keyline_under_face.py`: a layer that is >= 80% dark thin bands (<= 0.8 mm, L* <= 40), and is not the design's darkest ink,
moves to sew just before the earliest lighter face-sized layer it touches. Stage 5 then plans the overlap against the order
actually sewn, so the face covers the keyline's inner excess (the mechanism of #1681's black fix). Order only.
First version also moved the black: the white swoosh then covered the black arc; the darkest ink is now exempt.

## Result: 3 of 44 move; the red is not thin, it is gone

Golden Tee hat: stitches 9,943 -> 10,041, trims 54 -> 50, needle-up 642.6 -> 609.3 mm, jumps 21 -> 21, 6 threads, bare 0.0 both,
preflight B 76 both, same findings. 80 mm fixture: 10,602 -> 10,758, trims 59 -> 53, bare at 0.20 mm 0.31 -> 0.21, preflight C 64 both.
Summit badge: 28,526 -> 28,475 stitches, threads 8 -> 6 (two dark blocks merge), bare and preflight identical, picture unchanged by eye.

By eye: GOLF becomes one flat gold/orange face with the bevel, the pro's reading, and the GT white face is clean; **but the red
outline is all but erased everywhere** (a sliver survives at the T's right edge), not drawn at the art's 0.4 mm. The face
covers more than the keyline's inner excess (face underlap + pull reach about 1.2 mm). The art does draw a thin dark-red line there,
and the pro keeps one round GT. Not clearly better than OFF: **left OFF; the flip is Kent's, and the pictures are above.**

## Not changed / next

Satin floor, pull, cover tolerance: untouched (gate 1). A thin-red variant (sew the keyline last as a run or bean at about
0.45 mm) is the other direction and a sew-out question; row added to `docs/sew-out-list-2026-11-18.md`. Bevel colours on the GT and
the long travel across the face: not looked at (after the keyline, per the brief).
