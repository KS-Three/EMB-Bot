"""Truth-case edge error / reversals / right angles under variants, on the
rung inputs gate_table.py already wrote. usage: truth_ablate.py RUNS CASES VARIANTS"""
import dataclasses
import pickle
import re
import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(WT / "docs/renders/subpixel-res-gate-2026-10-11/scripts")]
import gate_table as G  # noqa: E402
import add_stairs  # noqa: E402
from digitizer_core import stage4_vectorize as S4  # noqa: E402
from digitizer_core import subpixel as SP  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402

runs = Path(sys.argv[1])
cases = sys.argv[2].split(",")       # e.g. fremont-gradient-r1.8
names = sys.argv[3].split(",")
O = dict(inh=SP._inherit_offsets, fold=S4.drop_folds, runs=SP._fit_corner_runs,
         reach=SP.CORNER_RUN_REACH_PX, sup=SP.CORNER_RUN_SUPPORT_PX, im=SP.CORNER_INHERIT_STEPS_MULT)


def apply(name):
    if "noinh" in name:
        SP._inherit_offsets = lambda *a, **k: None
    if "nofold" in name:
        S4.drop_folds = lambda p_, a_, c_, r_, s_: (p_, a_, c_)
    if "noruns" in name:
        SP._fit_corner_runs = lambda *a, **k: None
    if "oldfit" in name:
        SP._fit_corner_runs = SP._fit_corners
    m2 = re.search(r"inh([0-9.]+)", name)
    if m2:
        SP.CORNER_INHERIT_STEPS_MULT = float(m2.group(1))
    m = re.search(r"reach([0-9.]+)", name)
    if m:
        SP.CORNER_RUN_REACH_PX = float(m.group(1))


def restore():
    SP._inherit_offsets, S4.drop_folds, SP._fit_corner_runs = O["inh"], O["fold"], O["runs"]
    SP.CORNER_RUN_REACH_PX, SP.CORNER_RUN_SUPPORT_PX, SP.CORNER_INHERIT_STEPS_MULT = O["reach"], O["sup"], O["im"]


for case in cases:
    fx, lane, rung = case.rsplit("-", 2)
    d = runs / case
    cache = d / "_cap.pkl"
    if cache.exists():
        cap = pickle.loads(cache.read_bytes())
    else:
        G.CONFIGS = {"on": {}}
        cap = {}
        orig = G.pipeline.vectorize

        def wrap(masks, ti, p, c):
            cap.update(masks=masks, ti=ti, p=p, cfg=c)
            return orig(masks, ti, p, c)
        G.pipeline.vectorize = wrap
        try:
            G.pipeline.build_generation(str(d / "input.png"), PipelineConfig(target_width_mm=G.W_MM, forced_class=lane))
        finally:
            G.pipeline.vectorize = orig
        cache.write_bytes(pickle.dumps(cap))
    truth = G.A.Truth(runs / f"{fx}-{lane}-truth")
    on = [r.polygon for r in S4.vectorize(cap["masks"], cap["ti"], cap["p"], cap["cfg"])[0]]
    v = G.A.register(truth, G.mask_outline(cap["masks"], G.kept(cap["masks"], cap["p"], on, runs / "_tmp"), cap["p"]))
    for name in names:
        kw = {} if name.startswith("on") else {"subpixel_corner_runs": True}
        apply(name)
        try:
            polys = [r.polygon for r in S4.vectorize(cap["masks"], cap["ti"], cap["p"], dataclasses.replace(cap["cfg"], **kw))[0]]
        finally:
            restore()
        q = G.A.apply(polys, v)
        pr = G.A.stats(truth.dist(G.A.sample(q)))
        print(f"{case:24s} {name:22s} p_med {pr['med']:.4f}  rev {G.spikes(q):5.2f}  right {add_stairs.right_angles(q):6.2f}", flush=True)
