"""Which stage 4 switch makes the spikes, and what does each one buy at low
resolution? Re-runs stages 0-3 for existing run dirs and calls vectorize on
the same masks under several configs.

usage: variants.py OUT_DIR RUN_DIR...
"""
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

import analyze as A
from digitizer_core import pipeline
from digitizer_core.config import PipelineConfig

VARIANTS = {
    "shipped": {},
    "no native read": {"subpixel_edges_upscaled": False},
    "no subpixel": {"subpixel_edges": False},
    "no curves": {"curve_turn_deg": None},
    "plain DP": {"subpixel_edges": False, "curve_turn_deg": None},
}


def spikes(polys):
    """Vertices turning more than 120 degrees, per 100 mm of boundary."""
    n, length = 0, 0.0
    for r in A.rings_of(polys):
        seg = np.diff(r, axis=0)
        ln = np.hypot(seg[:, 0], seg[:, 1])
        ok = ln > 1e-9
        seg, ln = seg[ok], ln[ok]
        if len(seg) < 3:
            continue
        ang = np.arctan2(seg[:, 1], seg[:, 0])
        d = np.diff(np.concatenate([ang, ang[:1]]))
        d = np.abs((d + np.pi) % (2 * np.pi) - np.pi)
        n += int((d > np.radians(120)).sum()); length += ln.sum()
    return 100.0 * n / length if length else 0.0


def run(d):
    meta = json.loads((d / "meta.json").read_text())
    src = d / "input.png" if (d / "input.png").exists() else Path(meta["src"])
    cap = {}
    orig = pipeline.vectorize

    def wrap(masks, ti, p, cfg):
        for name, kw in VARIANTS.items():
            cap[name] = orig(masks, ti, p, dataclasses.replace(cfg, **kw))[0]
        return orig(masks, ti, p, cfg)

    pipeline.vectorize = wrap
    kw = {"target_width_mm": 80.0}
    if meta["forced"] != "-":
        kw["forced_class"] = meta["forced"]
    try:
        pipeline.build_generation(str(src), PipelineConfig(**kw))
    finally:
        pipeline.vectorize = orig
    return meta, {k: [r.polygon for r in v] for k, v in cap.items()}


def main(out, *dirs):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    truths = {}
    A.NAMES.update({"M": "shipped", "A0": "no native read", "A": "no subpixel",
                    "B1": "no curves", "B2": "plain DP", "B3": "-"})
    for d in map(Path, dirs):
        meta, arms = run(d)
        fx, lane = d.name.split("-")[:2]
        tdir = d.parent / f"{fx}-{lane}-truth"
        print(f"\n{d.name}  (source {meta['input_px_per_mm']:.2f} px/mm, work {meta['px_per_mm']:.2f})")
        if tdir.exists():
            truth = truths.setdefault(tdir, A.Truth(tdir))
            base, _ = A.load_arms(d, meta)
            v = A.register(truth, A.sample(base["M"]))
            print(f"  {'variant':16s} p_med  p_p90  r_med   turn spikes/100mm nodes")
            for k, p in arms.items():
                q = A.apply(p, v)
                pr, rc = A.stats(truth.dist(A.sample(q))), A.stats(truth.recall(q))
                print(f"  {k:16s} {pr['med']:.3f}  {pr['p90']:.3f}  {rc['med']:.3f} {A.turning(q):6.1f} "
                      f"{spikes(q):8.1f} {sum(len(r) - 1 for r in A.rings_of(q)):7d}")
        else:
            print(f"  {'variant':16s}     -      -      -   turn spikes/100mm nodes")
            for k, p in arms.items():
                print(f"  {k:16s}     -      -      - {A.turning(p):6.1f} {spikes(p):8.1f} "
                      f"{sum(len(r) - 1 for r in A.rings_of(p)):7d}")
            lab = np.load(d / "labels.npy")
            b = np.zeros(lab.shape, bool)
            b[:, 1:] |= lab[:, 1:] != lab[:, :-1]; b[1:, :] |= lab[1:, :] != lab[:-1, :]
            win = A.densest(b, meta["px_per_mm"], meta["cx"], meta["cy"], 14, 9)
            A.panels(out, d.name + "-variants",
                     {"M": arms["shipped"], "A0": arms["no native read"], "A": arms["no subpixel"],
                      "B1": arms["no curves"], "B2": arms["plain DP"], "B3": None},
                     A.rgb_backdrop(d, meta, win, 40), win)


if __name__ == "__main__":
    main(*sys.argv[1:])
