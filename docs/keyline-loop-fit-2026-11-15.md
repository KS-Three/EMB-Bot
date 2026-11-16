# `keyline_loop_fit`: a keyline whose loop would swamp its letters sews as the thin line (built OFF, 2026-11-15)

Kent, 2026-11-15: "Fix MFab white loops". `cfg.extra["keyline_loop_fit"]`,
default OFF. Nothing a customer sews changes.

## The defect

With `photo_enclosed_rim` ON the MFab hat's white keyline is read at its true
width. From 38 mm wide that width passes the hairline gate (0.6 mm at 40 wt),
so the keyline stops sewing as a bean and sews as a satin loop, which is never
under `machine.OUTLINE_WIDTH_MM`'s 1.5 mm. The loop is wider than the line the
art draws, and what it gains it takes from the letters it rings: at 38 to 60 mm
the M-FAB faces sew as slivers between white loops and the hyphen is lost.

## The rule

`keyline_bean.loop_fits`: a loop fits when the median body it rings, less the
loop's excess over the drawn keyline, is still at least as wide as the loop.

    stroke - (loop - keyline) >= loop

A thread whose loops do not fit is read against the loop's own width in place
of the hairline's, so its keylines sew as the bean. Every other test in
`keyline_bean.keyline_regions` still applies (one decision per thread, never a
letter, the thread draws nearly nothing but keyline, not a blob, not the
raster's fringe). A keyline already 1.5 mm wide or wider is never taken.

No new constant: the comparison is the loop against the face it leaves.
Layout, judged in the preview, as `OUTLINE_WIDTH_MM` is. Unsewn.

## MFab hat, `photo_enclosed_rim` ON, no cutout (mm)

| width | keyline | loop | letter stroke | face left | fits |
|---|---|---|---|---|---|
| 30 | 0.48 | 1.50 | 1.48 | bean already | |
| 36.7 | 0.58 | 1.60 | 1.83 | bean already | |
| 38 | 0.60 | 1.62 | 1.90 | 0.88 | no |
| 40 | 0.64 | 1.67 | 1.98 | 0.95 | no |
| 45 | 0.72 | 1.70 | 2.25 | 1.27 | no |
| 50 | 0.82 | 1.72 | 2.50 | 1.59 | no |
| 55 | 0.90 | 1.93 | 2.71 | 1.68 | no |
| 60 | 0.95 | 2.01 | 2.95 | 1.88 | no |
| 70 | 1.08 | 2.06 | 3.43 | 2.45 | yes |
| 80 | 1.20 | 2.14 | 3.91 | 2.97 | yes |
| 100.8 | 1.42 | 2.12 | 4.93 | 4.23 | yes (the pro borders this size at 2.40) |

Rim OFF, where the loop is what sews today: 55 mm 0.66, 1.50, 2.50 leaves
1.66 and 60 mm 0.70, 1.50, 2.73 leaves 1.93. Both fit.

## What it sews (flag ON; today ; with the key)

| width | stitches | trims | blocks |
|---|---|---|---|
| 38 | 5,048 ; 4,782 | 13 ; 7 | Black White Black ; Black White |
| 40 | 5,545 ; 5,263 | 12 ; 6 | same |
| 45 | 6,355 ; 5,834 | 13 ; 11 | same |
| 50 | 7,144 ; 6,581 | 15 ; 15 | same |
| 55 | 8,206 ; 7,510 | 15 ; 12 | same |
| 60 | 9,356 ; 8,405 | 14 ; 14 | same |
| 70 | 11,472 ; md5-identical | | |
| 80 | 14,038 ; md5-identical | | |

Grades are the same in both arms at every width (B, B, C, C, C, C, B, B).
Renders looked at, 38 to 70 mm, both arms: with the key the faces are black,
the keyline is a thin white line and the hyphen is back. Sheet:
[`renders/keyline-loop-fit/mfab-ladder.png`](renders/keyline-loop-fit/mfab-ladder.png).

**Open, for Kent:** at 50, 55 and 60 mm the thin line gains
`ARTWORK_UNCOVERED`. The drawn keyline there is 0.82 to 0.95 mm and a bean is
one thread, so the line is thinner than the art. The loop at those sizes is
1.7 to 2.0 mm. Neither is the drawn width; the rule picks the one that keeps
the letters. Where the loop should take over (the rule says between 60 and
70 mm) is his to judge from the sheet.

## What does not change

- **Key OFF:** `bodies` is never read; the code path is the one before.
- **Key ON, rim OFF, MFab at 45, 50, 55 and 60 mm:** md5-identical to key OFF.
- **Key ON, the repo's other 15 logos at 60 mm** (`testdata/art`, flat lane):
  the keylines taken are the same set on every one. Decisions only, no
  stitches planned. Commons "Ahora"'s gear fits by 0.03 mm (2.17, 0.86, 1.50).

## How this was measured, and what was not

- **No cutout lane only.** The rows were run on the cutout lane, but on this
  desktop the cutout was unavailable in 31 of 33 runs (kernel memory, DOCTRINE
  gotchas 2026-11-14), and a refused cutout sews the no-cutout design: three
  rows re-run with `photo_prep=False` were md5-identical. The two runs where
  the cutout did work are not used. **The cutout lane is not measured.**
- The "today" stitches at 40 to 60 mm are from the tree before main's latest
  merge; 38 and 80 mm were re-run on this tree and are md5-identical.
- The full digitizer suite was not run locally.

*(measured 2026-11-15 — `tests/test_keyline_loop_fit.py`; width runs on a
Windows desktop, hat_front, 6 colours)*
