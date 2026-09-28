# Does cropping flip `alpha_edge_extend` through the resolution floor?

Measured 2026-09-22 with `digitizer/tools/crop_floor_coupling.py` (spec section 8).
`alpha_edge_extend_upscaled_only` gates on `alpha_edge.upscale_expected`, which
compares the artwork's px/mm at the target width against `cfg.min_px_per_mm`
(4.0). A crop changes that px/mm, so in principle it can move the gate.

```
becker_marine_logo.png @ 100.0 mm

                      crop     px/mm     gate  regions stitches   trims
                      None      1.45     True       17     8070      54
      (0.0, 0.0, 1.0, 1.0)      1.45     True       17     8070      54
      (0.1, 0.1, 0.9, 0.9)      1.16     True       15    12485      57
      (0.2, 0.2, 0.8, 0.8)      0.88     True        8    11684      28
      (0.3, 0.3, 0.7, 0.7)      0.58     True        2     5448       8
```

## Finding

The `gate` column did not move: it is `True` for every crop, so the coupling
does not fire on this fixture and there is no flip to cost. That is a weak
result, though, and should be read as such: this fixture already sits at
1.45 px/mm, far under the 4.0 floor, and a crop can only ever LOWER px/mm here
(see below), so it could never have crossed the floor in the direction that
turns the extension on. The coupling is untested for an artwork that clears the
floor before the crop and falls under it after.

Two things the run does show:

- `crop=(0,0,1,1)` is identical to `crop=None` on every column, including
  stitches and trims.
- px/mm is measured on the ARTWORK's bounding box (`stage1_prep`,
  `art_w_px / target_width_mm`), not on the frame. Cropping away empty margin
  therefore moves nothing, and only a crop that cuts into the artwork lowers
  px/mm. The Task 4 test fixture had to be built around this (the plan's
  "400 px frame over 80 mm = 5.0" was really 1.25 on a 100 px square).

The size of the changes in regions/stitches/trims across the rows is the crop
removing artwork (17 regions down to 2), not the gate.

No engine change was made. Whether the untested direction matters (a
high-resolution source cropped down past the floor) is a decision for Kent, not
something to fix inside this plan; the honest options are pinning the gate to
the pre-crop px/mm or accepting the flip, and would be a separate brainstorm.
