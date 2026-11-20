# OFF-flag census: what each built-OFF flag changes on today's engine (2026-11-20)

Measure only. No engine change, no flag flipped, nothing sewn.

## The question

105 flags: the 103 `PipelineConfig` booleans that default to `False` (`tests/test_off_flags_smoke.py`'s `OFF_FLAGS`), plus `fill_technique="fur"` and `forbid_gap_mm=0.8` swept as their ON values. Which of them still change stitches on the shipped engine, and which have been left behind by later flips?

## Method

`python -m tools.flag_sweep --flag NAME` for every flag, OFF vs ON, over its full population: the 18 nightly tripwire placements (each at its pro's width and garment) and the 26 `corpus_scorecard.FIXTURES` (81 mm, hat front). 44 runs per flag. "Moved" means the stitch md5 differs between arms.

Run on Kent's 28-core desktop at `1089931d` (main, 2026-11-19), 22 sweeps in parallel, 10.2 hours for the 97-flag pass. `main` has moved since (#1731 onward), so re-sweep a flag before quoting its row in a flip.

A flag that moved nothing was swept again with its prerequisite chain ON in both arms (`--set`), read from its `config.py` comment.

**What "0 moved" does NOT say.** It says no stitch changed on these 44 placements. A report-only flag (`proofread`, `preflight_glyph_metric`), a class detector the Studio request already answers (`detect_photographic`), or a lane none of the 44 reach (SAM2, faces, script) will read 0 here and may still matter. Read each row against its config comment before retiring anything.

## Result: 28 flags change no stitch on any of the 44, even with prerequisites ON

| flag | prerequisites set | note |
|---|---|---|
| `curve_chord_stage4` | none |  |
| `curve_chord_stage4_spare_text` | `curve_chord_stage4` |  |
| `dark_ink_refuse_strays` | none |  |
| `detect_photographic` | none |  |
| `edge_cap_fold_into_colour` | none |  |
| `edge_cap_walk_covered` | none |  |
| `faces_route_flat` | `detect_photographic` |  |
| `hair_regions_directional` | `hairline` |  |
| `keep_counters` | `small_print_floor` |  |
| `lettering_columns_connectors_buried` | none |  |
| `monoline_script_satin` | none |  |
| `page_line_front` | `hairline` |  |
| `photo_prep_tone` | none |  |
| `photo_segment_sam2` | none |  |
| `preflight_glyph_metric` | `proofread` |  |
| `proofread` | none |  |
| `proofread_guard_clipped` | `proofread` |  |
| `satin_floor_content_gate` | `hairline` |  |
| `satin_hairline_tier` | `hairline` |  |
| `satin_patch_junctions` | none |  |
| `shade_axis_normalize` | none |  |
| `sliver_prune` | none |  |
| `small_lettering_skeleton` | none | reached only with `bean_only_lines` OFF (its own test sets it False); `bean_only_lines` is ON since 2026-10-27. Also swept with `small_print_floor` ON: 0/44. |
| `stripe_underfill` | none |  |
| `text_cluster_nest_guard` | none |  |
| `text_cluster_nest_guard_rotated` | `text_cluster_nest_guard` |  |
| `tonal_split_ceiling` | none |  |
| `tonal_split_layer_cap` | `tonal_split_ceiling` |  |

## 10 flags that read dead alone but move under their parent

| flag | prerequisites set | moved |
|---|---|---|
| `hairline_coverage_guard` | `hairline` | 14/44 |
| `hairline_from_lines` | `hairline` | 4/44 |
| `hairline_lines_chain` | `hairline`, `hairline_from_lines`, `hairline_lines_strand_test` | 1/44 |
| `hairline_lines_gradient` | `hairline`, `hairline_from_lines`, `hairline_lines_strand_test` | 3/44 |
| `hairline_lines_logo_refusal` | `hairline`, `hairline_from_lines`, `hairline_lines_strand_test`, `hairline_lines_gradient` | 3/44 |
| `hairline_lines_strand_mass` | `hairline`, `hairline_from_lines`, `hairline_lines_strand_test` | 1/44 |
| `hairline_lines_strand_test` | `hairline`, `hairline_from_lines` | 2/44 |
| `hairline_over_ground` | `hairline` | 5/44 |
| `lettering_word_tiers` | `lettering_words` | 8/44 |
| `open_cored_counters` | `small_print_floor`, `keep_counters` | 2/44 |

## Every flag, alone (OFF vs ON, nothing else set)

Sorted by designs moved. Σ columns sum ON minus OFF over the designs that moved; the stitch column is the median. Direction only: more or fewer is not better or worse without the pictures (CLAUDE.md, "A flip question comes with pictures").

| flag | moved | tripwire moved | median Δ stitches | Σ Δ trims | Σ Δ jumps | Σ Δ needle-up mm |
|---|---|---|---|---|---|---|
| `curve_chord_stage4` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `curve_chord_stage4_spare_text` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `dark_ink_refuse_strays` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `detect_photographic` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `edge_cap_fold_into_colour` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `edge_cap_walk_covered` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `faces_route_flat` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hair_regions_directional` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hairline_coverage_guard` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hairline_from_lines` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hairline_lines_chain` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hairline_lines_gradient` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hairline_lines_logo_refusal` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hairline_lines_strand_mass` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hairline_lines_strand_test` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `hairline_over_ground` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `keep_counters` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `lettering_columns_connectors_buried` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `lettering_word_tiers` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `monoline_script_satin` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `open_cored_counters` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `page_line_front` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `photo_prep_tone` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `photo_segment_sam2` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `preflight_glyph_metric` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `proofread` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `proofread_guard_clipped` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `satin_floor_content_gate` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `satin_hairline_tier` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `satin_patch_junctions` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `shade_axis_normalize` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `sliver_prune` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `small_lettering_skeleton` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `stripe_underfill` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `text_cluster_nest_guard` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `text_cluster_nest_guard_rotated` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `tonal_split_ceiling` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `tonal_split_layer_cap` | 0/44 | 0 | 0 | 0 | 0 | 0 |
| `blend_speckle_residual` | 1/44 | 0 | 271 | 1 | 4 | 13.9 |
| `lettering_columns_cover_handback` | 1/44 | 1 | 32 | 0 | 0 | -1.3 |
| `regular_structure` | 1/44 | 0 | -1 | 0 | 0 | 0.1 |
| `satin_junction_square` | 1/44 | 1 | -5 | -1 | 0 | -6.9 |
| `satin_mid_entry` | 1/44 | 1 | -2 | -1 | 0 | -1.4 |
| `dark_neutral_split` | 2/44 | 1 | -128.0 | -2 | -5 | 12.9 |
| `lettering_contrast_floor` | 2/44 | 1 | 2.5 | -1 | 13 | 114.9 |
| `merge_chroma_guard` | 2/44 | 1 | 1708.5 | 12 | 57 | 346.4 |
| `photo_enclosed_rim` | 2/44 | 1 | -684.5 | -7 | -33 | -432.3 |
| `satin_hop_under_column` | 2/44 | 0 | -1.0 | 0 | 0 | 0.0 |
| `script_strokes_drawn_width` | 2/44 | 1 | -26.0 | 2 | 1 | -6.0 |
| `underfill_untagged_riders` | 2/44 | 2 | 14.0 | -2 | -10 | -174.2 |
| `held_hole_bare_only` | 3/44 | 0 | -38 | 3 | 22 | 97.6 |
| `keyline_under_face` | 3/44 | 1 | 98 | -11 | 1 | 125.6 |
| `light_thin_stroke_keep` | 3/44 | 2 | 125 | 4 | -1 | -9.8 |
| `line_chain_one_thread` | 4/44 | 2 | 12.0 | 2 | 14 | 187.7 |
| `photo_work_grid` | 4/44 | 1 | -33.0 | -30 | -97 | -1116.6 |
| `small_letter_ties` | 4/44 | 2 | -8.0 | 0 | 0 | -6.4 |
| `shade_palette_demand` | 5/44 | 0 | 41 | 49 | 93 | 716.4 |
| `coverage_edges` | 6/44 | 5 | -57.5 | 0 | -45 | -480.9 |
| `fill_one_pass_sections` | 6/44 | 1 | 211.0 | -24 | -140 | -579.0 |
| `lettering_columns_apex_pro` | 6/44 | 5 | 68.5 | 2 | 1 | -1.7 |
| `lettering_columns_apex_pro_joints` | 6/44 | 5 | 148.0 | 5 | -4 | -59.9 |
| `lettering_columns_corner_fold_cap_flared` | 6/44 | 5 | 27.0 | -5 | -4 | -22.2 |
| `outline_one_band` | 6/44 | 5 | -471.5 | 49 | 55 | 552.3 |
| `script_strokes_pull_by_stroke` | 6/44 | 4 | -13.0 | 2 | 3 | 18.7 |
| `silhouette_underfill_photo` | 6/44 | 0 | -229.0 | -29 | -21 | 22.6 |
| `flat_page_fringe_exclude` | 8/44 | 4 | -24.5 | 12 | 10 | 269.9 |
| `outline_loop_split_shared` | 8/44 | 7 | -4.5 | -2 | -3 | -31.6 |
| `outline_strip_column` | 8/44 | 7 | -3.5 | 11 | -22 | -267.1 |
| `resnap_hairline_never_lightens` | 8/44 | 2 | 10.5 | -10 | 14 | -27.7 |
| `sew_enclosed_counters` | 8/44 | 4 | 239.5 | 68 | 159 | 1214.2 |
| `underlay_all_pieces` | 8/44 | 1 | 46.5 | 7 | -10 | -41.2 |
| `classify_area_weighted` | 9/44 | 2 | -56 | -26 | -46 | 226.2 |
| `satin_per_stroke` | 9/44 | 3 | -77 | 9 | 7 | 343.7 |
| `bevel_ring_fold` | 10/44 | 2 | -452.5 | -121 | -227 | -1774.1 |
| `fill_order_sewn_paths` | 11/44 | 2 | 3 | 21 | 10 | 149.8 |
| `run_soft_vertices` | 12/44 | 3 | 0.0 | -1 | -1 | -9.7 |
| `stitch_width_auto` | 13/44 | 9 | -6 | 0 | 3 | 23.7 |
| `overlap_by_angle` | 15/44 | 2 | 56 | -5 | 22 | 144.2 |
| `sew_enclosed_white_fields_fill` | 15/44 | 11 | 85 | 10 | 11 | 1.9 |
| `bg_structural` | 16/44 | 9 | -35.5 | -7 | -90 | -1000.4 |
| `fill_seam_aware_sections` | 19/44 | 8 | 119 | -94 | -310 | -1429.9 |
| `lettering_words` | 19/44 | 9 | 40 | 24 | 72 | 101.6 |
| `satin_tip_corner_gate` | 19/44 | 7 | -30 | 2 | 8 | 64.4 |
| `hairline` | 20/44 | 10 | -292.5 | 67 | 66 | 519.8 |
| `lettering_columns_apex_cut` | 21/44 | 14 | 1 | 0 | 0 | -36.6 |
| `tiny_detail_keep` | 21/44 | 13 | 18 | 20 | 8 | -111.6 |
| `wide_columns` | 22/44 | 11 | 67.0 | 1 | -11 | -110.2 |
| `fill_inside_satin_border` | 23/44 | 14 | 858 | 164 | 339 | 2723.9 |
| `pull_comp_by_stroke` | 23/44 | 15 | -1 | 8 | -4 | 4.6 |
| `forbid_gap_mm` | 27/44 | 12 | 1 | 40 | 77 | 784.1 |
| `outline_redraw_native` | 28/44 | 8 | 14.5 | 26 | 14 | 176.9 |
| `small_print_floor` | 29/44 | 17 | 0 | 14 | 23 | 135.8 |
| `cap_center_out` | 31/44 | 13 | 32 | 247 | 1455 | 19539.6 |
| `satin_tip_floor_cross` | 33/44 | 16 | 16 | 2 | -10 | -127.5 |
| `cut_every_jump` | 35/44 | 15 | 13 | 270 | -721 | -1094.6 |
| `detail_layer` | 35/44 | 13 | 2581 | 657 | 2032 | 7504.9 |
| `fill_density_boost` | 37/44 | 18 | 4945 | -145 | -240 | -2321.2 |
| `chain_links` | 38/44 | 16 | -0.5 | -268 | -927 | -2819.9 |
| `design_angle` | 39/44 | 18 | -10 | 61 | 140 | 524.3 |
| `satin_polygon_axis` | 39/44 | 18 | 1 | 52 | 85 | 738.6 |
| `satin_underlay_on_column` | 39/44 | 18 | 0 | -1 | 0 | 16.6 |
| `fill_technique` | 42/44 | 18 | -225.5 | -23 | -68 | -651.0 |
| `pro_measured_values` | 42/44 | 17 | -470.5 | 12 | 13 | -0.2 |
| `applique` | 44/44 | 18 | -5058.5 | -919 | 1972 | 35537.5 |
| `directional_comp` | 44/44 | 18 | -40.5 | 219 | 548 | 4945.0 |

0 errored across all sweeps.

## Against the flag audit's tiers

`docs/flag-audit-2026-11-19.md` sorts every switch into tiers. The 28 dead flags fall into five of them (all 28 still exist and still default `False` on `main` at `14c95010`):

| audit tier | dead flags | what the census adds |
|---|---|---|
| **H**, OFF with no final ruling (11) | `curve_chord_stage4`, `curve_chord_stage4_spare_text`, `dark_ink_refuse_strays`, `edge_cap_walk_covered`, `keep_counters`, `lettering_columns_connectors_buried`, `monoline_script_satin`, `satin_patch_junctions`, `shade_axis_normalize`, `text_cluster_nest_guard`, `text_cluster_nest_guard_rotated` | Turning any one ON changes no stitch on the 44 placements, prerequisites included. The strongest delete candidates in tier H. |
| **F**, gate 1, waiting on cloth (7) | `hair_regions_directional`, `page_line_front`, `satin_hairline_tier`, `sliver_prune`, `small_lettering_skeleton`, `stripe_underfill`, `tonal_split_ceiling` | A sew-out of these would show nothing on any tripwire or corpus design. Find art they act on before booking hoop time; `small_lettering_skeleton` is unreachable while `bean_only_lines` is ON. |
| **G**, instruments and metric-only (5) | `preflight_glyph_metric`, `proofread`, `proofread_guard_clipped`, `satin_floor_content_gate`, `tonal_split_layer_cap` | Expected for instruments. `satin_floor_content_gate` and `tonal_split_layer_cap` are named like layout switches; worth confirming they are metric-only. |
| **P**, product options the Studio or service sends (4) | `detect_photographic`, `edge_cap_fold_into_colour`, `faces_route_flat`, `photo_segment_sam2` | Expected: the sweep's request already fixes what these choose. Keep. |
| **E**, ask (1) | `photo_prep_tone` | Moves nothing on the 44. |

Five flags in the per-flag table below are no longer OFF on `main` (`coverage_edges`, `lettering_columns_apex_cut`, `line_chain_one_thread`, `outline_loop_split_shared`, `resnap_hairline_never_lightens`), and `puff` is new and unswept.

## What to do with it

- The dead list is a cleanup queue, not a verdict: each flag is retired, re-scoped, or kept with a reason in its config comment. Kent's call per flag.
- Before/after pictures for eight of these flags (`forbid_gap_mm`, `small_print_floor`, `small_lettering_skeleton`, `overlap_by_angle`, `hairline`, `bg_structural`, `lettering_words`, `fill_technique=fur`) are in Kent's private Flag Sweep Gallery artifact; they include client artwork and are not committed.
