"""Same measurement, EMB-Bot's own plan. No DST round-trip -- read the runs
straight out of the planner, so the DST axis bug cannot colour the result."""
import math, sys
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from digitizer_core.pipeline import digitize
from digitizer_core.config import PipelineConfig

result, plan = digitize("testdata/becker_marine_logo.png", PipelineConfig())
print("design_class:", getattr(result, "design_class", None), " blocks:", len(plan.blocks))

rows = []
for b in plan.blocks:
    for run in b.runs:
        pts = np.array([(p[0], p[1]) for p in run.points], dtype=float)
        if len(pts) < 12: continue
        v = np.diff(pts, axis=0); L = np.hypot(v[:,0], v[:,1])
        k = L >= 0.8
        if k.sum() < 10: continue
        ang = (np.degrees(np.arctan2(v[k,1], v[k,0])) % 180.0); w = L[k]
        a2 = np.radians(ang*2); C=(w*np.cos(a2)).sum(); S=(w*np.sin(a2)).sum()
        mean = (math.degrees(math.atan2(S,C))/2) % 180.0
        R = math.hypot(C,S)/w.sum()
        rows.append((getattr(b,"shape_id",None), getattr(run,"kind",None), len(pts),
                     pts[:,0].min(), np.ptp(pts[:,0]), pts[:,1].min(), np.ptp(pts[:,1]),
                     mean, R, w.sum(), ang, w))
sat = [r for r in rows if 1.0 < r[4] < 30 and 1.0 < r[6] < 30]
print(f"letter-sized runs: {len(sat)}")
allang = np.concatenate([r[10] for r in sat]); allw = np.concatenate([r[11] for r in sat])
h,e = np.histogram(allang, bins=36, range=(0,180), weights=allw)
mode = e[h.argmax()]+2.5
d = np.abs((allang-mode+90)%180-90)
print(f"modal cross angle: {mode:.0f} deg")
print(f"satin length within +/-15 deg of it: {allw[d<=15].sum()/allw.sum():.1%}")
pl = np.array([r[7] for r in sat]); dd = np.abs((pl-mode+90)%180-90)
print(f"runs agreeing (+/-20): {(dd<=20).sum()}/{len(pl)}")
print("per-run mean angles:", " ".join(f"{x:.0f}" for x in pl[:40]))
