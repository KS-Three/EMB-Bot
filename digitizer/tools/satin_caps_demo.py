"""A synthetic satin-column picture: round-capped strokes against butt caps.

    python -m tools.satin_caps_demo --out ../docs/renders/satin-caps-2026-11-18

Our own made-up geometry (no client art, no pro file): a straight 3 mm column,
a curved 3 mm column, and a 0.8 mm line sewn with crosses spaced 1 mm apart,
drawn at the kit's 30 px/mm with `stitchviz.render_design(caps="round")` on the
left and `caps="butt"` on the right. The first two sew a clean edge, and the
butt draw shows one; the third is a line of separate bars in either draw (what
the prime grader's rubric says cannot be drawn truthfully under about 1 mm).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PX = 30.0


def _zigzag(points, width, y_off=0.0):
    """points: [(x, y, nx, ny)] in mm with the unit normal; -> design stitch dicts (0.1 mm, y up).
    One needle point per position, alternating rails: a satin's crosses, with no run along a rail."""
    out = []
    for i, (x, y, nx, ny) in enumerate(points):
        sgn = -1 if i % 2 == 0 else 1
        out.append({"type": "stitch", "x": round((x + sgn * nx * width / 2) * 10),
                    "y": round((y + y_off + sgn * ny * width / 2) * 10)})
    return out


def synthetic_design() -> dict:
    straight = [(i * 0.4, 0.0, 0.0, 1.0) for i in range(0, 101)]
    curve = []
    for i in range(0, 121):
        a = math.radians(i * 1.5)
        r = 9.0
        curve.append((r * math.sin(a) + 46.0, r * (1 - math.cos(a)), -math.sin(a), math.cos(a)))
    thin = [(46.0 + i * 1.0, -8.0, 0.0, 1.0) for i in range(0, 25)]
    st = _zigzag(straight, 3.0) + [{"type": "jump", "x": 460, "y": 0}] + _zigzag(curve, 3.0, 0.0)
    st += [{"type": "jump", "x": 460, "y": -80}] + _zigzag(thin, 0.8)
    st.append({"type": "end", "x": st[-1]["x"], "y": st[-1]["y"]})
    return {"stitches": st, "colors": [{"r": 30, "g": 60, "b": 150}]}


def pair():
    import cv2
    import numpy as np
    from digitizer_core import stitchviz
    d = synthetic_design()
    imgs = []
    for caps in ("round", "butt"):
        im = stitchviz.render_design(d, px_per_mm=PX, pad_mm=2.0, caps=caps)
        cv2.rectangle(im, (0, 0), (im.shape[1], 30), (255, 255, 255), -1)
        cv2.putText(im, f"caps={caps}" + ("  (the shared draw)" if caps == "round" else "  (kit only)"),
                    (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
        imgs.append(im)
    gap = np.full((imgs[0].shape[0], 20, 3), 255, np.uint8)
    return np.hstack([imgs[0], gap, imgs[1]])


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    import cv2
    a.out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(a.out / "satin-caps-round-vs-butt.png"), pair())
    print(a.out / "satin-caps-round-vs-butt.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
