"""The native edge read (`subpixel_edges_upscaled`) by source resolution,
OFF / ON / ON with `subpixel_edges_min_px_per_mm` at 3.0, on golden_tee,
hotel_fremont and Becker. Reuses the 2026-10-10 head-to-head harness
(`docs/renders/tracer-head-to-head-2026-10-10/scripts/`): its truth runs,
its registration and its scores.

usage (from digitizer/; the script puts digitizer/ and the head-to-head
scripts on sys.path itself):
    .venv/Scripts/python ../docs/renders/subpixel-res-gate-2026-10-11/scripts/gate_table.py RUNS_DIR OUT_DIR

Cases. The two logos as stage 0 routes them (`gradient`, confidence 1.00 in
the head-to-head; forced here so the truth and the rung share a lane), and
the busiest single-colour layer of each written as a one-ink alpha cutout
(`make_sil.py`, the Becker class, flat lane) — four cases with a native-
resolution truth. Becker itself has no truth: it is read for reversals only,
at 80 mm (its own 1.8 px/mm) and at the widths that give 3 and 5.

Each rung is the source brought down with INTER_AREA so stage 1 reads it at
the nominal px/mm (calibrated on stage 1 itself, never under the nominal),
then stages 0-3 once; stage 4 is called on the SAME masks under each config.
Bare `vectorize()` output, as in `variants.py`.

Scores: `p_med` median distance arm edge -> truth edge, mm (the "edge error");
`r_med` the other direction; reversals = vertices turning back more than
120 degrees per 100 mm of boundary (`variants.spikes`). Registration: scale +
shift fitted on the MASK's own outline (4x nearest upsample of each kept
mask, traced), so no config is favoured.
"""
import dataclasses
import json
import runpy
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "digitizer"), str(ROOT / "docs/renders/tracer-head-to-head-2026-10-10/scripts")]

import analyze as A  # noqa: E402
import capture as C
from variants import spikes
from digitizer_core import pipeline
from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep

TESTDATA = ROOT / "digitizer" / "testdata"
LOGOS = {"golden": TESTDATA / "photo" / "logo_golden_tee.jpg",
         "fremont": TESTDATA / "photo" / "logo_hotel_fremont.webp"}
BECKER = TESTDATA / "becker_marine_logo.png"
RUNGS = (1.8, 3.0, 5.0)
W_MM = 80.0
CONFIGS = {
    "off": {"subpixel_edges_upscaled": False},
    "on": {},
    "gate3": {"subpixel_edges_min_px_per_mm": 3.0},
}


def _ppm(path, lane):
    return prep(str(path), PipelineConfig(target_width_mm=W_MM), design_class=lane).input_px_per_mm


def calibrate(src, img, lane, rung, tmp):
    """Width in px whose stage 1 reading is >= rung and within ~1% of it."""
    w = int(round(img.shape[1] * rung / _ppm(src, lane)))
    for _ in range(6):
        cv2.imwrite(str(tmp), C.downscale(img, w))
        got = _ppm(tmp, lane)
        if got >= rung:
            return w, got
        w += 1
    raise RuntimeError(f"could not reach {rung} px/mm")


