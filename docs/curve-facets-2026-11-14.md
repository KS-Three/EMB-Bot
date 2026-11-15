# Curve facets: Kent's 18 "smooth radiused edge" pins, traced to the stage that makes the chords (2026-11-14)

**Question (the Director, under Kent's "I want it exactly like the pros").**
Last night's trace (`docs/jag-source-2026-11-13.md`, (b)) put 18 of Kent's 49
smooth pins on clean curves written as chords. Find the stage that makes the
chords, measure ours against the pro's at the same place, fix it at that
stage behind a flag built OFF.

**Answer.**
- **The chords the satin follows on lettering are made by the Column lane, not
  by stage 4.** `outline_cut._letter_columns` re-simplifies every letter at
  max(0.12 mm, W/16) before it cuts it into stroke pieces. On and_pizza (W
  about 4 mm) that is 0.25 mm. A bowl reaches the rails as 2.0-2.6 mm chords
  turning 20-30 degrees, whatever stage 4 handed it. 15 of the 18 pins are
  lettering on this lane (and_pizza 14, dot_music 1).
- **Built:** `curve_chord_mm` (None = OFF). It splits each clean-curve edge of
  a lane piece's OUTER outline into 0.4 mm pieces along a tangent-continuous
  curve through the piece's own vertices. Built opt-in on top of it:
  `curve_chord_stage4` (OFF) does the same to stage 4's polygons.
- **What the lane flag bought: the rails, yes. The thread at the pins, not
  measurably.** The lane's rails go from p95 41.5 to 9 degrees a vertex. The
  satin's needle points at Kent's 15 lettering pins read the same OFF and ON:
  turn max better at 7, worse at 8, mean change -0.01 degrees. By eye some
  bowls are smoother (#7, #10, #16) and some are not.
- **What the stage-4 flag bought: Tires #0, clearly.** The satin tier's edge
  there stepped at a 3.1 mm chord. ON it is 0.37 mm chords, and the
  stitches' turn max goes 23.1 -> 8.1 degrees (std 9.6 -> 3.2, off-circle
  0.08 -> 0.02 mm, the pro's 0.05). By eye it is one even arc where OFF
  stepped. Gaulke #3 moves a little: turn max 9.5 -> 8.2, std 3.2 -> 2.6.
  Its 3.1 mm chord stays, because the guard refuses it.
- **Recommendation: neither flag is a flip on this evidence.** The lane
  flag does not move the thread measurably at the 15 lettering pins. The
  stage-4 flag cures Tires #0, but also moves the lane's cuts on lettering
  (the "p" of and_pizza). The facet Kent reads on the bowls is not the
  rail's chord alone: the satin's end placement jitters about 6 degrees an
  end (std) in both arms, where the pro's ends sit on a circle to his file's
  own 0.1 mm quantization. That is the next lever, in the satin emitter
  (`columns.py` stations), not in any polygon.

Instrument readings, not quality claims (ROADMAP gate 4). Every number is one
run on one laptop, n = 1 per design, on main 85abe7d0 (after #1515's flips).

## The 18 pins

and_pizza #5-#18 (Kent: "#6-#19 not a smooth radiused edge"), dot_music #2
("the shapes that have an arc or curve"), Gaulke #3 ("the circle edges should
be smooth"), Tires #0 ("jagged edges don't look clean"), Bridge #10 ("the
circle should be smooth, not jagged"). Indices are the sitting's list order,
so Kent's own numbers are one more. Pictures:
`digitizer/eye_pairs_out/facets-1114/sheets/` in the primary checkout
(gitignored): `art | OFF | ON | pro` per pin, with the polygon's turn, its
chord and the stitches' turn printed on each panel. The `control_*` sheets
show whole designs OFF | ON | changed pixels.

## 1. Ours against the pro at the pins

Tool: `python -m tools.curve_facets pins` (new). Ours is read from the plan's
runs in float mm. The design file is quantized to 0.1 mm, and at 0.4 mm end
spacing that alone reads as 14-18 degree turns: atan(1/4) and atan(1/3).
"Edge points" are the needle points within 0.3 mm of the thread's coverage
edge, ordered along it.

| where | polygon chord (median) | polygon turn a vertex | edge end spacing | per-end turn on that radius | ends off a fitted circle (RMS) |
|---|---|---|---|---|---|
| ours, and_pizza bowls (#5-#18), stage 4 | 0.76-1.35 mm | 7.5-11.9 deg (mean) | 0.40-0.42 mm | 2.8-6.2 deg | 0.014-0.036 mm |
| ours, and_pizza bowls, the lane's rails | 2.0-2.6 mm | 20-22 deg (p10, p13) | | | |
| ours, dot_music #2, the lane's rails | 1.35-1.44 mm | 25-30 deg | 0.42 mm | 7.9 deg | 0.034 mm |
| pro, Bridge #10 | (no polygon) | | 0.41 mm | 3.7 deg (r 6.3 mm) | 0.03 mm |
| pro, Gaulke #3 | (no polygon) | | 0.36 mm | 2.6 deg (r 7.9 mm) | 0.02 mm |

The pro sews one satin end every 0.36-0.41 mm on a curve. His ends sit on a
circle to 0.02-0.03 mm RMS, which is his file's quantization floor: 0.1 mm
steps give 0.029 mm RMS. That is what "on the curve" means in his file, and
it is why 0.4 mm is the flag's chord. Our ends are spaced the same, 0.40-0.42
mm. Our turns are not even: the mean per-end turn matches the radius, but the
max runs 11-20 degrees with a std of 5-7 degrees, in both arms.

and_pizza has no pro file (a Commons row). Tires' pro outline is a run at
0.14 mm. Gaulke #3 and Tires #0 are fill edges, not lane satin.

## 2. The stage that makes the chords

Tool: `python -m tools.curve_facets stages` traces stage 4 ring by ring and
re-runs the lane's simplify on every text-tagged region. "dev" is the largest
distance from the stage's input. "p95 turn" is the 95th percentile of a
curve's vertex turns (2-45 degrees at stage 4, 2-75 in the lane), the median
over rings.

| stage | and_pizza vertices / dev / p95 turn | dot_music | Gaulke |
|---|---|---|---|
| raw trace (sub-pixel) | 9131 | 7677 | 14129 |
| Douglas-Peucker at 0.2 mm | 158 / 0.198 mm / 35.5 deg | 131 / 0.197 / 38.5 | 635 / 0.200 / 38.3 |
| `curve_turn_deg` refinement | 322 / 0.174 / 18.1 | 279 / 0.078 / 24.0 | 2120 / 0.198 / 41.8 |
| **Column lane simplify, max(0.12, W/16)** | **73 / 0.246 / 41.5** | **116 / 0.170 / 46.6** | 610 / 0.120 / 45.7 |
| lane densify, `curve_chord_mm` 0.4, every ring | 305 / 0.068 / 9.0 | 408 / 0.111 / 12.3 | 1135 / 0.120 / 35.0 |
| stage-4 densify, `curve_chord_stage4` | 745 / 0.174 / 10.0 | 568 / 0.078 / 13.8 | 2454 / 0.198 / 37.6 |

The lane's simplify throws away what stage 4 refined and turns harder than
stage 4's raw Douglas-Peucker. It also leaves the outline 0.25 mm off the
traced letter, past stage 4's own 0.2 mm tolerance. Stage 4's chords never
reach a lettering rail. That is why last night's `outline_redraw_native`, and
this session's first build at stage 4, changed the polygon and not the satin
on the bowls (`sheets_v0`, scratch: the p10 stitches were identical OFF/ON).

Gaulke's lane rows are its words. Its pin #3 is the circle's FILL edge,
untouched by the lane. There stage 4 is the stage: under 20 px/mm the
refinement's resolution gate splits no chord the sub-pixel read did not
accept, and the binary art accepts none, so the edge keeps a 3.1 mm chord.

The lane's construction does not need the coarse simplify for its RAILS. It
needs it for its CUTS (`corners`, `find_cuts` read turn angles). So the fix
keeps the cuts on the simplified letter and refines only the rails.

## 3. The fix (`curve_densify.py`, both flags OFF)

`densify_curves(ring, trace, chord, guard)`:
- An edge bends when both ends turn the same way, each at least 2 degrees and
  neither a corner (over 45 degrees at stage 4, 75 in the lane, or a spike
  2.5 times both neighbours). An edge with one end a corner also bends: a
  bowl's first chord off its stem.
- Its new vertices lie on a cubic Hermite through the two end vertices. The
  tangent at an end is the bisector where the next edge bends too, the
  neighbour's own direction where that edge is straight, and the chord
  itself at a corner. Each piece is at most `chord` long.
- Every existing vertex stays exactly where it was. An edge whose new points
  do not ALL lie within `guard` of the trace keeps its chord. A result that
  turns a valid ring invalid is refused.
- Nothing is smoothed and nothing reads a raster. It is not DOCTRINE's
  "smoothing region polygons" negative, which blurred polygons by a radius.

**`curve_chord_mm` (the Column lane).** `outline_cut.build_column`
densifies each piece just before its rails are built, so the cuts and the
pieces are today's. The guard is half the lane's simplify tolerance, at most
0.08 mm, measured against the letter's OUTER outline as it came in. Cut lines
run inside the letter and stay straight. **Counters stay too.** The first
build densified counters as well, and stage 7's counter clearance re-cut the
"p" of and_pizza around the finer counter edge into a wedge, and half-filled
the "a"'s counter (crop sheets, scratch). With the trace on the outer outline
only, the "p" sews 2 columns and 1 cut in both arms (301 -> 303 stitches).

**`curve_chord_stage4` (stage 4, needs `curve_chord_mm`).** Runs after the
refinement, on the rings the refinement may touch, with the guard at one grid
pixel against the raw trace. It declines an UPSCALED source, where
`outline_redraw_k` (0.75 since #1515) redraws the rings as lines and arcs
after stage 4. So the two never refit the same edge, and the redraw's
functions are untouched. It also moves the lane's simplify (Douglas-Peucker
picks different vertices from a denser ring) and so its cuts. On and_pizza
the "&" sewed cleaner and the "p" opened a cut at its bowl, the same
unpredictable answer `outline_redraw_native` got. That is why it is a
separate flag.

No physical constant (ROADMAP gate 1). 0.4 mm is a polygon resolution read
off the pro's own end spacing, and the guards are raster or simplify
quantities.

## 4. Against `outline_redraw_k`

The two do not fight.
- The stage-4 site skips an upscaled source, the redraw's whole regime.
- The lane site runs at plan time, on whatever polygon stage 4 and the
  redraw left. On an upscaled letter the lane's own simplify re-coarsens the
  redraw's arcs (the same 41-degree problem as above), and the densify then
  refines the rails back toward them. Both point the same way.
- Bridge (x1.8, both flags) is NOT byte-identical: 8469 -> 8462 stitches,
  1687 px changed, all on its lettering through the lane. Its pin #10 (the
  wheel's ring) is unchanged.
- The flips worker's redraw functions are not touched.

## 5. Cost, and what moved

`curve_chord_mm` 0.4 alone (the lane), OFF on main against ON, one capture
each (`tools.jag_strips capture`, the service's call sequence). Seconds are
the whole digitize on a laptop shared with about ten other sessions: noise
of x2-x3 either way, NOT a runtime finding.

| design | stitches OFF -> ON | md5 | changed px (12 px/mm) | s OFF / ON |
|---|---|---|---|---|
| and_pizza | 2440 -> 2222 | moved | 1079 | 178 / 192 |
| dot_music | 1517 -> 1563 | moved | 3211 | 98 / 64 |
| n_sync | 2470 -> 2466 | moved | 26613 (the S and C) | 19 / 71 |
| k_line | 3381 -> 3381 | moved | 2553 | 42 / 86 |
| ProSeal | 5608 -> 5629 | moved | 2757 | 79 / 70 |
| Gaulke | 7413 -> 7428 | moved (its words) | 6209 | 42 / 162 |
| Tires | 4544 -> 4544 | **same** | 0 | 15 / 22 |
| Bridge (both flags) | 8469 -> 8462 | moved (its letters) | 1687 | 83 / 44 |

Both flags on (`curve_chord_stage4`), from a capture made before the lane's
trace moved to the outer outline, so read these as the stage-4 site's
direction only: and_pizza 2454 -> 2063, Tires 4552 -> 4510, Gaulke 7494 ->
7520 and ProSeal 5707 -> 5721 (`tools.jag_strips` counts, not plan points).
Stage 4's own vertices rise 413 -> 836 (and_pizza), 325 -> 614 (dot_music)
and 2223 -> 2557 (Gaulke).

- **and_pizza -218 is the "a" alone (471 -> 297 plan points).** It is not
  broken. OFF sews the "a" as SPLIT satin (crosses about 2.1 mm), because one
  over-long cross at the bowl-stem junction trips the column-wide split
  comb. ON the densified rail has no such cross, and the "a" sews as one
  column (crosses about 3.5 mm), like the word's other letters. Replayed in
  isolation with stage 7's exact arguments: same 2 cuts and 115 stations in
  both arms; satin 467 -> 293 points. ON also opens a small notch where the
  bowl meets the stem at the counter. Kent's eye should see it.
- n_sync's S and C (all curve) re-sew with a different cross pattern.
- k_line, ProSeal and Gaulke move a few letters by a handful of stitches.
- Tires: no lettering on the lane, byte-identical.

## Not fixed, and where it goes next

- **The satin's end jitter, in both arms.** At 0.4 mm end spacing on a
  4-5 mm radius the even per-end turn is 5-6 degrees. Ours runs 3.5 degrees
  mean, 6 degrees std and 11-20 degrees max, with the rails faceted or not.
  The stations are pitched along whichever rail moves
  (`_letter_columns`'s `pitch_mm`), so on a bowl the outer rail's ends land
  unevenly. A station sampler that spaces the OUTER rail's ends evenly on a
  curve is the next lever for these 15 pins. It is the satin emitter's, not
  the polygon's.
- **Counters (Kent's #21/#22, "these circles should be round").** The lane
  writes a 1.2 mm counter as a 7-gon (51-degree turns), visible in Kent's
  render. That is this same simplify, not the rail wobble the jag-source
  tally filed it under. Densifying it breaks the counter clearance (above),
  so it needs that clearance to read the letter's own counter, not the
  piece's.
- Gaulke #3 is a fill edge at a stage-4 chord. Only `curve_chord_stage4`
  reaches it, and only a little: its 3.1 mm chord is refused by the
  one-pixel guard against a binary staircase trace.
- Tires #0 is cured by `curve_chord_stage4`. A stage-4 site that reaches
  only non-lettering shapes would make that flag safe. It needs the text
  tags, which are only known after vectorize: a post-pass in `pipeline`
  beside the redraw, on untagged regions.
- Bridge #10 is upscaled and belongs to `outline_redraw_k`.
