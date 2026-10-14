"""detail_layer vs hairline_from_lines: one lines route or two? (2026-10-14)

    python -m tools.detail_vs_lines run --image owl_kent [--arms off,detail,lines,lines_chain,both]
    python -m tools.detail_vs_lines table

MEASURE ONLY. No core edit.

Two OFF flags both sew FDoG (Kang 2007) lines over the finished fills, last:

- `cfg.detail_layer` (`stage6_detail`): DARK lines only, no strand test, sewn
  as a three-pass BEAN run (forward, back, forward), thread = the cone nearest
  the median colour under all the lines, one block. Exposed in the Studio as
  "Add fine detail lines" (#123).
- `cfg.hairline` + `cfg.hairline_from_lines` (`stage6_hairline_lines`, #882):
  BOTH polarities, a ridge test (a strand, not an edge), a single RUN pass, one
  block per polarity. `cfg.hairline_lines_chain` (#917) sews hops between
  strands needle-down over thread already laid instead of cutting. The Studio
  does not expose it, and it applies on the photo lanes only.

Arms (one `run_stages` per image, then one `plan_stitches` per arm; the route
is #882's: photo lane forced, `photo_prep` off, 127 mm, 40 wt):

    off, detail, lines, lines_chain, both (= detail + lines together)

Per arm: stitches, trims, colour changes, thread laid, thread over bare
fabric and the flight over bare fabric of `tools.hairline_travel.measure_plan`
(a trimmed-jump flight carries no thread; `tests/test_chaining.py::
_thread_bare_mm` counts it as thread, so it is NOT used), and the uncovered
artwork new against OFF in mm2 (`tools.hairline_renders.bare_cells`, the
preflight instrument).

Overlap, from the SEWN centrelines of the `detail` and `lines` arms: every
strand of one route is sampled every `STEP_MM`; the share of its length within
`TOL_MM` (a laid 40 wt thread, `machine.COVERAGE_THREAD_W_MM`) of the other
route's centrelines is its overlap. A strand is SHARED at >= `SHARED_FRAC`,
PARTIAL below that down to `PARTIAL_FRAC`, ONLY under it. Each detail line is
also read by the lines route's own ridge test, so the lines only `detail` sews
are split into strand-like (would pass) and edge-like (would be refused).

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
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
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, preflight, stitches, stitchviz  # noqa: E402
from digitizer_core import stage6_hairline_lines as L  # noqa: E402
from digitizer_core.adapter import UNITS_PER_MM, plan_to_design  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from digitizer_core.stage6_hairline import _SRC_MIN_CONTRAST  # noqa: E402
from tools.hairline_lines_trial import measure, write_jpeg  # noqa: E402
from tools.hairline_renders import bare_cells, bare_new_mm2  # noqa: E402
from tools.hairline_travel import measure_plan  # noqa: E402

PHOTO = ROOT / "testdata" / "photo"
IMAGES = {"owl_kent": PHOTO / "owl_kent.jpg", "photo_owl_pale": PHOTO / "photo_owl_pale.png",
          "fur_ramp": PHOTO / "fur_ramp.png"}
WIDTH_MM = 127.0
WT = 40
ROUTE = {"forced_class": "photo_subject", "photo_prep": False}   # #882's `classical`
# arm -> (detail_layer, hairline + from_lines, hairline_lines_chain)
ARMS = {"off": (False, False, False), "detail": (True, False, False),
        "lines": (False, True, False), "lines_chain": (False, True, True),
        "both": (True, True, False)}
LABELS = {"off": "OFF", "detail": "detail_layer", "lines": "hairline_from_lines",
          "lines_chain": "lines + chain", "both": "both on"}
PICTURE_ARMS = ("off", "detail", "lines", "both")
TOL_MM = machine.COVERAGE_THREAD_W_MM
STEP_MM = 0.1
SHARED_FRAC = 0.8
PARTIAL_FRAC = 0.3
PPM = 40.0
FULL_W = 520            # px, each full-design panel
BOX_MM = (14.0, 9.0)
PARTS = ROOT / "debug_out" / "detail_vs_lines"
OUT = ROOT.parent / "docs" / "renders" / "claude-detail-layer-vs-lines"


def arm_cfg(arm: str, width: float = WIDTH_MM, wt: int = WT, route: dict | None = None):
    detail, lines, chain = ARMS[arm]
    return PipelineConfig(target_width_mm=width, detail_layer=detail, hairline=lines,
                          hairline_from_lines=lines, hairline_lines_chain=chain,
                          thread_wt=wt, **(ROUTE if route is None else route))


# --- the lines each route sewed ----------------------------------------------

def _path_mm(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def detail_strands(plan) -> list[dict]:
    """The detail layer's lines: one dict per BEAN run of shape `detail`.
    `mm` is the line's own length (the bean sews it `BEAN_PASSES` times)."""
    out = []
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id == "detail" and r.kind == stitches.BEAN and len(r.points) >= 2:
                out.append({"pts": [tuple(p) for p in r.points],
                            "mm": _path_mm(r.points) / machine.BEAN_PASSES})
    return out


