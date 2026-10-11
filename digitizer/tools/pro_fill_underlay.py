#!/usr/bin/env python
"""What is sewn UNDER each fill of a stitch file, read off the bare stream.

A DST or PES carries no underlay tag, so this infers it from geometry and
sew order alone. Per fill it answers: is there a sparse tatami pass beneath
the top rows, at what angle to them, at what pitch and stitch length, with
what share of the top fill's thread, and was an edge run sewn first.

    .venv/bin/python tools/pro_fill_underlay.py FILE [FILE ...] [--min-fill MM]

Verdicts, one per fill:

  CROSS     a sparse pass under the fill, 60 degrees or more off the top rows
  DIAG      a sparse pass 30-60 degrees off (our `double_lattice`)
  PARALLEL  a sparse pass within 30 degrees of the top rows
  MIXEDANG  sparse rows under the fill with no one angle
  RUNONLY   20 mm or more of running stitch before the fill, no pass
  BARE      the top rows go straight onto fabric

How it reads a stream:

 1. ROWS are stretches of consistent heading; short stitches ride along. A
    row turn sewn as its own perpendicular stitch does not hide the row.
 2. A row is DENSE when its neighbour is under `SPARSE_MIN` away, SPARSE up
    to `SPARSE_MAX`.
 3. A FILL is a connected region of dense-row footprint (a 0.2 mm raster),
    not a colour block: two fills in one colour are judged apart.
 4. A sparse row is UNDER a fill only if dense rows are sewn over it LATER.
    Sparse work on top of a fill, or elsewhere in the block, is not counted.
 5. A PASS needs rows that alternate direction, so the sides of an edge run
    and a travel line do not pose as rows.
 6. The angle is taken from that fill's own under-rows.

## Validation (2026-10-05, `docs/underlay-audit-2026-10-05.md`)

154 fills sewn by `stage6_fill.stitch_shape` at a known underlay, written by
the `/export` writer to DST and PES and read back: 62 of 62 crossing passes
found, 23 of 23 diagonal, 0 false positives in 65 with no pass; DST and PES
agreed on every case. `tests/test_pro_fill_underlay.py` keeps the cases that
each broke an earlier version.

The version before this one (a session scratch file, never committed) found
18 of the 62 and read 80 of the 154 files as "not a fill". Three faults, all
of which made it UNDER-count: it needed a reversal over 120 degrees between
two consecutive stitches, which our tatami never has; it judged a whole
colour block; and its 0.9 mm sparse bar sat on the professional's
0.94-1.00 mm pitch and dropped about half his rows. `SPARSE_MIN` is 0.7 for
that reason; at 0.9 this version still has no false positive but misses
every pass sewn at 0.75-0.8 mm.

## Known limits

- The edge-run flag had 5 false positives in 74 on ground truth. Treat an
  edge-run count on professional files as an upper bound.
- An underlay row under 4 mm long, or of fewer than 2 stitches, is not seen,
  so narrow fills under-read.
- Area reads 5-9% high (the footprint is dilated).
- `min_fill_mm` is millimetres of DENSE THREAD, not area. The audit's
  "large fill" is the default 1,500.
"""
from __future__ import annotations

import math
import sys

import cv2
import numpy as np
import pystitch

RES = 0.2            # raster cell, mm
SPARSE_MIN = 0.7     # row pitch at or above this is a sparse row (see above)
SPARSE_MAX = 8.0
HEAD_TOL = 20.0      # degrees a stitch may leave its row's heading
MIN_FILL_MM = 1500.0
_BIG = 1.0e9


def passes_of(path) -> list[list[list[tuple[float, float]]]]:
    """The file as colour blocks of needle-down passes, in mm."""
    pattern = pystitch.read(str(path))
    out: list[list] = [[]]
    cur: list[tuple[float, float]] = []
    for x, y, c in pattern.stitches:
        cmd = c % 256
        if cmd == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
            continue
        if len(cur) >= 2:
            out[-1].append(cur)
        cur = []
        if cmd == pystitch.COLOR_CHANGE:
            out.append([])
    if len(cur) >= 2:
        out[-1].append(cur)
    return [b for b in out if b]


