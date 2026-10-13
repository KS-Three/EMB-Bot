"""Thread layers per patch of fabric — defect 20's instrument.

Reads preflight's coverage map (`preflight._coverage_map`: every needle-down
stitch rasterized as the ribbon of thread it lays, ties excluded, on
`machine.COVERAGE_CELL_MM` cells) and expresses it in FILL LAYERS — coverage
units divided by `machine.COVERAGE_FILL_LAYER_UNITS` — the ruler the 3.5-layer
pucker ceiling (`machine.COVERAGE_BLOCK_UNITS`) is written in.

"Per pixel" here is per coverage cell (1 mm at the shipped constant): the
stitch plan has no pixels, and the cell is the grid every density finding in
preflight already reads. Percentiles are over SEWN cells only (coverage at or
over `preflight._COVERAGE_FLOOR_UNITS`), so bare fabric around the design
cannot pull them down.
"""
from __future__ import annotations

import numpy as np

from . import machine
from .stitches import StitchPlan

PERCENTILES = (50, 90, 95, 99)
CEILING_LAYERS = machine.COVERAGE_BLOCK_UNITS / machine.COVERAGE_FILL_LAYER_UNITS
WARN_LAYERS = machine.COVERAGE_WARN_UNITS / machine.COVERAGE_FILL_LAYER_UNITS


def layer_stats(plan: StitchPlan) -> dict:
    """-> {max, p50, p90, p95, p99, sewn_mm2, over_warn_mm2, over_ceiling_mm2,
    ceiling}. Layers are fill layers; areas are mm2. A plan with no thread
    reports zeros."""
    from . import preflight   # preflight imports pipeline, which imports this
    cell2 = machine.COVERAGE_CELL_MM ** 2
    out = {"max": 0.0, **{f"p{q}": 0.0 for q in PERCENTILES},
           "sewn_mm2": 0.0, "over_warn_mm2": 0.0, "over_ceiling_mm2": 0.0,
           "ceiling": round(CEILING_LAYERS, 3)}
    got = preflight._coverage_map(plan)
    if got is None:
        return out
    grid, _origin = got
    sewn = grid[grid >= preflight._COVERAGE_FLOOR_UNITS]
    if not len(sewn):
        return out
    layers = sewn / machine.COVERAGE_FILL_LAYER_UNITS
    out["max"] = round(float(layers.max()), 3)
    for q, v in zip(PERCENTILES, np.percentile(layers, PERCENTILES)):
        out[f"p{q}"] = round(float(v), 3)
    out["sewn_mm2"] = round(len(sewn) * cell2, 1)
    out["over_warn_mm2"] = round(int((grid >= machine.COVERAGE_WARN_UNITS).sum()) * cell2, 1)
    out["over_ceiling_mm2"] = round(int((grid >= machine.COVERAGE_BLOCK_UNITS).sum()) * cell2, 1)
    return out


def cells_past_ceiling_mm(plan: StitchPlan) -> list[tuple[float, float]]:
    """Plan-mm centres of every coverage cell at or past the ceiling, in
    row-major order — the points `cfg.tonal_split_layer_cap` vetoes."""
    from . import preflight
    got = preflight._coverage_map(plan)
    if got is None:
        return []
    grid, (x0, y0) = got
    c = machine.COVERAGE_CELL_MM
    iy, ix = np.nonzero(grid >= machine.COVERAGE_BLOCK_UNITS)
    return [(round(x0 + (i + 0.5) * c, 3), round(y0 + (j + 0.5) * c, 3))
            for j, i in zip(iy.tolist(), ix.tolist())]