def line_strands(plan) -> list[dict]:
    """The line route's strands: one dict per RUN of shape `hairline_lines`."""
    out = []
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id == L.SHAPE_ID and r.kind == stitches.RUN and len(r.points) >= 2:
                out.append({"pts": [tuple(p) for p in r.points], "mm": _path_mm(r.points)})
    return out


# --- overlap -----------------------------------------------------------------

def _tree(strands):
    geoms = [LineString(s["pts"]) for s in strands if len(s["pts"]) >= 2]
    return shapely.STRtree(geoms) if geoms else None


def near_share(pts, tree, tol: float = TOL_MM, step: float = STEP_MM) -> float:
    """The share of the polyline `pts` (0..1, by length) within `tol` mm of any
    geometry in `tree`."""
    if tree is None or len(pts) < 2:
        return 0.0
    path = LineString(pts)
    if path.length <= 0:
        return 0.0
    n = max(2, int(path.length / step))
    pp = shapely.line_interpolate_point(path, np.linspace(0.0, 1.0, n + 1), normalized=True)
    hit = tree.query(pp, predicate="dwithin", distance=tol)
    covered = np.zeros(len(pp), bool)
    covered[hit[0]] = True
    return float(covered.mean())


def classify(share: float, shared: float = SHARED_FRAC, partial: float = PARTIAL_FRAC) -> str:
    return "shared" if share >= shared else "partial" if share >= partial else "only"


def side(strands, other_tree, tol: float = TOL_MM) -> dict:
    """How one route's strands sit against the other route's centrelines."""
    shares = [near_share(s["pts"], other_tree, tol) for s in strands]
    out = {"n": len(strands), "mm": round(sum(s["mm"] for s in strands), 1),
           "near_mm": round(sum(sh * s["mm"] for sh, s in zip(shares, strands)), 1)}
    for kind in ("shared", "partial", "only"):
        pick = [s for sh, s in zip(shares, strands) if classify(sh) == kind]
        out[kind] = {"n": len(pick), "mm": round(sum(s["mm"] for s in pick), 1)}
    return out, shares


def overlap(detail: list[dict], lines: list[dict], tol: float = TOL_MM) -> dict:
    """Both directions, plus the tolerance sensitivity of the length share."""
    d_side, d_sh = side(detail, _tree(lines), tol)
    l_side, l_sh = side(lines, _tree(detail), tol)
    sens = {}
    for t in (0.2, 0.4, 0.8):
        sens[f"{t:g}"] = {
            "detail_near_pct": _pct(sum(near_share(s["pts"], _tree(lines), t) * s["mm"]
                                        for s in detail), sum(s["mm"] for s in detail)),
            "lines_near_pct": _pct(sum(near_share(s["pts"], _tree(detail), t) * s["mm"]
                                       for s in lines), sum(s["mm"] for s in lines))}
    return {"tol_mm": tol, "detail": d_side, "lines": l_side, "tolerance": sens,
            "detail_shares": [round(x, 3) for x in d_sh],
            "lines_shares": [round(x, 3) for x in l_sh]}


