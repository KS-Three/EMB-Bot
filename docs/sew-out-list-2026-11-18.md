# Sew-out list: every open gate-1 question, grouped by what to sew (2026-11-18)

Doc only. No engine code, flag or constant changed. Compiled from the write-ups named in
each row; every number below carries its source. Where a source did not say, the cell says
"not stated". This is a worklist for the machine, not a decision: ROADMAP gate 1 stays a
standing refusal (DOCTRINE "The sew-out is accepted as-is", 2026-08-21), and nothing here
becomes a scheduled to-do.

**Already on a card, NOT repeated here.** The existing cards stay the place to sew these:
[`docs/sewout-card-2026-07-31.md`](sewout-card-2026-07-31.md) (blocks 1-6 built, block 7
float clearance drafted, not built),
[`docs/sewout/card-v8-2026-11-01/README.md`](sewout/card-v8-2026-11-01/README.md)
(cut-every-jump, bold factor and halo arms on Hotel Fremont, Enthusiast and "Fritsch's
Stitches"), card v7 beside it, and the other `docs/sewout/card-*` folders. MASTER_SCOPE items
33 (pull comp per rail or total; line 335), 44 (`forbid_gap_mm`, 0.8 mm; line 393) and the
hairline-bean question (item 24, card block 5; line 133) already name their own sew-outs.
Rows 1-9, 12, 14, 15, 16 and 17 below are the questions that have NO card block yet.

## Grouping: what to sew so that one sitting answers the most rows

All of rows 1-8 are `hat_front` jobs except the beanie one, and `hat_front` maps to the
`structured_cap` fabric preset (`digitizer_core/fabrics.py:107`). Sizes are the tripwire
jobs' own (`tools/pro_baseline.JOBS`). Fabric for the cards so far was the structured twill of
card v4 with Kent's Fremont backing (card v8 README); no source names a cloth for the rows
below, so "same as card v8" is a suggestion, not a requirement from any note.

| Sew | Answers rows |
|---|---|
| **MFab hat at 104.9 mm** (`mfab_hat`) | 1, 2, 9 |
| **Toat Machine hat at 89.5 mm** (`toat_machine_hat`) | 6, 7, 10 |
| **Toat beanie at 82.3 mm** (`toat_beanie`) | 5, and 10 if the speed lines are in this design (not confirmed, see row 10) |
| **Precision Drone hat at 62.6 mm** + **Golden Tee hat at 74.9 mm** | 3, 4 (same cause, same constants) |
| **Tires hat at 114.3 mm** (`tires_hat_3d`) | 8, 13 |
| **Hotel Fremont**: the card v8 block F piece already covers the dividers (92.5 mm patch); the same piece, re-cut from today's engine and extended to the upper crest (EST / 1895), answers the small lettering | 11, 12 |

Fewest sittings: MFab hat, Toat Machine hat, Toat beanie, Drone + Golden Tee, Tires. Rows 2, 3
and 4 are all the same constant (the satin pull), so any one of those sews also speaks to the
other two.

## The rows

### 1. MFab hat, bottom line (AND WELDING LLC): black rim over the white keyline
1. **Design, spot.** `mfab_hat`, 104.9 mm, small line at about x 5-100, y 24-34 mm (grader fault
   list, "Every fault" for `L_mfab_hat`, scorecard-2026-11-18).
2. **In doubt.** The satin pull on a ~1 mm keyline beside 1.2-1.4 mm letter strokes.
   `Fabric.pull_comp_mm` = **0.4** for `structured_cap` (`digitizer_core/fabrics.py:47`),
   convention "each rail moves this" (`machine.py:1297`); satin cross floor
   `SATIN_MIN_CROSS_MM` = 0.5 (`machine.py:471`). Measured: black thread covers 17% of the white
   band as a ~0.2 mm rim; the split between pull, the white's gap and thread width was not
   measured.
3. **Sew, look.** The design at 104.9 mm on a hat-front blank, black body then white then
   black. Look at the white keyline edge beside each letter: is there a black rim over it, do
   the 1.3 mm strokes read as letters, are A/N/D counters open. Ruler the stroke and the keyline.
4. **Unlocks.** If the rim is visible and ugly: a column-lane flag that holds the pull off a
   lighter, already-sewn neighbour within ~0.6 mm (the director's option B, not built). If it
   reads fine on cloth: close the fault.
5. **Source.** `docs/mfab-bottom-line-2026-11-18.md` (PR #1673).

### 2. Satin pull: per rail or total?
1. **Design, spot.** Any satin of known drawn width; the MFab letters (row 1) serve.
2. **In doubt.** Browser `pullCompMm` is the total (a 2.5 mm column sews 2.8 mm); digitizer
   `pull_comp_mm` is per rail (3.1 mm for the same column). MASTER_SCOPE item 33 (line 335),
   pinned by `test/engine-service-parity.test.js`.
3. **Sew, look.** Measure the sewn width of one 2.5 mm column from each lane (card block 3,
   wide satin, already carries satin widths: `docs/sewout-card-2026-07-31.md` section 3).
4. **Unlocks.** Which of the two constants is right; rows 1, 3, 4 and 9 depend on the value.
5. **Source.** MASTER_SCOPE item 33.

### 3. Precision Drone: the propeller blade is a thick black slab; the crosshair ticks are below the satin spacing
1. **Design, spot.** `precision_drone`, 62.6 mm, lower-left blade (x -30..-24.5, y -17.9 plan mm)
   and the crosshair ticks (scorecard fault at 22.0, 35.5 mm).
2. **In doubt.** "The slab is the dark edges plus pull-compensation growth"
   (`docs/renders/light-thin-stroke-keep-2026-11-18/README.md`); crosshair line 0.33 mm wide,
   ticks ~0.3 mm wide and protruding 0.3-0.5 mm, against 0.5 mm satin spacing
   (`docs/drone-crosshair-2026-11-18.md`). Same constants as row 1.
3. **Sew, look.** The Drone at 62.6 mm: is the blade a black slab on cloth or does the
   highlight read; do the ticks show at all.
4. **Unlocks.** Whether `light_thin_stroke_keep` (#1660, built OFF; 3 of 35 runs move, one,
   MFab hat, is worse) is worth finishing, or the slab is a pull-comp limit.
5. **Source.** PR #1660; the two docs above.

### 4. Golden Tee swoosh: outer band sews 1.33 mm, the pro's is 1.0 mm
1. **Design, spot.** `goldentee_hat`, 74.9 mm, swoosh outer line at (10, 8) mm.
2. **In doubt.** The 0.3 mm excess "= satin cross floor + pull (gate 1)": `SATIN_MIN_CROSS_MM`
   0.5 (`machine.py:471`) and `pull_comp_mm` 0.4 (`fabrics.py:47`).
3. **Sew, look.** The swoosh at 74.9 mm, measure the outer band on cloth against the 1.0 mm
   the pro's file draws.
4. **Unlocks.** A satin floor or pull for thin bands (gate 1 constants); today no flag exists
   (`satin_hairline_tier` changes nothing here; global `hairline` thins G/T/GOLF edges the pro
   keeps thick).
5. **Source.** `docs/goldentee-swoosh-hairline-2026-11-18.md` (PR #1650).

### 5. Cover hops: the three exposure tolerances (flag ON over gate 1)
1. **Design, spot.** `toat_beanie`, 82.3 mm, the c mouth (the two bars across it are the cure).
2. **In doubt.** `columns._BARE_MAX_MM` 0.3, `_BARE_GROUND_MM` 0.1 (`columns.py:2897-2898`),
   0.2 on the script path. `lettering_columns_cover_hops` = True (`config.py:4536`), flipped by
   Kent as a knowing gate-1 override (memory `cover-hops-2026-11-17`; not a precedent).
3. **Sew, look.** Toat beanie 82.3 mm: any float or trim tail where a hop was cut and the old
   walk was clean. 15 extra trims across the 11 movers; the first suspect on a bad float.
4. **Unlocks.** Keep the three numbers, or retune them; or revert the flag.
5. **Source.** `docs/renders/cover-hops-2026-11-17/README.md`; PR #1636.

### 6. satin_thin_arm_stop: thin arm stops at a node 2x its width
1. **Design, spot.** `toat_machine_hat`, 89.5 mm, the script M, stem tops at about (10.5, 23.5)
   and (20.5, 24.0).
2. **In doubt.** The 2x node rule (`_meets_wider`, median field 1.5-4 mm back from the end);
   `satin_thin_arm_stop` True (`config.py:3611`). Not sewn on cloth. 15 of 35 runs move, 2
   slightly worse (scene_stub, phone_ui_golke).
3. **Sew, look.** The M's stem tops: is the hairline joined, any gap where the arm stops short.
4. **Unlocks.** Keeps the flag ON, or the guard that sews the shape both ways
   (`satin_shape_judged`) gets tightened.
5. **Source.** memory `thin-arm-stop-2026-11-17`; PR #1635.

### 7. stem_wedge_cap: the h stem and its hairline join
1. **Design, spot.** `toat_machine_hat`, 89.5 mm, the script h stem (scorecard pins y 35.0 and
   39.5).
2. **In doubt.** Hairline-join bound `THINNER` = 0.6 (`wedge_cap.py:92`), set between two
   measured ratios (0.49 the h, 0.65 Bridge's link), two examples; `lettering_columns_stem_wedge_cap`
   True (`config.py:4451`). Not sewn on cloth. Only the hat moves of 44 runs (2 stitches).
3. **Sew, look.** The h stem: steps and the seam notch visible or not.
4. **Unlocks.** Keep 0.6, or move it; or revert.
5. **Source.** memory `wedge-cap-2026-11-18`; PR #1668.

### 8. round_dot_ring: a 1.5 mm ring on a 5.7 mm dot
1. **Design, spot.** `tires_hat_3d`, 114.3 mm, the i dot.
2. **In doubt.** `ROUND_DOT_MIN_DIM_MM` = 4.0 (`machine.py:632`) and the 1.5 mm ring on a 5.7 mm
   dot (over the 5.0 mm hat satin ceiling, so it sews tatami); `round_dot_ring` True
   (`config.py:4828`). Kent flipped it over the written caveat that it is untested on cloth.
3. **Sew, look.** The dot at 114.3 mm: round or flat top and bottom with a jutting last stitch.
   (The stroke end at (21.5, 37) is NOT cured; the sew-out is also the place to see whether it
   matters.)
4. **Unlocks.** Keeps the ring size and the 4.0 threshold, or retunes them.
5. **Source.** memory `round-dot-ring-2026-11-18`; PR #1655.

### 9. off_line_mark: MFab's pointed mark at the M's inner V sews as fill
1. **Design, spot.** `mfab_hat`, 104.9 mm, the mark at about (16.0, 21.5) mm and the N at
   (16.0, 27.5).
2. **In doubt.** `OFF_LINE_MAX_GAP_FRAC` = 0.25 and the 50% overlap tests
   (`columns.py:442`); thresholds come from two measurements; `lettering_columns_off_line_mark`
   True (`config.py:4589`). Not sewn on cloth; MFab rendered without `rembg_isolated`.
3. **Sew, look.** The M's inner V: a clean pointed mark, or a fill that mats against the N
   (0.99 mm away).
4. **Unlocks.** Keep ON, or revert; the 0.25 threshold stays on one logo's evidence until then.
5. **Source.** memory `off-line-mark-2026-11-18`; PR #1656.

### 10. To a T speed lines: sew heavy
1. **Design, spot.** The "To a T" speed lines. The slug is not named in the notes I read; the
   Toat jobs are `toat_machine_hat` 89.5 mm and `toat_beanie` 82.3 mm (`JOBS`). Confirm which.
2. **In doubt.** Thread limit versus width: still heavy with `fine_bar_survive` and
   `border_from_outline_hairline_run` ON; "cause not traced" (memory `prime-grader-2026-11-17`).
   `keyline_fragment_drop` keeps them (PR #1643).
3. **Sew, look.** Measure the sewn bar width against the art's.
4. **Unlocks.** Settles whether it is a thread limit (close it, as the Fremont dividers) or a
   tracing fault worth chasing.
5. **Source.** memory `prime-grader-2026-11-17`, `keyline-fragment-2026-11-17`.

### 11. Hotel Fremont EAT | STAY | PLAY dividers: a 1.1 mm satin block where the art has a hairline
1. **Design, spot.** `hotel_fremont_hat`, 92.6 mm, dividers at (40, 37) and (53, 37) mm.
2. **In doubt.** Not a constant: ours and the pro's file sew the same thing (1.1 mm satin, same
   underlay, x 39.2-40.3 against 39.15-40.25). The open question is only whether a 3-pass bean
   would read better on cloth, which is MASTER_SCOPE item 24 / card block 5 (hairline bean,
   `pending sew-out`).
3. **Sew, look.** Card v8 block F (92.5 mm patch) already includes the lower crest with the
   dividers; add them to the "look at" list.
4. **Unlocks.** Nothing new on its own; feeds the hairline-bean decision.
5. **Source.** `docs/fremont-dividers-thread-limit-2026-11-17.md` (PR #1629).

### 12. Hotel Fremont small lettering (EST 1895, EAT STAY PLAY): a 0.5 mm bean cord where the pro sews bold satin
1. **Design, spot.** `hotel_fremont_hat`, 93.3 mm: EST 1895 (y about -14.7..-10.2 plan mm, caps 4.2-4.5 mm
   sewn) and EAT STAY PLAY (y 8.7..13.3, caps 4.6-4.8 mm sewn). Art caps are 1.9 and 2.5 mm, hair strokes
   0.27-0.30 mm; the reset regrows them to the pro's 4.5 / 4.6 mm.
2. **In doubt.** Bean cord versus satin. Ours sews one 0.5 mm bean line (`bean_letter_max_stroke_mm` 0.5)
   down a 0.9-1.2 mm drawn stroke; the pro sews 0.86-1.26 mm bold satin. Satin here would need a 0.6 mm
   counter (`small_text_min_counter_mm` 0.619) and a stroke at the 1.0 mm floor
   (`stage6_satin.PHOTO_MIN_SATIN_WIDTH_MM`, never tuned). Neither is sewn on cloth. Existing OFF flags
   (`small_print_floor`, `lettering_columns_small_stem`) change nothing visible at 93.3 mm.
3. **Sew, look.** Card v8 block F (92.5 mm patch) already sews the lower crest, so the tagline is on the
   card, but from the 11-01 engine: card v8's own README (line 134) says today's hat sews EST and 1895 as
   bean lines, so that piece does not answer it as it stands. Add: re-cut block F from current main and
   include the upper crest (EST / Wisconsin / 1895). Look at: do the bean letters read at arm's length
   against the pro's satin, is the A (no crossbar, no counter) legible as an A, are the 0.6 mm
   counters of E, P, 8, 9 open. No satin arm exists to sew; that is the second step, only if the bean
   reads badly.
4. **Unlocks.** If the bean reads: close the fault as a limit. If not: a built-OFF satin tier for re-set
   letters (small satin counters, gate 1) and the A's crossbar re-spine (the director declined it for now,
   it cannot be judged without cloth).
5. **Source.** `docs/fremont-small-lettering-limit-2026-11-18.md` (PR #1676).

### 13. script_strokes_pull_by_stroke: the pull on a 4.7 mm script pen, into the e and s counters
1. **Design, spot.** `tires_hat_3d`, 114.3 mm, the e counter (76-84, 21-29 mm) and the s counter
   (97-104, 23-34 mm).
2. **In doubt.** The fixed `Fabric.pull_comp_mm` = 0.4 per rail (`fabrics.py`) on a 4.7 mm pen:
   sewn counters 19.3 / 33.2 mm2 against the art's 28.7 / 43.3. The per-stroke fit
   `columns.pull_for_width` (0.07 at 4 mm) is read off the pro's hat files and not sewn on cloth.
3. **Sew, look.** Tires at 114.3 mm, three arms if cloth allows: OFF, `"counter"` (counter-facing
   rails only), `true` (every rail by width). Are the e and s counters open; is the art's edge
   covered, or do slivers of bare cloth show along the outer edges (the preflight counts uncovered
   patches 12 OFF, 17 `"counter"`, 220 `true`).
4. **Unlocks.** Whether the pull may drop by stroke width on script (and which mode), or stays 0.4.
5. **Source.** `docs/tires-script-counters-2026-11-18.md`; the flag's config comment.

### 14. Gaulke hat: counters and mullions at the hat pull
1. **Design, spot.** `gaulke_roofing_hat`, 114.2 mm: G counter (19.5, 35.5), R/E (98, 35.5), the
   ampersand (74, 44), the four-pane window (57, 24.5) mm.
2. **In doubt.** The hat pull `Fabric.pull_comp_mm` = **0.4** per rail (`fabrics.py:47`). Measured
   (`docs/gaulke-fine-detail-2026-11-18.md`): counters sew 0.4-0.5 mm wide against 0.8-0.9 mm
   with pull 0 (art 1.0-1.4 mm); sewn ink 1882 mm2 against the art's 1330 and the professional's
   1709 (same reader; the 0.4 mm drawn thread itself adds about 0.2 mm an edge in all three).
3. **Sew, look.** The design at 114.2 mm: are the G, R, E counters and the ampersand open, do the
   window mullions show, are the letter strokes visibly fatter than the art. Ruler a counter.
4. **Unlocks.** Whether the hat pull is too big for 1.0-1.4 mm counters (a per-feature or
   smaller pull is a gate-1 constant; `pull_comp_by_stroke`, built OFF, does not change this
   design), or the closed counters are the picture and not the cloth.
5. **Source.** `docs/gaulke-fine-detail-2026-11-18.md` (PR #1679).

### 15. Becker MARINE's R counter: how far to hold the bowl's crosses off the counter
1. **Design, spot.** `becker_hat_large` 101.9 mm and the other four Becker placements (76.5-101.9 mm), the R of MARINE,
   its counter about 4 mm wide at 101.9 (art 6.63 mm2).
2. **In doubt.** `lettering_columns_r_bowl` starts every bowl cross `BOWL_INNER_INSET_MM` = **0.5 mm** off the counter's edge
   (`outline_cut.py`). The number is read from the professional's file, not from cloth: his bowl cross is 4.4 mm over a 5.3 mm
   wall and his counter 9.85 mm2 at 101.9 (art 6.63; 4.49 at 76.5). With no inset the crosses, pushed into the counter by
   `Fabric.pull_comp_mm` = 0.4 (`digitizer_core/fabrics.py:47`), left 3.2 mm2 at 101.9 and 1.7 at 76.5; with 0.5 mm ours measure
   6.04 / 3.47 (block_butt alone 4.59 / 2.2).
3. **Sew, look.** The R at 101.9 and 76.5 mm: `block_butt` alone against `block_butt` + `r_bowl` (OFF by default,
   `docs/marine-pro-construction-2026-11-18.md`). Look: is the counter a clear hole of bare cloth, does the R read as an R at
   arm's length, does the thread ridge on the counter's edge show, does 0.5 mm leave a gap between the bowl's crosses and the
   counter edge (a ring of bare cloth around the hole).
4. **Unlocks.** If the counter reads closed or the ring shows: change the one constant (0.3-0.7 mm). If it reads fine:
   `r_bowl` flips on its construction.
5. **Source.** `docs/marine-pro-construction-2026-11-18.md` (#1686), the R rows of sections 3 and 4.

### 16. To a T hat small caps: the A counter and the C-to-L gap at the hat pull (2026-11-19)

Source: `docs/toat-a-and-c-2026-11-19.md`. The A of "To A T" (stroke 1.5 mm) sews a 1.1 mm2 counter where
the art has 2.26 mm2 (a 1.25 mm slit becomes 1.03 mm). The C of "LLC" (stroke 1.0 mm) sews its stems at
2.0-2.1 mm against the art's 1.23 mm and the L-to-C gap at 2.9 mm against 3.8 mm. Cause: the fixed 0.4 mm
per side pull on the hat (gate 1). Sew with the Toat Machine hat at 89.5 mm; the question is whether the
slit and the 2.9 mm gap read on cloth. No flag built.

### 17. Becker MARINE's top band: does the seam under it show on cloth?
1. **Design, spot.** `becker_hat_large` 101.9 mm, the MARINE line (all six letters), and `becker_hat_small` 76.5 mm for the small-size check.
2. **In doubt.** The professional sews a sheared band (near-upright crosses, one stroke deep, overlapping the stem 1.0-1.5 mm) across the
   top of all six letters and it reads as part of the letter in thread. Ours, `lettering_columns_top_slab` + `lettering_columns_e_top_arm`
   (both OFF, `docs/marine-pro-construction-2026-11-18.md` section 5), shows a seam along the band's lower edge in the flat preview
   (`docs/renders/marine-match-2026-11-18/top-slab/`, `e-top-arm/`). Whether that is the preview, which draws every change of direction, or
   a real ridge, is not known; ours butts the band to the stems where his overlaps them.
3. **Sew, look.** Becker hat large at 101.9 mm sewn TWICE, main as it is vs the two flags ON. Look at whether the band's lower edge reads
   as a seam or as part of the letter; at 76.5 mm whether the M's V and the N and E tops hold together (in the preview the M's V breaks
   into fans and the N and E tops come apart).
4. **Unlocks.** The slab family: if the band reads as part of the letter, `top_slab` (with `e_top_arm`, one family) becomes a flip question
   for Kent; if the seam shows, both stay OFF and the overlap (his 1.0-1.5 mm) is the next thing to build.
5. **Source.** `docs/marine-pro-construction-2026-11-18.md` sections 1 (rule 2) and 5 (#1689).

## What this list does not claim

- No row says a sew-out will come out any particular way.
- The 0.2 mm rim in row 1 is a render and raster measurement, not a cloth one.
- Cloth, backing and thread per sitting are not decided by any note; card v8's are the
  nearest precedent.
- If an existing sew-out list or card is extended instead of this page, move the rows, do not
  duplicate them.

## Golden Tee red keyline: sewn at the floor, or under the face (added 2026-11-19)

Art keyline 0.37-0.48 mm; we sew 1.2-1.3 mm satin (floor + pull 0.4), last, over the gold; `keyline_under_face` (built OFF)
puts it under the faces and the red all but disappears; the pro sews GT's at 1.7 mm after the face and has none in GOLF.
Sew the Golden Tee hat both ways (flag OFF and ON) and look: does the red read as a thin outline at arm's length, or as a heavy
band (OFF) / is it missing (ON)? Unlocks: whether a thin red run/bean (about 0.45 mm) is worth building.
Source: `docs/goldentee-red-keyline-2026-11-19.md`.
