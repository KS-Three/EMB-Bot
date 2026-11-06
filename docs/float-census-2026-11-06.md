# Float census: what a needle-up move is, and what `cut_every_jump` makes of each one (2026-11-06)

MASTER_SCOPE defect 4, on main `5777f91c`. `docs/trim-defects-4-6-2026-10-29.md`
found we cut at the pro's rate (391 vs 409 over 17 jobs) while our needle-up
moves were 2.07x his (879 vs 425): 488 short floats left uncut against his
16. That ratio counts every needle-up move as a break, and whether a
needle-DOWN walk on sewn thread -- what `cut_every_jump` (OFF) makes of most
floats on a field, and the pro's own habit letter to letter -- is a break was
unmeasured. This page builds the instrument, measures what a fresh clone can
measure, and closes the one known fidelity hole in the sewn hop. **Nothing
here flips a flag or moves a constant.** `trim_at_mm`, the bury budget and
jumps-per-trim are cloth's (ROADMAP gate 1); the flip is Kent's (gate 3).

## The instrument: `digitizer/tools/float_census.py`

One reader on both DSTs (`dst_moves`), reusing `tools/sequence_pro`,
`tools/trim_classes`, `tools/between_walks` and `tools/jump_walk_oracle`:

- every move between two penetrations of one colour block is **cut** (a TRIM
  on the way), **uncut** (needle-up, no TRIM: a float someone snips) or
  **walked** (needle-down from one piece to another, `between_walks`' step);
  the block's opening lift is a colour change and is not counted;
- an uncut move longer than a DST record can hold (12.1 mm,
  `machine.MAX_STITCH_MM`) is reported as **long-stitch**: how the writer
  encodes a needle-DOWN stitch over that length (pystitch's long-stitch
  contingency: jump records, then the needle). The machine flies it with the
  thread uncut all the same, so it is a float on the cloth, but no jump pass
  can see it: to the plan it is a stitch. `plan_long_segments` says which runs
  they come from.

The replay (`replay`, ours only): `cut_every_jump` ON on the same plan pickle,
with the engine's own `_cut_or_bury_jumps` recorded through its
`_later_thread_burier` calls, no second copy of the rule. Per float: length,
the engine's outcome (**buried** under later thread, **walked** on thread
already sewn, **cut** on bare cloth) and what its straight thread **lies on**,
read with the pass's own samples against the plan's thread as it stood: the
same colour, the white field (`sew_enclosed_white`'s block), another colour,
or bare. Stage 7 runs `sequence` once more on a trial sub-layout inside a
Column-lane plan (the OFF-rank pass) and the beanie knockdown runs the pass
again, so the rows kept are the ones whose run the finished plan sews.

Three break definitions, per file and pooled (`breaks`):

- **A** cut + uncut: every needle-up move, as the 10-29 doc counted;
- **B** cut: a float is not a break;
- **C** cut + uncut not walked: a float the replay would WALK on sewn thread
  is not a break. For OFF that is its floats minus the ones ON walks; for ON
  and for the pro every uncut move is still needle-up, so C = A there.

Gate 3 instruments ride along: `travel_cover` exposed mm (TRAVEL runs only,
so a 2 mm walk sewn as one stitch is not in it: the oracle's `walked_mm` is
the thread a walk lays on the work) and `flip_sheet_renders.bare_by_band` at
0.20 mm (an uncut float's thread counts as on the cloth there, which is why
it falls when floats are cut). CPU is `process_time` round `plan_stitches`
and round the pass.

    cd digitizer
    .venv/bin/python -m tools.float_census gen       # stages 0-4 once per job (pickled)
    .venv/bin/python -m tools.float_census arms      # OFF | ON | ON+fine off the pickle
    .venv/bin/python -m tools.float_census report --md out.md
    .venv/bin/python -m tools.float_census dst FILE.DST ...   # any machine file's moves

Tests: `tests/test_float_census.py` (the classifier on a hand-built DST and
on the committed Becker hat, the replay on a synthetic plan with one float
of each outcome and each lies-on class, the trial-pass filter, the
definitions' arithmetic).

## What a fresh clone can measure

The 17 pairs of the 10-29 doc are the client's Embroidery Files, gitignored.
A cloud checkout has the five Becker pro DSTs under
`digitizer/testdata/reference/becker_*` and the one Becker logo, and no
other pair. **The other 12 pairs are n/a here, not estimated:** becker_beanie,
gaulke_roofing_lc, hotel_fremont_patch, mfab_hat, mfab_lc, tires_hat_3d,
bridge_hat, bridge_lc, proseal_hat, proseal_beanie, and the pro sides of
gaulke_roofing_hat and precision_drone. Kent's machine has them all: the
same three commands there give the 17-job table.

Two of the five Becker pro files, `beckers logo hat` and `beckers logo hat
Smaller`, are the same job to us (101.9 mm, hat front, one logo): our plan is
byte-identical for both, so the pooled table counts our side of that job
twice. Three committed artworks with no pro file (Gaulke roofing hat at 114.2,
Hotel Fremont hat at 92.5, Precision Drone at 62.6: card v8's widths) are run
for the replay and the oracle alone.

## Becker-5, OFF vs `cut_every_jump` ON vs the pro

Cuts, uncut floats and walked moves are the DST reader's, both sides. ON and
ON+fine are byte-identical on every Becker job (the fine step changes
nothing where the thread is whole).

| job | side | cuts | uncut | of them long-stitch | walked (DST) | A cut+uncut | B cut | C cut+uncut not walked |
|---|---|---|---|---|---|---|---|---|
| becker_hat_large | pro | 9 | 0 | 0 | 0 | 9 | 9 | 9 |
|  | off | 11 | 2 | 2 | 0 | 13 | 11 | 13 |
|  | on | 11 | 2 | 2 | 0 | 13 | 11 | 13 |
| becker_lc_large | pro | 11 | 0 | 0 | 0 | 11 | 11 | 11 |
|  | off | 14 | 2 | 2 | 0 | 16 | 14 | 16 |
|  | on | 14 | 2 | 2 | 0 | 16 | 14 | 16 |
| becker_hat_small | pro | 10 | 0 | 0 | 0 | 10 | 10 | 10 |
|  | off | 11 | 4 | 1 | 0 | 15 | 11 | 14 |
|  | on | 13 | 1 | 1 | 0 | 14 | 13 | 14 |
| becker_chest_small | pro | 11 | 0 | 0 | 0 | 11 | 11 | 11 |
|  | off | 11 | 4 | 1 | 0 | 15 | 11 | 14 |
|  | on | 13 | 1 | 1 | 0 | 14 | 13 | 14 |
| becker_hat_smaller | pro | 10 | 0 | 0 | 0 | 10 | 10 | 10 |
|  | off | 11 | 2 | 2 | 0 | 13 | 11 | 13 |
|  | on | 11 | 2 | 2 | 0 | 13 | 11 | 13 |
| **pooled (5 jobs)** | pro | 51 | 0 | 0 | 0 | 51 | 51 | 51 |
|  | off | 58 | 14 | 8 | 0 | 72 | 58 | 70 |
|  | on | 62 | 8 | 8 | 0 | 70 | 62 | 70 |

| ours, pooled | A / pro A | B / pro B | C / pro A |
|---|---|---|---|
| off | 1.41x | 1.14x | 1.37x |
| on | 1.37x | 1.22x | 1.37x |

Reading it:

- **The pro cuts every needle-up move on Becker** (0 uncut, 0 walked between
  pieces, in all five files), as he did on 16 of the 17 jobs in the 10-29
  count. His 51 cuts are 42 between pieces and 9 inside one.
- **On Becker the needle-up gap is 1.41x, not 2.07x**, and it is not a
  float gap: **8 of our 14 "uncut" moves are long-stitch encodings**, one
  underlay segment of 13.8-16.7 mm and one fill segment of 34.4-37.5 mm
  inside the same shape on each job (`S92f2350b` on the hat, `Sd86ce3cb` on
  the LC, `S118e45fc` at 76.5 mm). `split_long_moves` is applied at the
  stage 6 construction sites that call it, and these runs did not pass
  through one. Stage 6's fill is another lane's today; this page only
  names them. They are counted as breaks in A and C above because the 10-29
  reader counted them too (so some of its 488 are these), and because the
  machine does fly them.
- **The six true floats** are 2.1-3.0 mm hops in the two 76.5 mm jobs. ON
  walks one per job (2.18 mm, on the white field, 14% of its thread on the
  field: `lies_on` white) and cuts two per job (2.7-3.0 mm, 57% of their
  thread on bare cloth). So C moves OFF from 72 to 70: on Becker a walk is
  almost never the answer, and the 2.07x -> "when a walk is not a break"
  question is a Fremont question (below), not a Becker one.
- **ON costs +4 cuts (58 -> 62) and buys 8 mm of bare thread**: 4.61 -> 0.82
  and 4.82 -> 0.72 mm at 0.20 on the two small jobs, the uncut floats'
  thread on the cloth. Exposed travel is unchanged on every job (no travel
  run is added: the walked hops are single stitches).
- **Where we cut more than the pro** (58 vs 51 OFF, 62 vs 51 ON) the excess
  is inside one piece: ours 2-5 in-piece cuts per job (17 pooled) against
  his 1-2 (9); the 10-29 doc's defect 6.

## The replay, job by job, with the oracle

| job | arm | floats | buried | walked | cut | on same colour | on white field | on other colour | bare | bare mm @0.20 | pass CPU s | oracle sewn-hop segs | off thread | worst mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large (= hat_smaller) | on / on+fine | 0 | | | | | | | | 0.1 | 0.01 | 0 | 0 | 0 |
| becker_lc_large | on / on+fine | 0 | | | | | | | | 0.4 | 0.01 | 0 | 0 | 0 |
| becker_hat_small | on / on+fine | 3 | 0 | 1 | 2 | 0 | 1 | 0 | 2 | 4.61 -> 0.82 | 0.01 / 0.03 | 2 | 0 | 0 |
| becker_chest_small | on / on+fine | 3 | 0 | 1 | 2 | 0 | 1 | 0 | 2 | 4.82 -> 0.72 | 0.01 / 0.03 | 2 | 0 | 0 |
| gaulke_roofing_hat (no pro) | on / on+fine | 23 | 0 | 0 | 23 | 2 | 0 | 0 | 21 | 7.33 -> 0.0 | 0.03 / 0.08 | 0 | 0 | 0 |
| hotel_fremont_hat (no pro) | on / on+fine | 148 | 5 | 143 | 0 | 5 | 143 | 0 | 0 | 0.0 | 1.09 / 4.25 | 154 | 0 | 0 |
| precision_drone (no pro) | on | 28 | 10 | 9 | 9 | 13 | 0 | 8 | 7 | 2.54 -> 0.21 | 0.11 | 21 | **1** | **0.0292** |
|  | on+fine | 28 | **9** | 9 | **10** | 13 | 0 | 8 | 7 | 2.54 -> 0.21 | 0.33 | 20 | **0** | **0** |

- **Fremont is card v8 to the stitch**: 148 floats, 143 walked on the white
  field and 5 buried, none cut, cuts 25 -> 25; the oracle's 154 sewn-hop
  segments, 170.7 mm, all on thread (`sewout-card-v8-2026-11-01` read 154
  and 170.7 mm). This is the job where "is a walk a break" decides the
  ratio: under A Fremont's 148 floats are 148 breaks OFF; under C they are
  5 (the buried ones ON would hide), and ON leaves 0 uncut and lays 171 mm
  of thread on top of its own white field instead.
- **Gaulke is the other answer**: 23 floats, 21 of them with thread on bare
  cloth (2 lie on the same colour but a thread edge leaves it), all 23 cut,
  bare thread 7.33 -> 0.0 mm. Where a float has no field under it the flag
  is +23 cuts, as `test_cut_every_jump`'s fixture has said since 10-21.
- **Drone** is the oracle's known case: of its 28 floats, 13 lie on the same
  colour, 8 on another colour, 7 on bare cloth; ON buries 10, walks 9, cuts
  9. The one 0.0292 mm stitch is below.

## The fidelity hole: `cfg.extra["bury_step_fine"]` (built OFF)

Card v8's oracle found one Python sewn hop on Drone 0.029 mm past the
thread's edge, and named the cure: `_BURY_STEP_MM` 0.1 -> 0.01, a sampling
step and not a physical constant. Built here as `cfg.extra["bury_step_fine"]`
(default OFF): `_cut_or_bury_jumps` samples a hop's thread every 0.01 mm
(`_BURY_STEP_FINE_MM`) instead of 0.1, for the hop it buries under later
thread and the hop it walks on sewn thread alike. Both call sites read it
from `cut_every_jump_step_mm(cfg)` (stage 7's art blocks and the beanie
knockdown's in `pipeline`). **`trim_bury_under_later`'s own pass keeps
0.1**, as does the bury path's reach pre-check.

- **Why both halves and not the walk alone.** The brief scoped the fine
  step to the walk judgment. Mapping the oracle's Drone stitch back to the
  plan (its DST record to the plan's command, same index) put it in the hop
  into run 657 of block 8 (0.517 mm, a bean-run loop to the next loop),
  which the pass **buried**: `bury(k)` accepted it at 0.1 (worst sample
  0.0063 mm inside the later thread) and refuses it at 0.01 (0.0189 mm
  past). The walk half never saw that hop, so a walk-only step left the
  oracle's verdict unchanged (measured: 1 off thread, 0.0292 mm, with the
  walk at 0.01). The oracle calls every fresh needle-down segment a walk,
  buried or not, so the done-test ("0 walk stitches off thread") needs the
  step on the bury half of this pass too. `trim_bury_under_later` is a
  separate pass and was never in the brief's scope; it is untouched.
- **Done-test, the committed fixtures, flag ON:** 0 off-thread sewn hops on
  all eight jobs (the five Becker, Gaulke, Fremont, Drone). Drone goes from
  1 off thread at 0.0292 mm to 0: the hop is cut instead of buried (buried
  10 -> 9, cut 9 -> 10, DST cuts 95 -> 96). Nothing else moves on any job: ON
  and ON+fine DSTs are byte-identical on the five Becker, Gaulke and
  Fremont.
- **OFF is byte-identical to main.** The five Becker OFF DSTs planned off
  the same pickles with main's `digitizer_core` (a detached worktree of
  `5777f91c`) and with this branch have the same md5 on every job
  (`4a5679f0`, `347cb1f2`, `b41b9f72`, `bcd45933`, `4a5679f0`). With
  `cut_every_jump` off the flag is never read (`test_bury_step_fine`).
- **Stage 7 CPU.** The pass itself, 0.1 -> 0.01: Becker 0.01 -> 0.01-0.03 s,
  Gaulke 0.03 -> 0.08, Drone 0.11 -> 0.33, **Fremont 1.09 -> 4.25 s** (148
  hops, each sampled ten times finer). On a Column-lane design the pass runs
  twice (the OFF-rank trial plan and the real one), so Fremont's whole
  `plan_stitches` went 9.4 -> 16.6 s. Everywhere else the plan's CPU moves
  inside its own noise.
- **Regression:** `tests/test_bury_step_fine.py`. The blind spot built by
  hand: fill rows 0.42 mm apart leave 0.02 mm gaps along a 2 mm hop's edge
  that fall between the 0.1 mm samples (0.02 mm clear of each) and under the
  0.01 mm ones (0.01 mm past). The coarse step walks it, the fine step cuts
  it; `jump_walk_oracle` reads the coarse walk 0.05 mm off thread from the
  DST bytes and the fine arm clean; the pass's bury half takes the fine step
  while `_bury_trims_under_later` buries the same hop regardless; rows 0.4
  mm apart (no gap) walk at either step; the flag reaches the pass only with
  `cut_every_jump` on.

## What this does and does not say about the flip

- The 2.07x was never a Becker number and is not a float number on Becker:
  the Becker gap is 1.41x needle-up, 1.14x cuts, and most of its floats are
  stage 6 long stitches. On Fremont-type jobs (small lettering on a white
  field) the whole gap is walkable floats and ON walks them; on Gaulke-type
  jobs (letters on bare cloth) ON cuts them all. A 17-job C/A table needs
  Kent's machine: `gen`, `arms`, `report` there.
- `cut_every_jump`'s flip still waits on card v8's sew-out (Kent 2026-10-21,
  blocks F, E, J): the question the card asks, whether 171 mm of thread
  walked on top of Fremont's field reads as a float or as the pro's habit,
  is one only cloth answers. Nothing here changes that; `bury_step_fine` is
  a fidelity switch under the same flag and should ride with it.
- Found on the way, not this lane's: over-length fill and underlay segments
  (13.8-37.5 mm) in Becker's fields, which the DST writer turns into
  needle-up flights. One per run kind per job on all five Becker pairs.
