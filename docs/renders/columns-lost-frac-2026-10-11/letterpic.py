"""Close-up of letters: artwork outline, sewn thread (satin runs of that
shape, drawn 0.4 mm wide), ink with no thread (red) and thread more than
0.5 mm outside the ink (blue). One panel per arm, side by side.

usage: letterpic.py DIR fixture out.png sid[,sid...] [arm,arm] [px_per_mm]
"""
import json
import sys

import cv2
import numpy as np
from shapely import wkt

d, fx, out = sys.argv[1], sys.argv[2], sys.argv[3]
sids = sys.argv[4].split(',')
arms = (sys.argv[5] if len(sys.argv) > 5 else 'off,on').split(',')
S = float(sys.argv[6]) if len(sys.argv) > 6 else 30.0
L = json.load(open(f'{d}/{fx}-on.json'))['letters']
polys = [wkt.loads(L[s]['wkt']) for s in sids]
x0 = min(p.bounds[0] for p in polys) - 1.0
y0 = min(p.bounds[1] for p in polys) - 1.0
x1 = max(p.bounds[2] for p in polys) + 1.0
y1 = max(p.bounds[3] for p in polys) + 1.0
W, H = int((x1 - x0) * S), int((y1 - y0) * S)


def px(x, y):
    # plan y is down-positive?  design y = -plan_y*10, plan coords are image-like (y down)
    return int(round((x - x0) * S)), int(round((y - y0) * S))


ART = None
if len(sys.argv) > 7:
    import os
    sys.path.insert(0, sys.argv[7])
    os.chdir(sys.argv[7])
    import tools.artfidelity_self as afs
    from tools.thin_strokes import REAL_ART, ROOT
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    rel, wmm, _g = REAL_ART[fx]
    ART = afs.art_ink_field(ROOT / 'testdata' / rel, wmm)
    KX, KY = json.load(open(f'{d}/matched-off-on.json'))[fx]['off']['K']
import os as _os
VSTACK = _os.environ.get("STACK") == "v"
LABELS = dict(x.split("=", 1) for x in _os.environ.get("LABELS", "").split(";") if "=" in x)
panels = []
for arm in arms:
    D = json.load(open(f'{d}/{fx}-{arm}.design.json'))
    st = D['stitches']
    ink = np.zeros((H, W), np.uint8)
    for p in polys:
        for ring in [p.exterior] + list(p.interiors):
            pass
        cv2.fillPoly(ink, [np.array([px(*c) for c in p.exterior.coords], np.int32)], 1)
        for h in p.interiors:
            cv2.fillPoly(ink, [np.array([px(*c) for c in h.coords], np.int32)], 0)
    thr = np.zeros((H, W), np.uint8)
    lines = np.zeros((H, W), np.uint8)
    tw = max(1, int(round(0.4 * S)))
    for r in D['runs']:
        if r.get('shape') not in sids:
            continue
        prev = None
        for i in range(r['i0'], r['i1'] + 1):
            s = st[i]
            if s.get('type') != 'stitch':
                prev = None
                continue
            p = px(s['x'] / 10.0, -s['y'] / 10.0)
            if prev is not None and prev != p:
                cv2.line(thr, prev, p, 1, tw)
                cv2.line(lines, prev, p, 1, 1)
            prev = p
    if ART is not None:
        gx, gy = np.meshgrid(np.arange(W) / S + x0, np.arange(H) / S + y0)
        cc = np.clip(np.round(gx * 10 + KX).astype(int), 0, ART.shape[1] - 1)
        rr = np.clip(np.round(gy * 10 + KY).astype(int), 0, ART.shape[0] - 1)
        poly_ink = ink > 0
        ink = (ART[rr, cc] >= 0.5).astype(np.uint8)
        ink[~cv2.dilate(poly_ink.astype(np.uint8), np.ones((int(S), int(S)), np.uint8)).astype(bool)] = 0
    inkb, thrb = ink > 0, thr > 0
    dist_out = cv2.distanceTransform((~inkb).astype(np.uint8), cv2.DIST_L2, 5) / S
    img = np.full((H, W, 3), 255, np.uint8)
    img[inkb] = (215, 215, 215)
    img[thrb & inkb] = (150, 190, 150)
    img[thrb & ~inkb] = (190, 220, 190)
    OUT = float(_os.environ.get('OUT_MM', '0.5'))
    img[thrb & (dist_out > OUT)] = (220, 120, 40)        # blue: > OUT mm outside the ink
    img[inkb & ~thrb] = (40, 40, 230)                     # red: ink with no thread
    img[lines > 0] = (60, 90, 60)
    for p in polys:
        cv2.polylines(img, [np.array([px(*c) for c in p.exterior.coords], np.int32)], True, (0, 0, 0), 1)
        for h in p.interiors:
            cv2.polylines(img, [np.array([px(*c) for c in h.coords], np.int32)], True, (0, 0, 0), 1)
    bare = (inkb & ~thrb).sum() / S / S
    deep = (thrb & (dist_out > OUT)).sum() / S / S
    cv2.putText(img, f'{LABELS.get(arm, arm)}: bare ink {bare:.2f} mm2, thread >{OUT:g} mm outside {deep:.2f} mm2',
                (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    print(arm, round(bare, 2), round(deep, 2))
    panels.append(img)
    panels.append(np.full((8, W, 3), 80, np.uint8) if VSTACK else np.full((H, 8, 3), 80, np.uint8))
cv2.imwrite(out, (np.vstack if VSTACK else np.hstack)(panels[:-1]))
