"""Re-run our pipeline (one job at a time) on the six paired jobs + four cartoons.
Writes ours/<job>/ours.dst and ours/<job>/plan.json (per block rgb, border-role runs)."""
import hashlib, json, sys, time
from pathlib import Path
HERE = Path(__file__).parent
REPO = Path(r"C:\Users\EE-LT-11030\Claude Personal\EMB-Bot")
R7 = HERE.parent / "rule7"
sys.path.insert(0, str(REPO / "digitizer"))
from tools import pro_pair
from tools.pro_intake import pair_record
from digitizer_core.export import write_dst

TD = REPO / "digitizer/testdata"
JOBS = []
for s in ["hotel_fremont_patch", "mfab_hat", "machine_hat", "precision_drone", "becker_hat_large", "golf_hat"]:
    rec = pair_record(s)
    JOBS.append((s, rec["art"], rec["width_mm"], rec["garment_id"] or "hat_front", R7 / "ours" / s / "ours.dst"))
JOBS += [("pooh", REPO / "scratch_kent/pooh_hunny_266px.jpg", 54.6, "left_chest", R7 / "cartoons/pooh/ours.dst"),
         ("owl_kent", TD / "photo/owl_kent.jpg", 127.0, "hat_front", R7 / "cartoons/owl_kent/ours.dst"),
         ("tux_gradient_mascot", TD / "photo/corpus/gradient_mascot.png", 80.0, "left_chest",
          R7 / "cartoons/tux_gradient_mascot/ours.dst"),
         ("bison_flat_emoji", TD / "photo/corpus/flat_emoji_icon.png", 80.0, "left_chest",
          R7 / "cartoons/bison_flat_emoji/ours.dst")]
only = sys.argv[1:]
for name, art, w, g, old in JOBS:
    if only and name not in only:
        continue
    out = HERE / "ours" / name
    out.mkdir(parents=True, exist_ok=True)
    t = time.time()
    d = pro_pair.digitize(art, w, g)
    write_dst(d.plan, out / "ours.dst")
    blocks = []
    for bi, b in enumerate(d.plan.blocks):
        border = [[list(map(float, p)) for p in r.points] for r in b.runs if r.role == "border"]
        blocks.append(dict(i=bi, rgb=list(b.rgb), thread=b.thread_number,
                           n_points=sum(len(r.points) for r in b.runs),
                           kinds=sorted({str(r.kind) for r in b.runs}),
                           border_runs=border))
    (out / "plan.json").write_text(json.dumps(dict(job=name, art=str(art), width_mm=w, garment=g,
                                                    blocks=blocks), default=str))
    new = hashlib.md5((out / "ours.dst").read_bytes()).hexdigest()
    oldh = hashlib.md5(old.read_bytes()).hexdigest() if old.exists() else None
    print(name, "secs", round(time.time() - t), "blocks", len(blocks), "md5", new,
          "rule7_md5", oldh, "same" if new == oldh else "DIFF", flush=True)
