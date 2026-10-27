---
name: script-strokes-2026-10-26
description: Kent "Measure, then build OFF" — a script word (Bridge, Tires "ires", To a T "achine") sewn one satin column per pen stroke, path read on the art's INK; `script_strokes` OFF; Bridge is trace-limited (fused, counters closed, ground knocked out) and the pro re-set it
metadata:
  type: project
---

L7b, 2026-10-26, lane `claude/script-strokes-b22fb4`. Module
`digitizer_core/script_strokes.py`; flag `script_strokes` (OFF); reader
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

Related: [[monoline-script-satin-2026-10-24]], [[bridge-border-and-script-2026-09-30]],
[[lettering-architecture-2026-10-07]], [[column-corner-folds-2026-10-23]].
