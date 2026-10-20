"""Signed distance of letter satin penetrations to the ARTWORK outline (mm,
+ inside), lane OFF vs ON, for the shapes the lane takes."""
import json
import sys

import numpy as np
from shapely import wkt
from shapely.geometry import Point

d = sys.argv[1]
for fx in sys.argv[2].split(','):
    L = json.load(open(f'{d}/{fx}-on.json'))['letters']
    polys = {k: wkt.loads(v['wkt']) for k, v in L.items()}
    for arm in sys.argv[3:] or ['off', 'on']:
        D = json.load(open(f'{d}/{fx}-{arm}.design.json'))
        st = D['stitches']
        vals = []
        kinds = {}
        for r in D['runs']:
            sid = r.get('shape')
            if sid not in polys:
                continue
            kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
            if r['kind'] != 'satin':
                continue
            P = polys[sid]
            B = P.boundary
            for i in range(r['i0'], r['i1'] + 1):
                s = st[i]
                if s.get('type') != 'stitch':
                    continue
                p = Point(s['x'] / 10, -s['y'] / 10)
                dd = B.distance(p)
                q = B.interpolate(B.project(p))
                # outward normal ~ from inside to boundary; use direction p->q or q->p
                vx, vy = (p.x - q.x, p.y - q.y) if not P.covers(p) else (q.x - p.x, q.y - p.y)
                if dd < 1e-6 or dd > 0.8:
                    continue
                ang = __import__('math').degrees(__import__('math').atan2(vy, vx)) % 360
                b = ['E', 'N', 'W', 'S'][int(((ang + 45) % 360) // 90)]
                vals.append((dd if P.covers(p) else -dd, b))
        for b in 'ENWS':
            vb = np.array([x for x, bb in vals if bb == b])
            if len(vb):
                print(f'{fx:10s} {arm:4s} outward {b}: n={len(vb):4d} median {np.median(vb):+.3f} p25 {np.percentile(vb,25):+.3f}')
        v = np.array([x for x, _ in vals])
        if not len(v):
            print(fx, arm, 'no satin', kinds)
            continue
        q = np.percentile(v, [5, 25, 50, 75, 95])
        print(f'{fx:10s} {arm:4s} n={len(v):5d} p5/25/50/75/95 = ' + ' '.join(f'{x:+.3f}' for x in q)
              + f'  out>0.35: {np.mean(v < -0.35):.3f}  out>0.5: {np.mean(v < -0.5):.3f}'
              + f'  in>0.1: {np.mean(v > 0.1):.3f}  kinds={kinds}', flush=True)
