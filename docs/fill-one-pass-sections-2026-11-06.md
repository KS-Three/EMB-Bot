# Fill-section cuts on the flipped main, and `fill_one_pass_sections` (2026-11-06)

MASTER_SCOPE defect 6's largest unexplained class is the cut between two
sections of ONE fill: 32 of our 104 in-piece cuts on 2026-10-29, the pro 0 on
all 17 pairs. That figure was taken on 44ecf1cb, before `fill_seam_order`,
`fill_seam_order_priced`, `fill_bridge_cut_exposed` and `knockdown_shorter_walk`
went ON (10-30). This page re-measures it on today's main (5777f91c), on the
pairs a fresh clone has, and builds one switch, OFF, for what is left.

## What a fresh clone can measure

The committed pairs are the five Becker jobs: the pro's files inside
`Embroidery Files.zip` (the same DSTs as `digitizer/testdata/reference/becker_*`),
the art `digitizer/testdata/becker_marine_logo.png`, which `tools.border_census`
falls back to when the customer's file is not mounted. Each is digitized at the
pro's own width and garment through the Studio's request
(`tools.pro_pair.digitize`, `tools.flip_sheet_renders.fixture_files`), stages
0-4 once per job, and `plan_stitches` replayed from the pickle per arm, as the
10-29 doc did; the OFF arm's replay is byte-identical to the live run on all
five (DST md5). The beanie's pro file is a PES (no DST was supplied), read as
the 10-30 sheet read it.

**The other 12 pairs (MFab, Drone, ProSeal, Gaulke, Bridge, Fremont, Tires) are
n/a here**: their art is a gitignored client file, so nothing below estimates
them. The 32 is therefore NOT re-measured as a 17-pair figure; the Becker five
carried 9 of those 32 on 10-29.

One reader on both DSTs, the 10-29 set: `tools.sequence_pro` (cuts, cuts inside
one piece), `tools.inpiece_cuts` (the cause of each in-piece cut; the pro's by
stitch character), `tools.travel_cover` (exposed travel mm),
`tools.flip_sheet_renders.bare_by_band` (bare thread mm at 0.20, gate 3), the
DST md5 and plan CPU (`process_time`, best of two warm replays). `python -m
tools.fill_section_cuts --arm 'one_pass={"fill_one_pass_sections": true}'
--repeat 2` reproduces every row (`PRO_PARITY_ROOT` at the unpacked zip).

## Step 1: fill-section cuts are not gone on the flipped main

| job | pro cuts | ours | in a piece, ours / pro | **fill-section (pro 0)** | exposed mm | bare mm @0.20 | the field |
|---|---|---|---|---|---|---|---|
| becker_hat_large | 9 | 11 | 2 / 1 | **1** | 23.1 | 0.10 | `Sb7019eaf` |
| becker_lc_large | 11 | 14 | 5 / 2 | **3** | 31.1 | 0.40 | `Sb59612cb` |
| becker_hat_small | 10 | 11 | 4 / 2 | **1** | 21.7 | 4.61 | `S1c041c47` |
| becker_chest_small | 11 | 11 | 4 / 2 | **1** | 21.3 | 4.82 | `S1c041c47` |
| becker_beanie | 4 | 14 | 6 / 0 | **3** | 38.6 | 3.72 | `S51503c0c` |
| **Becker five** | **45** | **61** | **21 / 7** | **9** | **135.8** | **13.65** | |

The other in-piece cuts are `satin_split` (12), the 10-27 class, out of scope
here. So the flips of 10-30 did not remove the fill-section class; every one
of the nine is in the white field under "BECKER".

## Step 2: what makes them, read on the beanie and the LC

`_plan_sections` and `_order_for_seams` were spied on both fields
(`fill_section_travel` is OFF on main, so the section planner never runs there;
seam order does, priced). Renders of each section order with every hop drawn
(green sewn, red cut) are in `docs/renders/fill-one-pass-sections-2026-11-06/`.

