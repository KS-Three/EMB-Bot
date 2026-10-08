#!/usr/bin/env python
"""`cfg.satin_free_end_square` on top of the shipped default
(`satin_join_square` ON since #666), beside `satin_slab_serifs`, per real
lettering logo: fan ends, bare artwork, bare corners, stitches, trims, and a
render of every letter an arm moves (2026-10-08).

Four arms, each a `plan_stitches` of the SAME `PipelineResult` -- stages 0-6
run once per logo and only stage 7 reads these flags -- so every difference
is the flags':

  base        join_square ON (the default), the two others OFF
  free_end    + `satin_free_end_square`
  slab        + `satin_slab_serifs` (the skeleton-level route to a slab's
              own column, built OFF in #663)
  both        + both (the shipped default since Kent's flip, 2026-10-08)

Per text-candidate letter (`meta.text_candidate`), over its satin runs:

  fan     `letter_band.fan_ends`   -- lean vs the local rail, sustained columns
  splay   `letter_band.splay_ends` -- absolute cross direction, column grown
          back over the crosses `fan_ends` drops
  bare    the letter's artwork uncovered by its own thread, mm2
  corner  the part of `bare` within `CORNER_R_MM` of a convex outline corner
          turning `CORNER_TURN_DEG` or more -- where a fan, a slab's wing or
          a square cap's face is sewn or not
  short   crosses under `SHORT_CROSS_MM` (guard-pulled penetrations)

and the whole design's stitch count and trims from `plan.stats`.

    .venv/bin/python tools/join_square_census.py [case ...] [--out DIR]
    .venv/bin/python tools/join_square_census.py fremont --width 80 --garment left_chest

`--out` (default `scratch_join_square/` at the repo root, gitignored by the
`scratch_*` pattern -- the renders hold client artwork) gets
`join_square_census.json` and `<case>_letters.png`: every letter an arm
moves, the four arms side by side.
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
CORNER_R_MM = 0.8
CORNER_TURN_DEG = 45.0
# Every arm sets both flags explicitly: since Kent's flip (2026-10-08) the
# config default is "both", and an arm that only ADDS a flag reads the same.
ARMS = {"base": {"satin_free_end_square": False, "satin_slab_serifs": False},
        "free_end": {"satin_free_end_square": True, "satin_slab_serifs": False},
        "slab": {"satin_free_end_square": False, "satin_slab_serifs": True},
        "both": {"satin_free_end_square": True, "satin_slab_serifs": True}}
# The corpus logos that carry text-tagged letters (fan_census.ORDER less
# bridge, whose eight tagged shapes are segmentation blobs, not letters).
DEFAULT = ["fremont", "becker", "gaulke", "enthusiast", "tires", "drone"]


def satin_of(plan, sid: str) -> list:
    return [strip_splits(strip_ties(list(run.points)))
            for _b, run in plan.iter_runs() if run.shape_id == sid and run.kind == "satin"]


def short_crosses(seqs) -> int:
    return sum(1 for s in seqs for a, b in zip(s, s[1:]) if math.dist(a, b) < SHORT_CROSS_MM)


def corner_zone(poly):
    """Discs of `CORNER_R_MM` at the outline's convex corners."""
    from shapely.geometry import Point
    discs = []
    for ring, outer in [(poly.exterior, True), *((r, False) for r in poly.interiors)]:
        pts = list(ring.coords)[:-1]
        n = len(pts)
        ccw = ring.is_ccw
        for i in range(n):
            a, b, c = np.asarray(pts[i - 1]), np.asarray(pts[i]), np.asarray(pts[(i + 1) % n])
            u, v = b - a, c - b
            if np.hypot(*u) < 1e-9 or np.hypot(*v) < 1e-9:
                continue
            turn = math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v))
            convex = (turn > 0) == (ccw == outer)
            if convex and abs(turn) >= CORNER_TURN_DEG:
                discs.append(Point(*b).buffer(CORNER_R_MM))
    return unary_union(discs) if discs else None


def bare_of(plan, region) -> tuple[float, float]:
    """(bare, bare at corners) mm2: the letter's artwork left uncovered by its
    own thread (satin, underlay and runs, each line at the coverage thread
    width), and the part of it in `corner_zone`."""
    lines = [LineString(run.points).buffer(machine.COVERAGE_THREAD_W_MM / 2)
             for _b, run in plan.iter_runs()
             if run.shape_id == region.shape_id and run.kind in ("satin", "underlay", "run")
             and len(run.points) > 1]
    bare = region.polygon.difference(unary_union(lines)) if lines else region.polygon
    zone = corner_zone(region.polygon)
    return float(bare.area), float(bare.intersection(zone).area) if zone is not None else 0.0


KEYS = ("fan", "columns", "splay", "splay_columns", "short", "points", "bare", "corner")


def read(plan, letters) -> dict:
    per = {}
    for r in letters:
        seqs = satin_of(plan, r.shape_id)
        fe, fc = fan_ends(seqs)
        se, sc = splay_ends(seqs)
        bare, corner = bare_of(plan, r)
        per[r.shape_id] = dict(fan=fe, columns=fc, splay=se, splay_columns=sc,
                               short=short_crosses(seqs), points=sum(len(s) for s in seqs),
                               bare=round(bare, 3), corner=round(corner, 3))
    tot = {k: sum(v[k] for v in per.values()) for k in KEYS}
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
        plans = {arm: plan_stitches(res, PipelineConfig(target_width_mm=width, garment_id=garment,
                                                        max_colors=6, **kw))
                 for arm, kw in ARMS.items()}
        rep = {arm: read(plans[arm], letters) for arm in plans}
        rep["letters"] = len(letters)
        rep["secs"] = round(time.time() - t)
        rep["width_mm"], rep["garment"] = width, garment
        report[name] = rep
        print(f"{name} at {width:g} mm / {garment}: {len(letters)} letters, {rep['secs']}s", flush=True)
        for arm in plans:
            e = rep[arm]
            print(f"  {arm:9} fan {e['total']['fan']:3}/{e['total']['columns']:<3} "
                  f"splay {e['total']['splay']:3}/{e['total']['splay_columns']:<3} "
                  f"bare {e['total']['bare']:7.2f} corner {e['total']['corner']:6.2f} mm2  "
                  f"short {e['total']['short']:3}  stitches {e['stitches']:6}  trims {e['trims']}", flush=True)
        b0 = rep["base"]["per"]
        moved = [r for r in letters if any(
            abs(rep[arm]["per"][r.shape_id]["bare"] - b0[r.shape_id]["bare"]) > 0.05
            or rep[arm]["per"][r.shape_id]["splay"] != b0[r.shape_id]["splay"] for arm in plans if arm != "base")]
        if moved:
            import cv2
            rows = []
            for r in moved:
                rows.append(render(r, [(f"{arm} splay {rep[arm]['per'][r.shape_id]['splay']} "
                                        f"bare {rep[arm]['per'][r.shape_id]['bare']:.2f}", plans[arm])
                                       for arm in plans]))
            Wm = max(p.shape[1] for p in rows)
            sheet = np.vstack([np.hstack([p, np.full((p.shape[0], Wm - p.shape[1], 3), 255, np.uint8)])
                               for p in rows])
            cv2.imwrite(str(out / f"{name}_letters.png"), sheet)
        (out / "join_square_census.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
