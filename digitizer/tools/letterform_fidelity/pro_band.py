"""Inside ONE letter, is there ONE cross angle or one per stroke?

That is the whole question. A per-stroke angle is what EMB-Bot does today
(every column takes its own spine tangent). A single angle per letter/word is
what Kent says block lettering requires.
"""
import sys, math
import numpy as np, pystitch

path, ylo, yhi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
p = pystitch.read(path)
runs, cur = [], []
for x, y, cmd in p.stitches:
    if cmd == 0: cur.append((x/10.0, y/10.0))
    else:
        if len(cur) > 3: runs.append(cur); 
        cur = []
if len(cur) > 3: runs.append(cur)

print(f"{'run':>4} {'n':>5} {'x0':>7} {'w':>6} {'h':>6}  peak1(deg,share)  peak2(deg,share)  spread")
for i, r in enumerate(runs):
    a = np.array(r)
    if not (ylo <= a[:,1].mean() <= yhi): continue
    v = np.diff(a, axis=0); L = np.hypot(v[:,0], v[:,1])
    k = L > 0.35
    if k.sum() < 20: continue
    ang = (np.degrees(np.arctan2(v[k,1], v[k,0])) % 180.0)
    w = L[k]
    # length-weighted histogram, 5-degree bins, wrapped
    h, edges = np.histogram(ang, bins=36, range=(0,180), weights=w)
    order = np.argsort(h)[::-1]
    tot = h.sum()
    p1, p2 = order[0], order[1]
    # circular spread of the mass (1 - R), doubled-angle
    a2 = np.radians(ang*2); C=(w*np.cos(a2)).sum()/w.sum(); S=(w*np.sin(a2)).sum()/w.sum()
    R = math.hypot(C,S)
    print(f"{i:>4} {int(k.sum()):>5} {a[:,0].min():>7.1f} {np.ptp(a[:,0]):>6.1f} {np.ptp(a[:,1]):>6.1f}"
          f"   {edges[p1]+2.5:>5.0f} {h[p1]/tot:>6.1%}   {edges[p2]+2.5:>5.0f} {h[p2]/tot:>6.1%}"
          f"   R={R:.2f}")
