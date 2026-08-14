"""What did the SHIPPED path stop emitting near a point?

Runs plan_stitches under both digitizer trees and reports the runs whose
geometry sits within R mm of the target point, per tree. No assumption about
which internal function produced them.

Usage: lostruns.py <dz_before> <dz_after> <corpus_out> <slug> <x_mm> <y_mm> [radius]
"""
import sys, json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = "/home/user/EMB-Bot/digitizer/.venv/bin/python"

RUNNER = r'''
import sys, json
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from digitizer_core.pipeline import run_stages, plan_stitches
from digitizer_core.config import PipelineConfig
from shapely.geometry import Point, LineString
OUT, slug, X, Y, R, dest = sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), sys.argv[7]
man = json.load(open(Path(OUT)/"manifest.json")); e=[x for x in man if x["slug"]==slug][0]
cfg = PipelineConfig(); cfg.fill_density_boost=True; cfg.target_width_mm=round(e["pro"]["width_mm"],1)
res = run_stages(str(Path(OUT)/slug/"art.png"), cfg); plan = plan_stitches(res, cfg)
p = Point(X, Y)
out=[]
for bi,b in enumerate(plan.blocks):
    for ri,r in enumerate(b.runs):
        pts=list(r.points)
        if len(pts)<2: continue
        ls=LineString(pts)
        d=ls.distance(p)
        if d<=R:
            out.append({"block":bi,"run":ri,"dist":round(d,3),"n":len(pts),
                        "len_mm":round(ls.length,2),
                        "shape_id":getattr(r,"shape_id",None) or getattr(b,"shape_id",None),
                        "kind":str(getattr(r,"kind",None) or getattr(r,"stitch_type",None)),
                        "bounds":[round(v,2) for v in ls.bounds]})
out.sort(key=lambda x:x["dist"])
json.dump(out, open(dest,"w"), indent=1)
print(f"  runs within {R}mm: {len(out)}")
'''
rp = HERE / "_lostrun.py"; rp.write_text(RUNNER)
dz_b, dz_a, OUT, slug, X, Y = sys.argv[1:7]
R = sys.argv[7] if len(sys.argv) > 7 else "2.0"
res = {}
for dz, nm in ((dz_b, "before"), (dz_a, "after")):
    print(nm, end=": ")
    subprocess.run([PY, str(rp), str((HERE / dz).resolve()), OUT, slug, X, Y, R,
                    str(HERE / f"_lr_{nm}.json")], check=True)
    res[nm] = json.load(open(HERE / f"_lr_{nm}.json"))

def key(r): return (r["shape_id"], tuple(r["bounds"]), r["n"])
kb = {key(r): r for r in res["before"]}
ka = {key(r): r for r in res["after"]}
print(f"\nLOST (in before, not after): {len(set(kb)-set(ka))}")
for k in sorted(set(kb) - set(ka), key=lambda k: kb[k]["dist"])[:10]:
    r = kb[k]; print(f"   shape={r['shape_id']} kind={r['kind']} n={r['n']} len={r['len_mm']}mm dist={r['dist']}mm bounds={r['bounds']}")
print(f"GAINED (in after, not before): {len(set(ka)-set(kb))}")
for k in sorted(set(ka) - set(kb), key=lambda k: ka[k]["dist"])[:10]:
    r = ka[k]; print(f"   shape={r['shape_id']} kind={r['kind']} n={r['n']} len={r['len_mm']}mm dist={r['dist']}mm bounds={r['bounds']}")
