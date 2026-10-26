"""script_census: how a script / italic word is built, read off a machine file --
one reader for the professional's DST and ours (L7, 2026-10-24).

WHAT IT READS. Every needle-down stitch (JUMP / TRIM / COLOR_CHANGE end a
run). PIECES (satin columns) and their crosses come from
`tools.letter_pieces.read`, unchanged. Its letters are the connected
components of the cross coverage; here a GROUP is the connected component of
ALL needle-down stitches (0.4 mm thread at PX px/mm, closed by CLOSE_MM), so
a fill, a run or a column all land in the group they sew. A joined script
word ("ires") is one group; a T's crossbar, stem and an i's dot are three.

THE STROKE, NOT THE STITCH. The question is whether a column's crosses lie
square to the STROKE or lean with the script's slant. A column's own spine
cannot answer it: a fill's rows advance at right angles to themselves, so
against its own spine every fill reads square. The stroke direction comes
from the file's OWN coverage instead -- the structure tensor of the group's
mask (gradient at SIGMA_MM, window half the group's median stroke width),
whose principal direction at a cross's midpoint is the stroke's NORMAL.
Points where the tensor is not coherent (COHERENT_MIN: a junction, a
terminal, a dot) carry no reading and are left out, counted.

PER CROSS: `dev` = the cross's direction minus the stroke normal, folded to
(-90, 90] (0 = square to the stroke). `square` = |dev| <= SQUARE_DEG.
`slant` = the stroke's own lean from vertical (y down: + leans right, an
italic stem). On SLANTED stroke (|slant| between 10 and 50 deg) the cross
against HORIZONTAL (the line of text) says whether the crosses stay square
to the stroke (cross_vs_text = -slant, dev 0) or flat to the text line
(cross_vs_text 0, dev = slant).

PER GROUP: stroke width (twice the distance transform's median on the mask's
ridge), stitches, stitches under 1 mm, needle-down runs that touch it
(entries), trims inside its box, crosses, square share (length-weighted),
median |dev|, columns (pieces that are not patches), patches, the cuts
between its columns by `letter_pieces` kind, and each cut's OVERLAP: how far
the next column runs (spine mm) inside thread the group already sewed.
Entry and exit: the group's first and last needle-down stitch.

    python -m tools.script_census FILE.dst[@BLOCK] [FILE.dst[@BLOCK] ...] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools import letter_pieces as LP  # noqa: E402

PX = 10.0               # px / mm
THREAD_MM = 0.4
CLOSE_MM = 0.6
MIN_GROUP_MM2 = 4.0
SIGMA_MM = 0.3          # gradient scale
COHERENT_MIN = 0.6
SQUARE_DEG = 20.0
SHORT_MM = 1.0


def stitches_of(path: Path, block: int | None = None) -> dict:
    """-> {segs: [(a, b, run)], trims: [(x, y)], runs: n}. mm, y down; only
    colour block `block` (0 = before the first colour change) when given."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    segs, trims, run, last, blk = [], [], 0, None, 0
    for x, y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        p = (x / 10.0, y / 10.0)
        if c == pystitch.STITCH:
            if last is not None and block in (None, blk):
                segs.append((last, p, run))
            last = p
        elif c in (pystitch.JUMP, pystitch.TRIM, pystitch.COLOR_CHANGE, pystitch.STOP):
            if c == pystitch.TRIM and block in (None, blk):
                trims.append(p)
            if c == pystitch.COLOR_CHANGE:
                blk += 1
            if last is not None:
                run += 1
            last = None
        elif c == pystitch.END:
            break
    return {"segs": segs, "trims": trims, "runs": run + 1}


def _frame(segs):
    xy = np.array([[*a, *b] for a, b, _r in segs])
    x0, y0 = xy[:, [0, 2]].min() - 2, xy[:, [1, 3]].min() - 2
    x1, y1 = xy[:, [0, 2]].max() + 2, xy[:, [1, 3]].max() + 2
    return x0, y0, int((x1 - x0) * PX) + 1, int((y1 - y0) * PX) + 1


def _px(p, x0, y0):
    return int(round((p[0] - x0) * PX)), int(round((p[1] - y0) * PX))


