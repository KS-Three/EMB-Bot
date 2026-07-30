#!/usr/bin/env python
"""Study a professionally digitized stitch file and report its technique.

The engine's quality bar is "what a human digitizer ships", so this reads the
sew-order truth out of real production files: run structure, satin density and
width, underlay, fill row spacing and stagger, lock stitches, and — the reason
it was written — what professionals actually do at a satin corner.

Usage: .venv/Scripts/python tools/study_pro.py <file.dst|pes|jef> [...]
Renders land in debug_out/study/<stem>/: full view colored by run class
(satin red, fill blue, running green, lock purple, other gray) and 4x crops
around every detected corner event.
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import pyembroidery

ROOT = Path(__file__).resolve().parent.parent
OUT_BASE = ROOT / "debug_out" / "study"
MM = 0.1                      # stitch coordinates arrive in 0.1 mm units

CLASS_COLOR = {               # BGR for cv2
    "satin": (60, 60, 220),
    "fill": (200, 120, 40),
    "run": (60, 160, 60),
    "lock": (180, 60, 180),
    "other": (130, 130, 130),
}


def load_runs(path: Path):
    """-> (runs, n_trim, n_jump_moves). A run is needle-down stitches between
    lifts: any TRIM/JUMP/COLOR_CHANGE ends it. Each run carries its block id so
    color structure survives."""
    pat = pyembroidery.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    runs: list[dict] = []
    cur: list[tuple[float, float]] = []
    block = 0
    n_trim = n_jump = 0
    for x, y, c in pat.stitches:
        cmd = c & pyembroidery.COMMAND_MASK
        if cmd == pyembroidery.STITCH:
            cur.append((x * MM, y * MM))
            continue
        if cur:
            runs.append({"pts": cur, "block": block})
            cur = []
        if cmd == pyembroidery.TRIM:
            n_trim += 1
        elif cmd == pyembroidery.JUMP:
            n_jump += 1
        elif cmd == pyembroidery.COLOR_CHANGE:
            block += 1
    if cur:
        runs.append({"pts": cur, "block": block})
    return runs, n_trim, n_jump


def classify(pts: list[tuple[float, float]]) -> str:
    n = len(pts)
    if n < 3:
        return "other"
    seg = [(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(n - 1)]
    lens = sorted(math.hypot(*s) for s in seg)
    med = lens[len(lens) // 2]
    rev = 0
    for a, b in zip(seg, seg[1:]):
        la, lb = math.hypot(*a), math.hypot(*b)
        if la * lb > 1e-12 and (a[0] * b[0] + a[1] * b[1]) / (la * lb) < -0.2:
            rev += 1
    rev_frac = rev / max(len(seg) - 1, 1)
    if n <= 8 and med <= 0.8:
        return "lock"
    if rev_frac >= 0.7 and med >= 0.7:
        return "satin"
    if rev_frac <= 0.25 and med >= 0.8:
        return "run"
    if 0.02 <= rev_frac <= 0.45 and med >= 1.5:
        return "fill"
    return "other"


def satin_stats(pts):
    """Width, density and spine of a zigzag run."""
    widths = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    ra, rb = pts[0::2], pts[1::2]
    adv = [math.dist(a, b) for a, b in zip(ra, ra[1:])] + \
          [math.dist(a, b) for a, b in zip(rb, rb[1:])]
    adv = [d for d in adv if d > 1e-6]
    spine = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(pts, pts[1:])]
    w = sorted(widths)
    return {
        "width_med": w[len(w) // 2] if w else 0.0,
        "width_max": w[-1] if w else 0.0,
        "density_med": sorted(adv)[len(adv) // 2] if adv else 0.0,
        "spine": spine,
    }


def spine_corners(spine, width_mm):
    """Direction changes > 30 deg over about one column width of spine."""
    n = len(spine)
    if n < 5:
        return []
    seg = [math.dist(a, b) for a, b in zip(spine, spine[1:])]
    sp = sorted(seg)[len(seg) // 2] if seg else 0.0
    if sp <= 0:
        return []
    k = max(1, round(max(width_mm, 0.5) / sp))
    if n <= 2 * k:
        return []
    out = []
    for i in range(k, n - k):
        a, b, c = spine[i - k], spine[i], spine[i + k]
        d1 = math.atan2(b[1] - a[1], b[0] - a[0])
        d2 = math.atan2(c[1] - b[1], c[0] - b[0])
        turn = abs(math.degrees((d2 - d1 + math.pi) % (2 * math.pi) - math.pi))
        if turn >= 30.0:
            if not out or i - out[-1][1] > 2 * k:
                out.append((turn, i))
    return [(t, spine[i]) for t, i in out]


def fill_stats(pts):
    """Row spacing, stitch length and the stagger pattern of a tatami run."""
    seg = [(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    lens = [math.hypot(*s) for s in seg]
    dirs = [math.atan2(s[1], s[0]) % math.pi for s, L in zip(seg, lens) if L > 1.0]
    if not dirs:
        return None
    hist = Counter(round(math.degrees(d) / 5) * 5 for d in dirs)
    dom_deg = hist.most_common(1)[0][0]
    th = math.radians(dom_deg)
    ux, uy = math.cos(th), math.sin(th)
    # split into rows where the along-axis direction flips
    rows, cur, sign = [], [pts[0]], 0
    for p, q, L in zip(pts, pts[1:], lens):
        s = (q[0] - p[0]) * ux + (q[1] - p[1]) * uy
        this = 1 if s > 0 else -1 if s < 0 else 0
        if L > 1.0 and sign != 0 and this != 0 and this != sign:
            rows.append(cur)
            cur = [p]
        if L > 1.0 and this != 0:
            sign = this
        cur.append(q)
    rows.append(cur)
    if len(rows) < 3:
        return None
    # row spacing = advance of row centroid along the normal
    cn = [(-uy, ux)]
    nx, ny = cn[0]
    cents = [(sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)) for r in rows]
    gaps = [abs((b[0] - a[0]) * nx + (b[1] - a[1]) * ny) for a, b in zip(cents, cents[1:])]
    gaps = sorted(g for g in gaps if 0.05 < g < 3.0)
    stitch = sorted(L for L in lens if L > 1.0)
    # stagger: penetration phase along the row axis, row to row
    phases = []
    slen = stitch[len(stitch) // 2] if stitch else 4.0
    for r in rows[:24]:
        ts = sorted(p[0] * ux + p[1] * uy for p in r)
        if len(ts) > 2:
            phases.append(round((ts[len(ts) // 2] % slen) / slen, 2))
    offs = [round((b - a) % 1.0, 2) for a, b in zip(phases, phases[1:])]
    return {
        "angle_deg": dom_deg % 180,
        "rows": len(rows),
        "row_gap_med": gaps[len(gaps) // 2] if gaps else 0.0,
        "stitch_med": slen,
        "stagger_offsets": offs[:12],
    }


def tail_lock(pts: list[tuple[float, float]]) -> bool:
    """Does this run END in a lock — a cluster of tiny stitches?

    Locks live in the last few stitches of the run they secure, not in a
    separate run: the first version of this tool classified whole runs and
    reported "0 locks" on files that certainly have them.
    """
    if len(pts) < 4:
        return False
    tail = pts[-5:]
    tiny = sum(1 for a, b in zip(tail, tail[1:]) if math.dist(a, b) <= 0.8)
    return tiny >= 2


def render(runs, out_dir: Path, corner_pts):
    xs = [p[0] for r in runs for p in r["pts"]]
    ys = [p[1] for r in runs for p in r["pts"]]
    if not xs:
        return
    x0, y0 = min(xs), min(ys)
    S = 12.0
    w = int((max(xs) - x0) * S) + 40
    h = int((max(ys) - y0) * S) + 40
    img = np.full((h, w, 3), 245, np.uint8)

    def px(p):
        return (int((p[0] - x0) * S) + 20, int((p[1] - y0) * S) + 20)

    for r in runs:
        col = CLASS_COLOR[r["cls"]]
        arr = np.array([px(p) for p in r["pts"]], np.int32)
        cv2.polylines(img, [arr], False, col, 1, cv2.LINE_AA)
    for _t, p in corner_pts:
        cv2.circle(img, px(p), 10, (0, 200, 255), 2)
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "full.png"), img)
    for i, (_t, p) in enumerate(corner_pts[:8]):
        cx, cy = px(p)
        x1, y1 = max(cx - 90, 0), max(cy - 90, 0)
        crop = img[y1:y1 + 180, x1:x1 + 180]
        if crop.size:
            big = cv2.resize(crop, (crop.shape[1] * 4, crop.shape[0] * 4),
                             interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(str(out_dir / f"corner_{i}.png"), big)


def study(path: Path) -> None:
    runs, n_trim, n_jump = load_runs(path)
    total = sum(len(r["pts"]) for r in runs)
    for r in runs:
        r["cls"] = classify(r["pts"])
    by = Counter(r["cls"] for r in runs)
    st = [r for r in runs if r["cls"] == "satin"]

    print(f"\n=== {path.name} ===")
    print(f"stitches={total} runs={len(runs)} blocks={max((r['block'] for r in runs), default=0) + 1} "
          f"trims={n_trim} jump_moves={n_jump}  trims/1k={1000 * n_trim / max(total, 1):.1f}")
    print("run classes:", dict(by))

    widths, dens, corner_pts, ends_at_corner = [], [], [], 0
    for r in st:
        s = satin_stats(r["pts"])
        widths.append(s["width_med"])
        dens.append(s["density_med"])
        cs = spine_corners(s["spine"], s["width_med"])
        corner_pts.extend(cs)
    if st:
        widths.sort(), dens.sort()
        print(f"SATIN: runs={len(st)} width med={widths[len(widths) // 2]:.2f} "
              f"max={max(widths):.2f}mm density med={dens[len(dens) // 2]:.2f}mm")
        print(f"  corner events INSIDE a continuing run (fan risk): {len(corner_pts)}")
        # mitre census: satin run ends with another satin run starting nearby
        ends = [(r["pts"][-1], r) for r in st]
        starts = [(r["pts"][0], r) for r in st]
        mitre = 0
        for e, re_ in ends:
            for s0, rs in starts:
                if rs is re_:
                    continue
                if math.dist(e, s0) < 2.0:
                    mitre += 1
                    break
        print(f"  satin run ends with another satin starting <2mm away (split/mitre): {mitre}/{len(st)}")
    for r in runs:
        if r["cls"] == "fill":
            f = fill_stats(r["pts"])
            if f and f["rows"] >= 5:
                print(f"FILL: rows={f['rows']} angle={f['angle_deg']}deg "
                      f"row_gap={f['row_gap_med']:.2f}mm stitch={f['stitch_med']:.2f}mm "
                      f"stagger_offsets={f['stagger_offsets']}")
    locked_tails = sum(1 for r in runs if tail_lock(r["pts"]))
    print(f"LOCKS: {locked_tails}/{len(runs)} runs end in a tie-off cluster "
          f"({by.get('lock', 0)} standalone lock runs); trims={n_trim}")
    render(runs, OUT_BASE / path.stem.replace(" ", "_"), corner_pts)


def main() -> None:
    for arg in sys.argv[1:]:
        study(Path(arg))


if __name__ == "__main__":
    main()
