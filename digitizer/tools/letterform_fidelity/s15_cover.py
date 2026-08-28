"""Per-stroke coverage over a capture — the dropped-feature lens, run for real.

Reads `s1_cap.py`'s pickle and scores every region, worst stroke first. See
`stroke_coverage.py` for what this sees (a limb the thread never reached) and
what it does NOT (a column sewn at the wrong angle).

    cd digitizer
    .venv/bin/python tools/letterform_fidelity/s1_cap.py      # required first
    .venv/bin/python tools/letterform_fidelity/s15_cover.py
"""
import os as _os, pathlib as _pl, sys as _sys
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))

import pickle

from shapely.geometry import LineString
from shapely.ops import unary_union

from tools.letterform_fidelity.stroke_coverage import (
    mean_coverage, stroke_coverage, worst_stroke,
)

TH = 0.2                                  # half a 0.4 mm thread, as s11_iou.py
SKIP = {"travel", "jump", "trim"}


def main() -> None:
    data = pickle.load(open(_OUT + "/cap.pkl", "rb"))
    regions = dict(data["regions"])
    segs = []
    for block in data["blocks"]:
        for pts, kind in zip(block["runs"], block["run_kinds"]):
            if kind in SKIP or len(pts) < 2:
                continue
            segs.append(LineString(pts).buffer(TH, cap_style=1, join_style=1))
    thread = unary_union(segs)

    rows = []
    for shape_id, poly in regions.items():
        cov = stroke_coverage(poly, thread)
        w = worst_stroke(cov)
        if w is None:
            continue
        rows.append((w, mean_coverage(cov), len(cov), poly.area, shape_id))

    print("%-12s %8s %8s %8s %9s" % ("shape", "worst", "mean", "strokes", "area mm2"))
    for w, m, n, area, sid in sorted(rows):
        print("%-12s %7.1f%% %7.1f%% %8d %9.1f" % (sid[:12], w * 100, m * 100, n, area))
    print("\n%d regions scored. The GAP between worst and mean is the signal:" % len(rows))
    print("a letter that is locally damaged opens one; a uniformly thin one does not.")


if __name__ == "__main__":
    main()
