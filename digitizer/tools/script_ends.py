"""script_ends: how a script column ENDS, read the same way off the professional's DST and ours.

NUMBERS ONLY (2026-11-19). Nothing is drawn; a professional's file is read from a path the caller
extracts (never commit the extract). Companion of `tools.script_flow`: same cross chains
(`letter_pieces.chains` over `fuse`), no cut at a turn.

PER COLUMN END (a chain of >= MIN_COLUMN crosses, each end):
  face_deg   the last cross's direction against the stroke axis (the heading of the cross midpoints
             over AXIS_MM of arc back from the end), folded: 90 = square to the pen, 0 = along it.
  shorten    mean length of the last `END_N` crosses / the column's median cross length (1.0 = no taper).
  taper_mm   arc length from the end to the first cross whose length reaches `TAPER_FRAC` of the median.
  free       no other column's cross midpoint within FREE_MM of the end's midpoint (a stroke END, not a join).
  join_mm    for a non-free end: distance to the nearest other column's cross midpoint.

    python -m tools.script_ends FILE.dst@BLOCK [--box x0,y0,x1,y1] [--json OUT]
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

from tools import script_flow as SF  # noqa: E402

MIN_COLUMN = 6
AXIS_MM = 1.2
END_N = 3
TAPER_FRAC = 0.9
FREE_MM = 1.5


def _fold90(d: float) -> float:
    """Undirected angle between two lines, 0..90."""
    d = abs(d) % 180.0
    return min(d, 180.0 - d)


def column_ends(cols: list[list[tuple]]) -> list[dict]:
    mids_all = [np.array([s[2] for s in c]) for c in cols]
    out = []
    for ci, c in enumerate(cols):
        mids = mids_all[ci]
        lens = np.array([s[4] for s in c])
        med = float(np.median(lens))
        seg = np.hypot(*np.diff(mids, axis=0).T)
        arc = np.concatenate([[0.0], np.cumsum(seg)])
        for end in ("first", "last"):
            idx = np.arange(len(c)) if end == "last" else np.arange(len(c))[::-1]
            # walk from the end inwards
            order = idx[::-1] if end == "last" else idx[::-1]
            order = np.arange(len(c) - 1, -1, -1) if end == "last" else np.arange(len(c))
            m_end = mids[order[0]]
            d_arc = np.abs(arc[order] - arc[order[0]])
            k = int(np.searchsorted(d_arc, AXIS_MM)) if d_arc[-1] >= AXIS_MM else len(order) - 1
            if k < 1:
                continue
            ax = m_end - mids[order[k]]
            if float(np.hypot(*ax)) < 1e-6:
                continue
            axis_deg = math.degrees(math.atan2(ax[1], ax[0]))
            cr = [c[order[j]][3] for j in range(min(2, len(order)))]
            face = _fold90(float(np.mean([_fold90(a - axis_deg) for a in cr])))
            short = float(np.mean(lens[order[:END_N]]) / med)
            taper = 0.0
            for j, o in enumerate(order):
                if lens[o] >= TAPER_FRAC * med:
                    taper = float(d_arc[j])
                    break
            else:
                taper = float(d_arc[-1])
            others = [m for cj, m in enumerate(mids_all) if cj != ci]
            dmin = min((float(np.min(np.hypot(*(m - m_end).T))) for m in others), default=99.0)
            out.append({"column": ci, "end": end, "n": len(c), "x": round(float(m_end[0]), 1),
                        "y": round(float(m_end[1]), 1), "face_deg": round(face, 1),
                        "shorten": round(short, 2), "taper_mm": round(taper, 2),
                        "median_cross_mm": round(med, 2), "free": dmin > FREE_MM,
                        "join_mm": round(dmin, 2)})
    return out


def summarise(ends: list[dict]) -> dict:
    def stat(rows, key):
        v = [r[key] for r in rows]
        return {"n": len(v), "median": round(float(np.median(v)), 2), "min": round(min(v), 2),
                "max": round(max(v), 2)} if v else {"n": 0}
    free = [e for e in ends if e["free"]]
    join = [e for e in ends if not e["free"]]
    return {"free_ends": {k: stat(free, k) for k in ("face_deg", "shorten", "taper_mm")},
            "joined_ends": {k: stat(join, k) for k in ("face_deg", "shorten", "taper_mm", "join_mm")}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", help="FILE.dst@BLOCK")
    ap.add_argument("--box", help="x0,y0,x1,y1 as fractions of the block's extent")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    path, _, blk = a.file.partition("@")
    box = tuple(float(v) for v in a.box.split(",")) if a.box else None
    chs = SF.columns_of(Path(path), int(blk or 0), box)
    cols = [c for c in chs if len(c) >= MIN_COLUMN]
    ends = column_ends(cols)
    res = {"columns": len(cols), "summary": summarise(ends), "ends": ends}
    print(json.dumps({"columns": res["columns"], "summary": res["summary"]}, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
