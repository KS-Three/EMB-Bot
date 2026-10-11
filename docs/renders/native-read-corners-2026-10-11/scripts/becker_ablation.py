"""Becker reversals / right angles under hypothesis variants, on cached masks."""
import dataclasses
import pickle
import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(WT / "digitizer"), str(WT / "docs/renders/tracer-head-to-head-2026-10-10/scripts"),
                str(WT / "docs/renders/subpixel-res-gate-2026-10-11/scripts")]
from variants import spikes  # noqa: E402
from add_stairs import right_angles  # noqa: E402
from digitizer_core import stage4_vectorize as S4  # noqa: E402
from digitizer_core import subpixel as SP  # noqa: E402

S = Path(sys.argv[1])
widths = sys.argv[2].split(",")
names = sys.argv[3].split(",") if len(sys.argv) > 3 else None

orig_spc = S4.subpixel_contour


def variant(name):
    """-> (cfg overrides, patch fn or None)"""
    if name == "off":
        return {"subpixel_edges_upscaled": False}, None
    if name == "on":
        return {}, None
    if name == "nocurve":
        return {"curve_turn_deg": None}, None
    if name == "nofit":
        def spc(*a, **k):
            k["corner_fit"] = False
            return orig_spc(*a, **k)
        return {}, spc
    if name in ("noinh", "nofold", "noruns"):
        return {}, None
    if name.startswith("cfg:"):
        k, v = name[4:].split("=")
        return {k: (v == "1") if v in ("0", "1") else float(v)}, None
    raise ValueError(name)


def combo(name):
    kw, patch, consts = {}, None, {}
    for part in name.split("+"):
        if part.startswith("c:"):
            k, v = part[2:].split("=")
            consts[k] = float(v)
            continue
        k2, p2 = variant(part)
        kw.update(k2)
        patch = patch or p2
    return kw, patch, consts


for w in widths:
    cap = pickle.loads((S / f"becker_{w}.pkl").read_bytes())
    for name in names:
        kw, patch, consts = combo(name)
        saved = {k: getattr(SP, k) for k in consts}
        for k, v in consts.items():
            setattr(SP, k, v)
        if patch:
            S4.subpixel_contour = patch
        o_inh, o_fold, o_runs = SP._inherit_offsets, S4.drop_folds, SP._fit_corner_runs
        if "noinh" in name:
            SP._inherit_offsets = lambda *a, **k: None
        if "nofold" in name:
            S4.drop_folds = lambda p_, a_, c_, r_, s_: (p_, a_, c_)
        if "noruns" in name:
            SP._fit_corner_runs = lambda *a, **k: None
        try:
            regs = S4.vectorize(cap["masks"], cap["ti"], cap["p"], dataclasses.replace(cap["cfg"], **kw))[0]
        finally:
            S4.subpixel_contour = orig_spc
            SP._inherit_offsets, S4.drop_folds, SP._fit_corner_runs = o_inh, o_fold, o_runs
            for k, v in saved.items():
                setattr(SP, k, v)
        polys = [r.polygon for r in regs]
        nodes = sum(len(p.exterior.coords) - 1 + sum(len(i.coords) - 1 for i in p.interiors) for p in polys)
        print(f"w={w} {name:28s} rev {spikes(polys):5.2f}  right {right_angles(polys):6.2f}  nodes {nodes}", flush=True)
