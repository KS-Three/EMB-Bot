"""Digitize the eye-pair logos three ways and record every straight column's
fanned ends, per lettering shape.

  off     shipped (both lane flags OFF)
  before  lane ON as on main before this change: `outline_cut._fan_ends`
          read from MAIN_SRC (a copy of main's outline_cut.py) and
          `columns._reach_fan_faces` off
  after   lane ON, this branch

usage (cwd digitizer/):  python run_arms.py OUTDIR MAIN_SRC fixture[,fixture]
Writes OUTDIR/<fx>-<arm>.design.json, OUTDIR/<fx>-on.json (letters, for
#828's matched.py / letterpic.py) and OUTDIR/<fx>-fans.json:
{arm: {shape_id: [{"end": +-1, "pivot_moved": bool, "fan": n_crosses}]}}.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.getcwd())
from tools.eye_pairs.features import base_cfg, digitize_once  # noqa: E402
from tools.thin_strokes import REAL_ART, ROOT  # noqa: E402
import digitizer_core.outline_cut as OC  # noqa: E402
import digitizer_core.columns as C  # noqa: E402
import digitizer_core.stage7_sequence as S7  # noqa: E402
from digitizer_core.columns import is_lettering  # noqa: E402

NEW_FAN = OC._fan_ends
NEW_CORNER = OC._slant_corner
NEW_REACH = C._reach_fan_faces


def old_fan(main_src):
    src = open(main_src, encoding="utf-8").read()
    m = re.search(r"^def _fan_ends\(.*?(?=^def )", src, re.S | re.M)
    ns = dict(vars(OC))
    exec(m.group(0), ns)
    return ns["_fan_ends"]


CUR = {"sid": None, "arm": None}
REC = {}       # id(piece) -> list of ends fanned in the LAST build of that piece
FANS = {}
_lc, _lcs = OC.letter_columns, C.lettering_columns_shape


def recording(fan_fn):
    def fan(st, piece, u, pitch_mm, W):
        moved = {}

        def corner_rec(*a, **k):
            r = NEW_CORNER(*a, **k)
            moved[a[5]] = r is not None            # a[5] is `end`
            return r
        OC._slant_corner = corner_rec
        out = fan_fn(st, piece, u, pitch_mm, W)
        OC._slant_corner = NEW_CORNER
        ends = []
        for end in (1, -1):
            b = out if end > 0 else out[::-1]
            if len(b) < 2:
                continue
            # a fan's crosses all share its pivot: count them from this end
            shared = [p for p in b[-1] if p in b[-2]]
            if not shared:
                continue
            P = shared[0]
            n = 0
            while n < len(b) and P in b[-1 - n]:
                n += 1
            ends.append({"end": end, "fan": n})
        REC[id(piece)] = (ends, moved, piece)
        return out
    return fan


def lc(poly, pitch_mm=0.4):
    REC.clear()
    cut = _lc(poly, pitch_mm)
    rows = []
    for col in cut.columns:
        r = REC.get(id(col.piece))
        if r is None:
            continue
        ends, moved, _p = r
        for e in ends:
            e = dict(e)
            e["pivot_moved"] = bool(moved.get(e["end"], False))
            rows.append(e)
    FANS.setdefault(CUR["arm"], {})[CUR["sid"]] = rows
    return cut


def lcs(poly, shape_id, **k):
    CUR["sid"] = shape_id
    return _lcs(poly, shape_id, **k)


OC.letter_columns = lc
C.lettering_columns_shape = lcs
S7.lettering_columns_shape = lcs

ARMS = {"off": {}, "before": {"lettering_columns": True, "lettering_words": True},
        "after": {"lettering_columns": True, "lettering_words": True}}

if __name__ == "__main__":
    outdir, main_src = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    OLD = old_fan(main_src)
    for fx in sys.argv[3].split(","):
        FANS.clear()
        rel, width, garment = REAL_ART[fx]
        image = ROOT / "testdata" / rel
        for arm, flags in ARMS.items():
            CUR["arm"] = arm
            OC._fan_ends = recording(OLD if arm == "before" else NEW_FAN)
            # main had no slant-face reach either
            C._reach_fan_faces = (lambda st, a, b, r: (list(a), list(b))) if arm == "before" else NEW_REACH
            cfg = base_cfg(width, garment, **flags)
            gen, result, plan, design = digitize_once(image, cfg)
            json.dump(design, open(os.path.join(outdir, f"{fx}-{arm}.design.json"), "w"))
            st = sum(1 for s in design["stitches"] if s.get("type") == "stitch")
            print(fx, arm, "stitches", st, flush=True)
            if arm == "after":
                letters = {r.shape_id: {"wkt": r.polygon.wkt, "area": round(r.polygon.area, 3)}
                           for r in result.regions if is_lettering(r, cfg)}
                json.dump({"letters": letters}, open(os.path.join(outdir, f"{fx}-on.json"), "w"))
        json.dump(FANS, open(os.path.join(outdir, f"{fx}-fans.json"), "w"), indent=1)
