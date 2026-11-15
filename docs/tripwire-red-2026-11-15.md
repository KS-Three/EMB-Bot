# Nightly tripwire red, 2026-11-15: one ruled flip PR (#1533), with a kappa cost Kent was not shown

*(measured 2026-11-15 — failing nightly 43722479841 against the last green 43656572379, both CI; attribution by local arms on Kent's laptop, local-ON against local-OFF only; new ledger from CI capture 43754823644, five passes, main `e739234c`.)*

**Verdict: every wrong-way row is explained by #1533** (`lettering_columns_connectors_edge_walk` + `lettering_columns_corner_fold_apex_side` ON, Kent 2026-11-14, "Flip ON" on each). No row traces to #1554 (the two `group_consistent_*` flips), to a non-flip commit, or to the reader. **But the corner fold's flip cost real pro agreement on two Becker jobs, and no ruling PR showed Kent a kappa figure** (#1512, #1518 and #1533 showed trims, travel mm, stitches and sheets). That trade is put to him before the re-captured ledger merges.

## The red night

Run 43722479841 (scheduled, `main` at `8cfa2fc4`): `25 wrong-way past tolerance, 0 missing, 0 reader moved, 32 right-way past tolerance, 54 within tolerance -> FAIL`. The last green, 43656572379 on `144ef169`, read 111 within tolerance against the same ledger (captured at `66b11432`, #1515). 39 commits lie between the two heads. Four of them flip a default (`git diff 144ef169 8cfa2fc4 -- digitizer/digitizer_core/config.py`):

| PR | flag | Kent's words (PR title/body) |
|---|---|---|
| #1533 | `lettering_columns_connectors_edge_walk` -> ON | "Flip ON" (built in #1512, "Build edge-walk") |
| #1533 | `lettering_columns_corner_fold_apex_side` -> ON | "Flip ON" (built in #1518, "nice corner with the thread", Becker #14) |
| #1554 | `group_consistent_thread` -> ON | "Flip ON with guard" |
| #1554 | `group_consistent_outline_body` -> ON | "Flip ON with guard" |

The other suspects named in the brief are not in this window or move nothing here: #1524 is a Cancel seam inside the redraw (the redraw flip was #1515, already in the ledger); the three Flatten-shading commits keep their tick OFF; #1542 (auto-fit sizes the ink) touches only `app/`.

## Method

`arms.py` (scratchpad, not committed) digitizes each committed pair through the Studio request (`tools.pro_pair.request` -> `_parse_config` -> `PipelineConfig`), sets the named flags False and nothing else, writes `ours.dst`, then reads every figure with the tripwire's own reader (`pro_baseline.measure`, `figures_from_baseline`; no OCR, so word cc is not read locally). Six arms on `6f0dead8`: main, all four OFF, #1533's two OFF, #1554's two OFF, edge-walk OFF, corner-fold OFF.

Local numbers are for attribution only. Even so, local tracks CI closely. Main reproduces CI's red-night stitch counts on 14 of the 18 jobs exactly; the other four are off by 1 to 6 (Goldentee 6). All-OFF reproduces the green night's counts on 13 of the 18; the other five are off by 2 to 6, toat_machine_hat's 4 being runner jitter (below). Several DSTs come out **byte-identical to CI** (md5 of `ours.dst`). All-OFF equals CI green on Gaulke x3, Fremont x2, MFab hat, Drone and Tires. Main equals CI red on Gaulke hat and lc, Fremont x2, Drone and Tires.

## Attribution, row by row

The 25 wrong-way rows. **All-OFF** and **#1533 OFF** are identical on every row, and both return it to its ledger value. **#1554 OFF** is identical to main on every row: md5 equal on all 18 jobs, so #1554 moves nothing in the tripwire, as its PR body said.

| job | figure | ledger | CI red | tol | cause |
|---|---|---|---|---|---|
| becker_hat_large | stitches | 16,049 | 16,222 | 0 | corner fold (+ edge-walk) |
| becker_hat_large | stitch-type kappa (chance 0.53) | 0.337 | 0.289 | 0.00 | **corner fold**, worse with edge-walk |
| becker_hat_large | direction kappa | 0.365 | 0.329 | 0.00 | **corner fold**, worse with edge-walk |
| becker_lc_large | stitches | 14,542 | 14,644 | 0 | corner fold (+ edge-walk) |
| becker_lc_large | needle-up mm | 319.2 | 321.3 | 0.0 | the two together (each alone differs) |
| becker_hat_small | stitches | 10,260 | 10,361 | 2 | corner fold (+ edge-walk) |
| becker_hat_small | stitch-type kappa (chance 0.50) | 0.557 | 0.518 | 0.00 | **corner fold** |
| becker_chest_small | stitches | 10,082 | 10,189 | 2 | corner fold (+ edge-walk) |
| becker_chest_small | direction kappa | 0.439 | 0.432 | 0.00 | both (each alone -0.004 to -0.006) |
| becker_beanie | stitches | 13,609 | 13,712 | 2 | corner fold (+ edge-walk) |
| gaulke_roofing_hat | hops / needle-up mm / stitch-type kappa / direction kappa | 45 / 396.6 / 0.115 / 0.513 | 48 / 396.8 / 0.107 / 0.509 | 0 | edge-walk |
| gaulke_roofing_lc | stitches / trims / hops / direction kappa | 5,778 / 23 / 47 / 0.511 | 5,813 / 25 / 49 / 0.506 | 0 | edge-walk |
| gaulke_roofing_beanie | hops | 48 | 51 | 0 | edge-walk |
| hotel_fremont_hat | stitches | 15,898 | 15,899 | 0 | edge-walk |
| mfab_hat | word cc, native | 0.007 | 0.000 | 0.00 | edge-walk (no OCR locally; with both flags OFF its DST is CI green's byte for byte, and edge-walk alone writes main's DST byte for byte) |
| mfab_lc | stitches / hops | 17,853 / 28 | 17,894 / 29 | 5 / 0 | edge-walk |
| precision_drone | stitch-type kappa / direction kappa | 0.374 / 0.088 | 0.373 / 0.086 | 0.00 | edge-walk |

With edge-walk OFF (the fold alone), every non-Becker row returns to its ledger value. With the corner fold OFF (edge-walk alone), every non-Becker DST is byte-identical to main's. So **edge-walk alone moves Gaulke, Fremont, MFab, Drone and Goldentee, and the corner fold moves only the five Becker jobs**, as Kent was told.

The 32 right-way rows ride the same two flags. Becker loses 2 trims and 2 hops on four jobs, and 14-15 needle-up mm on three. MFab hat loses 2 trims, Gaulke hat and beanie lose ~30 stitches, and becker_lc_large stitch-type kappa rises 0.306 -> 0.337.

**Toat moved on CI but is runner jitter, not a change.** toat_machine_hat read 18,815 green and 18,811 red, and the other toat DSTs also differ in md5. Locally the three toat jobs are byte-identical in all six arms, so no flag moves them. Both five-pass captures measure a 4-stitch spread on toat_machine_hat across five runners of one tree. tires_hat_3d is byte-identical on CI and locally.

## What the corner fold costs on the pro yardstick

Stitch-type kappa, chance-corrected (local arms, attribution only; the CI red-night figure is in brackets):

| job | none | edge-walk alone | corner fold alone | both (main) |
|---|---|---|---|---|
| becker_hat_large | 0.340 | 0.351 | 0.313 | **0.292** (CI 0.289) |
| becker_hat_small | 0.557 | 0.568 | 0.507 | **0.514** (CI 0.518) |
| becker_lc_large | 0.306 | 0.299 | 0.333 | **0.337** (CI 0.337) |
| becker_chest_small | 0.581 | 0.580 | 0.587 | 0.591 (CI 0.591) |
| becker_beanie | 0.284 | 0.282 | 0.291 | 0.289 (CI 0.289) |

Direction kappa on becker_hat_large: 0.365 none, 0.365 edge-walk alone, 0.350 corner fold alone, **0.329 both** (CI 0.329).

Plainly:
- **becker_hat_large's stitch-type agreement with the pro fell by 0.048 kappa** (0.337 -> 0.289 on CI). Its direction agreement fell by 0.036 (0.365 -> 0.329). On Kent's largest Becker job our stitch types agree with the pro's measurably less often than they did. The cause is the corner fold, and edge-walk beside it deepens the loss.
- **becker_hat_small fell 0.039** (0.557 -> 0.518).
- **becker_lc_large rose 0.031** (0.306 -> 0.337). The two small changes (chest +0.010, beanie +0.005) sit inside what the runners agree on.
- Across the five Becker jobs, stitch-type kappa averages 0.413 under the old ledger and 0.405 now: a small net loss, concentrated on the two hat jobs.
- Edge-walk alone raises becker_hat_large's stitch-type kappa (0.340 -> 0.351). Its cost on the other designs is a few hundredths or less (Gaulke hat stitch-type 0.115 -> 0.107, Drone -0.001).

**What Kent was shown when he ruled:** for the corner fold, "only the five Becker jobs move, one trim fewer each, about 150 more stitches per E, and the E's top-left also fans where the pro's Becker file caps" (#1533, #1518). For edge-walk, trims 589 -> 596 and travel on finished thread 268.1 -> 32.0 mm over 28 designs (#1512). Neither PR, nor #1533's combined check, quoted a kappa. The table above is new to him.

## The new ledger

CI capture 43754823644, five passes on main `e739234c` (the red head plus #1563, an OFF flag; #1564, docs; #1566, metric-only). The artifact's sha256 is `d6c3c82c…b993d484`, the same as printed in the capture job's log. Its baselines equal the red night's values on every moved row. 111 rows, none skipped.

**#1505 check:** no stitch row went from a measured tolerance to 0. Every row that had a tolerance before keeps one (Becker small jobs 2, toat_machine_hat 4). The one change is **mfab_lc stitches, narrowed 5 -> 3**, a measured spread of 3 over five passes, not a zero. It is left as measured (no hand edit) and noted here in case a later night lands 4-5 off. mfab_lc needle-up mm gained a tolerance (0.0 -> 1.7, spread 1.7).

The re-captured ledger is in the same PR as this note, **not armed for auto-merge**: merging it accepts the corner fold's kappa cost, which is Kent's trade.
