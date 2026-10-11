#!/usr/bin/env python
"""Defect 20: the stacked-layer histogram, tonal split ON vs the cure.

Prints, per fixture, how much fabric carries how many FILL LAYERS of thread
(preflight's own coverage map, divided by `machine.COVERAGE_FILL_LAYER_UNITS`)
with the split forced on, once with `cfg.tonal_split_ceiling` off and once on.
The last bin is the pucker ceiling, `machine.COVERAGE_BLOCK_UNITS`.

    python -m tools.tonal_stack_hist                     # the real owl
    python -m tools.tonal_stack_hist photo/owl_kent.jpg drone_render.png

Real artwork only (gate 2). Both committed real tonal fixtures classify
`gradient`, where the split is off by default, so it is FORCED here; the
photo classes' own fixtures are synthetic stubs. `is_photographic=True` is
the declaration a real photograph upload carries; undeclared, the owl splits
into 172 regions and stacks LESS split than whole (1 cell against 14).
"""
import argparse
import pathlib

import numpy as np

from digitizer_core import PipelineConfig, machine, preflight
from digitizer_core.pipeline import area_past_ceiling_mm2, digitize

TD = pathlib.Path("testdata")
CEIL = machine.COVERAGE_BLOCK_UNITS / machine.COVERAGE_FILL_LAYER_UNITS
BINS = [0.0, 1.0, 2.0, 2.5, 3.0, CEIL, np.inf]


def histogram(plan) -> tuple[list[int], float]:
    """-> (cells per layer bin, peak layers). Cells are 1 mm2."""
    got = preflight._coverage_map(plan)
    if got is None:
        return [0] * (len(BINS) - 1), 0.0
    grid, _o = got
    layers = grid[grid >= preflight._COVERAGE_FLOOR_UNITS] / machine.COVERAGE_FILL_LAYER_UNITS
    return [int(n) for n in np.histogram(layers, bins=BINS)[0]], float(grid.max()) / machine.COVERAGE_FILL_LAYER_UNITS


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fixtures", nargs="*", default=["photo/owl_kent.jpg"])
    ap.add_argument("--width-mm", type=float, default=80.0)
    a = ap.parse_args(argv)
    labels = [f"{lo:g}-{hi:g}" for lo, hi in zip(BINS[:-2], BINS[1:-1])] + [f">={CEIL:g}"]
    print(f"{'fixture':<22} {'arm':<12} {'regions':>7} {'peak':>5}  " + " ".join(f"{s:>7}" for s in labels))
    for fx in a.fixtures:
        for arm, cure in (("split", False), ("split+cure", True)):
            cfg = PipelineConfig(target_width_mm=a.width_mm, garment_id="left_chest",
                                 split_tonal_regions=True, tonal_split_ceiling=cure,
                                 is_photographic=True)
            res, plan = digitize(TD / fx, cfg)
            h, peak = histogram(plan)
            assert h[-1] == round(area_past_ceiling_mm2(plan))
            print(f"{pathlib.Path(fx).name:<22} {arm:<12} {len(res.regions):>7} {peak:>5.2f}  "
                  + " ".join(f"{n:>7}" for n in h))


if __name__ == "__main__":
    main()
