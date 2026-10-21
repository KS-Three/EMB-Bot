"""trim_classes: every trim in a machine file, sorted by what its hop lies on.

    python -m tools.trim_classes FILE [FILE ...] [--rows]

Reads any file `pystitch` reads; read the DST, never the PES, when counting
a pro's trims -- the PES reader reports a TRIM at every jump (Fremont's
patch: 53 as PES, 20 as DST). Both sides are read the same way, so our
`ours.dst` (from `tools/pro_pair.py`) and the pro's file are comparable.

Every TRIM record (a run of them counts once) is one hop, from the last
needle penetration before it to the first after it. Its straight line is
sampled every 0.1 mm against a raster (10 px/mm) of every needle-down
segment in the file, drawn 0.4 mm wide (`COVERAGE_THREAD_W_MM`) and
stamped with its record index, and the hop lands in one class:

  colour        a colour change between the two penetrations.
  under_later   >= 90% of the line lies under thread sewn AFTER the hop:
                travel there would have been hidden.
  on_work       >= 90% under thread, but not later thread: travel there
                would lie on top of finished work.
  bare_letters  on fabric, between two separate letter-sized pieces (a
                connected piece of the final footprint, max side <= 20 mm).
  bare_other    on fabric, anything else.

Measured with it 2026-10-21 over the ten jobs that have both artwork and
the pro's DST (`docs/trim-economy-2026-10-21.md`): the pro cut 9
`under_later` hops to our 43. It reads the STRAIGHT line only; a hop a
bent route could bury reads `on_work` or `bare_*` here.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter

PPM = 10.0
THREAD_MM = 0.4
COVER = 0.9
LETTER_MAX_MM = 20.0
CLASSES = ("colour", "under_later", "on_work", "bare_letters", "bare_other")


def classify(path) -> list[dict]:
    """One row per trim: class, hop length (mm), the two coverage fractions."""
    import cv2
    import numpy as np
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    m = pystitch.COMMAND_MASK
    st = [(x / 10.0, y / 10.0, c & m) for x, y, c in pat.stitches]
    if not st:
        return []
    x0 = min(p[0] for p in st) - 3
    y0 = min(p[1] for p in st) - 3
    w = int((max(p[0] for p in st) - x0 + 3) * PPM) + 1
    h = int((max(p[1] for p in st) - y0 + 3) * PPM) + 1
    hi = np.full((h, w), -1, np.int32)
    lw = max(1, int(round(THREAD_MM * PPM)))

    def px(x, y):
        return int(round((x - x0) * PPM)), int(round((y - y0) * PPM))

    prev = None
    prev_cmd = None
    for i, (x, y, c) in enumerate(st):
        if c == pystitch.STITCH and prev is not None and prev_cmd == pystitch.STITCH:
            (ax, ay), (bx, by) = px(*prev), px(x, y)
            xl, xh = max(0, min(ax, bx) - lw), max(ax, bx) + lw + 1
            yl, yh = max(0, min(ay, by) - lw), max(ay, by) + lw + 1
            sub = np.zeros((yh - yl, xh - xl), np.uint8)
            cv2.line(sub, (ax - xl, ay - yl), (bx - xl, by - yl), 1, lw)
            win = hi[yl:yh, xl:xh]
            win[sub[:win.shape[0], :win.shape[1]].astype(bool)] = i
        if c in (pystitch.STITCH, pystitch.JUMP):
            prev = (x, y)
        prev_cmd = c
    k = int(0.2 * PPM) | 1
    pieces = cv2.morphologyEx((hi >= 0).astype(np.uint8), cv2.MORPH_CLOSE,
                              np.ones((k, k), np.uint8))
    _n, lab, stats, _c = cv2.connectedComponentsWithStats(pieces, 8)

    def piece_at(p):
        qx, qy = px(*p)
        v = lab[max(0, qy - 3):qy + 4, max(0, qx - 3):qx + 4]
        v = v[v > 0]
        return int(np.bincount(v).argmax()) if v.size else 0

    def letter_sized(j):
        return j > 0 and max(stats[j, 2], stats[j, 3]) / PPM <= LETTER_MAX_MM

    out: list[dict] = []
    last = None
    i = 0
    while i < len(st):
        x, y, c = st[i]
        if c == pystitch.STITCH:
            last = (x, y)
        if c == pystitch.TRIM and last is not None:
            j, colour = i, False
            while j < len(st) and st[j][2] not in (pystitch.STITCH, pystitch.END):
                colour |= st[j][2] == pystitch.COLOR_CHANGE
                j += 1
            if j >= len(st) or st[j][2] != pystitch.STITCH:
                break
            a, b = last, st[j][:2]
            length = math.dist(a, b)
            n = max(2, int(length / 0.1))
            later = anywhere = 0
            for s in range(n + 1):
                t = s / n
                qx, qy = px(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                later += hi[qy, qx] > i
                anywhere += hi[qy, qx] >= 0
            later /= n + 1
            anywhere /= n + 1
            pa, pb = piece_at(a), piece_at(b)
            if colour:
                cls = "colour"
            elif later >= COVER:
                cls = "under_later"
            elif anywhere >= COVER:
                cls = "on_work"
            elif pa != pb and letter_sized(pa) and letter_sized(pb):
                cls = "bare_letters"
            else:
                cls = "bare_other"
            out.append({"cls": cls, "len_mm": round(length, 2),
                        "f_later": round(later, 2), "f_covered": round(anywhere, 2)})
            i = j
            continue
        i += 1
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.trim_classes",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("files", nargs="+", help="machine files (DST for the pro)")
    ap.add_argument("--rows", action="store_true", help="print every trim, not just the counts")
    args = ap.parse_args(argv)
    for f in args.files:
        rows = classify(f)
        c = Counter(r["cls"] for r in rows)
        print(json.dumps({"file": f, "trims": len(rows), **{k: c[k] for k in CLASSES}}))
        if args.rows:
            for r in rows:
                print("  ", json.dumps(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
