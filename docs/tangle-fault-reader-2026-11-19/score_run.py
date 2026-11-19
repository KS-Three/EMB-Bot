"""Run the tangle reader on both captures and score per the pre-registration."""
import json, sys
from pathlib import Path
import numpy as np
W = Path(sys.argv[1]); S = Path(sys.argv[2])
sys.path.insert(0, str(W / "digitizer"))
from tools import fault_reader_harness as h, tangle_fault_reader as t
D = W / "docs"
card = json.loads((D / "prime-grader/scorecard-2026-11-19.json").read_text(encoding="utf-8"))
kit = json.loads((D / "defect-marks-2026-11-10/kit.json").read_text(encoding="utf-8"))
marks = json.loads((D / "defect-marks-2026-11-10/marks.json").read_text(encoding="utf-8"))
check = {}
def run(cap, out, prefix, want=None):
    out.mkdir(parents=True, exist_ok=True)
    for f in sorted(cap.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("state") != "done": continue
        iid = "L_" + f.stem
        pf = rec.get("preflight") or {}; n = (rec.get("stats") or {}).get("stitch_count")
        check[(prefix, iid)] = {"grade": pf.get("grade"), "score": pf.get("score"), "stitches": n}
        if want is not None:
            w = want.get(iid)
            if w is None or w != n:
                print("REFUSED", prefix, iid, "stitches", n, "kit", w); continue
        res = t.read_design(rec["design"])
        np.savez_compressed(out / f"{prefix}{iid[2:]}.mask.npz", mask=res.pop("mask"), cand=res.pop("cand"))
        (out / f"{prefix}{iid[2:]}.flags.json").write_text(json.dumps(res), encoding="utf-8")
        print(prefix, iid, "flags", len(res["flags"]), "cands", len(res["candidates"]))
kw = {it["id"]: (it.get("yardstick") or {}).get("stitches") for it in kit["items"]}
run(S / "cap1119/run", S / "flagsG", "G_")
run(S / "cap1110/run", S / "flagsK", "K_", kw)
for k, v in check.items():
    if k[0] == "G_": print("G check", k[1], v, "card", card["yardstick"].get(k[1]))
def rename(m, p):
    return {"items": {p + k[2:]: v for k, v in m["items"].items() if k.startswith("L_")}}
G = rename(h.grader_marks(card), "G_"); K = rename(marks, "K_")
res = {"G": h.score_many([(G, S / "flagsG", "G_")], "tangle"),
       "K": h.score_many([(K, S / "flagsK", "K_")], "tangle"),
       "GK": h.score_many([(G, S / "flagsG", "G_"), (K, S / "flagsK", "K_")], "tangle")}
# leave-one-design-out on G, stricter null
def strict(rows, r="3.0"):
    out = {}
    for nul in ("chance_area", "chance_pick"):
        out[nul] = h.pool(rows, float(r), nul)
    return out
loo = {}
for iid in [k for k, v in res["G"]["items"].items() if v["pins"]]:
    rows = {k: v for k, v in res["G"]["items"].items() if k != iid}
    loo[iid] = strict(rows)
res["G_loo"] = loo
(S / "tangle-score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for s in ("G", "K", "GK"):
    print("==", s)
    for iid, row in res[s]["items"].items():
        b = row["by_radius"]["3.0"]
        if row["pins"]: print(f"  {iid:26s} pins {row['pins']} hit {b['hit']} area {b['chance_area']:.3f} pick {b.get('chance_pick', float('nan')):.3f} flags {row['flags']} auc {row.get('auc_area', float('nan')):.2f} nearest {row['pin_nearest_mm']}")
    for r in ("3.0", "2.0", "5.0"):
        print("  r", r, {k: (v.get("hit_rate"), v.get("chance"), v.get("kappa"), v.get("ci95")) for k, v in res[s]["pooled"][r].items()})
for k, v in loo.items(): print("LOO -", k, {n: (x.get("kappa"), x.get("ci95")) for n, x in v.items()})
