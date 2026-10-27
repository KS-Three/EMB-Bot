# Script strokes that flow (`script_strokes`) — 2026-10-26

Kent, 2026-10-26: "Also, the cursive needs to flow, as if the direction (or
centerline letter path) was drawn by a pencil or hand". This builds on
`script_strokes` as #1119 merged it (built OFF), before its flip, so the flip
carries it. Engine `d7eaeb33` (this branch); each job built once, planned
OFF, ON as #1119 merged (its module swapped in, same generation) and ON with
the flow; the pro's file read beside it for the numbers. The pictures are
OURS only: the repo is public, and no render of the pro's stitch file is
committed.

## What changed

- **Welds and cusps.** At a junction two arms that continue within 60 deg
  of straight are one pen stroke (was 40); a stroke splits only where it
  turns back more than 120 deg (was 75): the pen goes round a bend and
  through a join instead of stopping and restarting at a new angle.
- **Two smoothings, not one.** The stations sit on the stroke's middle
  smoothed 0.75 half-widths; each cross lies square to the path smoothed
  1.0 half-width. Harder smoothing looks smoother and is wrong on small
  script: at 2 half-widths the crosses leaned off their own column round
  Bridge's bowls (square-to-column 0.88 -> 0.72 hat, 0.79 -> 0.57 LC, word
  alone), and the pro's crosses turn sharply where his letters turn.
- No width, pull or density constant moved; rails stay on the traced polygon.

## One reader for both files (`tools/script_flow.py`, the word's colour block)