def mask_outline(masks, keep, p):
    """Every kept mask's pixel-EDGE outline in plan mm (4x nearest, traced)."""
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    pts = []
    for i, rm in enumerate(masks):
        if i not in keep:
            continue
        big = cv2.resize(rm.crop.astype(np.uint8), None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        big = np.pad(big, 1)
        cs, _ = cv2.findContours(big, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        oy, ox = rm.origin
        for c in cs:
            c = c.reshape(-1, 2).astype(float) - 1.0
            fx = (c[:, 0] + 0.5) / 4.0 - 0.5 + ox
            fy = (c[:, 1] + 0.5) / 4.0 - 0.5 + oy
            pts.append(np.column_stack([(fx - cx) / p.px_per_mm, (fy - cy) / p.px_per_mm]))
    return np.vstack(pts)


def run_configs(src, cfg):
    """-> (prep, masks, {config: polygons}) — stage 4 under every config on
    one set of masks."""
    cap = {}
    orig = pipeline.vectorize

    def wrap(masks, ti, p, c):
        cap.update(masks=masks, p=p)
        for name, kw in CONFIGS.items():
            cap[name] = [r.polygon for r in orig(masks, ti, p, dataclasses.replace(c, **kw))[0]]
        return orig(masks, ti, p, c)

    pipeline.vectorize = wrap
    try:
        pipeline.build_generation(str(src), cfg)
    finally:
        pipeline.vectorize = orig
    return cap["p"], cap["masks"], {k: cap[k] for k in CONFIGS}


def kept(masks, p, polys, tmp):
    """Indices of masks the ON polygons cover (half their pixels or more)."""
    H, W = p.rgb.shape[:2]
    lab = np.zeros((H, W), np.int32)
    for i, rm in enumerate(masks):
        y0, x0 = rm.origin
        h, w = rm.crop.shape
        lab[y0:y0 + h, x0:x0 + w][rm.crop.astype(bool)] = i + 1
    x0, y0, x1, y1 = p.art_bbox
    meta = {"px_per_mm": p.px_per_mm, "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0}
    tmp.mkdir(exist_ok=True)
    np.save(tmp / "labels.npy", lab)
    return A.kept_masks(tmp, meta, polys)


def nodes(polys):
    return sum(len(r) - 1 for r in A.rings_of(polys))


def ensure_truths(runs):
    """capture.py truth runs and the alpha-only cutouts, as 2026-10-10."""
    cases = {}
    for fx, src in LOGOS.items():
        for lane in ("gradient", "flat"):
            d = runs / f"{fx}-{lane}-truth"
            if not (d / "meta.json").exists():
                C.main(str(src), str(d), 0.0, lane, "default")
        cases[(fx, "gradient")] = (src, runs / f"{fx}-gradient-truth")
        sil = runs / f"{fx}sil.png"
        if not sil.exists():
            sys.argv = ["make_sil.py", str(runs / f"{fx}-flat-truth"), str(sil)]
            runpy.run_path(str(Path(A.__file__).with_name("make_sil.py")))
        d = runs / f"{fx}sil-flat-truth"
        if not (d / "meta.json").exists():
            C.main(str(sil), str(d), 0.0, "flat", "default")
        cases[(f"{fx}sil", "flat")] = (sil, d)
    return cases


def main(runs, out):
    runs, out = Path(runs), Path(out)
    runs.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for (fx, lane), (src, tdir) in ensure_truths(runs).items():
        truth = A.Truth(tdir)
        img = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
        for rung in RUNGS:
            w, ppm = calibrate(src, img, lane, rung, runs / "_calib.png")
            d = runs / f"{fx}-{lane}-r{rung:g}"
            d.mkdir(exist_ok=True)
            cv2.imwrite(str(d / "input.png"), C.downscale(img, w))
            p, masks, arms = run_configs(d / "input.png", PipelineConfig(target_width_mm=W_MM, forced_class=lane))
            v = A.register(truth, mask_outline(masks, kept(masks, p, arms["on"], runs / "_tmp"), p))
            for name, polys in arms.items():
                q = A.apply(polys, v)
                pr, rc = A.stats(truth.dist(A.sample(q))), A.stats(truth.recall(q))
                rows.append({"case": fx, "lane": lane, "rung": rung, "input_px_per_mm": float(p.input_px_per_mm),
                             "work_px_per_mm": float(p.px_per_mm), "config": name,
                             "p_med": pr["med"], "p_p90": pr["p90"], "r_med": rc["med"],
                             "reversals_per_100mm": spikes(q), "turn": A.turning(q), "nodes": nodes(q),
                             "regions": len(q), "reg": [float(x) for x in v]})
                (d / f"arm_{name}.json").write_text(json.dumps([g.wkt for g in polys]))
            print(f"{d.name}: in {p.input_px_per_mm:.3f} px/mm, " + ", ".join(
                f"{r['config']} {r['p_med']:.3f} mm {r['reversals_per_100mm']:.1f}/100mm"
                for r in rows[-3:]), flush=True)
    # Becker: no truth. Its own 1.8 px/mm at 80 mm; 3 and 5 by sewing it smaller.
    nat = prep(str(BECKER), PipelineConfig(target_width_mm=W_MM)).input_px_per_mm
    for rung in RUNGS:
        width = W_MM if rung <= nat + 0.05 else float(np.floor(W_MM * nat / rung * 10.0) / 10.0)
        p, masks, arms = run_configs(BECKER, PipelineConfig(target_width_mm=width))
        d = runs / f"becker-real-r{rung:g}"; d.mkdir(exist_ok=True)
        for name, polys in arms.items():
            rows.append({"case": "becker", "lane": "routed", "rung": rung, "width_mm": width,
                         "input_px_per_mm": float(p.input_px_per_mm), "work_px_per_mm": float(p.px_per_mm),
                         "config": name, "p_med": None, "p_p90": None, "r_med": None,
                         "reversals_per_100mm": spikes(polys), "turn": A.turning(polys),
                         "nodes": nodes(polys), "regions": len(polys)})
            (d / f"arm_{name}.json").write_text(json.dumps([g.wkt for g in polys]))
        print(f"becker r{rung:g} ({width} mm, in {p.input_px_per_mm:.3f}): " + ", ".join(
            f"{r['config']} {r['reversals_per_100mm']:.1f}/100mm {r['nodes']} nodes" for r in rows[-3:]), flush=True)
    (out / "results.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
