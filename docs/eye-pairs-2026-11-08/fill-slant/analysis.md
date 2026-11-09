# fill-slant-1108: analysis (kappa with 95% bootstrap intervals; n beside every figure)

14 live pairs, Kent chose a side on 7. Density held within tolerance on 14 pairs, not on 0.

| metric | tier | better | n scored | n Kent decided | kappa sides only | CI pairs | CI designs | reading | kappa ties in | CI pairs | CI designs | reading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `flow_circvar` | primary | lower | 14 | 7 | -0.62 | [-0.96, +0.00] | [-0.96, +0.00] | n too small (<10) | -0.40 | [-0.64, -0.07] | [-0.59, +0.05] | no evidence either way |
| `long_share` | primary | lower | 14 | 6 | +0.57 | [+0.00, +1.00] | [+0.00, +1.00] | n too small (<10) | +0.33 | [-0.07, +0.66] | [-0.25, +0.67] | no evidence either way |
| `thread_density` | primary | higher | 14 | 7 | -0.40 | [-0.75, +0.00] | [-1.00, +0.00] | n too small (<10) | -0.22 | [-0.49, +0.05] | [-0.52, +0.02] | no evidence either way |
| `trims_per_1000` | primary | lower | 14 | 7 | +0.00 | [+0.00, +0.00] | [+0.00, +0.00] | n too small (<10) | -0.08 | [-0.24, +0.07] | [-0.19, +0.21] | no evidence either way |
| `longest_jump_mm` | secondary | lower | 14 | 7 | +0.13 | [+0.00, +0.46] | [+0.00, +1.00] | n too small (<10) | +0.14 | [-0.15, +0.53] | [-0.18, +0.88] | no evidence either way |
| `jumps_per_1000` | secondary | lower | 14 | 7 | +0.00 | [+0.00, +0.00] | [+0.00, +0.00] | n too small (<10) | -0.11 | [-0.31, +0.09] | [-0.26, +0.26] | no evidence either way |
| `turns_per_100mm` | secondary | lower | 14 | 7 | +0.70 | [+0.00, +1.00] | [+0.00, +1.00] | n too small (<10) | +0.40 | [+0.05, +0.70] | [-0.07, +0.67] | no evidence either way |

**Control `trims_per_1000` replicates: NO.** If no, read nothing else in this table.

## Trims held against trims moved (the separation)

| metric | split | n pairs | n decided | kappa sides only | CI pairs | CI designs | reading | kappa ties in | reading |
|---|---|---|---|---|---|---|---|---|---|
| `flow_circvar` | trims_held | 14 | 7 | -0.62 | [-0.96, +0.00] | [-0.96, +0.00] | n too small (<10) | -0.40 | no evidence either way |
| `flow_circvar` | trims_moved | 0 | 0 | n/a | n/a | n/a | n too small (<10) | n/a | n too small (<10) |
| `long_share` | trims_held | 14 | 6 | +0.57 | [+0.00, +1.00] | [+0.00, +1.00] | n too small (<10) | +0.33 | no evidence either way |
| `long_share` | trims_moved | 0 | 0 | n/a | n/a | n/a | n too small (<10) | n/a | n too small (<10) |
| `thread_density` | trims_held | 14 | 7 | -0.40 | [-0.75, +0.00] | [-1.00, +0.00] | n too small (<10) | -0.22 | no evidence either way |
| `thread_density` | trims_moved | 0 | 0 | n/a | n/a | n/a | n too small (<10) | n/a | n too small (<10) |
| `trims_per_1000` | trims_held | 14 | 7 | +0.00 | [+0.00, +0.00] | [+0.00, +0.00] | n too small (<10) | -0.08 | no evidence either way |
| `trims_per_1000` | trims_moved | 0 | 0 | n/a | n/a | n/a | n too small (<10) | n/a | n too small (<10) |

## Arms that passed the manipulation check, alone

