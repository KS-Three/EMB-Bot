import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import reader

BARS = [(1.0, 4.0, 3, 3), (2.0, 10.0, 8, 3), (4.0, 8.0, 2, 10), (5.0, 8.0, 12, 9)]  # w, h, x, y (mm)


def tatami(size, holes, tongue):
    pts, y, row, step = [], 0.0, 0, 3.5
    while y <= size:
        off = (row % 3) * step / 3
        grid = [off + k * step for k in range(int(size / step) + 2) if 0 < off + k * step < size]
        cut = sorted((hx + tongue, hx + hw - tongue) for hw, hh, hx, hy in holes
                     if hy + tongue <= y <= hy + hh - tongue)
        spans, a = [], 0.0
        for c0, c1 in cut:
            spans.append((a, c0)); a = c1
        spans.append((a, size))
        rowpts = []
        for s0, s1 in spans:
            xs = [s0] + [g for g in grid if s0 < g < s1] + [s1]
            rowpts.append(xs)
        if row % 2:
            rowpts = [xs[::-1] for xs in rowpts[::-1]]
        for i, xs in enumerate(rowpts):
            for j, x in enumerate(xs):
                pts.append((x, y, "J" if (i > 0 and j == 0) else "S"))
                if i > 0 and j == 0:
                    pts.append((x, y, "S"))
        y += 0.2
        row += 1
    return pts


def satin(w, h, x, y):
    pts, t, k = [], 0.0, 0
    while t <= h:
        pts.append((x + (w if k % 2 else 0.0), y + t, "S"))
        t += 0.2
        k += 1
    return pts


out = {}
for case, holes, tg in (("solid", [], 0.25), ("knockout_tongue0.25", BARS, 0.25), ("knockout_gap0.3", BARS, -0.3)):
    pts = tatami(20.0, holes, tg)
    for b in BARS:
        pts += [(0, 0, "C")] if b is BARS[0] else [(pts[-1][0], pts[-1][1], "J")]
        pts += satin(*b)
    rows, summ = reader.read(pts, case)
    out[case] = dict(rows=rows, summary=summ)
    print(case, json.dumps(summ))
    for r in rows:
        print("  ", {k: r[k] for k in ("area_mm2", "width_mm", "under_cover", "core_under_cover", "band_bare", "band_bare_outside", "knocked_out")})
json.dump(out, open(Path(__file__).parent / "synth.json", "w"), indent=1)
