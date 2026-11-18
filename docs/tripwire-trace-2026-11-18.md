# Tripwire trace: which flip moved which figure, 2026-11-18

Kent, 2026-11-18: "Hold and trace the old flips (Recommended)" on the re-captured tripwire ledger (PR #1646, a draft).
This doc is the trace. It changes no default and proposes no revert: that is Kent's, with this table in front of him.

## Method

- **Base and head.** The 2026-11-15 ledger was captured at head `f095e1ab`. `PipelineConfig` defaults at `f095e1ab` against `origin/main`
  (3edc5011 plus two built-OFF commits; see the correction below for #1659) differ in **31 flags**: 7 flipped False -> True (`border_from_outline_follow_shape`,
  `outline_frame_guard`, `satin_cap_skew_inset`, `satin_free_end_chord_aim`, `satin_seam_hold`, `speck_prune`, `stroke_bridge_keep`),
  1 value change (`satin_push_keeps_gaps` None -> 0.5) and 23 new fields that default ON (the rest of the 11-15 to 11-17 flips).
- **Arms.** `tools.tripwire measure` (pinned frame, one process per arm, local Linux, nothing committed) over the 6 jobs that hold the
  movers none of today's five flags explained: `precision_drone`, `toat_beanie`, `toat_machine_beanie`, `toat_machine_hat`,
  `goldentee_hat`, `mfab_hat`. Arms: today's default; each of the 31 flags forced to its old value, one at a time; all 31 at once
  (ALLOFF); then 10 combinations of the suspects. "Share" below = (now - arm) / (now - old ledger), so 1.00 restores the old figure.
- **Not measured:** word cc (`mfab_hat` 0.0 -> -0.091; needs the OCR reader), the `becker_*` movers, and any job outside the six.

## Correction after #1659 (2026-11-18)

Three of the 31 flags below, `lettering_columns_apex_pro`, `lettering_columns_apex_pro_joints` and `lettering_columns_corner_fold_cap_flared`, were
flipped ON on 2026-11-15 in #1583 and **reverted to OFF by #1659** (d6a7cf70, Kent 2026-11-17: "Revert all three (Recommended)"). Main therefore no longer
differs from `f095e1ab` in them: **on current main the difference is 28 flags, not 31.** The arms in this doc ran on `49be98e6`, while those three were still ON,
so their rows (Becker's MARINE caps, and any share of a figure they carried) describe a state main no longer has. No figure in the tables below was
attributed to them (the carriers are the five listed under "The flags that carry it"), so no row changes, but the "31" and "ALLOFF" counts are of the
pre-#1659 tree.

## The fresh capture the ruling asked for (run 44241180150, main 5068c36d)

Kent, 2026-11-18: "Accept after one fresh capture (Recommended)". Captured after #1635 (`satin_thin_arm_stop`), #1652 (`text_cluster_mixed_caps`), #1654
(`color_cap_fuse_split_tones`), #1655 (`round_dot_ring`), #1656 (`lettering_columns_off_line_mark`), #1659 (the apex revert) and #1662
(`enclosed_white_keeps_known_colour`, also landed). Against the 2026-11-15 ledger: 57 figures better, 35 wrong-way, 19 unchanged (of 111); against the
intermediate capture 44205663556 on 3edc5011: 30 better, 34 wrong-way, 47 unchanged.

**Wrong-way movers on jobs this trace did NOT cover, or not explained by the trace** (not measured per flag):

- `mfab_lc` needle-up mm: 441.0 (11-15) -> 468.5 (capture on 3edc5011) -> **523.9** (this capture), +82.9 mm. #1656 says it moves `mfab_hat` only; no flag in this doc
  explains `mfab_lc`.
- The five `becker_*` jobs: stitches up (hat_small +254, chest_small +238, lc_large +102, beanie +89, hat_large +21 since 3edc5011) with stitch-type and direction
  kappas down 0.03-0.05 on four of them. The apex revert explains part of it (#1659's own table: Becker hat large -27 stitches, the other four +75 to +152), but hat_small (+254) and chest_small (+238) rise further than that and hat_large rises where #1659 says it falls, so other flips contribute; no per-flag arm was run.
  Against the 11-15 ledger the Becker rows are mostly still at or better than baseline (hat_large stitch-type 0.289 -> 0.303); the 11-15 wrong-way Becker figures
  are beanie needle-up +17.2 mm, stitch-type -0.018, direction -0.007 and hat_large +16 stitches / +2.7 mm.
- `toat_machine_beanie` needle-up +25.4 mm and `toat_machine_hat` +10.2 mm since 3edc5011 (the `satin_thin_arm_stop` arm above explains about +5.0 mm of the hat's).

Movers the flips themselves explain: Tires +106 stitches and +5.0 mm needle-up (`round_dot_ring`, #1655), `mfab_hat` +76 stitches (#1656), Drone +10 stitches
and +6.4 mm (`color_cap_fuse_split_tones`, #1654).

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

## Separate arm: `satin_thin_arm_stop` (#1635) ON vs OFF on current main

#1635 merged after the capture, so it is not in the ledger and is not in any arm above (those ran on `49be98e6`, which is comparable with
capture 3edc5011). One extra pair of arms on a tree that has it: the default (ON) against `satin_thin_arm_stop` forced OFF, same six jobs,
same method. The OFF arm reproduces the ledger's figures, so the comparison is clean. Of 36 figure readings: 14 unchanged, 14 better, 8 worse
(`mfab_hat` has no row in this list: unchanged).

| job | figure | OFF (= ledger) | ON | |
|---|---|---|---|---|
| precision_drone | stitches | 13947 | 13864 | better -83 |
| precision_drone | hops / trims / needle-up mm | 136 / 94 / 1551.6 | 137 / 95 / 1558.6 | worse +1 / +1 / +7.0 |
| precision_drone | stitch-type kappa / direction kappa | 0.346 / 0.083 | 0.352 / 0.082 | better +0.006 / worse -0.001 |
| toat_beanie | stitches / trims / hops / needle-up mm | 17389 / 24 / 32 / 245.1 | 17233 / 23 / 31 / 237.8 | all better |
| toat_beanie | stitch-type kappa | 0.359 | 0.365 | better +0.006 |
| toat_machine_beanie | stitches | 17030 | 16919 | better -111 |
| toat_machine_beanie | stitch-type kappa / direction kappa | 0.280 / 0.361 | 0.276 / 0.365 | worse -0.004 / better +0.004 |
| toat_machine_hat | stitches | 17314 | 17207 | better -107 |
| toat_machine_hat | needle-up mm / trims | 257.7 / 19 | 262.7 / 20 | worse +5.0 / +1 |
| toat_machine_hat | stitch-type kappa / direction kappa | 0.343 / 0.676 | 0.347 / 0.679 | better +0.004 / +0.003 |
| goldentee_hat | stitches | 10686 | 10583 | better -103 |
| goldentee_hat | stitch-type kappa / direction kappa | 0.813 / 0.323 | 0.806 / 0.331 | worse -0.007 / better +0.008 |

Every one of the six jobs sews 83-156 fewer stitches ON. The worse readings are small (1 cut or hop, 5-7 mm of needle-up, a kappa
within 0.007). Wrong-way moves against the tripwire's 0.00 tolerance are: precision_drone hops, trims, needle-up and direction kappa;
toat_machine_beanie stitch-type kappa; toat_machine_hat needle-up and trims; goldentee_hat stitch-type kappa.
