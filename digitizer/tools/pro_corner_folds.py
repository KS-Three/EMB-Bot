"""pro_corner_folds: how the professional turns a satin column round a
corner, read off his DST files (2026-10-23, `cfg.lettering_columns_corner_fold`).

WHAT IT READS. Within one needle-down run of a word's band, a FOLD is a
stretch of four or more consecutive satin crosses whose ends on one side
stay within `R` of one point (the inside corner) while the other ends walk
on at the satin pitch (median step under 0.7 mm), sweeping more than 50
degrees. A satin cross is a stitch of 0.9 mm or more with a direction
reversal either side of it. Per fold: crosses (zigzag legs) in the fan,
sweep, the inner ends' spread, the outer step, the outer arc, the median
cross either side of the fan (the two strokes' sewn widths). A corner the
pro CUT shows up as no fold at all: a column ends and another starts
(the band reader's butts, `tools/column_harness.py`'s `census`).

  python -m tools.pro_corner_folds fremont|drone|proseal|mfab [--json OUT]

The bands are the 5-10 mm words of `docs/lettering-5-10mm-2026-10-23.md`
(Fremont HOTEL FREMONT block 7, Drone PRECISION block 3, Proseal PROSEAL
block 0, MFab AND WELDING blocks 2 and 4), in each DST's own frame.
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

from tools._console import utf8_console  # noqa: E402

R = 0.45            # inner ends within this of their centroid pivot on one corner
MIN_SWEEP = 50.0
MIN_CROSS = 0.9
MAX_STEP = 0.7      # the outer ends walk at the satin pitch, not an underlay's zigzag
BANDS = {"fremont": (21.0, 30.0, {7}), "drone": (40.5, 48.5, {3}),
         "proseal": (44.0, 55.0, {0}), "mfab": (23.5, 33.5, {2, 4})}


def pro_file(job: str) -> Path:
    from tools import small_text_columns as stc
    if job == "mfab":
        return stc.PRO_DIR / "MFAB" / "Mfab Hat & Polo" / "mf4b logo hat.DST"
    return stc.JOBS[job]["pro"]


def crosses_of(run) -> list:
    """Satin crosses of one run: (a, b, stitch index)."""
    p = np.array(run)
    seg = np.diff(p, axis=0)
    ln = np.hypot(seg[:, 0], seg[:, 1])
    out = []
    for i in range(len(seg)):
        if ln[i] < MIN_CROSS:
            continue
        if i > 0 and np.dot(seg[i - 1], seg[i]) >= 0 and ln[i - 1] > 0.05:
            continue
        if i + 1 < len(seg) and np.dot(seg[i], seg[i + 1]) >= 0 and ln[i + 1] > 0.05:
            continue
        out.append((tuple(p[i]), tuple(p[i + 1]), i))
    return out


def folds(run) -> list[dict]:
    cr = crosses_of(run)
    if len(cr) < 8:
        return []
    found, i = [], 0
    while i < len(cr) - 3:
        hit = False
        for side in (0, 1):
            pts, j = [], i
            while j < len(cr):
                q = cr[j][0] if cr[j][2] % 2 == side else cr[j][1]
                pts.append(q)
                c = np.mean(pts, axis=0)
                if max(math.dist(q2, c) for q2 in pts) > R:
                    pts.pop()
                    break
                j += 1
            if j - i < 4:
                continue
            fan = cr[i:j]
            inner = [(a if k % 2 == side else b) for a, b, k in fan]
            outer = [(b if k % 2 == side else a) for a, b, k in fan]
            angs = [math.atan2(o[1] - n[1], o[0] - n[0]) for n, o in zip(inner, outer)]
            sweep = max(abs(math.degrees((x - angs[0] + math.pi) % (2 * math.pi) - math.pi)) for x in angs)
            steps = [math.dist(p1, p2) for p1, p2 in zip(outer, outer[1:])]
            if sweep < MIN_SWEEP or float(np.median(steps)) > MAX_STEP:
                break
            wb = [math.dist(a, b) for a, b, _ in cr[max(0, i - 6):i]]
            wa = [math.dist(a, b) for a, b, _ in cr[j:j + 6]]
            found.append(dict(n=len(fan), sweep=round(sweep), spread=round(max(
                math.dist(p1, p2) for p1 in inner for p2 in inner), 2),
                step_med=round(float(np.median(steps)), 2), arc=round(sum(steps), 2),
                w_before=round(float(np.median(wb)), 2) if wb else None,
                w_after=round(float(np.median(wa)), 2) if wa else None,
                at=[round(float(v), 1) for v in np.mean(inner, axis=0)]))
            i, hit = j - 1, True
            break
        i += 1
    return found


def read(job: str) -> list[dict]:
    from tools import small_text_columns as stc
    blocks = stc.read_blocks(pro_file(job))
    y0, y1, keep = BANDS[job]
    out = []
    for bi in keep:
        for r in stc._runs(blocks[bi]):
            if y0 <= float(np.mean([q[1] for q in r])) <= y1:
                out += folds(r)
    return out


def main(argv=None) -> int:
    utf8_console(sys.stdout)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("job", choices=sorted(BANDS))
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    rows = read(args.job)
    for f in rows:
        print(json.dumps(f))
    if rows:
        med = lambda k: float(np.median([f[k] for f in rows if f[k] is not None]))  # noqa: E731
        ratios = [max(f["w_before"], f["w_after"]) / min(f["w_before"], f["w_after"])
                  for f in rows if f["w_before"] and f["w_after"]]
        print(json.dumps({"job": args.job, "folds": len(rows), "legs_med": med("n"),
                          "sweep_med": med("sweep"), "spread_med": med("spread"),
                          "arc_med": med("arc"), "arc_max": max(f["arc"] for f in rows),
                          "width_ratio_med": round(float(np.median(ratios)), 2) if ratios else None,
                          "width_ratio_max": round(max(ratios), 2) if ratios else None}))
    else:
        print(json.dumps({"job": args.job, "folds": 0}))
    if args.json:
        args.json.write_text(json.dumps(rows, indent=0), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
