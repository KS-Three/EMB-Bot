# Does cropping flip `alpha_edge_extend`? Measured, not argued

Spec §8's recorded risk: `alpha_edge_extend_upscaled_only` gates on
`alpha_edge.upscale_expected` (`digitizer_core/alpha_edge.py:107`), which
compares the artwork's own px/mm at the target width against
`cfg.min_px_per_mm` (4.0). Cropping changes the pixel width the artwork
occupies, so in principle a crop could flip the gate as a side effect of
framing — the same coupling, from the other direction, that killed the
resolution-floor raise on 2026-09-20. Measured with
`digitizer/tools/crop_floor_coupling.py`, three arms, same fixture
(`becker_marine_logo.png`) and the same five-crop ladder (no crop, an
explicit full-frame crop, then progressively tighter insets down to the
middle 40% of the frame).

Round 1 (100 mm only) found the fixture's own resolution already deep
under the floor, so no crop in the ladder could reach the boundary — a
real result, but one that couldn't answer whether the coupling fires.
Round 2 added a straddling sweep (25 mm, discovered rather than guessed)
where the same crop ladder does cross the floor, and found the `gate`
column flips. Round 2 also flagged, honestly, that it couldn't tell how
much of the resulting stitch-count change was the gate versus the crop
itself, since both move together. This round (3) adds the counterfactual
that answers that: the same straddling sweep run again with
`alpha_edge_extend=False`, so the extension can never apply no matter what
the crop does — the difference between the shipped arm and this
forced-off arm, crop by crop, isolates what the gate itself costs.

## Output (exact)

```
SWEEP A (under-floor): becker_marine_logo.png @ 100.0 mm

                      crop     px/mm     gate  regions stitches   trims
                      None      1.45     True       17     8070      54
      (0.0, 0.0, 1.0, 1.0)      1.45     True       17     8070      54
      (0.1, 0.1, 0.9, 0.9)      1.16     True       15    12485      57
      (0.2, 0.2, 0.8, 0.8)      0.88     True        8    11684      28
      (0.3, 0.3, 0.7, 0.7)      0.58     True        2     5448       8

`gate` held constant across this sweep.

SWEEP B (straddling, shipped): becker_marine_logo.png @ 25.0 mm

                      crop     px/mm     gate  regions stitches   trims
                      None      5.80    False       15     1018       4
      (0.0, 0.0, 1.0, 1.0)      5.80    False       15     1018       4
      (0.1, 0.1, 0.9, 0.9)      4.64    False       15      994      12
      (0.2, 0.2, 0.8, 0.8)      3.52     True        9      851       9
      (0.3, 0.3, 0.7, 0.7)      2.32     True        2      335       2

`gate` CHANGED across this sweep.

SWEEP C (straddling, alpha_edge_extend=False): becker_marine_logo.png @ 25.0 mm

                      crop     px/mm     gate  regions stitches   trims
                      None      5.80    False       15     1018       4
      (0.0, 0.0, 1.0, 1.0)      5.80    False       15     1018       4
      (0.1, 0.1, 0.9, 0.9)      4.64    False       15      994      12
      (0.2, 0.2, 0.8, 0.8)      3.52     True        9      851       9
      (0.3, 0.3, 0.7, 0.7)      2.32     True        2      335       2

`gate` CHANGED across this sweep.

SWEEP B vs SWEEP C -- same crop, same width, only alpha_edge_extend differs:
                      crop     gate  B stitch  C stitch     d_st   B trim   C trim   d_trim
                      None    False      1018      1018        0        4        4        0
      (0.0, 0.0, 1.0, 1.0)    False      1018      1018        0        4        4        0
      (0.1, 0.1, 0.9, 0.9)    False       994       994        0       12       12        0
      (0.2, 0.2, 0.8, 0.8)     True       851       851        0        9        9        0
      (0.3, 0.3, 0.7, 0.7)     True       335       335        0        2        2        0

Sweep B/C agree on at least one row.

A `gate` column that CHANGES across crops is the coupling firing.
Sweep A moved: False. Sweep B moved: True. B/C diverged: False.
```

Exit 0. 70s wall for all three arms (15 digitizes) on this run. Sweep A's
and Sweep B's own tables are byte-identical to the earlier rounds.

## How the straddling width was picked

`Prep.input_px_per_mm` is fixed by the artwork's pixel bounding box, which
does not change with `target_width_mm`; only the ratio against the 4.0
floor does. Printing it across a width ladder (10–100 mm, uncropped) showed
becker's own gate flip between 35 mm (4.14 px/mm, `False`) and 40 mm (3.62,
`True`). 25 mm was chosen to sit inside the `False` side of that with
headroom (5.80 px/mm, 45% above the floor), leaving room for the same crop
ladder used in Sweep A to close the gap.

## Finding

**The gate flips (Sweep B), but on this fixture it costs nothing
measurable (Sweep C).** Sweep B vs Sweep C — identical fixture, identical
25 mm width, identical crop at every row, the *only* difference being
`alpha_edge_extend=True` (shipped) vs `alpha_edge_extend=False` (forced
off) — produced byte-for-byte identical `regions` / `stitches` / `trims`
on all five crops, including the two rows where Sweep B's gate is `True`
and the extension is actually live. Every row's `d_st` and `d_trim` in the
B-vs-C table is 0.

This is not a coincidence; it has a mechanical explanation, checked
directly against the pixel data rather than assumed: `becker_marine_logo.png`
decodes to exactly two RGB colours overall — a near-black `(35, 31, 32)`
under the opaque logo, and white `(255, 255, 255)` in the fully-transparent
background. `extend_opaque_colour` only has something to do where a
non-opaque pixel's colour differs from its nearest opaque neighbour's — and
by the `(0.1, 0.1, 0.9, 0.9)` inset, the crop has already cut the white
background entirely out of frame (confirmed directly: the cropped raster
at `(0.1,…)` and tighter is down to **one** unique colour). So by the time
the crop reaches the point where the resolution gate flips
(`(0.2, 0.2, 0.8, 0.8)`), there is no colour heterogeneity left for the
extension to correct — `extension_applies()` returns `True` there, but
`extend_opaque_colour` changes **0 of 4,840 pixels**. The gate firing and
the extension having work to do are two different conditions, and on this
fixture and this crop ladder the second one is already false by the time
the first one goes true.

Sweep A (100 mm, unchanged since round 1) still shows `gate` held
constant — Becker's own resolution there is already far under the floor,
so that arm remains a documented negative on the under-floor regime, not a
test of the coupling.

**Conclusion, stated plainly: on this one fixture, cropping does flip
`alpha_edge_extend_upscaled_only`, but the flip is a curiosity here, not a
measured hazard — it costs zero regions, zero stitches, zero trims,
because this crop ladder removes the only colour the extension would have
touched before the gate ever changes.** That is a property of this
specific artwork (a flat two-colour alpha cutout whose background sits
entirely outside the tighter crops), not a general proof that the coupling
is harmless on every upload — a fixture with colour variation still present
at the crop that crosses the floor could show a real, nonzero cost; this
measurement doesn't rule that out. No engine code was changed based on
this measurement, and none is proposed: whether the coupling is worth
guarding against in general remains a call for Kent, not settled by one
fixture reading zero cost.
