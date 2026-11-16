"""Contrast vs the SURROUND thread (the block with most thread 0.8-1.6 mm outside the piece, rings excluded).
Same-thread pairs (dE00 < 1) counted apart; distributions over different-thread pairs."""
import json
from pathlib import Path
import numpy as np
H = Path(__file__).parent
d = json.load(open(H / "rows.json"))
rows = [r for r in d["rows"] if not r["is_ring_of_other"] and not r["ring"] and r.get("dE00_surround") is not None]
PAIRED = ["hotel_fremont_patch", "mfab_hat", "machine_hat", "precision_drone", "becker_hat_large", "golf_hat"]
def q(v):
    a = np.array(v)
    return f"n{len(a)}: min {a.min():.1f} / q1 {np.percentile(a,25):.1f} / med {np.median(a):.1f} / q3 {np.percentile(a,75):.1f} / max {a.max():.1f}" if len(a) else "-"
out = []
for side in ("pro", "ours", "ours_cartoon"):
    rs = [r for r in rows if r["side"] == side]
    same = [r for r in rs if r["dE00_surround"] < 1]
    diff = [r for r in rs if r["dE00_surround"] >= 1]
    out.append(f"- {side}: {len(rs)} unseparated pieces with colours; same thread as surround {len(same)} "
               f"({', '.join(sorted(set(r['job'] for r in same)))}); different thread: dE00 {q([r['dE00_surround'] for r in diff])}; "
               f"|dL| {q([abs(r['dL_surround']) for r in diff])}")
out.append("\n| job | pro: same-thread n; min dE00 (dL) [area mm2] | ours: same-thread n; min dE00 (dL) [area mm2] |\n|---|---|---|")
for j in PAIRED:
    c = []
    for side in ("pro", "ours"):
        rs = [r for r in rows if r["job"] == j and r["side"] == side]
        if not rs:
            c.append("not read (no PES)" if side == "pro" and j == "machine_hat" else "no unseparated piece"); continue
        same = sum(r["dE00_surround"] < 1 for r in rs)
        diff = [r for r in rs if r["dE00_surround"] >= 1]
        m = min(diff, key=lambda r: r["dE00_surround"]) if diff else None
        c.append(f"{same}; " + (f"{m['dE00_surround']:.1f} ({m['dL_surround']:+.1f}) [{m['area_mm2']:.1f}]" if m else "-"))
    out.append(f"| {j} | {c[0]} | {c[1]} |")
pd = [r for r in rows if r["side"] == "pro" and r["dE00_surround"] >= 1]
pm = min(pd, key=lambda r: r["dE00_surround"])
out.append(f"\npro minimum over different-thread pairs, all colour-read files: {pm['dE00_surround']:.2f} ({pm['job']} b{pm['block']} A{pm['area_mm2']:.1f}, {pm['piece_thread']})")
for side in ("ours", "ours_cartoon"):
    rs = [r for r in rows if r["side"] == side and r["dE00_surround"] >= 1]
    out.append(f"- {side}: {sum(r['dE00_surround'] < pm['dE00_surround'] for r in rs)} of {len(rs)} different-thread pairs below it")
out.append("\npro ten lowest different-thread: " + "; ".join(f"{r['job']} b{r['block']} {r['dE00_surround']:.1f} A{r['area_mm2']:.1f}" for r in sorted(pd, key=lambda r: r['dE00_surround'])[:10]))
for side in ("ours", "ours_cartoon"):
    rs = sorted([r for r in rows if r["side"] == side and r["dE00_surround"] >= 1], key=lambda r: r["dE00_surround"])[:10]
    out.append(f"\n{side} ten lowest different-thread unseparated:\n| job | block | area | width | piece rgb | surround rgb | dE00 | dL | idx |\n|---|---|---|---|---|---|---|---|---|")
    for r in rs:
        i = d["rows"].index(r)
        out.append(f"| {r['job']} | {r['block']} | {r['area_mm2']:.1f} | {r['width_mm']:.2f} | {tuple(r['piece_rgb'])} | {tuple(r['surround_rgb'])} | {r['dE00_surround']:.1f} | {r['dL_surround']:+.1f} | {i} |")
(H / "contrast.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
