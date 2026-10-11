"""OFF vs ON thread render, exposed fill-travel legs (exact > 0.1 mm) drawn red.

    digitizer/.venv/bin/python docs/renders/fill-order-sewn-paths-2026-10-08/render_pair.py screenshot <out-dir>
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3] / 'digitizer'; sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import cv2, numpy as np
import travel_legs as tl                      # wraps StitchRun before the pipeline import
from digitizer_core import PipelineConfig, stitches
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.stitchviz import render_design
from thread_path_render import plan_mm_to_px
from thin_strokes import REAL_ART
name, out = sys.argv[1], Path(sys.argv[2]); PX = 14.0
rel, _w, garment = REAL_ART[name]
tiles = []
for flag in (False, True):
    cfg = PipelineConfig(target_width_mm=80.0, garment_id=garment, max_colors=6,
                         fill_order_sewn_paths=flag)
    res = finish_generation(build_generation(str(ROOT / 'testdata' / rel), cfg).fork(), cfg)
    plan = plan_stitches(res, cfg)
    design = plan_to_design(plan)
    img = render_design(design, px_per_mm=PX, lit=True)
    to_px = plan_mm_to_px(design, PX)
    rows = [r for r in tl.legs(res, plan) if r['emitter'][1] == 'emit' and r['exact_mm'] > 0.1]
    runs = [run for b in plan.blocks for run in b.runs]
    tot = 0.0
    for r in rows:
        pts = np.array([[int(round(c)) for c in to_px(x, y)]
                        for x, y in stitches.strip_ties(runs[r['idx']].points)], np.int32)
        cv2.polylines(img, [pts], False, (0, 0, 255), 3, cv2.LINE_AA)
        tot += r['exact_mm']
    label = f"{'ON ' if flag else 'OFF'} fill_order_sewn_paths: exposed fill travel {tot:.1f} mm, trims {plan.stats.trims}"
    band = np.full((40, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, label, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2, cv2.LINE_AA)
    tiles.append(np.vstack([band, img]))
    print(label, flush=True)
w = min(t.shape[1] for t in tiles)
cv2.imwrite(str(out / f'{name}_off_vs_on.png'), np.hstack([t[:min(x.shape[0] for x in tiles), :w] for t in tiles]))