def _pct(a: float, b: float) -> float:
    return round(100.0 * a / b, 1) if b > 0 else 0.0


# --- what the ridge test says about each route's lines ------------------------

def ridge_reads(strands, sp, cfg, polarity: str | None = None) -> list[tuple[str, float]]:
    """For each strand -> (polarity read, contrast). `polarity` fixed reads that
    one only; None reads both and keeps the stronger (the line route's own
    ridge test, `stage6_hairline_lines.ridge_contrast`)."""
    prof = machine.thread_profile(cfg.thread_wt)
    light = L._light(sp)
    core = 0.5 * prof.hairline_run_width_mm
    side0 = 0.5 * prof.hairline_max_width_mm
    side1 = side0 + L._SIDE_REACH_PX / sp.px_per_mm
    step = L._PROFILE_STEP_WIDTHS * prof.width_mm
    out = []
    for s in strands:
        reads = {}
        for pol in ((polarity,) if polarity else ("dark", "light")):
            reads[pol] = L.ridge_contrast(s["pts"], light, sp, polarity=pol, core_mm=core,
                                          side0_mm=side0, side1_mm=side1, step_mm=step)
        pol = max(reads, key=reads.get)
        out.append((pol, reads[pol]))
    return out


def ridge_split(strands, reads, shares) -> dict:
    """`strands` split by ridge read (strand-like >= the tier's contrast floor
    vs edge-like) and by overlap with the other route."""
    out = {}
    for like in ("strand", "edge"):
        row = {}
        for kind in ("shared", "partial", "only"):
            pick = [s for s, (_p, c), sh in zip(strands, reads, shares)
                    if (c >= _SRC_MIN_CONTRAST) == (like == "strand") and classify(sh) == kind]
            row[kind] = {"n": len(pick), "mm": round(sum(s["mm"] for s in pick), 1)}
        out[like] = row
    return out


def polarity_split(strands, reads, shares) -> dict:
    out = {}
    for pol in ("dark", "light"):
        row = {}
        for kind in ("shared", "partial", "only"):
            pick = [s for s, (p, _c), sh in zip(strands, reads, shares)
                    if p == pol and classify(sh) == kind]
            row[kind] = {"n": len(pick), "mm": round(sum(s["mm"] for s in pick), 1)}
        out[pol] = row
    return out


# --- per-arm numbers -----------------------------------------------------------

def route_stitches(plan) -> dict:
    d = sum(len(r.points) for b in plan.blocks for r in b.runs if r.shape_id == "detail")
    h = sum(len(r.points) for b in plan.blocks for r in b.runs if r.shape_id == L.SHAPE_ID)
    return {"detail_stitches": d, "line_stitches": h}


