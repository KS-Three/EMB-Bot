#!/usr/bin/env python
"""Why does a small sewn glyph still read wrong? A per-glyph trace of the thread.

`small_text_true_size` ON (the switch) takes Fremont's 81 mm Hat "1895" to
0.916 legibility with 3 of 3 counters open, and the OCR still reads two of
four: the 1 reads F and the 5 reads A. `tools/glyph_legibility.py` says WHICH
glyph is wrong and by how much; it cannot say which construction step laid the
thread that makes it wrong. This tool can. It measures only: no engine file is
edited and nothing is flagged.

For a named glyph of a digitized design it reports

  * the TIER that sewed it (bean letter / skeleton run / satin / run outline /
    fill), read from the shapes whose region owns the glyph (#905's rule) and
    from a spy on the two tier functions;
  * its SOURCE box against the SEWN box (needle points, and thread = points
    plus half a thread width);
  * the source skeleton the bean tier was handed, spine by spine: raw length,
    the slab-serif hook cut off a free end (`bean_letter_serif_mm`), whether the
    arm survived the floors (`bean_letter_stitch_mm`, `bean_letter_min_arm_mm`),
    the corner stations (`bean_letter_corner_deg`, #946);
  * every NEEDLE POINT within a millimetre of the glyph that lies off the
    source ink (distance in mm), and which construction step put it there:
    a bean leg station, a #946 corner station, a lock stitch (`apply_ties`),
    a sewn travel hop between runs, or a point nothing recorded;
  * every stretch of THREAD (a segment between two needle points) that leaves
    the ink, with the same attribution, because a needle point on the
    centreline can still lay a chord across a bay;
  * the BAY / GAP area: the concavities of the source glyph (a morphological
    closing minus the glyph), and the gap strip to each neighbour, bare in the
    source by definition, then how much of each the thread covers, split by
    the step that laid the covering thread;
  * the glyph's own OCR read and legibility row (`glyph_legibility`), so the
    trace sits beside the number it explains;
  * a zoomed render: source with its skeleton, the thread with numbered
    stations and the points off the ink, and the bay map.

What it is NOT. Not a sew-out (ROADMAP gate 1): a render has no pull, no push
and no nap, and the thread is a line of `thread_profile(cfg.thread_wt)` width.
Not a verdict on a fix: it names a cause per glyph and stops. Distances and
areas are candidates for a follow-on lane to size against, never constants.

    # one cell: digitizes (a few minutes), pickles the run, writes the table + renders
    .venv/Scripts/python -m tools.bean_glyph_trace --cell hat81 --out DIR --renders DIR2
    # the same cell again, from the pickle (no digitizing)
    .venv/Scripts/python -m tools.bean_glyph_trace --cell hat81 --out DIR --renders DIR2 --reuse
    # another glyph: WORD:CHAR (WORD is a fremont_triage.ROIS key), CHAR/n the n-th match
    .venv/Scripts/python -m tools.bean_glyph_trace --cell hat925 --glyph the:E --glyph tagline:S
    .venv/Scripts/python -m tools.bean_glyph_trace --list-glyphs hat81   # indices and labels
    # cells: hat81 (81 mm Hat), hat925 (92.5 mm Hat), patch925 (92.5 mm, garment patch)
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# cell -> (width mm, PipelineConfig overrides on the Studio request)
CELLS = {
    "hat81": (81.0, {}),
    "hat925": (92.5, {}),
    "patch925": (92.5, {"garment_id": "patch"}),
}
ARMS = {
    "switch": {"small_text_true_size": True},
    "main": {},
}
# The glyphs the lane was asked about, per cell.
DEFAULT_GLYPHS = {
    "hat81": ["1895:1", "1895:5"],
    "hat925": ["1895:1", "1895:5", "the:E", "tagline:S"],
    "patch925": ["1895:1", "1895:5", "the:E", "tagline:S"],
}
# What each word's source components should spell, left to right; used only to
# LABEL components, and only when the count agrees.
WORD_TEXT = {"est": "EST", "1895": "1895", "the": "THE", "tagline": "EAT|STAY|PLAY"}

RASTER_PPM = 60.0          # px/mm of the coverage rasters
RENDER_PPM = 110.0         # px/mm of the zoomed renders
ZONE_MM = 1.0              # an event within this of a glyph is "in its zone"
TOL_MM = 0.05              # a needle point / thread this far off the ink is "outside"
BAY_CLOSE_MM = 0.45        # closing radius that defines a bay of the source glyph
MIN_BAY_MM2 = 0.01         # a bay smaller than this is the contour's roughness
OPEN_SHARE = 0.5           # #905's rule: a bay or counter this bare is open
BRIDGE_GAP_MM = 0.15        # a bare gap this narrow between two threads is no slit
SAMPLE_MM = 0.02           # step along a thread segment when measuring excursions

# Step labels (the construction step that put a needle point or segment there).
L_BEAN = "bean leg"
L_CORNER = "bean leg at a #946 corner station"
L_TIE = "lock stitch (apply_ties)"
L_HOP = "sewn travel hop between runs"
L_OTHER = "needle point nothing recorded"
L_FOREIGN = " (a neighbour letter's run)"
L_NONLETTER = " (a shape that is no letter of the word)"
COMP_TOL_MM = 0.5          # the instrument's push-compensation tolerance (glyph_read.COMP_TOL_MM)
OCR_P = 20.0               # px/mm of the OCR masks (glyph_legibility works on a 20 px/mm grid)


def _stitches():
    from digitizer_core import stitches
    return stitches


# --- digitizing: the cell, with the tier functions spied ---------------------------


@contextlib.contextmanager
def spy_tiers(bean: dict, skel: dict):
    """Record every call stage 7 makes to the bean-letter and skeleton tiers:
    {shape_id: [call, ...]}. A call keeps the spines it was handed, the points
    of the runs it returned (copied, since `apply_ties` later rewrites the
    runs in place) and its report. The runs are returned untouched."""
    from digitizer_core import stage7_sequence as s7
    real_bean, real_sk = s7.bean_letter, s7.skeleton_letter_runs

    def spy_bean(spines, shape_id, **kw):
        runs, report = real_bean(spines, shape_id, **kw)
        bean.setdefault(shape_id, []).append({
            "spines": [[tuple(p) for p in s] for s in (spines or [])],
            "kw": {k: v for k, v in kw.items() if k != "entry"},
            "entry": kw.get("entry"),
            "runs": [{"points": [tuple(p) for p in r.points], "jump": r.jump, "trim": r.trim} for r in runs],
            "report": dict(report)})
        return runs, report

    def spy_sk(poly, shape_id, **kw):
        runs, report = real_sk(poly, shape_id, **kw)
        skel.setdefault(shape_id, []).append({"report": dict(report), "runs": len(runs)})
        return runs, report
    s7.bean_letter, s7.skeleton_letter_runs = spy_bean, spy_sk
    try:
        yield
    finally:
        s7.bean_letter, s7.skeleton_letter_runs = real_bean, real_sk


def digitize(cell: str, arm: str) -> dict:
    """Digitize one cell the way /digitize does (`fremont_triage.run_arm`),
    tier functions spied. -> the run dict, plus `bean`, `skel`, `cell`, `arm`."""
    from tools import fremont_triage as ft
    width, cell_over = CELLS[cell]
    overrides = {**ARMS[arm], **cell_over}
    bean: dict = {}
    skel: dict = {}
    t = time.time()
    with spy_tiers(bean, skel):
        run = ft.run_arm(f"{cell}__{arm}", width, None, preflight=False, overrides=overrides)
    run["bean"], run["skel"] = bean, skel
    run["cell"], run["arm"], run["overrides"] = cell, arm, overrides
    run["width_mm"] = width
    run["digitize_secs"] = round(time.time() - t)
    return run


def load_run(cell: str, arm: str, out: Path, reuse: bool) -> dict:
    pk = out / f"{cell}__{arm}.pkl"
    if reuse and pk.exists():
        return pickle.loads(pk.read_bytes())
    run = digitize(cell, arm)
    out.mkdir(parents=True, exist_ok=True)
    pk.write_bytes(pickle.dumps(run))
    return run


# --- geometry helpers ---------------------------------------------------------------


def dist_to(glyph, xy):
    """Distance (mm) from each of the points `xy` (N x 2) to the ink polygon
    `glyph`: 0 inside the ink, positive in a counter or off the letter."""
    import numpy as np
    xy = np.asarray(xy, float).reshape(-1, 2)
    if not len(xy):
        return np.zeros(0)
    try:
        import shapely
        return np.asarray(shapely.distance(glyph, shapely.points(xy)), float)
    except AttributeError:      # shapely 1.x
        from shapely.geometry import Point
        return np.array([glyph.distance(Point(float(x), float(y))) for x, y in xy])


def word_glyphs(p, word: str) -> list:
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft
    return fsl.source_glyphs(p, ft.ROIS[word])


def labels_for(word: str, n: int) -> list[str]:
    text = WORD_TEXT.get(word, "")
    return list(text) if len(text) == n else [f"#{i}" for i in range(n)]


def pick_glyph(spec: str, glyphs: list, word: str) -> int:
    """`CHAR`, `CHAR/n` (n-th match, 1-based) or `#i` -> a glyph index."""
    labels = labels_for(word, len(glyphs))
    if spec.startswith("#"):
        return int(spec[1:])
    ch, _, nth = spec.partition("/")
    hits = [i for i, lab in enumerate(labels) if lab == ch]
    k = int(nth) - 1 if nth else 0
    if not hits or k >= len(hits):
        raise SystemExit(f"no glyph {spec!r} in {word!r}: {len(glyphs)} components, labels {labels} "
                         "(use WORD:#index when the count does not match the word)")
    return hits[k]


def _mask(geoms, box, ppm=RASTER_PPM):
    from tools import fremont_small_lettering as fsl
    return fsl._mask(geoms, box, ppm)


def _fill_mask(glyph, box, ppm=RASTER_PPM):
    """The glyph with its counters filled."""
    from shapely.geometry import Polygon
    return _mask([Polygon(glyph.exterior)], box, ppm)


def bays_of(glyph, box, ppm=RASTER_PPM, close_mm=BAY_CLOSE_MM):
    """Concavities of the source glyph, as (label array, [component dict]): the
    morphological closing of the glyph with its counters filled, minus that
    filled glyph. A closing never reaches past the convex hull, so every bay
    lies inside the glyph's own bounding box."""
    import cv2
    import numpy as np
    filled = _fill_mask(glyph, box, ppm)
    r = max(1, int(round(close_mm * ppm)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    pad = r + 2
    padded = cv2.copyMakeBorder(filled, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    closed = cv2.morphologyEx(padded, cv2.MORPH_CLOSE, k)[pad:-pad, pad:-pad]
    bay = (closed > 0) & (filled == 0)
    n, lab = cv2.connectedComponents(bay.astype(np.uint8), connectivity=8)
    x0, y0, x1, y1 = box
    gx0, gy0, gx1, gy1 = glyph.bounds
    comps = []
    out = np.zeros_like(lab)
    for i in range(1, n):
        m = lab == i
        area = float(m.sum()) / ppm ** 2
        if area < MIN_BAY_MM2:
            continue
        ys, xs = np.nonzero(m)
        cx, cy = x0 + xs.mean() / ppm, y0 + ys.mean() / ppm
        fx = (cx - gx0) / max(gx1 - gx0, 1e-9)
        fy = (cy - gy0) / max(gy1 - gy0, 1e-9)
        out[m] = len(comps) + 1
        comps.append({"id": len(comps) + 1, "mm2": round(area, 3),
                      "where": f"{'top' if fy < 1 / 3 else 'bottom' if fy > 2 / 3 else 'middle'}-"
                               f"{'left' if fx < 1 / 3 else 'right' if fx > 2 / 3 else 'centre'}",
                      "centre_mm": [round(cx, 2), round(cy, 2)]})
    return out, comps


# --- the thread, event by event ------------------------------------------------------


def _tie_counts(pts: list) -> tuple[int, int]:
    """(leading, trailing) point counts of `apply_ties`' folded-in lock stitch:
    a bounce between exactly two coordinates (`stitches.strip_ties`' own
    detection, one lock at each end)."""
    lead = tail = 0
    n = len(pts)
    if n >= 5 and pts[0] == pts[2] and pts[1] == pts[3]:
        lead = 4
    if n - lead >= 5 and pts[-1] == pts[-3] and pts[-2] == pts[-4]:
        tail = 4
    return lead, tail


def _near(p, coords, tol=1e-6) -> bool:
    return any(abs(p[0] - c[0]) <= tol and abs(p[1] - c[1]) <= tol for c in coords)


def trimmed_spines(spines, cfg):
    from digitizer_core import stage6_beanletter as bl
    return bl.trim_serif_hooks([list(map(tuple, s)) for s in spines], cfg.bean_letter_serif_mm)


def recorded_points(calls: list) -> set:
    return {(round(x, 6), round(y, 6)) for c in calls for r in c["runs"] for (x, y) in r["points"]}


def corner_points(calls: list, cfg) -> list:
    """The corner stations `bean_letter` placed (`_corners` on each trimmed spine)."""
    from digitizer_core import stage6_beanletter as bl
    if not cfg.bean_letter_corner_deg or not calls:
        return []
    out = []
    for sp in trimmed_spines(calls[-1]["spines"], cfg):
        if len(sp) >= 3:
            out.extend(sp[i] for i in bl._corners(sp, cfg.bean_letter_corner_deg))
    return out


def build_events(run: dict) -> dict:
    """The thread of the whole design as a list of needle points and a list of
    thread segments, every one labelled with the construction step.

    -> {"points": [{x, y, run, i, shape, kind, label}], "segments": [{a, b, run, shape,
        kind, label, owner_label}], "runs": [...]}. White (ground) thread is left
    out, as `fremont_triage` leaves it: the letters are tan or black on a white
    patch that sews as one fill under everything."""
    from tools import fremont_triage as ft
    st = _stitches()
    plan, cfg = run["plan"], run["cfg"]
    corners = {sid: corner_points(calls, cfg) for sid, calls in run["bean"].items()}
    stations = {sid: recorded_points(calls) for sid, calls in run["bean"].items()}
    pts_out, segs_out, runs_out = [], [], []
    ridx = -1
    for bi, b in enumerate(plan.blocks):
        prev = None                       # the needle's last position in this block, None after a break
        white = min(b.rgb) >= ft.WHITE_MIN
        for r in b.runs:
            ridx += 1
            if not r.points:
                continue
            pts = [tuple(p) for p in r.points]
            lead, tail = _tie_counts(pts) if r.kind != st.TIE else (len(pts), 0)
            rec_jump = None
            if r.shape_id in run["bean"] and lead < len(pts):
                for c in run["bean"][r.shape_id]:
                    for rr in c["runs"]:
                        if rr["points"] and math.dist(rr["points"][0], pts[lead]) < 1e-6:
                            rec_jump = bool(rr["jump"])
            rec = {"run": ridx, "block": bi, "recorded_jump": rec_jump,
                   "shape": r.shape_id, "kind": r.kind, "jump": bool(r.jump),
                   "trim": bool(r.trim), "n": len(pts), "lead_tie": lead, "tail_tie": tail,
                   "white": white, "first": pts[0], "last": pts[-1],
                   "lead_leg": math.dist(pts[0], pts[1]) if lead and len(pts) > 1 else None,
                   "tail_leg": math.dist(pts[-1], pts[-2]) if tail else None}
            runs_out.append(rec)
            if r.trim or (r.jump and prev is not None):
                prev = None
            hop_from = prev if (prev is not None and not r.jump) else None
            labels = []
            for i, pt in enumerate(pts):
                if i < lead or i >= len(pts) - tail:
                    lab = L_TIE
                elif r.shape_id in stations:
                    key = (round(pt[0], 6), round(pt[1], 6))
                    if key in stations[r.shape_id]:
                        lab = L_CORNER if _near(pt, corners.get(r.shape_id, [])) else L_BEAN
                    else:
                        lab = L_OTHER
                else:
                    lab = f"{r.kind} run"
                labels.append(lab)
                if not white:
                    pts_out.append({"x": pt[0], "y": pt[1], "run": ridx, "i": i, "shape": r.shape_id,
                                    "kind": r.kind, "label": lab})
            if not white:
                if hop_from is not None and math.dist(hop_from, pts[0]) >= st.SAME_POINT_MM:
                    segs_out.append({"a": hop_from, "b": pts[0], "run": ridx, "shape": r.shape_id,
                                     "kind": r.kind, "label": L_HOP})
                for i in range(1, len(pts)):
                    if math.dist(pts[i - 1], pts[i]) < st.SAME_POINT_MM:
                        continue
                    if i - 1 < lead or i - 1 >= len(pts) - tail - 1 and tail:
                        lab = L_TIE
                    else:
                        la, lb = labels[i - 1], labels[i]
                        lab = L_CORNER if L_CORNER in (la, lb) else lb if la == lb else (
                            L_OTHER if L_OTHER in (la, lb) else lb)
                    segs_out.append({"a": pts[i - 1], "b": pts[i], "run": ridx, "shape": r.shape_id,
                                     "kind": r.kind, "label": lab})
            prev = pts[-1]
    return {"points": pts_out, "segments": segs_out, "runs": runs_out}


# --- one glyph ------------------------------------------------------------------------


def spine_table(spines: list, cfg) -> list[dict]:
    """The source skeleton the bean tier was handed, spine by spine, with what
    `bean_letter` does to each before sewing (re-derived from its own helpers;
    `check_spines` asserts the sewn count against the tier's report)."""
    from digitizer_core import stage6_beanletter as bl
    raw = [[tuple(p) for p in s] for s in spines]
    cut = bl.trim_serif_hooks(raw, cfg.bean_letter_serif_mm)
    stitch_mm = cfg.bean_letter_stitch_mm
    arm_floor = stitch_mm if stitch_mm and stitch_mm > 0 else bl._MIN_ARM_MM
    out = []
    for i, (a, b) in enumerate(zip(raw, cut)):
        la, lb = bl._length(a), bl._length(b)
        n = bl._length(b)
        free0 = not bl._attached(b[0], i, cut)
        free1 = not bl._attached(b[-1], i, cut)
        sews = len(b) >= 2 and (n >= arm_floor or bool(
            cfg.bean_letter_min_arm_mm and cfg.bean_letter_min_arm_mm > 0 and n >= cfg.bean_letter_min_arm_mm
            and not (not free0 and not free1)))
        out.append({"spine": i, "raw_mm": round(la, 3), "after_hook_cut_mm": round(lb, 3),
                    "hook_cut_mm": round(la - lb, 3), "free_ends": int(free0) + int(free1),
                    "corners": len(bl._corners(b, cfg.bean_letter_corner_deg)) if cfg.bean_letter_corner_deg and len(b) >= 3 else 0,
                    "start_mm": [round(b[0][0], 2), round(b[0][1], 2)],
                    "end_mm": [round(b[-1][0], 2), round(b[-1][1], 2)],
                    "sews": bool(sews)})
    return out


def check_spines(table: list, calls: list) -> bool:
    """The re-derived sewn count against what the tier reported (last call)."""
    if not calls:
        return True
    return sum(1 for t in table if t["sews"]) == calls[-1]["report"].get("strokes", 0) or not any(
        t["sews"] for t in table)


def thread_holes(glyph, glyphs, idx, box, all_thread, run_masks) -> list[dict]:
    """Bare areas the thread ENCLOSES near this glyph, each tagged as a source
    counter (its centroid lies in one of the glyph's counters) or SPURIOUS (a
    false counter: thread closed a bay or a gap into a ring), with the runs
    whose thread bounds it and the narrowest gap between them. This is the
    instrument's Euler read made attributable: `glyph_legibility` says a hole
    appeared, not whose thread closed it.

    Two readings. STRICT: the thread mask as drawn. BRIDGED: every bare gap
    under `BRIDGE_GAP_MM` closed first. A 0.4 mm filament leaves no visible
    slit that narrow on cloth, and the instrument's 20 px/mm render closes it
    or not by a pixel's rounding (THE's E at 92.5 mm: the top arm's serif tick
    ends 0.12 mm short of the middle arm; the instrument's render touches, a
    60 px/mm one does not). A hole that only exists bridged says `bridged`."""
    import cv2
    import numpy as np
    from scipy import ndimage as ndi
    from shapely.geometry import Point, Polygon
    r_b = max(1, int(round(BRIDGE_GAP_MM / 2.0 * RASTER_PPM)))
    bridged = cv2.dilate(all_thread, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r_b + 1, 2 * r_b + 1)))
    gx0, gy0, gx1, gy1 = glyph.bounds
    counters = [Polygon(r) for r in glyph.interiors]
    others = [g for j, g in enumerate(glyphs) if j != idx]
    out = []
    seen = []
    for reading, mask in (("strict", all_thread), ("bridged", bridged)):
        bare = (mask == 0).astype(np.uint8)
        n, lab = cv2.connectedComponents(bare, connectivity=4)
        edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
        for i in range(1, n):
            if i in edge:
                continue
            m = lab == i
            area = float(m.sum()) / RASTER_PPM ** 2
            if area < 0.004:
                continue
            ys, xs = np.nonzero(m)
            cx, cy = box[0] + xs.mean() / RASTER_PPM, box[1] + ys.mean() / RASTER_PPM
            c = Point(cx, cy)
            if not (gx0 - 0.1 <= cx <= gx1 + 0.1 and gy0 - 0.1 <= cy <= gy1 + 0.1):
                continue
            if any(g.contains(c) for g in others) or glyph.distance(c) > min([g.distance(c) for g in others] + [9.0]):
                continue
            if reading == "bridged" and any(math.dist((cx, cy), s) < 0.3 for s in seen):
                continue                      # the same hole, already found strict
            seen.append((cx, cy))
            ring = cv2.dilate(m.astype(np.uint8), np.ones((2 * r_b + 5, 2 * r_b + 5), np.uint8)) > 0
            touch = []
            for rid, rm in run_masks.items():
                k = int(((rm["mask"] > 0) & ring).sum())
                if k:
                    top = sorted(rm["labels"], key=lambda q: -rm["labels"][q])
                touch.append({"run": rid, "shape": rm["shape"], "label": " + ".join(top[:2]), "touching_px": k})
            touch.sort(key=lambda r: -r["touching_px"])
            pinch = None
            top = touch[:4]
            for p_i in range(len(top)):
                for q_i in range(p_i + 1, len(top)):
                    ma, mb = run_masks[top[p_i]["run"]]["mask"] > 0, run_masks[top[q_i]["run"]]["mask"] > 0
                    if ma.any() and mb.any() and not (ma & mb).any():
                        d = float(ndi.distance_transform_edt(~mb)[ma].min()) / RASTER_PPM
                        if pinch is None or d < pinch["gap_mm"]:
                            pinch = {"runs": [top[p_i]["run"], top[q_i]["run"]], "gap_mm": round(d, 3)}
            out.append({"source_counter": bool(any(cp.contains(c) for cp in counters)), "reading": reading,
                        "mm2": round(area, 3), "centre_mm": [round(cx, 2), round(cy, 2)],
                        "in_source_ink": bool(glyph.contains(c)), "bounded_by": touch[:5],
                        "narrowest_gap_between_bounding_runs": pinch})
    return out


def trace_glyph(run: dict, word: str, idx: int, glyphs: list, ev: dict, owners: dict,
                gl_read: tuple | None = None, ocr: bool = True) -> dict:
    """Everything about one source glyph. `ev`: `build_events`; `gl_read`: `gl_read_word`."""
    gl_rows, gl_dbg = gl_read if gl_read else (None, None)
    import cv2
    import numpy as np
    from shapely.geometry import Point
    from digitizer_core import machine
    from tools import fremont_small_lettering as fsl
    from tools import fremont_triage as ft

    cfg, plan, result = run["cfg"], run["plan"], run["result"]
    prof = machine.thread_profile(cfg.thread_wt)
    thread = prof.width_mm
    glyph = glyphs[idx]
    mine = set(owners[idx])
    labels = labels_for(word, len(glyphs))
    gx0, gy0, gx1, gy1 = glyph.bounds
    pad = ZONE_MM + 0.5
    box = (gx0 - pad, gy0 - pad, gx1 + pad, gy1 + pad)
    zone = glyph.buffer(ZONE_MM)

    # which shapes, which tier
    regions = [r for r in result.regions if r.shape_id in mine]
    reg_rows = []
    for r in regions:
        m = r.meta or {}
        inter = r.polygon.intersection(glyph).area
        reg_rows.append({
            "shape_id": r.shape_id, "area_mm2": round(r.polygon.area, 3),
            "bounds_mm": [round(v, 2) for v in r.polygon.bounds],
            "overlap_of_glyph": round(inter / glyph.area, 3),
            "polygon_off_ink_mm2": round(r.polygon.difference(glyph).area, 3),
            "restored": bool(m.get("small_text_restored")),
            "bean_spines": len(m.get("bean_letter_spines") or []),
            "ink_stroke_mm": m.get("ink_stroke_mm"),
            "text_candidate": bool(m.get("text_candidate")),
        })
    built = "outline"
    for sid in mine:
        if any(not c["report"].get("empty") for c in run["bean"].get(sid, [])):
            built = "bean"
            break
        if any(not c["report"].get("empty") for c in run["skel"].get(sid, [])):
            built = "skeleton"
    kinds = sorted({e["kind"] for e in ev["runs"] if e["shape"] in mine and not e["white"]})
    tier = {"bean": "bean letter", "skeleton": "skeleton run"}.get(built) or (
        "satin" if _stitches().SATIN in kinds else "fill" if _stitches().FILL in kinds
        else "run outline" if kinds else "none")

    # the skeleton the bean tier was handed, per owner shape
    spines = []
    for sid in sorted(mine):
        calls = run["bean"].get(sid, [])
        if calls:
            for row in spine_table(calls[-1]["spines"], cfg):
                row["shape_id"] = sid
                spines.append(row)
    sewn_report = {sid: run["bean"][sid][-1]["report"] for sid in sorted(mine) if sid in run["bean"]}

    # events in this glyph's zone. A needle point is OFF THE INK when it is
    # more than TOL_MM from this glyph's ink (its own runs) or, for a run that
    # is not this glyph's, from every glyph of the word and nearer this glyph
    # than any other: a neighbour's thread inside the neighbour's own ink is
    # the neighbour's business, not this glyph's.
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    letter_ids = {sid for ids in owners.values() for sid in ids}
    word_ink = unary_union(glyphs)
    others = unary_union([g for j, g in enumerate(glyphs) if j != idx]) if len(glyphs) > 1 else None

    def suffix(shape: str) -> str:
        return "" if shape in mine else (L_FOREIGN if shape in letter_ids else L_NONLETTER)

    def measure(xy):
        d_own = dist_to(glyph, xy)
        d_all = dist_to(word_ink, xy)
        d_oth = dist_to(others, xy) if others is not None else np.full(len(xy), np.inf)
        return d_own, d_all, d_oth

    pt_rows, outside_pts = [], []
    zx0, zy0, zx1, zy1 = zone.bounds
    cand = [e for e in ev["points"] if zx0 <= e["x"] <= zx1 and zy0 <= e["y"] <= zy1]
    if cand:
        xy = np.array([[e["x"], e["y"]] for e in cand])
        d_own, d_all, d_oth = measure(xy)
        for k, e in enumerate(cand):
            if not zone.covers(Point(*xy[k])):
                continue
            owner = e["shape"] in mine
            off = bool(d_own[k] > TOL_MM) if owner else bool(d_all[k] > TOL_MM and d_own[k] <= d_oth[k])
            row = {**e, "label": e["label"] + suffix(e["shape"]), "d_mm": float(d_own[k] if owner else d_all[k]),
                   "owner": owner, "off_ink": off,
                   "on_neighbour_ink": bool(owner and d_own[k] > TOL_MM and d_oth[k] <= 1e-9)}
            pt_rows.append(row)
            if off:
                outside_pts.append(row)
    owner_pts = [r for r in pt_rows if r["owner"]]
    non_tie = [r for r in owner_pts if r["label"] != L_TIE]
    needle_bbox = ([min(r["x"] for r in non_tie), min(r["y"] for r in non_tie),
                    max(r["x"] for r in non_tie), max(r["y"] for r in non_tie)] if non_tie else None)
    # the stations of the glyph's own runs in sew order: one row per distinct position
    stations: dict = {}
    for r in owner_pts:
        key = (round(r["x"], 4), round(r["y"], 4))
        s_ = stations.setdefault(key, {"x": round(r["x"], 3), "y": round(r["y"], 3), "d_mm": round(r["d_mm"], 3),
                                       "labels": [], "visits": 0, "first_run": r["run"]})
        s_["visits"] += 1
        if r["label"] not in s_["labels"]:
            s_["labels"].append(r["label"])
    station_rows = [{"n": i + 1, **v} for i, v in enumerate(stations.values())]

    # segments in this glyph's zone: excursions off the ink, and the thread itself, per step
    seg_rows, thread_masks, run_masks = [], {}, {}
    W = int(math.ceil((box[2] - box[0]) * RASTER_PPM)) + 1
    H = int(math.ceil((box[3] - box[1]) * RASTER_PPM)) + 1
    tpx = max(1, int(round(thread * RASTER_PPM)))

    def px(pt):
        return (int(round((pt[0] - box[0]) * RASTER_PPM)), int(round((pt[1] - box[1]) * RASTER_PPM)))
    for s in ev["segments"]:
        a, b = s["a"], s["b"]
        if max(a[0], b[0]) < zx0 or min(a[0], b[0]) > zx1 or max(a[1], b[1]) < zy0 or min(a[1], b[1]) > zy1:
            continue
        if not zone.intersects(LineString([a, b])):
            continue
        L = math.dist(a, b)
        n = max(2, int(math.ceil(L / SAMPLE_MM)) + 1)
        t = np.linspace(0.0, 1.0, n)
        xy = np.stack([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], 1)
        d_own, d_all, d_oth = measure(xy)
        owner = s["shape"] in mine
        lab = s["label"] + suffix(s["shape"])
        m = thread_masks.setdefault(lab, np.zeros((H, W), np.uint8))
        cv2.line(m, px(a), px(b), 1, tpx)
        rm = run_masks.setdefault(s["run"], {"labels": {}, "shape": s["shape"], "kind": s["kind"],
                                             "mask": np.zeros((H, W), np.uint8)})
        rm["labels"][lab] = rm["labels"].get(lab, 0) + 1
        cv2.line(rm["mask"], px(a), px(b), 1, tpx)
        if owner:
            d, out = d_own, d_own > TOL_MM
        else:
            d, out = d_all, (d_all > TOL_MM) & (d_own <= d_oth)
        if out.any():
            seg_rows.append({"a": [round(a[0], 3), round(a[1], 3)], "b": [round(b[0], 3), round(b[1], 3)],
                             "len_mm": round(L, 3), "max_off_mm": round(float(d[out].max()), 3),
                             "len_off_mm": round(float(out.sum()) * L / (n - 1), 3),
                             "run": s["run"], "shape": s["shape"], "owner": owner,
                             "kind": s["kind"], "label": lab})

    # what the instrument's zone (`glyph_read.read_glyphs`: pixels nearer this glyph than any
    # other, within COMP_TOL_MM + 0.5 mm of it) holds, by whose thread it is
    from scipy import ndimage as ndi
    gm = _mask([glyph], box)
    dg = ndi.distance_transform_edt(gm == 0) / RASTER_PPM
    if others is not None:
        om = _mask([g for j, g in enumerate(glyphs) if j != idx], box)
        do = ndi.distance_transform_edt(om == 0) / RASTER_PPM if om.any() else np.full_like(dg, np.inf)
    else:
        do = np.full_like(dg, np.inf)
    zmask = ((dg <= 1.0) | (_fill_mask(glyph, box) > 0)) & (dg <= do)
    zone_thread = {}
    for cls, test in (("own", lambda k: L_FOREIGN not in k and L_NONLETTER not in k),
                      ("neighbour letters", lambda k: L_FOREIGN in k),
                      ("non-letter shapes", lambda k: L_NONLETTER in k)):
        m = np.zeros((H, W), np.uint8)
        for k, tm in thread_masks.items():
            if test(k):
                m |= tm
        inz = (m > 0) & zmask
        zone_thread[cls] = {"mm2": round(float(inz.sum()) / RASTER_PPM ** 2, 3),
                            "beyond_0.5mm_of_ink_mm2": round(float((inz & (dg > COMP_TOL_MM)).sum()) / RASTER_PPM ** 2, 3),
                            "nearest_to_ink_mm": round(float(dg[m > 0].min()), 3) if (m > 0).any() else None}
    nl_shapes = sorted({e["shape"] + ":" + e["kind"] for e in ev["points"]
                        if e["shape"] not in letter_ids and zone.covers(Point(e["x"], e["y"]))})
    zone_thread["non_letter_runs_in_zone"] = nl_shapes
    by_id = {r.shape_id: r for r in result.regions}
    zone_thread["non_letter_shapes"] = []
    for sid in sorted({s_.split(":")[0] for s_ in nl_shapes}):
        r = by_id.get(sid)
        if r is None:
            continue
        zone_thread["non_letter_shapes"].append({
            "shape_id": sid, "area_mm2": round(r.polygon.area, 2),
            "bounds_mm": [round(v, 2) for v in r.polygon.bounds],
            "polygon_to_glyph_mm": round(r.polygon.distance(glyph), 3),
            "thread_rgb": list(ft._thread_rgb(r, plan)),
            "tier": "+".join(sorted({e["kind"] for e in ev["runs"] if e["shape"] == sid and not e["white"]}))})

    # bays, counters, gaps: bare in the source, then covered by which step's thread
    all_thread = np.zeros((H, W), np.uint8)
    for m in thread_masks.values():
        all_thread |= m
    bay_lab, bays = bays_of(glyph, box)
    for b in bays:
        m = bay_lab == b["id"]
        area = float(m.sum())
        cov = float((m & (all_thread > 0)).sum())
        b["covered_mm2"] = round(cov / RASTER_PPM ** 2, 3)
        b["bare_share"] = round(1.0 - cov / area, 3) if area else None
        b["status"] = "open" if (area and 1.0 - cov / area >= OPEN_SHARE) else "FILLED"
        b["covered_by_step_mm2"] = {k: round(float((m & (tm > 0)).sum()) / RASTER_PPM ** 2, 3)
                                    for k, tm in thread_masks.items() if (m & (tm > 0)).any()}
    holes = thread_holes(glyph, glyphs, idx, box, all_thread, run_masks)
    counters = []
    from shapely.geometry import Polygon
    for ring in glyph.interiors:
        c = Polygon(ring)
        cm = _mask([c], box)
        a = float(cm.sum())
        cov = float(((cm > 0) & (all_thread > 0)).sum())
        counters.append({"mm2": round(a / RASTER_PPM ** 2, 3),
                         "bare_share": round(1.0 - cov / a, 3) if a else None,
                         "status": "open" if a and 1.0 - cov / a >= OPEN_SHARE else "SHUT"})

    gaps = []
    for j in (idx - 1, idx + 1):
        if j < 0 or j >= len(glyphs):
            continue
        other = glyphs[j]
        gd = float(glyph.distance(other))
        if gd > 2.0:
            continue
        ob = (min(box[0], other.bounds[0] - 0.2), min(box[1], other.bounds[1] - 0.2),
              max(box[2], other.bounds[2] + 0.2), max(box[3], other.bounds[3] + 0.2))
        gW = int(math.ceil((ob[2] - ob[0]) * RASTER_PPM)) + 1
        gH = int(math.ceil((ob[3] - ob[1]) * RASTER_PPM)) + 1
        fa, fb = _fill_mask(glyph, ob), _fill_mask(other, ob)
        r = max(1, int(round((gd / 2.0 + 0.05) * RASTER_PPM)))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        un = cv2.morphologyEx(cv2.copyMakeBorder(((fa | fb) > 0).astype(np.uint8), r + 2, r + 2, r + 2, r + 2,
                                                 cv2.BORDER_CONSTANT, value=0), cv2.MORPH_CLOSE, k)[r + 2:-(r + 2), r + 2:-(r + 2)]
        strip = (un > 0) & (fa == 0) & (fb == 0)
        # drop what either glyph's own bays account for
        for g_, f_ in ((glyph, fa), (other, fb)):
            lab_, _c = bays_of(g_, ob)
            strip &= lab_ == 0
        tm_all = np.zeros((gH, gW), np.uint8)
        by_step = {}
        for s in ev["segments"]:
            a, b = s["a"], s["b"]
            if max(a[0], b[0]) < ob[0] or min(a[0], b[0]) > ob[2] or max(a[1], b[1]) < ob[1] or min(a[1], b[1]) > ob[3]:
                continue
            lab = s["label"] + suffix(s["shape"])
            m_ = by_step.setdefault(lab, np.zeros((gH, gW), np.uint8))
            cv2.line(m_, (int(round((a[0] - ob[0]) * RASTER_PPM)), int(round((a[1] - ob[1]) * RASTER_PPM))),
                     (int(round((b[0] - ob[0]) * RASTER_PPM)), int(round((b[1] - ob[1]) * RASTER_PPM))), 1, tpx)
            tm_all |= m_
        sa = float(strip.sum())
        cov = float((strip & (tm_all > 0)).sum())
        # thread to thread: this glyph's own thread against the neighbour's own
        own_a, own_b = np.zeros((gH, gW), np.uint8), np.zeros((gH, gW), np.uint8)
        oa = owners[idx]
        ob_ids = set(owners[j])
        for s in ev["segments"]:
            a, b = s["a"], s["b"]
            tgt = own_a if s["shape"] in oa else own_b if s["shape"] in ob_ids else None
            if tgt is None:
                continue
            if max(a[0], b[0]) < ob[0] or min(a[0], b[0]) > ob[2] or max(a[1], b[1]) < ob[1] or min(a[1], b[1]) > ob[3]:
                continue
            cv2.line(tgt, (int(round((a[0] - ob[0]) * RASTER_PPM)), int(round((a[1] - ob[1]) * RASTER_PPM))),
                     (int(round((b[0] - ob[0]) * RASTER_PPM)), int(round((b[1] - ob[1]) * RASTER_PPM))), 1, tpx)
        if own_a.any() and own_b.any():
            from scipy import ndimage as ndi
            sewn_gap = float(ndi.distance_transform_edt(own_b == 0)[own_a > 0].min()) / RASTER_PPM
        else:
            sewn_gap = None
        mine_in_nb = float(((own_a > 0) & (fb > 0)).sum()) / RASTER_PPM ** 2
        gaps.append({"to": labels[j], "side": "left" if j < idx else "right",
                     "src_gap_mm": round(gd, 3), "sewn_thread_gap_mm": None if sewn_gap is None else round(sewn_gap, 3),
                     "gap_mm2": round(sa / RASTER_PPM ** 2, 3),
                     "covered_mm2": round(cov / RASTER_PPM ** 2, 3),
                     "bare_share": round(1.0 - cov / sa, 3) if sa else None,
                     "this_glyph_thread_on_neighbour_ink_mm2": round(mine_in_nb, 3),
                     "covered_by_step_mm2": {k_: round(float((strip & (m_ > 0)).sum()) / RASTER_PPM ** 2, 3)
                                             for k_, m_ in by_step.items() if (strip & (m_ > 0)).any()}})

    # lock stitches (`apply_ties`) folded into this glyph's runs
    ties, tie_legs = [], []
    for e in ev["runs"]:
        if e["white"] or e["shape"] not in mine:
            continue
        for end, n_, key, leg in (("in", e["lead_tie"], "first", e["lead_leg"]),
                                  ("off", e["tail_tie"], "last", e["tail_leg"])):
            if n_:
                ties.append({"run": e["run"], "end": end, "at": [round(e[key][0], 3), round(e[key][1], 3)],
                             "leg_mm": round(leg, 3)})
                tie_legs.append(round(leg, 3))
    # the hops INTO this glyph's runs: what the bean tier booked (a jump) against what the
    # plan sews (stage 7's link pass buries a jump under cover and lays thread instead)
    hops = []
    prev_rec = None
    for e in ev["runs"]:
        if e["white"]:
            prev_rec = None
            continue
        if e["shape"] in mine and prev_rec is not None and prev_rec["block"] == e["block"] and not e["trim"]:
            a_, b_ = prev_rec["last"], e["first"]
            dm = math.dist(a_, b_)
            if dm >= _stitches().SAME_POINT_MM:
                nn = max(2, int(math.ceil(dm / SAMPLE_MM)) + 1)
                tt = np.linspace(0.0, 1.0, nn)
                dd = dist_to(glyph, np.stack([a_[0] + (b_[0] - a_[0]) * tt, a_[1] + (b_[1] - a_[1]) * tt], 1))
                hops.append({"run": e["run"], "from_run": prev_rec["run"], "from_shape": prev_rec["shape"],
                             "from_xy": [round(a_[0], 3), round(a_[1], 3)], "to_xy": [round(b_[0], 3), round(b_[1], 3)],
                             "dist_mm": round(dm, 3), "bean_letter_booked_jump": e["recorded_jump"],
                             "plan_jump": e["jump"], "thread_laid": not e["jump"],
                             "max_off_own_ink_mm": round(float(dd.max()), 3)})
        prev_rec = e
    # the three sizes
    src_b = [round(v, 3) for v in glyph.bounds]
    thread_b = None
    if needle_bbox:
        h = thread / 2.0
        thread_b = [round(needle_bbox[0] - h, 3), round(needle_bbox[1] - h, 3),
                    round(needle_bbox[2] + h, 3), round(needle_bbox[3] + h, 3)]
    by_label: dict = {}
    for r in outside_pts:
        by_label[r["label"]] = by_label.get(r["label"], 0) + 1
    seg_by_label: dict = {}
    for s in seg_rows:
        a = seg_by_label.setdefault(s["label"], {"segments": 0, "len_off_mm": 0.0, "max_off_mm": 0.0})
        a["segments"] += 1
        a["len_off_mm"] = round(a["len_off_mm"] + s["len_off_mm"], 3)
        a["max_off_mm"] = max(a["max_off_mm"], s["max_off_mm"])

    out = {
        "cell": run["cell"], "arm": run["arm"], "word": word, "index": idx, "glyph": labels[idx],
        "tier": tier, "built_as": built, "kinds": kinds, "shape_ids": sorted(mine), "regions": reg_rows,
        "thread_mm": round(thread, 3),
        "src_bbox_mm": src_b, "src_w_mm": round(gx1 - gx0, 3), "src_h_mm": round(gy1 - gy0, 3),
        "src_area_mm2": round(glyph.area, 3),
        "needle_bbox_mm": None if not needle_bbox else [round(v, 3) for v in needle_bbox],
        "thread_bbox_mm": thread_b,
        "spines": spines, "bean_reports": sewn_report,
        "needle_points_in_zone": len(pt_rows), "owner_needle_points": len(owner_pts),
        "points_outside": sorted(outside_pts, key=lambda r: -r["d_mm"]),
        "points_outside_by_step": by_label,
        "segments_outside": sorted(seg_rows, key=lambda r: -r["max_off_mm"]),
        "segments_outside_by_step": seg_by_label,
        "bays": bays, "counters": counters, "thread_holes": holes, "gaps": gaps,
        "lock_stitches": ties, "lock_leg_mm": tie_legs, "hops": hops,
        "owner_runs": [e for e in ev["runs"] if e["shape"] in mine and not e["white"]],
        "stations": station_rows, "zone_thread": zone_thread,
        "gl_row": gl_rows[idx] if gl_rows and len(gl_rows) > idx else None,
    }
    out["ocr_reads"] = ocr_reads(run, glyphs, idx, ev, mine, letter_ids, thread,
                                 gl_dbg[idx] if gl_dbg else None) if ocr else None
    return out


# --- the instrument's own read of the glyph --------------------------------------------


def gl_read_word(run: dict, word: str, n_glyphs: int, ocr: bool = True):
    """`glyph_legibility`'s read of `word`: (per-glyph rows left to right, the
    per-glyph debug windows {"S", "T", ...}), or None when its component count
    differs from ours (then no row is paired with a glyph)."""
    from tools import glyph_legibility as gl
    words, dbg, _reg = gl.read_case("fremont", run["design"], use_ocr=ocr, words=[word])
    if not words:
        return None
    rows = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in g.items()
             if k in ("legibility", "legibility_space", "strokes", "clean", "counters", "space",
                      "ocr_src", "ocr_sewn", "ocr_recovered", "ocr_readable_src")}
            for g in words[0].glyphs]
    glyph_dbg = dbg.get(word, {}).get("glyphs", [])
    return (rows, glyph_dbg) if len(rows) == n_glyphs and len(glyph_dbg) == n_glyphs else None


