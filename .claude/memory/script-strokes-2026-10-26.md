---
name: script-strokes-2026-10-26
description: Kent "Measure, then build OFF", then "Flip it ON" (10-26) — a script word (Bridge, Tires "ires", To a T "Machine") sewn one satin column per pen stroke, path read on the art's INK, crosses turning with the pen (flow, #1135); `script_strokes` ON; Bridge is trace-limited and the pro re-set it; its fusion is drawn width + pull, a narrower satin is gate 1 (Kent 10-27: record, no build)
metadata:
  type: project
---

**ON by default since Kent's flip, 2026-10-26: "Flip it ON (Recommended)"** (built OFF in #1119, flow in #1135, the flip PR after it; `PRE_FLIP` names the OFF arm). L7b, 2026-10-26, lane `claude/script-strokes-b22fb4`. Module
`digitizer_core/script_strokes.py`; flag `script_strokes` (ON since the flip, #1136); reader
`tools/script_census.py FILE.dst@N#x1,x2` (per-letter split at x-fractions of
the word, each file's own letters).

**The pro, measured:** each script letter one unbroken stretch of the file
(Bridge hat i, r, B, dot, d, g, e); columns B 5, r 3, i 1, d 3, g 4, e 2;
crosses rotate with the stroke (square 0.77 / 0.87 hat / LC); stacked overlap
0. He RE-SET Bridge in a taller font of his own (14.7 vs 11.5 mm tall at the
same 29.7 mm width) — no trace reproduces that; not chased. Width: his
crosses 1.56 / 1.78 mm against the art's drawn 1.76 / 2.12 (pipeline ink
read, half-max); ours = drawn + 0.4 a side. A thinner script pull is GATE 1.

**Script words in the 21 paired jobs: three artworks** (Bridge, Tires, To a
T Machine; 7 shapes). The door: not text, aspect >= 1.4, median mid-height
ink runs >= 5, axis >= 4 heights, half-width CV <= 0.43, largest hole <= 5 %
of hull. Nearest refusal: Golden Tee's fused italic GOLF on CV alone (0.455)
— thin margin. Capitals the trace keeps apart (Machine's M, Tires' T) are
not admitted: aspect < 1.4 / one ink run.

**Why Bridge OFF is a blob:** the satin tier's skeleton welds the FUSED
baseline into one 22.8 mm stroke (i's top -> d -> g), crosses run up the
letters. Force-tag into the Column lane now moves it (09-30 it did not): one
run, overlap 3.9 -> 1.25, but outline_cut took 1,411 s to plan on the loaded
laptop (OFF 100 s) and "ge" stayed two slabs.

**Built OFF, measured ON (one reader per file, the word's colour block;
`docs/renders/script-strokes-2026-10-26/`):** square-to-stroke Bridge hat
0.74 -> 0.84 (pro 0.77), LC 0.77 -> 0.87 (0.87), Tires 0.68 -> 0.95 (0.85),
Machine 0.77 -> 0.85 (0.90); stacked overlap 3.89 / 5.32 / 6.10 -> 0.66 /
1.84 / 0.91 mm (pro 0 / 0.67 / 0); Tires' word fill-in-a-border -> 10
columns (pro 9), 6,428 -> 3,033 st (pro 3,337). Bridge LC reads as six
letters; Bridge hat's "ge" stays a knot (trace). Legibility cc mixed (hat
0.83 -> 0.35, LC 0.28 -> 0.52; n = 1, two of four blind): no claim.
Bystanders Becker, MFab, Fremont, Golden Tee byte-identical ON.

**Traps found:**
- The trace CLOSED counters the art has (Bridge hat: g 1.28, e 0.57 + 0.61,
  B/r 0.36 mm2) and the ground is knocked out under the word except a
  ~0.8 mm underlap: 2.8 mm2 would show BARE CAP if a stroke opened them.
  So rails stay on the polygon; the pen PATH comes from the ink's core
  (t >= 0.85, where those counters are open), and a cross stops at the drawn
  edge only where it would run on into such a CLOSED counter (no fans), with a
  patch over what no stroke reaches.
- An ink read at a flat 20 px/mm shattered Tires' 4.4 mm stroke (608 axis
  edges): read ~16 px across the stroke, and fall back to the polygon when
  the ink's axis has > 3x the polygon's edges.
- Stationing on the SPINE opens the outer rail to 2x pitch round tight loops
  (sparse e/g, and `trim_bury_under_later` stops trusting the cover): keep
  one cross per pitch of the FASTER rail.
- Sewing strokes one by one left to right cut the word 6 / 5 / 14 times
  (Bridge / Tires / Machine); the Column lane's Euler walk over the same
  strokes: 0 / 1 / 1 (patches first). Order is not where the pro's look is.
