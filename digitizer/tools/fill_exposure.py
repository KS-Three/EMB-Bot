#!/usr/bin/env python
"""Exposed fill travel: how much travel a design lays on top of fill already sewn.

The instrument behind `PipelineConfig.fill_travel_under_cover` (2026-09-03).
Kent's Hotel Fremont note -- "the in-fill stitching doesn't look clean" -- was
fill-phase travel runs laid over columns already sewn: on that field, 22 of
27 runs and 286 of 450 mm. A number quoted without a re-runnable instrument
is not evidence (see the density lesson in
`.claude/memory/first-physical-sewout-2026-09-01.md`), so this is the
re-runnable one.

For every fill-tier shape, walk its runs in sew order; accumulate the
footprint of each FILL path (a full-row buffer of a half-row-simplified copy,
the same footprint stage 6 uses) and, for each fill-phase TRAVEL run, measure
how much of it lies over that footprint beyond one travel stitch
(`stage6_fill._EXPOSED_TOLERANCE_MM`, the bridge's unavoidable start inside
the column it just finished).

    .venv/bin/python tools/fill_exposure.py [fixture ...] [--off]

Fixtures are paths under `testdata/` or the short names below. `--off`
digitizes with the flag off, for the before/after pair.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from shapely.geometry import LineString  # noqa: E402

from digitizer_core import PipelineConfig, digitize, machine  # noqa: E402
from digitizer_core.stage6_fill import _EXPOSED_TOLERANCE_MM  # noqa: E402

SHORT = {
    "fremont": ("photo/logo_hotel_fremont.webp",
                dict(max_colors=3, forced_class="flat", border="off")),
    "becker": ("becker_marine_logo.png", {}),
    "enthusiast": ("photo/enthusiast_logo.png", {}),
    "drone": ("photo/drone_render.png", {}),
    "whitebg": ("logo_whitebg.png", {}),
    "gaulke": ("photo/logo_gaulke_roofing.png", {}),
    "meadow": ("photo/photo_dof_meadow.png", {}),
    "sunset": ("photo/photo_sunset_backlit.png", {}),
}


def exposure(plan) -> dict:
    """-> fill_mm, travel_runs, travel_mm, exposed_runs, exposed_mm over a plan."""
    row = machine.FILL_ROW_MM
    sewn: dict = {}
    out = dict(fill_mm=0.0, travel_runs=0, travel_mm=0.0, exposed_runs=0, exposed_mm=0.0)
    for _block, run in plan.iter_runs():
        sid = run.shape_id
        if run.kind == "fill":
            out["fill_mm"] += run.length_mm
            if len(run.points) > 1:
                fp = LineString(run.points).simplify(row / 2.0).buffer(row)
                sewn[sid] = fp if sid not in sewn else sewn[sid].union(fp)
        elif run.kind == "travel" and sid in sewn and len(run.points) > 1:
            out["travel_runs"] += 1
            out["travel_mm"] += run.length_mm
            over = LineString(run.points).intersection(sewn[sid]).length
            if over > _EXPOSED_TOLERANCE_MM:
                out["exposed_runs"] += 1
                out["exposed_mm"] += over
    return out


def main(argv: list[str]) -> None:
    off = "--off" in argv
    names = [a for a in argv if not a.startswith("--")] or list(SHORT)
    for name in names:
        rel, kw = SHORT.get(name, (name, {}))
        t0 = time.time()
        _result, plan = digitize(ROOT / "testdata" / rel,
                                 PipelineConfig(target_width_mm=80.0,
                                                fill_travel_under_cover=not off, **kw))
        e = exposure(plan)
        pct = 100.0 * e["exposed_mm"] / max(e["travel_mm"], 1e-9)
        print(f"{name:12s} {'off' if off else 'on ':3s} t={time.time() - t0:5.1f}s "
              f"st={plan.stats.stitch_count:6d} trims={plan.stats.trims:3d} "
              f"fill={e['fill_mm']:7.0f}mm travel={e['travel_runs']:3d}/{e['travel_mm']:6.1f}mm "
              f"EXPOSED={e['exposed_runs']:3d}/{e['exposed_mm']:6.1f}mm ({pct:.0f}%)")


if __name__ == "__main__":
    main(sys.argv[1:])
