"""Where do rails sit BEFORE the pull push? Signed distance (mm, + inside) of
each pre-push rail point to its artwork polygon, for letter shapes, shipped
satin tier (`_rail_points`) vs the Column lane (`column_runs`).

usage (cwd = digitizer/): python prepush.py fixture[,fixture] [arm ...]
"""
import os
import sys
import inspect

sys.path.insert(0, os.getcwd())
import numpy as np  # noqa: E402
from shapely.geometry import Point  # noqa: E402

import digitizer_core.stage6_satin as S  # noqa: E402
from digitizer_core.columns import is_lettering  # noqa: E402
from tools.eye_pairs.features import base_cfg, digitize_once  # noqa: E402
from tools.thin_strokes import REAL_ART, ROOT  # noqa: E402

REC = []
_orig = S._push_rails


def spy(a, b, poly, pull, floor):
    caller = inspect.stack()[1].function
    REC.append((caller, list(a), list(b), poly))
    return _orig(a, b, poly, pull, floor)


S._push_rails = spy
ARMS = {"off": {}, "on": {"lettering_columns": True, "lettering_words": True}}

for fx in sys.argv[1].split(","):
    rel, width, garment = REAL_ART[fx]
    for arm in sys.argv[2:] or ["off", "on"]:
        REC.clear()
        cfg = base_cfg(width, garment, **ARMS[arm])
        gen, result, plan, design = digitize_once(ROOT / "testdata" / rel, cfg)
        letters = [r.polygon for r in result.regions if is_lettering(r, cfg)]
        vals = {}
        for caller, a, b, poly in REC:
            rp = poly.representative_point()
            if not any(L.buffer(0.05).covers(rp) for L in letters):
                continue
            B = poly.boundary
            for p in a + b:
                P = Point(p)
                d = B.distance(P)
                vals.setdefault(caller, []).append(d if poly.covers(P) else -d)
        for caller, v in vals.items():
            v = np.array(v)
            v1 = v[np.abs(v) < 0.8]
            q = np.percentile(v1, [5, 25, 50, 75, 95])
            print(f"{fx:10s} {arm:3s} {caller:14s} n={len(v1):5d} mean {v1.mean():+.3f} "
                  f"p5/25/50/75/95 = " + " ".join(f"{x:+.3f}" for x in q), flush=True)