def groups_of(st: dict):
    """-> (label image, frame, {k: area_mm2})."""
    import cv2
    x0, y0, W, H = _frame(st["segs"])
    img = np.zeros((H, W), np.uint8)
    th = max(1, int(round(THREAD_MM * PX)))
    for a, b, _r in st["segs"]:
        cv2.line(img, _px(a, x0, y0), _px(b, x0, y0), 255, th)
    k = max(3, int(round(CLOSE_MM * PX)) | 1)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, stats, _c = cv2.connectedComponentsWithStats(img, 8)
    area = {i: stats[i, cv2.CC_STAT_AREA] / PX ** 2 for i in range(1, n)}
    return lab, (x0, y0, W, H), area


def stroke_width(mask: np.ndarray) -> float:
    """Twice the distance transform's median on its ridge (local maxima)."""
    import cv2
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    dil = cv2.dilate(dt, np.ones((3, 3), np.uint8))
    ridge = (dt > 1.0) & (dt >= dil - 1e-6)
    if not ridge.any():
        return 0.0
    return float(2.0 * np.median(dt[ridge]) / PX)


def normal_field(mask: np.ndarray, width_mm: float):
    """-> (normal angle deg [0,180), coherence) per pixel, structure tensor."""
    import cv2
    m = mask.astype(np.float32) / 255.0
    s = SIGMA_MM * PX
    g = cv2.GaussianBlur(m, (0, 0), s)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    w = max(0.5 * width_mm * PX, 2.0)
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), w)
    jyy = cv2.GaussianBlur(gy * gy, (0, 0), w)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), w)
    ang = (0.5 * np.degrees(np.arctan2(2 * jxy, jxx - jyy))) % 180.0
    tr = jxx + jyy
    coh = np.where(tr > 1e-9, np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / np.maximum(tr, 1e-9), 0.0)
    return ang, coh


def _fold(a: float) -> float:
    d = a % 180.0
    return d - 180.0 if d > 90.0 else d


