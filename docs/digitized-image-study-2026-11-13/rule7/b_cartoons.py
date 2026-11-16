"""B: today's pipeline on cartoon/character fixtures (Studio request via tools.pro_pair.digitize, as
tools.photo_corpus does), our DST read with reader.py. One job at a time."""
import json, sys, time
from pathlib import Path
HERE = Path(__file__).parent
REPO = Path(r"C:\Users\EE-LT-11030\Claude Personal\EMB-Bot")
sys.path.insert(0, str(REPO / "digitizer")); sys.path.insert(0, str(HERE))
from tools import pro_pair
import digitizer_core.pipeline as P
from digitizer_core.export import write_dst
import reader

cap = {}
_gate = P.gate_underfill_for_photo
def gate(cfg, cls, keyline_art=False):
    c = _gate(cfg, cls, keyline_art)
    cap.update(cls=cls, keyline=keyline_art, underfill=c.silhouette_underfill)
    return c
P.gate_underfill_for_photo = gate

TD = REPO / "digitizer/testdata"
JOBS = [("pooh", REPO / "scratch_kent/pooh_hunny_266px.jpg", 54.6, "left_chest"),
        ("owl_kent", TD / "photo/owl_kent.jpg", 127.0, "hat_front"),
        ("tux_gradient_mascot", TD / "photo/corpus/gradient_mascot.png", 80.0, "left_chest"),
        ("bison_flat_emoji", TD / "photo/corpus/flat_emoji_icon.png", 80.0, "left_chest")]
only = sys.argv[1:]
for name, art, w, g in JOBS:
    if only and name not in only:
        continue
    out = HERE / "cartoons" / name
    out.mkdir(parents=True, exist_ok=True)
    t = time.time()
    d = pro_pair.digitize(art, w, g)
    write_dst(d.plan, out / "ours.dst")
    rows, s = reader.read_file(out / "ours.dst", name)
    for r in rows:
        r["side"] = "ours_cartoon"
    s.update(side="ours_cartoon", design_class=cap.get("cls"), underfill_on=cap.get("underfill"),
             white_keyline_art=cap.get("keyline"), width_mm=w, garment=g, secs=round(time.time() - t))
    def clean(o):
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list): return [clean(v) for v in o]
        return o.item() if hasattr(o, "item") else o
    (out / "read.json").write_text(json.dumps(clean(dict(rows=rows, summary=s)), indent=1))
    print(name, "class", s["design_class"], "underfill", s["underfill_on"], "stitches", s["stitches"],
          "pieces", len(rows), "KO", sum(r["knocked_out"] for r in rows), "cost", s["solid_cost_stitches"],
          s["solid_cost_pct"], "secs", s["secs"], flush=True)
