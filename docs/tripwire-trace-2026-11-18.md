# Tripwire trace: which flip moved which figure, 2026-11-18

Kent, 2026-11-18: "Hold and trace the old flips (Recommended)" on the re-captured tripwire ledger (PR #1646, a draft).
This doc is the trace. It changes no default and proposes no revert: that is Kent's, with this table in front of him.

## Method

- **Base and head.** The 2026-11-15 ledger was captured at head `f095e1ab`. `PipelineConfig` defaults at `f095e1ab` against `origin/main`
  (3edc5011 plus two built-OFF commits) differ in **31 flags**: 7 flipped False -> True (`border_from_outline_follow_shape`,
  `outline_frame_guard`, `satin_cap_skew_inset`, `satin_free_end_chord_aim`, `satin_seam_hold`, `speck_prune`, `stroke_bridge_keep`),
  1 value change (`satin_push_keeps_gaps` None -> 0.5) and 23 new fields that default ON (the rest of the 11-15 to 11-17 flips).
- **Arms.** `tools.tripwire measure` (pinned frame, one process per arm, local Linux, nothing committed) over the 6 jobs that hold the
  movers none of today's five flags explained: `precision_drone`, `toat_beanie`, `toat_machine_beanie`, `toat_machine_hat`,
  `goldentee_hat`, `mfab_hat`. Arms: today's default; each of the 31 flags forced to its old value, one at a time; all 31 at once
  (ALLOFF); then 10 combinations of the suspects. "Share" below = (now - arm) / (now - old ledger), so 1.00 restores the old figure.
- **Not measured:** word cc (`mfab_hat` 0.0 -> -0.091; needs the OCR reader), the `becker_*` movers, and any job outside the six.

## Headline

**ALLOFF restores every one of these figures to the old ledger (share 1.00 on all 17), so none of them comes from unflagged code.**
They come from a few flags, and the movers are not independent: for several, no single flag restores the figure.

## Worst regression first

| mover | old -> now | what restores it | smallest set found |
|---|---|---|---|
| toat_beanie direction kappa | 0.24 -> 0.00 | `outline_inlets_kept` (#1594) alone: 0.211 (0.88) | INLET alone is 0.88 of it; 0.239 (1.00) with RIM + INLET + FREEEND (not every pair was run) |
| toat_machine_beanie stitch-type kappa | 0.372 -> 0.280 | `silhouette_underfill_rim_fabric_edges` (#1609) alone: 0.379 (1.08); direction 0.389 -> 0.361: 0.388 (0.96) | **one flag**: RIM |
| toat_machine_hat stitch-type kappa | 0.413 -> 0.343 | RIM alone: 0.416 (1.04); direction 0.709 -> 0.676: 0.705 (0.88) | **one flag**: RIM |
| precision_drone needle-up mm | 1419.8 -> 1551.6 | RIM 0.47, `satin_free_end_chord_aim` 0.41, `satin_seam_hold` 0.28, INLET 0.16 | **three**: RIM + INLET + FREEEND = 1418.0 (1.01) |
| precision_drone trims / hops | 85 -> 94 / 121 -> 136 | RIM 0.44 / 0.27, INLET 0.33 / 0.33, `color_cap_least_loss` 0 / 0.20 | no pair or triple restores both: RIM + INLET gives trims 87 (0.78); four flags give hops 125 (0.73); only ALLOFF reaches 85 / 121 |
| precision_drone stitch-type kappa | 0.373 -> 0.346 | RIM 0.48, FREEEND 0.30, SEAM 0.22 | RIM + INLET + FREEEND = 0.370 (0.89) |
| goldentee_hat stitch-type kappa | 0.868 -> 0.813 | `satin_push_keeps_gaps` 0.51, SEAM 0.24 | **pair**: PUSH + SEAM = 0.868 (1.00) |
| goldentee_hat trims / hops | 39 -> 45 / 68 -> 71 | SEAM 0.50 / FREEEND 0.67 | no single flag restores trims; best is SEAM (42) |
| mfab_hat needle-up mm | 727.5 -> 745.1 | `satin_push_keeps_gaps` alone: 730.2 (0.85) | PUSH + SEAM = 726.5 (1.06) |
| mfab_hat stitch-type kappa | 0.579 -> 0.571 | PUSH alone: 0.581 (1.25, overshoots) | PUSH + SEAM 0.577 (0.75) |
| toat_machine_hat needle-up mm | 252.2 -> 257.7 | `lone_glyph_keep` (#1588) alone: 253.6 (0.75) | LONE |
| toat_beanie stitch-type kappa | 0.391 -> 0.359 | RIM overshoots (0.418, 1.84), INLET undershoots (0.290, -2.16) | they offset: RIM + INLET + FREEEND = 0.390 (0.97) |

## The flags that carry it

- **`silhouette_underfill_rim_fabric_edges`** (#1609, Kent 2026-11-16, "Under-fill rim on fabric edges + per-line size ring"): the Toat Machine kappas
  and about half of the Drone's trims, needle-up and stitch-type kappa.
- **`outline_inlets_kept`** (#1594, Kent 2026-11-15, "K-Line box + gear flags"): toat_beanie direction kappa, a third of the Drone's trims and hops.
- **`satin_push_keeps_gaps` 0.5** (#1581, Kent 2026-11-15, "Flip both, value 0.5") and **`satin_seam_hold`** (flag ends/seam trio, #1641,
  2026-11-17): Golden Tee stitch-type kappa (as a pair) and mfab_hat needle-up.
- **`satin_free_end_chord_aim`** (same trio): Drone needle-up and Golden Tee hops. **`lone_glyph_keep`** (#1588): toat_machine_hat needle-up.
- Not carriers of these movers: `keyline_fragment_drop`, `rope_band`, `page_line_open` (no effect on any of the six jobs),
  `lettering_columns_cover_hops` and `color_cap_least_loss` (small shares of the Drone's hops and needle-up only).

## Reading the table

These figures are agreement with one professional's files (stitch-type and direction kappa with their chance floors, counts of
cuts, hops and needle-up mm). Each flip above was shown to Kent as before | after pictures. A kappa that falls while the picture got
better is possible, and this trace does not say which of the two is true for any mover; it says which flag moved it.
Single-flag arms were run on cloud Linux numbers locally; the committed ledger would still come from the capture dispatch.