- Free ends are not only skeleton ends: an end cut at a cusp, or whose only
  neighbour was a dropped knot, must run on to its cap too, or stage 7's
  EDGE CAP rings the bare outline (Tires' r) -- check `__edge_cap__` runs.
- A photo trace runs past the ink along whole strokes (Tires' bevel): stop a
  cross at the drawn edge only into a CLOSED pocket, never an open one.
- A variable named `rd` in a Bash heredoc trips the worktree guard (reads as
  Windows `rd`).
- The word can change the GROUND block's cuts: `trim_bury_under_later`
  buries a yellow hop only under real later thread. With crosses one pitch
  apart on the spine three of Bridge's buried yellow hops came back as cuts;
  with the faster-rail pitch the yellow block is byte-identical again.

**Flow (Kent 2026-10-26: "the cursive needs to flow, as if the direction (or
centerline letter path) was drawn by a pencil or hand").** Reader
`tools/script_flow.py FILE.dst@N [--box x0,y0,x1,y1]`: cross chains as
`letter_pieces` cuts them but NOT cut at a turn; each cross against the one
TWO on (a zigzag's neighbours lean opposite ways); a hand-over's angle is the
axial mean of each end's two crosses (the lean cancels); `--box` because To a
T's "Machine" shares its colour block with TO A T, LLC and the frame. Built:
welds up to 60 deg (was 40), cusps only past 120 (was 75), stations on the
spine smoothed 0.75 half-widths, crosses square to it smoothed 1.0.
Measured on the whole plan (`docs/renders/script-flow-2026-10-26/`), #1119
as merged -> flow (pro): hand-overs over 30 deg Bridge LC 5 -> 0 (0), hat
6 -> 3 (3), Tires 3 -> 1 (0), To a T 9 -> 4 (3); largest turn between
crosses 39 -> 31, 52 -> 34, 34 -> 27, 52 -> 44 deg. Cost: square-to-column
on Bridge 0.87 -> 0.80 LC, 0.84 -> 0.65 hat (pro 0.87 / 0.77; ~70 crosses
read, noisy); Tires 0.97, To a T 0.89 unchanged. Kinks unchanged (trace).

- **Smoothing the cross direction harder looks smoother and is WRONG on small
  script.** At 2 half-widths the crosses leaned off their own column round
  Bridge's bowls: square-to-column (script_census) hat 0.88 / 0.72 / 0.37 and
  LC 0.79 / 0.57 / 0.31 at 1 / 2 / 3 half-widths (pro 0.77 / 0.87); Tires and
  To a T barely move. A Gaussian lags any curve tighter than ~5 sigmas. The
  pro's crosses jump MORE than ours at any sigma (Bridge hat 39 over 15 deg):
  he turns them sharply where his letters turn. Judge flow by hand-overs and
  squareness, not by fewest jumps. A smoothing spline held to a pixel read the
  same as sigma 1; odd-reflection end padding did not help either.
- **Not built, measured (word alone, sigma 2):** pairing all arms at a 4-way junction
  by least total turn, plus joining two nodes a dropped stub apart (Tires' e
  loop meets its baseline 0.6 mm from where the baseline runs on, so the loop
  was its own stroke): Tires' e runs on, but Bridge LC left 6.7 -> 11.0 mm2
  to patches. Still showing in the 40 px/mm crops: the s's top (a cusp; the
  pro cuts there too) and its foot (one 65 deg hand-over).
- **The squareness reader is noisy on Bridge** (`script_census` read 0 to
  117 crosses between near-identical stitchings); trust a trend across a
  sweep, not one cell.
- Kinks left on Bridge are the trace's width wobble, not the path: the
  crosses change length 0.76 / 0.85 mm per mm, hat / LC (pro 0.19 / 0.22,
  our LC OFF 0.86); rails stay on the traced polygon as briefed. Tires:
  0.25 vs pro 0.30.
- With `script_strokes` ON, `monoline_script_satin` never sees a script word
  (the route returns first): Tires OFF = mono ON byte-identical, and ON =
  ON + mono byte-identical. Still reachable for monoline strokes the door
  refuses.

**Bridge's width: recorded, NOT built (Kent 2026-10-27: "Record it, no build
(Recommended)").** Bridge's letters still fuse where strokes crowd. Measured
on the word alone, strokes and stations as built, only where a cross ENDS
changed (scratch `widthrule.py`, `fusion.py`; numbers only):
- **The trace is not fatter than the art:** traced polygon 157 / 229 mm2
  against the drawn ink (half-max) 153 / 226, hat / LC. Our ~2.96 mm hat
  needle is the drawn width (station 2.16, the same at the polygon or the
  half-max edge) plus pull 0.4 a side. The pro re-set the word at 1.56 mm
  against the drawn 1.76.
- **Ending crosses at the drawn half-width (distance transform at the spine)
  does not separate the letters:** hat ribbons shared 10.9 -> 2.9 mm2 before
  pull, but 5 of 6 fused pairs stay fused and 24 mm2 more of the polygon
  goes uncovered (8.3 -> 32.2, nearly all on ink: patches). With the pull's
  footprint: 21.3 -> 9.9 mm2, 11 -> 10 pairs, uncovered 3.1 -> 8.0; LC
  15.8 -> 3.9, 7 -> 7 pairs, 7.8 -> 20.2. Capped at the pro's 1.56 needle:
  2.8 mm2, 6 pairs, 40.7 uncovered.
- So the fusion is drawn width + pull on letters drawn close. Only a satin
  NARROWER than the drawing (the pro's) separates them, and that is the
  satin width / pull floor: **gate 1**, a sew-out.
- Sewn overlap off the DSTs (share of column area two columns share): Bridge
  hat OFF 63.5% -> ON 28.3% -> flow 24.9% (pro 10.5%); LC 74.7 -> 25.9 ->
  18.5% (7.9%); Tires flow 6.8% (3.1%).
- **Tires sews SPLIT satin ON:** crosses ~4.33 + 2 x 0.4 = 5.13 mm, past
  `SPLIT_SATIN_ABOVE_MM` 5.0; `tools/satin_columns.py` reads 6.6% of its
  penetrations in columns (OFF's fill-in-a-border 26.4%, the pro's 3D puff
  file 94.1% at 4.16 mm, unsplit). The drawn-width end (4.93) would land
  under the ceiling; not built either. `test_satin_columns`' plan-reader
  control holds `script_strokes=False` for this.

Related: [[monoline-script-satin-2026-10-24]], [[bridge-border-and-script-2026-09-30]],
[[lettering-architecture-2026-10-07]], [[column-corner-folds-2026-10-23]].