- **The cuts are at the forks.** The field is a body with lobes hanging from it
  (under the "B", the two tails). `fill_seam_order` lays every section one way
  across the rows and starts a section only once its upstream neighbours are
  sewn, so the body sews first, then one lobe to its bottom -- and the other
  lobe is then walled off behind finished fill. The hop to it crosses finished
  fill or bare cloth; `fill_bridge_cut_exposed` cuts it. The beanie's three DST
  cuts are hops of 40, 12 and 68 mm; the LC's 44, 89 and 44; the hat's one is
  87 mm; the small jobs' one is 49 mm. The pro's way across is to run through
  the lobe still to come.
- **Stage 6 counts far more cuts than the DST carries.** Seam order's own order
  prices at 8 cuts on the beanie's field and 9 on the hat's; the DSTs carry 3
  and 1. `stage7_sequence._bury_trims_under_later` (ON since 10-21) sews a cut
  hop needle-down where later thread -- the field's own later rows, the letters
  on top -- buries it, never one past `machine.LINK_MAX_GAP_MM` (40 mm). What
  survives to the DST is the long walled hop. A stage-6 gate of "no more cuts"
  cannot see that: the first build of the switch cut the hat's field 9 -> 7 in
  stage 6 and the DST went 1 -> 2 (the two it kept were long hops; the chord's
  short ones were under the letters), and chest small 1 -> 3 the same way.
- **`fill_section_travel`'s hidden route could not cross a seam as built.** Its
  raster proposes the shortest route, which along a seam runs on the column
  just sewn, and its own exposure test then refuses it (2.0 mm on finished fill
  against a two-row allowance, 0.8 mm). The fixture in
  `tests/test_fill_one_pass_sections.py` loses its lobe-to-lobe hop that way.
- **Seam order's other progression is not the answer.** Bottom-up on the beanie
  prices at 2-3 cuts but 6 flips; the lay rule (`fill_seam_order_priced`) is
  right to refuse it. The unconstrained section planner (`fill_section_travel.plan`,
  "near") reaches 0 cuts on the beanie's field with 22 seam faults: the render
  is in the folder above, for what seam order is buying.
- **`knockdown._stay_down`** (step 3 of the brief): no route under later rows
  was visible on a Becker job; the beanie's knockdown is 3 sections sewn once
  with no lift inside it. Nothing built there.

## The switch: `cfg.fill_one_pass_sections` (OFF)

- Seam order's progression is re-planned with `_order_for_seams`' new `reach`:
  among the sections free to go, one the needle reaches hidden -- over unsewn
  ground (`travel_path`) or under rows still to come
  (`fill_section_travel.bridge`) -- goes before the nearest. The progression and
  the seam rule are untouched; the lay is read first and `_score_hidden_free`
  settles a tie, exactly as `fill_seam_order_priced` does.
- Where the re-plan is taken, the fill phase sews those hidden routes
  (`_hide_bridge`, fill only; underlay and `_plan_sections` stay
  `fill_section_travel`'s). A shape the re-plan leaves alone sews exactly as
  without the switch: that is what makes four of the five jobs byte-identical.
- Under the switch the hidden route's ground leaves out the fill already laid,
  except within one travel stitch of either end, and the route may lie on it up
  to that same tolerance -- `travel_path`'s own yardstick for a bridge that does
  not show. Nothing else in `fill_section_travel` moves; its arms are
  byte-identical (its tests pass unchanged).
- **Gate** (`_one_pass_sections`): the re-plan is kept only if it has FEWER
  hops past `LINK_MAX_GAP_MM` than seam order's own order (the cuts stage 7
  can never sew down), cuts no more in all, lays no more thread on finished
  fill, and is cheaper with the hidden travel free. A field whose incoming
  order has no hop past that length is left alone before anything is priced.
- No new constant: `travel_path`'s length budget, `_score`'s two rates,
  `_EXPOSED_TOLERANCE_MM`, chaining's `LINK_MAX_GAP_MM`, all read, none moved.
- Read inside `plan_stitches` only (`one_pass_scope`); `shape_memo` carries the
  ContextVar; `tests/conftest.py` PRE_FLIP and `tests/engine_2026_10_27.json`
  pin it False.

