# Does cropping flip `alpha_edge_extend` through the resolution floor?

Measured 2026-09-22 with `digitizer/tools/crop_floor_coupling.py` (spec section 8).
`alpha_edge_extend_upscaled_only` gates stage 1 on `alpha_edge.upscale_expected`,
which compares the artwork's px/mm at the target width against
`cfg.min_px_per_mm` (4.0). A crop changes that px/mm, so it can move the gate.

The last three columns (`rg_noext`, `st_noext`, `tr_noext`: regions, stitches,
trims) rerun the same crop with `alpha_edge_extend=False`, so the difference
between the paired columns is what the extension does at that crop. The
`rg_noext` column was added and the table re-run 2026-09-28; every other
column reproduced the 2026-09-22 run exactly.

```
becker_marine_logo.png @ 100.0 mm (already under the floor)

                      crop     px/mm     gate  regions stitches   trims   rg_noext   st_noext  tr_noext
                      None      1.45     True       17     8070      54         18       7958        59
      (0.0, 0.0, 1.0, 1.0)      1.45     True       17     8070      54         18       7958        59
      (0.1, 0.1, 0.9, 0.9)      1.16     True       15    12485      57         15      12485        57
      (0.2, 0.2, 0.8, 0.8)      0.88     True        8    11684      28          8      11684        28
      (0.3, 0.3, 0.7, 0.7)      0.58     True        2     5448       8          2       5448         8

becker_marine_logo.png @ 25.0 mm (above the floor uncropped: real art straddling it)

                      crop     px/mm     gate  regions stitches   trims   rg_noext   st_noext  tr_noext
                      None      5.80    False       15     1018       4         15       1018         4
      (0.0, 0.0, 1.0, 1.0)      5.80    False       15     1018       4         15       1018         4
      (0.1, 0.1, 0.9, 0.9)      4.64    False       15      994      12         15        994        12
      (0.2, 0.2, 0.8, 0.8)      3.52     True        9      851       9          9        851         9
      (0.3, 0.3, 0.7, 0.7)      2.32     True        2      335       2          2        335         2

synthetic RGBA cutout, above the floor uncropped, @ 80.0 mm

                      crop     px/mm     gate  regions stitches   trims   rg_noext   st_noext  tr_noext
                      None      5.00    False        2     5447       3          2       5248         4
      (0.0, 0.0, 1.0, 1.0)      5.00    False        2     5447       3          2       5248         4
  (0.05, 0.05, 0.95, 0.95)      4.50    False        2     5952       4          2       5756         4
      (0.1, 0.1, 0.9, 0.9)      4.00    False        2     6594       3          2       6360         4
      (0.2, 0.2, 0.8, 0.8)      3.00     True        2     8543       6          2       9752         5
      (0.3, 0.3, 0.7, 0.7)      2.00     True        5    11855       6          3      11049         4
```

## Finding

**Becker (already under the floor):** the gate is `True` for every crop, so no
flip. Not informative about the coupling, only about the never-above-floor case.

**Becker at 25 mm (real art that clears the floor uncropped): the gate flips
and costs nothing.** Added 2026-09-28, from the parallel build
(`claude/upload-crop-build` 40fabc9c/f0348214), which found this width and
reported the same five rows; this run reproduced them exactly. Becker's own
gate flips between 35 and 40 mm uncropped, so 25 mm sits 45% above the floor.
The gate goes False to True between crop 0.1 (4.64 px/mm) and 0.2
(3.52 px/mm), and the ON and OFF arms are identical on every row. That
build traced why: becker decodes to two colours, near-black ink under the
opaque logo and white under the transparency, and by the 0.1 inset the crop
has already cut the white out of frame. When the gate goes True,
`extend_opaque_colour` has nothing left to change (0 of 4,840 pixels). This
is a property of this artwork. The synthetic cutout below keeps colour
variety past the flip and does show a cost.

**Synthetic cutout (clears the floor uncropped): the gate DID flip**, False to
True between 4.00 px/mm (crop 0.1) and 3.00 px/mm (crop 0.2). Crops of 0 to 10%
per side leave it False; 20% and beyond turn it True. So a crop that cuts into
the artwork can switch the extension on as a side effect of framing.

**What the flip cost:** small and mixed in sign, and not separable from
everything else in one number.
- At the flip (0.1 to 0.2): stitches with the extension go 6594 to 8543, but the
  extension-off run goes 6360 to 9752, so the flip itself shows as ON being 12%
  FEWER stitches than OFF at 0.2 (8543 vs 9752), with +1 trim (6 vs 5). At 0.3
  the sign reverses: ON is 7% MORE stitches (11855 vs 11049), +2 trims (6 vs 4).
- Regions are 2 in both arms up to 0.2; at 0.3 the ON arm has 5 and the OFF
  arm 3 (re-run 2026-09-28 with `rg_noext` printed).
- The bulk of every row's change across crops is the crop itself (the artwork is
  enlarged to the same target width), not the gate.
- Caveat on the paired columns: stage 0 reads the whole image regardless of the
  gate (`alpha_edge_extend_stage0_whole`), so ON and OFF differ even where stage
  1's gate is False (rows 5.00 to 4.00, about 4% stitches). The gate-True rows
  therefore mix a stage-1 flip with a stage-0 effect that was already there.

None of it is large against the crop's own effect, and no direction is
consistently worse. Whether to pin the gate to the pre-crop px/mm or accept the
flip is Kent's decision; this measurement does not make it look urgent.

**Scope of the gate:** it exists only for images with an alpha channel
(`extension_applies` returns False when `alpha is None`, and the fully-opaque
case is dropped). Opaque uploads, such as a phone screenshot, never reach it, so
this coupling cannot affect them.

Also shown by the run: `crop=(0,0,1,1)` is identical to `crop=None` on every
column, and px/mm is measured on the artwork's bounding box, so cropping away
empty margin moves nothing; only a crop that cuts into artwork lowers px/mm.

No engine change was made.
