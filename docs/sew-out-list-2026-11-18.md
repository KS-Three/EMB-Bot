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
Rows 1-9 below are the questions that have NO card block yet.

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
| **Tires hat at 114.3 mm** (`tires_hat_3d`) | 8, 12 |
| **Hotel Fremont**: the card v8 block F piece already covers the dividers (92.5 mm patch) | 11 |

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

### 12. script_strokes_pull_by_stroke: the pull on a 4.7 mm script pen, into the e and s counters
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

## What this list does not claim

- No row says a sew-out will come out any particular way.
- The 0.2 mm rim in row 1 is a render and raster measurement, not a cloth one.
- Cloth, backing and thread per sitting are not decided by any note; card v8's are the
  nearest precedent.
- If an existing sew-out list or card is extended instead of this page, move the rows, do not
  duplicate them.
