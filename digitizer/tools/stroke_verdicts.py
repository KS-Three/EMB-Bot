#!/usr/bin/env python
"""Per-stroke satin verdicts for a design's regions, beside the shipped one.

The report half of PR 2 of
`docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`. Nothing in
the pipeline consults `stage6_satin.classify_strokes`; this is how its numbers
are read off real fixtures so the routing decision can be made on measurement
rather than on the pooling argument alone.

What it answers: `classify_ribbon` pools the distance transform over a whole
region's skeleton, so a branchy letterform — wide at its junctions, thin along
its arms — can fail `2 sigma < mu` as a unit while every arm of it is a clean
ribbon. This prints, per region the shipped classifier REFUSED, what its
strokes say individually and how much of the region's area they carry.

  .venv/bin/python tools/stroke_verdicts.py becker_marine_logo.png --width 100
  .venv/bin/python tools/stroke_verdicts.py logo_alpha.png --all

`--all` includes regions the shipped call already takes, which is how the
REVERSE case is read: a region sewing satin today whose strokes do not all
pass would be a demotion, and the plan flags that as a golden move to measure
before deciding (`logo_alpha.png`'s Sf5200f3f).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig                      # noqa: E402
from digitizer_core.machine import SATIN_MAX_WIDTH_MM          # noqa: E402
from digitizer_core.pipeline import run_stages                 # noqa: E402
from digitizer_core.stage6_satin import (                      # noqa: E402
    _STROKE_AREA_FRAC_MIN,
    classify_strokes,
)


def report(art: Path, width_mm: float, garment: str, show_all: bool) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result = run_stages(str(art), cfg)
    satin_max = cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM

    print(f"{art.name} @ {width_mm:g}mm/{garment}   satin_max {satin_max:g} mm"
          f"   {len(result.regions)} regions")
    print(f"{'region':12} {'shipped':16} {'area':>8}  strokes "
          f"(reason, area mm2, cv, p90 mm, explained)")

    earned_before = flips = flip_area = 0.0, 0, 0.0
    earned_before = 0.0
    flips = 0
    flip_area = 0.0
    demote = []
    for r in result.regions:
        v = classify_strokes(r.polygon, satin_max)
        if v.region.satin:
            earned_before += float(r.polygon.area)
        if not show_all and v.region.satin:
            continue
        would = (v.passing_frac >= _STROKE_AREA_FRAC_MIN)
        if would and not v.region.satin:
            flips += 1
            flip_area += float(r.polygon.area)
        if v.region.satin and not would:
            demote.append((r.shape_id, float(r.polygon.area), v.passing_frac))
        mark = "  <= FLIPS" if (would and not v.region.satin) else ""
        print(f"{r.shape_id:12} {v.region.reason:16} "
              f"{float(r.polygon.area):8.1f}  frac {v.passing_frac:.2f}{mark}")
        for s in v.strokes:
            cv = (s.stats.std / s.stats.mean) if s.stats and s.stats.mean else 0.0
            p90 = s.stats.p90_mm if s.stats else 0.0
            exp = s.stats.explained if s.stats else 0.0
            print(f"{'':12} {'':16} {s.area_mm2:8.1f}   {s.index:>2} "
                  f"{s.reason:14} cv {cv:5.3f}  p90 {p90:5.2f}  exp {exp:5.3f}")

    total = float(sum(r.polygon.area for r in result.regions))
    print(f"\nsatin area now      {earned_before:8.1f} mm2 "
          f"({100.0 * earned_before / total:4.1f}% of {total:.0f})")
    print(f"would flip          {flips} regions, {flip_area:8.1f} mm2 "
          f"at frac >= {_STROKE_AREA_FRAC_MIN}")
    print(f"satin area after    {earned_before + flip_area:8.1f} mm2 "
          f"({100.0 * (earned_before + flip_area) / total:4.1f}%)")
    if demote:
        print(f"\nREVERSE CASE — satin today, would not pass per stroke:")
        for sid, area, frac in demote:
            print(f"  {sid:12} {area:8.1f} mm2   frac {frac:.2f}")
    return {"before": earned_before, "flip_area": flip_area, "total": total}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fixture", help="path under testdata/, or a full path")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--all", action="store_true",
                    help="include regions the shipped call already takes")
    a = ap.parse_args()
    art = Path(a.fixture)
    if not art.exists():
        art = ROOT / "testdata" / a.fixture
    if not art.exists():
        print(f"no such fixture: {a.fixture}", file=sys.stderr)
        return 2
    report(art, a.width, a.garment, a.all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
