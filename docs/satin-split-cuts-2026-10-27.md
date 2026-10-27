# Satin-split cuts: three causes, one of them the letters' (2026-10-27)

**Question:** `tools/inpiece_cuts` counts cuts made INSIDE one sewn piece. Its
`satin_split` class is a cut between two satin runs of the same shape. Can we
bring it toward the pro's count?

**Answer:** only one of the three things behind that class is ours to fix:
the cuts inside lettering. The other two are already ruled, or the pro does
the same.

**Not built (the director, 2026-10-27: stop at the finding).** The narrow
cure for the letters, `lettering_columns_slot_guard`, takes 3 of the 8 letter
cuts:

- trims 261 → 258 over seven jobs;
- exposed travel falls 7.1 mm, and nothing rises;
- it pays for that with a second walk of every Column-lane letter.

It is written up below as a costed candidate, and its code is parked on
branch `claude/slot-guard-candidate`.

Measured on main 8341d1f7 (2026-10-27). Seven jobs at the pro's widths, via
`tools.pro_pair`: the five hats from #1072, plus Becker hat small and MFab LC.
Numbers only; no pro renders (Kent 2026-10-27).

## Cuts inside a piece, by cause

| job | width mm | DST trims ours / pro | inside ours / pro | satin_split | fill_section | shape_to_shape | edge_cap | other | exposed travel mm | bare mm |
|---|---|---|---|---|---|---|---|---|---|---|
| hotel_fremont_hat | 92.5 | 32 / 21 | 9 / 1 | 0 | 2 | 6 | 1 | 0 | 27.9 | 0.00 |
| becker_hat_large | 101.9 | 26 / 10 | 14 / 1 | 5 | 4 | 2 | 3 | 0 | 45.0 | 0.00 |
| mfab_hat | 104.9 | 25 / 19 | 15 / 3 | 3 | 9 | 3 | 0 | 0 | 23.3 | 0.00 |
| precision_drone | 62.6 | 104 / 59 | 20 / 20 | 8 | 6 | 2 | 4 | 0 | 44.3 | 3.93 |
| gaulke_roofing_hat | 114.2 | 34 / 42 | 4 / 0 | 2 | 0 | 1 | 1 | 0 | 16.7 | 5.99 |
| becker_hat_small | 76.5 | 19 / 11 | 7 / 2 | 6 | 1 | 0 | 0 | 0 | 29.2 | 0.73 |
| mfab_lc | 96.7 | 21 / 20 | 11 / 3 | 2 | 2 | 5 | 0 | 2 | 35.8 | 0.00 |
| **total** | | **261 / 182** | **80 / 30** | **26** | **24** | **19** | **9** | **2** | | |

How each side is read:

- Ours is attributed by plan run (`inpiece_cuts.attributed`).
- The pro's is read by stitch character (`classify_dst`). His inside cuts are
  almost all satin-to-run or satin-to-satin; 20 of his 30 are on the Drone.
- Exposed travel is `tools/travel_cover`; bare is `hairline_travel.scan`.
- The Drone's 104 against 59 is not inside pieces (20 / 20): its gap is
  between pieces.
- At 2c6b656c, before #1134 put `keyline_loop_chain` in the MFab gate, MFab
  read hat 33 trims / 8 satin_split and LC 27 / 7.

## The 26 satin_split cuts are three different things

**A. 16 cuts: loop to loop in a keyline / outline band** (`stage6_border.keyline_runs`).

These are Becker large 4, MFab hat 2, Drone 6, Becker small 3 and MFab LC 1.
Each loop is one closed satin, and between loops the needle lifts.

Lifts between the band's pieces, read by one reader for both files (our band
mapped onto his by registration):

| band | ours | pro |
|---|---|---|
| MFab hat | 5 | 7 |
| MFab LC | 7 | 10 |
| Drone | 37 | 31 |
| Becker large | 11 | 4 |
| Becker small | 6 | 3 |

