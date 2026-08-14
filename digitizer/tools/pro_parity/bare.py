import sys, json, math
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, str(Path(__file__).resolve().parent/sys.argv[1]))
from digitizer_core.pipeline import run_stages, plan_stitches
from digitizer_core.config import PipelineConfig
from shapely.geometry import LineString
from shapely.ops import unary_union
OUT=sys.argv[2]; TAG=sys.argv[3]
RES=10.0  # px/mm
for slug in sys.argv[4:]:
    man=json.load(open(Path(OUT)/"manifest.json")); e=[x for x in man if x["slug"]==slug][0]
    cfg=PipelineConfig(); cfg.fill_density_boost=True; cfg.target_width_mm=round(e["pro"]["width_mm"],1)
    res=run_stages(str(Path(OUT)/slug/"art.png"),cfg); plan=plan_stitches(res,cfg)
    runs=[list(r.points) for b in plan.blocks for r in b.runs if len(r.points)>1]
    shapes=unary_union([r.polygon for r in res.regions])
    x0,y0,x1,y1=shapes.bounds
    W=int((x1-x0)*RES)+8; H=int((y1-y0)*RES)+8
    def px(p): return (int((p[0]-x0)*RES)+4, int((p[1]-y0)*RES)+4)
    sh=np.zeros((H,W),np.uint8)
    polys=[g for g in (shapes.geoms if shapes.geom_type=="MultiPolygon" else [shapes])]
    for g in polys:
        cv2.fillPoly(sh,[np.array([px(c) for c in g.exterior.coords],np.int32)],1)
        for r in g.interiors: cv2.fillPoly(sh,[np.array([px(c) for c in r.coords],np.int32)],0)
    th=np.zeros((H,W),np.uint8)
    tw=max(1,int(0.40*RES))
    for r in runs:
        pts=[px(p) for p in r]
        for k in range(len(pts)-1): cv2.line(th,pts[k],pts[k+1],1,tw)
    bare=(sh>0)&(th==0)
    np.save(f"{Path(__file__).parent}/bare_{TAG}_{slug}.npy", bare)
    n,lab,st,_=cv2.connectedComponentsWithStats(bare.astype(np.uint8),8)
    areas=sorted(st[1:,4],reverse=True)[:5]
    print(f"{TAG} {slug}: bare={bare.sum()/RES**2:.1f}mm2 blobs={n-1} top5mm2={[round(a/RES**2,2) for a in areas]}", flush=True)
