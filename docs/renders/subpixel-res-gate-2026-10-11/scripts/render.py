"""Two before/after outline renders: today's default (native read ON, no
floor) against `subpixel_edges_min_px_per_mm` = 3.0.

  becker-1.8-before-after.png  the real Becker file at 80 mm (1.8 px/mm),
                               the region list as stages 0-4 leave it, over
                               the source's own alpha. No truth.
  <case>-1.8-before-after.png  a 14 x 9 mm window of a truth case at 1.8
                               px/mm, bare stage 4 on the same masks,
                               registered onto the native-resolution truth
                               (grey = truth's ink).

usage (from digitizer/):
    .venv/Scripts/python ../docs/renders/subpixel-res-gate-2026-10-11/scripts/render.py RUNS_DIR RESULTS_JSON OUT_DIR [CASE]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "digitizer"), str(ROOT / "docs/renders/tracer-head-to-head-2026-10-10/scripts")]

import analyze as A  # noqa: E402
from shapely import wkt  # noqa: E402
from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import build_generation  # noqa: E402

BECKER = ROOT / "digitizer" / "testdata" / "becker_marine_logo.png"
LABELS = (("before: today (native read ON)", {}, (0, 0, 220)),
          ("after: floor 3.0", {"subpixel_edges_min_px_per_mm": 3.0}, (200, 90, 0)))


def label(img, text):
    cv2.rectangle(img, (0, 0), (img.shape[1], 30), (255, 255, 255), -1)
    cv2.putText(img, text, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return cv2.copyMakeBorder(img, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0))


def becker(out, sc=22):
    tiles = []
    for text, kw, col in LABELS:
        gen = build_generation(str(BECKER), PipelineConfig(target_width_mm=80.0, **kw))
        p = gen.p
        x0, y0, x1, y1 = p.art_bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        w_mm, h_mm = (x1 - x0) / p.px_per_mm + 2, (y1 - y0) / p.px_per_mm + 2
        W, H = int(w_mm * sc), int(h_mm * sc)
        a = cv2.resize(p.native_alpha, None, fx=p.upscale[0], fy=p.upscale[1], interpolation=cv2.INTER_NEAREST)
        M = np.float32([[p.px_per_mm / sc, 0, cx - w_mm / 2 * p.px_per_mm],
                        [0, p.px_per_mm / sc, cy - h_mm / 2 * p.px_per_mm]])
        back = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP)
        img = cv2.cvtColor((255 - back // 4).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        for r in gen.regions:
            if r.meta.get("enclosed_background"):
                continue
            for ring in [r.polygon.exterior, *r.polygon.interiors]:
                q = (np.asarray(ring.coords) + [w_mm / 2, h_mm / 2]) * sc * 16
                cv2.polylines(img, [np.round(q).astype(np.int32).reshape(-1, 1, 2)], True, col, 2, cv2.LINE_AA, 4)
        tiles.append(label(img, f"{text}  (in {p.input_px_per_mm:.2f} px/mm)"))
    cv2.imwrite(str(out / "becker-1.8-before-after.png"), np.vstack(tiles))


def truth_case(runs, results, out, case, scale=40):
    lane = next(r["lane"] for r in results if r["case"] == case)
    truth = A.Truth(runs / f"{case}-{lane}-truth")
    tm = truth.meta
    win = A.densest(truth.b[::2, ::2], truth.ppm, tm["cx"], tm["cy"], 14, 9)
    back = A.label_backdrop(truth.lab, truth.ppm, tm["cx"], tm["cy"], win, scale)
    d = runs / f"{case}-{lane}-r1.8"
    tiles = []
    for (text, _kw, col), name in zip(LABELS, ("on", "gate3")):
        row = next(r for r in results if r["case"] == case and r["rung"] == 1.8 and r["config"] == name)
        polys = A.apply([wkt.loads(s) for s in json.loads((d / f"arm_{name}.json").read_text())],
                        np.asarray(row["reg"]))
        img = back.copy()
        for r in A.rings_of(polys):
            q = np.round((r - [win[0], win[1]]) * scale * 16).astype(np.int32)
            cv2.polylines(img, [q.reshape(-1, 1, 2)], True, col, 2, cv2.LINE_AA, 4)
        tiles.append(label(img, f"{text}: {row['p_med']:.3f} mm, {row['reversals_per_100mm']:.1f} rev, "
                           f"{row['right_angles_per_100mm']:.0f} right angles /100mm"))
    cv2.imwrite(str(out / f"{case}-1.8-before-after.png"), np.hstack(tiles))


if __name__ == "__main__":
    runs, res, out = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3])
    case = sys.argv[4] if len(sys.argv) > 4 else "fremontsil"
    becker(out)
    truth_case(runs, res, out, case)
