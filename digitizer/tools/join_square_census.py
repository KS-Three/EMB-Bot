#!/usr/bin/env python
"""`cfg.satin_join_square` OFF against ON, per real lettering logo: fan ends,
stitches, trims, and a render of every letter the flag moves (2026-10-08).

Built for Kent's flip decision. The flag's only evidence had been Hotel
Fremont (fan ends 7 -> 5 by `letter_band.fan_ends`); this reads it on the
rest of the corpus with the same instruments, plus the one that sees the
fans `fan_ends` cannot (`letter_band.splay_ends`: a splayed end breaks the
side-alternation `fan_ends`' column cutter needs, so the worst fans were
never in its count).

Stages 0-6 run ONCE per logo -- stage 7 is the flag's only reader
(`stage7_sequence` -> `satin_shape(join_square=...)`) -- and `plan_stitches`
runs twice on the same `PipelineResult`, so the two arms see the identical
regions and every difference is the flag's.

Per text-candidate letter (`meta.text_candidate`), over its satin runs:

  fan     `letter_band.fan_ends`   -- lean vs the local rail, sustained columns
  splay   `letter_band.splay_ends` -- absolute cross direction, column grown
          back over the crosses `fan_ends` drops
  bare    the letter's artwork left uncovered by its own thread, mm2 --
          the other price side: a slab's wings are owned by nobody, so a
          fan into them was their only thread
  short   crosses under `SHORT_CROSS_MM` -- the price side: a straightened
          spine re-stations its column, and a short cross is where the
          short-stitch guard pulled a penetration (see the PR body)

and the whole design's stitch count and trims from `plan.stats`.

    .venv/bin/python tools/join_square_census.py [case ...] [--out DIR]
    .venv/bin/python tools/join_square_census.py fremont --width 80 --garment left_chest

`--out` (default `scratch_join_square/` at the repo root, gitignored by the
`scratch_*` pattern -- the renders hold client artwork) gets
`join_square_census.json` and `<case>_letters.png`: every letter whose fan,
splay or short count moved, OFF on the left and ON on the right, satin
crosses drawn over the artwork outline.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from shapely.geometry import LineString                        # noqa: E402
from shapely.ops import unary_union                            # noqa: E402

from digitizer_core import PipelineConfig, machine             # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from digitizer_core.stage6_satin import strip_splits           # noqa: E402
from digitizer_core.stitches import strip_ties                 # noqa: E402
from letter_band import fan_ends, splay_ends                   # noqa: E402
from tools.thin_strokes import corpus_cases                    # noqa: E402

# A cross this short in a lettering column is a guard-pulled penetration or a
# pinch, not a body cross: the lettering on the corpus is 0.6 mm and up wide.
SHORT_CROSS_MM = 0.6
# The corpus logos that carry text-tagged letters (fan_census.ORDER less
# bridge, whose eight tagged shapes are segmentation blobs, not letters).
DEFAULT = ["fremont", "becker", "gaulke", "enthusiast", "tires", "drone"]


def satin_of(plan, sid: str) -> list:
    return [strip_splits(strip_ties(list(run.points)))
            for _b, run in plan.iter_runs() if run.shape_id == sid and run.kind == "satin"]


def short_crosses(seqs) -> int:
    return sum(1 for s in seqs for a, b in zip(s, s[1:]) if math.dist(a, b) < SHORT_CROSS_MM)


def bare_mm2(plan, region) -> float:
    """The letter's artwork left uncovered by its own thread (satin, underlay
    and runs, each line at the coverage thread width)."""
    lines = [LineString(run.points).buffer(machine.COVERAGE_THREAD_W_MM / 2)
             for _b, run in plan.iter_runs()
             if run.shape_id == region.shape_id and run.kind in ("satin", "underlay", "run")
             and len(run.points) > 1]
    if not lines:
        return float(region.polygon.area)
    return float(region.polygon.difference(unary_union(lines)).area)


def read(plan, letters) -> dict:
    per = {}
    for r in letters:
        seqs = satin_of(plan, r.shape_id)
        fe, fc = fan_ends(seqs)
        se, sc = splay_ends(seqs)
        per[r.shape_id] = dict(fan=fe, columns=fc, splay=se, splay_columns=sc,
                               short=short_crosses(seqs), points=sum(len(s) for s in seqs),
                               bare=round(bare_mm2(plan, r), 3))
    tot = {k: sum(v[k] for v in per.values())
           for k in ("fan", "columns", "splay", "splay_columns", "short", "points", "bare")}
    return dict(per=per, total=tot, stitches=plan.stats.stitch_count, trims=plan.stats.trims)


def render(region, plans, ppm: int = 30):
    import cv2
    poly = region.polygon
    b = poly.bounds
    x0, y0 = b[0] - 0.8, b[1] - 0.8
    Wd, H = int((b[2] - b[0] + 1.6) * ppm), int((b[3] - b[1] + 1.6) * ppm)

    def px(P):
        return np.round((np.asarray(P, float) - (x0, y0)) * ppm).astype(np.int32)

    panels = []
    for label, plan in plans:
        im = np.full((H, Wd, 3), 255, np.uint8)
        for ring in [poly.exterior, *poly.interiors]:
            cv2.polylines(im, [px(ring.coords)], True, (200, 160, 60), 1, cv2.LINE_AA)
        for s in satin_of(plan, region.shape_id):
            for a, c in zip(s, s[1:]):
                col = (0, 0, 220) if math.dist(a, c) < SHORT_CROSS_MM else (40, 40, 40)
                cv2.line(im, tuple(px(a)), tuple(px(c)), col, 1, cv2.LINE_AA)
        bar = np.full((18, Wd, 3), 230, np.uint8)
        cv2.putText(bar, label, (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(np.vstack([bar, im]))
        panels.append(np.full((H + 18, 4, 3), 120, np.uint8))
    return np.hstack(panels[:-1])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*", help=f"corpus case names (default: {' '.join(DEFAULT)})")
    ap.add_argument("--out", default=str(ROOT.parent / "scratch_join_square"))
    ap.add_argument("--width", type=float, help="override the case's width, mm (e.g. 80)")
    ap.add_argument("--garment", help="override the case's garment (e.g. left_chest)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = {c[0]: c for c in corpus_cases()}
    report: dict = {}
    for name in a.cases or DEFAULT:
        _n, path, width, garment = cases[name]
        width, garment = a.width or width, a.garment or garment
        t = time.time()
        base = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6)
        res = run_stages(path, base)
        letters = sorted([r for r in res.regions if r.meta.get("text_candidate")],
                         key=lambda r: (round(r.polygon.bounds[1]), r.polygon.bounds[0]))
        plans = {}
        for arm, on in (("off", False), ("on", True)):
            cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6,
                                 satin_join_square=on)
            plans[arm] = plan_stitches(res, cfg)
        rep = {arm: read(plans[arm], letters) for arm in plans}
        rep["letters"] = len(letters)
        rep["secs"] = round(time.time() - t)
        rep["width_mm"], rep["garment"] = width, garment
        report[name] = rep
        o, n = rep["off"], rep["on"]
        print(f"{name:10} letters {len(letters):2}  fan {o['total']['fan']}/{o['total']['columns']} -> "
              f"{n['total']['fan']}/{n['total']['columns']}  splay {o['total']['splay']}/{o['total']['splay_columns']} -> "
              f"{n['total']['splay']}/{n['total']['splay_columns']}  short {o['total']['short']} -> {n['total']['short']}  "
              f"bare {o['total']['bare']:.2f} -> {n['total']['bare']:.2f} mm2  "
              f"stitches {o['stitches']} -> {n['stitches']}  trims {o['trims']} -> {n['trims']}  {rep['secs']}s",
              flush=True)
        moved = [r for r in letters
                 if any(o["per"][r.shape_id][k] != n["per"][r.shape_id][k] for k in ("fan", "splay", "short"))
                 or abs(o["per"][r.shape_id]["bare"] - n["per"][r.shape_id]["bare"]) > 0.05]
        if moved:
            import cv2
            rows = []
            for r in moved:
                po, pn = o["per"][r.shape_id], n["per"][r.shape_id]
                rows.append(render(r, [
                    (f"OFF fan {po['fan']} splay {po['splay']} short {po['short']} bare {po['bare']:.2f}", plans["off"]),
                    (f"ON  fan {pn['fan']} splay {pn['splay']} short {pn['short']} bare {pn['bare']:.2f}", plans["on"])]))
            Wm = max(p.shape[1] for p in rows)
            sheet = np.vstack([np.hstack([p, np.full((p.shape[0], Wm - p.shape[1], 3), 255, np.uint8)])
                               for p in rows])
            cv2.imwrite(str(out / f"{name}_letters.png"), sheet)
        (out / "join_square_census.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
