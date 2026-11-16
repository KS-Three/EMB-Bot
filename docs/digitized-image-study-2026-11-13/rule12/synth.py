"""Synthetic check for the ring detector: 30x30 tatami ground, satin bars + an 8x8 tatami piece
on it (block 1). Cases: bare; a contrast ring in a third thread (block 2) of width w;
a ring in the piece's own colour sewn in the piece's block; a run-stitch line on the edge."""
import json, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import reader, ring

BARS = [(1.0, 4.0, 3, 3), (2.0, 10.0, 8, 3), (4.0, 8.0, 2, 16), (5.0, 8.0, 12, 16)]
SQ = (8.0, 8.0, 20, 4)    # tatami piece w, h, x, y


def tatami(x0, y0, w, h, step=3.5, row=0.2):
    pts, y, k = [], 0.0, 0
    while y <= h:
        off = (k % 3) * step / 3
        xs = [0.0] + [off + i * step for i in range(int(w / step) + 2) if 0 < off + i * step < w] + [w]
        if k % 2:
            xs = xs[::-1]
        pts += [(x0 + x, y0 + y, "S") for x in xs]
        y += row; k += 1
    return pts


def satin(w, h, x, y):
    pts, t, k = [], 0.0, 0
    while t <= h:
        pts.append((x + (w if k % 2 else 0.0), y + t, "S")); t += 0.2; k += 1
    return pts


def ring_satin(w, h, x, y, rw):
    """satin ring of width rw centred on the rectangle's edge, zigzag along the perimeter."""
    pts, a = [], rw / 2
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        L = abs(bx - ax) + abs(by - ay)
        dx, dy = (bx - ax) / L, (by - ay) / L
        nx, ny = dy, -dx       # outward normal for a clockwise (y-down) walk
        t, k = 0.0, 0
        while t <= L:
            s = a if k % 2 else -a
            pts.append((ax + dx * t + nx * s, ay + dy * t + ny * s, "S")); t += 0.2; k += 1
    return pts


def ring_run(w, h, x, y, st=2.0):
    pts = []
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        L = abs(bx - ax) + abs(by - ay)
        n = max(1, int(L / st))
        pts += [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n, "S") for i in range(n)]
    pts.append((x, y, "S"))
    return pts


def jump(pts, nxt):
    return [(nxt[0][0], nxt[0][1], "J")] + nxt


def build(case, rw=1.0):
    pts = tatami(0, 0, 30, 30)
    pts.append((0, 0, "C"))
    shapes = [("bar", b) for b in BARS] + [("sq", SQ)]
    for kind, (w, h, x, y) in shapes:
        body = satin(w, h, x, y) if kind == "bar" else tatami(x, y, w, h)
        pts += jump(pts, body)
        if case == "own":
            pts += jump(pts, ring_satin(w, h, x, y, rw))
    if case in ("contrast", "run"):
        pts.append((0, 0, "C"))
        for kind, (w, h, x, y) in shapes:
            pts += jump(pts, ring_satin(w, h, x, y, rw) if case == "contrast" else ring_run(w, h, x, y))
    return pts


out = {}
cases = [("bare", 1.0), ("contrast", 1.0), ("own", 1.0), ("run", 0.0)] + \
        [("contrast", w) for w in (0.2, 0.3, 0.5, 0.7, 1.5, 2.0)] + [("own", w) for w in (0.5, 0.7, 1.5)]
for case, rw in cases:
    rows, summ, ctx = reader.read(build(case, rw), case)
    ring.annotate(rows, ctx)
    name = f"{case}_{rw}"
    res = []
    for r in rows:
        res.append(dict(block=r["block"], area=r["area_mm2"], width=r["width_mm"],
                        rings=[(c["block"], c["cov"], c["far"]) for c in r["rings"]],
                        cands=[(c["block"], c["cov"], c["far"]) for c in r["ring_cands"]],
                        own_cov=r["own_satin_edge_cov"], own=r["own_satin_edge_ring"],
                        is_ring_of=r["is_ring_of"] is not None))
    out[name] = dict(grounds=summ["grounds"], rows=res)
    print(name, "grounds", [(g["block"], g["area_mm2"]) for g in summ["grounds"]])
    for x in res:
        print("   ", x)
json.dump(out, open(HERE / "synth.json", "w"), indent=1)
