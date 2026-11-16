import json
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
d = json.load(open(HERE / "raw.json"))
rows, summ = d["rows"], d["summaries"]
syn = json.load(open(HERE / "synth.json"))
BINS = [("<2", 0, 2), ("2-5", 2, 5), (">5", 5, 1e9)]
PAIRED = ["becker_hat_large", "hotel_fremont_patch", "golf_hat", "mfab_hat", "machine_hat", "precision_drone", "gaulke_roofing_hat"]


def q(v):
    if not v:
        return "-"
    a = np.array(v)
    return f"{np.median(a):.2f} [{np.percentile(a, 25):.2f}-{np.percentile(a, 75):.2f}]"


def cell(rs, key):
    out = []
    for name, lo, hi in BINS:
        sub = [r[key] for r in rs if lo <= r["width_mm"] < hi and r[key] is not None]
        out.append(f"n{len([r for r in rs if lo <= r['width_mm'] < hi])}: {q(sub)}")
    return out


S = {(s["side"], s["job"]): s for s in summ}
L = []
L.append("## Table 1. Pro, every DST (under-cover, median [IQR], by piece width)\n")
L.append("Width = 2 x max distance transform of the piece's footprint, thread drawn 0.4 mm wide (so it includes ~0.4 mm of thread). Cells: n pieces: footprint under-cover. Second row of each job: core under-cover (piece eroded 0.5 mm); pieces under ~1.2 mm wide have no core.\n")
L.append("| job | beanie | blocks | grounds | pieces on a ground | <2 mm | 2-5 mm | >5 mm | core <2 | core 2-5 | core >5 | core pen. ratio median |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
for s in summ:
    if s["side"] != "pro":
        continue
    rs = [r for r in rows if r["side"] == "pro" and r["job"] == s["job"]]
    pr = [r["core_pen_ratio"] for r in rs if r.get("core_pen_ratio") is not None]
    c1 = cell(rs, "under_cover_any"); c2 = cell(rs, "core_under_cover_any")
    L.append(f"| {s['job']} | {'yes' if s['beanie'] else ''} | {s['blocks']} | {len(s['grounds'])} | {len(rs)} | "
             + " | ".join(c1) + " | " + " | ".join(x.split(': ', 1)[1] for x in c2) + f" | {q(pr)} |")
L.append("\n## Table 2. Paired jobs, pro vs ours, same reader\n")
L.append("| job | side | stitches | grounds | pieces on a ground | <2 mm | 2-5 mm | >5 mm | knocked out (core uc < 0.5) | band bare 0.5 mm (median [IQR]) | outside-band bare |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|")
for j in PAIRED:
    for side in ("pro", "ours"):
        s = S.get((side, j))
        if s is None:
            L.append(f"| {j} | {side} | not read | | | | | | | | |")
            continue
        rs = [r for r in rows if r["side"] == side and r["job"] == j]
        c1 = cell(rs, "under_cover_any")
        ko = sum(1 for r in rs if r.get("knocked_out"))
        L.append(f"| {j} | {side} | {s['stitches']} | {len(s['grounds'])} | {len(rs)} | " + " | ".join(c1)
                 + f" | {ko} | {q([r['band_bare'] for r in rs])} | {q([r['band_bare_outside'] for r in rs])} |")
L.append("\n## Table 3. Ours: cost of a solid ground\n")
L.append("| job | stitches | knocked-out pieces | hole area mm2 | stitches a solid ground adds | % of job |")
L.append("|---|---|---|---|---|---|")
for j in PAIRED:
    s = S.get(("ours", j))
    if s is None:
        continue
    rs = [r for r in rows if r["side"] == "ours" and r["job"] == j]
    L.append(f"| {j} | {s['stitches']} | {sum(1 for r in rs if r.get('knocked_out'))} | {s['hole_area_mm2']} | {s['solid_cost_stitches']} | {s['solid_cost_pct']} |")
L.append("\n## Synthetic check\n")
L.append("| case | piece area | footprint width | under-cover | core under-cover | core pen. ratio | band bare | knocked out | hole mm2 (case) | solid cost st (case) |")
L.append("|---|---|---|---|---|---|---|---|---|---|")
dims = ["1 x 4", "2 x 10", "5 x 8", "4 x 8"]
for case, v in syn.items():
    for i, r in enumerate(v["rows"]):
        L.append(f"| {case} | {r['area_mm2']} mm2 | {r['width_mm']} | {r['under_cover']} | {r['core_under_cover']} | {r.get('core_pen_ratio')} | {r['band_bare']} | {r['knocked_out']} | {v['summary']['hole_area_mm2']} | {v['summary']['solid_cost_stitches']} |")
(HERE / "tables.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
