#!/usr/bin/env python
"""Per-stroke satin verdicts for a design's regions, beside the shipped one.

The report half of PR 2 of
`docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`. The pipeline
does not call `stage6_satin.classify_strokes` itself, but since PR 3 it DOES
consult the same reading: `classify_ribbon`'s `dt_irregular` branch calls
`_stroke_rung_takes`, which shares `_stroke_rows` with this report, whenever
`cfg.satin_per_stroke` is on (default OFF, flipping it is Kent's). So this is
no longer a pre-decision instrument only — it is how the flag's effect is read
off a fixture without sewing it, and it calls `classify_ribbon` BOTH ways to
say so rather than restating the rung's rule.

What it answers: `classify_ribbon` pools the distance transform over a whole
region's skeleton, so a branchy letterform — wide at its junctions, thin along
its arms — can fail `2 sigma < mu` as a unit while every arm of it is a clean
ribbon. This prints, per region the shipped classifier REFUSED, what its
strokes say individually and how much of the region's area they carry.

  .venv/bin/python tools/stroke_verdicts.py becker_marine_logo.png --width 100
  .venv/bin/python tools/stroke_verdicts.py logo_alpha.png --all

Two denominators, deliberately. A classifier verdict on a region the PLAN
never sews is not satin on cloth: on `becker_marine_logo` @ 100 mm, 198.8 of
the "274.0 mm2 of satin" sits in enclosed-background regions that never become
thread. Quote the SEWN column.

Three rules, for the same reason. `satin now` is the flag OFF, `satin ON` is
the flag on, and the `bare >= 0.75` line is the PLAN'S ARITHMETIC, which is
not what ships: the cap veto and Law 31's floor sit between them, and on
Becker @ 100 mm that is 5 regions against 3.

`--all` includes regions the shipped call already takes, which is how the
REVERSE case is read: a region sewing satin today whose strokes do not all
pass would be a demotion under a REPLACEMENT rung — which the flag is not,
being promotion-only — and the plan flags that as a golden move to measure
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
from digitizer_core.pipeline import plan_stitches, run_stages   # noqa: E402
from digitizer_core.stage6_satin import (                      # noqa: E402
    _STROKE_AREA_FRAC_MIN,
    classify_ribbon,
    classify_strokes,
)


def report(art: Path, width_mm: float, garment: str, show_all: bool) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result = run_stages(str(art), cfg)
    satin_max = cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    dc = result.design_class

    # Which regions become THREAD. A classifier verdict on a region the plan
    # never sews is not satin on cloth, and reporting it as area is how a
    # headline gets inflated: on `becker_marine_logo` @ 100 mm, 198.8 of the
    # "274.0 mm2 of satin" sits in two enclosed-background regions
    # (`S805585ef` 191.4, `S501501b6` 7.4) that BACKGROUND_ENCLOSED leaves
    # open by design, so 27% of that figure is thread. Measured 2026-09-06.
    plan = plan_stitches(result, cfg)
    sewn_ids = {r.shape_id for _b, r in plan.iter_runs() if r.shape_id}

    # The design's own class, not the default: on a photo class Law 31's
    # width floor refuses a stroke under PHOTO_MIN_SATIN_WIDTH_MM, and a
    # report that omitted it would show hairline strokes earning satin.
    print(f"{art.name} @ {width_mm:g}mm/{garment}   satin_max {satin_max:g} mm"
          f"   class {dc}   {len(result.regions)} regions")
    print(f"{'region':12} {'shipped':16} {'area':>8}  strokes "
          f"(reason, area mm2, cv, p90 mm, explained)")

    now_mm2 = now_sewn = 0.0
    flag_n, flag_mm2, flag_sewn = 0, 0.0, 0.0
    bare_n, bare_mm2, bare_sewn = 0, 0.0, 0.0
    demote = []
    for r in result.regions:
        area = float(r.polygon.area)
        sewn = area if r.shape_id in sewn_ids else 0.0
        v = classify_strokes(r.polygon, satin_max, design_class=dc)
        # What the FLAG does, read off the shipped function rather than off a
        # restatement of its rule: `classify_ribbon` twice, once each way.
        # `v.passing_frac >= _STROKE_AREA_FRAC_MIN` below is the PLAN's
        # arithmetic and not what ships — the cap veto and Law 31's floor sit
        # between the two, and on Becker @ 100 mm that is 5 regions vs 3.
        on = classify_ribbon(r.polygon, satin_max, design_class=dc,
                             per_stroke=True)
        bare = (v.passing_frac >= _STROKE_AREA_FRAC_MIN)
        if v.region.satin:
            now_mm2 += area
            now_sewn += sewn
        if not show_all and v.region.satin:
            continue
        if on.satin and not v.region.satin:
            flag_n += 1
            flag_mm2 += area
            flag_sewn += sewn
            mark = "  <= FLIPS"
        elif bare and not v.region.satin:
            mark = f"  <= bare rule only, flag refuses ({on.reason})"
        else:
            mark = ""
        if bare and not v.region.satin:
            bare_n += 1
            bare_mm2 += area
            bare_sewn += sewn
        if v.region.satin and not bare:
            demote.append((r.shape_id, area, v.passing_frac))
        print(f"{r.shape_id:12} {v.region.reason:16} "
              f"{area:8.1f}  frac {v.passing_frac:.2f}{mark}")
        for s in v.strokes:
            cv = (s.stats.std / s.stats.mean) if s.stats and s.stats.mean else 0.0
            p90 = s.stats.p90_mm if s.stats else 0.0
            exp = s.stats.explained if s.stats else 0.0
            print(f"{'':12} {'':16} {s.area_mm2:8.1f}   {s.index:>2} "
                  f"{s.reason:14} cv {cv:5.3f}  p90 {p90:5.2f}  exp {exp:5.3f}")

    total = float(sum(float(r.polygon.area) for r in result.regions))
    sewn_total = float(sum(float(r.polygon.area) for r in result.regions
                           if r.shape_id in sewn_ids))

    def pct(part: float, whole: float) -> str:
        return f"{100.0 * part / whole:4.1f}%" if whole > 0 else " n/a "

    # Both denominators, because they answer different questions and the
    # classifier's flatters: "of all region area" counts shapes the plan
    # leaves open, which never become thread. Quote the SEWN column.
    print(f"\nregion area  all {total:8.1f} mm2 "
          f"| SEWS {sewn_total:8.1f} mm2 ({pct(sewn_total, total)} of all)")
    print(f"satin now    {now_mm2:8.1f} mm2 ({pct(now_mm2, total)} of all) "
          f"| SEWN {now_sewn:8.1f} mm2 ({pct(now_sewn, sewn_total)} of sewn)")
    print(f"flag adds    {flag_n} regions, {flag_mm2:8.1f} mm2 "
          f"| SEWN {flag_sewn:8.1f} mm2   [cfg.satin_per_stroke]")
    print(f"satin ON     {now_mm2 + flag_mm2:8.1f} mm2 "
          f"({pct(now_mm2 + flag_mm2, total)} of all) "
          f"| SEWN {now_sewn + flag_sewn:8.1f} mm2 "
          f"({pct(now_sewn + flag_sewn, sewn_total)} of sewn)")
    print(f"bare frac >= {_STROKE_AREA_FRAC_MIN} — the PLAN's rule, NOT shipped: "
          f"{bare_n} regions, {bare_mm2:8.1f} mm2 "
          f"| SEWN {bare_sewn:8.1f} mm2")
    if demote:
        # Only a REPLACEMENT rung could do this; the flag is promotion-only.
        print(f"\nREVERSE CASE — satin today, would not pass per stroke:")
        for sid, area, frac in demote:
            print(f"  {sid:12} {area:8.1f} mm2   frac {frac:.2f}")
    return {"before": now_mm2, "before_sewn": now_sewn,
            "flag_area": flag_mm2, "flag_sewn": flag_sewn,
            "bare_area": bare_mm2, "bare_sewn": bare_sewn,
            "total": total, "sewn_total": sewn_total}


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
