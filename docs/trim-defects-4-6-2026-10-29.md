# Defects 4 and 6 re-measured, and the next cut-reducer (2026-10-29)

Kent asked on 2026-10-29 for MASTER_SCOPE defects 4 ("we trim 3.1x the pro")
and 6 ("satin fragments; the trim bulk is inside one shape") to be fixed. Both
figures were from 2026-08/09. This page re-measures them on `main` 44ecf1cb,
prices the trim levers already built OFF, and measures the one this PR adds,
`cfg.extra["fill_section_cuts_first"]` (OFF).

## How it was measured

- **Jobs:** every pair with the customer's art and the pro's DST:
  `tools/border_census.PAIRS` plus ProSeal beanie, 17 jobs. Each is digitized at
  the pro's own width and garment through the Studio's request
  (`tools.pro_pair.digitize`, `tools.flip_sheet_renders.fixture_files`).
- **Arms:** stages 0-4 run once per job, then `plan_stitches` runs once per arm
  on the same result. Replayed from a pickle, the OFF arm's DST is
  byte-identical to the live run on all 17 jobs.
- **One reader on both DSTs:**
  - `tools/sequence_pro`: cuts, and how they split between inside one piece and
    between pieces.
  - `tools/trim_classes`: what each cut's hop lies on.
  - Needle-up moves left uncut, from the raw records.
- **Plan side, ours only:** `tools/trim_locality.split` (TRIM_HEAVY's
  `in_shape` / `between`), `tools/inpiece_cuts.classify_plan` (cause of each cut
  inside a piece), and `tools/travel_cover` (exposed travel).
- **Gate 3:** `flip_sheet_renders.bare_by_band`, mm of bare thread at 0.20 mm.

Trims are DST cuts. A colour change is not counted.

## Defect 4: the 3.1x is gone; the needle-up gap is not

| | ours (main) | pro | ratio |
|---|---|---|---|
| cuts, 17 jobs pooled | 391 | 409 | **0.96x** |
| cuts, per-job ratio | median 1.18x, range 0.33-3.00 | | |
| needle-up moves (cut + uncut) | 879 | 425 | **2.07x** |
| uncut needle-up moves | 488 | 16 | |

- **We now cut about as often as the pro.** The 3.1x (2026-08) was a different
  reading, on an older engine. Since then these went ON: `trim_bury_under_later`,
  the white recipe, `keyline_loop_chain`, `keyline_fold_slivers` and
  `skip_covered_shapes`.
  - The pro cuts 18 under-later hops; we cut 14 (was 43 vs 9 on 10-21).
  - On-work cuts: ours 233, his 235.
- **Breaks are still 2.1x.** The pro cuts every needle-up move. We leave 488
  short ones uncut: Fremont about 150 each, ProSeal 20-26, Gaulke 15-23.
  `cut_every_jump` (OFF) is the lever already built for those.
- **Where we cut LESS than the pro** (Gaulke, ProSeal, Tires, Bridge), the
  missing cuts are those floats.
- **The excess that is left is concentrated:**
  - Drone +25: between pieces. `buried-walk-2026-10-26` found that is
    construction: layering and colour revisits, Kent's call from renders.
  - Becker beanie +8.
  - MFab hat +9 and MFab LC +5.
  - The Becker family +2 to +4 each, all of it inside one piece.

## Defect 6: the trim bulk is no longer inside one shape

| | ours | pro |
|---|---|---|
| cuts inside one piece (`sequence_pro`) | 104 of 391 (27%) | 73 of 409 (18%) |
| `trim_locality` in-shape / between | 60 / 375 (14% in-shape) | n/a |

Our 104 cuts inside a piece, by cause (`inpiece_cuts`):

- **shape_to_shape 42.** The pro's own in-piece cuts are 73, mostly satin to
  satin: letters touching inside a word (ProSeal, Drone).
- **fill_section 32.** The pro has 0 on all 17 jobs.
- **satin_split 27.** The pro's satin-to-satin is 32.
- **satin_fill_section 1.**

So the class the pro never has is the cut between two sections of ONE fill. It
is also the largest class with no explanation already on record:

- Becker's fields cause 2-4 per job.
- MFab's field, 5 per job.
- Drone, 7.

## What still causes the fill-section cuts

We spied on `stage6_fill._plan_sections` with `fill_section_travel` ON.

