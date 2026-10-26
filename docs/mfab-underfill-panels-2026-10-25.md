# MFab: one black under-fill, the white keyline on it, the small lettering on a white panel (2026-10-25)

Kent, 2026-10-25: "Do you have any workers troubleshooting the satin infill in
between and around letters? Use The M-Fab logo for comparison. The Pro file has
clean sating stitching that follows the flow of lettering and shapes. while your
digitized version is very chaotic."

Nothing changes at today's defaults. The cure for what Kent sees is his flip of
the switches below. This lane makes them reachable cleanly: two fixes to the
existing OFF flag `silhouette_underfill` and its partner switch, and one new OFF
flag, `silhouette_underfill_panels`.

## How the pro builds MFab (hat and LC agree)

- **Block 0:** one black tatami at 22-25 deg under the whole silhouette, letter
  faces included, with a 1.84-1.92 mm closed black satin rim.
- **Block 1:** the white keyline as 2.2-2.4 mm satin loops round each M-FAB
  letter, sewn ON the black. Behind AND WELDING / LLC a white panel, CLOSED under
  the small letters (white under them 1.000).
- **Blocks 2 and 4:** AND WELDING and LLC as black satin AFTER the white
  (35 columns, cross p50 1.55 / 1.50 mm). Black fill under only 0.13-0.15 of
  them.

## M2: where the M-FAB / WELDING bodies vanished under `silhouette_underfill` alone

- `silhouette_underfill.plan` cuts the unsewn white keyline out of the ring's
  closed outline. On MFab LC (96.7 mm) that left a MultiPolygon of 21 parts:
  the band (972.7 mm2) and the letter bodies (269.8, 249.4, 218.4, ... mm2).
- `apply` merges all 26 black inner shapes into the host, dropping them as
  regions: M-FAB and every AND WELDING LLC letter.
- Stage 5 unions the host's grown polygon with that outline (`ground_under`),
  then `_split_clip` keeps the piece carrying the HOST's ink, the band.
  - This happens because `clip_parent_keeps_ink` and `clip_keep_pieces` both
    default ON. `_largest_polygon` is only the both-OFF path.
  - Every body piece carries none of the band's artwork. So each read as pull
    growth and was dropped UNCOUNTED.
- **Result: the host is one 1,151 mm2 polygon, and its coverage of each merged
  body is 0.00.** Nothing sewed them.

**Why #1064 / the flip sheet read 17,540 / 37 on the hat, and today reads
12,308 / 54.** This is a different flag set, not a regression.

- The flip sheet's `silhouette_underfill` row runs on base `_WHITE_SEWN`
  (`sew_enclosed_white` + `enclosed_white_keyline`), and #1064 measured it that
  way. With the white sewn, the outline is never cut, and nothing drops. That is
  arm d2.
- 12,308 / 54 is the under-fill ALONE, the white unsewn. Only
  `test_a_shape_left_unsewn_stays_garment` exercised that path, and it never
  checked that the letters were sewn.

## The build (each part byte-identical with its flag OFF)

**A. `silhouette_underfill` keeps every body.** This touches only the flag's ON
path (`stage5_overlap`).

- An under-fill host's pieces are judged on its artwork AND its outline.
- The bodies are kept as `-clip<k>` pieces of the host. They sew as its fill,
  at ONE angle: the silhouette's `best_fill_angle_deg`, used only when the host
  has no compensation axis.
- d2 is byte-identical: its outline is one piece.
- Test: `test_an_unsewn_keyline_round_two_bodies_leaves_both_sewn`. It fails
  on main's stage 5.

**B. `sew_enclosed_white_fields_fill` never pre-empts an outline loop.**

- `_white_field_fill` declines in two cases:
  - an id the art-outline branch loops (`outline_rings`, passed in by
    `stitch_one`, the seam-ownership pass and the pick order);
  - a keyline band `enclosed_white_keyline` would claim.
- An outline is neither a letter nor a field.
- `borders_last_layers` runs before outlines exist and sees only the
  keyline-band exclusion. This is a residual.
- Tests: two loop tests (each fails on main) and a plain-field test.

