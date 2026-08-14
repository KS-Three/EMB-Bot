"""Which region owns a design-mm point, and what does _corner_forks say there?

Usage: whichshape.py <dz> <corpus_out> <slug> <x_mm> <y_mm>
"""
import sys, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str((HERE / sys.argv[1]).resolve()))
from digitizer_core.pipeline import run_stages, plan_stitches
from digitizer_core.config import PipelineConfig
from shapely.geometry import Point

OUT, slug, X, Y = sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
man = json.load(open(Path(OUT) / "manifest.json"))
e = [x for x in man if x["slug"] == slug][0]
cfg = PipelineConfig(); cfg.fill_density_boost = True
cfg.target_width_mm = round(e["pro"]["width_mm"], 1)
res = run_stages(str(Path(OUT) / slug / "art.png"), cfg)
p = Point(X, Y)
hits = [r for r in res.regions if r.polygon.buffer(0.6).contains(p)]
if not hits:
    hits = sorted(res.regions, key=lambda r: r.polygon.distance(p))[:2]
    print("(no containing region; nearest shown)")
for r in hits:
    print(f"shape {r.shape_id}  tier={getattr(r,'tier',None)}  area={r.polygon.area:.1f}mm2 "
          f"dist={r.polygon.distance(p):.2f}mm bounds={[round(v,1) for v in r.polygon.bounds]}")

import digitizer_core.stage6_satin as S
for r in hits:
    print(f"\n--- {r.shape_id} ---")
    try:
        strokes, dbg, extra = S.extract_strokes(r.polygon)
    except Exception as ex:
        print("  extract_strokes:", type(ex).__name__, ex); continue
    print(f"  strokes={len(strokes)}")
    for k, s in enumerate(strokes):
        L = sum(((a[0]-b[0])**2 + (a[1]-b[1])**2) ** .5 for a, b in zip(s.spine, s.spine[1:]))
        near = min(Point(q).distance(p) for q in s.spine)
        print(f"   [{k}] len={L:5.2f}mm free=({s.free_start},{s.free_end}) "
              f"closed={s.closed} capped=({getattr(s,'capped_start',None)},"
              f"{getattr(s,'capped_end',None)}) tuck=({getattr(s,'tuck_under_start',None)},"
              f"{getattr(s,'tuck_under_end',None)}) min_dist_to_pt={near:.2f}mm")
