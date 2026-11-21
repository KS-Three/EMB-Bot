Moved: 9 of 44 runs; pictured: 4.

# `satin_junction_block`: flip-readiness evidence, 2026-11-21

**What it does** (`cfg.extra["satin_junction_block"]`, built OFF 2026-11-20, #1738,
`digitizer_core/column_junction.py`). Where two satin runs of one shape lay
side-by-side bars over the same block (MFab's F: arm and stem each about 1.9 mm,
offset across the stitch), the later run is widened across the union and sewn
as one wide column, and the earlier bar under it becomes a running path. This
is how the pro's file sews it. Swept at its shipped ON value `true`. The
`"short"` variant (#1738's doc: it fixes 1 of 5 MFab top-line faults at a pile
cost) was not swept tonight.

**The sweep.** `python -m tools.flag_sweep --flag extra.satin_junction_block --pictures`
on `main` at `2d4e132e`. All 44 runs finished (18 tripwire placements, 26 corpus
fixtures), with 0 errors. 9 moved. In every mover, trims, jumps, needle-up mm
and colours are identical OFF and ON. Only the stitch count moves, and by at
most 59.

- `mfab_hat`: stitches 20,516 -> 20,457 (-59); trims 23, jumps 68, needle-up 580.1 mm unchanged
- `mfab_lc`: stitches 17,564 -> 17,559 (-5); trims 17, jumps 60, needle-up 505.4 mm unchanged
- `becker_lc_large`: stitches 14,423 -> 14,419 (-4); trims 11, jumps 27, needle-up 196.9 mm unchanged
- `gaulke_roofing_beanie`: stitches 7,093 -> 7,091 (-2); trims 22, jumps 59, needle-up 276.9 mm unchanged
- `photo_scene_stub` (corpus): stitches 23,655 -> 23,653 (-2); trims 70, jumps 179, needle-up 1595.0 mm unchanged
- `becker_hat_large`, `becker_hat_small`, `becker_chest_small`, `hotel_fremont_hat`: counts identical (15,958 / 9,847 / 9,713 / 15,169); the md5 moved, the render does not

**By-eye read against the original art.** I diffed the BEFORE and AFTER
renders pixel for pixel. At the 0.6 mm blur the labelled-page change locator
uses, 7 of the 9 show **no changed pixel at all**. The other two show under
70 px of a 2 Mpx render: `mfab_hat` at x 81.8 mm, y 22.3 mm, and `mfab_lc`
at x 40.3 mm, y 10.6 mm. At a 1 px blur, 5 of the 9 change somewhere. The
`zoom_*` files are those spots at stitch level, BEFORE left and AFTER right.

- **`mfab_hat`: same at print size; slightly worse at zoom** (`zoom_mfab_hat_z0.png`).
  Where a vertical column meets the base, the AFTER column steps out to the
  right for a few stitches: a small nick in an otherwise straight edge the
  art does not have. `zoom_mfab_hat_z1.png` is the F's diagonal arm: the
  stitch lengths rearrange, but neither side is closer to the art.
- `mfab_lc`: same (the same diagonal junction, stitches re-spread, `zoom_mfab_lc_z0.png`).
- `becker_lc_large`: same (a few black satin stitches shift at a bowl join, `zoom_becker_lc_large_z0.png`).
- `gaulke_roofing_beanie`: same (one stitch-width shift at a junction).
- `photo_scene_stub`, the three other Becker placements, `hotel_fremont_hat`: same, with no visible pixel change.

**Verdict: no visible change at print size.** The F4 "one wide block" this flag
was built to make does not appear in the `mfab_hat` / `mfab_lc` renders with
the value `true`. That matches #1738's own measurement: `true` fixes 0 of the
5 top-line faults. The one change I can call worse is the small nick in
`mfab_hat`, and it shows only at zoom.

Files: the full ORIGINAL | BEFORE | AFTER strips for the four movers that
change at all at stitch level (`mfab_hat.png`, `mfab_lc.png`,
`becker_lc_large.png`, `gaulke_roofing_beanie.png`); the `zoom_*.png` crops at
3x; `sweep.md`. The originals are art already in the repo (`Embroidery Files.zip`).
No pro stitch file is rendered.
