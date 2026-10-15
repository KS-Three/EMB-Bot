"""Hair line supplement: refuse rendered-logo line detail (2026-10-15).

    python -m tools.hairline_logo_refusal probe [--only drone,owl_kent]

#942's supplement (`cfg.hairline_lines_gradient`, OFF) moves 3 of the 9
corpus logos (drone, screenshot, golden_tee): it sews highlights, hatching
and bevel edges of rendered art as if they were hair. `probe` plans the
supplement arm once per design and records, for every strand that SURVIVES
#942's two refusals, the features a third refusal could read: the host
shape the strand lies on, that shape's tone spread and grain (source L*
minus a blur of itself, over the shape's own pixels), and the same in a
band beside the strand. Every number is a property of the FILE, not of
cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import shapely

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import stage6_hairline_lines as L  # noqa: E402
from digitizer_core import stage7_sequence as S7  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools import hair_reach as hr  # noqa: E402
from tools import hairline_lines_gradient as G  # noqa: E402
from tools.thin_strokes import STUDIO_MAX_COLORS, corpus_cases  # noqa: E402

DEBUG = ROOT / "debug_out" / "hairline_logo_refusal"
OWL_WIDTH = G.OWL_WIDTH
GRAIN_SIGMAS = (1.0, 2.0, 4.0)


def _cases(only):
    out = [(n, p, w, dict(garment_id=g, max_colors=STUDIO_MAX_COLORS))
           for n, p, w, g in corpus_cases()]
    out.append(("owl_kent", hr.IMAGES["owl_kent"], OWL_WIDTH, {}))
    return [c for c in out if not only or c[0] in only]


def _mask(poly, sp, shape) -> np.ndarray:
    m = np.zeros(shape, np.uint8)
    geoms = getattr(poly, "geoms", [poly])
    for g in geoms:
        if g.is_empty:
            continue
        def px(ring):
            c = np.asarray(ring.coords, np.float64)
            return np.round(np.c_[c[:, 0] * sp.px_per_mm + sp.origin_px[0],
                                  c[:, 1] * sp.px_per_mm + sp.origin_px[1]]).astype(np.int32)
        cv2.fillPoly(m, [px(g.exterior)], 1)
        for h in g.interiors:
            cv2.fillPoly(m, [px(h)], 0)
    return m.astype(bool)


def _line_mask(pts, sp, shape, r: int) -> np.ndarray:
    m = np.zeros(shape, np.uint8)
    q = np.round(np.array([sp.to_px(x, y) for x, y in pts])).astype(np.int32)
    cv2.polylines(m, [q], False, 1, thickness=2 * r + 1)
    return m.astype(bool)


class Probe:
    """Wraps stage 7's `hairline_supplement_test`: every strand its refuse
    lets through is recorded with its features."""

    def __init__(self, image: str):
        self.image = image
        self.rows: list[dict] = []

    def __call__(self, regions, walked, sp, cfg):
        refuse = L.supplement_test(regions, walked, sp, cfg)
        light = L._light(sp)
        shape = light.shape
        resid = {s: np.abs(light - cv2.GaussianBlur(light, (0, 0), s)) for s in GRAIN_SIGMAS}
        tree = shapely.STRtree([r.polygon for r in regions])
        host_stats: dict[int, dict] = {}

        def stats_for(j):
            if j not in host_stats:
                m = _mask(regions[j].polygon, sp, shape)
                d = {"px": int(m.sum())}
                if m.any():
                    d["tone_std"] = round(float(light[m].std()), 2)
                    for s in GRAIN_SIGMAS:
                        d[f"grain_s{s:g}"] = round(float(np.median(resid[s][m])), 3)
                host_stats[j] = (m, d)
            return host_stats[j]

        def wrapped(s):
            why = refuse(s)
            if why is not None:
                return why
            x, y = L._samples(s["pts"])
            hit = tree.query(shapely.points(x, y), predicate="within")
            top = np.full(len(x), -1)
            for i, j in zip(hit[0].tolist(), hit[1].tolist()):
                top[i] = max(top[i], j)
            on = top[top >= 0]
            row = {"polarity": s["polarity"], "length_mm": round(s["length_mm"], 2),
                   "contrast": round(s["contrast"], 1), "strength": round(s["strength"], 3),
                   "stack": s.get("stack"), "on_shape_share": round(float(np.mean(top >= 0)), 2)}
            q = np.array([sp.to_px(a, b) for a, b in s["pts"]]).mean(axis=0)
            h, w = shape
            row["zone"] = hr.zone_of(self.image, q[0] / w, q[1] / h)
            if len(on):
                j = int(np.bincount(on).argmax())
                poly = regions[j].polygon
                row["host"] = j
                row["host_width_mm"] = round(2.0 * poly.area / poly.length, 2)
                row["host_area_mm2"] = round(poly.area, 1)
                bd = shapely.distance(poly.boundary, shapely.points(x, y))
                row["edge_share_0.3"] = round(float(np.mean(bd < 0.3)), 2)
                m, d = stats_for(j)
                row.update({f"host_{k}": v for k, v in d.items()})
                core = _line_mask(s["pts"], sp, shape, 2)
                band = _line_mask(s["pts"], sp, shape, 8) & ~core & m
                row["band_px"] = int(band.sum())
                if band.any():
                    row["band_tone_std"] = round(float(light[band].std()), 2)
                    for sg in GRAIN_SIGMAS:
                        row[f"band_grain_s{sg:g}"] = round(float(np.median(resid[sg][band])), 3)
                rest = m & ~core
                if rest.any():
                    for sg in GRAIN_SIGMAS:
                        row[f"host_rest_grain_s{sg:g}"] = round(
                            float(np.median(resid[sg][rest])), 3)
            self.rows.append(row)
            return None
        return wrapped


def cmd_probe(only) -> int:
    DEBUG.mkdir(parents=True, exist_ok=True)
    orig = S7.hairline_supplement_test
    try:
        for name, path, width, kw in _cases(only):
            t0 = time.time()
            cfg = G.cfg_for("supp", width, **kw)
            result = run_stages(path, cfg)
            probe = Probe(name)
            S7.hairline_supplement_test = probe
            plan = plan_stitches(result, cfg)
            S7.hairline_supplement_test = orig
            light = L._light(result.source_pixels)
            g = {f"image_grain_s{s:g}": round(float(np.median(
                np.abs(light - cv2.GaussianBlur(light, (0, 0), s)))), 3) for s in GRAIN_SIGMAS}
            row = {"image": name, "width_mm": width, "design_class": result.design_class,
                   "raster": list(result.source_pixels.rgb.shape[:2]), **g,
                   "trims": plan.stats.trims, "strands": probe.rows,
                   "seconds": round(time.time() - t0)}
            (DEBUG / f"probe_{name}.json").write_text(json.dumps(row, indent=1) + "\n",
                                                    encoding="utf-8")
            print(json.dumps({k: v for k, v in row.items() if k != "strands"}),
                  len(probe.rows), flush=True)
    finally:
        S7.hairline_supplement_test = orig
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--only", default="")
    args = ap.parse_args(argv)
    if args.cmd == "probe":
        return cmd_probe({s for s in args.only.split(",") if s})
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
