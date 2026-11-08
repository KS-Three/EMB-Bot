# Fill rows off the axis, at the pro's angle (2026-11-07)

`cfg.extra["fill_angle_pro_offset"]`, **built OFF**. Follows #1337
(`docs/direction-kappa-axis-2026-11-07.md`). That PR found direction kappa
is low because our fills sit on an axis while the pro's sit about 20 deg off
one.

**Verdict: the angle is measured, and the rule built from it helps on
balance, but it fails the done-test.** Mean direction kappa goes from 0.311
to 0.400 over the 18 tripwire jobs. The 95% CI on that change crosses zero,
and three jobs' trims rise by more than 2. My pick is to keep it OFF.

## 1. The pro's fill angle, measured

**Tool:** `python -m tools.fill_angle_pro_census measure|report` (new). Its
`measure` is `tools.tripwire measure` with a spy on stage 7's fill calls.

**Method, per fill shape:**

- The pro's angle is the doubled-angle mean of his cells of type fill
  (`scorecard.cell_stats`) whose centre lies inside our shape inset by 1 mm.
- Both DSTs go through one reader, with translation-only registration.
- **No mirror.** The first cut let registration choose a mirror, and on
  Fremont's near-symmetric field the mirror scored higher (IoU 0.987 against
  0.985). That read the pro as 108 deg when the true value is 72.
- The frame is the stitch frame: mm, y-down. Inputs: main dd752bb1, shipped
  defaults, Kent's laptop.

**Population:** the 27 shapes with at least 2 pro fill cells, on 17 jobs.
Tires has no usable fill.

| figure | n | median | p25 | p75 | range |
|---|---|---|---|---|---|
| \|pro offset from nearest of 0/90\| | 27 | **20.7** | 18.0 | 23.4 | 5.9 to 39.1 |
| \|ours offset from nearest of 0/90\| | 27 | 0.4 | 0.1 | 12.6 | 0.0 to 45.0 |
| \|pro minus the shape's principal axis\| | 27 | 23.4 | 20.5 | 71.6 | 5.5 to 89.6 |
| \|pro minus ours\| | 27 | 39.1 | 20.4 | 68.4 | 7.9 to 87.6 |
| \|pro offset\| on each job's largest fill | 17 | 20.4 | 13.5 | 21.8 | 8.4 to 32.8 |

**The pro never sits on an axis, and ours almost always does.** The
magnitude holds well across jobs. The sign does not:

- **+ (rows fall to the right):** 12 of the 17 largest fills. That covers
  all five Becker files (+20.1 to +20.5; beanie +10.2), both MFab files
  (+21.6, +21.8), Golden Tee (+21.7), Drone (+8.4), Fremont patch (+11.1),
  Gaulke beanie (+22.8) and Gaulke hat (+13.5 off 90).
- **- :** all three To a T files (-23.4, -23.4, -32.8), Fremont hat (-18.0
  off 90) and Gaulke LC (-13.1).

So the same Fremont art goes + on the patch and - on the hat.

The pro's figure is not our axis plus an offset. Our axis is often the wrong
one: we sew MFab at 90 and he sews it at 21.6, and we sew To a T beanie at 90
and he sews it at 156.6. Neither is it the principal axis plus an offset:
the p75 of that figure is 71.6.

## 2. The rule, chosen offline before building

Each candidate was scored against the pro's cells inside the 27 shapes. The
score is cell-weighted (1 - |diff|/90), shown here as 2r - 1. This is a
selection aid only, not a reported figure.

| candidate (offset 20) | score |
|---|---|
| ours (status quo) | +0.201 |
| our axis + 20 | +0.170 |
| principal axis + 20 | +0.474 |
| nearest axis of the principal axis + 20 | +0.477 |
| **one fixed 20 for every fill** | **+0.492** |
| fewer columns of +20 / -20 (offline only) | +0.596 |
| fewest columns of the 4 off-axis angles | -0.025 |
| oracle: the better of 20 / 110 | +0.567 |

**Built: one fixed angle, `machine.FILL_ANGLE_PRO_DEG = 20.0`.** It is the
median above, with the majority sign.

- **Where it applies:** every fill-tier shape that goes through stage 7's
  `_fill_angle_for`.
- **What outranks it:** only the review screen's own `fill_angle_deg` and the
  global `cfg.fill_angle_deg`.
- **What it overrides:** the lettering house angle that the text tagger
  writes into the same meta slot, and the design angle. Those are the axis
  sources the pro disagrees with.
- **Stage 5:** `_comp_axis` and `seam_row_angles` read the same rule, so
  directional comp and `overlap_by_angle` (both OFF) follow the rows.
- **Not touched:** fills sewn by the gradient lane's blend tier. Drone's
  800 mm2 fill still sews at 101.

**Fewest columns does not predict the pro.** He sews MFab's field at 21.6,
which costs 77 columns against 37 at our 90.

**The +/-20 column pick is not robust.** It scored best at 20 but fell below
the fixed angle at 15 (+0.458 against +0.490). It was not built.

## 3. OFF vs ON, tripwire measure path

Shipped defaults, one job at a time. `--no-words` because word cc is not in
this done-test. Direction kappa is chance-corrected, chance 0.5, floor 0.

