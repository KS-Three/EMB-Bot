# heatstitch floor beside ours (2026-11-05)

Measured on main `67319af2` (engine tree `1efc955606d4+4c85679b53e4`): ours is `tools.tripwire measure` at the pro's size (the nightly's own figures, run on Kent's Windows laptop, not the Linux runner the committed ledger was captured on); heatstitch's column is its DST for the same job, read by the same code (`pro_baseline.kappas`) against the same pro file. Stitch-type kappa only, chance floor in brackets (ROADMAP gate 4; no raw agreement). Numbers only: heatstitch's files are third-party and stay in the gitignored `scratch_bench/heatstitch/`; no render of them is committed.

Why: [`free-digitizers-2026-11-04`](free-digitizers-2026-11-04.md) found heatstitch's untuned width rule reaches stitch-type kappa 0.13 (median) against ours 0.38. A classifier change that drops a job's margin toward zero means a rule of thumb is catching up. Re-run on a laptop that holds the files:

    python -m tools.tripwire floor --figures <a measure pass> [--floor-warn 0.05]

heatstitch floor (untuned rule: run < 1 mm, satin <= 7 mm and even, else fill), stitch-type kappa against the pro's file, chance floor in brackets; margin = ours - heatstitch, flagged below 0.05. Flag only, never a failure.

| job | ours | heatstitch | margin | flag |
|---|---|---|---|---|
| becker_hat_large | 0.29 (0.53) | 0.17 (0.56) | +0.12 |  |
| becker_lc_large | 0.33 (0.51) | 0.32 (0.52) | +0.01 | FLAG |
| becker_hat_small | 0.53 (0.50) | 0.47 (0.48) | +0.07 |  |
| becker_chest_small | 0.58 (0.50) | 0.47 (0.48) | +0.11 |  |
| becker_beanie | 0.24 (0.56) | 0.10 (0.50) | +0.14 |  |
| gaulke_roofing_hat | 0.14 (0.84) | 0.22 (0.73) | -0.08 | FLAG |
| gaulke_roofing_lc | 0.29 (0.87) | 0.13 (0.66) | +0.15 |  |
| gaulke_roofing_beanie | 0.31 (0.51) | 0.13 (0.56) | +0.17 |  |
| hotel_fremont_hat | 0.53 (0.43) | 0.00 (0.59) | +0.53 |  |
| hotel_fremont_patch | 0.52 (0.43) | 0.09 (0.61) | +0.42 |  |
| mfab_hat | 0.56 (0.48) | 0.16 (0.46) | +0.41 |  |
| mfab_lc | 0.57 (0.49) | 0.21 (0.45) | +0.36 |  |
| precision_drone | 0.38 (0.50) | 0.00 (0.45) | +0.38 |  |
| tires_hat_3d | 0.00 (0.51) | 0.00 (0.39) | +0.00 | FLAG |
| goldentee_hat | 0.83 (0.62) | 0.25 (0.48) | +0.58 |  |
| toat_machine_hat | 0.32 (0.57) | 0.13 (0.59) | +0.19 |  |
| toat_machine_beanie | 0.38 (0.58) | 0.10 (0.57) | +0.28 |  |
| toat_beanie | 0.40 (0.55) | 0.13 (0.58) | +0.26 |  |

18 of 18 jobs scored; medians: ours 0.38, heatstitch 0.13, margin +0.18; 3 flagged.
