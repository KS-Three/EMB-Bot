#!/usr/bin/env python
"""Does cropping flip `alpha_edge_extend` by moving px_per_mm across the floor?

`alpha_edge_extend_upscaled_only` gates on `alpha_edge.upscale_expected`,
which compares the artwork's own px/mm at the target width against
`cfg.min_px_per_mm`. Cropping changes that ratio. So a crop can turn the
extension on or off without anyone deciding to -- which is a flag Kent
flipped ON on 2026-09-20 precisely BECAUSE it was gated to the under-floor
regime.

This sweeps an alpha cutout across the boundary and reports both the gate's
verdict and what it costs, so the interaction is a measured number rather
than an argument.

Usage (cwd digitizer/):
  .venv/Scripts/python tools/crop_floor_coupling.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np                                            # noqa: E402
from digitizer_core import PipelineConfig, digitize          # noqa: E402
from digitizer_core.alpha_edge import upscale_expected       # noqa: E402
from digitizer_core.stage1_prep import _load, prep           # noqa: E402

# An alpha cutout under the floor at its census width: the population the
# gate was built for.
FIXTURE = "becker_marine_logo.png"
WIDTH_MM = 100.0


def sweep(art, width_mm, crops) -> None:
    print("{:>26}{:>10}{:>9}{:>9}{:>9}{:>8}".format(
        "crop", "px/mm", "gate", "regions", "stitches", "trims")
          + "{:>10}{:>8}".format("st_noext", "tr_noext"))
    for crop in crops:
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
        print("{:>26}{:>10.2f}{:>9}{:>9}{:>9}{:>8}".format(
            str(crop), ppm, str(gate), len(result.regions),
            plan.stats.stitch_count, plan.stats.trims), end="")
        # Same crop with the extension forced OFF: the difference is what the
        # gate's verdict costs, separated from what the crop itself changes.
        _r0, plan0 = digitize(art, PipelineConfig(
            target_width_mm=width_mm, garment_id="left_chest", crop=crop,
            alpha_edge_extend=False))
        print("{:>10}{:>8}".format(plan0.stats.stitch_count, plan0.stats.trims))


def synthetic_above_floor() -> np.ndarray:
    """BGRA cutout that CLEARS the floor uncropped: an opaque band spanning a
    400 px frame (400 px over 80 mm = 5.0 px/mm, floor 4.0) with an inner
    block so there is more than one region."""
    art = np.zeros((400, 400, 4), np.uint8)
    art[150:250, :, :3] = 20
    art[150:250, :, 3] = 255
    art[170:230, 100:300, :3] = (30, 30, 200)       # BGR: a red block
    return art


def main() -> int:
    print(f"{FIXTURE} @ {WIDTH_MM} mm (already under the floor)\n")
    sweep(ROOT / "testdata" / FIXTURE, WIDTH_MM,
          (None, (0.0, 0.0, 1.0, 1.0), (0.1, 0.1, 0.9, 0.9),
           (0.2, 0.2, 0.8, 0.8), (0.3, 0.3, 0.7, 0.7)))
    print("\nsynthetic RGBA cutout, above the floor uncropped, @ 80.0 mm\n")
    sweep(synthetic_above_floor(), 80.0,
          (None, (0.0, 0.0, 1.0, 1.0), (0.05, 0.05, 0.95, 0.95),
           (0.1, 0.1, 0.9, 0.9), (0.2, 0.2, 0.8, 0.8), (0.3, 0.3, 0.7, 0.7)))
    print("\nA `gate` column that CHANGES across crops is the coupling firing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
