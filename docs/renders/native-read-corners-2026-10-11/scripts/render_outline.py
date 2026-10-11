"""Before/after Becker outline at its own 1.8 px/mm (80 mm): today's native
read against `subpixel_corner_runs`, stage 4's polygons over the source's
own alpha, with every reversal (a vertex turning back past 120 deg) ringed
and the counts in the label. Plus a 3x close-up of the MARINE letters.

usage (from digitizer/):
    .venv/Scripts/python ../docs/renders/native-read-corners-2026-10-11/scripts/render_outline.py OUT_DIR
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "digitizer")]

from digitizer_core import PipelineConfig, pipeline  # noqa: E402

BECKER = ROOT / "digitizer" / "testdata" / "becker_marine_logo.png"
ARMS = (("before: today (native read ON)", {}, (0, 0, 220)),
        ("after: subpixel_corner_runs ON", {"subpixel_corner_runs": True}, (200, 90, 0)))


def turns(polys, lo, hi):
    n, length, where = 0, 0.0, []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            r = np.asarray(ring.coords)
            seg = np.diff(r, axis=0)
            ln = np.hypot(seg[:, 0], seg[:, 1])
            keep = ln > 1e-9
            pts, seg, ln = r[:-1][keep], seg[keep], ln[keep]
            if len(seg) < 3:
                continue
            ang = np.arctan2(seg[:, 1], seg[:, 0])
            d = np.abs((np.diff(np.concatenate([ang, ang[:1]])) + np.pi) % (2 * np.pi) - np.pi)
            hit = (d > np.radians(lo)) & (d <= np.radians(hi))
            n += int(hit.sum())
            length += ln.sum()
            where += list(np.roll(pts, -1, axis=0)[hit])
    return (100.0 * n / length if length else 0.0), where


def stage4(kw):
    cap = {}
    orig = pipeline.vectorize

    def wrap(masks, ti, p, c):
        out = orig(masks, ti, p, c)
        cap.update(p=p, polys=[r.polygon for r in out[0]])
        return out

    pipeline.vectorize = wrap
    try:
        pipeline.build_generation(str(BECKER), PipelineConfig(target_width_mm=80.0, **kw))
    finally:
        pipeline.vectorize = orig
    return cap["p"], cap["polys"]


def draw(p, polys, col, sc, window=None):
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if window is None:
        wx0, wy0 = -(x1 - x0) / p.px_per_mm / 2 - 1, -(y1 - y0) / p.px_per_mm / 2 - 1
        w_mm, h_mm = (x1 - x0) / p.px_per_mm + 2, (y1 - y0) / p.px_per_mm + 2
    else:
        wx0, wy0, w_mm, h_mm = window
    W, H = int(w_mm * sc), int(h_mm * sc)
    a = cv2.resize(p.native_alpha, None, fx=p.upscale[0], fy=p.upscale[1], interpolation=cv2.INTER_NEAREST)
    M = np.float32([[p.px_per_mm / sc, 0, cx + wx0 * p.px_per_mm],
                    [0, p.px_per_mm / sc, cy + wy0 * p.px_per_mm]])
    back = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP)
    img = cv2.cvtColor((255 - back // 4).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    for g in polys:
        for ring in [g.exterior, *g.interiors]:
            q = (np.asarray(ring.coords) - [wx0, wy0]) * sc * 16
            cv2.polylines(img, [np.round(q).astype(np.int32).reshape(-1, 1, 2)], True, col, 2, cv2.LINE_AA, 4)
    _r, where = turns(polys, 120, 180)
    for v in where:
        c = np.round((v - [wx0, wy0]) * sc).astype(int)
        cv2.circle(img, tuple(int(x) for x in c), max(6, sc // 3), (0, 170, 0), 2, cv2.LINE_AA)
    return img


def label(img, text):
    img = img.copy()
    cv2.rectangle(img, (0, 0), (img.shape[1], 30), (255, 255, 255), -1)
    cv2.putText(img, text, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return cv2.copyMakeBorder(img, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0))


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    whole, close = [], []
    for text, kw, col in ARMS:
        p, polys = stage4(kw)
        rev, _ = turns(polys, 120, 180)
        right, _ = turns(polys, 60, 120)
        tag = (f"{text}  (in {p.input_px_per_mm:.2f} px/mm): {rev:.1f} reversals, "
               f"{right:.1f} right angles per 100 mm; green rings = reversals")
        whole.append(label(draw(p, polys, col, 22), tag))
        # the MARINE line, lower left: 3x
        close.append(label(draw(p, polys, col, 66, window=(-40.0, 8.5, 40.0, 14.0)), tag))
    cv2.imwrite(str(out / "becker-1.8-before-after.png"), np.vstack(whole))
    cv2.imwrite(str(out / "becker-1.8-marine-before-after.png"), np.vstack(close))


if __name__ == "__main__":
    main(sys.argv[1])
