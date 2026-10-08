#!/usr/bin/env python
"""`cfg.overlap_by_angle` (defect 47, Law 26): seam underlap and cost, OFF vs ON.

For each real-art fixture, one generation, then stages 5-7 twice. Seams are
read with `tools/seam_underlap.measure` (the earlier colour's sewn tongue
under the later one) and split by how parallel the two sides' rows run:

  * `par` — fill->fill seams whose rows are within 30 deg of each other
    (|cos| >= 0.866), the joins the law says open under pull;
  * `other` — every other seam (perpendicular-ish fills, or satin on a side),
    which the flag must leave at today's depth.

Reported per class: seam length, length-weighted mean depth, and length
under 0.5 mm (`<0.5`) — the seam the cloth can show once pull opens it.
Cost: stitches, trims and thread metres from the full plan.

    .venv/bin/python tools/overlap_by_angle.py            # all REAL_ART
    .venv/bin/python tools/overlap_by_angle.py becker fremont
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.machine import satin_ceiling_mm  # noqa: E402
from digitizer_core.pipeline import (build_generation, fabric_for,  # noqa: E402
                                     finish_generation, plan_stitches)
from digitizer_core.stage5_overlap import _comp_axis, resolve_overlaps  # noqa: E402
from tools.seam_underlap import measure  # noqa: E402
from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS  # noqa: E402

PARALLEL_COS = math.cos(math.radians(30.0))


def _split(pairs, angle):
    out = {"par": [], "other": []}
    for p in pairs:
        a, b = angle.get(p["earlier"]), angle.get(p["later"])
        par = (a is not None and b is not None
               and abs(math.cos(math.radians(a - b))) >= PARALLEL_COS)
        out["par" if par else "other"].append(p)
    return out


def _summ(pairs):
    L = sum(p["shared_mm"] for p in pairs)
    d = sum(p["shared_mm"] * p["depth_mm"] for p in pairs) / L if L else 0.0
    u = sum(p["shared_mm"] for p in pairs if p["depth_mm"] < 0.5)
    return L, d, u


def run(name: str) -> dict:
    rel, width_mm, garment = REAL_ART[name]
    base = dict(target_width_mm=width_mm, garment_id=garment, max_colors=STUDIO_MAX_COLORS)
    cfg0 = PipelineConfig(**base)
    gen = build_generation(str(ROOT / "testdata" / rel), cfg0)
    row = {}
    for tag, on in (("off", False), ("on", True)):
        cfg = PipelineConfig(**base, overlap_by_angle=on)
        result = finish_generation(gen.fork(), cfg)
        regions = [r for r in result.regions if r.meta.get("stitched", True)]
        planned, _ = resolve_overlaps(regions, fabric_for(cfg), cfg, result.design_class)
        sm = satin_ceiling_mm(cfg)
        angle = {}
        for r in regions:
            a, sat = _comp_axis(r, cfg, sm, result.design_class)
            angle[r.shape_id] = None if sat else a
        m = measure(regions, planned)
        parts = _split(m["pairs"], angle)
        st = plan_stitches(result, cfg).stats
        row[tag] = {"par": _summ(parts["par"]), "other": _summ(parts["other"]),
                    "st": st.stitch_count, "trims": st.trims, "m": st.thread_m_total}
    return row


def main(argv=None) -> int:
    names = (argv if argv is not None else sys.argv[1:]) or list(REAL_ART)
    print(f"{'fixture':11s} {'par mm':>7s} {'depth off->on':>14s} {'<0.5 off->on':>14s}"
          f" {'other depth off->on':>20s} {'stitches':>16s} {'trims':>9s} {'thread m':>13s}")
    for n in names:
        r = run(n)
        o, i = r["off"], r["on"]
        print(f"{n:11s} {o['par'][0]:7.1f} {o['par'][1]:6.3f}->{i['par'][1]:6.3f}"
              f" {o['par'][2]:6.1f}->{i['par'][2]:6.1f}"
              f" {o["other"][0]:6.1f}mm {o["other"][1]:6.3f}->{i['other'][1]:6.3f}"
              f" {o['st']:7d}->{i['st']:7d} {o['trims']:4d}->{i['trims']:3d}"
              f" {o['m']:6.1f}->{i['m']:5.1f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