| shape | incoming order (cuts, travel st, exposed st) | planner's order | `_score` (rate 25/cut, exposed x2) |
|---|---|---|---|
| Becker small field | (4, 123, 22.6) | **(3, 217, 11.4)** | 268 vs 315: refused |
| MFab hat field | (8, 77, 0.4) | **(6, 153, 0.4)** | 278 vs 304: refused |

**The planner already finds the better order.** It has fewer cuts and no more
exposed travel; Becker's exposed travel is halved. `_score` refuses it for the
extra TRAVEL stitches alone. That travel is the hidden kind: under rows still
to come, which the fill sews over afterwards. That is the pro's own way across
a fill.

The 10-25 doc (`in-piece-cuts-2026-10-25.md`) wrote that "every such order
lays thread on finished fill or travels further than its cuts are worth". On
these two fields the first half is false, and the second half is the price of
hidden travel.

## The lever: `cfg.extra["fill_section_cuts_first"]` (OFF)

- Turns `fill_section_travel` on.
- Prices the section planner's orders with `stage6_fill._score_hidden_free`:
  cuts and exposed travel only, at `_score`'s own two rates, with the travel
  under rows still to come free.
- **The gate is unchanged.** A plan is kept only if it cuts no more, and lays
  no more thread on finished fill, than the incoming order.
- Every hidden route stays inside `travel_path`'s length budget. No new
  constant.
- Read inside `plan_stitches` only. `shape_memo` carries the new ContextVar.

### Priced, 17 jobs, OFF | ON | pro

Each cell is DST cuts / exposed travel mm (`travel_cover`) / bare thread mm at
0.20.

| job | pro cuts | main (OFF) | `fill_section_travel` | **`fill_section_cuts_first`** | `cut_every_jump` | `fill_bridge_cut_exposed` | cuts_first + bridge_cut | + cut_every_jump |
|---|---|---|---|---|---|---|---|---|
| becker_beanie | 4 | 12 / 55 / 3.7 | 11 / 45 / 3.7 | 11 / 45 / 3.7 | 13 / 55 / 3.3 | 12 / 39 / 3.7 | 11 / 39 / 3.7 | 12 / 39 / 3.3 |
| becker_chest_small | 11 | 13 / 40 / 4.8 | 13 / 40 / 4.8 | 12 / 21 / 4.8 | 15 / 40 / 0.7 | 15 / 21 / 4.8 | 13 / 21 / 4.8 | 15 / 21 / 0.7 |
| becker_hat_large | 9 | 12 / 38 / 0.1 | 12 / 38 / 0.1 | 11 / 23 / 0.1 | 12 / 38 / 0.1 | 12 / 23 / 0.1 | 11 / 23 / 0.1 | 11 / 23 / 0.1 |
| becker_hat_small | 10 | 13 / 41 / 4.6 | 13 / 41 / 4.6 | 12 / 22 / 4.6 | 15 / 41 / 0.8 | 15 / 22 / 4.6 | 13 / 22 / 4.6 | 15 / 22 / 0.8 |
| becker_lc_large | 11 | 15 / 42 / 0.4 | 14 / 49 / 0.4 | 14 / 49 / 0.4 | 15 / 42 / 0.4 | 15 / 31 / 0.4 | 14 / 31 / 0.4 | 14 / 31 / 0.4 |
| bridge_hat | 19 | 15 / 10 / 0.0 | = | = | = | = | = | = |
| bridge_lc | 19 | 17 / 16 / 0.0 | = | = | = | = | = | = |
| gaulke_roofing_hat | 41 | 30 / 17 / 6.0 | = | = | 44 / 17 / 0.0 | = | = | 44 / 17 / 0.0 |
| gaulke_roofing_lc | 41 | 23 / 11 / 7.2 | = | = | 42 / 11 / 0.0 | = | = | 42 / 11 / 0.0 |
| hotel_fremont_hat | 20 | 25 / 9 / 0.0 | = | = | = | = | = | = |
| hotel_fremont_patch | 20 | 20 / 12 / 0.0 | = | = | = | = | = | = |
| mfab_hat | 18 | 27 / 14 / 0.0 | 27 / 14 / 0.0 | **24** / 14 / 0.0 | = | = | 27 / 14 / 0.0 | 27 / 14 / 0.0 |
| mfab_lc | 19 | 24 / 39 / 0.0 | 21 / 40 / 0.0 | 21 / 40 / 0.0 | = | 25 / 39 / 0.0 | 21 / 39 / 0.0 | 21 / 39 / 0.0 |
| precision_drone | 58 | 83 / 40 / 2.5 | 82 / 30 / 2.5 | 79 / 30 / 2.5 | 92 / 40 / 0.2 | 87 / 20 / 2.5 | 84 / 20 / 2.5 | 93 / 20 / 0.2 |
| proseal_beanie | 47 | 27 / 298 / 118.4 | = | = | 45 / 298 / 118.0 | 29 / 292 / 118.4 | 27 / 294 / 118.4 | 45 / 294 / 118.0 |
| proseal_hat | 53 | 32 / 28 / 1.6 | = | 33 / 21 / 1.6 | 47 / 28 / 0.2 | 36 / 17 / 1.6 | 36 / 17 / 1.6 | 51 / 17 / 0.2 |
| tires_hat_3d | 9 | 3 / 13 / 9.0 | = | = | = | = | = | = |

