# The `rec4_mask` flip — handoff, 2026-09-07

**Status: INCOMPLETE. The branch `claude/emb-bot-docs-gaps-u2lgij` is pushed
with the five defaults FLIPPED ON and the suite knowingly RED.** No PR is open
for it. Do not merge it as it stands; do not assume a red run here is a
regression until you have read this file.

Kent's ruling 2026-09-07: flip the **`rec4_mask`** set — `satin_patch_junctions`,
`bind_resnap_all_classes`, `revalidate_small_shapes`, `satin_per_stroke`,
`resnap_mask_matches_grader`. Measured as one arm of `tools/flip_sheet.py`:
11 of 26 fixtures move, −2,965 stitches, −22 blocks, −21 cones, **five grades
up and none down**. He did NOT flip `dissolve_phantom_blends`; that stays OFF
and its 2026-09-04 ruling stands.

## What is DONE (committed and pushed)

1. **The five defaults are `True`** in `digitizer_core/config.py`, each with the
   ruling recorded in its own rationale block.
2. **Their own tests inverted**, keeping discrimination: every one asserts the
   default equals ON **and** differs from OFF, so a flag going inert still
   fails. (`test_bind_resnap_all_classes` 13 passed, and the others below.)
3. **`conftest.PRE_REC4_MASK` + `legacy_cfg()`** — the five flags at pre-flip
   values, for tests of OTHER features. Its docstring carries the rule that
   matters: pin a test that needs a CONDITION back; do NOT pin one whose
   subject genuinely changed.
4. **Tests of other features triaged** into three treatments, deliberately:
   - *pinned* — `test_color_stops_merge`, `test_thread_match_better_spool`,
     `test_thread_match_area_in_message`, `test_thread_match_enclosed_background`,
     `test_duplicate_cone_layers`, `test_merge_adjacent_same_thread`,
     `test_shape_overrides`, `test_phantom_blend_photo`;
   - *updated* — `test_raw_score_metric`, because it reports what the SHIPPED
     engine does (see the finding below);
   - *rewritten* — `test_thread_revalidate_palette`, which asserted the exact
     invariant the flip removes.
5. **The goldens do NOT move, measured** — see "Findings" below. No key of
   `flat_lane_golden.json` was recaptured and none needed to be.

## What REMAINS

- [ ] **Re-run the pinned batch.** Last run: 3 failed, 129 passed, 5 errors.
      The 5 errors were a missing `PRE_REC4_MASK` import in
      `test_phantom_blend_photo` — **fixed, uncommitted at the time of writing,
      re-verify.** Genuinely open: `test_duplicate_cone_layers`
      (`test_off_leaves_the_design_exactly_as_it_was`,
      `test_an_explicit_layer_override_still_beats_the_fold`) and
      `test_shape_overrides::test_forced_satin_on_a_fill_classified_shape`.
- [ ] **Recapture the scorecard baseline.** `tools/corpus_scorecard.py capture`.
      **The diff is DONE and clears the bar**: 22 fixture/garment combos moved
      and **no new blocking finding anywhere**, which is the only thing that
      script enforces. The protocol requires every mover attributed in the
      recapture commit — the attribution is drafted below.
- [ ] **Doc sweep.** `-272` is quoted in 5 places and is now **-146**
      (`docs/scope-history.md`, `docs/yardstick-disagreements-2026-09-06.md`,
      `digitizer_core/preflight.py`, `tools/flip_sheet.py`, `tools/floor_depth.py`).
      "DEFAULT OFF" for the five flags appears across 4–6 docs each.
      `docs/flip-sheet-2026-09-06.md` needs the ruling recorded.
- [ ] **Full suite**, then a PR. Expect the three documented platform reds
      (`test_pushcomp`, `test_flat_lane_byte_identical`,
      `test_stage2_photo_segment`) and NOTHING else.

## Scorecard movers, attributed

Every one is an improvement and every one ties to a named flag.

| fixture | moved | flag |
|---|---|---|
| `drone_render` (both garments) | `THREAD_MATCH_POOR:block` **x4 → x3**, warn x12 → x6, cones 16 → 11, worst ΔE 14.1 → 12.9 | `bind_resnap_all_classes` + mask |
| `photo_chrome_specular` @ left_chest | **C 64 → B 76**, `STITCHES_TOO_SHORT` resolved, satin_shapes 2 → 8, satin_steps 133 → 2522, −1,998 stitches, trims 2.4 → 3.5 | `satin_per_stroke` |
| `photo_chrome_specular` @ hat_front | **76 → 88**, same signature | `satin_per_stroke` |
| `screenshot_phone_ui_golke` | worst ΔE **33.0 → 23.9** | `revalidate_small_shapes` + mask |
| `enthusiast_logo` @ hat_front | uncovered_worst 0.5 → 0.2 mm² | `satin_patch_junctions` |

Full diff: `digitizer/build/scorecard_diff_2026-09-07.txt` (gitignored, so
re-run `diff` if that container is gone). Twelve distinct fixtures moved:
becker, tires, drone, enthusiast, bridge_bar, gaulke, golden_tee, fremont,
chrome_specular, dof_meadow, scene_stub, screenshot.

## Findings worth keeping even if this flip is abandoned

**1. The goldens do not move, and the record said they did.** Every entry on
these flags — MASTER_SCOPE, the config comments, my own commit message —
claimed the flip "moves the flat and gradient goldens the phase-4 spec pins".
Measured key by key against a pre-change worktree on one machine:
`logo_whitebg`, `logo_alpha`, `ribbon_curve` are byte-identical under the
shipped engine, and `photo/enthusiast_logo` is **identical between the
pre-change tree and the shipped one** (its disagreement with the stored golden
is this container's documented platform drift, unchanged). Those four fixtures
have no palette escape, no sub-200-px shard, no branchy letterform, no bare
junction and no halo, so the five flags have nothing to act on. The golden
churn argument was always about the SCORECARD. Corrected in MASTER_SCOPE and
in `config.py`.

**2. `screenshot_phone_ui_golke`'s unclamped depth is −146, not −272.** The
flip halves it. Its printed grade is still F 0 — which is exactly the blindness
`raw_score` exists to see through (yardstick row 6), now demonstrated by a real
improvement rather than argued from a hypothetical. `test_raw_score_metric`
carries the new number deliberately rather than being pinned.

**3. The failures are mostly the flip REMOVING each test's subject**, not
breaking it: the revisit-hoist test has no revisit to hoist because
`bind_resnap_all_classes` already removed the duplicate cone;
`test_bridge_bar_loses_its_grey_cones` needs `0182` to be there to lose, and it
is not. That is why the triage is three-way rather than a bulk assertion
update.

## Traps hit while doing this, so they are not re-hit

- `@lru_cache` on a function taking a `PipelineConfig` raises TypeError —
  that dataclass is unhashable. It surfaces as test **ERRORS**, not failures,
  which reads differently in a log and is easy to skim past. Key on the flag.
- A `**PRE_REC4_MASK` splat with no matching import is also an ERROR, not a
  failure, and cost a whole 10-minute batch run. Check `--co` after editing.
- After pinning a file's `_cfg` to `PRE_REC4_MASK`, any helper built on it
  (`_default_digest`) stops meaning "the shipped engine". A test about the
  shipped default then compares the wrong pair and fails for a reason that
  looks like a real regression.
