"""Read every pro DST (registry, minus Test Files) and every ours.dst in scratch/ours."""
import json, sys
from pathlib import Path
HERE = Path(__file__).parent
REPO = Path(r"C:\Users\EE-LT-11030\Claude Personal\EMB-Bot")
sys.path.insert(0, str(REPO / "digitizer"))
sys.path.insert(0, str(HERE))
import reader
from tools import pro_intake

reg = json.loads((REPO / "scratch_kent/pro_intake/registry.json").read_text(encoding="utf-8"))
slugs = [p["slug"] for j in reg["jobs"].values() for p in j["pairs"] if not p["slug"].startswith("test_files")]
rows, summ = [], []
for s in slugs:
    rec = pro_intake.pair_record(s)
    dst = Path(rec["dst"])
    r, sm = reader.read_file(dst, s)
    for x in r:
        x["side"] = "pro"
    sm.update(side="pro", file=dst.name, beanie="beanie" in s or "BEANI" in dst.name.upper())
    rows += r; summ.append(sm)
    print("pro", s, len(r), sm["grounds"], flush=True)
for d in sorted((HERE / "ours").iterdir()):
    f = d / "ours.dst"
    if not f.exists():
        continue
    r, sm = reader.read_file(f, d.name)
    for x in r:
        x["side"] = "ours"
    sm.update(side="ours", file=str(f), beanie=False)
    rows += r; summ.append(sm)
    print("ours", d.name, len(r), sm["grounds"], sm["solid_cost_stitches"], flush=True)


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if hasattr(o, "item"):
        return o.item()
    return o


json.dump(clean(dict(rows=rows, summaries=summ)), open(HERE / "raw.json", "w"), indent=1)