def census(path: Path, block: int | None = None) -> dict:
    import cv2
    path = Path(path)
    st = stitches_of(path, block)
    lab, (x0, y0, W, H), area = groups_of(st)
    keep = {k for k, a in area.items() if a >= MIN_GROUP_MM2}
    ext = np.array([p for a, b, _r in st["segs"] for p in (a, b)])
    dx0, dy0 = ext.min(0)
    dx1, dy1 = ext.max(0)

    def label_at(p):
        x, y = _px(p, x0, y0)
        return int(lab[min(max(y, 0), H - 1), min(max(x, 0), W - 1)])

    G: dict[int, dict] = {}
    for k in sorted(keep):
        ys, xs = np.nonzero(lab == k)
        bx = [xs.min() / PX + x0, ys.min() / PX + y0, xs.max() / PX + x0, ys.max() / PX + y0]
        G[k] = {"bbox": [round(float(v), 2) for v in bx],
                "rel": [round(float(v), 3) for v in ((bx[0] - dx0) / (dx1 - dx0), (bx[1] - dy0) / (dy1 - dy0),
                                                     (bx[2] - dx0) / (dx1 - dx0), (bx[3] - dy0) / (dy1 - dy0))],
                "area_mm2": round(area[k], 1), "stitches": 0, "short": 0, "runs": set(),
                "first": None, "last": None, "trims": 0}
    for a, b, r in st["segs"]:
        k = label_at(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        if k not in G:
            continue
        g = G[k]
        L = math.dist(a, b)
        g["stitches"] += 1
        g["short"] += int(L < SHORT_MM)
        g["runs"].add(r)
        g["first"] = g["first"] or [round(a[0], 2), round(a[1], 2)]
        g["last"] = [round(b[0], 2), round(b[1], 2)]
    for t in st["trims"]:
        for g in G.values():
            bx = g["bbox"]
            if bx[0] - 0.5 <= t[0] <= bx[2] + 0.5 and bx[1] - 0.5 <= t[1] <= bx[3] + 0.5:
                g["trims"] += 1
                break

    fields = {}
    for k in G:
        mask = np.where(lab == k, 255, 0).astype(np.uint8)
        w = stroke_width(mask)
        G[k]["stroke_mm"] = round(w, 2)
        fields[k] = normal_field(mask, w)

    lp = LP.read(path)
    for g in G.values():
        g.update(crosses=0, read=0, sq_len=0.0, len=0.0, devs=[], slanted=[], columns=0, patches=0,
                 cuts={}, overlaps=[])
    for L in lp["letters"]:
        cross_of = L["crosses"]
        pieces = L["pieces"]
        by_piece: dict[int, list] = {}
        for (a, b), pi in zip(cross_of, L["piece_of_cross"]):
            by_piece.setdefault(pi, []).append((a, b))
        # group of each piece: majority vote of its cross midpoints
        pg = {}
        if block is not None:
            by_piece = {pi: cs for pi, cs in by_piece.items() if pieces[pi]["block"] == block}
        for pi, cs in by_piece.items():
            votes = {}
            for a, b in cs:
                k = label_at(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
                votes[k] = votes.get(k, 0) + 1
            pg[pi] = max(votes, key=votes.get)
        for pi, cs in by_piece.items():
            k = pg[pi]
            if k not in G:
                continue
            g = G[k]
            if pieces[pi]["role"] == "patch":
                g["patches"] += 1
            else:
                g["columns"] += 1
            ang, coh = fields[k]
            for a, b in cs:
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                x, y = _px(m, x0, y0)
                x, y = min(max(x, 0), W - 1), min(max(y, 0), H - 1)
                L_ = math.dist(a, b)
                g["crosses"] += 1
                if coh[y, x] < COHERENT_MIN:
                    continue
                d = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
                n = float(ang[y, x])
                dev = _fold(d - n)
                g["read"] += 1
                g["len"] += L_
                g["sq_len"] += L_ * (abs(dev) <= SQUARE_DEG)
                g["devs"].append(abs(dev))
                # stroke direction = normal + 90; slant from vertical (y down, + leans right)
                sdir = (n + 90.0) % 180.0
                slant = _fold(sdir - 90.0)    # (1, -1) runs up-right: 135 deg -> +45
                if 10.0 <= abs(slant) <= 50.0:
                    g["slanted"].append((slant, _fold(d), dev))
        # cuts and overlaps, in sewing order inside each group
        order = sorted(by_piece, key=lambda pi: pieces[pi]["order"])
        sewn: dict[int, np.ndarray] = {}
        for pi in order:
            k = pg[pi]
            if k not in G:
                continue
            if k in sewn:
                prev = [q for q in order if pg[q] == k and pieces[q]["order"] < pieces[pi]["order"]]
                if prev:
                    kind = next((c["kind"] for c in L["cuts"] if c["before"] == pieces[pi]["order"]), "restart")
                    G[k]["cuts"][kind] = G[k]["cuts"].get(kind, 0) + 1
                    cov = sewn[k]
                    ov = 0.0
                    cs = by_piece[pi]
                    mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in cs]
                    for m0, m1 in zip(mids, mids[1:]):
                        x, y = _px(m1, x0, y0)
                        if 0 <= x < W and 0 <= y < H and cov[y, x]:
                            ov += math.dist(m0, m1)
                    G[k]["overlaps"].append(round(ov, 2))
            cov = sewn.setdefault(k, np.zeros((H, W), np.uint8))
            th = max(1, int(round(THREAD_MM * PX)))
            for a, b in by_piece[pi]:
                cv2.line(cov, _px(a, x0, y0), _px(b, x0, y0), 1, th)

    out = []
    for k, g in G.items():
        sl = g.pop("slanted")
        devs = g.pop("devs")
        row = {**g, "runs": len(g["runs"]),
               "square_share": round(g["sq_len"] / g["len"], 3) if g["len"] else None,
               "dev_med": round(float(np.median(devs)), 1) if devs else None,
               "dev_p90": round(float(np.percentile(devs, 90)), 1) if devs else None,
               "slanted_n": len(sl),
               "slant_med": round(float(np.median([s[0] for s in sl])), 1) if sl else None,
               "cross_vs_text_med": round(float(np.median([s[1] for s in sl])), 1) if sl else None,
               "slanted_dev_med": round(float(np.median([s[2] for s in sl])), 1) if sl else None}
        row.pop("sq_len")
        row.pop("len")
        row["overlap_med"] = round(float(np.median(row["overlaps"])), 2) if row["overlaps"] else None
        out.append(row)
    out.sort(key=lambda r: (r["bbox"][0]))
    return {"file": path.name, "block": block, "stitches": len(st["segs"]), "trims": len(st["trims"]),
            "groups": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+", help="FILE.dst, or FILE.dst@N for colour block N only")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    res = []
    for f in a.files:
        name, _, blk = f.rpartition("@") if "@" in f else (f, "", "")
        res.append(census(Path(name), int(blk) if blk else None))
    for r in res:
        print(f"== {r['file']} block {r['block']}: {r['stitches']} stitches, {r['trims']} trims")
        for g in r["groups"]:
            print(json.dumps({k: v for k, v in g.items() if k not in ("overlaps",)}))
    if a.json:
        a.json.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
