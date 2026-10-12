"""Column lane rail inset (`columns.RAIL_REACH_INSET_MM`): shipped vs the lane
before (inset 0) vs the lane after, at several widths.

usage (cwd = digitizer/):
    python ../docs/renders/columns-rail-inset-2026-10-11/measure_inset.py OUTDIR fixture[,..] [50,80,100]

Per (fixture, width, arm) writes OUTDIR/<fx>@<w>-<arm>.design.json and one
JSON line to OUTDIR/<fx>.jsonl with three lost_frac readings -- grid (as
`tests/test_lettering_coverage_regression.py` reads it), one-pixel, and
MATCHED (#828's `matched.py`: the lane designs read at the shipped design's
physical alignment) -- plus the median signed distance of letter satin
penetrations from the artwork edge (mm, negative outside; #828's
`railedge_dir.py`).
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "columns-lost-frac-2026-10-11"))

import numpy as np  # noqa: E402
from shapely.geometry import Point  # noqa: E402

import tools.artfidelity_self as afs  # noqa: E402
_GRID = (afs.SHIFT_STEP_MM, afs.SHIFT_MM)
import matched as M  # noqa: E402  (sets afs to the fine grid on import)
from tools.dropped_elements import analyse_design  # noqa: E402
from tools.eye_pairs.features import base_cfg, digitize_once  # noqa: E402
from tools.thin_strokes import REAL_ART, ROOT  # noqa: E402
import digitizer_core.columns as C  # noqa: E402
from digitizer_core.columns import is_lettering  # noqa: E402

AFTER = C.RAIL_REACH_INSET_MM
LANE = {"lettering_columns": True, "lettering_words": True}
ARMS = {"shipped": ({}, AFTER), "lane0": (LANE, 0.0), "lane": (LANE, AFTER)}


def penetration(design, polys):
    st = design["stitches"]
    vals = []
    for r in design["runs"]:
        P = polys.get(r.get("shape"))
        if P is None or r["kind"] != "satin":
            continue
        B = P.boundary
        for i in range(r["i0"], r["i1"] + 1):
            s = st[i]
            if s.get("type") != "stitch":
                continue
            p = Point(s["x"] / 10, -s["y"] / 10)
            d = B.distance(p)
            if 1e-6 <= d <= 0.8:
                vals.append(d if P.covers(p) else -d)
    return round(float(np.median(vals)), 3) if vals else None


def reading(res):
    return {k: res[k] for k in ("lost_frac", "unsewn_frac", "wrong_colour_frac", "overshoot_frac",
                                "overshoot_mm2", "unsewn_mm2", "wrong_colour_mm2",
                                "uncovered_ink_frac", "shift_x_mm", "shift_y_mm")}


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    widths = [float(w) for w in (sys.argv[3] if len(sys.argv) > 3 else "50,80,100").split(",")]
    for fx in sys.argv[2].split(","):
        rel, _w, garment = REAL_ART[fx]
        image = ROOT / "testdata" / rel
        for width in widths:
            designs, polys, K = {}, {}, None
            for arm, (flags, inset) in ARMS.items():
                C.RAIL_REACH_INSET_MM = inset
                t = time.time()
                _gen, result, _plan, design = digitize_once(image, base_cfg(width, garment, **flags))
                C.RAIL_REACH_INSET_MM = AFTER
                if flags:
                    cfg = base_cfg(width, garment, **flags)
                    polys = {r.shape_id: r.polygon for r in result.regions if is_lettering(r, cfg)}
                designs[arm] = (design, round(time.time() - t, 1))
                (out / f"{fx}@{width:g}-{arm}.design.json").write_text(json.dumps(design))
            letters = list(polys)
            for arm, (design, t_dig) in designs.items():
                afs.SHIFT_STEP_MM, afs.SHIFT_MM = _GRID
                grid = reading(analyse_design(image, design))
                afs.SHIFT_STEP_MM, afs.SHIFT_MM = 0.1, 1.2
                fine = reading(analyse_design(image, design))
                m, _per, _v = M.analyse(image, design, width, K, letters)
                if arm == "shipped":
                    K = m["K"]
                m.pop("K", None)
                row = {"fixture": fx, "width": width, "arm": arm, "grid": grid, "fine": fine,
                       "matched": m, "penetration_median_mm": penetration(design, polys),
                       "stitches": sum(1 for s in design["stitches"] if s.get("type") == "stitch"),
                       "trims": sum(1 for s in design["stitches"] if s.get("type") == "trim"),
                       "t_digitize_s": t_dig}
                with open(out / f"{fx}.jsonl", "a") as f:
                    f.write(json.dumps(row) + "\n")
                print(fx, width, arm, grid["lost_frac"], fine["lost_frac"], m["lost_frac"],
                      row["penetration_median_mm"], flush=True)


if __name__ == "__main__":
    main()