| metric | n pairs | n decided | kappa sides only | CI pairs | CI designs | reading | kappa ties in | reading |
|---|---|---|---|---|---|---|---|---|
| `flow_circvar` | 14 | 7 | -0.62 | [-0.96, +0.00] | [-0.96, +0.00] | n too small (<10) | -0.40 | no evidence either way |
| `long_share` | 14 | 6 | +0.57 | [+0.00, +1.00] | [+0.00, +1.00] | n too small (<10) | +0.33 | no evidence either way |
| `thread_density` | 14 | 7 | -0.40 | [-0.75, +0.00] | [-1.00, +0.00] | n too small (<10) | -0.22 | no evidence either way |
| `trims_per_1000` | 14 | 7 | +0.00 | [+0.00, +0.00] | [+0.00, +0.00] | n too small (<10) | -0.08 | no evidence either way |

## Population A: distance to the pro's file (cuts, hops, needle-up mm)

Distance = |ours - pro|, lower is closer; cost = the plain count, lower is better, no pro in it. Read over all live pairs, then per stratum (`trims` is the control arm).

| pairs | metric | reading | n scored | n decided | kappa sides only | CI pairs | CI designs | reading | kappa ties in | reading | pairs scoring his pick farther from the pro |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all (14) | `cuts` | distance | 14 | 4 | +0.00 | [+0.00, +0.00] | n/a | n too small (<10) | +0.19 | no evidence either way | 1 |
| all (14) | `cuts` | cost | 14 | 4 | +0.00 | [+0.00, +0.00] | n/a | n too small (<10) | -0.21 | no evidence either way | - |
| all (14) | `hops` | distance | 14 | 4 | +0.00 | [+0.00, +0.00] | n/a | n too small (<10) | -0.27 | below chance | 4 |
| all (14) | `hops` | cost | 14 | 4 | +0.00 | [+0.00, +0.00] | n/a | n too small (<10) | -0.27 | below chance | - |
| all (14) | `needle_up_mm` | distance | 14 | 7 | -0.24 | [-0.52, +0.00] | [-1.00, +0.00] | n too small (<10) | -0.02 | no evidence either way | 3 |
| all (14) | `needle_up_mm` | cost | 14 | 7 | +0.13 | [+0.00, +0.46] | [+0.00, +1.00] | n too small (<10) | -0.01 | no evidence either way | - |
| fill (14) | `cuts` | distance | 14 | 4 | +0.00 | [+0.00, +0.00] | n/a | n too small (<10) | +0.19 | no evidence either way | 1 |
| fill (14) | `cuts` | cost | 14 | 4 | +0.00 | [+0.00, +0.00] | n/a | n too small (<10) | -0.21 | no evidence either way | - |
| fill (14) | `hops` | distance | 14 | 4 | +0.00 | [+0.00, +0.00] | n/a | n too small (<10) | -0.27 | below chance | 4 |
| fill (14) | `hops` | cost | 14 | 4 | +0.00 | [+0.00, +0.00] | n/a | n too small (<10) | -0.27 | below chance | - |
| fill (14) | `needle_up_mm` | distance | 14 | 7 | -0.24 | [-0.52, +0.00] | [-1.00, +0.00] | n too small (<10) | -0.02 | no evidence either way | 3 |
| fill (14) | `needle_up_mm` | cost | 14 | 7 | +0.13 | [+0.00, +0.46] | [+0.00, +1.00] | n too small (<10) | -0.01 | no evidence either way | - |

## Did the pre-registration predict his eye?

Expected picks against his, over 14 pairs: kappa sides only -0.69 [-0.96, +0.00] (designs [-1.00, +0.00]), n too small (<10); ties in -0.50 [-0.71, -0.19] (designs [-0.66, -0.05]), below chance.

## Controls (counts of his own answers)

- identical pairs called a tie: 3 of 4
- repeats answered differently: 0 of 4
- sides picked: 5 left, 7 right (a lopsided count is a side habit)
