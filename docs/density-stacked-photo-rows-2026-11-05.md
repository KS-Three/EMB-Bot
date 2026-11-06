# DENSITY_STACKED on five photo rows since 10-05: rendered and attributed (measure only)

*(measured 2026-11-05, HEAD 9660b28b, `digitizer/tools/density_stacked_rows.py`; nothing flipped, no default moved)*

## Result in one paragraph

All five rows reproduce on this box to within 4 stitches of the committed baseline (39,984 / 22,525 / 31,904 here
against 39,984 / 22,525 / 31,908). **None of the three named suspects is the cause**: `photo_cutout_min_kept`,
`color_cap_sewn` and `dark_ink_floor_rescue` each leave dof_meadow left_chest unchanged (21,437 stitches, same patch).
The finding is also not `border_by_size`, `border_from_outline`, `border_by_size_fabric_edges` or
`keep_dark_thin_strokes`: each toggled OFF at HEAD still shows it. It first appears between two first-parent trees,
**46949f78 (2026-10-26, absent)** and **ad218cea (2026-10-29, present)**, 78 commits apart. The bisect below then pins it to
one merge (5ff48c56, PR #1143). What the patch IS is clear from the renders: a small tonal band (its own fill plus a satin ring) sewn on top
of the big ground fill beside it, which is defect 20's shape (photo tonal splitting stacking thread).

## Path: which route this ran on

This box HAS a rembg venv (junctioned into the worktree), but the rembg worker did not finish inside the 120 s
`photo_prep_background_removal_timeout_s` on this loaded laptop (a hand run of the worker went past 180 s), so every
row logged `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE` and took the plain classical route, **the same route CI and the cloud
capture take**. That is why the stitch counts match the baseline. Consequence: `photo_cutout_min_kept` is unreachable
on this path (its guard sits in the branch that needs a cutout), so it cannot explain a CI-measured move. Where a
working rembg refuses a cutout (meadow and sunset keep 0-2%, see the `config.py` comment) the whole frame is sewn;
that is a separate local-only effect this run did not measure.

## The five rows at HEAD (scorecard config, 80 mm)

| Row | Grade / score | Stitches (10-05 ruler -> now) | peak units | over_warn mm2 | patches | worst patch mm2 | worst patch at (mm) |
|---|---|---|---|---|---|---|---|
| chrome_specular hat_front | C 64 | 36,555 -> 39,984 | 12.63 | 35.0 | 1 | 35.0 | (1.9, 19.1) |
| dof_meadow left_chest | C 64 | n/a -> 21,437 | 9.48 | 28.0 | 1 | 28.0 | (-3.6, -12.8) |
| dof_meadow hat_front | C 64 | 21,993 -> 22,525 | 10.96 | not recorded | 2 | 28.0 | (-28.7, 5.6) |
| sunset_backlit left_chest | B 76 | 25,813 -> 31,904 | 13.78 | 42.0 | 1 | 42.0 | (-23.0, -10.2) |
| sunset_backlit hat_front | B 76 | n/a -> 31,410 | 12.77 | 198.0 | 5 | 57.0 | (-3.8, -16.7) |

Renders (`stitchviz.render_design`, lit, 12 px/mm, worst patch circled in red) are in
`docs/renders/density-stacked-2026-11-05/` as `photo_<name>_<garment>_head.png`. The renderer draws the three passes of
a bean as one thread (DOCTRINE), so a ring can look lighter than its thread count; the number comes from the coverage
grid and the picture only says where.

## Attribution table (dof_meadow left_chest, one row, arms run serially)

| Arm | Stitches | DENSITY_STACKED | peak units | worst patch mm2 |
|---|---|---|---|---|
| HEAD | 21,437 | present | 9.48 | 28.0 |
| `photo_cutout_min_kept = 0.0` (pre-#1179) | not run: unreachable on this route, identical by construction | present | - | - |
| `color_cap_sewn = False` | 21,437 | present | 9.48 | 28.0 |
| `dark_ink_floor_rescue = False` | 21,437 | present | 9.48 | 28.0 |
| `keep_dark_thin_strokes = False` | 21,437 | present | 9.48 | 28.0 |
| `border_from_outline = False` and `border_by_size = False` | 20,843 | present | 9.48 | 27.0 |
| `border_by_size_fabric_edges = False` | 23,209 | present (2 patches) | 12.21 | 29.0 |
| tree d000e370 (10-05 ruler) | 20,868 | **absent** (B 76) | - | - |
| tree 4d1fbb76 (10-14, first-parent midpoint) | 21,002 | **absent** (B 76) | - | - |
| tree 46949f78 (10-26) | 22,103 | **absent** | - | - |
| tree ad218cea (10-29, #1180) | 20,737 | **present** | - | - |

Reading it: the two border flags move stitches (-594) back toward the 10-05 figure (20,868), yet the patch and its
9.48 peak stay, so the stitch drift and the finding are two separate things. The `fabric_edges` flag lowers stitches
inside the window and its OFF arm makes the finding worse, so it is not the trigger. No arm removed the finding; the
10-26 to 10-29 window is the only attribution this run earned.

The window (`git log --first-parent 46949f78..ad218cea`, 78 commits) holds, among others: `bean_only_lines` ON
(5a3181dc), `keep_dark_thin_strokes` ON (a71fd5cd, ruled out above), `stage0_texture_gate` (75efec5c; the design class
stays `photo_scene` in every tree here, so it is not a reroute), the cutout guard (03098055, unreachable here),
`border_by_size_fabric_edges` ON (ruled out above), and `script_strokes`, `fine_bars_satin`, `outline_loop_mitre` ON.
Not bisected further for time. Next step: the same one-row digitize on 4-5 more first-parent trees (2-4 minutes each on
an old tree, `tools/density_stacked_rows.py` copied in).

## What the stacked patch is, per render

- **chrome_specular hat_front**: a satin tonal-band ring (thread 0108, 4,000 satin points) crossing a lighter band's
  fill on the ball's lower seam; four shapes meet there (one is a 0.4 mm2 run speck). Tonal band over ground, the ring
  doubling the neighbour band's fill.
- **dof_meadow left_chest**: a 42 mm2 olive band (fill plus its `border:border` satin ring, 170 points) lying on the
  2,199 mm2 ground fill in the sky. Small band over a big ground fill, ring included.
- **dof_meadow hat_front**: the ground fill's own satin ring (1,475 satin points) crossing two small same-thread fills.
- **sunset_backlit** (both): satin rings round each sky band (2,000 to 2,400 satin points per band) lying over the next
  band's fill; hat_front has five patches totalling 198 mm2. Band-edge ring over neighbour fill, which is what a tonal
  split produces.

None is a kept-frame background under a subject (no cutout in any run) or a cap/border over a designed object: every
patch is two tonal bands from the photo lane's own split on top of each other.

## Bisect: first-parent commits 46949f78 (absent) to ad218cea (present), dof_meadow left_chest, classical route

Oldest-first halving, one digitize per tree, serial (tree list from `git rev-list --first-parent`).

| Commit | Date | DENSITY_STACKED | Stitches | worst_patch_mm2 |
|---|---|---|---|---|
| 46949f78 | 10-26 | absent | 22,103 | - |
| 8341d1f7 | 10-27 | absent | 22,103 | - |
| 1d83bc4c | 10-27 | absent | 22,103 | - |
| 1c69607d | 10-27 | absent | 22,103 | - |
| 9d097c1d | 10-27 | absent | 22,103 | - |
| **5ff48c56** (merge of PR #1143, `white-recipe-every-job`) | 10-27 | **present** | 22,534 | 27.0 |
| 1ce2af22 | 10-27 | present | 22,534 | 27.0 |
| ad218cea | 10-29 | present | 20,737 | - |

**First bad: 5ff48c56, the merge of #1143.** Its first commit f53d6508 ("Flip the white-keyline recipe onto every
job", Kent 2026-10-27) made the MFab recipe's switches plain defaults for every job: `silhouette_underfill`,
`silhouette_underfill_panels`, `silhouette_underfill_rim`, `enclosed_white_keyline`, `keyline_fold_slivers`,
`skip_covered_shapes`, `keyline_loop_chain`, `absorb_fragments` all went False to True in `config.py`.

**Mechanism.** The under-fill recipe sews a full fill of the ground under every piece contained in it ("the pro sews
every contained piece on its ground"). On a photo's tonal split each band is a contained piece, so each band, with its
own satin ring, now lands on a complete ground fill and the three layers stack to 9.5 to 13.8 units.

Confirmed at HEAD with one arm: `silhouette_underfill`, `_panels` and `_rim` all OFF gives **20,873 stitches (10-05 was
20,868), B 76, DENSITY_STACKED gone**. Which of the three does the work was not split further. The other recipe
switches were left ON in that arm.

## `tonal_split_ceiling` ON at HEAD (same row)

Clears the finding: **B 88, DENSITY_STACKED absent, 14,059 stitches** against 21,437 (-34%). It does so by keeping
the whole-design plan (the tonal split is dropped), so it removes the banding the photo was split for, not just the
stack. The under-fill arm above clears it at 20,873 stitches with the split intact.

## Verdict for the foreman

A flag Kent rules on, not a code bug: the recipe switches landed in #1143 as defaults for all art. Cheapest lever is
`silhouette_underfill` (with `_panels`, `_rim`) gated off for the photo classes (`photo_scene`, `photo_subject`), keeping
it for flat and gradient logos where it was measured. That gate is a code change under Kent's ruling. Measured here on
one row (dof_meadow left_chest); the other four rows were not re-run with the arm.

## Reproduce

```
cd digitizer
.venv/Scripts/python tools/density_stacked_rows.py --arm head --out run.json --render ../docs/renders/density-stacked-2026-11-05
.venv/Scripts/python tools/density_stacked_rows.py --arm border_both_off --only meadow.png/left_chest
```

Arms: head, cutout_off, cap_off, floor_off, dark_thin_off, border_outline_off, border_size_off, border_both_off,
fabric_edges_off, underfill_off, tonal_ceiling_on. `--ci-path` hides the rembg venv. Each digitize is 3.5 to 5.5 minutes on this laptop.