| job | direction OFF | ON | stitch-type OFF | ON | stitches OFF | ON | trims OFF | ON | hops OFF | ON | needle-up mm OFF | ON |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 0.350 | **0.586** | 0.287 | 0.266 | 16262 | 16547 | 11 | 10 | 14 | 13 | 327.3 | 266.6 |
| becker_lc_large | 0.351 | **0.581** | 0.334 | 0.356 | 14922 | 14955 | 12 | 11 | 15 | 14 | 292.1 | 248.3 |
| becker_hat_small | 0.416 | **0.643** | 0.533 | 0.541 | 10546 | 10530 | 11 | 10 | 16 | 15 | 281.3 | 229.7 |
| becker_chest_small | 0.445 | **0.678** | 0.578 | 0.590 | 10309 | 10294 | 11 | 10 | 16 | 15 | 281.4 | 229.9 |
| becker_beanie | 0.396 | 0.476 | 0.245 | 0.237 | 13864 | 13858 | 14 | 13 | 19 | 18 | 339.4 | 332.9 |
| gaulke_roofing_hat | 0.513 | 0.449 | 0.115 | 0.156 | 7413 | 7439 | 32 | 32 | 45 | 45 | 396.6 | 400.6 |
| gaulke_roofing_lc | 0.511 | 0.468 | 0.286 | 0.348 | 5778 | 5847 | 23 | 22 | 47 | 45 | 316.9 | 272.9 |
| gaulke_roofing_beanie | 0.007 | 0.068 | 0.307 | 0.315 | 7601 | 7617 | 24 | 22 | 48 | 47 | 327.2 | 346.6 |
| hotel_fremont_hat | 0.000 | 0.000 | 0.533 | 0.513 | 15898 | 16004 | 25 | **30** | 175 | 177 | 499.4 | 606.3 |
| hotel_fremont_patch | 0.418 | 0.503 | 0.519 | 0.529 | 14858 | 14955 | 20 | 21 | 175 | 174 | 475.9 | 515.1 |
| mfab_hat | 0.000 | **0.621** | 0.563 | 0.583 | 20801 | 20355 | 16 | 17 | 30 | 34 | 556.2 | 536.5 |
| mfab_lc | 0.000 | **0.634** | 0.585 | 0.572 | 17848 | 17636 | 19 | **23** | 26 | 32 | 389.3 | 560.8 |
| precision_drone | 0.084 | 0.000 | 0.376 | 0.386 | 14769 | 14912 | 86 | **90** | 122 | 128 | 1442.6 | 1468.0 |
| tires_hat_3d | 0.706 | 0.721 | 0.000 | 0.000 | 4544 | 4549 | 3 | 3 | 3 | 3 | 52.7 | 55.2 |
| goldentee_hat | 0.311 | **0.545** | 0.868 | 0.843 | 13515 | 13593 | 39 | 39 | 68 | 70 | 644.6 | 650.4 |
| toat_machine_hat | 0.697 | **0.000** | 0.422 | 0.409 | 18917 | 18756 | 21 | 22 | 28 | 29 | 264.8 | 284.9 |
| toat_machine_beanie | 0.392 | 0.115 | 0.390 | 0.399 | 18339 | 18356 | 19 | 19 | 35 | 35 | 314.6 | 321.8 |
| toat_beanie | 0.000 | 0.106 | 0.388 | 0.376 | 18410 | 18290 | 22 | 20 | 34 | 34 | 240.0 | 314.7 |

**The pooled change, ON minus OFF:**

- 95% CIs come from 10,000 bootstrap resamples (seed 1107).
- The "jobs" CI resamples the 18 jobs. The "artworks" CI resamples the 8
  artworks, because Becker counts as five jobs.

| figure | mean OFF | mean ON | mean change | 95% CI, jobs | 95% CI, artworks | up / down |
|---|---|---|---|---|---|---|
| direction kappa | 0.311 | 0.400 | **+0.089** | [-0.048, +0.218] | [-0.103, +0.281] | 12 / 5 |
| stitch-type kappa | 0.407 | 0.412 | +0.005 | [-0.005, +0.016] | [-0.006, +0.018] | 10 / 7 |
| stitches | 13,589 | 13,583 | -6 | [-83, +61] | [-115, +72] | 11 / 7 |
| trims | 22.67 | 23.00 | +0.33 | [-0.50, +1.33] | [-0.60, +1.92] | 6 / 8 |
| hops | 50.9 | 51.6 | +0.7 | [-0.3, +1.8] | [-0.5, +2.7] | 6 / 8 |
| needle-up mm | 413.5 | 424.5 | +11.1 | [-13.4, +39.8] | [-20.9, +50.9] | 11 / 7 |

## 4. Done-test

- **Pro-angle distribution measured: yes.** See section 1.
- **Per-job direction kappa with a bootstrap CI on the mean: done.** The CI
  crosses zero on both resamplings.
- **No job's trims up by more than 2: FAILS.** Fremont hat +5 (25 to 30),
  MFab LC +4 (19 to 23), Drone +4 (86 to 90). Rows at 20 deg cut these fields
  into more sections than 0 or 90 does.
- **Default-path md5s unchanged: yes.** `python -m tools.default_path_diff
  --base-ref origin/main` reads 5 of 5 identical (plan md5, DST md5,
  stitches, colour changes, DST trims). The OFF arm of the new test is also
  byte-identical to the default on logo_alpha.

## 5. Where the sign costs

On the five jobs where the pro sews `-`, a fixed `+20` is about 40 deg wrong
instead of 20 deg on an axis:

- toat_machine_hat 0.697 to 0.000. Our 135 there had been near his 147.
- toat_machine_beanie 0.392 to 0.115.
- Gaulke hat and Gaulke LC, about -0.05 each.

Fremont hat does not move (0.000 to 0.000). The pro sews it at 72, the
other axis's `-` side.

The magnitude is settled. **What decides the sign and the axis, per design,
is not in any figure measured here.** The same art goes + on the Fremont
patch and - on the Fremont hat.
