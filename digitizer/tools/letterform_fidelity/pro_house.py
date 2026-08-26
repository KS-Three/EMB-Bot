"""Does the pro hold ONE cross angle across a whole lettering run?

Measured on stitch LENGTH, not stitch count, and only on stitches long enough
to be satin crosses (>=0.8mm) -- underlay and travel are short and would wash
the signal out. Reports, per file: the modal angle over the text band, and how
much of the satin length lies within +/-15 deg of it.
"""
import sys, math
import numpy as np, pystitch

# Only stitches this long count as satin crosses; underlay and travel are short
# and would wash the signal out. 0.8 is the value the reported figures use.
# The pro's modal angle held at 2 deg across 0.8 / 1.5 / 2.2, so the finding is
# not an artefact of where this cut is drawn -- but the AGREEMENT count does
# move (6/7 at 0.8 and 1.5, 5/7 at 2.2), so quote it with the threshold.
CROSS_MIN_MM = 0.8

def band_runs(path, ylo, yhi):
    p = pystitch.read(path); runs, cur = [], []
    for x, y, cmd in p.stitches:
        if cmd == 0: cur.append((x/10.0, y/10.0))
        else:
            if len(cur) > 3: runs.append(cur)
            cur = []
    if len(cur) > 3: runs.append(cur)
    out = []
    for r in runs:
        a = np.array(r)
        if ylo <= a[:,1].mean() <= yhi: out.append(a)
    return out

def seg(a):
    v = np.diff(a, axis=0); L = np.hypot(v[:,0], v[:,1])
    k = L >= CROSS_MIN_MM                         # satin crosses only
    if k.sum() < 10: return None, None
    return (np.degrees(np.arctan2(v[k,1], v[k,0])) % 180.0), L[k]

for path, ylo, yhi in [(p_.split(':')[0], float(p_.split(':')[1]), float(p_.split(':')[2])) for p_ in sys.argv[1:]]:
    runs = band_runs(path, ylo, yhi)
    A, W = [], []
    per_letter = []
    for a in runs:
        ang, w = seg(a)
        if ang is None: continue
        A.append(ang); W.append(w)
        a2 = np.radians(ang*2); C=(w*np.cos(a2)).sum(); S=(w*np.sin(a2)).sum()
        per_letter.append((math.degrees(math.atan2(S,C))/2) % 180.0)
    if not A: print(f"{path}: no band runs"); continue
    ang = np.concatenate(A); w = np.concatenate(W)
    h, e = np.histogram(ang, bins=36, range=(0,180), weights=w)
    mode = e[h.argmax()] + 2.5
    d = np.abs((ang - mode + 90) % 180 - 90)      # angular distance, mod 180
    within = w[d <= 15].sum() / w.sum()
    print(f"\n{path.split('/')[-1]}")
    print(f"  letter-ish runs in band : {len(per_letter)}")
    print(f"  modal cross angle       : {mode:.0f} deg")
    print(f"  satin length within +/-15 deg of it : {within:.1%}")
    pl = np.array(per_letter)
    dd = np.abs((pl - mode + 90) % 180 - 90)
    print(f"  per-run mean angles     : " + " ".join(f"{x:.0f}" for x in pl))
    print(f"  runs agreeing (+/-20)   : {(dd<=20).sum()}/{len(pl)}")
