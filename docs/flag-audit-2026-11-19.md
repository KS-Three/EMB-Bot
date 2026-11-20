# Flag consolidation audit — 2026-11-19

Read-only audit of every engine switch on `main` `70ff3902`. Nothing in the
engine changed. This sorts each switch into one tier: fold it into the code,
delete it, keep it, or ask Kent.

## The numbers

- **342 switches:** 295 bool fields on `PipelineConfig`, 192 ON and 103 OFF,
  plus 47 `cfg.extra` keys that are not fields. On top of these sit 113
  non-bool tunables (44 `None`, 43 float, 16 str, 10 int), which this audit
  does not tier.
- **`digitizer_core/config.py` is 8,180 lines: 7,518 comment, 590 code, 72
  blank.** Each flag's history (rulings, measurements, PRs) is written into
  its comment.
- **95 of the 192 ON flags flipped after the 2026-10-27 engine snapshot, 71 of
  them in the last 14 days.** On 2026-11-17 three were reverted (the apex_pro
  family). Most of the ON set is still young enough to come back out.

## What a fold actually costs

Deleting the `if cfg.x:` branch is the easy part. Three things push back:

1. **Tests pin the OFF arm.** 231 test files set a pre-10-27 ON flag to
   `False`, and 161 do the same for a post-10-27 one. When a flag folds, its
   OFF-arm tests have to be deleted, not fixed.
2. **The frozen engine snapshot spreads every field.**
   `tests/conftest.py:frozen_cfg` builds `PipelineConfig(**ENGINE_2026_10_27)`,
   and 12 test files use it directly. Removing a field the snapshot names
   raises `TypeError` unless `engine_snapshot()` learns to drop retired keys.
   Folding a flag that flipped AFTER 10-27 also moves every md5 that
   `frozen_cfg` pins wherever that flag acts. So tier C waits for a
   rolled-forward snapshot, which is the mechanism the conftest comment
   already describes ("Roll forward with a NEW dated file after a flip wave").
3. **The service refuses unknown config keys.**
   `digitizer_service/app.py:_validate_config_dict` returns 400 `unknown
   config field(s)`. A removed field would break any script or old client
   that still sends it, so retired names need an accept-and-ignore set. The
   Studio itself sends only tier P fields, and none of those fold.

## Proposed order

| Step | Scope | Proof required |
|---|---|---|
| 1 | Plumbing: a `RETIRED_FIELDS` set in `config.py`; `engine_snapshot()` and the service ignore retired keys. Delete tier D (6). Fix the 13 stale comments (ON flags whose comment still says "built OFF"). | Full digitizer suite; `tools.flag_sweep` byte-identical on all 44 jobs |
| 2 | Fold tier A (20): ON before 10-27, no test sets them False | Same: byte-identical on 44 jobs. Update the tools that build an OFF arm for these. |
| 3+ | Fold tier B (67) in batches by stage, deleting each flag's OFF-arm tests | Byte-identical per batch |
| later | Roll the snapshot forward once tier C flags have stayed ON for 30 days without a revert, then fold them | New dated snapshot; byte-identical |

When a flag folds, its comment's history moves to a docs file with the PR
pointer, and the config keeps nothing for it. The 7,518 comment lines shrink
in step with the folds.

Byte-identical is the bar for every fold PR: a fold that moves a stitch
anywhere is a bug in the fold, not a change to ask about.

## For Kent

- **Tier D (6):** delete on your rulings below. Confirm.
- **Tier E (7):** your call on each: delete, keep, or rebuild.
- **Tier H (73):** OFF layout switches with no final ruling found. Under the
  rule "built OFF = not delivered, ask the flip", each one is either a flip
  candidate or dead code. The largest group is the `lettering_columns_*`
  `cfg.extra` keys from the MARINE / Toat / Becker work.

## Method and limits

- Fields, defaults and comments come from `tools.flag_ledger.fields`.
  `cfg.extra` keys come from `tools.scope_flag_lint.extra_readers` (AST over
  `digitizer_core/` and `digitizer_service/`).
