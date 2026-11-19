# RESULT 2026-11-19: `lettering_columns_hairline_leave` built OFF, measured, NOT clearly better, left OFF

`cfg.extra["lettering_columns_hairline_leave"]`, `digitizer_core/hairline_leave.py`, applied to the
columns after `wedge_cap` in `script_strokes_shape`. It is a station-level fix, not a change inside
`pen_strokes`: reading the stations showed the "ride along the stem" is a shallow diagonal crossing
(hat col 3 stations 32-44, mid (0.4,5.9) -> (4.2,3.6), stem col 5 at x 1.8-2.6) where the skeleton
runs through the merged blob, so the hairline's crosses there are 2.1 mm long (its own 0.6-0.8) and
at 63-72 deg against the stem's 16. A column whose stations pass through a HEAVIER column's ribbon
(median cross >= 1.4x its own) now leaves at the last thin station before the merge: the blob run is
replaced by the straight line to the first thin station after it, cross length and angle eased between
the two, each cross clipped to the art. Column ends are never touched.

Turned overlap (mm2 at crosses > 30 deg apart; `tools.script_flow`'s pairing, columns after `wedge_cap`
and the flag), same method as above:

| | h arch x stem (3 x 5) | whole word |
|---|---|---|
| hat OFF -> ON | 5.95 -> 0 | 19.25 -> 12.73 |
| toat_machine_beanie OFF -> ON | 7.58 -> 0 | 15.49 -> 7.91 |
| toat_beanie | 1.38 -> 1.38 (byte-identical) | 8.96 -> 8.96 |
| bridge_hat, bridge_lc, tires_hat_3d | byte-identical, every pair unchanged | |

Caution on the 0: the eased cross angle is the hairline's own (about 44 deg) against the stem's 16, a
28 deg turn, just under the 30 deg line, so part of the drop is the line, not only the area. The
pro's 1.95 is the target; the stations did stop lying wide over the stem.

Cost: hat 17,100 -> 17,158 stitches, trims 18 -> 19, jumps 45 -> 46 (WORSE by one each), needle-up
267.9 -> 264.7 mm; beanie 16,862 -> 16,861, trims, jumps unchanged. The 3 x 6 pair (hat 3.56, beanie 2.70)
and the i-n-e column's e crossbar are not reached.

**Print size: not clearly better.** `docs/renders/hairline-leave-2026-11-19/` (ORIGINAL | BEFORE | AFTER,
and an h close-up, OFF left, ON right): at print size the word is indistinguishable ON and OFF, and
even in the close-up the h junction differs by a few stitches. With one trim and one jump more on the
hat, **left OFF, no flip recommended.** The 44-run flag sweep was not run (about 90 minutes, flag stays
OFF); Bridge and Tires were checked by column measurement and stitch counts only. Tests:
`tests/test_hairline_leave.py`.

---

# NEXT THING TO TRY: the h's hairline route (superseded above for the hairline; the rest stands)