## Before | after, the Becker five (OFF = main 5777f91c)

| job | cuts OFF -> ON | fill-section OFF -> ON | stitches | exposed mm | bare mm @0.20 | plan CPU s | DST |
|---|---|---|---|---|---|---|---|
| becker_hat_large | 11 -> 11 | 1 -> 1 | 16,262 | 23.1 -> 23.1 | 0.10 -> 0.10 | 8.5 -> 12.0 | byte-identical |
| becker_lc_large | 14 -> 14 | 3 -> 3 | 14,830 | 31.1 -> 31.1 | 0.40 -> 0.40 | 9.3 -> 13.0 | byte-identical |
| becker_hat_small | 11 -> 11 | 1 -> 1 | 10,541 | 21.7 -> 21.7 | 4.61 -> 4.61 | 6.8 -> 8.7 | byte-identical |
| becker_chest_small | 11 -> 11 | 1 -> 1 | 10,309 | 21.3 -> 21.3 | 4.82 -> 4.82 | 6.2 -> 8.5 | byte-identical |
| **becker_beanie** | **14 -> 13** | **3 -> 2** | 13,862 -> 13,747 | 38.6 -> 38.6 | 3.72 -> 3.72 | 7.7 -> 10.8 | moved, 377 points |
| **Becker five** | **61 -> 60** (pro 45) | **9 -> 8** (pro 0) | 65,804 -> 65,689 | 135.8 -> 135.8 | 13.65 -> 13.65 | 38.5 -> 53.0 (+38%) | |

- **What moved:** the beanie's field `S51503c0c`. Its 68 mm walled hop is gone:
  the re-plan reaches the far lobe through rows still to come, 115 stitches
  fewer in all (the hidden route replaces a longer walk), exposed travel and
  bare thread unchanged to the tenth. Its 40 mm and 12 mm cuts remain: the 12
  mm one is under the bury limit but has no later thread over it, and the
  re-plan found no order without the 40.
- **What did not:** the LC's three (44, 89, 44 mm) and the hat's 87 mm hop.
  The greedy reach-first found no seam-respecting order with fewer long hops
  on those fields (the hat's re-plan traded one for two and was refused; the
  LC's removed only cuts stage 7 was burying, and was refused by the long-hop
  rule). So they sew byte-identically.
- **Gate 3:** bare thread at 0.20 mm equal on every job; so at 0.25 and 0.30.
- **CPU:** plan CPU +38% on the five (38.5 -> 53.0 s), all of it the pricing with hidden
  routing on the fields that do have a long hop, whether or not the re-plan is
  taken. Stages 0-4 are untouched.
- **OFF arm:** DST md5 equal to main's live run on all five
  (`4a5679f0`, `347cb1f2`, `b41b9f72`, `bcd45933`, `ba01f1fb`).

The two numbers for defect 6 after this, honestly stated: on the committed
subset the class goes 9 -> 8 with the switch ON; 8 of the 9 are the long walled
hop a greedy seam-respecting re-plan cannot remove, and the 12 gitignored pairs
are unmeasured.

## Flip sheet

[`flip-sheet-2026-11-06-fill-one-pass.md`](flip-sheet-2026-11-06-fill-one-pass.md):
the beanie's OFF | ON crops on the window holding the changed points (under
the "C" of BECKER, the field's rows), the pro's panel local only. The other
four rows read "no change (byte-identical DST)". The change is travel under
the field's rows, so the crops look alike: the sheet's row is the proof it
moved nothing visible.

## Not reached

- The 12 gitignored pairs: measured the same evening, see the last section.
- A seam-aware version of `fill_section_travel.plan` (its one-step lookahead
  and articulation rule, under the seam constraint) is the next step for the
  LC's and the hat's long hops; `_order_for_seams`' `reach` hook is where it
  plugs in. The greedy here has no lookahead, which is exactly what let it
  trade one long hop for two on the hat before the long-hop rule.
