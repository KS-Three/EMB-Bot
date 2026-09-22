#!/usr/bin/env python
"""Does cropping flip `alpha_edge_extend` by moving px_per_mm across the floor?

`alpha_edge_extend_upscaled_only` gates on `alpha_edge.upscale_expected`,
which compares the artwork's own px/mm at the target width against
`cfg.min_px_per_mm`. Cropping changes that ratio. So a crop can turn the
extension on or off without anyone deciding to -- which is a flag Kent
flipped ON on 2026-09-20 precisely BECAUSE it was gated to the under-floor
regime.

Two sweeps, same fixture and same crop ladder, two target widths:

  * UNDER-FLOOR (100 mm) -- the original sweep. Becker's own resolution
    already sits at 1.45 px/mm against a 4.0 floor at this width, so every
    crop in the ladder only pushes it further under. `gate` cannot move
    here; it is a documented negative on the under-floor regime, not a test
    of the coupling.
  * STRADDLING (25 mm) -- picked by discovery, not guessed: at 25 mm the
    UNCROPPED artwork reads 5.8 px/mm (gate False, comfortably above the
    4.0 floor), and the same crop ladder that does nothing at 100 mm pushes
    it below the floor by the (0.2, 0.2, 0.8, 0.8) inset. This is the arm
    that can actually show the coupling firing -- a `gate` change here,
    not in the first sweep, is the number the spec asked for.

Usage (cwd digitizer/):
  .venv/Scripts/python tools/crop_floor_coupling.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize          # noqa: E402
from digitizer_core.alpha_edge import upscale_expected       # noqa: E402
from digitizer_core.stage1_prep import _load, prep           # noqa: E402

# An alpha cutout under the floor at its census width: the population the
# gate was built for.
FIXTURE = "becker_marine_logo.png"
WIDTH_MM = 100.0

# Same fixture, a width discovered (not guessed) so the UNCROPPED artwork
# sits comfortably above `min_px_per_mm` (5.8 vs 4.0) -- the arm that gives
# the crop ladder a boundary to actually cross. Found by printing
# `Prep.input_px_per_mm` across a width ladder (10-100 mm): becker's
# uncropped gate flips between 35 mm (4.14, False) and 40 mm (3.62, True),
# so 25 mm leaves headroom on the False side for the crop ladder to close.
STRADDLE_WIDTH_MM = 25.0

# Shared crop ladder for both sweeps: no crop, an explicit full-frame crop
# (inertness control), then progressively tighter insets.
CROPS = (None, (0.0, 0.0, 1.0, 1.0), (0.1, 0.1, 0.9, 0.9),
         (0.2, 0.2, 0.8, 0.8), (0.3, 0.3, 0.7, 0.7))


def run_sweep(fixture: str, width_mm: float, label: str) -> bool:
    """Runs the crop ladder at one target width; returns whether `gate`
    changed across it."""
    art = ROOT / "testdata" / fixture
    print(f"{label}: {fixture} @ {width_mm} mm\n")
    print("{:>26}{:>10}{:>9}{:>9}{:>9}{:>8}".format(
        "crop", "px/mm", "gate", "regions", "stitches", "trims"))
    gates = []
    for crop in CROPS:
        cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest",
                             crop=crop)
        _rgb, alpha = _load(art, cfg.strip_letterbox, cfg.crop)
        gate = (upscale_expected(alpha, cfg.target_width_mm, cfg.min_px_per_mm)
                if alpha is not None else None)
        # `input_px_per_mm` is what the SOURCE delivered for this crop, before
        # the floor upscale -- which is the number the gate compares, so it is
        # the one to print. `px_per_mm` would show the post-upscale value and
        # make the gate look inconsistent with its own input.
        ppm = prep(art, cfg).input_px_per_mm
        result, plan = digitize(art, cfg)
        gates.append(gate)
        print("{:>26}{:>10.2f}{:>9}{:>9}{:>9}{:>8}".format(
            str(crop), ppm, str(gate), len(result.regions),
            plan.stats.stitch_count, plan.stats.trims))
    moved = len(set(gates)) > 1
    print(f"\n`gate` {'CHANGED' if moved else 'held constant'} across this sweep.")
    return moved


def main() -> int:
    under_floor_moved = run_sweep(FIXTURE, WIDTH_MM, "SWEEP A (under-floor)")
    print()
    straddle_moved = run_sweep(FIXTURE, STRADDLE_WIDTH_MM, "SWEEP B (straddling)")
    print("\nA `gate` column that CHANGES across crops is the coupling firing.")
    print(f"Sweep A moved: {under_floor_moved}. Sweep B moved: {straddle_moved}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
