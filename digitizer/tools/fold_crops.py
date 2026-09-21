"""Crop-render one arm's sharp column folds against the shipped engine.

The judge for `tools/decomposition_census.py`'s `folds60` count, which is a
number about SPINES and cannot say whether a bend is a defect. Each crop is
the same window under both arms, artwork outline included, so the pair can be
read side by side: black is satin, salmon a bean/run, grey a fill.

Read on `cfg.satin_polygon_axis` 2026-09-16 (renders in
`docs/renders/polygon-axis-2026-09-16/`): every fold on Fremont and drone
sits at a letter junction, and Fremont's T upgrades a bean run to a satin
column -- mitres, not the 108 deg weld the metric was built to find.

Usage (cwd digitizer/, after a census run with --json):
  python tools/fold_crops.py <outdir> <case...>
The census JSON is read from <outdir>/../census.json.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

DIGI = Path.cwd()
sys.path.insert(0, str(DIGI))
sys.path.insert(0, str(DIGI / "tools"))

import decomposition_census as dc  # noqa: E402

PX = 40.0          # render scale, px per mm
HALF = 7.0         # crop half-width, mm


def run(case, arm):
    dc.apply_arm(arm)
    from digitizer_core import PipelineConfig, digitize
    rel, kw = dc.CASES[case]
    result, plan = digitize(DIGI / "testdata" / rel, PipelineConfig(**kw))
    runs = [(r.kind, r.points, r.shape_id) for _b, r in plan.iter_runs() if r.points]
    polys = {r.shape_id: r.polygon for r in result.regions}
    return runs, polys


def crop(runs, polys, cx, cy, shape_id, title):
    n = int(2 * HALF * PX)
    img = np.full((n, n, 3), 255, np.uint8)

    def to_px(p):
        return (int((p[0] - cx + HALF) * PX), int((p[1] - cy + HALF) * PX))

    poly = polys.get(shape_id)
    if poly is not None:
        for geom in getattr(poly, "geoms", [poly]):
            for ring in [geom.exterior, *geom.interiors]:
                pts = np.asarray([to_px(p) for p in ring.coords], np.int32)
                cv2.polylines(img, [pts], True, (235, 205, 170), 2)
    for kind, pts, sid in runs:
        col = {"satin": (0, 0, 0), "fill": (150, 150, 150), "bean": (90, 90, 200),
               "run": (90, 90, 200), "border": (40, 140, 40)}.get(kind, (200, 200, 200))
        a = np.asarray([to_px(p) for p in pts], np.int32)
        cv2.polylines(img, [a], False, col, 1, cv2.LINE_AA)
    cv2.putText(img, title, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 0, 0), 1, cv2.LINE_AA)
    return img


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    cases = sys.argv[2:]
    import json
    import subprocess
    for case in cases:
        # each arm in its own process: the arm patches module globals
        data = {}
        for arm in ("shipped", "polyaxis"):
            f = out / f"{case}_{arm}.json"
            subprocess.run([sys.executable, __file__, "--one", str(f), case, arm], check=True)
            data[arm] = json.loads(f.read_text())
        census = json.loads((out.parent / "census.json").read_text())
        folds = next(r["folds"] for r in census
                     if r["case"] == case and r["arm"] == "polyaxis")
        print(case, "folds", [(f["turn_deg"], f["at"]) for f in folds])
        for i, f in enumerate(folds[:4]):
            cx, cy = f["at"]
            tiles = []
            for arm in ("shipped", "polyaxis"):
                d = data[arm]
                runs = [(k, p, s) for k, p, s in d["runs"]]
                polys = {}
                from shapely.geometry import shape
                for sid, gj in d["polys"].items():
                    polys[sid] = shape(gj)
                tiles.append(crop(runs, polys, cx, cy, f["shape_id"],
                                  f"{arm} {f['turn_deg']}deg"))
            cv2.imwrite(str(out / f"{case}_fold{i}_{int(f['turn_deg'])}.png"),
                        np.hstack(tiles))
    print("wrote", out)


def one():
    import json
    from shapely.geometry import mapping
    f, case, arm = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    runs, polys = run(case, arm)
    f.write_text(json.dumps({
        "runs": [[k, [list(map(float, p)) for p in pts], s] for k, pts, s in runs],
        "polys": {sid: mapping(p) for sid, p in polys.items()},
        "folds": [],
    }))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        one()
    else:
        main()