Cross chains as `tools/letter_pieces` cuts them but NOT cut at a turn (a jump
in cross angle is what this reads). Each cross against the one two on (a
zigzag's neighbours lean opposite ways). A hand-over: two columns sewn one
after the other whose ends meet within 1.5 mm, its angle the axial mean of
each end's two crosses. A kink: the midpoint path's heading turning more
than 35 deg within 1 mm. To a T's "Machine" is read in a box
(`--box 0.04,0.30,0.96,0.69`): its colour block also holds TO A T, LLC and
the frame. Squareness: `tools/script_census.py` (a cross within 20 deg of
square to the column its own coverage draws).

| job | arm | columns | cross turn deg/mm p50 / p95 | largest turn between crosses | crosses turning > 15 deg | hand-overs (> 30 deg) | hand-over turn p50 / max | kinks per 10 mm | square to the column (crosses read) |
|---|---|---|---|---|---|---|---|---|---|
| Bridge LC | OFF | 23 | 4.3 / 17.1 | 19.7 | 16 | 7 (5) | 75.5 / 81.7 | 2.48 | 0.77 (116) |
|  | ON as #1119 merged | 18 | 8.6 / 41.1 | 39.1 | 26 | 5 (5) | 62.4 / 86.9 | 3.55 | 0.87 (85) |
|  | ON + flow | 13 | 7.2 / 32.5 | 31.2 | 17 | 0 (0) | - | 3.5 | 0.80 (77) |
|  | pro | 15 | 10.8 / 49.9 | 49.8 | 38 | 3 (0) | 11.7 / 25.3 | 1.31 | 0.87 (322) |
| Bridge hat | OFF | 14 | 5.4 / 18.6 | 78.9 | 26 | 3 (1) | 14.5 / 75.5 | 2.27 | 0.74 (87) |
|  | ON as #1119 merged | 17 | 11.8 / 43.4 | 52.4 | 35 | 6 (6) | 62.7 / 80.7 | 3.95 | 0.84 (64) |
|  | ON + flow | 15 | 8.3 / 41.4 | 33.9 | 25 | 4 (3) | 49.8 / 83.5 | 4.16 | 0.65 (76) |
|  | pro | 21 | 11.2 / 52.5 | 49.6 | 39 | 9 (3) | 26.8 / 78.6 | 0.73 | 0.77 (216) |
| Tires | OFF | 26 | 4.2 / 23.8 | 38.2 | 84 | 3 (3) | 42.6 / 48.1 | 2.15 | 0.77 (2099) |
|  | ON as #1119 merged | 16 | 3.0 / 12.6 | 34.2 | 12 | 3 (3) | 75.8 / 79.4 | 3.07 | 0.97 (1324) |
|  | ON + flow | 23 | 2.9 / 15.2 | 27.4 | 9 | 8 (1) | 0.7 / 65.1 | 2.64 | 0.97 (1274) |
|  | pro | 14 | 4.4 / 11.7 | 7.1 | 0 | 5 (0) | 1.2 / 2.5 | 2.37 | 0.91 (3898) |
| To a T "Machine" | OFF | 39 | 4.8 / 18.6 | 60.6 | 44 | 11 (7) | 33.0 / 77.4 | 1.8 | 0.86 (3849) |
|  | ON as #1119 merged | 34 | 5.7 / 25.8 | 52.2 | 34 | 10 (9) | 50.2 / 76.4 | 1.65 | 0.89 (3531) |
|  | ON + flow | 27 | 4.9 / 29.0 | 43.6 | 53 | 5 (4) | 57.6 / 78.4 | 1.82 | 0.89 (3550) |
|  | pro | 27 | 5.2 / 24.4 | 55.3 | 27 | 7 (3) | 27.1 / 81.8 | 0.6 | 0.89 (3020) |

To a T's squareness is over its whole colour block (`script_census` has no box); the flow columns are read in the box.

Letter order (Bridge only: Tires' T bar overhangs its i, so letters do not
cut by x; backtracks = a column sewn in a letter left of the one before):

| job | arm | backtracks | columns per letter |
|---|---|---|---|
| Bridge LC | OFF | 4 | [5, 4, 1, 5, 5, 3] |
| Bridge LC | ON as #1119 merged | 3 | [4, 1, 1, 4, 3, 5] |
| Bridge LC | ON + flow | 4 | [3, 2, 1, 1, 2, 4] |
| Bridge LC | pro | 0 | [4, 3, 2, 2, 3, 1] |
| Bridge hat | OFF | 3 | [6, 2, 1, 4, 1, 0] |
| Bridge hat | ON as #1119 merged | 5 | [4, 3, 1, 3, 3, 3] |
| Bridge hat | ON + flow | 2 | [3, 2, 0, 3, 3, 4] |
| Bridge hat | pro | 2 | [6, 3, 2, 3, 4, 3] |

Whole design (stitches / trims): Bridge hat 9,608 / 30 OFF -> 9,555 / 30 as #1119 merged -> 9,419 / 30 with the flow; Bridge LC 15,278 / 38 -> 15,011 / 39 -> 14,861 / 38; Tires 8,205 / 8 -> 4,807 / 5 -> 4,624 / 6 (pro 5,555 / 10); To a T Machine hat 23,427 / 60 -> 22,837 / 58 -> 22,821 / 58.

## Pictures

| file | what |
|---|---|
| `angle_*.jpg` | every satin cross coloured by its direction (hue = angle mod 180): OFF, ON as #1119 merged, ON + flow. A pen's satin changes colour smoothly; a jump in colour is a jump in the crosses |
| `crops40_*.jpg` | OFF, ON as #1119 merged, ON + flow at 40 px/mm, crosses visible (Tires and To a T drawn grey) |

## What it does not do

- **Kinks did not come down on Bridge or To a T: they are the trace, not
  the path.** Bridge's crosses change length 0.76 / 0.85 mm per mm of
  advance, hat / LC (the pro 0.19 / 0.22, our LC OFF 0.86): the rails
  follow a traced outline that swells and pinches, and keeping the reach to
  the traced polygon was the brief. Tires reads 0.25 against the pro's 0.30,
  and its kinks sit at the pro's (2.64 / 2.37).
- **Squareness on Bridge fell against #1119 as merged** (hat 0.84 -> 0.65,
  LC 0.87 -> 0.80; the pro 0.77 / 0.87), read on 64-85 crosses a cell, so
  noisy; at a 2 half-width sigma it was 0.55 / 0.62. Tires and To a T are
  unchanged. That is the trade for hand-overs at the pro's count.
- **Two spots on Tires still hand over hard:** the s's top, a cusp the pro
  also cuts at, and the s's foot (one 65 deg hand-over onto an 8-cross
  piece). The e's loop is read as a stroke of its own (it meets the
  baseline 0.6 mm from where the baseline runs on); joining the two nodes
  and pairing a 4-way junction's arms by least total turn ran the e on in
  one, but left Bridge LC 6.7 -> 11.0 mm2 to patches (word alone, sigma 2):
  not built.
- With `script_strokes` ON, `monoline_script_satin` never sees a script word
  (the route returns first). Tires: monoline ON = OFF byte for byte, and
  ON + monoline = ON byte for byte. It is still reachable for a monoline
  stroke the door refuses; nothing in the 21 paired jobs is one.
