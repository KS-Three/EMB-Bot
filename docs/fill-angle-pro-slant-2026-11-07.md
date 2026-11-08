# Fill slant per shape, with a trims guard (2026-11-07)

`cfg.extra["fill_angle_pro_slant"]`, **built OFF**. Follows #1346
(`docs/fill-angle-pro-offset-2026-11-07.md`). That PR measured the pro's fill
rows at a median 20.7 deg off the nearest axis and built
`fill_angle_pro_offset`, a fixed +20 on every fill. It gained direction
kappa, but its CI crossed zero, three jobs gained 4-5 trims, and To a T
machine hat fell from 0.697 to 0. Its suggested next step was to choose the
sign per design.

**Verdict:**

- **The sign is not predictable from anything we read.** Six candidate
  signals all score at or below "always +" when the art is left out.
- **The trims guard is what pays.** Each shape takes +20, else -20, only if
  the angle does not cut the shape into many more fill columns than OFF does.
  Otherwise the shape keeps its OFF angle.
- **Result:** mean direction kappa goes from 0.311 to 0.395 (+0.084). Both
  95% CIs exclude zero. No job's trims rise by more than 1, and To a T
  machine hat stays at 0.697.

## 1. Can the sign be predicted? No

**Tool:** `python -m tools.fill_angle_slant_signals RUNS` (new). RUNS is an
OFF `tools.fill_angle_pro_census measure` directory.

**Truth:** the sign of the pro's offset on each job's largest fill with at
least 2 pro fill cells. That gives 17 jobs; tires has none.

**Signals.** Each is read from inputs a digitize already has:

| signal | what it reads |
|---|---|
| `art` | edge slant of the artwork (Sobel) |
| `satin` | slant of our own satin crossings |
| `ourfill` | slant of our own fill rows |
| `pca_off` | which side of the nearest axis the shape's principal axis falls |
| `edges` | length-weighted slant of the shape's boundary |
| `cols` | whether +20 or -20 cuts the shape into fewer columns |

**Scoring.** Each signal becomes the rule "- if d·v < -t, else +". The
direction d and the threshold t are fit on the training jobs, then scored on
the held-out job. Ties keep the larger t, which stays nearer "always +".

Two leave-out schemes:

- **Leave one job out.**
- **Leave one artwork out.** This is the honest one: the five Becker jobs
  share art, and so do the three To a T jobs.

Run on main 0b870eb8, shipped defaults, Kent's laptop:

| signal | leave-one-job-out | leave-one-artwork-out |
|---|---|---|
| always + (the bar) | 11 / 17 | 11 / 17 |
| `art` | 13 | 10 |
| `satin` | 11 | 11 |
| `ourfill` | 9 | 10 |
| `pca_off` | 9 | 3 |
| `edges` | 13 | 11 |
| `cols` | 11 | 9 |

`art` reaches 13 only by learning the To a T art from its two sibling jobs.
With the artwork held out it falls to 10.

**The case nothing can explain:** the same Fremont art is - on the hat
(72 deg) and + on the patch (11 deg), on near-identical field polygons. Every
signal reads the two the same.

**A lead, not built.** On the 9 secondary fills that touch a design's largest
fill, the pro used the opposite sign 7 times. That looks like the
"contrast neighbouring fills" habit. But those shapes hold only 2-12 pro
cells each, and the read was made in-sample, so it is a lead for a future
lane and nothing more.

## 2. The rule

Per fill shape, when no review angle and no global angle is set:

1. **Prior: +20.** That is the majority sign, and on every job's largest
   fill the pro sits near-horizontal (20 or 160) on 15 of 17.
2. **The trims guard.** A candidate is taken only if its monotone column
   count (`_cols_at_angle` at `FILL_ROW_MM`) is at most
   `1.25 × columns at the OFF angle + 2`. The OFF angle is the shape's own,
   the design angle, or stage 6's `best_fill_angle_deg`.
