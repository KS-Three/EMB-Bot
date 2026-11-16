"""Tables from rows.json -> tables.md, results.json (per-piece rows, slimmed)."""
import json
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
d = json.load(open(HERE / "rows.json"))
rows = [r for r in d["rows"] if not r["is_ring_of_other"]]
ringof = [r for r in d["rows"] if r["is_ring_of_other"]]
summ = {(s["job"], s["side"]): s for s in d["summaries"]}
PAIRED = ["hotel_fremont_patch", "mfab_hat", "machine_hat", "precision_drone", "becker_hat_large", "golf_hat"]
FRAG = 2.0
out = []


def q(v):
    if not v:
        return "-"
    a = np.array(v)
    return f"n{len(a)}: min {a.min():.1f} / q1 {np.percentile(a,25):.1f} / med {np.median(a):.1f} / q3 {np.percentile(a,75):.1f} / max {a.max():.1f}"


def counts(job, side):
    rs = [r for r in rows if r["job"] == job and r["side"] == side]
    big = [r for r in rs if r["area_mm2"] >= FRAG]
    return dict(pieces=len(rs), pieces_ge2=len(big),
                ring=sum(r["ring"] for r in rs), ring_ge2=sum(r["ring"] for r in big),
                own=sum(r["own_colour_ring"] for r in rs), own_ge2=sum(r["own_colour_ring"] for r in big),
                ring_pieces_dropped=sum(1 for r in ringof if r["job"] == job and r["side"] == side),
                colours=summ[(job, side)]["colours"])


out.append("## Counts per file (pieces on a ground; a piece that is itself another's ring is not counted)\n")
out.append("| side | job | pieces | pieces >= 2 mm2 | contrast ring (all / >= 2 mm2) | own-colour ring (all / >= 2 mm2) | colours |")
out.append("|---|---|---|---|---|---|---|")
for s in d["summaries"]:
    c = counts(s["job"], s["side"])
    out.append(f"| {s['side']} | {s['job']} | {c['pieces']} | {c['pieces_ge2']} | {c['ring']} / {c['ring_ge2']} | "
               f"{c['own']} / {c['own_ge2']} | {c['colours']} |")
for side in ("pro", "ours", "ours_cartoon"):
    rs = [r for r in rows if r["side"] == side]
    big = [r for r in rs if r["area_mm2"] >= FRAG]
    out.append(f"\n**{side} total**: pieces {len(rs)} ({len(big)} >= 2 mm2); contrast ring {sum(r['ring'] for r in rs)} "
               f"({sum(r['ring'] for r in big)} >= 2 mm2); own-colour ring {sum(r['own_colour_ring'] for r in rs)} "
               f"({sum(r['own_colour_ring'] for r in big)} >= 2 mm2)")
    if side == "pro":
        pr = [r for r in rs if r["job"] in PAIRED]
        out.append(f"  paired jobs only: pieces {len(pr)}; contrast ring {sum(r['ring'] for r in pr)} "
                   f"({sum(r['ring'] for r in pr if r['area_mm2'] >= FRAG)} >= 2 mm2); own {sum(r['own_colour_ring'] for r in pr)}")

out.append("\n## Contrast of pieces with NO contrast ring (thread colours; colour-not-read files left out)\n")
for side in ("pro", "ours", "ours_cartoon"):
    for scope, sel in (("all", lambda r: True), (">= 2 mm2", lambda r: r["area_mm2"] >= FRAG)):
        rs = [r for r in rows if r["side"] == side and not r["ring"] and r.get("dE00_ground") is not None and sel(r)]
        out.append(f"- {side} {scope}: dE00 piece-ground {q([r['dE00_ground'] for r in rs])}; |dL| {q([abs(r['dL_ground']) for r in rs])}; "
                   f"dE00 piece-surround {q([r['dE00_surround'] for r in rs if r.get('dE00_surround') is not None])}")
