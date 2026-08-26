"""What stitch angle does the PRO use, letter by letter?

Satin lays crosses back and forth across a column, so each stitch segment runs
(near enough) along the cross direction. Angle mod 180 -- a cross sewn either
way round is the same angle. If a pro sets one angle for a word, every letter's
dominant angle is the same number.
"""
import sys, math, collections
import numpy as np
import pystitch

path = sys.argv[1]
p = pystitch.read(path)
st = p.stitches

# Break at anything that is not a normal stitch (jump/trim/colour/end).
runs, cur = [], []
for x, y, cmd in st:
    if cmd == 0:
        cur.append((x / 10.0, y / 10.0))          # 0.1mm units -> mm
    else:
        if len(cur) > 3: runs.append(cur)
        cur = []
if len(cur) > 3: runs.append(cur)

def dominant_angle(pts):
    """Circular mode of segment angles, doubled so 0 and 180 coincide."""
    v = np.diff(np.array(pts), axis=0)
    L = np.hypot(v[:, 0], v[:, 1])
    keep = L > 0.35                                # ignore travel/anchor micro-steps
    if keep.sum() < 4: return None, 0.0, 0
    a = np.arctan2(v[keep, 1], v[keep, 0]) * 2.0   # double-angle => mod 180
    w = L[keep]
    C, S = (w * np.cos(a)).sum(), (w * np.sin(a)).sum()
    R = math.hypot(C, S) / w.sum()                 # 1.0 = perfectly parallel
    ang = (math.degrees(math.atan2(S, C)) / 2.0) % 180.0
    return ang, R, int(keep.sum())

print(f"{'#':>3} {'n':>5} {'x0':>7} {'x1':>7} {'y0':>7} {'y1':>7} {'w':>6} {'h':>6} {'angle':>7} {'concen':>7}")
rows = []
for i, r in enumerate(runs):
    a = np.array(r)
    ang, R, n = dominant_angle(r)
    if ang is None: continue
    x0, y0 = a.min(0); x1, y1 = a.max(0)
    rows.append((i, n, x0, x1, y0, y1, x1 - x0, y1 - y0, ang, R))
    print(f"{i:>3} {n:>5} {x0:>7.1f} {x1:>7.1f} {y0:>7.1f} {y1:>7.1f} {x1-x0:>6.1f} {y1-y0:>6.1f} {ang:>7.1f} {R:>7.2f}")

# Only well-aligned, letter-sized runs speak to a lettering convention.
lets = [r for r in rows if r[9] > 0.55 and 1.0 < r[6] < 25 and 1.0 < r[7] < 25]
print(f"\ncoherent letter-sized runs: {len(lets)} of {len(rows)}")
if lets:
    angs = np.array([r[8] for r in lets])
    a2 = np.radians(angs * 2)
    C, S = np.cos(a2).mean(), np.sin(a2).mean()
    print(f"  circular mean angle : {(math.degrees(math.atan2(S, C))/2)%180:.1f} deg")
    print(f"  circular concentration: {math.hypot(C,S):.3f}   (1.0 = every letter identical)")
    print("  per-run angles:", " ".join(f"{x:.0f}" for x in sorted(angs)))
    h = collections.Counter((int(x)//10)*10 for x in angs)
    print("  histogram (10 deg bins):", dict(sorted(h.items())))
