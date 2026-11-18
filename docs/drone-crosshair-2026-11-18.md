# Precision Drone crosshair: the left arm is not lost (2026-11-18)

Scorecard fault: `L_precision_drone`, (22.0, 35.5) mm, "the left arm of the horizontal crosshair with its tick marks is missing; only the right arm is sewn, and without ticks." Reproduced on main `8051f118` (`tools.prime_grader capture --only precision_drone`, then `kit`). Pictures are our render and the original only: `docs/renders/drone-crosshair-2026-11-18/`.

## What is true by eye and by number

- **The left arm is sewn whole.** Stage 2 labels and stage 3 regions both carry the white line with its ticks; one region (`Sc839deb3`, thread 3971, 0.33 mm wide) holds the left arm, the ring and the right arm, from x = -11.2 to +10.9 mm (plan coords). The plan sews it as satin (50 points on the left arm, 0.5 mm apart, 0.8 mm columns) over the underlay. `arms-region-vs-stitches.png` draws region against stitches. `left-arm-ours.png` beside `left-arm-original.png`: a row of white bars from ruler x 23.3 to the ring, the art's arm being 8.6 mm long. Not dropped, merged or clipped at any stage.
- **The right arm is sewn too** (a white band with a tick-shaped jog near ruler x 41).
- **The grader's "missing" is a misread** of the bars: each stitch is drawn as a separate tube at this scale, so a 0.8 mm satin at 0.5 mm spacing reads as a dashed ladder, not a line.

## What is real: the ticks

The traced ticks are about 0.3 mm wide and protrude 0.3-0.5 mm beyond the 0.8 mm band. Three of the four are sewn as a short zigzag or as no more than one column (the left one at plan x -7.4 is a plain column); none stands out as a tick. A tick that small is below what the 0.5 mm satin spacing resolves. Drawing it would mean a column wider than its neighbours at one spot, or a separate 0.3 mm run: a satin width / spacing decision that only a sew-out settles (ROADMAP gate 1). Not built.

## Existing flags

`merge_chroma_guard` (OFF) acts on the sky/black merge, not on this region; `fine_bar_survive` (ON) rebuilds broken dark straight bars, and this white line was never broken. Neither is the cure; nothing was changed in code.
