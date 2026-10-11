import json
import sys

rows = json.load(open(sys.argv[1]))
by = {}
for r in rows:
    by[(r["case"], r["rung"], r["config"])] = r
for (c, g, cf), r in sorted(by.items()):
    pm = "-" if r["p_med"] is None else f"{r['p_med']:.4f}"
    print(f"{c:12s} {g:4} {cf:5s} p_med {pm:7s} rev {r['reversals_per_100mm']:5.2f} "
          f"right {r['right_angles_per_100mm']:6.2f} nodes {r['nodes']}")
