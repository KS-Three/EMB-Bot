#!/usr/bin/env python
"""Can anything we read predict the SIGN of the pro's fill slant? (2026-11-07,
`docs/fill-angle-pro-slant-2026-11-07.md`)

    python -m tools.fill_angle_slant_signals RUNS [--json OUT]

RUNS is a `tools.fill_angle_pro_census measure` directory run OFF: per job
`shapes.json` (our fill polygons + the pro's angle inside each) and
`design.json` (our stitches and runs). Per job, on its largest fill with >= 2
pro fill cells, the truth is the sign of the pro's offset from the nearest
axis; the candidate signals, all read from inputs a digitize has:

- `art`      edge slant of the artwork (Sobel, edge line = gradient + 90)
- `satin`    slant of OUR satin crossings (design.json runs of kind satin)
- `ourfill`  slant of our own fill rows
- `pca_off`  the shape's principal axis, signed offset from the nearest axis
- `edges`    the shape's boundary segments, length-weighted slant
- `cols`     (cols at -20 - cols at +20) / min: + when +20 cuts fewer columns

A slant figure is (mass at +8..+40 deg off axis - mass at -40..-8) / total.
Each signal becomes a rule `- if d * v < -t else +` whose direction d and
threshold t are FIT on the training jobs (ties keep the larger t, i.e. stay
nearer "always +"), and is scored leave-one-job-out and leave-one-ARTWORK-out
(the three To a T jobs share art, as do five Becker). "Always +" is the bar.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

SIGNALS = ("art", "satin", "ourfill", "pca_off", "edges", "cols")
ARTWORK = {"becker": "becker", "gaulke": "gaulke", "hotel_fremont": "fremont", "mfab": "mfab",
           "precision_drone": "drone", "goldentee": "goldentee", "toat": "toat",
           "tires": "tires", "bridge": "bridge", "proseal": "proseal"}


def artwork(job: str) -> str:
    return next((v for k, v in ARTWORK.items() if job.startswith(k)), job)


def off_axis(a: float) -> float:
    d = a % 90.0
    return d - 90.0 if d > 45.0 else d


def slant(angles, weights, lo: float = 8.0, hi: float = 40.0) -> float:
    p = m = t = 0.0
    for a, w in zip(angles, weights):
        o = off_axis(a)
        t += w
        if lo <= o <= hi:
            p += w
        elif -hi <= o <= -lo:
            m += w
    return (p - m) / t if t else 0.0


def art_slant(path: Path) -> float:
    import cv2
    import numpy as np
    from PIL import Image
    im = Image.open(path)
    rgba = np.asarray(im.convert("RGBA"), dtype=np.float32)
    a = rgba[:, :, 3:4] / 255.0
    g = (rgba[:, :, :3] * a + 255.0 * (1 - a)).mean(axis=2)
    s = 800.0 / max(g.shape)
    g = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    keep = mag > 0.2 * mag.max()
    ang = (np.degrees(np.arctan2(gy[keep], gx[keep])) + 90.0) % 180.0
    return slant(ang.tolist(), mag[keep].tolist())


def run_slant(design: dict, kind: str) -> float:
    st = design["stitches"]
    angs, lens = [], []
    for r in design["runs"]:
        if r["kind"] != kind:
            continue
        for i in range(r["i0"] + 1, r["i1"] + 1):
            a, b = st[i - 1], st[i]
            if a.get("type") != "stitch" or b.get("type") != "stitch":
                continue
            dx, dy = (b["x"] - a["x"]) / 10.0, (b["y"] - a["y"]) / 10.0
            ln = math.hypot(dx, dy)
            if ln >= 1.0:
                angs.append(math.degrees(math.atan2(dy, dx)) % 180.0)
                lens.append(ln)
    return slant(angs, lens)


def edge_slant(poly) -> float:
    polys = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    angs, lens = [], []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            c = list(ring.coords)
            for (x0, y0), (x1, y1) in zip(c, c[1:]):
                ln = math.hypot(x1 - x0, y1 - y0)
                if ln > 0:
                    angs.append(math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0)
                    lens.append(ln)
    return slant(angs, lens)


def job_rows(runs: Path, min_cells: int = 2) -> list[dict]:
    from shapely import wkt
    from digitizer_core import machine
    from digitizer_core.stage6_fill import _cols_at_angle
    from tools import pro_baseline as pb
    out = []
    for d in sorted(p for p in runs.iterdir() if (p / "shapes.json").exists()):
        j = json.loads((d / "shapes.json").read_text(encoding="utf-8"))
        rows = [r for r in j.get("shapes", []) if r.get("pro_deg") is not None
                and r.get("sewn_deg") is not None and r["pro_fill_cells"] >= min_cells]
        if not rows:
            continue
        big = max(rows, key=lambda r: r["area_mm2"])
        poly = wkt.loads(big["poly_wkt"])
        design = json.loads((d / "design.json").read_text(encoding="utf-8"))
        cp = _cols_at_angle(poly, machine.FILL_ANGLE_PRO_DEG, machine.FILL_ROW_MM)
        cm = _cols_at_angle(poly, 180.0 - machine.FILL_ANGLE_PRO_DEG, machine.FILL_ROW_MM)
        out.append({"job": d.name, "shape": big["shape"], "area_mm2": big["area_mm2"],
                    "pro_off": round(off_axis(big["pro_deg"]), 1),
                    "art": round(art_slant(pb.resolve(pb.JOBS[d.name][2])), 3),
                    "satin": round(run_slant(design, "satin"), 3),
                    "ourfill": round(run_slant(design, "fill"), 3),
                    "pca_off": round(off_axis(big["pca_deg"]), 1),
                    "edges": round(edge_slant(poly), 3),
                    "cols": round((cm - cp) / max(1, min(cm, cp)), 3), "cols_pm": [cp, cm]})
    return out


def fit(rows: list[dict], key: str) -> tuple[int, float]:
    truth = {r["job"]: 1 if r["pro_off"] > 0 else -1 for r in rows}
    best = None
    cuts = [math.inf] + sorted({abs(r[key]) - 1e-9 for r in rows})
    for d in (1, -1):
        for t in cuts:
            acc = sum((-1 if d * r[key] < -t else 1) == truth[r["job"]] for r in rows)
            k = (acc, t)
            if best is None or k > best[0]:
                best = (k, d, t)
    return best[1], best[2]


def predict(r: dict, key: str, d: int, t: float) -> int:
    return -1 if d * r[key] < -t else 1


def score(rows: list[dict]) -> dict:
    truth = {r["job"]: 1 if r["pro_off"] > 0 else -1 for r in rows}
    res = {"always_plus": sum(v == 1 for v in truth.values()), "n": len(rows)}
    for key in SIGNALS:
        lojo = loao = 0
        for r in rows:
            d, t = fit([x for x in rows if x["job"] != r["job"]], key)
            lojo += predict(r, key, d, t) == truth[r["job"]]
            d, t = fit([x for x in rows if artwork(x["job"]) != artwork(r["job"])], key)
            loao += predict(r, key, d, t) == truth[r["job"]]
        res[key] = {"leave_one_job_out": lojo, "leave_one_artwork_out": loao}
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    rows = job_rows(a.runs)
    print("| job | pro off-axis | " + " | ".join(SIGNALS) + " |")
    print("|---|---|" + "---|" * len(SIGNALS))
    for r in rows:
        print(f"| {r['job']} | {r['pro_off']:+.1f} | " + " | ".join(f"{r[k]:+.3f}" if k != "pca_off" else f"{r[k]:+.1f}"
                                                            for k in SIGNALS) + " |")
    res = score(rows)
    print(f"\nsign accuracy over {res['n']} jobs; always + = {res['always_plus']}")
    for k in SIGNALS:
        print(f"  {k:8s} leave-one-job-out {res[k]['leave_one_job_out']:2d}  "
              f"leave-one-artwork-out {res[k]['leave_one_artwork_out']:2d}")
    if a.json:
        a.json.write_text(json.dumps({"rows": rows, "score": res}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
