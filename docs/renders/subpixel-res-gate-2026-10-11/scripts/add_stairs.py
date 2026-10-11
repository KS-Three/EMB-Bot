"""Add `right_angles_per_100mm` to results.json: vertices turning between 60
and 120 degrees, per 100 mm of outline — the staircase the reversal count
cannot see (a stair step turns 90 degrees, never past 120). A genuinely
square corner counts too, so read it as a difference between columns.

Written after the Becker render showed the floor bring the 0.68 mm stair
back with ZERO reversals. Reads the polygons gate_table.py saved per run.

usage: python add_stairs.py RUNS_DIR RESULTS_JSON
"""
import json
import sys
from pathlib import Path

import numpy as np
from shapely import wkt


def right_angles(polys):
    n, length = 0, 0.0
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            r = np.asarray(ring.coords)
            seg = np.diff(r, axis=0)
            ln = np.hypot(seg[:, 0], seg[:, 1])
            seg, ln = seg[ln > 1e-9], ln[ln > 1e-9]
            if len(seg) < 3:
                continue
            ang = np.arctan2(seg[:, 1], seg[:, 0])
            d = np.abs((np.diff(np.concatenate([ang, ang[:1]])) + np.pi) % (2 * np.pi) - np.pi)
            n += int(((d > np.radians(60)) & (d <= np.radians(120))).sum())
            length += ln.sum()
    return 100.0 * n / length if length else 0.0


def main(runs, res):
    runs, res = Path(runs), Path(res)
    rows = json.loads(res.read_text())
    for r in rows:
        lane = "real" if r["case"] == "becker" else r["lane"]
        d = runs / f"{r['case']}-{lane}-r{r['rung']:g}"
        polys = [wkt.loads(s) for s in json.loads((d / f"arm_{r['config']}.json").read_text())]
        r["right_angles_per_100mm"] = right_angles(polys)
    res.write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