- "ON since" is the latest commit that wrote the current default
  (`git log -p` on `config.py`). "Flipped after 10-27" means the field's value
  in `tests/engine_2026_10_27.json` differs from today's default.
- "Tests set False" is a regex for `name=False` or `"name": False` in
  `tests/`. A test that turns a flag off another way (`setattr`, a built dict)
  is missed, so tiers A and B can undercount OFF arms. The byte-identical
  check catches what the regex misses.
- "Product option" means the name appears in `app/src/` or
  `digitizer_service/`. Generic names (`satin`, `underlay`) land there and
  are kept regardless.
- Tiers D and E come from rulings checked by hand against memory notes and
  MASTER_SCOPE. The F/G/H split for OFF flags is read from comment and memory
  wording (gate 1, sew-out, instrument), which is rough. Treat an F or H row
  as a starting guess.

## Tiers

### A. Fold now: ON before the 10-27 snapshot, no test sets it False (20)

| Flag | ON since | Core files | Tools with an OFF arm |
|---|---|---|---|
| `split_satin` | 2026-07-31 | 3 | 3 |
| `satin_house_fourfold` | 2026-09-03 | 2 | 1 |
| `fill_travel_under_cover` | 2026-09-03 | 3 | 1 |
| `enforce_color_cap` | 2026-09-10 | 9 | 1 |
| `revalidate_small_shapes` | 2026-09-10 | 2 | 1 |
| `resnap_mask_matches_grader` | 2026-09-10 | 1 | 1 |
| `layer_palette_from_regions` | 2026-09-12 | 3 | 0 |
| `satin_cap_recentre` | 2026-10-03 | 2 | 0 |
| `satin_outer_rail_pitch` | 2026-10-06 | 2 | 0 |
| `satin_join_square` | 2026-10-07 | 2 | 0 |
| `satin_slab_serifs` | 2026-10-08 | 2 | 1 |
| `satin_free_end_square` | 2026-10-08 | 2 | 1 |
| `text_cluster_rescued_ink_link` | 2026-10-15 | 2 | 1 |
| `lettering_columns_rail_axis` | 2026-10-20 | 3 | 1 |
| `text_cluster_counters_as_drawn` | 2026-10-20 | 2 | 1 |
| `lettering_columns_inside_stagger` | 2026-10-24 | 2 | 0 |
| `text_cluster_wide_letters` | 2026-10-24 | 2 | 0 |
| `border_from_outline_line_art_guard` | 2026-10-25 | 2 | 0 |
| `small_text_cap_reach_edges` | 2026-10-25 | 2 | 0 |
| `outline_loop_mitre` | 2026-10-26 | 3 | 0 |

### B. Fold after deleting off-arm tests: ON before 10-27, tests pin the OFF arm (67 flags, 231 test files)

