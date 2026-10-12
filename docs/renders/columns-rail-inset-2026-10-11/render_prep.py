"""Write the files #828's `letterpic.py` reads, for shipped (`off`), the lane
before this change (`lane0`, inset 0) and after (`lane`), at the fixture's
REAL_ART width: DIR/<fx>-<arm>.design.json, DIR/<fx>-on.json (letter
outlines), DIR/matched-off-on.json (the shipped design's alignment K).

usage (cwd = digitizer/): python ../docs/renders/columns-rail-inset-2026-10-11/render_prep.py DIR fixture[,..]
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "columns-lost-frac-2026-10-11"))

import matched as M  # noqa: E402
from tools.eye_pairs.features import base_cfg, digitize_once  # noqa: E402
from tools.thin_strokes import REAL_ART, ROOT  # noqa: E402
import digitizer_core.columns as C  # noqa: E402
from digitizer_core.columns import is_lettering  # noqa: E402

AFTER = C.RAIL_REACH_INSET_MM
LANE = {"lettering_columns": True, "lettering_words": True}
ARMS = {"off": ({}, AFTER), "lane0": (LANE, 0.0), "lane": (LANE, AFTER)}

d = Path(sys.argv[1])
d.mkdir(parents=True, exist_ok=True)
mfile = d / "matched-off-on.json"
mres = json.loads(mfile.read_text()) if mfile.exists() else {}
for fx in sys.argv[2].split(","):
    rel, width, garment = REAL_ART[fx]
    image = ROOT / "testdata" / rel
    for arm, (flags, inset) in ARMS.items():
        C.RAIL_REACH_INSET_MM = inset
        cfg = base_cfg(width, garment, **flags)
        _g, result, _p, design = digitize_once(image, cfg)
        C.RAIL_REACH_INSET_MM = AFTER
        (d / f"{fx}-{arm}.design.json").write_text(json.dumps(design))
        if arm == "off":
            m, _per, _v = M.analyse(image, design, width, None, [])
            mres[fx] = {"off": {"K": m["K"]}}
        if arm == "lane":
            letters = {r.shape_id: {"wkt": r.polygon.wkt, "bounds": [round(v, 2) for v in r.polygon.bounds]}
                       for r in result.regions if is_lettering(r, cfg)}
            (d / f"{fx}-on.json").write_text(json.dumps({"letters": letters}))
            for k, v in sorted(letters.items(), key=lambda kv: (kv[1]["bounds"][1] // 5, kv[1]["bounds"][0])):
                print(fx, k, v["bounds"])
mfile.write_text(json.dumps(mres))