- The stage-6 price still cannot see stage 7's burying. The long-hop rule is a
  necessary condition, not the whole truth: a short hop with no later thread
  over it (the beanie's 12 mm one) is a DST cut too.

Tests: `digitizer/tests/test_fill_one_pass_sections.py`.

## 2026-11-06 (evening): all 17 pairs, on Kent's laptop

The 12 gitignored pairs measured where the client files are, plus the Becker
five again from the customer's art, so all 17 rows come from one machine and
one reader.

- **Engine:** #1271's head 4aaee9ef (main 15cde8de plus the switch). Stages 0-4
  once per job, pickled; `plan_stitches` replayed per arm, plan CPU the best of
  two (`python -m tools.fill_section_cuts --slugs <job> --arm
  'one_pass={"fill_one_pass_sections": true}' --repeat 2`).
- **One job at a time** under the shared CPU slot.
- **rembg:** pointed at the primary checkout's venv, so MFab and Tires took the
  product's route.
- **Becker art:** the customer PNG this time, not the committed crop. So
  Becker LC's figures differ from the table above (12 cuts and 1 fill-section
  cut here, 14 and 3 there).
- **OFF md5:** each pickle's plan was also replayed on a clean checkout of
  origin/main, both 15cde8de and today's 59545716. The OFF arm's DST matched
  both on all 17 jobs.

Cuts and in-piece cuts are `sequence_pro` on both DSTs. Fill-section cuts are
`inpiece_cuts` (pro 0 on every job). Exposed mm is `travel_cover`, bare mm is
`bare_by_band` at 0.20.

| job | pro cuts | cuts OFF -> ON | in a piece, ours / pro | **fill-section OFF -> ON** | exposed mm | bare mm @0.20 | plan CPU s | ON DST |
|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 9 | 11 -> 11 | 2 / 1 | 1 -> 1 | 23.1 | 0.10 | 9.8 -> 14.0 | byte-identical |
| becker_lc_large | 11 | 12 -> 12 | 3 / 2 | 1 -> 1 | 31.1 | 0.40 | 10.0 -> 10.5 | byte-identical |
| becker_hat_small | 10 | 11 -> 11 | 4 / 2 | 1 -> 1 | 21.7 | 4.61 | 7.1 -> 9.6 | byte-identical |
| becker_chest_small | 11 | 11 -> 11 | 4 / 2 | 1 -> 1 | 21.3 | 4.82 | 6.7 -> 9.6 | byte-identical |
| **becker_beanie** | 4 (PES) | **14 -> 13** | 6 / 0 | **3 -> 2** | 38.6 | 3.72 | 8.1 -> 11.0 | moved, -115 st |
| bridge_hat | 19 | 16 -> 16 | 3 / 3 | 0 -> 0 | 10.5 | 0.00 | 3.9 -> 4.4 | byte-identical |
| bridge_lc | 19 | 17 -> 17 | 2 / 2 | 0 -> 0 | 15.5 | 0.00 | 9.6 -> 8.9 | byte-identical |
| gaulke_roofing_hat | 41 | 30 -> 30 | 3 / 0 | 0 -> 0 | 16.7 | 5.99 | 17.6 -> 16.8 | byte-identical |
| gaulke_roofing_lc | 41 | 23 -> 23 | 1 / 0 | 0 -> 0 | 10.6 | 7.22 | 6.5 -> 6.2 | byte-identical |
| hotel_fremont_hat | 20 | 25 -> 25 | 4 / 1 | 0 -> 0 | 9.1 | 0.00 | 13.5 -> 13.2 | byte-identical |
| hotel_fremont_patch | 20 | 20 -> 20 | 6 / 1 | 0 -> 0 | 12.4 | 0.00 | 10.8 -> 11.4 | byte-identical |
| mfab_hat | 18 | 29 -> 29 | 21 / 3 | 6 -> 6 | 7.9 | 0.00 | 22.6 -> 31.7 | byte-identical |
| mfab_lc | 19 | 22 -> 22 | 15 / 3 | 2 -> 2 | 10.8 | 0.00 | 21.5 -> 22.6 | byte-identical |
| precision_drone | 58 | 86 -> 86 | 14 / 20 | 9 -> 9 | 22.0 | 2.54 | 19.5 -> 20.1 | byte-identical |
| proseal_hat | 53 | 38 -> 38 | 13 / 12 | 5 -> 5 | 13.7 | 1.56 | 11.8 -> 12.5 | byte-identical |
| proseal_beanie | 47 | 28 -> 28 | 7 / 16 | 3 -> 3 | 150.5 | 100.25 | 13.5 -> 14.9 | byte-identical |
| tires_hat_3d | 9 | 3 -> 3 | 0 / 5 | 0 -> 0 | 13.2 | 9.03 | 1.6 -> 1.6 | byte-identical |
| **17 pairs** | **409** | **396 -> 395** | **108 / 73** | **32 -> 31** (pro 0) | **428.7** | **140.24** | **194.1 -> 219.0 (+12.8%)** | 16 identical |

