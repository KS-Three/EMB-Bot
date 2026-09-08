#!/usr/bin/env python
"""Per-shape SEWN tier for a fixture, read off the emitted plan.

`tools/stroke_verdicts.py` reports what the classifier SAYS about each
region. This reports what the plan actually EMITS for it — which run kinds
carry its thread, and how many segments — so a verdict can be checked
against the stitches, which is this repo's rule for proving anything about
satin (DOCTRINE: prove a seam on the stitches, never on the plan).

Built 2026-09-08 for `docs/quality-review-2026-09-08.md` §2b, where it
showed that `becker_marine_logo.png` @ 100 mm sews every MARINE letter as
tatami with `cfg.satin_per_stroke` ON as well as OFF: the flag promotes three
shapes of 22–34 mm², and the letters are refused by the width cap.

  .venv/bin/python tools/sewn_tiers.py becker_marine_logo.png --width 100
  .venv/bin/python tools/sewn_tiers.py logo_alpha.png --flag off
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig                      # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages   # noqa: E402


def report(art: Path, width_mm: float, garment: str, per_stroke: bool) -> list[dict]:
    """-> one row per region: shape id, area, enclosed flag, segments by kind."""
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         satin_per_stroke=per_stroke)
    result = run_stages(str(art), cfg)
    plan = plan_stitches(result, cfg)
    kinds: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _block, run in plan.iter_runs():
        if run.shape_id is None:
            continue
        kinds[run.shape_id][str(run.kind)] += max(0, len(run.points) - 1)
    rows = []
    for r in sorted(result.regions, key=lambda r: -r.polygon.area):
        rows.append({
            "shape_id": r.shape_id,
            "area_mm2": r.polygon.area,
            "enclosed": bool(r.meta.get("enclosed_background")),
            "kinds": dict(kinds.get(r.shape_id, {})),
        })
    st = plan.stats
    return rows, {"stitches": st.stitch_count, "trims": st.trims, "jumps": st.jumps}


def _print(rows, totals, per_stroke: bool, width_mm: float) -> None:
    print(f"\n== satin_per_stroke={per_stroke}  width={width_mm:g} mm  "
          f"stitches={totals['stitches']} trims={totals['trims']} jumps={totals['jumps']}")
    print(f"{'shape':12} {'mm2':>8}  kinds (segments)")
    for row in rows:
        k = row["kinds"]
        ks = ", ".join(f"{kk}={vv}" for kk, vv in sorted(k.items(), key=lambda kv: -kv[1]))
        tag = "  ENCLOSED" if row["enclosed"] else ""
        print(f"{row['shape_id']:12} {row['area_mm2']:8.1f}  {ks or '(unsewn)'}{tag}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture", help="path under testdata/, or a full path")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--flag", choices=("both", "off", "on"), default="both",
                    help="which `satin_per_stroke` settings to run")
    a = ap.parse_args(argv)
    art = Path(a.fixture)
    if not art.exists():
        art = ROOT / "testdata" / a.fixture
    for per_stroke in ((False, True) if a.flag == "both" else ((a.flag == "on"),)):
        rows, totals = report(art, a.width, a.garment, per_stroke)
        _print(rows, totals, per_stroke, a.width)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
