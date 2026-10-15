"""Hotel Fremont's small lettering: what `small_print_floor` would sew HERE.

PR #898 (`tools/fremont_triage.py`) reproduced Kent's 81 mm Hat stitch-out
and found that THE, the EAT | STAY | PLAY tagline and EST all come from
stage 7's small-shape rescue (`routes_to_run`, `min_detail_mm`^2 = 2.25 mm^2):
a letter under that area is sewn as an outline run before the Column lane is
asked. What small lettering under 2.25 mm^2 SHOULD sew as is left open.
`cfg.small_print_floor` (#873/#878/#880, OFF) is the existing answer and
`cfg.lettering_columns_small_stem` (#896, OFF) is the existing way to let a
thin stem reach the Column lane. This measures exactly what they give on this
upload, at this size, per glyph. Nothing in the engine changes, no flag is
flipped, no constant is touched (ROADMAP gate 1: pull and floor values are
cloth constants, measured here, not set).

Arms (the Studio request of `fremont_triage.studio_request`, Hat):

    main_81         main
    floor_81        small_print_floor ON
    floor_stem_81   small_print_floor + lettering_columns_small_stem ON
    floor_stem_92   the same at 92.5 mm (the pro's size)
    stem_81         lettering_columns_small_stem alone  (attribution control)
    main_92         main at 92.5 mm                     (does size alone fix it)

Per glyph (the source artwork's connected ink components in the THE, tagline
and EST boxes) it reports the tier sewn, whether the Column lane took it,
the source counters and how many are still bare, the narrowest column
(source stroke vs sewn), the pull applied, stitches and trims. `pull_sweep`
re-runs the lane on the THE glyphs at several pulls, which is a measurement of
the 0.4 mm hat pull and not a change to it.

    # one arm at a time (a digitize is minutes and gigabytes; run ONE process)
    .venv/Scripts/python -m tools.fremont_small_lettering --arm main_81 --out DIR
    # the table, from the saved arms (no digitizing)
    .venv/Scripts/python -m tools.fremont_small_lettering --analyze --out DIR
    # the render sheets from the saved arms
    .venv/Scripts/python -m tools.fremont_small_lettering --sheets --out DIR --renders DIR2
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRO_WIDTH_MM = 92.5     # the pro's file (memory pro-files-refute-scale-limit-2026-09-03)

# name -> (width mm, PipelineConfig overrides on the Studio request, label)
FLOOR = {"small_print_floor": True}
STEM = {"lettering_columns_small_stem": True}
ARMS = {
    "main_81": (81.0, {}, "main"),
    "floor_81": (81.0, dict(FLOOR), "small_print_floor ON"),
    "floor_stem_81": (81.0, {**FLOOR, **STEM}, "small_print_floor + small_stem ON"),
    "floor_stem_92": (PRO_WIDTH_MM, {**FLOOR, **STEM}, "small_print_floor + small_stem ON, 92.5 mm"),
    "stem_81": (81.0, dict(STEM), "small_stem ON alone (control)"),
    "main_92": (PRO_WIDTH_MM, {}, "main at 92.5 mm (control)"),
    # The flags that DO move a sub-2.25 mm^2 letter's tier (the floor and the
    # stem rule do not, see the table): measured as the priced alternatives,
    # at their documented values, nothing flipped.
    "bean_81": (81.0, {"bean_letter_max_stroke_mm": 1.0},
                "bean_letter_max_stroke_mm 1.0 (the value its comment names)"),
    "wordtier_81": (81.0, {"lettering_words": True, "lettering_word_tiers": True},
                    "lettering_words + lettering_word_tiers"),
    "wordtier_floor_81": (81.0, {"lettering_words": True, "lettering_word_tiers": True,
                                 **FLOOR},
                          "lettering_words + lettering_word_tiers + small_print_floor"),
    # `small_glyph_keep` (936224e4): stage 4's hole floor, the other half of
    # the counter loss. It is ON by default since 2026-10-13 (Kent's ruling),
    # so every arm above runs with it ON and these two are the OFF controls
    # (they were `keep_81` / `keep_floor_81`, the ON arms, before the flip).
    "nokeep_81": (81.0, {"small_glyph_keep": False}, "small_glyph_keep OFF (control)"),
    "nokeep_floor_81": (81.0, {"small_glyph_keep": False, **FLOOR},
                        "small_glyph_keep OFF + small_print_floor ON (control)"),
}
# `small_text_true_size` is ON by default since 2026-10-14 (Kent, WoK 56
# option A). This table and its committed record (`signatures.json`) were
# measured before that flip, so every arm runs with it OFF: the arms price the
# floor, the stem rule and the tier flags against the engine they were
# measured on. `tools/small_lettering_compare.py` measures the switch itself.
PRE_TRUE_SIZE = {"small_text_true_size": False}
ARMS = {name: (w, {**PRE_TRUE_SIZE, **o}, label) for name, (w, o, label) in ARMS.items()}
# The four arms Kent named, in his order; the controls and alternatives follow.
KENT_ARMS = ["main_81", "floor_81", "floor_stem_81", "floor_stem_92"]
ARM_ORDER = list(ARMS)

# Boxes (fractions of the source image) from `fremont_triage.ROIS`.
BOXES = ["the", "tagline", "est"]


def run_one(name: str, out: Path) -> Path:
    """Digitize one arm and pickle the run (the pipeline objects the analysis
    reads) under `out`. Preflight is skipped: nothing here reads a finding."""
    from tools import fremont_triage as ft
    width, overrides, _label = ARMS[name]
    t = time.time()
    run = ft.run_arm(name, width, None, preflight=False, overrides=overrides)
    out.mkdir(parents=True, exist_ok=True)
    pk = out / f"{name}.pkl"
    pk.write_bytes(pickle.dumps(run))
    s = run["plan"].stats
    print(f"{name}: {s.stitch_count:,} stitches, {s.trims} trims, "
          f"{len(run['result'].regions)} regions, lane took {len(run['taken'])}, "
          f"{time.time() - t:.0f} s -> {pk}", flush=True)
    return pk


# --- the source glyphs --------------------------------------------------------

RASTER_PPM = 60          # px/mm of every glyph raster below
MIN_GLYPH_MM2 = 0.02     # an ink speck under this is not a glyph
OPEN_SHARE = 0.5         # a counter with this share still bare is "open"
_SRC_CACHE: dict = {}


def _source_ink():
    """The fixture at full resolution: (ink mask uint8, H, W). Ink is the
    non-white artwork (`fremont_triage.WHITE_MIN`), alpha > 127."""
    if "ink" not in _SRC_CACHE:
        import cv2
        import numpy as np
        from tools import fremont_triage as ft
        src = cv2.imread(str(ft.FIXTURE), cv2.IMREAD_UNCHANGED)
        ink = ((src[..., 3] > 127) & (src[..., :3].min(axis=2) < ft.WHITE_MIN)).astype(np.uint8)
        _SRC_CACHE["ink"] = (ink, src.shape[0], src.shape[1])
    return _SRC_CACHE["ink"]


def source_glyphs(p, frac) -> list:
    """The connected ink components of the artwork inside the fraction box
    `frac`, left to right, as shapely polygons (with their counters) in the
    design frame of prep `p` (mm, y down). A component that touches the
    crop's edge belongs to a neighbour and is dropped."""
    import cv2
    from shapely.geometry import Polygon
    ink, H, W = _source_ink()
    mx = 0.004
    fx0, fy0, fx1, fy1 = frac
    x0, y0 = int(max(0, fx0 - mx) * W), int(max(0, fy0 - mx) * H)
    x1, y1 = int(min(1, fx1 + mx) * W), int(min(1, fy1 + mx) * H)
    crop = ink[y0:y1, x0:x1]
    h, w = p.bg_mask.shape
    ax0, ay0, ax1, ay1 = p.art_bbox
    cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0

    def to_mm(pts):
        return [((((x + x0 + 0.5) / W) * w - cx) / p.px_per_mm,
                 (((y + y0 + 0.5) / H) * h - cy) / p.px_per_mm) for x, y in pts.reshape(-1, 2)]
    cnts, hier = cv2.findContours(crop, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    if hier is None:
        return out
    for i, c in enumerate(cnts):
        if hier[0][i][3] != -1 or len(c) < 4:
            continue
        bx, by, bw, bh = cv2.boundingRect(c)
        if bx <= 0 or by <= 0 or bx + bw >= crop.shape[1] or by + bh >= crop.shape[0]:
            continue
        holes = []
        j = hier[0][i][2]
        while j != -1:
            if len(cnts[j]) >= 4:
                holes.append(to_mm(cnts[j]))
            j = hier[0][j][0]
        poly = Polygon(to_mm(c), holes).buffer(0)
        if poly.is_empty or poly.geom_type != "Polygon" or poly.area < MIN_GLYPH_MM2:
            continue
        out.append(poly.simplify(0.5 / p.px_per_mm))
    out.sort(key=lambda g: g.centroid.x)
    return out


def _mask(geoms, box, ppm=RASTER_PPM):
    """Rasterize shapely polygons (holes honoured) into a uint8 mask over
    `box` (x0, y0, x1, y1 mm)."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = box
    W, H = int(np.ceil((x1 - x0) * ppm)) + 1, int(np.ceil((y1 - y0) * ppm)) + 1
    m = np.zeros((H, W), np.uint8)
    for g in geoms:
        for part in getattr(g, "geoms", [g]):
            if part.is_empty:
                continue
            cv2.fillPoly(m, [np.array([((x - x0) * ppm, (y - y0) * ppm)
                                       for x, y in part.exterior.coords], np.int32)], 1)
            for r in part.interiors:
                cv2.fillPoly(m, [np.array([((x - x0) * ppm, (y - y0) * ppm)
                                           for x, y in r.coords], np.int32)], 0)
    return m


def ridge_widths(mask, ppm=RASTER_PPM) -> dict:
    """Stroke width along the mask's skeleton: 2 x the distance transform at
    each skeleton pixel (mm). `p50` is the stroke, `p10` the narrowest stretch
    that is not a skeleton tip's taper."""
    import cv2
    import numpy as np
    from skimage.morphology import skeletonize
    if not mask.any():
        return {"p50": 0.0, "p10": 0.0, "max": 0.0}
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    sk = skeletonize(mask > 0)
    wd = 2.0 * dt[sk] / ppm
    if not len(wd):
        return {"p50": 0.0, "p10": 0.0, "max": 0.0}
    return {"p50": float(np.percentile(wd, 50)), "p10": float(np.percentile(wd, 10)),
            "max": float(wd.max())}


def inscribed_width(poly) -> float:
    """Twice the largest inscribed radius of a polygon (mm): how wide the
    counter is where it is widest."""
    from shapely.ops import polylabel
    if poly.is_empty:
        return 0.0
    c = polylabel(poly, tolerance=0.005)
    return 2.0 * float(c.distance(poly.exterior))


# --- one arm's per-glyph table ------------------------------------------------

def _segments(runs):
    """Needle-down segments of `runs` (consecutive points; plus the hop into
    a run that is not a jump, when the previous run is in the list too)."""
    segs, prev = [], None
    for run in runs:
        pts = run.points
        if prev is not None and not run.jump and pts:
            segs.append((prev, tuple(pts[0])))
        for a, b in zip(pts, pts[1:]):
            segs.append((tuple(a), tuple(b)))
        if pts:
            prev = tuple(pts[-1])
    return segs


def _sewn_mask(runs, box, thread_mm, ppm=RASTER_PPM):
    import cv2
    import numpy as np
    x0, y0, x1, y1 = box
    W, H = int(np.ceil((x1 - x0) * ppm)) + 1, int(np.ceil((y1 - y0) * ppm)) + 1
    m = np.zeros((H, W), np.uint8)
    t = max(1, int(round(thread_mm * ppm)))
    for a, b in _segments(runs):
        cv2.line(m, (int(round((a[0] - x0) * ppm)), int(round((a[1] - y0) * ppm))),
                 (int(round((b[0] - x0) * ppm)), int(round((b[1] - y0) * ppm))), 1, t)
    return m


def tier_of(kinds) -> str:
    """The tier name of a set of run kinds: what the glyph is sewn AS."""
    from digitizer_core import stitches
    k = set(kinds)
    if stitches.FILL in k:
        return "fill"
    if stitches.SATIN in k or stitches.BORDER in k:
        return "satin"
    if stitches.RUN in k or stitches.BEAN in k:
        return "run"
    return "none" if not k else "other"


def glyph_row(run: dict, glyph, name: str, owned_ids: list, taken: set, floor_on: bool) -> dict:
    """One source glyph -> its row: the tier its own regions sew as, the Column
    lane, counters (source vs still bare), stroke widths (source vs sewn), the
    pull the needle points carry, stitches and trims."""
    import numpy as np
    from shapely.geometry import Point
    from digitizer_core import fabrics, preflight as pf
    from digitizer_core import stitches

    plan, result, cfg = run["plan"], run["result"], run["cfg"]
    fabric = fabrics.fabric_for_garment(cfg.garment_id)
    region_ids = {r.shape_id for r in result.regions}
    mine = set(owned_ids)
    regions = [r for r in result.regions if r.shape_id in mine]
    runs, rgb = [], None
    for b, r in plan.iter_runs():
        if r.points and r.shape_id and pf._owning_region_id(r.shape_id, region_ids) in mine:
            runs.append(r)
            rgb = rgb or tuple(int(v) for v in b.rgb)
    kinds = sorted({r.kind for r in runs})
    prof = __import__("digitizer_core.machine", fromlist=["x"]).thread_profile(cfg.thread_wt)
    pad = 1.0
    gx0, gy0, gx1, gy1 = glyph.bounds
    box = (gx0 - pad, gy0 - pad, gx1 + pad, gy1 + pad)
    src_m = _mask([glyph], box)
    sewn = _sewn_mask(runs, box, prof.width_mm)
    src_area = int(src_m.sum())
    # --- counters
    counters = []
    for ring in glyph.interiors:
        from shapely.geometry import Polygon
        c = Polygon(ring)
        cm = _mask([c], box)
        a = int(cm.sum())
        bare = float((cm & (1 - sewn)).sum()) / a if a else 0.0
        pt = c.representative_point()
        # known to the planner: the region polygon still has it as a hole, or
        # (floor ON) stage 4 recorded it for the Column lane / run cut
        known = False
        for r in regions:
            if not r.polygon.covers(pt) and r.polygon.buffer(0.05).intersects(pt):
                known = True            # a hole in the region's own polygon
            for sc in (r.meta or {}).get("small_counters") or ():
                if floor_on and len(sc) >= 3 and Polygon(sc).buffer(0).covers(pt):
                    known = True        # recorded by stage 4 (floor ON)
        counters.append({
            "mm2": round(a / RASTER_PPM ** 2, 3),
            "width_mm": round(inscribed_width(c), 3),
            "bare_share": round(bare, 3),
            "known_to_planner": known,
            "status": ("SHUT" if bare < OPEN_SHARE else
                       "open" if known else "bare-unplanned"),
        })
    # --- widths: source stroke vs sewn
    sw = ridge_widths(src_m)
    dw = ridge_widths(sewn)
    # --- the pull the needles carry: signed distance of every needle point
    # from the artwork outline (outside positive), over the glyph's own runs
    off = []
    ext = glyph.exterior
    for r in runs:
        if r.kind in (stitches.TIE,):
            continue
        for x, y in r.points:
            pt = Point(x, y)
            d = ext.distance(pt) if not glyph.contains(pt) else -min(ext.distance(pt), 9)
            off.append(d)
    off = np.asarray(off) if off else np.zeros(1)
    # --- stitches / trims
    pts = sum(len(r.points) for r in runs)
    sat = [r for r in runs if r.kind == stitches.SATIN]
    return {
        "glyph": name, "bbox_mm": [round(v, 2) for v in glyph.bounds],
        "w_mm": round(gx1 - gx0, 2), "h_mm": round(gy1 - gy0, 2),
        "area_mm2": round(glyph.area, 2),
        "shape_ids": sorted(mine),
        "kinds": kinds, "tier": tier_of(kinds),
        "column_lane": bool(mine & taken),
        "src_stroke_mm": round(sw["p50"], 3), "src_stroke_min_mm": round(sw["p10"], 3),
        "sewn_w_mm": round(dw["p50"], 3), "sewn_w_min_mm": round(dw["p10"], 3),
        "width_ratio": round(dw["p50"] / sw["p50"], 2) if sw["p50"] else None,
        "satin_runs": len(sat),
        "needle_offset_p50_mm": round(float(np.percentile(off, 50)), 3),
        "needle_offset_p90_mm": round(float(np.percentile(off, 90)), 3),
        "pull_nominal_mm": fabric.pull_comp_mm,
        "counters": counters,
        "counters_src": len(counters),
        "counters_open": sum(1 for c in counters if c["status"] == "open"),
        "counters_bare_unplanned": sum(1 for c in counters if c["status"] == "bare-unplanned"),
        "counters_shut": sum(1 for c in counters if c["status"] == "SHUT"),
        "covered": round(float((src_m & sewn).sum()) / src_area, 3) if src_area else None,
        "spill": round(float((sewn & (1 - src_m)).sum()) / src_area, 3) if src_area else None,
        "stitches": pts,
        "trims": sum(1 for r in runs if r.trim),
        "jumps": sum(1 for r in runs if r.jump),
        "thread_rgb": list(rgb) if rgb else None,
    }


def analyze_arm(name: str, run: dict) -> dict:
    """Per glyph, per box, for one pickled arm."""
    from tools import fremont_triage as ft
    from digitizer_core import preflight as pf
    p = run["gen"].p
    result, plan = run["result"], run["plan"]
    taken = set(run["taken"])
    floor_on = bool(run["cfg"].small_print_floor)
    region_ids = {r.shape_id for r in result.regions}
    nonwhite = [r for r in result.regions if min(ft._thread_rgb(r, plan)) < ft.WHITE_MIN]
    boxes = {}
    for bname in BOXES:
        frac = ft.ROIS[bname]
        glyphs = source_glyphs(p, frac)
        owners: dict[int, list] = {i: [] for i in range(len(glyphs))}
        for r in nonwhite:
            best, bi = 0.0, None
            for i, g in enumerate(glyphs):
                a = r.polygon.intersection(g).area if r.polygon.intersects(g) else 0.0
                if a > best:
                    best, bi = a, i
            if bi is not None and best > 0.2 * min(r.polygon.area, glyphs[bi].area):
                owners[bi].append(r.shape_id)
        rows = [glyph_row(run, g, f"{bname}[{i}]", owners[i], taken, floor_on)
                for i, g in enumerate(glyphs)]
        census = None
        boxes[bname] = {"glyphs": rows, "n_glyphs": len(rows)}
    census = ft.roi_census(run)
    for bname in BOXES:
        c = census[bname]
        boxes[bname]["box_mm"] = c["box_mm"]
        boxes[bname]["ink_mm2"] = c["ink_mm2"]
        boxes[bname]["ink_bare_mm2"] = c["ink_bare_mm2"]
        boxes[bname]["stitches"] = c["stitches"]
        boxes[bname]["trims"] = c["trims"]
    s = plan.stats
    width, overrides, label = ARMS[name]
    return {"arm": name, "label": label, "width_mm": width, "overrides": overrides,
            "size_mm": [round(v, 1) for v in s.size_mm], "stitches": s.stitch_count,
            "trims": s.trims, "lane_taken": len(taken), "boxes": boxes}


# --- the pull sweep: what the hat's 0.4 mm does to a column ------------------

PULLS_MM = (0.0, 0.1, 0.2, 0.3, 0.4)


def pull_sweep(run: dict, glyph_rows: list, glyphs: list) -> list:
    """The Column lane re-run on each glyph's own region at several pulls.
    A MEASUREMENT of the hat preset's 0.4 mm (`Fabric.pull_comp_mm`), never a
    change to it: the same artwork polygon, the same call stage 7 makes
    (spacing, split, floor, underlay none under the small-extent rule), only
    `pull_mm` varies. Per glyph and pull: the sewn column width (skeleton
    median of the thread raster, laid width included), the needle span (the
    narrowest rail-to-rail distance between a satin run's alternate points),
    how many counters stay bare, and what the lane returned. A glyph with no
    region of its own (nothing to hand the lane) is skipped."""
    import numpy as np
    from digitizer_core import fabrics, machine, stitches
    from digitizer_core.columns import lettering_columns_shape
    cfg, result = run["cfg"], run["result"]
    fabric = fabrics.fabric_for_garment(cfg.garment_id)
    prof = machine.thread_profile(cfg.thread_wt)
    split = float("inf") if not cfg.split_satin else cfg.split_satin_above_mm
    by_id = {r.shape_id: r for r in result.regions}
    out = []
    for row, g in zip(glyph_rows, glyphs):
        for sid in row["shape_ids"]:
            poly = by_id[sid].polygon
            if poly.is_empty or poly.geom_type != "Polygon":
                continue
            for pull in PULLS_MM:
                runs, report = lettering_columns_shape(
                    poly, sid, trim_at_mm=fabric.trim_at_mm,
                    spacing_mm=machine.SATIN_SPACING_MM, split_above_mm=split,
                    pull_mm=pull, pull_floor_mm=cfg.min_detail_mm,
                    underlay_style="none")
                ent = {"glyph": row["glyph"], "shape_id": sid, "pull_mm": pull,
                       "lane_empty": bool(report.get("empty")),
                       "src_stroke_mm": row["src_stroke_mm"]}
                if not report.get("empty"):
                    x0, y0, x1, y1 = g.bounds
                    box = (x0 - 1.0, y0 - 1.0, x1 + 1.0, y1 + 1.0)
                    sewn = _sewn_mask([r for r in runs if r.kind == stitches.SATIN] or runs,
                                      box, prof.width_mm)
                    dw = ridge_widths(sewn)
                    spans = [float(np.hypot(b[0] - a[0], b[1] - a[1]))
                             for r in runs if r.kind == stitches.SATIN
                             for a, b in zip(r.points[0::2], r.points[1::2])]
                    from shapely.geometry import Polygon
                    cms = [(_mask([Polygon(ring)], box)) for ring in g.interiors]
                    bare = [float((m & (1 - sewn)).sum()) / max(1, int(m.sum())) for m in cms]
                    ent.update({
                        "sewn_w_mm": round(dw["p50"], 3), "sewn_w_min_mm": round(dw["p10"], 3),
                        "needle_span_med_mm": round(float(np.median(spans)), 3) if spans else None,
                        "needle_span_min_mm": round(float(np.min(spans)), 3) if spans else None,
                        "satin_stitches": sum(len(r.points) for r in runs if r.kind == stitches.SATIN),
                        "counters_bare": [round(b, 2) for b in bare],
                    })
                out.append(ent)
    return out


# --- render sheets -----------------------------------------------------------

SHEET_PPM = 60


def _source_crop_mm(p, box_mm, margin_mm, ppm, size):
    """The artwork over `box_mm` (+ margin), cut from the source by the prep's
    own transform and resized to `size` (w, h) px, flattened on slate."""
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    src = cv2.imread(str(ft.FIXTURE), cv2.IMREAD_UNCHANGED)
    H, W = src.shape[:2]
    rgb = src[..., :3].astype(float)
    a = src[..., 3:4].astype(float) / 255.0
    flat = (rgb * a + np.array([145, 128, 120]) * (1 - a)).astype(np.uint8)
    h, w = p.bg_mask.shape
    ax0, ay0, ax1, ay1 = p.art_bbox
    cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
    x0, y0, x1, y1 = box_mm

    def sx(x):
        return int(round((((x * p.px_per_mm + cx) / w) * W)))

    def sy(y):
        return int(round((((y * p.px_per_mm + cy) / h) * H)))
    c = flat[max(0, sy(y0 - margin_mm)):sy(y1 + margin_mm), max(0, sx(x0 - margin_mm)):sx(x1 + margin_mm)]
    return cv2.resize(c, size, interpolation=cv2.INTER_AREA)


def build_sheets(out: Path, renders: Path, ppm: int = SHEET_PPM) -> list:
    """One sheet per box (THE, tagline, EST): the artwork, then each arm, all
    at `ppm` px/mm. Reads `<arm>.pkl` for the designs and `<arm>_table.json`
    for each row's caption. Renders one arm at a time."""
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    renders.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list] = {b: [] for b in BOXES}
    art: dict[str, tuple] = {}
    for name in ARM_ORDER:
        pk, tj = out / f"{name}.pkl", out / f"{name}_table.json"
        if not (pk.exists() and tj.exists()):
            continue
        run = pickle.loads(pk.read_bytes())         # our own scratch file
        tab = json.loads(tj.read_text())
        img, to_px = ft._render(run["design"], ppm)
        p = run["gen"].p
        for b in BOXES:
            box = tab["boxes"][b]["box_mm"]
            crop = ft._crop(img, to_px, box, margin_mm=0.6)
            g = tab["boxes"][b]["glyphs"]
            tiers = " ".join(("S" if r["tier"] == "satin" else "R" if r["tier"] == "run"
                              else r["tier"][:1].upper()) + ("*" if r["column_lane"] else "")
                             for r in g)
            cap = (f"{name} ({tab['label']}) | tiers {tiers} | "
                   f"st {tab['boxes'][b]['stitches']} tr {tab['boxes'][b]['trims']} | "
                   f"bare {tab['boxes'][b]['ink_bare_mm2']}/{tab['boxes'][b]['ink_mm2']} mm2")
            rows[b].append((name, crop, cap))
            if name == "main_81":
                art[b] = (_source_crop_mm(p, box, 0.6, ppm,
                                          (crop.shape[1], crop.shape[0])), box)
        del img, run
    written = []
    for b in BOXES:
        if b not in art:
            continue
        panels = [ft._label(art[b][0], f"artwork, same scale ({ppm} px/mm)")]
        panels += [ft._label(c, cap) for _n, c, cap in rows[b]]
        w = max(x.shape[1] for x in panels)
        sheet = np.vstack([np.pad(x, ((0, 8), (0, w - x.shape[1]), (0, 0)), constant_values=255)
                           for x in panels])
        title = {"the": "THE", "tagline": "EAT | STAY | PLAY", "est": "EST"}[b]
        sheet = ft._label(sheet, f"{title}: S satin, R run, * Column lane; every row {ppm} px/mm", width=w)
        path = renders / f"arms_{b}.png"
        cv2.imwrite(str(path), sheet)
        written.append(path)
    return written