3. **Order:** try +20, then -20 (160). If neither passes, the shape sews at
   its OFF angle.

**Where the guard's numbers come from.** They were read off #1346's OFF/ON
pass. Every in-fill cut that pass added sat on a shape whose column count
grew x1.5 or more:

- MFab LC's field went from 19 to 70 columns and gained 5 cuts.
- Drone's three small fills grew x1.5 to x2.2 and gained 6 cuts.
- Becker's fields grew only x1.0 to x1.12, and each lost a cut.

The constants are `machine.FILL_ANGLE_SLANT_COLS_RATIO` and
`machine.FILL_ANGLE_SLANT_COLS_SLACK`. They were chosen on that one pass:
this is a routing proxy, not a cloth constant.

**Where it is read.** `stage6_fill.pro_offset_fill_angle(cfg, sid, poly=,
base_deg=)` is shared by stage 7's `_fill_angle_for` and by stage 5's
`_comp_axis` and `seam_row_angles`.

**One caveat on stage 5.** Stage 5 prices the guard on the artwork polygon,
while stage 7 prices it on the grown one. On a borderline shape the two can
disagree. That only matters with directional comp or `overlap_by_angle`
on, and both are OFF.

## 3. OFF vs ON, 18 tripwire jobs

**Setup:** `python -m tools.fill_angle_pro_census measure [--slant]`, one job
at a time, main 0b870eb8 plus this branch, Kent's laptop. Direction kappa is
chance-corrected, with chance 0.5 and floor 0.

| job | direction OFF | ON | stitch-type OFF | ON | stitches OFF | ON | trims OFF | ON | needle-up mm OFF | ON |
|---|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 0.350 | 0.586 | 0.287 | 0.266 | 16262 | 16547 | 11 | 10 | 327.3 | 266.6 |
| becker_lc_large | 0.351 | 0.581 | 0.334 | 0.356 | 14922 | 14955 | 12 | 11 | 292.1 | 248.3 |
| becker_hat_small | 0.416 | 0.643 | 0.533 | 0.541 | 10546 | 10530 | 11 | 10 | 281.3 | 229.7 |
| becker_chest_small | 0.445 | 0.678 | 0.578 | 0.590 | 10309 | 10294 | 11 | 10 | 281.4 | 229.9 |
| becker_beanie | 0.396 | 0.476 | 0.245 | 0.237 | 13864 | 13858 | 14 | 13 | 339.4 | 332.9 |
| gaulke_roofing_hat | 0.513 | 0.513 | 0.115 | 0.115 | 7413 | 7413 | 32 | 32 | 396.6 | 396.6 |
| gaulke_roofing_lc | 0.511 | 0.506 | 0.286 | 0.276 | 5778 | 5816 | 23 | 22 | 316.9 | 273.1 |
| gaulke_roofing_beanie | 0.007 | 0.008 | 0.307 | 0.306 | 7601 | 7599 | 24 | 22 | 327.2 | 324.1 |
| hotel_fremont_hat | 0.000 | 0.000 | 0.533 | 0.533 | 15898 | 15901 | 25 | 26 | 499.4 | 505.0 |
| hotel_fremont_patch | 0.418 | 0.418 | 0.519 | 0.519 | 14858 | 14858 | 20 | 20 | 475.9 | 475.9 |
| mfab_hat | 0.000 | 0.000 | 0.563 | 0.591 | 20801 | 20653 | 16 | 16 | 556.2 | 508.2 |
| mfab_lc | 0.000 | 0.000 | 0.585 | 0.583 | 17848 | 17854 | 19 | 19 | 389.3 | 387.1 |
| precision_drone | 0.084 | 0.084 | 0.376 | 0.376 | 14769 | 14769 | 86 | 86 | 1442.6 | 1442.6 |
| tires_hat_3d | 0.706 | 0.721 | 0.000 | 0.000 | 4544 | 4549 | 3 | 3 | 52.7 | 55.2 |
| goldentee_hat | 0.311 | 0.545 | 0.868 | 0.843 | 13515 | 13593 | 39 | 39 | 644.6 | 650.4 |
| toat_machine_hat | 0.697 | **0.697** | 0.422 | 0.422 | 18917 | 18917 | 21 | 21 | 264.8 | 264.8 |
| toat_machine_beanie | 0.392 | **0.654** | 0.390 | 0.395 | 18339 | 18337 | 19 | 19 | 314.6 | 332.5 |
| toat_beanie | 0.000 | 0.000 | 0.388 | 0.388 | 18410 | 18410 | 22 | 22 | 240.0 | 240.0 |

