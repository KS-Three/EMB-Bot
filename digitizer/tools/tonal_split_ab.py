#!/usr/bin/env python
"""What does photo tonal-region splitting BUY? Measured against its own absence.

MASTER_SCOPE 20 records what the tier COSTS (`photo_scene_stub` coverage_max
4.40 -> 6.44, same_hole_fraction up 4-7x) and, until this tool, said the other
half could not be measured: *"No off switch for photo classes
(`effective_split_tonal` ORs flag with class)"*. **That has been false since
2026-09-01 (PR #316)** -- an explicit `split_tonal_regions=False` wins in both
directions, and `effective_split_tonal`'s own docstring names defect 20 as the
reason the switch was built. The claim outlived its fix by a day.

Runs every photo-class fixture in the scorecard corpus twice, default (tier ON
for photo classes) against `split_tonal_regions=False`, and prints cost and
quality together, because the whole question is the trade.

    python -m tools.tonal_split_ab          # from digitizer/, ~20 min

READ THE PER-FIXTURE TABLE, NOT ONLY THE SUMMARY. The summary's first version
compared grades as STRINGS ("100" < "76") and reported two fixtures moving the
wrong way; the table was right throughout. It uses int() now.

AND READ THE RESULT HONESTLY: the scorecard has no instrument for what this
tier is FOR. It measures density, coverage, trims and thread-to-artwork dE00 --
nothing scores tonal gradation, so "scores better with the tier off" is not
"looks better with the tier off". That gap is phase 1's exit condition, not a
verdict on the tier, and the tier is Kent's ratified spec decision 2.
"""
import pathlib

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.preflight import run_preflight
from tools.corpus_scorecard import FIXTURES

TD = pathlib.Path("testdata")
PHOTO = ("photo_subject", "photo_scene")


def one(fixture: str, split):
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                         split_tonal_regions=split)
    result, plan = digitize(TD / fixture, cfg)
    report = run_preflight(result, plan, cfg, image=TD / fixture)
    m = report["metrics"]
    return {
        "cls": result.design_class,
        "regions": len(result.regions),
        "cones": len({r.thread_index for r in result.regions}),
        "st": sum(len(r.points) for _b, r in plan.iter_runs()),
        "blocks": sum(1 for f in report["findings"]
                      if f.get("severity") == "block"),
        "grade": f"{report['grade']} {report['score']}",
        "cov": m.get("coverage_max"),
        "hole": m.get("same_hole_fraction"),
        "de": m.get("thread_worst_delta_e"),
    }


def fmt(v):
    return "-" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))


rows = []
for fixture in FIXTURES:
    on = one(fixture, None)
    if on["cls"] not in PHOTO:
        continue
    off = one(fixture, False)
    rows.append((fixture, on, off))
    name = pathlib.Path(fixture).name
    print(f"\n{name}   ({on['cls']})")
    print(f"    grade        {on['grade']:>9}  ->  {off['grade']:<9}"
          f"   blocks {on['blocks']} -> {off['blocks']}")
    print(f"    coverage_max {fmt(on['cov']):>9}  ->  {fmt(off['cov']):<9}"
          f"   same_hole {fmt(on['hole'])} -> {fmt(off['hole'])}")
    print(f"    worst dE00   {fmt(on['de']):>9}  ->  {fmt(off['de']):<9}"
          f"   regions {on['regions']} -> {off['regions']}"
          f"   cones {on['cones']} -> {off['cones']}")
    print(f"    stitches     {on['st']:>9}  ->  {off['st']:<9}"
          f"   ({off['st'] - on['st']:+d}, {100.0 * (off['st'] - on['st']) / max(1, on['st']):+.1f}%)")

print(f"\n{len(rows)} photo-class fixtures")
if rows:
    ds = sum(r[2]["st"] - r[1]["st"] for r in rows)
    tot = sum(r[1]["st"] for r in rows)
    print(f"tier OFF is {ds:+d} stitches over the photo lane "
          f"({100.0 * ds / max(1, tot):+.1f}%)")
    # int(), not a string compare: "100" < "76" lexically, which reversed
    # this summary on its first run while the per-fixture table above was
    # right. The table is the measurement; this is a convenience.
    score = lambda g: int(g.split()[1])
    better = [pathlib.Path(r[0]).name for r in rows
              if score(r[2]["grade"]) > score(r[1]["grade"])]
    worse = [pathlib.Path(r[0]).name for r in rows
             if score(r[2]["grade"]) < score(r[1]["grade"])]
    print(f"score higher with the tier OFF: {better or 'none'}")
    print(f"score lower  with the tier OFF: {worse or 'none'}")