def ocr_reads(run: dict, glyphs: list, idx: int, ev: dict, mine: set, letter_ids: set,
              thread: float, dbg: dict | None) -> dict:
    """tesseract on the glyph alone (psm 10, no language model: the instrument's
    own reader), on four masks, so a wrong read can be told from a wrong glyph:

      source          the artwork's glyph;
      instrument      the thread window `glyph_legibility` handed its reader
                      (registered, shifted, and holding whatever thread of ANY
                      shape lies in the glyph's zone);
      own thread      only this glyph's own runs, drawn at the thread's width;
      all thread      every run in the window, drawn the same way;
      own thread, half width   the own thread at half the filament (a thread-physics control).

    If the instrument and `all thread` read alike and `own thread` reads the
    glyph, the wrong read is somebody else's thread, not this glyph's."""
    import cv2
    import numpy as np
    from tools import glyph_legibility as gl
    if not gl.tesseract_available():
        return {"unavailable": True}
    glyph = glyphs[idx]
    gx0, gy0, gx1, gy1 = glyph.bounds
    box = (gx0 - 1.0, gy0 - 1.0, gx1 + 1.0, gy1 + 1.0)
    W = int(math.ceil((box[2] - box[0]) * OCR_P)) + 1
    H = int(math.ceil((box[3] - box[1]) * OCR_P)) + 1
    tpx = max(1, int(round(thread * OCR_P)))

    def draw(pred, width=None):
        m = np.zeros((H, W), np.uint8)
        for s in ev["segments"]:
            a, b = s["a"], s["b"]
            if not pred(s) or max(a[0], b[0]) < box[0] or min(a[0], b[0]) > box[2] \
                    or max(a[1], b[1]) < box[1] or min(a[1], b[1]) > box[3]:
                continue
            cv2.line(m, (int(round((a[0] - box[0]) * OCR_P)), int(round((a[1] - box[1]) * OCR_P))),
                     (int(round((b[0] - box[0]) * OCR_P)), int(round((b[1] - box[1]) * OCR_P))), 1, width or tpx)
        return m > 0
    masks = {"source": _mask([glyph], box, OCR_P) > 0}
    if dbg is not None:
        masks["instrument"] = np.asarray(dbg["T"], bool)
    masks["own thread"] = draw(lambda s: s["shape"] in mine)
    masks["all thread"] = draw(lambda s: True)
    masks["own thread, half width"] = draw(lambda s: s["shape"] in mine, max(1, tpx // 2))
    out = {"_masks": masks}
    for name, m in masks.items():
        ch, conf = gl._ocr_char(m, OCR_P) if m.any() else ("", -1.0)
        out[name] = {"char": ch, "conf": round(max(conf, 0.0), 1)}
    return out


def strip_private(tr: dict) -> dict:
    """Drop the arrays and geometry the renderer needs, keep what is JSON."""
    for k in [k for k in tr if k.startswith("_")]:
        tr.pop(k)
    if isinstance(tr.get("ocr_reads"), dict):
        tr["ocr_reads"].pop("_masks", None)
    return tr


# --- the renders ------------------------------------------------------------------------

_COL = {L_BEAN: (200, 120, 30), L_CORNER: (30, 150, 230), L_TIE: (60, 60, 200), L_HOP: (60, 170, 60),
        L_OTHER: (180, 60, 180)}


def render_glyph(run: dict, glyphs: list, tr: dict, ev: dict, path: Path, ppm: float = RENDER_PPM) -> None:
    """Three panels at `ppm` px/mm: (1) the source ink with the skeleton the bean
    tier was handed; (2) the thread (width of the thread profile) coloured by
    construction step, stations numbered in sew order, needle points off the
    ink marked red; (3) the bays and the gap strip: green bare, red covered."""
    import cv2
    import numpy as np
    from tools import fremont_triage as ft

    idx = tr["index"]
    glyph = glyphs[idx]
    gx0, gy0, gx1, gy1 = glyph.bounds
    m = 1.0
    nb = [g for j, g in enumerate(glyphs) if j != idx and glyph.distance(g) < 1.2]
    xs = [gx0, gx1] + [v for g in nb for v in (g.bounds[0], g.bounds[2])]
    ys = [gy0, gy1] + [v for g in nb for v in (g.bounds[1], g.bounds[3])]
    box = (min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)
    W = int(math.ceil((box[2] - box[0]) * ppm))
    H = int(math.ceil((box[3] - box[1]) * ppm))

    def px(pt):
        return (int(round((pt[0] - box[0]) * ppm)), int(round((pt[1] - box[1]) * ppm)))

    def ink_layer():
        img = np.full((H, W, 3), 255, np.uint8)
        for g in [glyph] + nb:
            col = (225, 225, 225) if g is not glyph else (200, 200, 200)
            for part in getattr(g, "geoms", [g]):
                cv2.fillPoly(img, [np.array([px(q) for q in part.exterior.coords], np.int32)], col)
                for r in part.interiors:
                    cv2.fillPoly(img, [np.array([px(q) for q in r.coords], np.int32)], (255, 255, 255))
        return img

    def outline(img, thick=1):
        for g in [glyph] + nb:
            for part in getattr(g, "geoms", [g]):
                cv2.polylines(img, [np.array([px(q) for q in part.exterior.coords], np.int32)], True, (0, 0, 0), thick, cv2.LINE_AA)
                for r in part.interiors:
                    cv2.polylines(img, [np.array([px(q) for q in r.coords], np.int32)], True, (0, 0, 0), thick, cv2.LINE_AA)

    # panel 1: source + skeleton
    p1 = ink_layer()
    outline(p1)
    cfg = run["cfg"]
    for sid in tr["shape_ids"]:
        calls = run["bean"].get(sid, [])
        if not calls:
            continue
        raw = calls[-1]["spines"]
        cut = trimmed_spines(raw, cfg)
        for s in raw:
            cv2.polylines(p1, [np.array([px(q) for q in s], np.int32)], False, (60, 60, 230), 1, cv2.LINE_AA)   # raw (red)
        for s in cut:
            cv2.polylines(p1, [np.array([px(q) for q in s], np.int32)], False, (200, 120, 30), 2, cv2.LINE_AA)  # after hook cut (blue)
            cv2.circle(p1, px(s[0]), 4, (0, 140, 0), -1)
            cv2.circle(p1, px(s[-1]), 4, (0, 140, 0), -1)
        for c in corner_points(calls, cfg):
            cv2.circle(p1, px(c), 5, (0, 200, 255), -1)
            cv2.circle(p1, px(c), 5, (0, 0, 0), 1)

    # panel 2: thread
    p2 = np.full((H, W, 3), 255, np.uint8)
    mine = set(tr["shape_ids"])
    layer = p2.copy()
    tpx = max(1, int(round(tr["thread_mm"] * ppm)))
    for s in ev["segments"]:
        a, b = s["a"], s["b"]
        if max(a[0], b[0]) < box[0] or min(a[0], b[0]) > box[2] or max(a[1], b[1]) < box[1] or min(a[1], b[1]) > box[3]:
            continue
        col = _COL.get(s["label"], (150, 150, 150))
        if s["shape"] not in mine:
            col = (170, 170, 170)
        cv2.line(layer, px(a), px(b), col, tpx, cv2.LINE_AA)
    p2 = cv2.addWeighted(layer, 0.55, p2, 0.45, 0)
    outline(p2, 1)
    seen = {}
    for e in ev["points"]:
        if e["shape"] in mine and box[0] <= e["x"] <= box[2] and box[1] <= e["y"] <= box[3]:
            key = (round(e["x"], 4), round(e["y"], 4))
            if key not in seen and e["label"] != L_TIE:
                seen[key] = len(seen) + 1
    for (x, y), k in seen.items():
        cv2.circle(p2, px((x, y)), 3, (0, 0, 0), -1)
        cv2.putText(p2, str(k), (px((x, y))[0] + 4, px((x, y))[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
    for r in tr["points_outside"]:
        q = px((r["x"], r["y"]))
        cv2.drawMarker(p2, q, (0, 0, 255), cv2.MARKER_TILTED_CROSS, 12, 2)
    # panel 3: bays and gaps
    p3 = ink_layer()
    allm = np.zeros((H, W), np.uint8)
    for s in ev["segments"]:
        a, b = s["a"], s["b"]
        if max(a[0], b[0]) < box[0] or min(a[0], b[0]) > box[2] or max(a[1], b[1]) < box[1] or min(a[1], b[1]) > box[3]:
            continue
        cv2.line(allm, px(a), px(b), 1, tpx)
    bb = (box[0], box[1], box[2], box[3])
    lab, _bays = bays_of(glyph, bb, ppm=ppm)
    lab = lab[:H, :W]
    thread_px = np.zeros((H, W), bool)
    thread_px[:allm.shape[0], :allm.shape[1]] = allm[:H, :W] > 0
    over = p3.copy()
    over[(lab > 0) & ~thread_px[:lab.shape[0], :lab.shape[1]]] = (120, 200, 120)
    over[(lab > 0) & thread_px[:lab.shape[0], :lab.shape[1]]] = (90, 90, 230)
    p3 = cv2.addWeighted(over, 0.8, p3, 0.2, 0)
    tl = np.zeros((H, W, 3), np.uint8)
    p3[thread_px & (lab == 0)] = (p3[thread_px & (lab == 0)] * 0.6 + np.array([150, 150, 150]) * 0.4).astype(np.uint8)
    outline(p3, 1)
    # panel 4: what each OCR read saw
    p4 = np.full((H, W, 3), 255, np.uint8)
    oc = tr.get("ocr_reads") or {}
    ms = oc.get("_masks") or {}
    if ms:
        cells = list(ms.items())
        cw, ch_ = W // 2, H // 2
        for n_, (name, m) in enumerate(cells[:4]):
            ys_, xs_ = np.nonzero(m)
            if not len(ys_):
                continue
            crop = m[max(0, ys_.min() - 4):ys_.max() + 5, max(0, xs_.min() - 4):xs_.max() + 5]
            f_ = max(1, int(min((cw - 8) / crop.shape[1], (ch_ - 30) / crop.shape[0])))
            big = cv2.resize((~crop).astype(np.uint8) * 255, None, fx=f_, fy=f_, interpolation=cv2.INTER_NEAREST)
            ox, oy = (n_ % 2) * cw + 4, (n_ // 2) * ch_ + 4
            p4[oy:oy + big.shape[0], ox:ox + big.shape[1]] = big[..., None]
            cv2.rectangle(p4, (ox, oy), (ox + big.shape[1], oy + big.shape[0]), (160, 160, 160), 1)
            txt = oc.get(name, {}).get("char", "?")
            cv2.putText(p4, f"{name} -> {txt!r}", (ox, oy + big.shape[0] + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 160), 1, cv2.LINE_AA)
    head = 54
    panels = []
    for img, title in ((p1, "source ink + skeleton (red raw, blue after hook cut, green ends, yellow corners)"),
                       (p2, "thread, numbered stations, red X = needle point off the ink"),
                       (p3, "bays: green bare, red covered by thread; grey = other thread"),
                       (p4, "what OCR read: source / instrument window / own thread only / all thread")):
        canvas = np.full((H + head, W, 3), 255, np.uint8)
        canvas[head:] = img
        cv2.putText(canvas, title[:74], (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(canvas, title[74:150], (4, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)
        panels.append(canvas)
    sheet = np.concatenate(panels, axis=1)
    cap = (f"{tr['cell']} {tr['arm']}  {tr['word']} '{tr['glyph']}'  tier {tr['tier']}  "
           f"{box[2] - box[0]:.1f} x {box[3] - box[1]:.1f} mm  thread {tr['thread_mm']} mm")
    cv2.putText(sheet, cap, (4, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 120), 1, cv2.LINE_AA)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), sheet)


# --- the table --------------------------------------------------------------------------


def _f(v, nd=2):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def markdown(tr: dict) -> str:
    g = tr["gl_row"] or {}
    lines = [f"### {tr['cell']} / {tr['arm']} / {tr['word']} '{tr['glyph']}'", ""]
    lines.append(f"- tier **{tr['tier']}** (built as {tr['built_as']}; run kinds {', '.join(tr['kinds']) or '-'}); "
                 f"shapes {', '.join(tr['shape_ids']) or 'none'}; thread {tr['thread_mm']} mm")
    if g:
        lines.append(f"- instrument: legibility {_f(g.get('legibility'))}, clean {_f(g.get('clean'))}, "
                     f"space {_f(g.get('space'))}, OCR source '{g.get('ocr_src', '')}' -> sewn '{g.get('ocr_sewn', '')}'")
    sb, nb, tb = tr["src_bbox_mm"], tr["needle_bbox_mm"], tr["thread_bbox_mm"]
    lines.append(f"- source box {tr['src_w_mm']} x {tr['src_h_mm']} mm; needle box "
                 f"{'-' if not nb else f'{nb[2] - nb[0]:.2f} x {nb[3] - nb[1]:.2f}'}; thread box "
                 f"{'-' if not tb else f'{tb[2] - tb[0]:.2f} x {tb[3] - tb[1]:.2f}'} mm")
    for r in tr["regions"]:
        lines.append(f"- region {r['shape_id']}: {r['area_mm2']} mm2, {r['overlap_of_glyph']:.0%} of the glyph, "
                     f"{r['polygon_off_ink_mm2']} mm2 off the ink, restored={r['restored']}, bean spines {r['bean_spines']}, "
                     f"ink stroke {r['ink_stroke_mm']} mm")
    for s in tr["spines"]:
        lines.append(f"- spine {s['spine']} ({s['shape_id']}): raw {s['raw_mm']} mm, hook cut {s['hook_cut_mm']} mm, "
                     f"kept {s['after_hook_cut_mm']} mm, free ends {s['free_ends']}, corners {s['corners']}, "
                     f"{'sewn' if s['sews'] else 'NOT sewn'}")
    lines.append(f"- lock stitches on its runs: {len(tr['lock_stitches'])} bounce(s), leg(s) {tr['lock_leg_mm']} mm")
    lines.append(f"- needle points in its zone: {tr['needle_points_in_zone']} ({tr['owner_needle_points']} its own); "
                 f"off the ink by > {TOL_MM} mm: {len(tr['points_outside'])} {tr['points_outside_by_step']}")
    for r in tr["points_outside"][:12]:
        lines.append(f"    - ({r['x']:.2f}, {r['y']:.2f}) {r['d_mm']:.2f} mm off, run {r['run']} {r['shape']}, {r['label']}"
                     f"{', on a neighbour glyph' if r.get('on_neighbour_ink') else ''}")
    lines.append(f"- thread segments leaving the ink: {len(tr['segments_outside'])} {tr['segments_outside_by_step']}")
    for s in tr["segments_outside"][:8]:
        lines.append(f"    - {s['a']} -> {s['b']}: {s['len_mm']} mm long, {s['len_off_mm']} mm of it off the ink, "
                     f"max {s['max_off_mm']} mm, {s['label']}")
    for b in tr["bays"]:
        lines.append(f"- bay {b['id']} ({b['where']}): {b['mm2']} mm2 in the source, covered {b['covered_mm2']} mm2, "
                     f"bare {_f(b['bare_share'])} -> {b['status']}; by step {b['covered_by_step_mm2']}")
    for h in tr.get("thread_holes", []):
        kind = "a source counter" if h["source_counter"] else "SPURIOUS (not a source counter)"
        pin = h.get("narrowest_gap_between_bounding_runs")
        lines.append(f"- thread hole ({h['reading']}) at ({h['centre_mm'][0]}, {h['centre_mm'][1]}): {h['mm2']} mm2, {kind}; "
                     f"bounded by " + ", ".join(f"run {b['run']} {b['label']} {b['touching_px']}px" for b in h["bounded_by"])
                     + (f"; narrowest gap between bounding runs {pin['gap_mm']} mm (runs {pin['runs']})" if pin else ""))
    for c in tr["counters"]:
        lines.append(f"- counter: {c['mm2']} mm2, bare {_f(c['bare_share'])} -> {c['status']}")
    for s_ in tr["stations"]:
        lines.append(f"    - station {s_['n']}: ({s_['x']:.2f}, {s_['y']:.2f}) {s_['d_mm']:.2f} mm from the ink, "
                     f"visited {s_['visits']}x, {' / '.join(s_['labels'])}")
    zt = tr["zone_thread"]
    lines.append("- thread in the instrument's zone (nearer this glyph than any other, within 1 mm of its ink), "
                 + "; ".join(f"{k}: {v['mm2']} mm2 ({v['beyond_0.5mm_of_ink_mm2']} beyond 0.5 mm of the ink)"
                             for k, v in zt.items() if isinstance(v, dict))
                 + f"; non-letter runs in the zone: {zt.get('non_letter_runs_in_zone') or 'none'}")
    for nl in zt.get("non_letter_shapes", []):
        lines.append(f"    - non-letter shape {nl['shape_id']}: {nl['tier']}, {nl['area_mm2']} mm2, bounds {nl['bounds_mm']}, "
                     f"{nl['polygon_to_glyph_mm']} mm from the glyph, thread rgb {nl['thread_rgb']}")
    oc = tr.get("ocr_reads")
    if oc and not oc.get("unavailable"):
        lines.append("- OCR (psm 10) on: " + ", ".join(f"{k} -> '{v['char']}' ({v['conf']})" for k, v in oc.items()
                                                        if isinstance(v, dict) and "char" in v))
    for hp in tr.get("hops", []):
        lines.append(f"- hop into run {hp['run']} from run {hp['from_run']} ({hp['from_xy']} -> {hp['to_xy']}): {hp['dist_mm']} mm, "
                     f"bean_letter booked jump={hp['bean_letter_booked_jump']}, plan jump={hp['plan_jump']} "
                     f"({'THREAD LAID' if hp['thread_laid'] else 'no thread'}), up to {hp['max_off_own_ink_mm']} mm off the ink")
    for gp in tr["gaps"]:
        lines.append(f"- gap to {gp['side']} neighbour '{gp['to']}': source {gp['src_gap_mm']} mm, thread-to-thread "
                     f"{_f(gp['sewn_thread_gap_mm'], 3)} mm; strip {gp['gap_mm2']} mm2, covered {gp['covered_mm2']} mm2 "
                     f"(bare {_f(gp['bare_share'])}); this glyph's thread on the neighbour's ink "
                     f"{gp['this_glyph_thread_on_neighbour_ink_mm2']} mm2; by step {gp['covered_by_step_mm2']}")
    return "\n".join(lines)


def summary_row(tr: dict) -> dict:
    """One line per glyph for the PR table."""
    g = tr["gl_row"] or {}
    filled = [b for b in tr["bays"] if b["status"] == "FILLED"]
    return {"glyph": f"{tr['word']} '{tr['glyph']}' ({tr['cell']})", "tier": tr["tier"],
            "ocr": f"{g.get('ocr_src', '?')} -> {g.get('ocr_sewn', '?')}", "legibility": g.get("legibility"),
            "points_off_ink": len(tr["points_outside"]), "points_by_step": tr["points_outside_by_step"],
            "segments_off_ink": len(tr["segments_outside"]), "segments_by_step": tr["segments_outside_by_step"],
            "bays": len(tr["bays"]), "bays_filled": len(filled),
            "locks": len(tr["lock_stitches"]),
            "min_gap_bare": min([gp["bare_share"] for gp in tr["gaps"] if gp["bare_share"] is not None], default=None)}


# --- main -------------------------------------------------------------------------------


def analyse(run: dict, specs: list[str], ocr: bool = True) -> list[dict]:
    from tools import small_lettering_skeleton as sls
    cache: dict = {}
    ev = build_events(run)
    out = []
    for spec in specs:
        word, _, sel = spec.partition(":")
        if word not in cache:
            glyphs = word_glyphs(run["gen"].p, word)
            owners = sls._owners(run["result"], run["plan"], glyphs)
            cache[word] = (glyphs, owners, gl_read_word(run, word, len(glyphs), ocr))
        glyphs, owners, rows = cache[word]
        idx = pick_glyph(sel, glyphs, word)
        tr = trace_glyph(run, word, idx, glyphs, ev, owners, rows, ocr)
        tr["_glyphs"], tr["_ev"] = glyphs, ev
        out.append(tr)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cell", choices=sorted(CELLS), help="what to digitize: hat81, hat925 or patch925")
    ap.add_argument("--arm", choices=sorted(ARMS), default="switch",
                    help="switch = small_text_true_size ON (default); main = it OFF")
    ap.add_argument("--glyph", action="append", default=None,
                    help="WORD:CHAR to trace (repeatable); default is the cell's own list")
    ap.add_argument("--out", type=Path, default=Path("bean_glyph_trace_out"),
                    help="where the pickle and the JSON go (default: ./bean_glyph_trace_out)")
    ap.add_argument("--renders", type=Path, default=None, help="where the PNGs go (default: none)")
    ap.add_argument("--reuse", action="store_true", help="load the pickled run if there is one")
    ap.add_argument("--no-ocr", action="store_true", help="skip glyph_legibility's OCR read")
    ap.add_argument("--list-glyphs", metavar="CELL", choices=sorted(CELLS),
                    help="print each word's source components (index, label, box) from the saved run and exit")
    a = ap.parse_args(argv)
    if a.list_glyphs:
        a.cell = a.list_glyphs
    if not a.cell:
        ap.error("--cell is required")
    run = load_run(a.cell, a.arm, a.out, a.reuse)
    if a.list_glyphs:
        from tools import fremont_triage as ft
        for w in ft.ROIS:
            gl_ = word_glyphs(run["gen"].p, w)
            print(w, [(i, l, [round(v, 1) for v in g.bounds]) for i, (l, g) in enumerate(zip(labels_for(w, len(gl_)), gl_))])
        return 0
    specs = a.glyph or DEFAULT_GLYPHS[a.cell]
    st = run["plan"].stats
    print(f"{a.cell} / {a.arm}: {st.stitch_count:,} stitches, {st.trims} trims, "
          f"digitized in {run.get('digitize_secs', '?')} s", flush=True)
    traces = analyse(run, specs, ocr=not a.no_ocr)
    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for tr in traces:
        print(markdown(tr), "\n", flush=True)
        if a.renders:
            name = f"{tr['cell']}__{tr['arm']}__{tr['word']}_{tr['glyph'].strip('#')}.png".replace("|", "bar")
            render_glyph(run, tr["_glyphs"], tr, tr["_ev"], a.renders / name)
        rows.append(summary_row(tr))
        strip_private(tr)
    (a.out / f"{a.cell}__{a.arm}__trace.json").write_text(json.dumps(
        {"cell": a.cell, "arm": a.arm, "overrides": run.get("overrides"), "stitches": st.stitch_count,
         "trims": st.trims, "glyphs": traces, "summary": rows}, indent=1, default=str))
    return 0

if __name__ == "__main__":
    sys.exit(main())
