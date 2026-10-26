#!/usr/bin/env python
"""flip_two_proof: OFF | ON | pro for the 2026-10-23 flip of `border_by_size`
and `enclosed_alpha_hole_parts`.

OFF is today's engine with just those two flags set back to False through the
Studio request's `extra`; ON is the plain defaults. Per design: bordered-shape
counts per size band (the border census's detector, ring = BORDER or OUTLINE),
stitch and trim totals, and for Drone the O counter (our stitches inside the
O polygon's counter hole, and the pro's, registered onto ours).

    .venv/Scripts/python -m tools.flip_two_proof [--cache DIR] [--out FILE.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402

SLUGS = ["hotel_fremont_hat", "becker_hat_large", "mfab_hat", "precision_drone", "gaulke_roofing_hat"]
OFF = {"border_by_size": False, "enclosed_alpha_hole_parts": False}
BANDS = ((4, 6), (6, 10), (10, 999))


def digitize_arm(slug: str, cache: Path, arm: str) -> dict:
    from tools import border_census as bc, pro_pair as pp
    real = pp.digitize
    seen = {}

    def patched(art, width, garment="hat_front", extra=None):
        d = real(art, width, garment, dict(OFF) if arm == "off" else extra)
        seen["stitches"] = d.plan.stats.stitch_count
        seen["trims"] = d.plan.stats.trims
        return d

    pp.digitize = patched
    try:
        info = bc.digitize_one(slug, cache / arm)
    finally:
        pp.digitize = real
    (cache / arm / slug / "totals.json").write_text(json.dumps(seen), encoding="utf-8")
    return seen


def bands(rows: list[dict], side: str) -> dict:
    from tools.border_census import RING
    out = {}
    for lo, hi in BANDS:
        sel = [r for r in rows if lo <= r["mindim"] < hi]
        out[f"{lo}-{hi if hi < 999 else 'up'}"] = [len(sel), sum(r[side]["cls"] in RING for r in sel)]
    return out


def drone_o(cache: Path, arm: str) -> dict:
    """Stitch points inside the interior ring that looks like the O's counter
    (4.1 x 3.4 mm, +-0.8), ours and the pro's."""
    from shapely import wkt
    from shapely.affinity import affine_transform
    from shapely.geometry import Point, Polygon
    from tools.pro_parity.pairframe import register_pair
    from tools.study_pro import load_runs
    out = cache / arm / "precision_drone"
    info = json.loads((out / "ours.json").read_text(encoding="utf-8"))
    reg = register_pair(Path(info["pro"]), out / "ours.dst")
    ours_runs, _t, _j = load_runs(out / "ours.dst")
    pro_runs, _t, _j = load_runs(Path(info["pro"]))
    res = None
    for r in info["regions"]:
        p = wkt.loads(r["wkt"])
        for g in getattr(p, "geoms", [p]):
            for ring in g.interiors:
                h = Polygon(ring)
                x0, y0, x1, y1 = h.bounds
                w, hh = x1 - x0, y1 - y0
                if abs(w - 4.1) < 0.7 and abs(hh - 3.4) < 0.7 and (res is None or h.area > res[0].area):
                    res = (h, r["id"])
    if res is None:
        return {"found": False}
    hole, sid = res
    hole_pro = affine_transform(hole, reg.matrix())

    def inside(runs, poly):
        inner = poly.buffer(-0.3)
        return sum(inner.contains(Point(x, y)) for rr in runs for x, y in rr["pts"])

    return {"found": True, "shape": sid, "hole_mm": [round(hole.bounds[2] - hole.bounds[0], 2),
            round(hole.bounds[3] - hole.bounds[1], 2)], "area_mm2": round(hole.area, 1),
            "ours_pts_in_counter": inside(ours_runs, hole), "pro_pts_in_counter": inside(pro_runs, hole_pro)}


def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cache", default=str(DIGITIZER / "debug_out" / "flip_two"))
    ap.add_argument("--out", default=str(DIGITIZER.parent / "docs" / "renders" / "flip-two-2026-10-23" / "rows.json"))
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    cache = Path(a.cache)
    from tools import border_census as bc
    res = {}
    for slug in SLUGS:
        if a.only and slug not in a.only:
            continue
        row = {}
        for arm in ("off", "on"):
            if a.redo or not (cache / arm / slug / "totals.json").exists():
                print("digitizing", slug, arm, flush=True)
                digitize_arm(slug, cache, arm)
            tot = json.loads((cache / arm / slug / "totals.json").read_text(encoding="utf-8"))
            an = bc.analyse(slug, cache / arm)
            row[arm] = {"totals": tot, "bands": bands(an["rows"], "ours"), "pro_bands": bands(an["rows"], "pro")}
        res[slug] = row
        print(slug, json.dumps(row), flush=True)
    if not a.only or "precision_drone" in a.only:
        res["drone_O"] = {arm: drone_o(cache, arm) for arm in ("off", "on")}
        print("drone_O", json.dumps(res["drone_O"]))
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