`alpha_edge_extend` (2), `alpha_edge_extend_stage0_whole` (2), `alpha_edge_extend_upscaled_only` (1), `beanie_knockdown` (1), `bind_resnap_all_classes` (1), `blend_fallback_underlay` (2), `border_by_size` (17), `border_from_outline` (5), `borders_last` (2), `clip_parent_keeps_ink` (1), `compact_solids_satin` (3), `design_ramp` (2), `dissolve_phantom_blends` (4), `edge_cap_follow_adjacent` (1), `edge_cap_skip_bean_letters` (2), `edge_cap_skip_lettering` (1), `enclosed_alpha_hole_parts` (3), `fill_bridge_cut` (1), `fill_turn_slant` (2), `fill_underlay_cross` (3), `fine_bars_satin` (1), `keep_thin_strokes` (12), `legibility_check` (2), `lettering_columns` (14), `lettering_columns_corner_fold` (2), `lettering_columns_fold_cuts` (1), `lettering_columns_icon_guard` (1), `lettering_columns_ink_link` (1), `lettering_columns_inside_connectors` (3), `lettering_columns_skip_blobs` (6), `lettering_columns_small_bold` (1), `lettering_columns_small_stem` (2), `lettering_columns_square_ends` (3), `lettering_columns_text_lean` (1), `merge_adjacent_same_thread` (5), `merge_duplicate_cones` (1), `photo_prep` (20), `photo_prep_background_removal` (5), `rehome_resnapped` (1), `robust_region_colour` (4), `satin_corner_twigs` (4), `satin_crown_cover` (4), `satin_exit_toward_next` (1), `satin_house_anchor` (2), `satin_house_from_line` (1), `satin_junction_stack` (4), `satin_lettering_split` (4), `satin_rail_comp` (4), `satin_tip_caps` (3), `satin_underlay_short_columns` (3), `shade_palette_bind` (4), `small_dot_rung` (3), `small_dot_rung_lettering` (2), `small_glyph_keep` (3), `small_shape_rescue` (3), `small_solids_satin` (4), `small_text_bay_mouth` (2), `small_text_true_size` (17), `snap_region_edges` (4), `strip_letterbox` (1), `subpixel_corner_runs` (1), `subpixel_edges` (3), `subpixel_edges_upscaled` (4), `tie_in_off` (3), `trim_bury_under_later` (2), `two_tone_snap` (2), `white_keyline_art_recipe` (1)

### C. Wait: flipped ON after the 10-27 snapshot (95)

Flipped 14+ days ago (24): `absorb_fragments` (10-27), `bean_ink_outlined_letters` (10-27), `border_by_size_fabric_edges` (10-29), `color_cap_sewn` (11-01), `dark_ink_bean` (10-29), `dark_ink_floor_rescue` (11-04), `enclosed_white_keyline` (10-27), `fill_bridge_cut_exposed` (10-30), `fill_seam_order` (10-30), `fill_seam_order_priced` (10-30), `keep_dark_thin_strokes` (10-28), `keyline_fold_slivers` (10-27), `keyline_loop_chain` (10-27), `knockdown_shorter_walk` (10-30), `lettering_columns_italic_lean` (10-27), `lettering_stray_word_thread` (11-02), `script_strokes` (10-27), `silhouette_underfill` (10-27), `silhouette_underfill_panels` (10-27), `silhouette_underfill_rim` (10-27), `skip_covered_shapes` (10-27), `small_text_reset_grow_away` (10-26), `text_cluster_part_touching` (10-27), `thread_match_excess_gradient` (10-30)

Flipped under 14 days ago (71): `blend_shade_median`, `border_by_size_corner_loss`, `border_from_outline_follow_shape`, `border_from_outline_hairline_run`, `border_significant_ring_room`, `cap_merged_layer_home`, `color_cap_fuse_split_tones`, `color_cap_least_loss`, `compact_satin_keeps_gaps`, `counter_fan_satin`, `dark_ink_bean_by_width`, `dropped_element_v2`, `enclosed_white_keeps_known_colour`, `enclosed_white_skip_transparent`, `fine_bar_survive`, `flat_blend_band_any_scale`, `flat_light_text_runs`, `flat_page_fringe_soft_ramp`, `flat_ramp_blend_dissolve`, `group_consistent_border_by_size`, `group_consistent_fill_angle`, `group_consistent_outline_body`, `group_consistent_thread`, `group_consistent_tier`, `inshape_piece_lift`, `keyline_fragment_drop`, `lettering_columns_a_bar`, `lettering_columns_absorb_unsewn`, `lettering_columns_block_butt`, `lettering_columns_block_butt_small`, `lettering_columns_block_lean`, `lettering_columns_connectors_edge_walk`, `lettering_columns_corner_fold_apex_side`, `lettering_columns_cover_hops`, `lettering_columns_off_line_mark`, `lettering_columns_off_line_mark_single_only`, `lettering_columns_r_bowl`, `lettering_columns_ribbon_handback`, `lettering_columns_ring_floor`, `lettering_columns_stem_wedge_cap`, `lettering_columns_stroke_floor`, `lettering_columns_whole_letter_floor`, `lone_glyph_keep`, `outline_frame_guard`, `outline_inlets_kept`, `outline_inlets_teeth`, `page_line_open`, `point_touch_split`, `rope_band`, `round_dot_ring`, `satin_cap_skew_inset`, `satin_free_end_chord_aim`, `satin_rectangles`, `satin_seam_hold`, `satin_thin_arm_stop`, `shadow_to_page`, `silhouette_underfill_ground_guard`, `silhouette_underfill_rim_fabric_edges`, `small_text_handover`, `small_text_reset_bean_follows`, `small_text_reset_ground_ring`, `small_text_reset_one_baseline`, `small_text_reset_tight_word_space`, `speck_prune`, `stage0_scale_relative_grad`, `stroke_bridge_keep`, `text_cluster_mixed_caps`, `text_cluster_nest_door_aspect`, `text_cluster_solid_guard`, `thin_letters_after_ground`, `thread_match_grade_traced_letter`

