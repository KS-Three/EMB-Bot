# Perceptual yardstick vs Kent's eye: pre-registration (2026-11-08)

Kent's ruling, 2026-11-08: "Pre-register, run once", and, once the earlier
renders turned out to be gone, "Re-render 100, then run". This file is
committed and pushed **before any score exists**. The run that follows reads
the instrument as written here, once. Any change to what is below means a
new dated pre-registration, and this run still gets reported.

## The instrument and its settings (the shipped defaults, unchanged)

`tools/yardstick_perceptual.py score` as it is on main `15b0f5a0`
(#1297, #1310, #1314):

| setting | value |
|---|---|
| render scale | `--ppm` 12 px/mm, `--pad-mm` 3, `--max-px` 1024 |
| registration | on (`pairframe.register_pair`) |
| colour | monochrome (no `--colour`) |
| tie rule | `--tie-band` 0.0: equal distances only |
| DreamSim | `--dreamsim-type ensemble` |
| bootstrap | percentile, B = 10,000 over pairs and over designs, seed 20261107 |
| oracles | `--oracles` on (self row and blank canvas, reported beside the kappa) |

## Data

The 100 labelled pro pairs in `docs/eye-pairs-2026-11-01/pro-pair-inputs.json`.
Kent chose a side on 41 of them. Every design is re-rendered on 2026-11-08
with `tools.eye_pairs.pro_pooled_build render`, on each sitting's own tree,
143 designs. The renders from 11-01 and 11-06 no longer exist. The pair list
comes from `from-pro-pooled`. A pair whose render fails is listed with its
reason and left out, never imputed.

## What is read

- **Primary: `dreamsim`.** Cohen's kappa against Kent's picks, with ties in,
  on the 3x3 table, plus the bootstrap 95% interval over pairs.
- **Secondary:** `flip`, `lpips_alex`, `lpips_vgg`, and the pixel control `mse`.
  Each is reported the same way. None of them can carry a claim alone.

**The claim rule, fixed now.** "DreamSim agrees with Kent above chance"
holds only if the primary interval's lower bound is above 0 **and** DreamSim
beats `mse`'s point kappa. A secondary metric clearing its interval is
recorded as a lead for a second labelled sitting, and nothing more. One
interval clearing out of five read at once is not evidence.

No raw agreement share is computed or quoted (ROADMAP gate 4). No flag,
route or default moves on this reading, and no phase marker moves. What it
can license is a proposal to Kent.

## What would invalidate the run

- A render tree that differs from `SITTINGS` in `pro_pooled_build.py`.
- More than 10% of the 100 pairs failing to render. The run is still
  reported, but the reading is marked partial.
- Any setting above changed after a score has been seen.
