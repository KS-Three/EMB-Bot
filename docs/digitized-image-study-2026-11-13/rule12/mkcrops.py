"""crops for: every ringed / own-colour-ringed piece (both sides), and ours' ten lowest-contrast
unseparated pairs (paired jobs) + cartoon lowest. Writes crops/index.json."""
import json, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import reader, crops

d = json.load(open(HERE / "rows.json"))
S = {(s["job"], s["side"]): s for s in d["summaries"]}
out = HERE / "crops"; out.mkdir(exist_ok=True)
pts_cache = {}
idx = []


def pts_of(s):
    if s["dst"] not in pts_cache:
        pts_cache[s["dst"]] = reader.points_of(s["dst"])
    return pts_cache[s["dst"]]


def box(r):
    x0, y0, x1, y1 = r["bbox_mm"]
    return (x0 + 2, y0 + 2, x1 - 2, y1 - 2)   # reader bbox carries a 2 mm pad


def make(r, name, title):
    s = S[(r["job"], r["side"])]
    art = s.get("art")
    crops.sheet(out / name, pts_of(s), s.get("block_colours"), art if art and Path(str(art)).exists() else None,
                box(r), title)
    idx.append(dict(file=name, job=r["job"], side=r["side"], block=r["block"], bbox_mm=r["bbox_mm"]))


rows = d["rows"]
for i, r in enumerate(rows):
    r["_i"] = i
k = 0
for r in rows:
    if r["is_ring_of_other"]:
        continue
    if r["ring"] or r["own_colour_ring"]:
        tag = "ring" if r["ring"] else "own"
        make(r, f"{tag}_{r['side']}_{r['job']}_b{r['block']}_{r['_i']}.png",
             f"{r['side']} {r['job']} b{r['block']} A{r['area_mm2']:.1f} w{r['width_mm']:.1f} {tag}")
        k += 1
low = sorted([r for r in rows if r["side"] in ("ours", "ours_cartoon") and not r["is_ring_of_other"]
              and not r["ring"] and r.get("dE00_surround") is not None and r["dE00_surround"] >= 1],
             key=lambda r: r["dE00_surround"])
for side in ("ours", "ours_cartoon"):
    for r in [x for x in low if x["side"] == side][:10]:
        make(r, f"low_{side}_{r['job']}_b{r['block']}_{r['_i']}.png",
             f"{side} {r['job']} b{r['block']} dE {r['dE00_surround']} dL {r['dL_surround']}")
json.dump(idx, open(out / "index.json", "w"), indent=1)
print("crops", len(idx), "ringed", k)