**C. `silhouette_underfill_panels` (new, OFF).** It is read only with
`silhouette_underfill`, `sew_enclosed_white` and `border_from_outline` all ON.

- A **rider** meets all of these (`silhouette_underfill.find_riders`):
  - it is text-tagged;
  - it is in the host's thread;
  - it sits 0.9 inside a hole of a sewn white field;
  - more than half of its word is not the art outline's bodies (WELDING's I
    is a body; its word is not).
- Riders are never merged, and they are dropped from the outlines' body lists.
- Each field holding riders fills them a closed panel (`_panels`, tag
  `underfill_rider_holes`). The panel is the parts `keyline_rest` leaves (field
  with rider holes closed, body loops only) that hold a rider hole, plus those
  holes.
- The host's outline gives the panel up, shrunk by `overlap_mm`.
- Riders sew in their own layer right after the field's: black, white, black.
- In stage 7's outline branch the rider rings are dropped, and the rest fill
  runs on the artwork with rider holes closed.
- `art_outlines` is computed once, before the under-fill.
- Tests: `tests/test_silhouette_underfill_panels.py`, with OFF md5 pinned on
  origin/main cdb96d63.

## The numbers

Every arm uses the Studio request at the pro's width, `tools/pro_pair.digitize`,
on this lane.

- The hat is `photo_scene`: rembg runs from the main checkout's venv, with
  `photo_prep_background_removal_timeout_s` 900, and every hat arm logged
  `PHOTO_BACKGROUND_REMOVED`.
- The LC is `CLASSIFIED_GRADIENT`.
- One pystitch reader reads both files, each in its own frame
  (`panels/scripts/panel_metrics.py` in the evidence folder; layering by
  `tier/scripts/layers.py`'s footprints).
- "Small" means the dark blocks sewn after the first light one.

Arms:
- **defaults:** today's engine.
- **b-fixed:** `silhouette_underfill` alone, with fix A.
- **d2:** + `sew_enclosed_white` + `enclosed_white_keyline`.
- **d2+panels:** d2 + `silhouette_underfill_panels`.
- **+ff:** d2+panels + `sew_enclosed_white_fields_fill`.

### Hat (104.9 mm)

| arm | st | trims | under 1 mm | black fp mm2 | white under small | black under small | small columns / cross p50 | white clamped | white under 2+ loops | black m |
|---|---|---|---|---|---|---|---|---|---|---|
| pro | 17,568 | 19 | 1,449 | 3,258 | 1.000 | 0.127 | 35 / 1.55 | -- | 2.2% | 27.4 |
| defaults | 11,125 | 59 | 2,371 | 3,148 | n/a | n/a | n/a | -- | -- | 20.9 |
| b-fixed | 23,257 | 84 | 10,466 | 3,335 | n/a (white unsewn) | n/a | n/a | -- | -- | 30.3 |
| d2 | 18,164 | 39 | 4,392 | 3,745 | merged | merged | merged | 34.7% | 17.1% | 27.5 |
| d2+panels | 21,413 | 62 | 5,958 | 3,285 | 0.973 | 0.158 | 43 / 1.80 | 37.6% | 10.3% | 27.6 |
| d2+panels+ff | 21,717 | 58 | 6,277 | 3,285 | 0.976 | 0.158 | 44 / 1.75 | 37.4% | 10.3% | 27.6 |

### LC (96.7 mm)

| arm | st | trims | under 1 mm | black fp mm2 | white under small | black under small | small columns / cross p50 | white clamped | white under 2+ loops | black m |
|---|---|---|---|---|---|---|---|---|---|---|
| pro | 15,786 | 20 | 1,395 | 2,773 | 1.000 | 0.148 | 35 / 1.50 | -- | 2.4% | 23.8 |
| defaults | 11,691 | 69 | 4,630 | 2,632 | n/a | n/a | n/a | -- | -- | 17.9 |
| b-fixed | 19,750 | 103 | 11,341 | 2,751 | n/a (white unsewn) | n/a | n/a | -- | -- | 21.3 |
| d2 | 16,943 | 45 | 5,338 | 3,154 | merged | merged | merged | 36.7% | 17.7% | 21.8 |
| d2+panels | 19,333 | 65 | 6,688 | 2,811 | 0.977 | 0.137 | 37 / 1.46 | 38.1% | 10.6% | 21.9 |
| d2+panels+ff | 19,417 | 70 | 6,872 | 2,811 | 0.987 | 0.137 | 37 / 1.46 | 38.1% | 10.3% | 21.9 |

Trims are read off the DST, so they differ slightly from the plan's.

**Colour changes:** the pro has 4 (black, white, black, white, black). Ours with
panels has 2 (black, white, black): LLC is a rider of the one white field, not
a second white block.

**White stitches under 1 mm** (`tiny`):

| arm | hat | LC |
|---|---|---|
| pro | 8.6% | 9.2% |
| d2 | 37.4% | 47.9% |
| d2+panels | 39.2% | 48.8% |

The panels do not cure them. They are the loops' own (residual).

What the numbers say:

- **d2+panels has the pro's layering on both files.**
  - White under the small letters: 0.973 / 0.977 (pro 1.000).
  - Black under them: 0.158 / 0.137 (pro 0.127 / 0.148).
  - Black footprint: 3,285 / 2,811 mm2 (pro 3,258 / 2,773), against d2's
    3,745 / 3,154.
  - The lower line is black satin again: 43 / 37 columns at cross p50
    1.80 / 1.46 (pro 35 / 35 at 1.55 / 1.50).
  - White under two or more loops: 17% -> 10% (pro ~2%).
- **It costs stitches and trims against d2:** +3,249 / +23 on the hat (pro
  17,568 / 19).
  - The riders sew as Column-lane letters, each with its own entry and exit.
  - The panel is a white fill that d2 did not have.
- **b-fixed sews the bodies** (black 20.9 -> 30.3 m on the hat, pro 27.4). But
  it is no target arm: with the white unsewn, each body is a separate black
  fill island, ringed by the Studio's bean edge cap (4,789 edge-cap points on
  the hat), so stitches under 1 mm and trims jump. Its job is to stop the flag
  sewing NOTHING where a body was.