def _rows_heading(p: np.ndarray) -> list[tuple[int, int]]:
    d = np.diff(p, axis=0)
    length = np.hypot(d[:, 0], d[:, 1])
    rows = []
    start = 0
    acc = np.zeros(2)
    cos_tol = math.cos(math.radians(HEAD_TOL))
    for j in range(len(d)):
        if length[j] < 0.5:
            continue
        na = float(np.hypot(*acc))
        if na > 1e-9 and float(np.dot(d[j], acc)) / (length[j] * na) < cos_tol:
            rows.append((start, j))
            start = j
            acc = np.zeros(2)
        acc = acc + d[j]
    rows.append((start, len(p) - 1))
    return rows


def _axial_diff(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _axial_mean(axes, weights) -> float:
    a = np.radians(np.asarray(axes) * 2.0)
    w = np.asarray(weights)
    return (math.degrees(math.atan2(float((w * np.sin(a)).sum()),
                                    float((w * np.cos(a)).sum()))) / 2.0) % 180.0


def _records(passes) -> list[dict]:
    """Every row of the block, in sew order, classed DENSE / SPARSE / ISO /
    RUN by the pitch to its nearest like-headed neighbour."""
    recs = []
    for pi, ps in enumerate(passes):
        p = np.asarray(ps, dtype=float)
        if len(p) < 2:
            continue
        for a, b in _rows_heading(p):
            seg = p[a:b + 1]
            if len(seg) < 2:
                continue
            st = np.hypot(*np.diff(seg, axis=0).T)
            chord = seg[-1] - seg[0]
            clen = float(np.hypot(*chord))
            tot = float(st.sum())
            if tot <= 0:
                continue
            big = st[st >= 0.5]
            hd = math.degrees(math.atan2(chord[1], chord[0])) % 360 if clen > 0 else 0.0
            recs.append(dict(
                pi=pi, seg=seg, n=int(len(big)), clen=clen, tot=tot, hd=hd,
                ax=hd % 180.0, mid=seg.mean(axis=0),
                st=float(np.median(big)) if len(big) else 0.0,
                straight=(min(1.0, clen / max(1e-9, float(big.sum())))
                          if len(big) else 0.0)))
    for i, r in enumerate(recs):
        r["i"] = i
        r["multi"] = r["n"] >= 2 and r["clen"] >= 4.0 and r["straight"] >= 0.97

    def pair(i: int, step: int):
        r = recs[i]
        k = i
        seen = 0
        while seen < 3:
            k += step
            if k < 0 or k >= len(recs):
                return None
            q = recs[k]
            seen += 1
            if q["multi"] and _axial_diff(q["ax"], r["ax"]) <= HEAD_TOL:
                t = math.radians(r["ax"])
                nx, ny = -math.sin(t), math.cos(t)
                dm = r["mid"] - q["mid"]
                pitch = abs(dm[0] * nx + dm[1] * ny)
                along = abs(dm[0] * math.cos(t) + dm[1] * math.sin(t))
                if along > 0.75 * max(r["clen"], q["clen"]) + 2.0:
                    return None
                alt = abs(((r["hd"] - q["hd"] + 180) % 360) - 180) > 150
                return pitch, alt
        return None

    for i, r in enumerate(recs):
        r["pitch"] = float("nan")
        r["alt"] = False
        r["c"] = "RUN"
        if not r["multi"]:
            continue
        cand = [x for x in (pair(i, -1), pair(i, +1)) if x is not None]
        if not cand:
            r["c"] = "ISO"
            continue
        pit = min(x[0] for x in cand)
        r["pitch"] = pit
        r["alt"] = any(x[1] for x in cand)
        r["c"] = "DENSE" if pit < SPARSE_MIN else ("SPARSE" if pit <= SPARSE_MAX else "ISO")
    return recs


def analyse_block(passes, min_fill_mm: float = MIN_FILL_MM) -> list[tuple[str, dict]]:
    """One colour block -> [(verdict, detail)] per fill, largest first."""
    recs = _records(passes)
    dense = [r for r in recs if r["c"] == "DENSE"]
    if not dense:
        return []
    allp = np.vstack([r["seg"] for r in recs])
    x0, y0 = allp.min(axis=0) - 3.0
    x1, y1 = allp.max(axis=0) + 3.0
    width = int((x1 - x0) / RES) + 1
    height = int((y1 - y0) / RES) + 1
    org = np.array([x0, y0])

    def px(seg):
        return np.round((seg - org) / RES).astype(np.int32).reshape(-1, 1, 2)

    # `first[y, x]`: the sew index of the FIRST dense row to cover the cell.
    first = np.full((height, width), _BIG, dtype=np.float32)
    for r in reversed(dense):
        cv2.polylines(first, [px(r["seg"])], False, float(r["i"]), thickness=3)
    k5 = np.ones((5, 5), np.uint8)
    mask = (first < _BIG).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k5)
    first_f = cv2.erode(first, k5)
    first_f[mask == 0] = _BIG
    _nlab, lab = cv2.connectedComponents(mask, connectivity=8)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 3) * RES

    def sample(seg):
        out = []
        for a, b in zip(seg[:-1], seg[1:]):
            n = max(1, int(np.hypot(*(b - a)) / 0.5))
            for t in range(n + 1):
                out.append(a + (b - a) * (t / n))
        q = np.round((np.asarray(out) - org) / RES).astype(int)
        q[:, 0] = np.clip(q[:, 0], 0, width - 1)
        q[:, 1] = np.clip(q[:, 1], 0, height - 1)
        return q

    regs: dict[int, dict] = {}
    for r in dense:
        q = sample(r["seg"])
        ls = lab[q[:, 1], q[:, 0]]
        ls = ls[ls > 0]
        if not len(ls):
            continue
        label = int(np.bincount(ls).argmax())
        regs.setdefault(label, dict(dense=[], under=[], over=[], runs_pre=0.0,
                                    runs_pre_edge=0.0, runs_cov=0.0))["dense"].append(r)
    for g in regs.values():
        g["first_i"] = min(r["i"] for r in g["dense"])
    for r in recs:
        if r["c"] == "DENSE":
            continue
        q = sample(r["seg"])
        ls = lab[q[:, 1], q[:, 0]]
        fi = first_f[q[:, 1], q[:, 0]]
        inside = ls > 0
        if inside.sum() < 0.5 * len(q):
            continue
        label = int(np.bincount(ls[inside]).argmax())
        if label not in regs:
            continue
        g = regs[label]
        # the share of this row that dense thread is laid over AFTER it
        later = float(np.logical_and(fi > r["i"], inside).sum()) / len(q)
        if r["c"] == "SPARSE":
            if later >= 0.6:
                g["under"].append(r)
            elif later <= 0.2:
                g["over"].append(r)
        else:
            if later >= 0.6:
                g["runs_cov"] += r["tot"]
            if r["i"] < g["first_i"]:
                g["runs_pre"] += r["tot"]
                dd = dist[q[:, 1], q[:, 0]]
                g["runs_pre_edge"] += r["tot"] * float((dd[inside] <= 2.5).mean())

    out = []
    for label, g in regs.items():
        dn = g["dense"]
        dense_mm = sum(r["tot"] for r in dn)
        if dense_mm < min_fill_mm:
            continue
        rm = (lab == label).astype(np.uint8)
        area = float(rm.sum()) * RES * RES
        cnts, _ = cv2.findContours(rm, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        perim = sum(cv2.arcLength(c, True) for c in cnts) * RES
        dax = _axial_mean([r["ax"] for r in dn], [r["tot"] for r in dn])
        off = sum(r["tot"] for r in dn if _axial_diff(r["ax"], dax) > 30) / dense_mm
        d = dict(
            area=round(area), dense_mm=round(dense_mm), perim=round(perim),
            dense_pitch=round(float(np.median([r["pitch"] for r in dn])), 2),
            dense_stitch=round(float(np.median([r["st"] for r in dn])), 2),
            dense_rowlen=round(float(np.median([r["clen"] for r in dn])), 1),
            dense_ax=round(dax, 1), top_offaxis=round(off, 2),
            runs_pre=round(g["runs_pre"]), runs_pre_edge=round(g["runs_pre_edge"]),
            runs_cov=round(g["runs_cov"]),
            over_rows=len(g["over"]), over_mm=round(sum(r["tot"] for r in g["over"])))
        d["edge"] = bool(perim > 0 and g["runs_pre_edge"] >= 0.5 * perim)
        under = g["under"]
        under_mm = sum(r["tot"] for r in under)
        d["n_under"] = len(under)
        d["under_mm"] = round(under_mm)
        d["share"] = round(100.0 * under_mm / dense_mm, 1)
        interior = "NONE"
        if len(under) >= 4 and under_mm >= 0.03 * dense_mm:
            alt_frac = sum(1 for r in under if r["alt"]) / len(under)
            off_top = np.array([_axial_diff(r["ax"], dax) for r in under])
            w = np.array([r["tot"] for r in under])
            pitches = [r["pitch"] for r in under]
            d["alt"] = round(alt_frac, 2)
            d["angle_vs_top"] = round(float(np.median(off_top)), 1)
            d["sparse_pitch"] = round(float(np.median(pitches)), 2)
            d["sparse_pitch_p10"] = round(float(np.percentile(pitches, 10)), 2)
            d["sparse_pitch_p90"] = round(float(np.percentile(pitches, 90)), 2)
            d["sparse_stitch"] = round(float(np.median([r["st"] for r in under])), 2)
            um = np.zeros((height, width), np.uint8)
            rad = max(3, int(round(1.0 * d["sparse_pitch"] / RES)))
            for r in under:
                cv2.polylines(um, [px(r["seg"])], False, 1, thickness=2 * rad + 1)
            # the share of the fill within one row pitch of the pass
            d["cov"] = round(float(np.logical_and(um > 0, rm > 0).sum())
                             / max(1.0, float(rm.sum())), 2)
            if alt_frac >= 0.6:
                cross = float(w[off_top >= 60].sum() / w.sum())
                parallel = float(w[off_top < 30].sum() / w.sum())
                diag = 1.0 - cross - parallel
                interior = ("CROSS" if cross >= 0.6 else
                            "DIAG" if diag >= 0.6 else
                            "PARALLEL" if parallel >= 0.6 else "MIXEDANG")
        d["interior"] = interior
        verdict = interior if interior != "NONE" else (
            "RUNONLY" if g["runs_pre"] >= 20 else "BARE")
        out.append((verdict, d))
    out.sort(key=lambda t: -t[1]["area"])
    return out


def classify_file(path, min_fill_mm: float = MIN_FILL_MM) -> list[tuple[str, dict]]:
    """Every fill of the file with at least `min_fill_mm` of dense thread:
    [(verdict, detail)], `detail["block"]` the colour block it is in."""
    out = []
    for bi, passes in enumerate(passes_of(path)):
        for verdict, d in analyse_block(passes, min_fill_mm):
            d["block"] = bi
            out.append((verdict, d))
    return out


def main(argv: list[str]) -> None:
    min_fill = MIN_FILL_MM
    paths = []
    it = iter(argv)
    for a in it:
        if a == "--min-fill":
            min_fill = float(next(it))
        else:
            paths.append(a)
    if not paths:
        raise SystemExit(__doc__)
    print(f"{'file':34s} blk verdict   area  top_pitch  pass: pitch stitch angle share%  edge")
    for path in paths:
        name = path.replace("\\", "/").rsplit("/", 1)[-1][:34]
        fills = classify_file(path, min_fill)
        if not fills:
            print(f"{name:34s}   - no fill of {min_fill:.0f} mm dense thread")
        for verdict, d in fills:
            print(f"{name:34s} {d['block']:3d} {verdict:8s} {d['area']:5d} "
                  f"{d['dense_pitch']:9.2f}        "
                  f"{str(d.get('sparse_pitch', '-')):>5s} {str(d.get('sparse_stitch', '-')):>6s} "
                  f"{str(d.get('angle_vs_top', '-')):>5s} {d['share']:6.1f}  "
                  f"{'yes' if d['edge'] else 'no'}")


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    main(sys.argv[1:])
