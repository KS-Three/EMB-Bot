# `fill_seam_aware_sections`: seam order planned with lookahead (2026-11-06)

Defect 6. This follows [`fill-one-pass-sections-2026-11-06.md`](fill-one-pass-sections-2026-11-06.md).
On the 17 pairs, `fill_one_pass_sections` took the cuts between two sections
of one fill from 32 to 31; the pro has 0. Kent ruled "Hold, build planner
(Recommended)". This page is that planner, built OFF, with its 17-job
census. **It does not pass the done-test**, and this page says where.

## What the 31 cuts actually are

Spied inside `plan_stitches` on Drone and ProSeal hat (pickles from #1280's
census):

- **Every fill-section cut on both jobs is a short hop, 3-15 mm.**
  - ProSeal hat `S9e42b538`: 6, 13, 15, 9 and 9 mm.
  - Drone `Sb5e7d7ed`: 6, 10, 3, 7 and 8 mm.
  - Drone `S09963415`: 10, 9 and 6 mm.
  - Drone `S1f7420c4`: 13 mm.
- **`fill_one_pass_sections` never re-plans them.** Its gate wants a hop past
  `machine.LINK_MAX_GAP_MM` (40 mm), and none of these is that long. They
  reach the DST because stage 7 finds no later thread to bury them under, not
  because they are long.
- **Priced with the hidden routes, seam order's own order already cuts less.**
  ProSeal hat's field prices at 2 cuts that way, against the 6 it sews in
  stage 6 (5 in the DST). The cuts there are routes `emit` does not sew:
  under the switch they become travel under rows still to come. So the
  baseline is the order as it sews without hidden routes, and seam order's
  own order with its hops hidden is the first candidate.
- **The reach-first pick, freed of the long-hop rule, makes some fields
  worse.** On Drone `S09963415` it walls the needle in, 4 -> 9 stage-6 cuts.
  Lookahead and the articulation rule are what the planner adds for that.

## The switch: `cfg.fill_seam_aware_sections` (OFF)

