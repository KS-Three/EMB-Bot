"""Where does a jagged edge ENTER? One zoomed strip per pin, every stage.

Built 2026-11-13 for the jag-source trace (`docs/jag-source-2026-11-13.md`):
Kent pins "should be smooth / straight / square" on a render; this puts the
art's own pixels (native resolution), the stage-3 mask, the stage-4 polygon,
the stage-5 polygon, our needle points and thread, and the pro's stitches
side by side at that pin, so the stage that adds the jag can be named by eye.

    # one digitize, every stage's geometry pickled (ONE at a time on the laptop)
    python -m tools.jag_strips capture NAME ART WIDTH_MM GARMENT OUT.pkl [KEY=JSON ...]
    # strips for a spots file (pins from a defect-marks sitting)
    python -m tools.jag_strips strips SPOTS.json CAPDIR OUTDIR [ID ...]
    # OFF | ON | pro thread crops at the same spots, and full renders
    python -m tools.jag_strips offon SPOTS.json CAP_OFF CAP_ON OUTDIR NAME
    # edge_wobble + curve_fidelity + bare fabric inside the art, OFF vs ON
    python -m tools.jag_strips metrics SPOTS.json CAP_OFF CAP_ON NAME [NAME ...]

A spot: {"id", "cap" (pickle name), "sit" ("1110"|"1111"|"1112"), "item" (kit
id), "pin" (index in that item's pins), "pro" (a `pro_baseline.resolve` spec,
optional), "half_mm" (window half-width, optional), "at" ([x, y] design mm,
optional: overrides the pin)}. Pins live in the gitignored sittings under
`eye_pairs_out/` (`EMB_EYE_PAIRS` to point elsewhere); a lane has none, so
read them from the primary checkout. Pictures are gitignored output.

Frames: a pin is design mm from the stitch bbox's top-left, y down
(`stitchviz._frame`); the plan is mm about the art box's centre, y down;
the working raster is `mm * px_per_mm + centre`; the source pixel under it is
`(px + 0.5) / upscale - 0.5` (`Prep.upscale`, cv2's half-pixel convention).
Today's design is phase-correlated against the kit's render so a pin from an
older tree still lands on the same spot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DIGITIZER))

D = 64.0  # display px per mm
EYE = Path(os.environ.get("EMB_EYE_PAIRS") or DIGITIZER / "eye_pairs_out")
SITS = {"1110": ("defect-marks-1110", "marks.export-kent-20261110.json"),
        "1111": ("defect-marks-1111", "marks.json"), "1112": ("defect-marks-1112", "marks.json")}


# ------------------------------------------------------------------ capture
def capture(name: str, art: str, width: float, garment: str, out: str, extra: dict) -> dict:
    """The service's call sequence (`photo_corpus`'s worker), with stage 3's
    masks and stage 5's polygons caught off `debugviz`, everything pickled."""
    import tempfile
    from digitizer_core import PipelineConfig, debugviz
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode, _parse_config
    from tools import pro_pair

    req = pro_pair.request(width, garment, extra)
    cap: dict = {}

    def noop(*_a, **_k):
        return None

    for nm in ("stage1", "stage1_photo_prep", "stage2", "stage4", "stage6"):
        setattr(debugviz, nm, noop)
    debugviz.stage3 = lambda d, rgb, masks: cap.__setitem__("masks", [
        (m.crop.copy(), tuple(m.origin), None) for m in masks])
    debugviz.stage5 = lambda d, planned, size, chart=None: cap.__setitem__("planned", [
        (p.polygon, p.region.thread_index, p.region.shape_id, None) for p in planned])
    cfg = PipelineConfig(**{**_parse_config(json.dumps(req)), "debug_dir": Path(tempfile.mkdtemp(prefix="jag_"))})
    data = open(art, "rb").read()
    t0 = time.time()
    gen = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    p = gen.p
    blob = {"name": name, "art": art, "width": width, "garment": garment, "req": req,
            "rgb": p.rgb, "bg_mask": p.bg_mask, "px_per_mm": p.px_per_mm, "art_bbox": p.art_bbox,
            "input_px_per_mm": p.input_px_per_mm, "native_rgb": p.native_rgb,
            "native_alpha": p.native_alpha, "upscale": p.upscale, "class": gen.classification_class,
            "regions": [(r.polygon, r.thread_index, r.shape_id, dict(r.meta)) for r in result.regions],
            "masks": cap.get("masks"), "planned": cap.get("planned"),
            "runs": [[(b.rgb, [(list(r.points), r.kind, r.jump, r.trim, r.shape_id) for r in b.runs])]
                     for b in plan.blocks],
            "design": plan_to_design(plan, name=name), "elapsed": time.time() - t0}
    with open(out, "wb") as f:
        pickle.dump(blob, f)
    return blob