def sweep_sheet(out: Path, renders: Path, sweep: list, ppm: int = SHEET_PPM) -> Path | None:
    """THE's glyphs at each pull (columns), the artwork outline in red: what
    0.4 mm of pull does to the column, at one scale."""
    import cv2
    import numpy as np
    from digitizer_core import fabrics, machine, stitches
    from digitizer_core.columns import lettering_columns_shape
    from tools import fremont_triage as ft
    run = pickle.loads((out / "main_81.pkl").read_bytes())
    cfg, result = run["cfg"], run["result"]
    fabric = fabrics.fabric_for_garment(cfg.garment_id)
    prof = machine.thread_profile(cfg.thread_wt)
    split = float("inf") if not cfg.split_satin else cfg.split_satin_above_mm
    by_id = {r.shape_id: r for r in result.regions}
    sids = sorted({e["shape_id"] for e in sweep if not e["lane_empty"]},
                  key=lambda s: by_id[s].polygon.centroid.x)
    if not sids:
        return None
    cols = []
    for pull in PULLS_MM:
        col = []
        for sid in sids:
            poly = by_id[sid].polygon
            runs, rep = lettering_columns_shape(
                poly, sid, trim_at_mm=fabric.trim_at_mm, spacing_mm=machine.SATIN_SPACING_MM,
                split_above_mm=split, pull_mm=pull, pull_floor_mm=cfg.min_detail_mm,
                underlay_style="none")
            x0, y0, x1, y1 = poly.bounds
            box = (x0 - 0.9, y0 - 0.9, x1 + 0.9, y1 + 0.9)
            m = np.full((int(np.ceil((box[3] - box[1]) * ppm)) + 1,
                         int(np.ceil((box[2] - box[0]) * ppm)) + 1, 3), 255, np.uint8)
            t = max(1, int(round(prof.width_mm * ppm)))
            for r in runs:
                for a, b in zip(r.points, r.points[1:]):
                    cv2.line(m, (int(round((a[0] - box[0]) * ppm)), int(round((a[1] - box[1]) * ppm))),
                             (int(round((b[0] - box[0]) * ppm)), int(round((b[1] - box[1]) * ppm))),
                             (60, 60, 60), t)
            for ring in [poly.exterior, *poly.interiors]:
                cv2.polylines(m, [np.array([((x - box[0]) * ppm, (y - box[1]) * ppm)
                                            for x, y in ring.coords], np.int32)],
                              True, (40, 40, 220), 1, cv2.LINE_AA)
            col.append(m)
        w = max(c.shape[1] for c in col)
        stack = np.vstack([np.pad(c, ((0, 6), (0, w - c.shape[1]), (0, 0)), constant_values=255)
                           for c in col])
        cols.append(ft._label(stack, f"pull {pull:.1f} mm"))
    sheet = ft._hstack(cols, gap=10)
    sheet = ft._label(sheet, "THE, Column lane at several pulls (red = artwork outline, grey = thread "
                              f"at the laid width {prof.width_mm:.2f} mm), {ppm} px/mm; 0.4 = the hat preset",
                      width=sheet.shape[1])
    path = renders / "the_pull_sweep.png"
    cv2.imwrite(str(path), sheet)
    return path


