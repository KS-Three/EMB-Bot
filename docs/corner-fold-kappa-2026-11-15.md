# Corner fold and the Becker kappa drop: the fold barely moves agreement; registration moved the grid

*(measured 2026-11-15 — local arms on Kent's laptop from the tripwire triage (`docs/tripwire-red-2026-11-15.md`), read through `tools/pro_parity/scorecard.py`'s own steps 1-3, the reader the tripwire uses. Local-ON against local-OFF only; no baseline captured. Measurement and diagnosis only: no flag, default or engine file changed.)*

**Question** (Kent's ruling 2026-11-15, "Accept + investigate (Recommended)"): where do `becker_hat_large` and `becker_hat_small` lose stitch-type agreement with the pro under `lettering_columns_corner_fold_apex_side`? And why does `becker_lc_large` go up under the same flag?

**Answer: they don't lose it to the fold.** Measured in one fixed frame, the fold changes chance-corrected stitch-type kappa by **+0.006 on hat_large, −0.008 on hat_small and +0.002 on lc_large**. All three are inside the instrument's own grid noise (SD 0.02-0.04).

The −0.048 and −0.039 the tripwire read, and lc_large's +0.031, come from **registration**. The fold adds a tenth of a millimetre of thread at the E. That tips the scorecard's IoU hill-climb onto another point of a flat plateau, 0.2-0.55 mm away. The 2 mm cell grid every kappa is read on then moves with it. The hypothesis (the E's top-left, where we fan and the pro caps) is **not** what the number measured.

## 1. The two figures, own registration against one frame

`regsweep.py` (scratchpad) scores each arm three ways:
- at its own registration (what the tripwire reads);
- at the other arm's registration;
- in a common frame: the fold-OFF arm's registration and bounds for both arms, so both are cut on one cell grid.

It also sweeps the grid origin over 64 offsets (0-1.75 mm in x and y, 0.25 mm steps) with ours held at its own registration. That shows how much the 2 mm grid alone moves the figure.

Fold OFF -> ON, edge-walk ON in both (`cf_off` -> `main`) unless marked:

| job | registration OFF -> ON (mm) | stitch-type kappa, own registration | **stitch-type kappa, one frame** | direction kappa, own -> one frame (ON) | grid SD (OFF / ON) | grid range, OFF |
|---|---|---|---|---|---|---|
| becker_hat_large | (0.35, 0.15) -> (0.35, −0.40) | 0.351 -> 0.292 (−0.059) | **0.351 -> 0.357 (+0.006)** | 0.365 -> 0.329 / 0.370 | 0.023 / 0.030 | 0.294-0.399 |
| becker_hat_large, fold alone (`all_off` -> `ew_off`) | (0.35, 0.15) -> (0.35, −0.15) | 0.340 -> 0.314 (−0.026) | **0.340 -> 0.352 (+0.012)** | 0.365 -> 0.350 / 0.370 | 0.020 / 0.026 | 0.298-0.391 |
| becker_hat_small | (0.15, 0.40) -> (0.25, 0.25) | 0.568 -> 0.514 (−0.054) | **0.568 -> 0.560 (−0.008)** | 0.402 -> 0.412 / 0.410 | 0.040 / 0.033 | 0.481-0.661 |
| becker_hat_small, fold alone | (0.15, 0.40) -> (0.25, 0.25) | 0.557 -> 0.507 (−0.050) | **0.557 -> 0.553 (−0.004)** | 0.406 -> 0.410 / 0.410 | 0.037 / 0.030 | 0.485-0.654 |
| becker_lc_large | (0.35, −0.05) -> (0.35, 0.15) | 0.299 -> 0.337 (+0.038) | **0.299 -> 0.301 (+0.002)** | 0.356 -> 0.369 / 0.358 | 0.026 / 0.022 | 0.279-0.402 |
| becker_chest_small | (0.15, 0.45) -> (0.15, 0.40) | 0.580 -> 0.591 (+0.011) | **0.580 -> 0.581 (+0.001)** | 0.435 -> 0.432 / 0.442 | 0.034 / 0.038 | 0.518-0.705 |
| becker_beanie | (0.25, 0.25) -> (0.25, 0.25) | 0.282 -> 0.289 (+0.007) | **0.282 -> 0.289 (+0.007)** | 0.554 -> 0.554 / 0.554 | 0.028 / 0.031 | 0.212-0.340 |

What the table shows:
- **Where registration did not move (beanie), own and one-frame agree exactly.** Where it moved, the own-registration figure swings by up to 0.059 and the one-frame figure stays within ±0.012.
- **Re-cut on the other arm's registration, each arm reads the other's number.** On hat_large, fold-OFF scored at the ON arm's registration reads 0.297, and fold-ON at the OFF arm's reads 0.358. The figure follows the frame, not the thread.
- **The pro's own cell mix changes between the two arms on hat_large: 345 -> 327 satin cells, 911 -> 899 typed cells.** The pro's file is committed and identical in both; only the grid moved.
- **Direction kappa behaves the same way.** hat_large's −0.036 on the tripwire is +0.005 in one frame.
- **lc_large goes UP for the same reason the hats go down.** Its registration moved 0.20 mm the other way, onto a luckier cut of the same grid. In one frame the fold is +0.002 there.

## 2. Why the registration moved

`scorecard.register` hill-climbs on solid IoU from several seeds, down to a 0.25 mm step. On becker_hat_large the IoU surface is flat across the whole band (`iouplateau.py`):

| dy (dx 0.35) | +0.25 | +0.15 | 0.00 | −0.15 | −0.25 | −0.40 | −0.50 |
|---|---|---|---|---|---|---|---|
| fold OFF, IoU | 0.9009 | **0.9000** | 0.8971 | 0.8993 | 0.9020 | 0.9003 | 0.8959 |
| fold ON, IoU | 0.8996 | 0.8994 | 0.8977 | 0.9000 | 0.9008 | **0.9001** | 0.8966 |

(Bold = the shift each arm's climb returned. Neither is the plateau's best point; the climb stops at the first local maximum it reaches.)

The fold extends our design's top edge by 0.1 mm (y extent 31.9 -> 32.0 mm). Our DST is bbox-centred, so every stitch shifts by 0.05 mm, and the climb settles on a different point of a plateau where the IoU differs by about 0.001. Stitch type is then read per 2 mm cell (`cell_stats`: one type per cell from median stitch length and reversal rate), and a cell straddling a satin-fill boundary flips type as the grid slides under it. Over 64 grid offsets with registration held, hat_large's fold-OFF kappa ranges 0.294-0.399. That range is the size of the effect the tripwire attributed to the fold.

## 3. Where the fold does change agreement

In the common frame (`commoncells.py`), the fold changes stitch type in **9 of 911 cells on hat_large**: 3 lose agreement with the pro and 6 gain it. All 9 are in one patch, x 37-47 mm, y 15-31 mm: **MARINE's E**, its stem and the two left corners.

The renders (ours fold OFF | ours fold ON | pro, one frame, cells tinted by type, changed cells boxed red) are in the primary checkout's gitignored `pro_renders/corner-fold-kappa-2026-11-15/` (`hat_large_full.png`, `hat_large_crop.png`). They show:
- **Fold OFF:** the stem is one vertical column, with the arms butted to it.
- **Fold ON:** the stem's crosses fan round both left corners, so the top arm, stem and bottom arm are one column, as #1518 built.
- **The pro:** the bottom-left fans like ours, and the top-left is capped, the top arm running across the stem's top, as #1518 said.

The fan's radial crosses read as satin in some stem cells and fill in others, and so do the pro's cells there. The top-left box is one of the 9. So the hypothesis region does differ from the pro, but the whole E moves the figure by 3 cells of 911, net in our favour. **The E's top-left is not where 0.048 kappa went.**

## 4. What this means

- **For Kent's ruling:** the cost he accepted on 2026-11-15 is, on this evidence, not a cost of the fold. The fold's stitch-type effect against the pro is within ±0.012 on every Becker job, and positive on four of five.
- **For the tripwire and every kappa read through `scorecard`:** a figure can move by ±0.05 when an engine change adds or removes a sliver of thread anywhere in the design. The cause is that registration lands elsewhere on a flat plateau and re-cuts the grid. The five-pass capture cannot see this: runners write the same DST, so they agree on the registration, and the kappa rows get tolerance 0.00. The next PR that touches a Becker outline by 0.1 mm can turn any of these rows red or green with no stitch-type change at all.
- **Not changed here:** the scorecard, the ledger, any flag. The options for Kent are in the PR body and the foreman's message.

## Reproduce

The arms are the triage's (`docs/tripwire-red-2026-11-15.md`, Method). The scripts (`regsweep.py`, `iouplateau.py`, `commoncells.py`, `render3.py`) are uncommitted scratch, one screen each. Every one imports `tools.pro_parity.scorecard` and calls its `load_side`, `register`, `bounds`, `shifted`, `coverage_component`, `direction_cells`, `type_chance` and `chance_correct` unchanged; only the shift and the bounds passed in differ. Grid sweep: 64 anchors per arm, about 2 s each on the laptop.
