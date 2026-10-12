"""Per-letter table for every lettering shape with a fanned (slanted)
terminal, from `run_arms.py`'s output.

Readings per shape, three arms (off = shipped, before, after):
  unsewn   #828's matched reading (`matched.py`, one physical alignment, the
           shipped design's best 0.1 mm fit), mm2 of ink attributed to the
           shape, in components the instrument counts
  bare     same alignment, every ink pixel with no thread nearest the shape
  trace    ink of the shape's own TRACED polygon with no thread within the
           0.4 mm the instrument draws (no raster, no registration)
  st       stitch penetrations in the shape's runs

usage (cwd digitizer/): python fan_table.py OUTDIR fixture[,fixture] > table.md
"""
import json
import os
import sys

import cv2
import numpy as np
from shapely import wkt

sys.path.insert(0, os.getcwd())
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "columns-lost-frac-2026-10-11"))
import matched  # noqa: E402  (#828's instrument)
from tools.thin_strokes import REAL_ART, ROOT  # noqa: E402

ARMS = ("off", "before", "after")


def trace_bare(design, sid, poly, S=20.0):
    x0, y0, x1, y1 = poly.bounds
    x0, y0 = x0 - 1, y0 - 1
    W, H = int((x1 + 1 - x0) * S), int((y1 + 1 - y0) * S)
    px = lambda p: (int(round((p[0] - x0) * S)), int(round((p[1] - y0) * S)))
    ink = np.zeros((H, W), np.uint8)
    cv2.fillPoly(ink, [np.array([px(c) for c in poly.exterior.coords], np.int32)], 1)
    for h in poly.interiors:
        cv2.fillPoly(ink, [np.array([px(c) for c in h.coords], np.int32)], 0)
    thr = np.zeros((H, W), np.uint8)
    st = design["stitches"]
    tw = max(1, int(round(0.4 * S)))
    for r in design["runs"]:
        if r.get("shape") != sid:
            continue
        prev = None
        for i in range(r["i0"], r["i1"] + 1):
            s = st[i]
            if s.get("type") != "stitch":
                prev = None
                continue
            p = px((s["x"] / 10.0, -s["y"] / 10.0))
            if prev is not None:
                cv2.line(thr, prev, p, 1, tw)
            prev = p
    return float(((ink > 0) & (thr == 0)).sum()) / S / S


def n_stitches(design, sid):
    st = design["stitches"]
    return sum(1 for r in design["runs"] if r.get("shape") == sid
               for i in range(r["i0"], r["i1"] + 1) if st[i].get("type") == "stitch")


def main():
    d = sys.argv[1]
    print("| logo | shape | fanned ends before / after | pivots moved | unsewn off / before / after | "
          "bare off / before / after | trace-bare off / before / after | stitches off / before / after |")
    print("|---|---|---|---|---|---|---|---|")
    totals = {}
    for fx in sys.argv[2].split(","):
        rel, width, _g = REAL_ART[fx]
        image = ROOT / "testdata" / rel
        fans = json.load(open(f"{d}/{fx}-fans.json"))
        letters = json.load(open(f"{d}/{fx}-on.json"))["letters"]
        D = {a: json.load(open(f"{d}/{fx}-{a}.design.json")) for a in ARMS}
        ra, pa, _ = matched.analyse(image, D["off"], width, None, list(letters))
        per = {"off": pa}
        whole = {"off": ra}
        for a in ("before", "after"):
            r, p, _ = matched.analyse(image, D[a], width, ra["K"], list(letters))
            per[a], whole[a] = p, r
        totals[fx] = {a: (whole[a]["lost_frac"], whole[a]["unsewn_mm2"], whole[a]["letters_unsewn_mm2"])
                      for a in ARMS}
        sids = sorted(set(fans.get("before", {})) | set(fans.get("after", {})))
        for sid in sids:
            fb = fans.get("before", {}).get(sid, [])
            fa = fans.get("after", {}).get(sid, [])
            if not fb and not fa:
                continue
            moved = sum(1 for e in fa if e["pivot_moved"])
            poly = wkt.loads(letters[sid]["wkt"]) if sid in letters else None
            g = lambda a, k: per[a].get(sid, {}).get(k, 0.0)
            tb = [trace_bare(D[a], sid, poly) if poly is not None else float("nan") for a in ARMS]
            ns = [n_stitches(D[a], sid) for a in ARMS]
            print(f"| {fx} | {sid} | {len(fb)} / {len(fa)} | {moved} | "
                  f"{g('off','unsewn'):.1f} / {g('before','unsewn'):.1f} / {g('after','unsewn'):.1f} | "
                  f"{g('off','bare'):.2f} / {g('before','bare'):.2f} / {g('after','bare'):.2f} | "
                  f"{tb[0]:.2f} / {tb[1]:.2f} / {tb[2]:.2f} | {ns[0]} / {ns[1]} / {ns[2]} |", flush=True)
    print()
    print("| logo | lost_frac off / before / after (matched) | unsewn mm2 | letters' unsewn mm2 |")
    print("|---|---|---|---|")
    for fx, t in totals.items():
        print(f"| {fx} | " + " / ".join(f"{t[a][0]:.4f}" for a in ARMS) + " | "
              + " / ".join(f"{t[a][1]:.1f}" for a in ARMS) + " | "
              + " / ".join(f"{t[a][2]:.1f}" for a in ARMS) + " |")


if __name__ == "__main__":
    main()
