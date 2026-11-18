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
