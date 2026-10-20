#!/usr/bin/env python
"""`cfg.forbid_gap_mm` (defect 47, Law 26): narrow gaps between colours, OFF vs ON.

For each real-art fixture, one generation, then stages 5-7 twice — OFF
(None) and ON at the documented candidate, 0.8 mm (a reading, not a ruling:
the value is ROADMAP gate 1's, card block 6). Per run:

  * `open` — strips of bare fabric under the threshold between two
    stitched colours that no one colour covers on the cloth
    (`tools/seam_underlap.narrow_gaps`, sewn polygons less the fabric's
    pull, `cloth_take_back`), as a count and in mm²;
  * `bridged` — the pairs the rule closed (`stage5_overlap.gap_bridges`)
    and the fabric area it gave the earlier colour;
  * cost — stitches, trims and thread metres from the full plan.

With `--pairs`, every OFF gap and what ON did to it: `closed` (the pair
reads no open strip ON) or `still open` with its ON reading.

    .venv/bin/python tools/forbid_gap.py                  # fremont, drone
    .venv/bin/python tools/forbid_gap.py becker bridge --pairs
    .venv/bin/python tools/forbid_gap.py --all            # every REAL_ART fixture
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import (build_generation, fabric_for,  # noqa: E402
                                     finish_generation, plan_stitches)
from digitizer_core.stage5_overlap import gap_bridges, resolve_overlaps  # noqa: E402
from tools.seam_underlap import GAP_MM, cloth_take_back, narrow_gaps  # noqa: E402
from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS  # noqa: E402

DEFAULT = ("fremont", "drone")


def run(name: str, gap_mm: float = GAP_MM) -> dict:
    rel, width_mm, garment = REAL_ART[name]
    base = dict(target_width_mm=width_mm, garment_id=garment, max_colors=STUDIO_MAX_COLORS)
    gen = build_generation(str(ROOT / "testdata" / rel), PipelineConfig(**base))
    row = {}
    for tag, value in (("off", None), ("on", gap_mm)):
        cfg = PipelineConfig(**base, forbid_gap_mm=value)
        result = finish_generation(gen.fork(), cfg)
        regions = [r for r in result.regions if r.meta.get("stitched", True)]
        fabric = fabric_for(cfg)
        planned, _ = resolve_overlaps(regions, fabric, cfg, result.design_class)
        gaps = narrow_gaps(regions, planned, gap_mm,
                           take_back=cloth_take_back(planned, cfg, fabric))
        bridged = gap_bridges(regions, gap_mm)[1] if value else []
        st = plan_stitches(result, cfg).stats
        row[tag] = {"gaps": gaps, "bridged": bridged, "pull": fabric.pull_comp_mm,
                    "st": st.stitch_count, "trims": st.trims, "m": st.thread_m_total}
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("names", nargs="*", help=f"REAL_ART keys (default: {' '.join(DEFAULT)})")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--gap", type=float, default=GAP_MM)
    ap.add_argument("--pairs", action="store_true")
    args = ap.parse_args(argv)
    names = list(REAL_ART) if args.all else (args.names or list(DEFAULT))
    print(f"{'fixture':11s} {'pull':>4s} {'open off->on':>13s} {'open mm2 off->on':>17s}"
          f" {'bridged':>7s} {'mm2':>6s} {'stitches':>16s} {'trims':>9s} {'thread m':>13s}")
    for n in names:
        r = run(n, args.gap)
        o, i = r["off"], r["on"]
        a_off = sum(g["open_mm2"] for g in o["gaps"])
        a_on = sum(g["open_mm2"] for g in i["gaps"])
        print(f"{n:11s} {o['pull']:4.2f} {len(o['gaps']):5d}->{len(i['gaps']):<5d}"
              f" {a_off:8.2f}->{a_on:<7.2f} {len(i['bridged']):7d}"
              f" {sum(b['area_mm2'] for b in i['bridged']):6.2f}"
              f" {o['st']:7d}->{i['st']:7d} {o['trims']:4d}->{i['trims']:3d}"
              f" {o['m']:6.1f}->{i['m']:5.1f}", flush=True)
        if args.pairs:
            still = {(g["earlier"], g["later"]): g for g in i["gaps"]}
            for g in o["gaps"]:
                k = (g["earlier"], g["later"])
                fate = (f"still open ({still[k]['open_mm2']} mm2)" if k in still else "closed")
                print(f"    {g['earlier']} | {g['later']}: gap {g['gap_mm']} mm,"
                      f" strip {g['gap_mm2']} mm2, open {g['open_mm2']} mm2 -> {fate}")
            for g in i["gaps"]:
                if (g["earlier"], g["later"]) not in {(x["earlier"], x["later"]) for x in o["gaps"]}:
                    print(f"    NEW ON: {g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