ZOOM_ARMS = ["main_81", "floor_81", "floor_stem_81", "nokeep_81", "nokeep_floor_81",
             "floor_stem_92", "main_92"]
ZOOM_GLYPHS = [("tagline", 1, "A of EAT"), ("tagline", 9, "P of PLAY")]


def counter_zoom(out: Path, renders: Path, ppm: int = 150) -> Path:
    """The two tagline glyphs that carry a counter at 81 mm (the A of EAT and
    the P of PLAY), one row per arm, the artwork outline in red, one scale:
    the evidence for the counter column of the table."""
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    rows = []
    for name in ZOOM_ARMS:
        pk = out / f"{name}.pkl"
        if not pk.exists():
            continue
        run = pickle.loads(pk.read_bytes())          # our own scratch file
        p = run["gen"].p
        img, to_px = ft._render(run["design"], ppm)
        cells = []
        for box, idx, title in ZOOM_GLYPHS:
            g = source_glyphs(p, ft.ROIS[box])[idx]
            x0, y0, x1, y1 = g.bounds
            crop = ft._crop(img, to_px, (x0, y0, x1, y1), margin_mm=0.5).copy()
            a, b = to_px(x0 - 0.5, y0 - 0.5), to_px(x1 + 0.5, y1 + 0.5)
            ox, oy = int(max(0, min(a[0], b[0]))), int(max(0, min(a[1], b[1])))
            for ring in [g.exterior, *g.interiors]:
                pts = np.array([[to_px(x, y)[0] - ox, to_px(x, y)[1] - oy]
                                for x, y in ring.coords], np.int32)
                cv2.polylines(crop, [pts], True, (40, 40, 220), 1, cv2.LINE_AA)
            cells.append(ft._label(crop, f"{title}"))
        rows.append(ft._label(ft._hstack(cells, gap=10), f"{name}  ({ARMS[name][2]}), {ppm} px/mm"))
        del img, run
    w = max(r.shape[1] for r in rows)
    sheet = np.vstack([np.pad(r, ((0, 8), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
    path = renders / "counters_zoom.png"
    cv2.imwrite(str(path), sheet)
    return path


def signature(tab: dict) -> dict:
    """The part of an arm's table a test can pin across platforms: per box,
    the tier string (`S` satin, `R` run, `F` fill, `*` = the Column lane took
    it), each counter's status, stitches and trims. No measured width: those
    are numbers to read, not to pin."""
    out = {}
    for b, v in tab["boxes"].items():
        out[b] = {
            "n": v["n_glyphs"],
            "tiers": " ".join({"satin": "S", "run": "R", "fill": "F"}.get(g["tier"], "?")
                              + ("*" if g["column_lane"] else "") for g in v["glyphs"]),
            "counters": [c["status"] for g in v["glyphs"] for c in g["counters"]],
            "stitches": v["stitches"], "trims": v["trims"],
        }
    return {"arm": tab["arm"], "width_mm": tab["width_mm"], "overrides": tab["overrides"],
            "stitches": tab["stitches"], "trims": tab["trims"], "boxes": out}


LABELS = {"the": list("THE"),
          "tagline": ["E", "A", "T", "bar", "S", "T", "A", "Y", "bar", "P", "L", "A", "Y"],
          "est": list("EST")}


def label_of(box: str, i: int, n: int) -> str:
    ls = LABELS[box]
    return ls[i] if len(ls) == n else f"#{i}"


def markdown(tabs: dict, boxes=BOXES) -> str:
    """The per-glyph table, one block per box and arm, as markdown."""
    lines = []
    for b in boxes:
        lines.append(f"### {b.upper() if b != 'tagline' else 'EAT | STAY | PLAY'}\n")
        for name, tab in tabs.items():
            v = tab["boxes"][b]
            lines.append(f"**{name}** ({tab['label']}, {tab['size_mm'][0]} x {tab['size_mm'][1]} mm): "
                         f"{v['stitches']} stitches, {v['trims']} trims in the box, "
                         f"{v['ink_bare_mm2']}/{v['ink_mm2']} mm2 ink bare\n")
            lines.append("| glyph | tier | lane | src stroke mm | sewn w mm (narrowest) | x src | "
                         "needle offset mm | counters (bare share) | stitches | trims |")
            lines.append("|---|---|---|---|---|---|---|---|---|---|")
            for i, g in enumerate(v["glyphs"]):
                cs = ", ".join(f"{c['status']} {c['bare_share']:.2f}" for c in g["counters"]) or "-"
                lines.append(
                    f"| {label_of(b, i, v['n_glyphs'])} | {g['tier']} | {'yes' if g['column_lane'] else 'no'} "
                    f"| {g['src_stroke_mm']:.2f} | {g['sewn_w_mm']:.2f} ({g['sewn_w_min_mm']:.2f}) "
                    f"| {g['width_ratio']} | {g['needle_offset_p50_mm']:+.2f} | {cs} "
                    f"| {g['stitches']} | {g['trims']} |")
            lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", choices=ARM_ORDER)
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--markdown", nargs="*", metavar="ARM",
                    help="print the per-glyph table of these saved arms (default: the four Kent named)")
    ap.add_argument("--signatures", action="store_true",
                    help="write <out>/signatures.json from the saved tables")
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    if a.arm:
        run_one(a.arm, a.out)
    if a.analyze:
        for name in ARM_ORDER:
            pk = a.out / f"{name}.pkl"
            if not pk.exists():
                continue
            run = pickle.loads(pk.read_bytes())     # our own scratch file
            res = analyze_arm(name, run)
            if name == "main_81":
                p = run["gen"].p
                from tools import fremont_triage as ft
                gl = source_glyphs(p, ft.ROIS["the"])
                res["pull_sweep"] = pull_sweep(run, res["boxes"]["the"]["glyphs"], gl)
            (a.out / f"{name}_table.json").write_text(json.dumps(res, indent=1))
            print(f"{name}: analysed", flush=True)
            del run
    if a.markdown is not None:
        names = a.markdown or KENT_ARMS
        print(markdown({n: json.loads((a.out / f"{n}_table.json").read_text()) for n in names}))
    if a.signatures:
        tabs = {n: json.loads((a.out / f"{n}_table.json").read_text())
                for n in ARM_ORDER if (a.out / f"{n}_table.json").exists()}
        sigs = {n: signature(t) for n, t in tabs.items()}
        (a.out / "signatures.json").write_text(json.dumps(sigs, indent=1))
        (a.out / "tier_table.json").write_text(json.dumps({"arms": tabs}, indent=1))
        print(f"signatures.json, tier_table.json: {len(sigs)} arms")
    if a.sheets:
        renders = a.renders or a.out / "renders"
        sw = json.loads((a.out / "main_81_table.json").read_text()).get("pull_sweep", [])
        for pth in build_sheets(a.out, renders) + [sweep_sheet(a.out, renders, sw),
                                                    counter_zoom(a.out, renders)]:
            print(pth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
