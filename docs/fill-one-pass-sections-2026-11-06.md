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

- The 12 gitignored pairs: run `tools.fill_section_cuts` on a machine with the
  client files before quoting a 17-pair figure.
- A seam-aware version of `fill_section_travel.plan` (its one-step lookahead
  and articulation rule, under the seam constraint) is the next step for the
  LC's and the hat's long hops; `_order_for_seams`' `reach` hook is where it
  plugs in. The greedy here has no lookahead, which is exactly what let it
  trade one long hop for two on the hat before the long-hop rule.
- The stage-6 price still cannot see stage 7's burying. The long-hop rule is a
  necessary condition, not the whole truth: a short hop with no later thread
  over it (the beanie's 12 mm one) is a DST cut too.

Tests: `digitizer/tests/test_fill_one_pass_sections.py`.