# ------------------------------------------------------------------- frames
def kit_item(sit: str, item: str):
    d, mf = SITS[sit]
    kit = json.loads((EYE / d / "kit.json").read_text(encoding="utf-8"))
    it = {i["id"]: i for i in kit["items"]}[item]
    marks = json.loads((EYE / d / mf).read_text(encoding="utf-8"))["items"][item]
    return it, marks, EYE / d / "img"


def pin_mm(it: dict, pin: dict) -> tuple[float, float]:
    """A pin in design mm; the 11-10 sitting stored some as image fractions only."""
    if pin.get("x_mm") is not None:
        return pin["x_mm"], pin["y_mm"]
    return (pin["x"] * it["img_w"] / it["px_per_mm"] - it["pad_mm"],
            pin["y"] * it["img_h"] / it["px_per_mm"] - it["pad_mm"])


def bbox_units(design: dict):
    xs = [s["x"] for s in design["stitches"] if s.get("type") in ("stitch", "jump")]
    ys = [s["y"] for s in design["stitches"] if s.get("type") in ("stitch", "jump")]
    return min(xs), max(xs), min(ys), max(ys)


def kit_offset(kit_png, design: dict):
    """(dx, dy) mm to ADD to a kit pin so it lands on `design`'s frame, + response."""
    from digitizer_core.stitchviz import render_design
    a = cv2.cvtColor(cv2.imread(str(kit_png)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    b = cv2.cvtColor(render_design(design, px_per_mm=12.0, pad_mm=2.0), cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    A = np.full((h, w), 255, np.float32); A[:a.shape[0], :a.shape[1]] = a
    B = np.full((h, w), 255, np.float32); B[:b.shape[0], :b.shape[1]] = b
    (sx, sy), resp = cv2.phaseCorrelate(255 - A, 255 - B)
    return sx / 12.0, sy / 12.0, resp


def design_runs_mm(design: dict):
    """[(rgb, [(x, y) plan mm, y down])] continuous thread paths of a Design."""
    cols = design.get("colors") or [{"r": 0, "g": 0, "b": 0}]
    ci, paths, cur = 0, [], []
    for s in design["stitches"]:
        if s.get("type") == "stitch":
            cur.append((s["x"] / 10.0, -s["y"] / 10.0))
            continue
        if cur:
            paths.append((ci, cur))
        cur = []
        if s.get("type") == "color":
            ci = min(ci + 1, len(cols) - 1)
    if cur:
        paths.append((ci, cur))
    return [((cols[c]["r"], cols[c]["g"], cols[c]["b"]), p) for c, p in paths]


# ------------------------------------------------------------------- panels
def panel_from_raster(img, to_src, x0, y0, wmm, hmm):
    W, H = int(wmm * D), int(hmm * D)
    u, v = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    sx, sy = to_src(x0 + u / D, y0 + v / D)
    return cv2.remap(img, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_NEAREST,
                     borderMode=cv2.BORDER_CONSTANT,
                     borderValue=(255, 255, 255) if img.ndim == 3 else 0)


def rings(poly):
    for g in ([poly] if poly.geom_type == "Polygon" else list(getattr(poly, "geoms", []))):
        if g.is_empty:
            continue
        yield list(g.exterior.coords)
        for h in g.interiors:
            yield list(h.coords)


def draw_poly(img, coords, x0, y0, color, thick=2, dots=False):
    pts = np.array([((x - x0) * D, (y - y0) * D) for x, y in coords], np.float64)
    cv2.polylines(img, [np.round(pts * 4).astype(np.int32)], True, color, thick, cv2.LINE_AA, shift=2)
    if dots:
        for x, y in pts:
            cv2.circle(img, (int(round(x)), int(round(y))), 4, color, -1, cv2.LINE_AA)


def label(img, text):
    cv2.rectangle(img, (0, 0), (img.shape[1], 22), (255, 255, 255), -1)
    cv2.putText(img, text, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return img


def thread_panel(paths, x0, y0, wmm, hmm, dots=True):
    W, H = int(wmm * D), int(hmm * D)
    img = np.full((H, W, 3), (223, 232, 235), np.uint8)
    tw = max(2, int(round(0.4 * D * 0.6)))
    for rgb, pts in paths:
        a = np.array(pts)
        inwin = (a[:, 0] > x0 - 3) & (a[:, 0] < x0 + wmm + 3) & (a[:, 1] > y0 - 3) & (a[:, 1] < y0 + hmm + 3)
        if not inwin.any():
            continue
        q = np.round((a - [x0, y0]) * D * 4).astype(np.int32)
        col = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
        dark = tuple(int(c * 0.55) for c in col)
        for i in range(1, len(q)):
            if inwin[i] or inwin[i - 1]:
                cv2.line(img, tuple(q[i - 1]), tuple(q[i]), dark, tw + 2, cv2.LINE_AA, shift=2)
                cv2.line(img, tuple(q[i - 1]), tuple(q[i]), col, tw, cv2.LINE_AA, shift=2)
        if dots:
            for i in np.flatnonzero(inwin):
                cv2.circle(img, (int(q[i][0] / 4), int(q[i][1] / 4)), 3, (0, 0, 255), -1)
    return img


class _Ctx:
    """One capture's frames, cached per pickle."""
    _cache: dict = {}

    def __init__(self, path):
        self.cap = cap = self._cache.get(path) or pickle.load(open(path, "rb"))
        self._cache[path] = cap
        self.ppm = cap["px_per_mm"]
        bx0, by0, bx1, by1 = cap["art_bbox"]
        self.cx, self.cy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
        self.src_ppm = cap["input_px_per_mm"] or self.ppm

    def to_work(self, mx, my):
        return mx * self.ppm + self.cx, my * self.ppm + self.cy

    def to_native(self, mx, my):
        wx, wy = self.to_work(mx, my)
        sx, sy = self.cap["upscale"]
        return (wx + 0.5) / sx - 0.5, (wy + 0.5) / sy - 0.5

    def work_bgr(self):
        w = cv2.cvtColor(self.cap["rgb"], cv2.COLOR_RGB2BGR).copy()
        w[self.cap["bg_mask"]] = (200, 200, 200)
        return w

    def source_panel(self, x0, y0, wmm, hmm):
        cap = self.cap
        if cap["native_rgb"] is None:
            return panel_from_raster(self.work_bgr(), self.to_work, x0, y0, wmm, hmm)
        nat = cap["native_rgb"].astype(np.float32)
        if cap["native_alpha"] is not None:
            a = cap["native_alpha"].astype(np.float32)[..., None] / 255.0
            nat = nat * a + 200.0 * (1 - a)
        src = cv2.cvtColor(np.clip(nat, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        return panel_from_raster(src, self.to_native, x0, y0, wmm, hmm)

    def plan_mm(self, spot):
        it, marks, imgdir = kit_item(spot["sit"], spot["item"])
        pin = marks["pins"][spot["pin"]]
        px, py = spot.get("at") or pin_mm(it, pin)
        key = ("off", id(self.cap))
        if key not in self._cache:
            self._cache[key] = kit_offset(imgdir / it["render"], self.cap["design"])
        ox, oy, _r = self._cache[key]
        x0u, _x1u, _y0u, y1u = bbox_units(self.cap["design"])
        return px + ox + x0u / 10.0, py + oy - y1u / 10.0, (px, py), it, pin, imgdir


def pro_panel(spot, it, imgdir, pxy, half):
    from tools import pro_baseline as pb
    from tools.eye_pairs.filearm import design_from_file
    key = ("pro", spot["pro"])
    if key not in _Ctx._cache:
        prod = design_from_file(pb.resolve(spot["pro"]))
        _Ctx._cache[key] = (prod, kit_offset(imgdir / it["pro"], prod) if it.get("pro") else (0, 0, 0))
    prod, (pox, poy, _r) = _Ctx._cache[key]
    qx0, _qx1, _qy0, qy1 = bbox_units(prod)
    qmx, qmy = pxy[0] + pox + qx0 / 10.0, pxy[1] + poy - qy1 / 10.0
    return label(thread_panel(design_runs_mm(prod), qmx - half, qmy - half, 2 * half, 2 * half),
                 "pro: thread + needle")


def _hstack(panels, title1, title2):
    for p in panels:
        cv2.circle(p, (p.shape[1] // 2, p.shape[0] // 2), 6, (0, 0, 255), 1)
    hh = max(p.shape[0] for p in panels)
    row = np.hstack([cv2.copyMakeBorder(p, 0, hh - p.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(40, 40, 40))
                     for p in panels])
    title = np.full((44, row.shape[1], 3), 255, np.uint8)
    cv2.putText(title, title1, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(title, title2[:150], (6, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 160), 1, cv2.LINE_AA)
    return np.vstack([title, row])


def strip(spot: dict, capdir: str) -> np.ndarray:
    ctx = _Ctx(os.path.join(capdir, spot["cap"] + ".pkl"))
    cap = ctx.cap
    pmx, pmy, pxy, it, pin, imgdir = ctx.plan_mm(spot)
    half = spot.get("half_mm") or max(3.0, 6.0 / ctx.src_ppm)
    x0, y0, w = pmx - half, pmy - half, 2 * half
    p1 = ctx.source_panel(x0, y0, w, w)
    pw = panel_from_raster(ctx.work_bgr(), ctx.to_work, x0, y0, w, w)
    H, W = cap["rgb"].shape[:2]
    lab = np.zeros((H, W), np.float32)
    for i, (crop, (oy_, ox_), _t) in enumerate(cap["masks"] or []):
        sl = lab[oy_:oy_ + crop.shape[0], ox_:ox_ + crop.shape[1]]
        sl[crop.astype(bool)] = i + 1
    labp = panel_from_raster(lab, ctx.to_work, x0, y0, w, w).astype(np.int32)
    pal = np.random.default_rng(3).integers(60, 230, (len(cap["masks"] or []) + 2, 3)).astype(np.uint8)
    pal[0] = (250, 250, 250)
    p2 = pal[labp]
    p3 = (p1.astype(np.float32) * 0.45 + 255 * 0.55).astype(np.uint8)
    p4 = np.full_like(p1, 255)
    p5 = thread_panel(design_runs_mm(cap["design"]), x0, y0, w, w)

    def near(poly):
        b = poly.bounds
        return not (b[2] < x0 or b[0] > x0 + w or b[3] < y0 or b[1] > y0 + w)

    for poly, *_ in cap["regions"]:
        for r in rings(poly):
            draw_poly(p4, r, x0, y0, (170, 170, 170), 1)
            draw_poly(p5, r, x0, y0, (255, 0, 255), 1)
            if near(poly):
                draw_poly(p3, r, x0, y0, (200, 0, 0), 2, dots=True)
    for poly, *_ in (cap["planned"] or []):
        if near(poly):
            for r in rings(poly):
                draw_poly(p4, r, x0, y0, (0, 140, 0), 2, dots=True)
    panels = [label(p1, f"source {ctx.src_ppm:.2f} px/mm ({1 / ctx.src_ppm:.2f} mm/px)"),
              label(pw, f"work raster {ctx.ppm:.1f}"), label(p2, "stage-3 masks"),
              label(p3, "stage-4 polygon"), label(p4, "stage-5 (green) vs 4 (grey)"),
              label(p5, "ours: thread + needle")]
    if spot.get("pro"):
        panels.append(pro_panel(spot, it, imgdir, pxy, half))
    return _hstack(panels, f"{spot['id']}  {it['size']}  pin@({pxy[0]:.2f},{pxy[1]:.2f})  win {w:.1f} mm",
                   pin.get("note") or "")


def offon(spot: dict, cap_off: str, cap_on: str) -> np.ndarray:
    a = _Ctx(os.path.join(cap_off, spot["cap"] + ".pkl"))
    b = _Ctx(os.path.join(cap_on, spot["cap"] + ".pkl"))
    pmx, pmy, pxy, it, pin, imgdir = a.plan_mm(spot)
    half = spot.get("half_mm") or 3.0
    panels = [label(a.source_panel(pmx - half, pmy - half, 2 * half, 2 * half), f"art {a.src_ppm:.2f} px/mm")]
    for lab, ctx in (("OFF", a), ("ON", b)):
        x, y, *_ = ctx.plan_mm(spot)
        panels.append(label(thread_panel(design_runs_mm(ctx.cap["design"]), x - half, y - half,
                                         2 * half, 2 * half, dots=False), f"{lab} thread"))
    if spot.get("pro"):
        panels.append(pro_panel(spot, it, imgdir, pxy, half))
    return _hstack(panels, spot["id"], pin.get("note") or "")


# ------------------------------------------------------------------ metrics
class _PlanShim:
    """What `edge_wobble.analyse_plan` / `curve_fidelity.traces` read of a plan."""

    def __init__(self, cap):
        self.blocks = [[SimpleNamespace(points=p, kind=k, jump=j, trim=t, shape_id=s)
                        for p, k, j, t, s in runs] for blk in cap["runs"] for _rgb, runs in blk]

    def iter_runs(self):
        for b in self.blocks:
            for r in b:
                yield b, r


def bare_inside_art(art_cap: dict, cap: dict, res: float = 20.0) -> tuple[float, int]:
    """mm2 of `art_cap`'s sewn regions (eroded 0.4 mm, so an edge difference
    does not count) that `cap`'s thread (0.4 mm wide) never covers, and the
    patches of at least 0.05 mm2."""
    from shapely.ops import unary_union
    sewn = {s for blk in art_cap["runs"] for _rgb, runs in blk for *_x, s in runs}
    art = unary_union([p for p, _t, sid, _m in art_cap["regions"] if sid in sewn]).buffer(-0.4)
    x0, y0, x1, y1 = art.bounds
    ox, oy = x0 - 1, y0 - 1
    shape = (int((y1 - y0 + 2) * res) + 1, int((x1 - x0 + 2) * res) + 1)
    am = np.zeros(shape, np.uint8)
    for g in getattr(art, "geoms", [art]):
        cv2.fillPoly(am, [np.round((np.asarray(g.exterior.coords) - [ox, oy]) * res).astype(np.int32)], 255)
        for h in g.interiors:
            cv2.fillPoly(am, [np.round((np.asarray(h.coords) - [ox, oy]) * res).astype(np.int32)], 0)
    tm = np.zeros(shape, np.uint8)
    for blk in cap["runs"]:
        for _rgb, runs in blk:
            for pts, kind, *_ in runs:
                if kind == "travel" or len(pts) < 2:
                    continue
                q = np.round((np.asarray(pts) - [ox, oy]) * res * 4).astype(np.int32)
                cv2.polylines(tm, [q], False, 255, max(1, int(round(0.4 * res))), cv2.LINE_8, shift=2)
    bare = (am > 0) & (tm == 0)
    _n, _cc, st, _ = cv2.connectedComponentsWithStats(bare.astype(np.uint8), 8)
    areas = st[1:, cv2.CC_STAT_AREA] / res / res
    return round(float(bare.sum() / res / res), 2), int((areas >= 0.05).sum())


def metrics(cap_off: dict, cap_on: dict) -> dict:
    from digitizer_core import curve_fidelity as cf
    from digitizer_core import edge_wobble as ew

    def polys(c):
        return {sid: p for p, _t, sid, _m in c["regions"]}

    def md5(c):
        return hashlib.md5(json.dumps(c["design"]["stitches"], sort_keys=True).encode()).hexdigest()

    pa, pb = _PlanShim(cap_off), _PlanShim(cap_on)
    row = {"stitches": [len(cap_off["design"]["stitches"]), len(cap_on["design"]["stitches"])],
           "md5_same": md5(cap_off) == md5(cap_on)}
    for lab, polys_, plan in (("off", polys(cap_off), pa), ("on", polys(cap_on), pb),
                              ("on_vs_off_polygons", polys(cap_off), pb)):
        w = ew.analyse_plan(polys_, plan, unsewn=False)
        row[f"edge_wobble_{lab}"] = {t: {"std_mm": v["wobble_std_mm"], "p95_mm": v["wobble_p95_mm"]}
                                     for t, v in w["by_tier"].items()}
    for lab, plan in (("off", pa), ("on", pb)):
        m = cf.measure([p for _k, _s, p in cf.traces(plan)])
        row[f"curve_fidelity_{lab}"] = {k: m.get(k) for k in ("roughness_deg", "turn_gini")}
    row["bare_inside_art_off"] = bare_inside_art(cap_off, cap_off)
    row["bare_inside_art_on"] = bare_inside_art(cap_off, cap_on)
    return row


# ---------------------------------------------------------------------- cli
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("name"); c.add_argument("art"); c.add_argument("width", type=float)
    c.add_argument("garment"); c.add_argument("out"); c.add_argument("set", nargs="*")
    s = sub.add_parser("strips")
    s.add_argument("spots"); s.add_argument("capdir"); s.add_argument("outdir"); s.add_argument("only", nargs="*")
    o = sub.add_parser("offon")
    o.add_argument("spots"); o.add_argument("cap_off"); o.add_argument("cap_on"); o.add_argument("outdir")
    o.add_argument("name")
    m = sub.add_parser("metrics")
    m.add_argument("spots"); m.add_argument("cap_off"); m.add_argument("cap_on"); m.add_argument("names", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "capture":
        extra = {k: json.loads(v) for k, _s, v in (kv.partition("=") for kv in a.set)}
        blob = capture(a.name, a.art, a.width, a.garment, a.out, extra)
        print(a.name, "class", blob["class"], "ppm", blob["px_per_mm"], "input", blob["input_px_per_mm"],
              "stitches", len(blob["design"]["stitches"]), "s", round(blob["elapsed"], 1))
        return 0
    spots = json.loads(Path(a.spots).read_text(encoding="utf-8"))
    if a.cmd == "strips":
        os.makedirs(a.outdir, exist_ok=True)
        for sp in spots:
            if (a.only and sp["id"] not in a.only) or not os.path.exists(os.path.join(a.capdir, sp["cap"] + ".pkl")):
                continue
            cv2.imwrite(os.path.join(a.outdir, sp["id"] + ".png"), strip(sp, a.capdir))
            print(sp["id"])
        return 0
    if a.cmd == "offon":
        from digitizer_core.stitchviz import render_design
        os.makedirs(a.outdir, exist_ok=True)
        for lab, d in (("off", a.cap_off), ("on", a.cap_on)):
            cap = _Ctx(os.path.join(d, a.name + ".pkl")).cap
            cv2.imwrite(os.path.join(a.outdir, f"{a.name}_full_{lab}.png"),
                        render_design(cap["design"], px_per_mm=12.0, pad_mm=2.0))
        for sp in spots:
            if sp["cap"] == a.name:
                cv2.imwrite(os.path.join(a.outdir, sp["id"] + "_offon.png"), offon(sp, a.cap_off, a.cap_on))
        return 0
    out = {}
    for name in a.names:
        out[name] = metrics(_Ctx(os.path.join(a.cap_off, name + ".pkl")).cap,
                            _Ctx(os.path.join(a.cap_on, name + ".pkl")).cap)
        print(name, json.dumps(out[name]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