`=` means the same as main. Totals:

| arm | cuts (pro 409) | inside a piece (pro 73) | fill-section cuts (pro 0) | exposed mm | bare mm @0.20 | uncut moves (pro 16) | plan CPU s |
|---|---|---|---|---|---|---|---|
| main (OFF) | 391 | 104 | 32 | 723 | 158.3 | 488 | 551 |
| `fill_section_travel` | 385 | 98 | 26 | 711 | 158.3 | 488 | 650 |
| **`fill_section_cuts_first`** | **377** | **90** | **18** | **651** | 158.3 | 485 | 641 |
| `cut_every_jump` | 471 | 104 | 32 | 723 | 132.8 | 25 | 526 |
| `fill_bridge_cut_exposed` | 406 | 119 | 47 | 606 | 158.3 | 488 | 552 |
| cuts_first + bridge_cut | 390 | 103 | 31 | 609 | 158.3 | 487 | 663 |
| cuts_first + bridge_cut + cut_every_jump | 470 | 103 | 31 | 609 | 132.8 | 25 | 676 |

### Reading it

- **`fill_section_cuts_first` alone:**
  - 14 fewer cuts, all of them fill sections (32 -> 18).
  - 72 mm less exposed travel.
  - Bare thread unchanged on every job, so gate 3 is clear.
  - It changes 9 of 17 jobs. Becker's fields gain on exposure as well as cuts:
    hat small 41 -> 22 mm.
- **Two rows rise:**
  - becker_lc_large exposure 42 -> 49 mm and mfab_lc 39 -> 40 mm. Both are
    already there with `fill_section_travel` alone: that flag's hidden routes,
    which `travel_cover`'s 1 mm cells read as exposed. This switch adds nothing
    to either.
  - proseal_hat cuts 32 -> 33, with its exposure 28 -> 21 mm.
- **With `fill_bridge_cut_exposed`:**
  - That flag, alone, removes 117 mm of travel on finished fill for +15 cuts.
  - Beside this switch it costs one cut fewer than main (390 vs 391).
  - The two together: 609 mm exposed against 723.
- **`cut_every_jump`** is the only lever on the 2.1x break gap: uncut moves
  488 -> 25, cuts +80, bare thread 158 -> 133 mm. Its sew-out arm
  (Kent 2026-10-21) still stands.
- **CPU:** stage 7 +16% on these jobs, the same as `fill_section_travel`
  alone.
- **Still OFF:** OFF and `fill_section_travel` alone are byte-identical to
  main on all 17 jobs (DST md5).

## Not reached, for the record

- **Drone's +25 between pieces:** construction (`buried-walk-2026-10-26`).
- **Satin to satin in letters:** `satin-split-cuts-2026-10-27` costed a
  candidate and did not build it.
- **MFab's shape_to_shape 10 per job:** satin then the next satin's underlay,
  3-39 mm apart. Unattributed beyond that.
- **ProSeal beanie:** 298 mm exposed and 118 mm bare on every arm. That is
  41% of the corpus's exposed travel and three quarters of its bare thread in
  one job, and nothing here touches it. It is the next travel investigation,
  not a trim one.
- **Underlay hops buried under rows nearly parallel to them** can show in the
  render while every instrument reads them covered (#1187's note). The hidden
  travel this switch frees is the same kind. Judge the flip in the preview
  (`layout-judged-in-preview-2026-10-22`).

Tests: `digitizer/tests/test_fill_section_cuts_first.py`.
