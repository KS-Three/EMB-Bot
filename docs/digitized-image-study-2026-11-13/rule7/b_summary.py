import json
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
BINS = [("<2", 0, 2), ("2-5", 2, 5), (">5", 5, 1e9)]
def q(v):
    if not v: return "-"
    a = np.array(v); return f"{np.median(a):.2f} [{np.percentile(a, 25):.2f}-{np.percentile(a, 75):.2f}]"
def c(r):
    return r["core_under_cover_any"] if r["core_under_cover_any"] is not None else r["under_cover_any"]
L = ["| fixture | width, garment | class (lane) | under-fill on | stitches | grounds | pieces on a ground | <2 mm | 2-5 mm | >5 mm | knocked out | hole mm2 | solid adds (st, %) | band bare median |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
ko_lines = []
for f in sorted((HERE / "cartoons").glob("*/read.json")):
    d = json.loads(f.read_text()); s = d["summary"]; rs = d["rows"]
    cells = []
    for _n, lo, hi in BINS:
        sub = [c(r) for r in rs if lo <= r["width_mm"] < hi]
        cells.append(f"n{len(sub)}: {q(sub)}")
    L.append(f"| {s['job']} | {s['width_mm']} mm, {s['garment']} | {s['design_class']} | {s['underfill_on']} | {s['stitches']} | "
             f"{len(s['grounds'])} | {len(rs)} | " + " | ".join(cells) +
             f" | {sum(r['knocked_out'] for r in rs)} | {s['hole_area_mm2']} | {s['solid_cost_stitches']} ({s['solid_cost_pct']}%) | {q([r['band_bare'] for r in rs])} |")
    for r in rs:
        if r["knocked_out"]:
            ko_lines.append(f"{s['job']} b{r['block']} A {r['area_mm2']} w {r['width_mm']} core {r['core_under_cover_any']} depth {r['cover_by_depth_mm']} bare {r['band_bare']}")
txt = "\n".join(L) + "\n\nKnocked-out pieces:\n```\n" + "\n".join(ko_lines) + "\n```\n"
(HERE / "b_table.md").write_text(txt, encoding="utf-8")
print(txt)