### D. Delete: OFF, and your ruling is final (6)

| Flag | Ruling |
|---|---|
| `resnap_hairline_never_lightens` | Kent 2026-11-11, with line_chain_one_thread (item 74) |
| `coverage_edges` | Kent 2026-10-12: a NO; already DEPRECATED in __setattr__ (MASTER_SCOPE Waiting 38) |
| `lettering_columns_apex_cut` | Kent 2026-11-14 withdrew the flip: "I want it exactly like the pros" |
| `line_chain_one_thread` | Kent 2026-11-11: "Keep off, very little improvements were made, if any" (item 74) |
| `fill_angle_pro_slant` | Kent 2026-11-09: "Keep OFF, record" (item 73) - cfg.extra |
| `lettering_columns_apex_guard` | with apex_cut, 2026-11-14 - cfg.extra |

### E. Ask: OFF, but the ruling is not final (7)

| Flag | Ruling |
|---|---|
| `photo_enclosed_rim` | Kent 2026-11-14 "Keep off, fix the collapse" - wants a fix, keep |
| `photo_prep_tone` | Kent 2026-11-13 "Switch it off by default" |
| `open_cored_counters` | Kent 2026-10-19 "Leave OFF for now" |
| `lettering_columns_apex_pro` | REVERTED 2026-11-17 (MARINE slab caps, PR #1659) |
| `lettering_columns_apex_pro_joints` | REVERTED 2026-11-17 with apex_pro |
| `lettering_columns_corner_fold_cap_flared` | REVERTED 2026-11-17 with apex_pro |
| `lettering_columns_lean_flat_ends` | Kent ruled ON 2026-11-15, held OFF (flip-run-2026-11-16) - cfg.extra |

### F. Keep: gate 1, waiting on cloth (43)

`bury_step_fine`, `cap_center_out`, `classify_area_weighted`, `cut_every_jump`, `design_angle`, `directional_comp`, `growth_keeps_gaps`, `hair_regions_directional`, `hairline_coverage_guard`, `hairline_from_lines`, `hairline_lines_chain`, `hairline_lines_gradient`, `hairline_lines_logo_refusal`, `hairline_lines_strand_mass`, `hairline_lines_strand_test`, `hairline_over_ground`, `keyline_under_face`, `lettering_columns_rail_pair_bars`, `lettering_word_tiers`, `lettering_words`, `light_thin_stroke_keep`, `merge_chroma_guard`, `overlap_by_angle`, `page_line_front`, `pro_measured_values`, `pull_comp_by_stroke`, `regular_structure`, `satin_hairline_tier`, `satin_hop_under_column`, `satin_mid_entry`, `satin_overlap_run`, `satin_tip_corner_gate`, `satin_tip_floor_cross`, `satin_underlay_on_column`, `script_strokes_pull_by_stroke`, `sliver_prune`, `small_lettering_skeleton`, `small_print_floor`, `stripe_underfill`, `tiny_detail_keep`, `tonal_split_ceiling`, `underlay_all_pieces`, `wide_columns`

### G. Keep: instruments and metric-only switches (11)

`edge_walk_judge_off_walk`, `fill_one_pass_sections`, `fill_seam_aware_sections`, `outline_redraw_native`, `preflight_glyph_metric`, `proofread`, `proofread_guard_clipped`, `satin_floor_content_gate`, `shapefield`, `small_text_reset_report`, `tonal_split_layer_cap`

### H. Your queue: OFF layout switches with no final ruling found (73)

`alpha_extend_keeps_interior` (extra), `applique`, `bg_structural`, `blend_speckle_residual`, `curve_chord_stage4`, `curve_chord_stage4_spare_text`, `dark_ink_ground_innermost` (extra), `dark_ink_refuse_ground_gaps` (extra), `dark_ink_refuse_strays`, `dark_neutral_split`, `edge_cap_walk_covered`, `fill_angle_pro_offset` (extra), `fill_density_boost`, `fill_inside_satin_border`, `fill_order_sewn_paths`, `fill_section_cuts_first` (extra), `fill_section_travel` (extra), `flat_page_fringe_exclude`, `group_consistent_fill_angle_split_ground` (extra), `growth_keeps_gaps_between` (extra), `growth_keeps_gaps_between_min_gap_mm` (extra), `growth_keeps_gaps_between_min_mm2` (extra), `growth_keeps_gaps_between_taper_mm` (extra), `held_hole_bare_only`, `keep_counters`, `keyline_bean_between_fills` (extra), `keyline_loop_fit` (extra), `lettering_columns_a_cap_centered` (extra), `lettering_columns_apex_pro_band_knots` (extra), `lettering_columns_connectors_buried`, `lettering_columns_cover_handback`, `lettering_columns_e_top_arm` (extra), `lettering_columns_end_overlap_cut` (extra), `lettering_columns_flare_top_fold` (extra), `lettering_columns_hairline_leave` (extra), `lettering_columns_judge_entry_free` (extra), `lettering_columns_junction_align` (extra), `lettering_columns_neck_cuts` (extra), `lettering_columns_reading_order` (extra), `lettering_columns_sew_dropped_branch` (extra), `lettering_columns_sew_dropped_hairline` (extra), `lettering_columns_top_slab` (extra), `lettering_contrast_floor`, `monoline_script_satin`, `off_line_mark_row_only` (extra), `outline_loop_split_shared`, `outline_one_band`, `outline_strip_column`, `photo_sequencing` (extra), `photo_work_grid`, `pull_comp_along_stitch_only` (extra), `run_soft_vertices`, `satin_junction_square`, `satin_patch_junctions`, `satin_per_stroke`, `satin_polygon_axis`, `satin_straight_slots` (extra), `script_strokes_drawn_width`, `script_strokes_patch_merge` (extra), `sew_enclosed_white_fields_fill`, `shade_axis_normalize`, `shade_palette_demand`, `silhouette_underfill_photo`, `small_bold_pull_reaches_floor` (extra), `small_letter_ties`, `small_text_keep_tall_letters` (extra), `split_long_inshape_stitches` (extra), `stroke_floor_keeps_lost_strokes` (extra), `text_cluster_adopt_contrast` (extra), `text_cluster_nest_guard`, `text_cluster_nest_guard_rotated`, `thread_match_skip_enlarged_text` (extra), `underfill_untagged_riders`

### P. Keep: product options the Studio or service sends (20)

`bean_only_lines` (ON), `bevel_ring_fold` (OFF), `chain_links` (OFF), `clip_keep_pieces` (ON), `denoise` (ON), `detail_layer` (OFF), `detail_spokes` (ON), `detect_photographic` (OFF), `edge_cap_fold_into_colour` (OFF), `enclosed_by_garment` (ON), `faces_route_flat` (OFF), `hairline` (OFF), `photo_segment_sam2` (OFF), `preflight` (ON), `satin` (ON), `sew_enclosed_counters` (OFF), `sew_enclosed_white` (ON), `stage0_texture_gate` (ON), `stitch_width_auto` (OFF), `underlay` (ON)
