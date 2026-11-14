"""art | fill (#1519 ON) | prototype fan (rails paired by arc length) | pro, at MFab's A counter.
argv: tree corpus_dir on_run_dir out.png"""
import json
import pickle
import sys
from pathlib import Path

tree, corpus, on_dir, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
here = Path(__file__).parent
sys.argv = [sys.argv[0], str(tree), str(corpus), r"C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/eye_pairs_out/apex-guard-1114/tipgroups.json", str(here)]
sys.path.insert(0, str(tree))
sys.path.insert(0, str(here))
exec(open(here / "gain_sheets.py", encoding="utf-8").read().split("for name, sids in GAINS")[0])
from fan_proto import fan_satin  # noqa: E402

HALF = 5.0
S = 400 / (2 * HALF)
cx, cy = 17.5, -4.45
rs = json.load(open(on_dir / "runs.json"))
ours = [[(tuple(rgb), [(pts, kind, jump, False, s) for kind, jump, s, pts in runs])] for rgb, runs in rs]
cap = pickle.load(open(corpus / "off" / "mfab_hat.pkl", "rb"))
poly = next(p for p, t, s, m in cap["regions"] if s == "S6f70d810")
under, sat, info = fan_satin(poly, max_cross_mm=9.0)
others = [(rgb, pts) for rgb, pts in flat(ours) if True]
# the fan replaces the counter's own runs
fan_runs = [(rgb, pts) for blk in ours for rgb, rs_ in blk for pts, kind, jump, trim, sid in rs_ if sid != "S6f70d810"]
fan_runs += [((255, 160, 0), under), ((240, 240, 240), sat)]
j = pb.JOBS["mfab_hat"]
path = pb.resolve(j[4]) if len(j) > 4 and j[4] else pb.resolve(j[3])
pro = pro_runs(path, register(path, ours))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
row = [panel(flat(ours), cx, cy, "fill (#1519 ON)"), panel(fan_runs, cx, cy, f"fan proto, cross {info['longest']} mm"),
       panel(pro, cx, cy, "pro")]
cv2.imwrite(str(outp), np.hstack(row))
print("wrote", outp, info)