Both flags built here stay OFF and neither is a flip candidate (marginal at print size; `junction_align`
also raises the hat's `coverage_max` 7.19 -> 7.68). The valuable finding is where the real pile-up is:

- **Toat Machine hat, "h":** the arch hairline (column 3 of the word, 63 stations, after `wedge_cap`,
  columns sorted left to right by `script_strokes._left_key`) runs ALONG the stem (column 5, 61
  stations) for 11 stations: hairline stations 32-43 lie over stem stations 13-22, **5.95 mm2** at
  crosses more than 30 degrees apart. The pro's equivalent pair (its h stem x the arch column) overlaps
  **1.95 mm2**. It is a through-run, so no turn or cut at a column END reaches it.
- **Where the route is chosen:** `digitizer_core/script_strokes.py`, `pen_strokes` (welds the
  skeleton's arms at a junction by straightest pair, `WELD_MAX_DEG`) reading the medial axis in
  `_skeleton` (`_cluster_junctions`, `_prune_spurs`), then `_split_cusps` and `_stations`. The merged
  ink at the h's junction pulls the skeleton down the stem's centre before it peels off; the fix is the
  route (leave the stem at the first station past the merge, or weld at a different arm pair), not the
  cross angle. Reader: the hat's capped columns via `script_strokes_shape` (`/tmp`-style capture of
  `wedge_cap.cap_columns`' return is how the stations above were read).
- Judge any route change on To a T, Bridge and Tires whole words at print size, then
  `python -m tools.flag_sweep` (44 runs); a route change moves column stations everywhere.

---

# Toat "Machine" script: what the plan shows, and a flag that does not clear it (2026-11-18)

**Verdict: the faults are real in the stitches. One cause is built as
`lettering_columns_end_overlap_cut` (OFF) and is NOT clearly better at print size, so no flip is
recommended. The larger causes (U-turn fans, joined i-n-e column) need a different build.**

Faults: scorecard 2026-11-18, `L_toat_beanie` (c, h, e tangle; M lumps) and `L_toat_machine_hat`
(lumps and crossovers at letter joins; the h's top cap). Reproduced at the Studio request on
`main`: beanie 82.3 mm, 17,258 stitches; hat 89.5 mm, 17,153 stitches.

## The plan, read (word columns after `wedge_cap`; stations in design mm)

Beanie: 13 columns for "achine". Hat: 11. No column turns its cross by more than 30 degrees between
neighbouring stations (max over all columns: none), so the "direction changes mid-stroke" are not a
station-to-station jump. Three things are real:

1. **Column ends lying across another stroke at a turned cross** (pile-ups, crosshatch). Overlap
   of sewn station quads at cross angles over 30 degrees, mm2 (beanie / hat): c terminal on its arc
   (cols 2 x 4) 1.21 / 2.18; h arch hairline on the stem (3 x 5) 2.52 / 6.10; i entry (9 x 10 beanie)
   2.71; a bowl (0 x 1) 0.99 / 2.17; n entry (7 x 9) 0.88; hat 3 x 6 3.60, 6 x 7 2.05, 7 x 8 2.31.
   `script_columns`' cut-back tests only a station's MIDDLE, so a straddling station stays.
2. **Radial fans at every U-turn** (bottoms of c, h, i, n, e: beanie cols 3, 9, 10, 11; hat 3, 6, 7, 9).
   The pen turns 180 degrees inside a stroke whose inner rail has no radius, so the crosses fan from
   a point. Each step is under 30 degrees; the fan is the turn. This is the grader's "radial pinch".
3. **One 128-station column sews i-n-e's joined stroke** (beanie col 11, hat col 9): the n's
   arch, the e's entry and the crossbar crossover are one pen path, so the e's crossbar and left
   side stack (the e's pile-up) inside one column, not between two.

## What was built (OFF): `cfg.extra["lettering_columns_end_overlap_cut"]`, `end_overlap.py`

A column yields end stations to a LONGER column: from an end inward a station goes while at least
0.6 of its quad lies over longer columns' quads at a cross turned more than 30 degrees (at most 6
an end, the column keeps 6). 0.3 was tried first: it cut more, the patch lane re-covered the
cut ground with straight patches, and the h arch got messier; 0.6 and 0.8 cut the same stations.

| | stitches | trims | jumps | needle-up mm |
|---|---|---|---|---|
| beanie OFF -> ON | 17,258 -> 17,119 | 27 -> 27 | 35 -> 35 | 233.6 -> 255.5 |
| hat OFF -> ON | 17,153 -> 17,147 | 19 -> 19 | 32 -> 32 | 267.9 -> 267.9 |

Preflight grade B -> B on both; `coverage_p95` 6.04 -> 5.95 (beanie), 4.89 -> 4.88 (hat).
Pictures, ORIGINAL | BEFORE | AFTER, whole design and the word:
`docs/renders/end-overlap-2026-11-18/`. At print size the hat is indistinguishable; on the beanie
the c terminal and the i-n join are a little tidier, and the h arch, the e crossbar and every
U-turn fan are unchanged. **Not clearly better, so left OFF.** Beanie needle-up grows 22 mm.

## Not done, and why

- The 18-job tripwire + 26-fixture sweep was NOT run: with no flip recommended it would cost about
  40 minutes for a flag that stays OFF. Run it before any flip question. Bare-artwork, cover and
  Becker 114 mm / MFab 30 mm checks are likewise open.
- U-turn fans (2) and the joined i-n-e column (3) are the larger causes. A fan fix means splitting
  the column at the turn (a new column per leg, as the pro's `i` and `e`) or capping the inner
  rail's radius; neither is built. The h's top cap (hat) is in neither list: it is the wedge-cap
  note's separate fault.
- The speed lines are closed as a thread limit, per the brief.

## Addendum: causes 2 and 3 against the professional's file (numbers only; nothing of the pro's committed)

Read from the pro's `Machine beanie.PES` (in `Embroidery Files.zip`), cross chains by
`tools.script_flow.columns_of`, block 2. No render and no stitch data of it is committed.

- **U-turn fans (cause 2) are not a departure from the pro.** Fastest 60-degree rotation of the cross
  in a column, stations and mid-path arc: ours beanie 4-7 stations over 1.3-2.2 mm (cols 11, 2, 9, 10,
  3, 12), hat 4-7 over 1.1-2.4 mm; the pro's long columns 3-11 stations over 0.8-2.0 mm. The pro keeps
  ONE column through a hairpin: col 71 (122 crosses) turns its cross 29 -> 176 degrees over 56 crosses,
  col 79 (197 crosses) 148 -> 11 degrees, cross length 1.5-3.0 mm and never pinched. Same rotation
  rate, same one-column construction. The scorecard marks the fans at nitpick level on the hat; my
  "biggest visible fault" above was wrong. **No split or inner-rail cap was built: the measurement does
  not support one.**
- **Long joined columns (cause 3) are the pro's construction too.** The word's pro columns run 122, 143
  and 197 crosses; ours are MORE split (13 columns for "achine" against roughly 8 pro columns).
  Splitting further is the wrong direction; the e's crossbar pile-up is a crossing, not a column count.
- What is left that the pro does not show: the end-on-stroke overlaps (cause 1, built OFF above, only
  marginal) and the h arch / e crossbar crossings, which need a per-crossing rule (which stroke sews
  last, the other stops at its edge), not a turn rule. Not started.

## Addendum 2: what the pro does AT the crossings, and `lettering_columns_junction_align` (OFF, not recommended)

Same file, same method (numbers only). Overlap of the word's sewn columns, total and the part at crosses
more than 30 degrees apart: pro 11.9 and **1.55 mm2**; ours beanie 14.8 and **9.5**, hat 19.8 and **19.2**.
The pro overlaps as much as we do, but a joining stroke's last crosses are turned to the through
stroke's angle (its overlap pairs 57x61, 62x64, 62x71, 79x82 are all at 0 turned mm2); nobody stops at an
edge and nobody double-covers at a turned angle. So our turned overlap IS a departure, and the fix the
measurement supports is a TURN, not the cut built first.

Built (OFF, `cfg.extra["lettering_columns_junction_align"]`, `end_overlap.align_columns`): the end
stations of a stroke that ENDS on another's body (the longer column wholly; a shorter one along its body
only, as the h's hairline ends in the stem) rotate about their middle, length kept and clipped to the
art, to that column's cross angle, easing in over 4 stations. On the plan: turned-cross overlap beanie
8.96 -> 4.45 mm2 (19 stations turned), hat 19.25 -> 15.87 (14). Stitches beanie 17,258 -> 17,134, hat 17,153
-> 17,153; trims, jumps unchanged; needle-up beanie +26.6 mm; hat `coverage_max` 7.19 -> 7.68 (WORSE),
beanie `coverage_p95` 6.04 -> 5.97. Pictures (OFF over ON, the word):
`docs/renders/end-overlap-2026-11-18/*junction_align*`. By eye at print size the hat's h junction is a
touch smoother and the beanie is hardly changed: **not clearly better, left OFF, no sweep run** (about 90
minutes for a flag nobody should flip).

What is left, and why a turn does not reach it: the hat's 5.95 mm2 (cols 3 x 5) is the h's hairline
running ALONG the stem's body for 11 stations (hairline stations 32-43 over stem stations 13-22), a
through-run neither end of which is a junction. The pro's equivalent pair (57 x 103) overlaps 1.95 mm2.
That is the skeleton routing the hairline down the merged ink (the wedge cap's ground), so the fix is in
the route (leave the stem at the first station past the merge), not in the cross angle.
