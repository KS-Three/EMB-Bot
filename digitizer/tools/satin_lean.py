#!/usr/bin/env python
"""How far satin crosses lean, and where they sit against the house angle.

The instrument behind the stitch-angle rule's first pass (2026-09-03,
`docs/stitch-angle-convention-2026-09-03.md`): two histograms over every
satin cross of the housed lettering in a design, split penetrations and
ties stripped first so a wide column's split points do not read as crosses.

- **lean off own perpendicular** -- the angle between each cross and the
  perpendicular to the column's local advance (the direction between the
  cross midpoints one station either side). A stock column wanders ~19 deg
  here on a raster skeleton (Hotel Fremont, no house angle: p50 19.2, p90
  31.7, 1% past 45); the retired 45 deg bisector put every cross at 45
  (p50 45, half past 45); the rule holds p50 ~20 with 3% past 45 on
  Fremont. Corners still sweep -- a merged stem-to-bar chain turns its cross
  90 deg across the smoothing width -- and that is the Goldman join's job,
  not this pass's. With `--stock` every satin shape is read, house or not,
  which is the instrument's own floor.
- **cross vs house** -- the same crosses against the house angle: the stems
  hold it (0-10), the bars take their own perpendicular (80-90) under the
  rule, and the 30-60 band is diagonals leaning plus the corner sweeps.

Also prints the median THREAD pitch across the column (two threads per
station, so 0.200 mm at `SATIN_SPACING_MM` 0.4): 0.152 on every leaned
column before density compensation, 0.20 after.

    .venv/bin/python tools/satin_lean.py [case ...] [--stock]

Cases: fremont (four-fold on), enthusiast (93 mm, four-fold on), drone
(four-fold on), becker, gaulke, or a path under `testdata/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.stage6_satin import strip_splits  # noqa: E402
from digitizer_core.stitches import strip_ties  # noqa: E402

CASES = {
    "fremont": ("photo/logo_hotel_fremont.webp",
                dict(target_width_mm=80.0, max_colors=3, forced_class="flat",
                     border="off", satin_house_fourfold=True)),
    "enthusiast": ("photo/enthusiast_logo.png",
                   dict(target_width_mm=93.0, garment_id="left_chest",
                        satin_house_fourfold=True)),
    "drone": ("photo/drone_render.png",
              dict(target_width_mm=80.0, satin_house_fourfold=True)),
    "becker": ("becker_marine_logo.png", dict(target_width_mm=80.0)),
    "gaulke": ("photo/logo_gaulke_roofing.png", dict(target_width_mm=80.0)),
}
LEAN_BINS = [0.0, 5.0, 15.0, 30.0, 45.0, 90.1]
HOUSE_BINS = [0.0, 10.0, 30.0, 60.0, 80.0, 90.1]


def _fold(a: np.ndarray) -> np.ndarray:
    return np.abs((a + 90.0) % 180.0 - 90.0)


def crosses(plan, house: dict[str, float]):
    """-> (lean, vs_house, pitch) arrays over the satin runs of `house`'s shapes."""
    leans, rel, pitches = [], [], []
    for _block, run in plan.iter_runs():
        if run.kind != "satin" or run.shape_id not in house:
            continue
        pts = np.asarray(strip_splits(strip_ties(list(run.points))), dtype=float)
        if len(pts) < 6:
            continue
        vec = pts[1:] - pts[:-1]
        length = np.hypot(vec[:, 0], vec[:, 1])
        idx = np.nonzero(length > 0.6)[0]
        if len(idx) < 5:
            continue
        mids = (pts[idx] + pts[idx + 1]) / 2.0
        cross = np.degrees(np.arctan2(vec[idx, 1], vec[idx, 0]))
        advance = np.degrees(np.arctan2(mids[2:, 1] - mids[:-2, 1],
                                        mids[2:, 0] - mids[:-2, 0]))
        leans.extend(_fold(cross[1:-1] - (advance + 90.0)).tolist())
        rel.extend(_fold(cross[1:-1] - house[run.shape_id]).tolist())
        unit = vec[idx] / length[idx][:, None]
        normal = np.stack([-unit[:, 1], unit[:, 0]], axis=1)
        gaps = np.abs(np.einsum("ij,ij->i", mids[1:] - mids[:-1], normal[:-1]))
        pitches.extend(gaps[(gaps > 0.1) & (gaps < 1.0)].tolist())
    return np.asarray(leans), np.asarray(rel), np.asarray(pitches)


def main(argv: list[str]) -> None:
    stock = "--stock" in argv
    names = [a for a in argv if not a.startswith("--")] or list(CASES)
    for name in names:
        rel, kw = CASES.get(name, (name, dict(target_width_mm=80.0)))
        result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**kw))
        house = {r.shape_id: r.meta["satin_angle_deg"] for r in result.regions
                 if r.meta.get("satin_angle_deg") is not None}
        if stock:
            house = {r.shape_id: r.meta.get("satin_angle_deg", 0.0) for r in result.regions}
        lean, vs_house, pitch = crosses(plan, house)
        print(f"## {name}{' (stock)' if stock else ''} st={plan.stats.stitch_count} "
              f"trims={plan.stats.trims} housed={len(house)} crosses={len(lean)}")
        if len(lean) == 0:
            continue
        lh = np.histogram(lean, LEAN_BINS)[0] * 100.0 / len(lean)
        hh = np.histogram(vs_house, HOUSE_BINS)[0] * 100.0 / len(vs_house)
        print("  lean off own perpendicular  "
              + "  ".join(f"{LEAN_BINS[i]:>2.0f}-{LEAN_BINS[i + 1]:<4.0f}:{lh[i]:4.0f}%" for i in range(5))
              + f"  p50={np.median(lean):.1f} p90={np.percentile(lean, 90):.1f}")
        print("  cross vs house              "
              + "  ".join(f"{HOUSE_BINS[i]:>2.0f}-{HOUSE_BINS[i + 1]:<4.0f}:{hh[i]:4.0f}%" for i in range(5))
              + f"  thread pitch={np.median(pitch):.3f} mm")


if __name__ == "__main__":
    main(sys.argv[1:])