def arm_row(plan, result, p, cfg, base_bare) -> tuple[dict, tuple]:
    row = measure(plan)
    t = measure_plan(plan, with_legacy=False)
    row.update({k: t[k] for k in ("thread_bare_mm", "thread_exposed_legs", "flight_bare_mm",
                                  "trims_block_start", "trims_in_shape",
                                  "trims_between_shapes", "flight_total_mm")})
    row.update(route_stitches(plan))
    row["blocks"] = len(plan.blocks)
    bare = bare_cells(plan, result, p)
    row["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
    row["bare_new_mm2"] = 0.0 if base_bare is None else round(bare_new_mm2(bare, base_bare), 2)
    return row, bare


# --- pictures ----------------------------------------------------------------

def densest_window(points, size) -> tuple[float, float, float, float] | None:
    """The `size` window (mm) holding the most of `points`."""
    if len(points) == 0:
        return None
    pts = np.asarray(points, float)
    best = (-1, None)
    # candidates: every 25th point keeps this O(n^2/25) on a dense design
    for cx, cy in pts[:: max(1, len(pts) // 400)]:
        box = (cx - size[0] / 2, cy - size[1] / 2, cx + size[0] / 2, cy + size[1] / 2)
        n = int(((pts[:, 0] >= box[0]) & (pts[:, 0] <= box[2])
                 & (pts[:, 1] >= box[1]) & (pts[:, 1] <= box[3])).sum())
        if n > best[0]:
            best = (n, box)
    return best[1]


def _sample_points(strands) -> list:
    out = []
    for s in strands:
        out.extend(s["pts"])
    return out


def render_arm(plan, arm: str, wt: int) -> dict:
    design = plan_to_design(plan, name=f"{arm}")
    img = stitchviz.render_design(design, px_per_mm=PPM,
                                  thread_mm=machine.thread_profile(wt).width_mm)
    _size, to_px = stitchviz._frame(design.get("stitches") or [], PPM, 2.0)
    origin = to_px({"x": 0.0, "y": 0.0})
    tx = to_px({"x": UNITS_PER_MM, "y": 0.0})
    ty = to_px({"x": 0.0, "y": -UNITS_PER_MM})
    meta = {"origin": list(origin), "x": [tx[0] - origin[0], tx[1] - origin[1]],
            "y": [ty[0] - origin[0], ty[1] - origin[1]]}
    return {"img": img, "meta": meta}


def _px(meta, x, y):
    o, ax, ay = meta["origin"], meta["x"], meta["y"]
    return (o[0] + ax[0] * x + ay[0] * y, o[1] + ax[1] * x + ay[1] * y)


def _crop(img, meta, box):
    a, b = _px(meta, box[0], box[1]), _px(meta, box[2], box[3])
    x0, x1 = sorted((max(int(a[0]), 0), max(int(b[0]), 0)))
    y0, y1 = sorted((max(int(a[1]), 0), max(int(b[1]), 0)))
    return img[y0:y1, x0:x1].copy(), (x0, y0)


def _label(img, text):
    band = np.full((34, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, text, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2, cv2.LINE_AA)
    return np.vstack([band, img])


def _hstack(tiles, gap=8):
    h = min(t.shape[0] for t in tiles)
    out = []
    for t in tiles:
        if t.shape[0] != h:
            t = cv2.resize(t, (int(t.shape[1] * h / t.shape[0]), h), interpolation=cv2.INTER_AREA)
        out += [t, np.full((h, gap, 3), 255, np.uint8)]
    return np.hstack(out[:-1])


def overlay_panel(base_img, meta, box, detail, lines):
    """The OFF render over `box` with the two routes' centrelines drawn: the
    detail layer's wide and blue, the line route's thin and red on top, so a
    shared line shows a red core in a blue halo."""
    crop, (x0, y0) = _crop(base_img, meta, box)
    for strands, colour, width in ((detail, (230, 120, 20), 5), (lines, (30, 30, 230), 1)):
        for s in strands:
            q = np.array([_px(meta, x, y) for x, y in s["pts"]])
            q = np.round(q - [x0, y0]).astype(np.int32)
            cv2.polylines(crop, [q], False, colour, width, cv2.LINE_AA)
    return crop


def compose_pictures(image: str, renders: dict, box, detail, lines, OUT_DIR: Path) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    full, zoom = [], []
    for arm in PICTURE_ARMS:
        if arm not in renders:
            continue
        r = renders[arm]
        k = FULL_W / r["img"].shape[1]
        small = cv2.resize(r["img"], None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        full.append(_label(small, LABELS[arm]))
        if box is not None:
            c, _ = _crop(r["img"], r["meta"], box)
            zoom.append(_label(c, LABELS[arm]))
    if "off" in renders and box is not None:
        zoom.append(_label(overlay_panel(renders["off"]["img"], renders["off"]["meta"], box,
                                         detail, lines), "OFF + lines (blue detail, red strands)"))
    if full:
        write_jpeg(OUT_DIR / f"{image}_full.jpg", _hstack(full))
    if zoom:
        write_jpeg(OUT_DIR / f"{image}_zoom.jpg", _hstack(zoom))


# --- run ---------------------------------------------------------------------

def run_image(image: str, arms: list[str], width: float = WIDTH_MM, wt: int = WT,
              pictures: bool = True, check_off: bool = False) -> dict:
    path = IMAGES[image]
    t0 = time.perf_counter()
    # Stages 0-4 once, on the config that carries source pixels for both routes.
    result = run_stages(path, arm_cfg("both", width, wt))
    print(f"{image}: stages 0-4 {time.perf_counter() - t0:.0f}s, class {result.design_class}",
          flush=True)
    p = preflight.prep(path, arm_cfg("off", width, wt), design_class=result.design_class)
    rows, plans, base_bare = {}, {}, None
    for arm in arms:
        t1 = time.perf_counter()
        cfg = arm_cfg(arm, width, wt)
        plan = plan_stitches(result, cfg)
        row, bare = arm_row(plan, result, p, cfg, base_bare)
        if arm == "off":
            base_bare = bare
        rows[arm] = row
        plans[arm] = plan
        print(f"{image} {arm}: {time.perf_counter() - t1:.0f}s "
              + json.dumps({k: row[k] for k in ("stitches", "trims", "thread_bare_mm",
                                                "flight_bare_mm", "bare_new_mm2")}), flush=True)
    off_check = None
    if check_off and "off" in plans:
        # The arms share one run_stages made on the `both` config; OFF planned
        # from it must be the plan a fresh OFF run makes (md5 over the runs).
        c = arm_cfg("off", width, wt)
        fresh = measure(plan_stitches(run_stages(path, c), c))["md5"]
        off_check = {"shared_stages_md5": rows["off"]["md5"], "fresh_md5": fresh,
                     "identical": rows["off"]["md5"] == fresh}
        print("off check", off_check, flush=True)
    out = {"image": image, "width_mm": width, "thread_wt": wt, "route": ROUTE,
           "class": result.design_class, "arms": rows, "off_check": off_check}
    sp = result.source_pixels
    if "detail" in plans and "lines" in plans:
        det, lin = detail_strands(plans["detail"]), line_strands(plans["lines"])
        ov = overlap(det, lin)
        cfg = arm_cfg("lines", width, wt)
        d_reads = ridge_reads(det, sp, cfg, polarity="dark")
        l_reads = ridge_reads(lin, sp, cfg)
        ov["detail_by_ridge"] = ridge_split(det, d_reads, ov.pop("detail_shares"))
        ov["lines_by_polarity"] = polarity_split(lin, l_reads, ov.pop("lines_shares"))
        w = [x for x in plans["lines"].warnings if x["code"] == "HAIRLINE_TIER_SEWN"]
        ov["lines_census"] = ({k: w[0].get(k) for k in ("strands", "dropped", "found",
                                                         "refused_no_ridge", "sewn_by_polarity")}
                              if w else {})
        out["overlap"] = ov
        if "both" in plans:
            bd, bl = detail_strands(plans["both"]), line_strands(plans["both"])
            out["both_check"] = {"detail_lines": len(bd), "line_strands": len(bl),
                                 "same_as_alone": [len(bd) == len(det), len(bl) == len(lin)]}
        if pictures:
            box = densest_window(_sample_points(det) + _sample_points(lin), BOX_MM)
            renders = {a: render_arm(plans[a], a, wt) for a in PICTURE_ARMS if a in plans}
            compose_pictures(image, renders, box, det, lin, OUT)
            out["zoom_box_mm"] = [round(v, 1) for v in box] if box else None
    PARTS.mkdir(parents=True, exist_ok=True)
    (PARTS / f"{image}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out["overlap"], indent=1) if "overlap" in out else "no overlap (needs detail+lines)",
          flush=True)
    return out


# --- table -------------------------------------------------------------------

def markdown(rows: dict) -> str:
    lines = ["### Per arm (127 mm, 40 wt, #882's `classical` route)", "",
             "| image | arm | stitches | trims | colour chg | thread m | thread over bare mm "
             "| flight over bare mm | uncovered new mm2 | stitches under 1 mm | detail stitches "
             "| line stitches |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for img, r in rows.items():
        for arm, a in r["arms"].items():
            lines.append(f"| {img} | {arm} | {a['stitches']:,} | {a['trims']} | {a['color_changes']} "
                         f"| {a['thread_m']} | {a['thread_bare_mm']} | {a['flight_bare_mm']} "
                         f"| {a['bare_new_mm2']} | {a['under_1mm']:,} | {a['detail_stitches']:,} "
                         f"| {a['line_stitches']:,} |")
    lines += ["", "### Overlap of the sewn centrelines (within 0.4 mm of the other route)", "",
              "| image | route | strands | mm | shared (>=80%) | partial (30-80%) | only (<30%) "
              "| mm near the other route |", "|---|---|---|---|---|---|---|---|"]
    for img, r in rows.items():
        ov = r.get("overlap")
        if not ov:
            continue
        for route in ("detail", "lines"):
            s = ov[route]
            lines.append(f"| {img} | {route} | {s['n']} | {s['mm']} | {s['shared']['n']} / {s['shared']['mm']} mm "
                         f"| {s['partial']['n']} / {s['partial']['mm']} mm "
                         f"| {s['only']['n']} / {s['only']['mm']} mm | {s['near_mm']} |")
    lines += ["", "### The detail layer's lines, read by the line route's ridge test", "",
              "| image | strand-like: shared / partial / only (mm) | edge-like: shared / partial / only (mm) |",
              "|---|---|---|"]
    for img, r in rows.items():
        ov = r.get("overlap")
        if not ov:
            continue
        cells = []
        for like in ("strand", "edge"):
            d = ov["detail_by_ridge"][like]
            cells.append(" / ".join(f"{d[k]['n']} ({d[k]['mm']})" for k in ("shared", "partial", "only")))
        lines.append(f"| {img} | {cells[0]} | {cells[1]} |")
    lines += ["", "### The line route's strands by polarity read (the stronger ridge read)", "",
              "| image | dark: shared / partial / only (mm) | light: shared / partial / only (mm) |",
              "|---|---|---|"]
    for img, r in rows.items():
        ov = r.get("overlap")
        if not ov:
            continue
        cells = []
        for pol in ("dark", "light"):
            d = ov["lines_by_polarity"][pol]
            cells.append(" / ".join(f"{d[k]['n']} ({d[k]['mm']})" for k in ("shared", "partial", "only")))
        lines.append(f"| {img} | {cells[0]} | {cells[1]} |")
    return "\n".join(lines) + "\n"


def cmd_table(args) -> int:
    rows = {}
    for img in IMAGES:
        f = PARTS / f"{img}.json"
        if f.exists():
            rows[img] = json.loads(f.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "table.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    (OUT / "table.md").write_text(markdown(rows), encoding="utf-8")
    sys.stdout.write(markdown(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--image", required=True, choices=sorted(IMAGES))
    r.add_argument("--arms", default=",".join(ARMS))
    r.add_argument("--width", type=float, default=WIDTH_MM)
    r.add_argument("--no-pictures", action="store_true")
    r.add_argument("--check-off", action="store_true")
    sub.add_parser("table")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        arms = [a for a in args.arms.split(",") if a]
        bad = [a for a in arms if a not in ARMS]
        if bad:
            ap.error(f"unknown arm(s): {bad}")
        run_image(args.image, arms, args.width, pictures=not args.no_pictures,
                  check_off=args.check_off)
        return 0
    return cmd_table(args)


if __name__ == "__main__":
    raise SystemExit(main())