out.append("\n### (a) lowest-contrast unseparated pair per paired job\n")
out.append("| job | pro min dE00 (dL) [area] | ours min dE00 (dL) [area] | pro min >= 2 mm2 | ours min >= 2 mm2 |")
out.append("|---|---|---|---|---|")
for j in PAIRED:
    cells = []
    for big in (False, True):
        for side in ("pro", "ours"):
            rs = [r for r in rows if r["job"] == j and r["side"] == side and not r["ring"]
                  and r.get("dE00_ground") is not None and (not big or r["area_mm2"] >= FRAG)]
            if not rs:
                cells.append("not read" if summ[(j, side)]["colours"].startswith(("no PES", "colours not")) else "none")
                continue
            m = min(rs, key=lambda r: r["dE00_ground"])
            cells.append(f"{m['dE00_ground']:.1f} ({m['dL_ground']:+.1f}) [{m['area_mm2']:.1f}]")
    out.append(f"| {j} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
pro_all = [r for r in rows if r["side"] == "pro" and not r["ring"] and r.get("dE00_ground") is not None]
pmin = min(r["dE00_ground"] for r in pro_all)
pmin2 = min(r["dE00_ground"] for r in pro_all if r["area_mm2"] >= FRAG)
out.append(f"\n### (b) pro minimum across all his colour-read files: {pmin:.2f} (all pieces), {pmin2:.2f} (>= 2 mm2)\n")
for side in ("ours", "ours_cartoon"):
    rs = [r for r in rows if r["side"] == side and not r["ring"] and r.get("dE00_ground") is not None]
    out.append(f"- {side}: {sum(r['dE00_ground'] < pmin for r in rs)} of {len(rs)} below {pmin:.2f}; "
               f">= 2 mm2: {sum(r['dE00_ground'] < pmin2 for r in rs if r['area_mm2'] >= FRAG)} of "
               f"{sum(r['area_mm2'] >= FRAG for r in rs)} below {pmin2:.2f}")
lowpro = sorted(pro_all, key=lambda r: r["dE00_ground"])[:8]
out.append("\npro lowest: " + "; ".join(f"{r['job']} b{r['block']} {r['dE00_ground']:.1f} A{r['area_mm2']:.1f} "
                                        f"{r['piece_thread']}/{r['ground_thread']}" for r in lowpro))
for side in ("ours", "ours_cartoon"):
    rs = sorted([r for r in rows if r["side"] == side and not r["ring"] and r.get("dE00_ground") is not None],
                key=lambda r: r["dE00_ground"])[:10]
    out.append(f"\n### {side}: ten lowest unseparated (vs host ground)\n")
    out.append("| job | block | area mm2 | width mm | piece rgb | ground rgb | dE00 | dL | surround dE00 | own-colour ring |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rs:
        out.append(f"| {r['job']} | {r['block']} | {r['area_mm2']:.1f} | {r['width_mm']:.2f} | {tuple(r['piece_rgb'])} | "
                   f"{tuple(r['ground_rgb'])} | {r['dE00_ground']:.1f} | {r['dL_ground']:+.1f} | {r.get('dE00_surround')} | {r['own_colour_ring']} |")
out.append("\n## Ringed pieces (for the by-eye calls)\n")
for r in rows:
    if r["ring"] or r["own_colour_ring"]:
        out.append(f"- {r['side']} {r['job']} b{r['block']} A{r['area_mm2']:.1f} w{r['width_mm']:.2f} "
                   f"contrast={[(c['block'], c['cov'], c['far'], c.get('thread'), c.get('dE_to_piece'), c.get('dE_to_ground')) for c in r['contrast_rings']]} "
                   f"own_blk={[c['block'] for c in r['own_colour_rings_block']]} own_satin={r['own_satin_edge_cov']} "
                   f"piece={r.get('piece_thread')} ground={r.get('ground_thread')} dEg={r.get('dE00_ground')}")
(HERE / "tables.md").write_text("\n".join(out), encoding="utf-8")
keep = ["job", "side", "block", "host_ground_block", "area_mm2", "width_mm", "bbox_mm", "ring", "contrast_rings",
        "own_colour_ring", "own_colour_rings_block", "own_satin_edge_ring", "own_satin_edge_cov", "piece_rgb",
        "piece_thread", "ground_rgb", "ground_thread", "dE00_ground", "dL_ground", "surround_block", "surround_rgb",
        "dE00_surround", "dL_surround", "colours"]
slim = [{k: r.get(k) for k in keep} | {"is_ring_of_other": r["is_ring_of_other"]} for r in d["rows"]]
json.dump(dict(rows=slim, files=[{k: v for k, v in s.items() if k != "block_colours"} for s in d["summaries"]]),
          open(HERE / "results.json", "w"), indent=1, default=str)
print("\n".join(out))
