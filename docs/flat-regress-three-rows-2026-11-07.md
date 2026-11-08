# Three more flat-lane tripwire rows: Gaulke hat trims, Fremont patch trims, MFab LC needle-up (2026-11-07)

Diagnosis only. `digitizer_core/` is untouched and no default moves. The pinned
test is `digitizer/tests/test_flat_regress_three_rows.py`.

## Question

#1321 traced three more wrong-way tripwire rows to `stage0_scale_relative_grad`
(#1301), which now routes all three jobs down the FLAT lane instead of the
gradient lane, but named no region-level cause:

| job | figure | gradient lane | flat lane | pro |
|---|---|---|---|---|
| gaulke_roofing_hat | trims | 30 | 32 | 42 |
| hotel_fremont_patch | trims | 20 | 24 | 21 |
| mfab_lc | needle-up mm | 345.2 | 389.3 | 367.5 |

This doc repeats #1325's method (`docs/goldentee-flat-regress-2026-11-07.md`)
on each row: what the flat lane does differently, by kind of region and by
place in the design.

## Answer, one line per row

| row | lane class | in one sentence |
|---|---|---|
| gaulke_roofing_hat trims 30 -> 32 | **route** | Both lanes give stage 7 the same 53 regions. Their polygons differ by 0.72 mm2 in total, and that is enough to re-roll the sew route through the lettering. From -0.2 to +0.2 mm of width the flat-minus-gradient trim delta reads 0 / -2 / **+2** / +2 / 0. |
| hotel_fremont_patch trims 20 -> 24 | **cured on main** | `flat_light_text_runs` (#1328, ON in #1329) gives the flat lane the dark-ink carve. On today's main both arms read 20 trims, 175 hops and 475.9 mm. #1321's 24 trims come back only with that switch off. |
| mfab_lc needle-up 345.2 -> 389.3 | **route** | The +44.1 mm splits into three route moves: the white block's entry (+58.2), the white keyline's own route (+40.3) and the black body's route (-57.7). From -0.2 to +0.2 mm of width the delta reads -17.8 / -87.4 / **+44.1** / -32.3 / +73.4. |

So none of the three is a flat-lane region defect of the Golden Tee kind. Two
are route noise, which the tripwire happened to sample at the pro's exact
width. The third is already fixed, and the ledger re-seed at fc0d32ac
(#1333) already holds 20.

## Method

- **Arms.** Each job is digitized with shipped defaults ("flat", stage 0
  routes it flat) and with `{"stage0_scale_relative_grad": False}`
  ("gradient"). Both go through `tools.pro_pair.digitize` at the pro's width
  and garment, the same call `tools.tripwire.measure` makes. Fremont patch
  gets a third arm, `{"flat_light_text_runs": False}`, which is main as it
  stood when #1321 ran. Jobs ran one at a time on main 21b8b57d, on Kent's
  Windows laptop.
- **Reproduction.** Every arm matches #1321 and the ledger exactly:
  - Gaulke: 30 / 32 trims and 371.5 / 396.6 mm.
  - MFab: 345.2 / 389.3 mm and 31 / 26 hops.
  - Fremont patch, switch off: 24 trims, 149 hops, 467.3 mm.
- **Figures.** These are machine-file figures, read back from each arm's DST
  the way `tools.pro_baseline` reads them: trims, hops and needle-up mm.
  Stitches are the plan's own count, which equals the DST's here.
- **Attribution.** Each DST lift (the gap from the last stitch before a
  JUMP, TRIM or COLOR_CHANGE to the first stitch after it) is matched by its
  endpoints to the plan transition that produced it. It belongs to the shape
  the needle lands on, and to that shape's region; merged shapes count with
  their host. The match closes exactly on every arm: no lift and no stitch is
  left unowned.
  - A plan transition is a run's trim or jump flag, a colour change, or a
    needle-down step over 12 mm between runs. pystitch's DST writer turns that
    last kind into a trim plus jumps (see #1339 below).
- **Region kinds.** Each region gets the first kind that applies:
  1. lettering: rescued small text (`text_cluster_id` and `rescued_small_shape`)
  2. lettering: drawn (`text_cluster_id`)
  3. rescued speck (`rescued_small_shape`)
  4. dark-ink read (`dark_ink`)
  5. enclosed white (`sew_enclosed_white` or `enclosed_background`)
  6. narrow (under 0.7 mm, by 2 x area / perimeter)
  7. small (under 5 mm2)
  8. body
- **Zones.** Each region goes to a zone by where its centroid falls in the
  design's box.
- **Width jitter.** Gaulke and MFab were also digitized in both arms at the
  pro's width -0.2, -0.1, +0.1 and +0.2 mm.

## Gaulke Roofing hat: trims 30 -> 32

Two inks, black on white. 39 regions carry a text cluster: the 35 glyphs of the
two lines, plus the house window's four panes, which the tagger also clusters.

| region kind | gradient: n / stitches / trims / hops / needle-up mm | flat | change |
|---|---|---|---|
| lettering, drawn | 39 / 3,792 / 28 / 42 / 267.2 | 39 / 3,761 / 30 / 42 / 301.5 | -31 / **+2** / 0 / +34.3 |
| narrow (the roofline's thin stroke) | 1 / 397 / 1 / 1 / 29.5 | 1 / 397 / 1 / 1 / 29.5 | 0 |
| body (roof mark) | 3 / 3,257 / 1 / 2 / 74.7 | 3 / 3,255 / 1 / 2 / 65.6 | -2 / 0 / 0 / -9.2 |
| total | 43 / 7,446 / 30 / 45 / 371.5 | 43 / 7,413 / 32 / 45 / 396.6 | -33 / +2 / 0 / +25.1 |

| zone | gradient: n / stitches / trims / hops / needle-up mm | flat | change |
|---|---|---|---|
| roof mark | 5 / 3,324 / 2 / 4 / 83.3 | 5 / 3,322 / 2 / 4 / 74.2 | -2 / 0 / 0 / -9.2 |
| C GOLKE INDUSTRIES | 19 / 2,169 / 16 / 21 / 147.6 | 19 / 2,169 / 17 / 21 / 217.3 | 0 / +1 / 0 / +69.6 |
| STEEL ROOFING & SUPPLY | 19 / 1,953 / 12 / 20 / 140.5 | 19 / 1,922 / 13 / 20 / 105.2 | -31 / +1 / 0 / -35.3 |

The whole +2 is in drawn lettering, one trim in each line. It is not a region
the flat lane adds or splits:

- **Same regions.** Both lanes give stage 7 the same 53 regions under the
  same 53 shape ids. Polygon change, summed over all of them, is 0.72 mm2.
  It sits on 7 letters, the largest 0.27 mm2 (one letter, 19.4 -> 19.6 mm2).
  No region is rescued, enclosed or new on either lane.
- **Same route for 12 lifts.** The two runs land on the same shapes in the
  same order for the first 12 of 45 lifts. The lift lengths start to drift at
  lift 8, after the letters whose polygons moved (S51246dbf moved 0.22 mm2).
  At lift 11, letter Scd6b2ed5 is reached by a 2.3 mm float on the gradient
  lane and by a 7.2 mm trim on the flat lane. From lift 13 the order through
  both lines differs, and one more entry in each line lands as a trim rather
  than a float.
- **Width spread.** At -0.2 to +0.2 mm, trims read 28 / 29 / 32 / 28 / 28 on
  the flat lane and 28 / 31 / 30 / 26 / 28 on the gradient lane. The pro's
  114.2 mm is the high point for both lanes. The delta's mean over the five
  widths is +0.4 trims.

Gaulke's needle-up (371.5 -> 396.6, also a #1321 row) is the same route. Its
delta by width is +0.2 / +33.2 / +25.1 / +14.8 / -0.2 mm. It never goes
negative, but it stays under the 98-123 mm that either lane spans on its own.

## Hotel Fremont patch: trims 20 -> 24

Three inks: white field, black wordmark and frame, tan rope and tan small text
(EST 1895, EAT | STAY | PLAY). This is the same art as Fremont hat in #1325,
at patch size.

| arm | class | regions | stitches | trims | hops | needle-up mm | blocks in order |
|---|---|---|---|---|---|---|---|
| gradient | gradient | 166 | 14,856 | 20 | 175 | 475.9 | white, tan, black, white |
| flat, `flat_light_text_runs` off (#1321's arm) | flat | 166 | 14,852 | **24** | 149 | 467.3 | white, black, white, **tan** |
| flat, as shipped today | flat | 168 | 14,858 | **20** | 175 | 475.9 | white, tan, black, white |

On today's main, the flat arm equals the gradient arm on trims, hops and
needle-up, and differs by 2 stitches. The row was cured by #1328/#1329,
which landed between #1321's measurement and this one.

What #1321 saw: the flat arm with the switch off, against the gradient arm.
The table matches shapes by id and takes each shape's kind from the gradient
arm. Without the carve the flat lane drops every `dark_ink` tag, so kinds
read from each arm would move the black frame between kinds and hide where
the trims went.

| region kind (from the gradient arm) | gradient: n / stitches / trims / hops / needle-up mm | flat, switch off | change |
|---|---|---|---|
| lettering, drawn (THE, HOTEL FREMONT) | 19 / 2,239 / 5 / 25 / 57.7 | 19 / 2,309 / 8 / 19 / 69.4 | +70 / **+3** / -6 / +11.8 |
| lettering, rescued small text (tan tagline) | 14 / 499 / 5 / 25 / 92.5 | 14 / 731 / 6 / 16 / 64.7 | +232 / **+1** / -9 / -27.9 |
| rescued speck (the tan rope) | 120 / 1,700 / 6 / 119 / 201.2 | 119 / 1,393 / 6 / 108 / 273.0 | -307 / 0 / -11 / +71.8 |
| dark-ink read (black hexagon frame halves, band rules) | 5 / 1,671 / 4 / 5 / 121.2 | 5 / 1,671 / 4 / 5 / 53.0 | 0 / 0 / 0 / -68.2 |
| body (white field) | 2 / 8,747 / 0 / 1 / 3.3 | 2 / 8,748 / 0 / 1 / 7.2 | +1 / 0 / 0 / +3.9 |
| total | | | -4 / +4 / -26 / -8.6 |

| zone | gradient: n / stitches / trims / hops / needle-up mm | flat, switch off | change |
|---|---|---|---|
| top: rope, EST 1895, the state | 65 / 1,576 / 4 / 69 / 225.8 | 65 / 1,550 / 4 / 64 / 160.9 | -26 / 0 / -5 / -64.9 |
| THE | 3 / 223 / 0 / 4 / 5.5 | 3 / 240 / 1 / 3 / 7.0 | +17 / +1 / -1 / +1.5 |
| HOTEL FREMONT band | 19 / 11,371 / 6 / 18 / 81.9 | 19 / 11,336 / 8 / 17 / 88.5 | -35 / +2 / -1 / +6.5 |
| bottom: EAT STAY PLAY, rope | 73 / 1,686 / 10 / 84 / 162.7 | 72 / 1,726 / 11 / 65 / 210.9 | +40 / +1 / -19 / +48.3 |

By kind, all +4 trims fall on lettering: +3 on the black wordmark and +1 on the
tan tagline. The mechanism is #1325's Fremont hat finding, at patch size.
Without dark-ink labels:

- **The tan tagline goes the small-text re-set.** It is enlarged into satin,
  +232 stitches.
- **The tan block moves.** It goes from second to last, so the black
  wordmark is sewn straight after the white and enters each letter from a
  different place.

With `flat_light_text_runs` ON, stage 2 on the flat lane finds the tan
strokes again. The pinned test reads this on the patch: no dark-ink labels
from `quantize`, some after `carve_flat_dark_ink`. Block order, trims, hops
and needle-up all return to the gradient arm's.

## MFab LC: needle-up 345.2 -> 389.3 mm

Black lettering, a white keyline ring around everything, and a black outer
body. That is three blocks: black, white, black.

| region kind | gradient: n / stitches / trims / hops / needle-up mm | flat | change |
|---|---|---|---|
| enclosed white (keyline ring + letter counters) | 5 / 5,574 / 7 / 9 / 153.5 | 5 / 5,517 / 8 / 9 / 252.8 | -57 / +1 / 0 / **+99.3** |
| body (black outer body) | 1 / 10,793 / 2 / 3 / 101.8 | 1 / 10,664 / 1 / 1 / 44.1 | -129 / -1 / -2 / **-57.7** |
| lettering, drawn | 14 / 1,678 / 8 / 16 / 71.1 | 13 / 1,631 / 8 / 14 / 66.7 | -47 / 0 / -2 / -4.4 |
| lettering, rescued small text | 3 / 47 / 2 / 3 / 18.9 | 2 / 36 / 2 / 2 / 25.7 | -11 / 0 / -1 / +6.8 |
| rescued speck, narrow, small | 0 sewn (all merged or unsewn) | 0 sewn | 0 |
| total | 23 / 18,092 / 19 / 31 / 345.2 | 21 / 17,848 / 19 / 26 / 389.3 | -244 / 0 / -5 / +44.1 |

| zone | gradient: n / stitches / trims / hops / needle-up mm | flat | change |
|---|---|---|---|
| M-FAB word + keyline ring (its centroid is here) | 5 / 16,175 / 8 / 11 / 225.6 | 5 / 15,990 / 8 / 9 / 251.9 | -185 / 0 / -2 / +26.4 |
| AND WELDING LLC | 18 / 1,917 / 11 / 20 / 119.7 | 16 / 1,858 / 11 / 17 / 137.4 | -59 / 0 / -3 / +17.7 |

The +44.1 mm, lift by lift:

| part | gradient mm | flat mm | change |
|---|---|---|---|
| black body's own lifts (block 1) | 101.8 (3 hops) | 44.1 (1 hop) | -57.7 |
| colour change into white: the needle lands on... | the keyline, 5.4 | a letter counter, 63.5 | **+58.2** |
| white keyline's own lifts after its entry | 85.0 | 125.3 | +40.3 |
| other counters, lettering, second colour change | 153.1 | 156.4 | +3.3 |

The kinds are all named, and the four parts cover all of the change. What
moved is the route, not the shape count:

- **Same shapes, small polygon changes.** The black body is the same polygon
  to 6 mm2 in 958. The keyline is 30 mm2 larger on the flat lane (800.8
  against 771.0 mm2, white area 899.7 against 869.2 mm2). The flat lane also
  rescues 64 sub-floor masks against 45 (59 of them white). Outside the
  lettering, none of them owns a run: each is merged into a host or left
  unsewn.
- **The route moves anyway.** Those changes move where the black body ends
  and where the white block starts. Every part of the route is then
  re-ordered.
- **Width spread.** From -0.2 to +0.2 mm, the flat lane reads 399.9 / 405.7
  / 389.3 / 561.4 / 469.2 mm and the gradient lane 417.7 / 493.1 / 345.2 /
  593.7 / 395.8. Either lane alone spans 170-250 mm. The delta's mean over
  five widths is -4.0 mm.
- **The ledger sampled the gradient lane's low.** Its 345.2 mm is the
  gradient lane's lowest reading of the five. It is the only width where its
  white block entered 5.4 mm from the black's last stitch.

## Overlap with the flat fleck-rescue lane, and next lanes

**Left to the fleck-rescue lane.** No attributed delta in these three rows
sits in the rescued-speck kind:

- Gaulke rescues nothing that sews.
- Fremont patch's rope specks are the same 120 on both lanes, and they own 0
  of its +4 trims.
- MFab's flat lane keeps 19 more white flecks than the gradient lane (64
  against 45), but none of them sews.

What the fleck lane does change on MFab is the keyline polygon those flecks
sit against. Through the route, that can move MFab's needle-up either way.
So **read any fleck-lane move on gaulke or mfab against the width spreads
above, not as a cure or a cost.**

**Left to #1339 (`split_long_inshape_stitches`, open).**

- **What it is.** The plan has needle-down steps of 22 mm and more between
  two runs of one shape, with no jump flag. pystitch's DST writer turns each one into a trim plus
  jumps.
- **What it costs MFab.** 31 to 79 mm of its DST needle-up comes from these
  steps, depending on arm and width: 47.5 mm on the flat arm and 69.4 on the
  gradient arm at 96.7 mm.
- **Why it matters for trims.** It is also why plan trims (21) and DST trims
  (19) disagree on MFab: a counter that reads the plan sees different trims
  from a counter that reads the file.

**Candidate next lanes:**

1. **A width bracket in the tripwire, for route figures.** Measure trims,
   hops and needle-up at the pro's width +-0.1 mm, and keep the median or the
   bracket. These two jobs move up to 5 trims and up to 250 mm within 0.2 mm of
   width. That is more than either "wrong-way" move.
2. **Colour-block entry.** On the flat lane, MFab's white block enters
   63-68 mm from black's last stitch at all five widths. The gradient lane
   lands 5.4-68 mm away. One job only, so it is a lane to measure, not a
   finding.
3. **Lettering route stability.** On Gaulke, a 0.2 mm2 change in one letter
   re-orders the whole route through both lines. Lower value: the route it
   picks is not worse on average (+0.4 trims).

## Decisions for Kent

1. **Accept: no build.**
   - Delivers: the doc closes #1321's last three rows. Two are route noise,
     and one is already fixed on main and already in the ledger.
   - Cost: none.
   - Catch: the ledger keeps rows that flip by 2-5 trims or 100-250 mm under
     any change that moves a polygon by a fraction of a mm2. The next re-seed will
     list "wrong-way" rows like these again.
2. **Width bracket in the tripwire (tool only, new lane).**
   - Delivers: route rows whose baseline is the median of three widths
     (pro, +-0.1 mm), so a re-seed lists only moves larger than the route's
     own scatter.
   - Cost: about three times the nightly's digitize time on the route
     figures, a ledger schema change, and one re-seed.
   - Catch: three widths may still be too few on MFab, where one lane alone
     spans 250 mm over five widths. It does not touch the engine.
3. **Colour-block entry lane (engine, behind a new OFF flag).**
   - Delivers: possibly 30-60 mm off MFab's needle-up at every width.
   - Cost: one engine lane, a census across the 18 tripwire pairs, a sitting.
   - Catch: one job's evidence. The block's first shape may be chosen by a
     rule (underlay, order of knockouts) that a nearest-entry rule breaks.

**My pick: 2.** The last three re-seed reviews each spent a lane to learn
that a row was route scatter. A bracket answers that before anyone opens a
lane, and it moves no stitch.

## Reproduce

Per arm: `tools.pro_pair.digitize(art, width, garment, extra)` with `{}`,
`{"stage0_scale_relative_grad": False}` or `{"flat_light_text_runs": False}`.
Then `digitizer_core.export.write_dst`, and read that DST back
with `tools.pro_baseline.needle_up` and `pro_pair.pro_counts`. For the
attribution, walk `stitches.iter_machine_commands`'s rule over the plan's
runs. Match each DST lift to the plan transition with the same endpoints
(within 0.11 mm), and group by `run.shape_id` against `result.regions`. Each
digitize took 27-108 s, run one at a time. The pinned test takes about 50 s,
of which 21 s is Gaulke's two-lane stage 0-6 replay.