**Mean change (ON minus OFF), with 10,000-resample bootstrap 95% CIs.**
"Jobs" resamples the 18 jobs; "artworks" resamples the 8 artworks.

| figure | mean OFF → ON | CI, jobs | CI, artworks | up / down |
|---|---|---|---|---|
| direction kappa | 0.311 → 0.395 (**+0.084**) | **[+0.035, +0.136]** | **[+0.012, +0.153]** | 9 / 1 |
| stitch-type kappa | +0.000 | [-0.005, +0.006] | [-0.005, +0.004] | 5 / 6 |
| stitches | +14 | [-17, +54] | [-20, +41] | 7 / 6 |
| trims | -0.39 | [-0.72, -0.06] | [-0.77, +0.15] | 1 / 7 |
| needle-up mm | -15.5 | [-27.3, -4.4] | [-30.5, +1.7] | 4 / 9 |

**What the guard picked on each job's largest fill:**

- **Slanted on 7 jobs, all at the pro's sign:** the five Becker files and
  Golden Tee at +20, and To a T machine beanie at -20.
  - To a T machine beanie took -20 only because +20 would have cut its field
    into 8 columns where -20 cuts 1. That is the guard choosing the sign.
- **Kept its OFF angle on 10 jobs:**
  - MFab hat and LC: +20 cuts their field into 77 and 70 columns, against
    37 and 19 OFF.
  - To a T machine hat: the hat that collapsed in #1346.
  - To a T beanie, Gaulke x3, Fremont x2 and Drone.

**Against #1346's fixed +20, over the same 18 jobs:**

| | fixed +20 (#1346) | this rule |
|---|---|---|
| mean direction kappa gain | +0.089 | +0.084 |
| CI, jobs | [-0.048, +0.218] | **[+0.035, +0.136]** |
| CI, artworks | [-0.103, +0.281] | **[+0.012, +0.153]** |
| jobs up / down | 12 / 5 | 9 / 1 |
| worst trims change | +5 | **+1** |
| To a T machine hat | 0 | **0.697** |

**What this rule gives up:**

- **MFab's 0 → 0.62.** Its field cannot take a slant without about 3.5x the
  columns.
- **Toat beanie, Gaulke beanie and Drone's small gains.**

What it removes is every loss #1346 had.

## 4. Done-test

- **Sign accuracy, leave-one-out (section 1):** no signal beats "always +"
  (11/17) leave-one-artwork-out. The best are `satin` and `edges` at 11. On
  the largest fills where the guarded rule slants, its sign matches the pro
  on 7 of 7. Its constants were fit to #1346's trims, not to the pro's sign.
- **Mean direction kappa:** +0.084. The CIs are [+0.035, +0.136] by job and
  [+0.012, +0.153] by artwork, so both exclude 0.
- **No job's trims up by more than 2: PASSES.** The maximum is +1, on
  Fremont hat; 7 jobs go down.
- **To a T machine hat not below 0.6: PASSES.** It stays at 0.697.
- **Default-path md5s: unchanged.** `python -m tools.default_path_diff
  --base-ref origin/main` reads 5 of 5 jobs identical, plan and DST md5.
- **Touched tests pass locally:** `test_fill_angle_pro_slant` (8 new),
  `test_fill_angle_pro_offset`, `test_design_angle`, `test_white_fields_fill`
  and `test_machine_wire`, 36 passed.
