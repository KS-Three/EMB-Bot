"""script_flow: does a script word's satin FLOW -- one reader for the
professional's DST and ours (2026-10-26, Kent: "the cursive needs to flow, as
if the direction (or centerline letter path) was drawn by a pencil or hand").

WHAT IT READS. One colour block's needle-down runs, fused and cut into cross
CHAINS exactly as `tools.letter_pieces` does (anti-parallel stitches whose
midpoints advance at satin pitch), but WITHOUT its cut at a 35 deg turn: a
jump in cross angle inside a sewn column is what this measures, so it must not
be read away. A chain of `MIN_COLUMN` crosses or more is a COLUMN.

PER CROSS PAIR inside a column (each cross against the one TWO on, sewing
order -- a zigzag's neighbours lean opposite ways by twice its pitch over its
width, which is the satin, not the stroke turning): the turn of the cross
angle (deg, folded to 0-90) over the advance of its midpoint (mm):
`turn_per_mm`. A pen's satin turns its crosses smoothly with the stroke; a
column built on a jagged centreline turns them in jumps. `jump` is that turn
whatever the advance.

PER JOIN: two columns sewn one after the other whose ends meet (the next one's
first cross within `JOIN_MM` of the last one's last): the cross angle's turn
across the join, each end's angle the axial mean of its two end crosses (so
the zigzag's lean cancels, as above). A pen carries the satin through a
letter; a construction that stops and restarts at a new angle shows here.

CENTRELINE: each column's cross midpoints, the heading taken over `HEADING_MM`
of arc either side; a KINK is a heading change over `KINK_DEG` within
`KINK_MM` of arc -- a corner in what should be a curve. Reported per 10 mm.

ORDER: with `#x1,x2,...` after the file, the word is cut into letters at those
fractions of its own width (each file's letters where it draws them, as
`tools.script_census` does) and each column belongs to the letter holding its
median midpoint. `backtracks`: a column sewn in a letter LEFT of the one sewn
before it -- writing goes left to right.

BOX: `--box x0,y0,x1,y1` keeps only the columns whose median midpoint lies in
that box, in fractions of the block's own needle-down extent -- for a word
that shares its colour block with other lettering (To a T's "Machine" sits
between "TO A T", "LLC" and the frame, in both files).

    python -m tools.script_flow FILE.dst@BLOCK[#x1,x2,...] [...] [--box x0,y0,x1,y1] [--json OUT]
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

MIN_COLUMN = 6          # crosses
JOIN_MM = 1.5
HEADING_MM = 0.8
KINK_MM = 1.0
KINK_DEG = 35.0
MIN_ADVANCE_MM = 0.05


def _fold(d: float) -> float:
    d = abs(d) % 180.0
    return min(d, 180.0 - d)


def _axial(*deg: float) -> float:
    """-> the mean of undirected angles (deg, 0-180)."""
    c = sum(math.cos(math.radians(2 * d)) for d in deg)
    s = sum(math.sin(math.radians(2 * d)) for d in deg)
    return math.degrees(math.atan2(s, c)) / 2.0 % 180.0


def columns_of(path: Path, block: int, box: tuple | None = None) -> list[list[tuple]]:
    """-> the block's cross chains in sewing order (each a list of
    `letter_pieces.chains` crosses: (a, b, mid, dir_deg, len, idx, d)),
    only those in `box` (see BOX) when it is given."""
    runs = [r for r in LP.runs_of(Path(path)) if r["block"] == block]
    out = [ch for r in runs for ch in LP.chains(LP.fuse(r["pts"]))]
    if box is None or not runs:
        return out
    xy = np.concatenate([np.asarray(r["pts"], float) for r in runs])
    (x0, y0), (x1, y1) = xy.min(0), xy.max(0)
    lo = (x0 + box[0] * (x1 - x0), y0 + box[1] * (y1 - y0))
    hi = (x0 + box[2] * (x1 - x0), y0 + box[3] * (y1 - y0))

    def inside(ch):
        m = np.median(np.array([s[2] for s in ch]), axis=0)
        return lo[0] <= m[0] <= hi[0] and lo[1] <= m[1] <= hi[1]
    return [ch for ch in out if inside(ch)]


def _headings(mids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """-> (arc length at each midpoint, heading deg there over +-HEADING_MM)."""
    seg = np.hypot(*np.diff(mids, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    hd = np.full(len(mids), np.nan)
    j0 = j1 = 0
    for i in range(len(mids)):
        while s[i] - s[j0] > HEADING_MM:
            j0 += 1
        while j1 < len(mids) - 1 and s[j1] - s[i] < HEADING_MM:
            j1 += 1
        if j1 > j0:
            d = mids[j1] - mids[j0]
            if float(np.hypot(*d)) > 1e-6:
                hd[i] = math.degrees(math.atan2(d[1], d[0]))
    return s, hd


def flow(path: Path, block: int, letters: list[float] | None = None,
         box: tuple | None = None) -> dict:
    chs = columns_of(path, block, box)
    cols = [c for c in chs if len(c) >= MIN_COLUMN]
    rates, jumps, kinks, spine_mm = [], [], 0, 0.0
    for c in cols:
        mids = np.array([s[2] for s in c])
        # every OTHER cross: a zigzag's neighbours lean opposite ways by
        # twice the pitch over the width (11 deg on a 2 mm column), which
        # is the satin, not the stroke turning
        for p, q in zip(c, c[2:]):
            t = _fold(q[3] - p[3])
            adv = float(np.hypot(*(q[2] - p[2])))
            jumps.append(t)
            rates.append(t / max(adv, MIN_ADVANCE_MM))
        s, hd = _headings(mids)
        spine_mm += float(s[-1])
        k, i = 0, 0
        last_kink = -1e9
        for i in range(len(mids)):
            if np.isnan(hd[i]):
                continue
            k = i
            while k < len(mids) - 1 and s[k + 1] - s[i] <= KINK_MM:
                k += 1
            if k > i and not np.isnan(hd[k]):
                turn = abs((hd[k] - hd[i] + 180.0) % 360.0 - 180.0)
                if turn > KINK_DEG and s[i] - last_kink > KINK_MM:
                    kinks += 1
                    last_kink = s[i]
    joins = []
    for p, q in zip(cols, cols[1:]):
        gap = float(np.hypot(*(q[0][2] - p[-1][2])))
        if gap <= JOIN_MM:
            joins.append(_fold(_axial(q[0][3], q[1][3]) - _axial(p[-2][3], p[-1][3])))
    out = {"file": Path(path).name, "block": block, "columns": len(cols),
           "crosses": sum(len(c) for c in cols),
           "turn_per_mm_p50": round(float(np.percentile(rates, 50)), 1) if rates else None,
           "turn_per_mm_p95": round(float(np.percentile(rates, 95)), 1) if rates else None,
           "jump_p95": round(float(np.percentile(jumps, 95)), 1) if jumps else None,
           "jump_max": round(float(max(jumps)), 1) if jumps else None,
           "jumps_over_15": sum(1 for j in jumps if j > 15.0),
           "joins": len(joins),
           "join_turn_p50": round(float(np.median(joins)), 1) if joins else None,
           "join_turn_max": round(float(max(joins)), 1) if joins else None,
           "joins_over_30": sum(1 for j in joins if j > 30.0),
           "kinks_per_10mm": round(10.0 * kinks / spine_mm, 2) if spine_mm else None,
           "spine_mm": round(spine_mm, 1)}
    if letters is not None and cols:
        allx = [s[2][0] for c in cols for s in c]
        x0, x1 = min(allx), max(allx)
        seq = []
        for c in cols:
            xs = sorted(s[2][0] for s in c)
            f = (xs[len(xs) // 2] - x0) / max(x1 - x0, 1e-9)
            seq.append(sum(1 for cut in letters if f >= cut))
        out["letter_seq"] = seq
        out["backtracks"] = sum(1 for a, b in zip(seq, seq[1:]) if b < a)
        out["columns_per_letter"] = [seq.count(k) for k in range(len(letters) + 1)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+", help="FILE.dst@N, optionally #x1,x2 letter cuts")
    ap.add_argument("--box", help="x0,y0,x1,y1: fractions of the block's extent")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    box = tuple(float(v) for v in a.box.split(",")) if a.box else None
    res = []
    for f in a.files:
        f, _, cuts = f.partition("#")
        name, _, blk = f.rpartition("@")
        res.append(flow(Path(name), int(blk), [float(c) for c in cuts.split(",")] if cuts else None, box))
        print(json.dumps(res[-1]))
    if a.json:
        a.json.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
