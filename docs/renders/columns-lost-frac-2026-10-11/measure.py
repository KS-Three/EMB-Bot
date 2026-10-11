"""Per-logo, per-shape lost_frac split, lane OFF vs ON.

usage: python measure.py OUTDIR fixture[,fixture] [arm ...]
arms: off, on (both flags), cols (lettering_columns only)
Writes OUTDIR/<fixture>-<arm>.json (summary + per-region attribution) and
OUTDIR/<fixture>-<arm>.design.json.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import tools.artfidelity_self as afs  # noqa: E402
from tools.dropped_elements import analyse_design, RES  # noqa: E402
from tools.eye_pairs.features import base_cfg, digitize_once  # noqa: E402
from tools.thin_strokes import REAL_ART, ROOT  # noqa: E402
from digitizer_core.columns import is_lettering  # noqa: E402
from digitizer_core.stitchviz import _frame  # noqa: E402

ARMS = {"off": {}, "on": {"lettering_columns": True, "lettering_words": True},
        "cols": {"lettering_columns": True},
        "pullm": {"lettering_columns": True, "lettering_words": True},
        "nocap": {"lettering_columns": True, "lettering_words": True},
        "cov": {"lettering_columns": True, "lettering_words": True, "coverage_edges": True},
        "covcap": {"lettering_columns": True, "lettering_words": True, "coverage_edges": True},
        "covoff": {"coverage_edges": True}}


def _patch_pull(delta):
    import digitizer_core.columns as C
    orig = C.column_runs

    def wrapped(*a, **k):
        k["pull_mm"] = max(0.0, k.get("pull_mm", 0.0) - delta)
        return orig(*a, **k)
    C.column_runs = wrapped


def label_map(design, H, W):
    """shape index per pixel, drawn like render_design, placed on the H x W
    registration canvas the way artfidelity_self._place centres it."""
    st = design["stitches"]
    (h, w), to_px = _frame(st, RES, 2.0)
    lab = np.zeros((h, w), np.int32)
    shapes = [""]
    tw = max(2, int(round(0.4 * RES)))
    for r in design.get("runs", []):
        sid = r.get("shape") or ""
        if sid not in shapes:
            shapes.append(sid)
        k = shapes.index(sid)
        prev = None
        for i in range(r["i0"], r["i1"] + 1):
            s = st[i]
            if s.get("type") != "stitch":
                prev = None
                continue
            p = to_px(s)
            if prev is not None and prev != p:
                cv2.line(lab, prev, p, int(k), tw)
            prev = p
    canvas = np.zeros((H, W), np.int32)
    oy, ox = (H - h) // 2, (W - w) // 2
    canvas[oy:oy + h, ox:ox + w] = lab
    return canvas, shapes


def attribute(design, res, image):
    """Re-derive the lost regions with their pixel masks so each one can be
    named by the shape whose thread is on it (overshoot) or nearest it."""
    # Re-run the same registration analyse_design did, to get the canvas.
    ours_f = afs.stitch_coverage_field(design)
    art_f = afs.art_ink_field(image, float(design["widthMM"]))
    _, O_f, A_f, dx, dy = afs.register(ours_f, art_f)
    H, W = O_f.shape
    lab, shapes = label_map(design, H, W)
    # nearest labelled pixel for every pixel
    dist, idx = cv2.distanceTransformWithLabels(
        (lab == 0).astype(np.uint8), cv2.DIST_L2, 5,
        labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(lab)
    seed_lab = np.zeros(idx.max() + 1, np.int32)
    seed_lab[idx[ys, xs]] = lab[ys, xs]
    near = seed_lab[idx]
    out = []
    for x in res["_lost"]:
        y0, x0 = x["y"] if "y" in x else None, None
        out.append(x)
    return lab, near, shapes, (dx, dy)


def run(fixture, arm, outdir, fine):
    rel, width, garment = REAL_ART[fixture]
    image = ROOT / "testdata" / rel
    cfg = base_cfg(width, garment, **ARMS[arm])
    if arm == "pullm":
        _patch_pull(0.12)
    import digitizer_core.outline_cut as OC
    if not hasattr(OC, "_orig_cap"):
        OC._orig_cap = OC._cap_square_ends
    OC._cap_square_ends = (lambda st, *a, **k: st) if arm in ("nocap", "cov") else OC._orig_cap
    t = time.time()
    gen, result, plan, design = digitize_once(image, cfg)
    t_dig = time.time() - t
    for fine in (False, True):
        if fine:
            afs.SHIFT_STEP_MM, afs.SHIFT_MM = 0.1, 1.2
        else:
            afs.SHIFT_STEP_MM, afs.SHIFT_MM = _GRID
        _analyse(fixture, arm, outdir, fine, image, cfg, result, design, t_dig)


_GRID = (afs.SHIFT_STEP_MM, afs.SHIFT_MM)


def _analyse(fixture, arm, outdir, fine, image, cfg, result, design, t_dig):
    res = analyse_design(image, design)
    # pixel masks of the lost regions: recompute exactly as analyse_design
    from tools.dropped_elements import (art_colour_field, sewn_colour_field,
                                        disagreement, _components,
                                        MIN_ELEMENT_MM2)
    ours_f = afs.stitch_coverage_field(design)
    art_f = afs.art_ink_field(image, float(design["widthMM"]))
    _, O_f, A_f, dx, dy = afs.register(ours_f, art_f)
    H, W = O_f.shape
    art_rgb, art_ink = art_colour_field(image, float(design["widthMM"]))
    sewn_rgb = sewn_colour_field(design)

    def place(img, ddx, ddy, fill):
        shape = (H, W) + img.shape[2:]
        c = np.full(shape, fill, img.dtype)
        oy = (H - img.shape[0]) // 2 + int(round(ddy * RES))
        ox = (W - img.shape[1]) // 2 + int(round(ddx * RES))
        y0, x0 = max(0, oy), max(0, ox)
        y1, x1 = min(H, oy + img.shape[0]), min(W, ox + img.shape[1])
        c[y0:y1, x0:x1] = img[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        return c
    A_rgb = place(art_rgb, dx, dy, 255)
    A_ink = place(art_ink.astype(bool), dx, dy, False)
    S_rgb = place(sewn_rgb, 0, 0, 255)
    A_show = np.where(A_ink[..., None], A_rgb, np.uint8(255))
    _de, wrong = disagreement(A_show, S_rgb)
    min_px = max(1, int(round(MIN_ELEMENT_MM2 * RES * RES)))
    lab_c, comps = _components(wrong, min_px)
    thread = O_f >= 0.5

    lab, shapes = label_map(design, H, W)
    _d, idx = cv2.distanceTransformWithLabels(
        (lab == 0).astype(np.uint8), cv2.DIST_L2, 5,
        labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(lab)
    seed = np.zeros(int(idx.max()) + 1, np.int32)
    seed[idx[ys, xs]] = lab[ys, xs]
    near = seed[idx]

    letter_ids = {r.shape_id for r in result.regions if is_lettering(r, cfg)}
    regions = []
    for c in comps:
        sel = lab_c == c["label"]
        ink = bool(A_ink[sel].mean() > 0.5)
        cover = float(thread[sel].mean())
        kind = ("overshoot" if not ink else
                ("wrong_colour" if cover >= 0.5 else "unsewn"))
        vals, cnt = np.unique(near[sel], return_counts=True)
        sid = shapes[int(vals[np.argmax(cnt)])]
        yy, xx = np.nonzero(sel)
        regions.append({"mm2": round(sel.sum() / (RES * RES), 2), "kind": kind,
                        "shape": sid, "letter": sid in letter_ids,
                        "cx": int(xx.mean()), "cy": int(yy.mean()),
                        "bbox": [int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())]})
    # unfiltered per-shape reading too: thread outside ink (spill) and ink
    # without thread (bare), by nearest shape, in mm2
    per_shape = {}
    spill = thread & ~A_ink
    bare = A_ink & ~thread
    for name, m in (("spill", spill), ("bare", bare)):
        v, cnt = np.unique(near[m], return_counts=True)
        for k, n in zip(v, cnt):
            per_shape.setdefault(shapes[int(k)], {})[name] = round(n / (RES * RES), 2)
    summary = {k: res[k] for k in ("lost_frac", "unsewn_frac", "wrong_colour_frac",
                                   "overshoot_frac", "lost_mm2", "unsewn_mm2",
                                   "wrong_colour_mm2", "overshoot_mm2",
                                   "uncovered_ink_frac", "uncovered_elements",
                                   "shift_x_mm", "shift_y_mm")}
    summary["widthMM"] = design["widthMM"]
    summary["stitches"] = sum(1 for s in design["stitches"] if s.get("type") == "stitch")
    summary["trims"] = sum(1 for s in design["stitches"] if s.get("type") == "trim")
    summary["sum_check"] = round(sum(r["mm2"] for r in regions), 1)
    summary["t_digitize_s"] = round(t_dig, 1)
    letters = {}
    for r in result.regions:
        if r.shape_id in letter_ids:
            letters[r.shape_id] = {"wkt": r.polygon.wkt, "area": round(r.polygon.area, 3)}
    tag = f"{fixture}-{arm}{'-fine' if fine else ''}"
    with open(os.path.join(outdir, tag + ".json"), "w") as f:
        json.dump({"summary": summary, "regions": regions, "per_shape": per_shape,
                   "letters": letters, "frame": [H, W, dx, dy]}, f, indent=1)
    with open(os.path.join(outdir, f"{fixture}-{arm}.design.json"), "w") as f:
        json.dump(design, f)
    print(tag, json.dumps(summary), flush=True)


if __name__ == "__main__":
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    fine = "--fine" in sys.argv
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    fixtures = args[0].split(",")
    arms = args[1:] or ["off", "on"]
    for fx in fixtures:
        for arm in arms:
            run(fx, arm, outdir, False)
