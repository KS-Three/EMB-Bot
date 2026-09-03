#!/usr/bin/env python
"""Fill stitches halved by float dust at the stitch-length threshold.

Found 2026-09-03 while measuring `PipelineConfig.curve_turn_deg` (defect 22):
Hotel Fremont's fill field lost 13% of its stitches when its boundary gained
vertices, at the same area and the same row angle, and the reason was not
the curve flag. `stage6_fill.emit` runs every fill path through
`stitches.split_long_moves(path, stitch_mm)`, which splits any step LONGER
than `stitch_mm`; the interior row grid is laid at exactly `stitch_mm` in the
row frame, and after the rotation back to design space a step measures
3.0000000000000004 as often as 2.9999999999999996. The former is split into
two 1.5 mm stitches. Which rows get it depends on the row angle's cosine, so
any change to a shape's polygon re-rolls the dice -- that is the +-10%
stitch-count noise on fill-heavy fixtures, and every one of those half
stitches is a needle penetration the design did not want.

Counts, per fixture: the fill/travel steps that pass through the splitter,
how many exceed the threshold by less than a micron (`dust`), how many by
more (`real`, the long bridges the splitter exists for), and what the dust
costs as a share of the design's stitches.

    .venv/bin/python tools/fill_dust.py [fixture ...]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core import stage6_fill, stitches  # noqa: E402

SHORT = {
    "whitebg": ("logo_whitebg.png", {}),
    "alpha": ("logo_alpha.png", {}),
    "becker": ("becker_marine_logo.png", {}),
    "fremont": ("photo/logo_hotel_fremont.webp",
                dict(max_colors=3, forced_class="flat", border="off")),
    "drone": ("photo/drone_render.png", {}),
    "enthusiast": ("photo/enthusiast_logo.png",
                   dict(target_width_mm=93.0, garment_id="left_chest")),
    "sunset": ("photo/photo_sunset_backlit.png", {}),
}
DUST_MM = 1e-6


def census(rel: str, kw: dict) -> dict:
    """-> steps, dust, real, stitch_count for one fixture, by spying on the splitter."""
    stats = {"steps": 0, "dust": 0, "real": 0}
    original = stitches.split_long_moves

    def spy(points, max_mm=stitches.machine.MAX_STITCH_MM):
        for a, b in zip(points, points[1:]):
            d = math.dist(a, b)
            stats["steps"] += 1
            if d > max_mm:
                stats["dust" if d - max_mm < DUST_MM else "real"] += 1
        return original(points, max_mm)

    stitches.split_long_moves = spy
    stage6_fill.stitches.split_long_moves = spy
    try:
        kw2 = dict(target_width_mm=80.0)
        kw2.update(kw)
        _result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**kw2))
    finally:
        stitches.split_long_moves = original
        stage6_fill.stitches.split_long_moves = original
    stats["stitch_count"] = plan.stats.stitch_count
    return stats


def main(argv: list[str]) -> None:
    names = argv or list(SHORT)
    for name in names:
        rel, kw = SHORT.get(name, (name, {}))
        s = census(rel, kw)
        share = 100.0 * s["dust"] / max(s["stitch_count"], 1)
        print(f"{name:12s} st={s['stitch_count']:6d} steps={s['steps']:6d} "
              f"dust={s['dust']:5d} ({100.0 * s['dust'] / max(s['steps'], 1):4.1f}% of steps, "
              f"{share:4.1f}% of the design) real={s['real']:4d}")


if __name__ == "__main__":
    main(sys.argv[1:])
