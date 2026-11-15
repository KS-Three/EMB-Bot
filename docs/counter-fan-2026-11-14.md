# A small three-sided counter as one fanned satin (2026-11-14, built OFF)

`cfg.extra["counter_fan_satin"]`, `digitizer_core/stage6_counter_fan.py`, hook in
`stage7_sequence.stitch_one`. Kent's MFab pin "random stitch in the middle", and his
word that day: "I want it exactly like the pros".

## The pro's stitches on MFab's A counter (hat, 104.9 mm)

These were read off his file, registered at IoU 0.99.

- **Underlay.** About 30 white zigzag stitches, then a short run up into the narrow
  tip.
- **Top.** ONE satin from the base to the tip.
  - The crosses turn steadily: 3° at the base, about 40° mid-shape, and 80-90° in
    the narrow arm, where they run along it.
  - Their length falls from 5.73 mm at the base to 1.5 mm at the tip.

Ours sewed the counter as split satin columns, or as a fill, depending on size.

## The construction: a lagging-pivot sweep

- **The wedge.**
  - The tip is the sharpest convex corner of the ring simplified at 0.4 mm, and
    the base corners are the next two.
  - The rails walk the REAL ring between them. The simplified ring left the
    traced edge's bulge bare (0.86 covered at 90 mm).
- **The sweep.**
  - The outer end steps evenly up the longer rail.
  - The inner end climbs the other rail but stops 0.22 of it short of the tip,
    where the pro's last arm crosses end.
  - So near the tip the crosses turn about it.
  - Paired rails, the earlier prototype on `claude/mfab-fan-proto`, keep the
    crosses parallel, and the arm never turns.
- **The stitches.**
  - An underlay zigzag from the tip to the base, inset 0.4 mm. In the arm it
    becomes the run up the tip.
  - Then satin from the base to the tip, each end pushed out by the fabric's
    pull.
- **The refusals** (the shape sews as it did):
  - no three dominant corners, or a shape that does not fill its corner
    triangle;
  - a cross over the ceiling;
  - a cross leaving the shape;
  - a base under the fill floor (`MIN_FILL_WIDTH_MM`, a speck);
  - a sweep covering under 0.9 of the shape.
- **Where it applies.** Only a shape whose own tier is `auto`, an enclosed
  background, and not a letter.

## The ceiling is gate 1

The ceiling is `machine.SATIN_MAX_WIDTH_MM`, 5.0 mm, read as a parameter.

| MFab hat width | our base cross | fan |
|---|---|---|
| 104.9 mm (the pro's) | 5.37 mm | refused |
| 96 mm | 5.11 mm | refused |
| 93 mm | 4.95 mm | sews |
| 90 mm | 4.79 mm | sews |
| 75 mm | | sews |

At MFab's own size the pro crosses 5.73 mm. Whether ours may go past 5.0 is Kent's
call, after a sew-out.

## Closeness to the pro

The measure is `tools/apex_pro.measure_window`. It paints each file's stitch
directions in a window round the counter and gives:

- the mean angle error where both sew;
- the seam distance;
- the shared mm²;
- the IoU.

The pro's file is registered to ours, so it is scaled to the same width.

| width | today: angle err | fan: angle err | today: seam | fan: seam | shared mm², today → fan | IoU, today → fan |
|---|---|---|---|---|---|---|
| 90 mm | 29.9° | **7.1°** | 3.54 mm | 0.67 mm | 20.7 → 22.0 | 0.525 → 0.556 |
| 75 mm | 68.7° | **6.9°** | 0.52 mm | 0.29 mm | 13.3 → 15.9 | 0.474 → 0.568 |

Sheets (gitignored): `digitizer/eye_pairs_out/mfab-triangle-1114/sheets/fan_mfab_hat_<w>.png`,
laid out art | today | fan | pro.

## Every other small triangular counter in the kits

The 43 apex-corpus designs, at their corpus widths:

- They hold 144 sewn enclosed counters. Nine read as wedges.
- **None but MFab's would take a fan:**
  - **mfab_hat:** the cap refuses it at 104.9 mm.
  - **mfab_lc, 96.7 mm:** the same A, but its arm ends in a blunt tip, two
    corners 0.7 mm apart.
    - The sharpest corner is then the base corner, and the out-of-shape guard
      refuses: no bad stitches, but no fan.
    - Its base would be 5.45 mm, over the cap anyway.
    - Merging a blunt tip into one corner is the follow-up.
  - **toat_beanie (1), distressed_grunge (6):** specks of 0.23-0.79 mm², under
    the fill floor.
- **The A counters of proseal_hat, proseal_beanie, precision_drone and
  lt_bukit_asam** are wedges, but open fabric (`stitched: False`). The fan never
  sews a counter the art leaves empty.