- **MFab is at or under the pro already.** `keyline_loop_chain` rides the
  MFab gate (#1134).
- **Becker's gap is the chain's**, and Kent held the chain to MFab art (Kent
  2026-10-27, "MFab gate only (Recommended)").
- **That changes with #1143** (border lane, in CI when this was written). It
  turns the white recipe on as plain defaults on every job (Kent: "Every job
  (Recommended)"), and the recipe includes `keyline_loop_chain`. So Becker's
  bands, at 11 / 6 lifts against his 4 / 3, get the chain once it lands.
  **Re-measure class A after #1143.**
- **Burying the existing lifts with the loops left where they are buries 0
  of Becker's 7.** That was tested with `_bury_walks` over the band's own
  runs. Each loop ends where it began, on the far side from the next loop, so
  only the chained start reaches.
- **Not built.**

**B. 8 cuts: inside a Column-lane letter** (`columns.column_runs`, step 4).

These are Becker small M, N and E, Becker large E, Gaulke E ×2, MFab hat I and
MFab LC N.

- Lifts on those eight letters: ours 11 (8 trims, 3 short jumps), the pro's 1.
- **This class is real.**

**C. 2 cuts: Drone satin-tier shapes** (`stage6_satin.satin_shape`).

- A 0.8 mm bar 25 mm long: the pro does not sew it as satin pieces.
- A 4.5 × 32 mm shape: ours 3 lifts, the pro's 6.
- **The premise is false here.**

## The pro's rule inside a letter

`tools/letter_pieces`' letters, with the link between consecutive pieces read
from the DST (needle-down, or a lift):

| letter size | pro links down / lift | ours down / lift |
|---|---|---|
| under 5 mm | 12 / 0 | 11 / 7 |
| 5-10 mm | 71 / 1 | 43 / 7 |
| 10-20 mm | 78 / 8 (lifts 3.4 mm and up, median 6.1) | 35 / 14 |

Read per letter on the eight letters above, his links between pieces are
needle-down. They run 2-12.5 mm and lie under satin he sews LATER: the
"hidden" class of the per-shape reader.

**Rule:** inside a letter under 10 mm he does not lift. From 10 mm up he lifts
about one link in eleven, and only over 3.4 mm.

**Contradicting row:** Becker small's M (12.8 mm). He lifts 4.7 mm there too.

## Why ours cuts there

A spy on `column_runs`, run on every one of the eight letters:

1. **`_span_graph` merges column ends across a slot or a notch.** Two column
   ends within `merge_r` (1.3 W + 0.3 + pull) become one walk node. On Becker's
   bold letters `merge_r` is 5 mm: wider than an E's slot and the M's or N's
   notch.
   - So the top arm's root and the middle arm's root become one node, across
     the slot.
   - So do the middle arm's tip and the bottom arm's tip.
2. **The walk treats them as one place and the needle cannot.** The hop
   between the two real ends leaves the letter (6 of 8: straight hop outside
   the letter).
   - `_inside_path`, strict (`inside_connectors`), finds only a 9-47 mm detour
     along the centrelines.
   - Most of that detour is not under later satin, so step 4 trims.
3. **The guard against this already exists, for some letters.** The guard is
   `within`: the letter must cover the line between the two ends. It was added
   for the corner fold, after the same E fault on the Drone. It runs only on a
   letter that has a folded column.
   - Gaulke's E has a folded column, but `within` there is the letter grown
     by 0.1 + pull (0.5 mm). That closes its 1 mm slot, so it merges anyway.
4. **The other two letters (MFab hat I, MFab LC N) are different.** Their walk
   splits into two components. The hop between the components stays inside
   the letter, but 2.7-3.3 mm of it is not under later satin, over the 3.0 mm
   `allow`.

## Prototype: the guard on every letter

These arms are scratch monkeypatches, nothing committed. A verbatim copy of
`_span_graph` reproduces OFF byte for byte on Becker small and Gaulke.

- **p1** — `within` = letter + 0.1 + pull on the letters that had none.
- **p2** — `within` = letter + 0.1 on every letter.

| job | trims OFF | p1 | p2 |
|---|---|---|---|
| becker_hat_small | 19 | 16 | 16 |
| gaulke_roofing_hat | 34 | 34 | 32 |
| becker_hat_large | 26 | 25 | 25 |
| mfab_lc | 21 | 21 | 20 |
| mfab_hat | 25 | 25 | 24 |
| precision_drone | 104 | 104 | 104 |
| hotel_fremont_hat | 32 | 32 | **34** |

**p2 removes all 8 in-letter cuts, but pays in exposure.** Per letter
(`travel_cover`, each letter's own travel), the exposed travel on the changed
letters goes **48.1 → 58.3 mm**.

The reason is in step 4 itself:

- Step 4 already sews a hop needle-down when no more than `allow` =
  max(trim_at, 2 W) of it is left on top of finished work. That is 6.6 mm on
  Becker's 3.3 mm strokes.
- So the new walk's leg changes become rail-to-centre connectors drawn across
  satin just sewn. The crops show them as diagonals over the E's top arm and
  stem foot; the pro's E has none.
- Fremont's +2 job trims come from letters whose walk now starts or ends
  elsewhere: no in-letter cut moved there.

**Per-letter pick.** Keep p2's walk only where the letter cuts no more AND
exposes no more:

- in-letter cuts 8 → 4 (Becker small M, Gaulke E, Becker large E, MFab LC N);
- exposure 48.1 → 37.7 mm.

The other four letters keep their cut; their guarded walk exposes 1.3-4.9 mm
more:

- Becker small N 4.2 → 7.7 mm;
- Becker small E 4.4 → 9.2 mm;
- Gaulke E 0 → 1.7 mm;
- MFab hat I 1.6 → 2.9 mm.

## Costed candidate: `cfg.lettering_columns_slot_guard` (built, not merged)

**Where it is.** Branch `claude/slot-guard-candidate` (50c8bc0a). It is the
per-letter pick as one OFF flag, with its tests, and is ready if Kent wants it.

**Files:**

- `digitizer_core/letter_walk.py` (new);
- `columns.column_runs`: a `slot_guard` kwarg on the `_span_graph` call;
- `columns.lettering_columns_shape`: the pick at the final sew;
- one stage-7 kwarg;
- one config block;
- `tests/engine_2026_10_27.json`;
- `tests/test_column_slot_guard.py`, with `testdata/slot_guard_letters.json`
  (the 8 letters' lane arguments, captured from stage 7).

**Why it was not merged** (the director): -3 trims across seven jobs is about
2% of the trim gap. It costs a second `column_runs` on every Column-lane
letter, and the lane is already the digitizer's largest CPU cost: the
customer waits on every digitize.

**Runtime.** Lane CPU, `lettering_columns_shape` per letter (one core, one
repeat, inside a CPU slot), on every captured letter set:

| letters | n | OFF s | ON s | × |
|---|---|---|---|---|
| the 8 cut letters | 8 | 6.50 | 7.44 | 1.14 |
| Becker 80 mm | 6 | 1.14 | 3.92 | 3.44 |
| Fremont 92.5 mm | 12 | 2.92 | 5.12 | 1.75 |
| MFab hat 104.9 mm | 14 | 89.34 | 93.95 | 1.05 |
| Drone 62.6 mm | 19 | 13.62 | 14.50 | 1.06 |
| **all** | 59 | **113.5** | **124.9** | **1.10** |

Where the fold-cut judge dominates (MFab), the second walk is noise. On plain
letters (Becker) it triples the lane. Whole-plan wall times on the loaded
machine did not separate the arms.

How the candidate works:

- `columns.column_runs` takes `slot_guard`: `within` = the letter grown
  `SLOT_GUARD_GROW_MM` (0.1), on every letter.
- `columns.lettering_columns_shape` walks the letter's final cut both ways
  (`letter_walk.pick`). It keeps the guarded walk only where `walk_cost` is no
  worse on both counts and better on one:
  - cuts: trims after the first run;
  - on top: travel no later satin of the letter covers, zigzag widened
    0.25 mm.
- **The fold-cut judge stays on today's walk.** The pick chooses how a cut is
  walked, never which cut is chosen. Routed through the pick, the judge took
  a different cut on a Drone letter, and that letter laid 2.2 mm of travel on
  top where today lays none.
- **No constant moves.** `SLOT_GUARD_GROW_MM` is float slack on the artwork,
  and `COVER_HALF_MM` closes the 0.4 mm zigzag spacing. Neither is cloth
  (gate 1).
- **Gate 3 is clear.** Chaining and contour are untouched.

Re-planned on main 98603fb4 + the flag, from each job's stage 0-5 result at
8341d1f7. MFab hat's runs took the rembg route (`PHOTO_BACKGROUND_REMOVED`),
using the primary checkout's `rembg_isolated` venv; none was the classical
route.

**OFF is byte for byte the census**, on all seven DST md5s. ON:

| job | trims OFF / ON / pro | stitches OFF / ON / pro | inside OFF / ON / pro | satin_split OFF / ON | exposed mm OFF / ON | bare mm OFF / ON |
|---|---|---|---|---|---|---|
| hotel_fremont_hat | 32 / 32 / 21 | 17,263 / 17,259 / 17,067 | 9 / 9 / 1 | 0 / 0 | 27.90 / 27.05 | 0.00 / 0.00 |
| becker_hat_large | 26 / **25** / 10 | 16,915 / 16,937 / 12,356 | 14 / 13 / 1 | 5 / 4 | 44.95 / 44.95 | 0.00 / 0.00 |
| mfab_hat | 25 / 25 / 19 | 20,516 / 20,516 / 17,568 | 15 / 15 / 3 | 3 / 3 | 23.29 / 23.29 | 0.00 / 0.00 |
| precision_drone | 104 / 104 / 59 | 14,599 / 14,599 / 14,552 | 20 / 20 / 20 | 8 / 8 | 44.28 / 44.28 | 3.93 / 3.93 |
| gaulke_roofing_hat | 34 / **33** / 42 | 7,474 / 7,478 / 6,138 | 4 / 3 / 0 | 2 / 1 | 16.71 / 16.71 | 5.99 / 5.99 |
| becker_hat_small | 19 / **18** / 11 | 11,144 / 11,212 / 8,694 | 7 / 6 / 2 | 6 / 5 | 29.18 / **22.80** | 0.73 / 0.63 |
| mfab_lc | 21 / 21 / 20 | 17,754 / 17,771 / 15,786 | 11 / 11 / 3 | 2 / 2 | 35.80 / **34.06** | 0.00 / 0.00 |
| **total** | **261 / 258** / 182 | | **80 / 77** / 30 | **26 / 23** | **221.1 / 214.0** | **10.65 / 10.55** |

- **Three cuts go, one per job:** Becker small's M, Becker large's E and
  Gaulke's first E. MFab hat and the Drone are byte for byte OFF.
- **Exposed travel falls 7.1 mm** across the seven jobs. Bare thread falls
  0.1 mm.
- **Nothing rises on any job.** Becker's M also loses its 6.4 mm walk across
  its own finished top.

Per letter, on the captured arguments (`testdata/slot_guard_letters.json`, on
the candidate branch):

| letter | cuts OFF / ON | on top mm OFF / ON | taken |
|---|---|---|---|
| Becker 76.5 M | 1 / 0 | 9.69 / 3.86 | yes |
| Becker 76.5 N | 1 / 1 | 4.03 / 4.03 | no |
| Becker 76.5 E | 1 / 1 | 4.47 / 4.47 | no |
| Becker 101.9 E | 1 / 0 | 11.62 / 11.62 | yes |
| Gaulke 114.2 E (1) | 1 / 0 | 3.26 / 3.26 | yes |
| Gaulke 114.2 E (2) | 1 / 1 | 0.00 / 0.00 | no |
| MFab LC 96.7 N | 1 / 1 | 1.01 / 1.01 | no |
| MFab hat 104.9 I | 1 / 1 | 1.98 / 1.98 | no |

Why the rest are not taken:

- **Becker small's N and E, and Gaulke's other E:** the guarded walk would lay
  travel on finished satin (the N: 4.0 → 7.9 mm).
- **MFab's N and I:** they cut between two walk components, which the guard
  does not join.

On the other Column-lane letters of four jobs (the band fixtures):

- Becker at 80 mm: travel on top 31.0 → 17.0 mm.
- MFab hat: 22.0 → 20.6.
- Drone: cuts 2 → 1, 12.3 → 10.5.
- Fremont: unchanged.

Crops (OFF | ON | pro at 40 px/mm, scratch only; no pro render is committed):

- **Becker's M:** the in-letter trim and the diagonal across its top go.
- **Becker large's E:** the trim at the middle arm's tip goes. Its two
  diagonals across finished satin stay, as OFF has them.

## What is left

**What the pro does that we don't** is end each satin where the next one
starts, under satin still to come. Ours ends on a rail and crosses the column
it just sewed to reach the next leg's centre. That is why the guard alone
turned trims into on-top travel.

**All eight letter cuts stand on main.** The candidate would take three. The
other five need that construction change, not a merge rule.
