# Does cropping flip `alpha_edge_extend`? Measured, not argued

Spec §8's recorded risk: `alpha_edge_extend_upscaled_only` gates on
`alpha_edge.upscale_expected` (`digitizer_core/alpha_edge.py:107`), which
compares the artwork's own px/mm at the target width against
`cfg.min_px_per_mm`. Cropping changes the pixel width the artwork occupies,
so in principle a crop could flip the gate as a side effect of framing —
the same coupling, from the other direction, that killed the
resolution-floor raise on 2026-09-20. This is measured with
`digitizer/tools/crop_floor_coupling.py` on `becker_marine_logo.png` at
100 mm, sweeping five crops from no crop down to keeping the middle 40% of
the frame.

## Output (exact)

```
becker_marine_logo.png @ 100.0 mm

                      crop     px/mm     gate  regions stitches   trims
                      None      1.45     True       17     8070      54
      (0.0, 0.0, 1.0, 1.0)      1.45     True       17     8070      54
      (0.1, 0.1, 0.9, 0.9)      1.16     True       15    12485      57
      (0.2, 0.2, 0.8, 0.8)      0.88     True        8    11684      28
      (0.3, 0.3, 0.7, 0.7)      0.58     True        2     5448       8

A `gate` column that CHANGES across crops is the coupling firing.
```

Reproduced twice, byte-identical both runs (44s for the five digitizes,
exit 0).

## Finding

The `gate` column did not move — it is `True` for all five crops, so
**no effect measured on this fixture**: the coupling does not fire here.

The reason is visible in the `px/mm` column, not just the `gate` column:
Becker's uncropped input already sits at 1.45 px/mm against a 4.0
`min_px_per_mm` floor (art_w_px ≈145 against a 400 px_w threshold at 100 mm),
and every crop in this sweep only *tightens* the frame around the artwork,
which strictly lowers px/mm further (1.45 → 1.16 → 0.88 → 0.58) — it pushes
the reading deeper under the floor, never across it to the other side. This
sweep can prove the coupling fires (a crop that drives px/mm below the
floor while starting above it, or a padding crop that drives it back above
while starting below), but on this fixture, with these five crop windows,
every reading starts and stays under the floor, so the gate has no boundary
to cross. The regions/stitches/trims swings in the table (e.g. 8,070 →
12,485 → 5,448 stitches) are the crop removing/rescaling artwork content
itself, not the gate switching — they are not evidence of the coupling.

This does not clear the coupling in general — a fixture or crop range that
straddles the 4.0 px/mm floor (rather than starting deep under it) could
still flip the gate. That is a follow-up measurement, not a conclusion this
run supports either way. No engine change was made in this task regardless
of outcome; per the task brief, a harmful coupling is Kent's decision, not
a fix to make here.
