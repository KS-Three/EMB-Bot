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

from digitizer_core import PipelineConfig, digitize          # noqa: E402
from digitizer_core.alpha_edge import upscale_expected       # noqa: E402
from digitizer_core.stage1_prep import _load, prep           # noqa: E402

# An alpha cutout under the floor at its census width: the population the
# gate was built for.
FIXTURE = "becker_marine_logo.png"
WIDTH_MM = 100.0


def main() -> int:
    art = ROOT / "testdata" / FIXTURE
    print(f"{FIXTURE} @ {WIDTH_MM} mm\n")
    print("{:>26}{:>10}{:>9}{:>9}{:>9}{:>8}".format(
        "crop", "px/mm", "gate", "regions", "stitches", "trims"))
    for crop in (None, (0.0, 0.0, 1.0, 1.0), (0.1, 0.1, 0.9, 0.9),
                 (0.2, 0.2, 0.8, 0.8), (0.3, 0.3, 0.7, 0.7)):
        cfg = PipelineConfig(target_width_mm=WIDTH_MM, garment_id="left_chest",
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
            plan.stats.stitch_count, plan.stats.trims))
    print("\nA `gate` column that CHANGES across crops is the coupling firing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