Exposed and bare are equal OFF and ON on every job, to the tenth and the
hundredth, so each cell shows one figure. Bare at 0.25 and 0.30 is equal too.

### Reading it

- **On the flipped main the class is still 32.** It is the same total as 10-29
  on 44ecf1cb, but not the same jobs.
  - Six fields carry 31 of the 32: Drone 9 (`Sb5e7d7ed` 5, `S09963415` 3,
    `S1f7420c4` 1), MFab hat 6 and LC 2 (`Sb1779555` on both, plus
    `Sfbae5fe3`), ProSeal hat 5 (`S9e42b538`), ProSeal beanie 3
    (`Sfa487ac0`), Becker beanie 3.
  - Bridge, Gaulke, Fremont and Tires have none.
- **The switch moves one job of 17.** Becker beanie goes 3 -> 2, the same
  change the five-job table shows. Every other job is byte-identical, so the
  switch's gate refuses the re-plan on all 30 other fill-section cuts.
- **Gate 3 is clear:** bare thread is unchanged on every job, so is exposed
  travel, and total cuts are 396 -> 395.
- **Its cost:** plan CPU +12.8% over the 17 jobs (194 -> 219 s). It is spent on
  fields with a long hop whether the re-plan is taken or not: MFab hat +40%,
  Becker hat large +43%.
- **What the gate can't reach.** These are the forks this page describes: a
  greedy, seam-respecting pick with no lookahead finds no order with fewer
  long hops.
  - Drone's three fields and ProSeal hat's `S9e42b538` (5 cuts) are the
    largest.
  - The next build is the seam-aware planner named under "Not reached": the
    section planner's lookahead and articulation rule, under the seam
    constraint, plugged into `reach`.

### ProSeal beanie's knockdown walks (`knockdown._stay_down`)

This reads the 150.5 mm exposed and 100.25 mm bare thread on the OFF plan.
- **Its 12 walk legs come to 519.3 mm:**
  - 14.6 mm lies under later thread: the design's needle-down lines at a
    0.4 mm thread.
  - 405.4 mm lies on the knockdown's own rows.
  - 99.4 mm lies on neither, which is the job's 100.25 mm bare at 0.20.
  - The longest legs are 151, 94, 89 and 82 mm, against chords of 53, 17, 65
    and 12 mm: `_bridge`'s way round an inset ring.
- **No leg of 10 mm or more has a route under later thread.**
  - The search ran `fill_section_travel.hidden_route` over the design's thread
    footprint (lines grown one row either side), inside the knockdown's reach.
  - It used both budgets: `travel_path`'s and the walk's own length.
  - The ends were docked at 1 mm and at 2 mm; they sit 0.2-1.6 mm off the
    design. No route turned up either way.
  - The letters are separate pieces on bare knit, so every route crosses a
    gap that nothing sews over. The straight chords lie 0-81% under later
    thread, never all of it.
- **So step 3 builds nothing.** The bare reading is in the 0.20 band only
  (0.25 reads 0), so these walks run within a quarter millimetre of a
  knockdown row, which is garment-coloured thread on the garment.