- **fields_fill (+ff) now leaves the keyline loops alone** (part B). It still
  fills the other white fields, which adds 304 / 84 stitches.

### OFF and bystanders

- **LC defaults DST md5 `da38d9b2`, plan `f444ae5e`:** identical on main
  cdb96d63, on main 82b0bf28, and on this lane.
- **Hat defaults plan `3673370d`:** main's (the rembg route).
- **d2 is byte-identical before and after parts A and C:** LC `d43b1919`, hat
  `21a27cf3`.
- **With the d2 flags ON, panels ON vs OFF:** see the bystander table in the PR
  body.
  - Becker hat small: identical (md5 `2e1d3e2a` both ways, no riders).
  - Riders found on each other job: see the PR.

## Crops (25 px/mm, each design in its own frame, the pro last)

`docs/renders/mfab-underfill-panels-2026-10-25/` covers hat and LC.

- **Boxes:** M (box0), AND (box3), WELDING/LLC, and the whole design.
- **Renders:** true colour (thread colours on mid-grey) and angle-coloured
  (hue = stitch direction).
- **Rows:** defaults | b-fixed | d2 | d2+panels | pro.

## Residuals

- **M-FAB keyline corner spikes:** `keyline_runs` clamps 35-38% of the white
  crosses by reach. That is the outline-loop corner mitre in `stage6_border.py`,
  another lane's (apex-cut, task 10).
- **The loops are 0.5 mm narrow** against the pro's 2.2-2.4. `art_outline`
  measures the width (task 9).
- **No black outer satin rim** (the pro: 1.84-1.92 mm).
- **No satin edge on the panel** (the pro: 1.3-1.4 mm). No existing builder
  does it without a new constant, so it is not built.
- **White stitches under 1 mm stay ~4x the pro's.** They come from the loops,
  not the panel.
- **Riders cost trims** (+20 to +23 against d2).
- **`borders_last_layers` predicts without the outline set.** With fields_fill
  ON it still counts an art outline that is not a keyline band as a fill.
