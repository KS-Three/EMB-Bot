# Does cropping flip `alpha_edge_extend`? Measured, not argued

Spec §8's recorded risk: `alpha_edge_extend_upscaled_only` gates on
`alpha_edge.upscale_expected` (`digitizer_core/alpha_edge.py:107`), which
compares the artwork's own px/mm at the target width against
`cfg.min_px_per_mm` (4.0). Cropping changes the pixel width the artwork
occupies, so in principle a crop could flip the gate as a side effect of
framing — the same coupling, from the other direction, that killed the
resolution-floor raise on 2026-09-20. Measured with
`digitizer/tools/crop_floor_coupling.py`, two sweeps, same fixture
(`becker_marine_logo.png`) and the same five-crop ladder (no crop, an
explicit full-frame crop, then progressively tighter insets down to the
middle 40% of the frame), at two target widths.

The first round of this measurement (100 mm only) found the fixture's own
resolution already deep under the floor, so no crop in the ladder could
reach the boundary — a real result, but one that cannot answer whether the
coupling fires, only that it didn't on that one arm. This round adds a
second sweep at a width discovered (not guessed) to put the uncropped
artwork above the floor, so the same crop ladder has a boundary to cross.

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

SWEEP B (straddling): becker_marine_logo.png @ 25.0 mm

                      crop     px/mm     gate  regions stitches   trims
                      None      5.80    False       15     1018       4
      (0.0, 0.0, 1.0, 1.0)      5.80    False       15     1018       4
      (0.1, 0.1, 0.9, 0.9)      4.64    False       15      994      12
      (0.2, 0.2, 0.8, 0.8)      3.52     True        9      851       9
      (0.3, 0.3, 0.7, 0.7)      2.32     True        2      335       2

`gate` CHANGED across this sweep.

A `gate` column that CHANGES across crops is the coupling firing.
Sweep A moved: False. Sweep B moved: True.
```

Exit 0, ran twice (once before this round, once for this round),
byte-identical output for Sweep A across both. 58s wall for both sweeps
(10 digitizes) on this run.

## How the straddling width was picked

`Prep.input_px_per_mm` is fixed by the artwork's pixel bounding box, which
does not change with `target_width_mm`; only the ratio against the 4.0
floor does. Printing it across a width ladder (10–100 mm, uncropped) showed
becker's own gate flip between 35 mm (4.14 px/mm, `False`) and 40 mm (3.62,
`True`). 25 mm was chosen to sit inside the `False` side of that with
headroom (5.80 px/mm, 45% above the floor), leaving room for the same crop
ladder used in Sweep A to close the gap.

## Finding

**The coupling fires.** In Sweep B, `gate` is `False` for the uncropped and
full-frame-crop rows and the `(0.1, 0.1, 0.9, 0.9)` inset, then flips to
`True` at `(0.2, 0.2, 0.8, 0.8)` and stays `True` at the tightest inset.
Nothing about the artwork changed except the crop rectangle; the flip is
the crop alone moving `input_px_per_mm` (4.64 → 3.52) across the 4.0 floor.

Sweep A (100 mm, unchanged from the first round) still shows `gate` held
constant — Becker's own resolution there is already far under the floor, so
that arm remains a documented negative on the under-floor regime, not a
test of the coupling. Both sweeps are kept because they answer different
questions: A says the coupling does not create surprises for artwork that
was already going to upscale regardless of crop; B says the coupling is
real for artwork that starts above the floor and gets cropped into it.

**What it cost, at the flip step in Sweep B** (the `(0.1,…)` → `(0.2,…)`
transition, where `gate` changes from `False` to `True`):

| | regions | stitches | trims |
|---|---|---|---|
| `(0.1, 0.1, 0.9, 0.9)` — gate `False` | 15 | 994 | 12 |
| `(0.2, 0.2, 0.8, 0.8)` — gate `True` | 9 | 851 | 9 |
| change | −6 | −143 (−14.4%) | −3 |

For scale, the same crop step (`(0.1,…)` → `(0.2,…)`) in Sweep A — where
`gate` does NOT change — also drops region and stitch counts by a
comparable order (15 → 8 regions, 12,485 → 11,684 stitches, −6.4%). Both
sweeps lose regions and stitches at that step because the crop itself is
removing artwork content at every width; that happens whether or not the
gate moves. This measurement does not isolate how much of Sweep B's −143
stitches is the gate flipping the alpha extension on versus the crop
narrowing the artwork, and no such isolation was attempted — reporting it
either way, without a controlled counterfactual, would be more than this
run supports.

The size of the move (single-digit percent-to-low-double-digit-percent
swings in stitches/regions/trims at the crop step where the gate flips) is
not obviously catastrophic on this one fixture, but it is a real,
measured, silent change in output driven purely by framing — no flag
touched, no resolution changed, just where the crop rectangle sits. Per the
task brief, this is a decision for Kent, not a fix to make in this task:
the honest options remain pinning the gate to the pre-crop px/mm, or
accepting that cropping can silently move it. No engine code was changed
based on this measurement.