- **Where it runs:** on any field whose seam order cuts in stage 6.
- **Three candidates, all priced with the hidden travel free
  (`_score_hidden_free`):**
  1. Seam order's own order, its hops hidden.
  2. The reach-first re-plan (`_order_for_seams`' `reach`).
  3. `_seam_aware_chooser`, which keeps seam order's seams and picks among the
     free sections by: reached hidden; then, leaving by its tail, a section
     freed next reached hidden (`fill_section_travel.plan`'s one-step
     lookahead, asked of its `_LOOKAHEAD` best); then not an articulation
     point of the sections still to sew on the seam graph; then nearest.
     Reaches are memoized on (needle, head, sections sewn).
- **Gate.** A candidate is kept only if it:
  - lays no worse (`_seam_faults`);
  - cuts FEWER than the unhidden order;
  - has no more hops past `LINK_MAX_GAP_MM`;
  - lays no more on finished fill;
  - is cheaper with the hidden travel free.
  Where a re-plan is kept, `emit` sews the hidden routes, the same as under
  `fill_one_pass_sections`.
- **No new constant.** It reads `travel_path`'s budget, `_score`'s two rates,
  `_EXPOSED_TOLERANCE_MM`, `LINK_MAX_GAP_MM` and the planner's own work caps
  (`_ROUTABLE_PROBE_LIMIT`, `_LOOKAHEAD`).
- **Wiring:** read inside `plan_stitches` only (`seam_aware_scope`).
  `shape_memo._AMBIENT`, `conftest.PRE_FLIP` and `engine_2026_10_27.json`
  carry it False.
- **Tests:** `digitizer/tests/test_fill_seam_aware_sections.py`.
  - A short fork, where `fill_one_pass_sections` alone leaves the cut, goes
    1 -> 0 cuts. Three lobes go 2 -> 0. The lay is no worse on both.
  - The chooser keeps the seams, prefers a hidden reach over the nearest, and
    sews the dead end last.
  - With the switch OFF, the new code is never reached.

## The 17 pairs, OFF -> ON

**How it was run:**
- **Engine:** b23daa22, which is main 3cbe99a7 plus the switch.
- **Same pickles** as #1280's census (stages 0-4 on 15cde8de), the plan
  replayed per arm, plan CPU the best of two.
- **Command:** `python -m tools.fill_section_cuts --slugs <job> --arm
  'seam_aware={"fill_seam_aware_sections": true}' --repeat 2`, one job at a
  time under the shared CPU slot. MFab and Tires used the primary
  checkout's rembg.
- **OFF md5:** each pickle's plan was also replayed on a clean checkout of
  origin/main 3cbe99a7. The OFF arm's DST matches it on all 17 jobs.

| job | pro cuts | cuts OFF -> ON | **fill-section OFF -> ON** (pro 0) | exposed mm | bare mm @0.20 | plan CPU s | ON DST |
|---|---|---|---|---|---|---|---|
| becker_hat_large | 9 | 11 -> 11 | 1 -> 1 | 23.1 -> 23.1 | 0.10 -> 0.10 | 12.0 -> 112.8 | byte-identical |
| becker_lc_large | 11 | 12 -> 12 | 1 -> 1 | 31.1 -> 31.1 | 0.40 -> 0.40 | 9.7 -> 61.7 | moved, +4 st |
| becker_hat_small | 10 | 11 -> 11 | 1 -> 1 | 21.7 -> 21.7 | 4.61 -> 4.61 | 7.0 -> 53.4 | moved, -2 st |
| becker_chest_small | 11 | 11 -> 11 | 1 -> 1 | 21.3 -> 21.3 | 4.82 -> 4.82 | 7.2 -> 54.2 | moved, -2 st |
| **becker_beanie** | 4 (PES) | **14 -> 13** | **3 -> 2** | 38.6 -> 38.6 | 3.72 -> 3.72 | 9.4 -> 31.5 | moved, -130 st |
| bridge_hat | 19 | 16 -> 16 | 0 -> 0 | 10.5 -> 10.5 | 0.00 -> 0.00 | 3.1 -> 3.1 | byte-identical |
| bridge_lc | 19 | 17 -> 17 | 0 -> 0 | 15.5 -> 15.5 | 0.00 -> 0.00 | 7.5 -> 7.4 | byte-identical |
| gaulke_roofing_hat | 41 | 30 -> 30 | 0 -> 0 | 16.7 -> 16.7 | 5.99 -> 5.99 | 15.8 -> 15.3 | byte-identical |
| gaulke_roofing_lc | 41 | 23 -> 23 | 0 -> 0 | 10.6 -> 10.6 | 7.22 -> 7.22 | 16.2 -> 16.2 | byte-identical |
| hotel_fremont_hat | 20 | 25 -> 25 | 0 -> 0 | 9.1 -> 9.1 | 0.00 -> 0.00 | 30.4 -> 29.9 | byte-identical |
| hotel_fremont_patch | 20 | 20 -> 20 | 0 -> 0 | 12.4 -> 12.4 | 0.00 -> 0.00 | 29.1 -> 29.3 | byte-identical |
| **mfab_hat** | 18 | **29 -> 28** | **6 -> 4** | 7.9 -> 6.7 | 0.00 -> 0.00 | 30.3 -> 137.8 | moved, +128 st |
| **mfab_lc** | 19 | **22 -> 24** | **2 -> 4** | **10.8 -> 19.8** | 0.00 -> 0.00 | 32.4 -> 71.8 | moved, +203 st |
| precision_drone | 58 | 86 -> 86 | 9 -> 9 | 22.0 -> 22.8 | 2.54 -> 2.54 | 22.7 -> 226.1 | moved, +8 st |
| **proseal_hat** | 53 | **38 -> 35** | **5 -> 2** | 13.7 -> 14.6 | 1.56 -> 1.56 | 11.0 -> 14.1 | moved, +11 st |
| **proseal_beanie** | 47 | **28 -> 26** | **3 -> 1** | 150.5 -> 147.6 | 100.25 -> 100.25 | 16.2 -> 23.2 | moved, +49 st |
| tires_hat_3d | 9 | 3 -> 3 | 0 -> 0 | 13.2 -> 13.2 | 9.03 -> 9.03 | 4.5 -> 4.5 | byte-identical |
| **17 pairs** | **409** | **396 -> 391** | **32 -> 26** | **428.7 -> 435.3** | **140.24 -> 140.24** | **264.5 -> 892.3 (x3.4)** | 9 moved |

Cuts inside one piece go 108 -> 104 (pro 73). Plan CPU here is higher on the
OFF arm than in #1280's census (264 against 194 s): the laptop was more
loaded.

## Reading it

- **Gains:**
  - ProSeal hat 5 -> 2 fill-section cuts, 3 fewer cuts in all.
  - ProSeal beanie 3 -> 1, 2 fewer.
  - MFab hat 6 -> 4, 1 fewer in all: it gains one satin-to-fill and one
    shape-to-shape cut, but its exposed travel goes down.
  - Becker beanie 3 -> 2: the same 68 mm hop `fill_one_pass_sections`
    removes.
- **Done-test, against the brief's gate:**
  - Fill-section cuts down: yes, 32 -> 26.
  - Total cuts not up: yes in total (396 -> 391), but **not on MFab LC**
    (22 -> 24).
  - Exposed travel not up: **no**, 428.7 -> 435.3 mm.
    - MFab LC: +9.0 mm, its two new fill-section cuts and the travel beside
      them.
    - ProSeal hat: +0.9 mm.
    - Drone: +0.8 mm.
  - Bare thread at 0.20 not up: yes, equal on every job, to the hundredth.
  - OFF byte-identical to main: yes, all 17.
- **Why MFab LC goes the wrong way.** Stage 6 priced its field as fewer cuts.
  The DST carries more, because stage 6 cannot see what stage 7 buries:
  - The orders seam order sews leave short hops that stage 7 sews down under
    later thread.
  - The re-plan moves the field's exits.
  - The long-hop rule is the only proxy for stage 7, and it does not see
    this.
  - The same blind spot is why Drone moves (+8 stitches, +0.8 mm exposed)
    for no cut. Its stage-6 cuts that the re-plans remove were the ones
    stage 7 was already burying.
- **CPU, the other cost:**
  - x3.4 on the plan over the 17 jobs.
  - x9 on Becker hat large, which does not move at all: the chooser's
    reaches on fields that cut only short, buried hops.
  - x10 on Drone.
  - The work caps bound it, but they don't bring it near
    `fill_one_pass_sections`' +13%.

## Verdict

Measured negative for a flip as built. The planner reaches the short hops,
with -6 fill-section cuts and -5 cuts in all. But it fails "exposed not up"
and, on MFab LC, "cuts not up", and it triples plan CPU. What it lacks is a
stage-7 view: which stage-6 cuts the bury rule will sew down anyway.

The next step, if any, is to price the re-plan on what reaches the DST:
- run `stage7_sequence._bury_trims_under_later`'s test inside the price, or
  replay stage 7 on the shape;
- only that removes both MFab LC's regression and the CPU spent on fields
  whose cuts are already buried.

## Renders

OFF | ON sew paths (`tools.sequence_pro.render`: needle-up moves in red,
visits numbered) for the nine jobs whose DST moved are in
`pro_renders/fill-seam-aware-2026-11-06/`.
They are gitignored and local to Kent's laptop, `<job>__main.png` beside
`<job>__seam_aware.png`.
