# Script stroke ends: the professional's measured, and why no end flag (2026-11-19)

**Verdict: on Tires hat the stroke-end PROFILE is already the professional's. A flag that clips free-end
crosses to a round cap was built, changed 0 columns, and was removed. What differs is the stroke's width
(gate 1), the cross angle at some ends, and the join gap, which sit in the route / column split another worker
owns.** Numbers only; the professional's DST was read from the committed `Embroidery Files.zip`
(`tires_hat_3d`), extracted outside the repo. Nothing of it is rendered or committed.

Reader: `python -m tools.script_ends FILE.dst@BLOCK` (new; same cross chains as `tools.script_flow`). Pro =
block 1 of `TIRES HAT 3D.DST` (14 columns of 6+ crosses); ours = `tools.pro_pair.digitize(testdata/
logo_script_tires.png, 114.3, 'hat_front')` written with `export.write_dst` (26 columns, block 0).

## Free stroke ends (pro 16, ours 19)

| | face to axis (90 = square) | last 3 crosses / median | taper to full cross |
|---|---|---|---|
| pro | 80.9 deg median | 0.39 (0.25-0.45) | 1.84 mm |
| ours | 65.8 deg | 0.67 | 0.9 mm |

Read alone that looks like "ours is slanted and abrupt", which is what the 11-18 note guessed. The cross
lengths from the tip inward, at five ends matched by position, say otherwise (mm, tip first):

- pro (-54.9, 17.5): 1.1 1.3 1.6 1.7 2.0 2.2 2.4 2.5 2.8 2.8
- ours (-55.0, 17.5): 1.1 1.5 1.8 2.2 2.5 2.9 3.1 3.6 4.0 4.3

Same tip (1.1 mm), same round-cap growth; the pro's stroke simply stops widening at about 3 mm there where
ours goes on to 4.3. Interior cross length (columns of 20+ crosses, middle half): pro median **4.31** mm
(p10-p90 3.98-4.75), ours **4.92** (4.39-5.30): ours is 0.6 mm wider, about the 0.4 mm/side pull minus his
own. That is the pull constant (ROADMAP gate 1, `docs/sew-out-list-2026-11-18.md` row 13), not an end face.
The "taper 1.84 vs 0.9" and "0.39 vs 0.67" rows above come from his narrower stroke reaching full width
sooner after a tip of the same size, not from a different cap.

Inside the plan the free end already tapers: the last station of a free stroke is 0.13 mm long (0.86 on the
other end), before the satin adds its pull. Clipping those crosses to a circle chord
(`round_ends`, tried 2026-11-19) changed 0 of 5 Tires columns and the DST was byte-identical.

## Joined ends (12 pro, 33 ours): the e-to-s style butt

| | face | last 3 / median | nearest other column's cross midpoint |
|---|---|---|---|
| pro | 62.7 deg | 1.08 (no taper) | 0.25 mm (0.15-0.30, one 1.00) |
| ours | 65.9 deg | 1.02 | 0.6 mm (0-1.27) |

At the e/s step (design 36, 14) ours has four column ends 0.99-1.38 mm from their neighbour where the pro has
one free end at (37.5, 11.9). The pro sews 14 columns of this word to ours 26; the extra ends are splits.
**That is the route/column split (`script_strokes.pen_strokes`, `_split_cusps`), the area the "Prime fix 33"
worker is changing, so it was not touched here.**

## Left for others
- Join gap and column count: route selection (Prime fix 33).
- Stroke width 4.92 vs 4.31 mm: gate 1, `script_strokes_pull_by_stroke` (built OFF).
- Face angle: ours is 15-20 deg off square at a few ends ((7.3, -20): 66-76 deg along ten crosses against
  the pro's 85-89). The Tires polygon carries a bevel, so the chord midpoints wander off the spine; not
  shown to be an error, not fixed.
