#!/usr/bin/env python
"""What does `cfg.edge_cap_fold_into_colour` buy, and what does it move?

The A/B for the flag (photo/tonal v1 spec, engineering item "sequencing trim
thrash"; Kent 2026-08-24: "68-78 stops a portrait is too many"). The
follow-adjacent edge cap (PR #647, default on) sews each cone's stretches of
the design's outer edge in a block of its own after ALL the artwork, so it
adds one machine stop per cone it touches -- every one a cone the artwork
already loaded. The flag sews a cone's stretches at the end of that cone's
last artwork block instead, when nothing sewn later comes within half a
border width of them.

Per (fixture, route), OFF vs ON:
  blocks, stops, revisits   blocks in the plan, colour changes, and blocks
                            beyond one per distinct cone
  stitches, trims           must not move: the flag reorders, it never adds
                            or removes a stitch or a cut
  diff_px                   share of the rendered design (`stitchviz`, 10
                            px/mm) whose colour changes by more than 8/255
                            in any channel -- what the reorder costs on the
                            picture, where a cap now sits under something
                            it used to sit over. Zero by construction when
                            the clearance test holds; measured, not assumed.

Writes OFF/ON renders to --out (gitignored debug_out by default) for the
fixtures named in --render.

Usage (cwd digitizer/):
  python tools/cap_fold_ab.py [--out DIR] [--render NAME ...] [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.stitchviz import render_design  # noqa: E402

PHOTO = ROOT / "testdata" / "photo"
# Real artwork only (ROADMAP gate 2's rule, applied here too): the one real
# photograph, through the photo lanes and the Studio's own route, then real
# customer logos so the flag's reach outside the tonal lane is on the record.
STUDIO = {"detect_photographic": True, "faces_route_flat": True}
CASES = [
    ("owl/photo_subject", PHOTO / "owl_kent.jpg", 127.0, {"forced_class": "photo_subject"}),
    ("owl/photo_scene", PHOTO / "owl_kent.jpg", 127.0, {"forced_class": "photo_scene"}),
    ("owl/studio", PHOTO / "owl_kent.jpg", 127.0, STUDIO),
    ("owl/default", PHOTO / "owl_kent.jpg", 127.0, {}),
    ("drone_render", PHOTO / "drone_render.png", 80.0, {}),
    ("golden_tee", PHOTO / "logo_golden_tee.jpg", 80.0, {}),
    ("gaulke", PHOTO / "logo_gaulke_roofing.png", 80.0, {}),
    ("hotel_fremont", PHOTO / "logo_hotel_fremont.webp", 92.5, {}),
    ("bridge_bar", PHOTO / "logo_bridge_bar.jpg", 80.0, {}),
    ("enthusiast", PHOTO / "enthusiast_logo.png", 93.0, {}),
    ("screenshot", PHOTO / "screenshot_phone_ui_golke.jpg", 80.0, {}),
    ("becker", ROOT / "testdata" / "becker_marine_logo.png", 80.0, {}),
]
PX_PER_MM = 10.0
DIFF_LEVEL = 8


def run(path: Path, width: float, extra: dict, on: bool):
    cfg = PipelineConfig(target_width_mm=width, edge_cap_fold_into_colour=on, **extra)
    result, plan = digitize(path, cfg)
    seq = [b.thread_number for b in plan.blocks]
    st = plan.stats
    row = dict(blocks=len(seq), stops=st.color_changes,
               revisits=len(seq) - len(Counter(seq)),
               stitches=st.stitch_count, trims=st.trims,
               cls=result.design_class)
    img = render_design(plan_to_design(plan), px_per_mm=PX_PER_MM)
    return row, img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "debug_out" / "cap_fold_ab")
    ap.add_argument("--render", nargs="*", default=["owl/photo_subject", "owl/studio"])
    ap.add_argument("--cases", nargs="*", default=None)
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    hdr = (f"{'case':<20} {'blocks':>9} {'stops':>9} {'revisits':>9} "
           f"{'stitches':>13} {'trims':>9} {'diff_px':>8}")
    print(hdr)
    for name, path, width, extra in CASES:
        if a.cases and name not in a.cases:
            continue
        off, img0 = run(path, width, extra, False)
        on, img1 = run(path, width, extra, True)
        if img0.shape == img1.shape:
            moved = (np.abs(img0.astype(int) - img1.astype(int)).max(axis=2)
                     > DIFF_LEVEL)
            diff = float(moved.mean())
        else:
            diff = float("nan")
        rows.append(dict(case=name, off=off, on=on, diff_px=diff))
        print(f"{name:<20} {off['blocks']:>4}>{on['blocks']:<4} "
              f"{off['stops']:>4}>{on['stops']:<4} {off['revisits']:>4}>{on['revisits']:<4} "
              f"{off['stitches']:>6}>{on['stitches']:<6} {off['trims']:>4}>{on['trims']:<4} "
              f"{diff:>8.5f}")
        if name in (a.render or ()):
            stem = name.replace("/", "_")
            cv2.imwrite(str(a.out / f"{stem}_off.png"), img0)
            cv2.imwrite(str(a.out / f"{stem}_on.png"), img1)
    if a.json:
        a.json.write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
