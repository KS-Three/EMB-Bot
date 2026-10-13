"""Hotel Fremont at 81 mm on a hat: Kent's 2026-10-13 stitch-out, reproduced.

Kent digitized his Hotel Fremont logo in the Studio at 81 x 44 mm, garment
Hat, 5x7 hoop, and got 15,129 stitches in 3 colours with seven defects he
circled: EST ragged, 1895 gone ("098"), THE a blob, the EAT | STAY | PLAY
tagline illegible, a stray accent over HOTEL's E, a loop at FREMONT's M->O
junction and a tick after the final T. His upload was the transparent-
background logo, which is the committed `photo/logo_hotel_fremont.webp`
(2500 x 1345 RGBA, 37% transparent): the same artwork, same aspect (81 x 44
is 1.84; the file is 1.86). `art/logo_hotel_fremont_patch.png` is a 371 px
RGB flattening with no alpha, so it is not what he sent.

This runs the request the Studio sends (`studio_request`, a mirror of
`app/src/lib/digitizer.js` `buildDigitizeConfig` over `DEFAULT_DIGITIZE_PARAMS`
for a fresh upload on a Hat project) through the service's own steps: the
config is validated by `digitizer_service.app._parse_config`, the upload
decoded by `_decode`, then `build_generation` -> `finish_generation` ->
`plan_stitches` -> `plan_to_design` -> `run_preflight`, which is the body of
`/digitize`'s `work()` with the job registry left out. Nothing in the engine
changes; a wrapper on `stage7_sequence.lettering_columns_shape` records which
shapes the Column lane took.

Measurement only. Fremont is an UNREPRESENTATIVE fixture: reproduce defects
on it, never size a constant on it.

    # one arm (writes <out>/<arm>.json and <arm>_design.json)
    .venv/Scripts/python -m tools.fremont_triage --arm main --out DIR
    .venv/Scripts/python -m tools.fremont_triage --arm guards_off --out DIR
    # the pre-#863 core, extracted with `git archive 0f03f6fc^1 ...`:
    PYTHONPATH=<extract>/digitizer .venv/Scripts/python -m tools.fremont_triage \
        --arm pre863 --core <extract>/digitizer --out DIR
    # panels from the saved arms (no digitizing)
    .venv/Scripts/python -m tools.fremont_triage --panels --out DIR --renders DIR2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "testdata" / "photo" / "logo_hotel_fremont.webp"

# What Kent's Studio showed: 81 x 44 mm, 15,129 stitches, 3 colours.
KENT_WIDTH_MM = 81.0
KENT_STITCHES = 15129
KENT_COLOURS = 3

# The Studio's project default fabric (project.js `fabricRgb`, "Natural").
# Kent's swatch is not recoverable from his screenshot; on this upload it
# cannot matter, because every enclosed hole is an ALPHA hole and the
# garment rule never sews an alpha hole (config `enclosed_by_garment`).
STUDIO_FABRIC_RGB = [235, 232, 223]


def studio_request(width_mm: float = KENT_WIDTH_MM) -> dict:
    """The /digitize `config` the Studio sends for a fresh upload of this
    file on a Hat project at `width_mm`: `buildDigitizeConfig` over
    `DEFAULT_DIGITIZE_PARAMS` (target width replaced), with `garment_id`
    and `garment_rgb` from the project. No thread brand (the Studio's own
    palette is omitted), no crop, no edits, SAM2 off."""
    return {
        "target_width_mm": float(width_mm),
        "max_colors": 6,
        "satin": True,
        "detail_layer": False,
        "edge_cap": "bean",
        "detect_photographic": True,
        "faces_route_flat": True,
        "garment_id": "hat_front",
        "garment_rgb": list(STUDIO_FABRIC_RGB),
    }


# The bisect arms. Each is a set of PipelineConfig overrides on top of the
# Studio request; `pre863` is the core as of 0f03f6fc^1 (run with --core).
ARMS = {
    "main": {},
    "ink_link_off": {"lettering_columns_ink_link": False},
    "skip_blobs_off": {"lettering_columns_skip_blobs": False},
    "guards_off": {"lettering_columns_ink_link": False,
                   "lettering_columns_skip_blobs": False},
    "lane_off": {"lettering_columns": False},
    "pre863": {},
}
ARM_ORDER = list(ARMS)

# Kent's seven red circles, plus the 1895/EST pair, as boxes in FRACTIONS of
# the source image (x0, y0, x1, y1), read off the 2500 x 1345 artwork. A
# fraction maps to the prep raster and from there to design mm through the
# prep's own transform, so every arm (and the old core) is read in the same
# place on the artwork.
ROIS = {
    "est": (0.380, 0.190, 0.460, 0.256),
    "1895": (0.537, 0.190, 0.620, 0.256),
    "the": (0.440, 0.315, 0.562, 0.397),
    "tagline": (0.344, 0.684, 0.680, 0.782),
    # 5-7 are where Kent's red pen strokes POINT (his marks are annotation,
    # not thread): HOTEL's E upper arm end; FREMONT's M at its V vertex on
    # the baseline, beside the O; the foot of N's diagonal before the T.
    "accent_e": (0.285, 0.395, 0.340, 0.475),
    "m_o_junction": (0.655, 0.480, 0.720, 0.580),
    "final_t": (0.860, 0.490, 0.912, 0.590),
}
CIRCLES = [
    ("est", "1. EST ragged"),
    ("1895", "2. 1895 missing / reads 098"),
    ("the", "3. THE garbled"),
    ("tagline", "4. EAT | STAY | PLAY illegible"),
    ("accent_e", "5. mark over HOTEL's E (upper arm end)"),
    ("m_o_junction", "6. loop at FREMONT's M vertex (M->O)"),
    ("final_t", "7. tick at N's diagonal foot, before the final T"),
]


# --- running one arm ---------------------------------------------------------

def _decode(data: bytes):
    """The service's `_decode` for an image under its 2800 px ceiling, which
    this one is (2500 px): `cv2.imdecode(..., IMREAD_UNCHANGED)`, no resize.
    Used only for the old-core arm, where importing the service would pull
    today's service onto yesterday's core."""
    import cv2
    import numpy as np
    raw = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
    if max(raw.shape[:2]) > 2800:
        raise SystemExit("fixture is over the service's decode ceiling; use the service")
    return raw


def run_arm(arm: str, width_mm: float = KENT_WIDTH_MM, core: str | None = None,
            preflight: bool = True) -> dict:
    """Digitize the fixture the way /digitize does for `arm`. Returns
    {result, plan, design, preflight, gen, taken, declined, cfg_dict, secs}."""
    from digitizer_core import PipelineConfig
    from digitizer_core import stage7_sequence as s7
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.preflight import run_preflight

    data = FIXTURE.read_bytes()
    if core is None:
        from digitizer_service.app import _decode as svc_decode
        from digitizer_service.app import _parse_config
        cfg_dict = _parse_config(json.dumps(studio_request(width_mm)))
        pixels = svc_decode(data)
    else:
        cfg_dict = dict(studio_request(width_mm))
        pixels = _decode(data)
    cfg = PipelineConfig(**{**cfg_dict, **ARMS[arm]})

    taken: list[str] = []
    declined: list[str] = []
    real = getattr(s7, "lettering_columns_shape", None)
    if real is not None:
        def spy(poly, shape_id, **kw):
            runs, report = real(poly, shape_id, **kw)
            (declined if report.get("empty") else taken).append(shape_id)
            return runs, report
        s7.lettering_columns_shape = spy
    t = time.time()
    try:
        gen = build_generation(pixels, cfg, exif_source=data)
        result = finish_generation(gen.fork(), cfg)
        plan = plan_stitches(result, cfg)
    finally:
        if real is not None:
            s7.lettering_columns_shape = real
    design = plan_to_design(plan, name="Digitized design")
    t_plan = round(time.time() - t, 1)
    pre = run_preflight(result, plan, cfg, image=pixels) if (preflight and cfg.preflight) else None
    return {"secs_to_plan": t_plan,"result": result, "plan": plan, "design": design, "preflight": pre,
            "gen": gen, "taken": taken, "declined": declined, "cfg_dict": cfg_dict,
            "cfg": cfg, "secs": round(time.time() - t, 1)}


def roi_mm(p, frac) -> tuple[float, float, float, float]:
    """Source-image fraction box -> design mm box (x0, y0, x1, y1; y down),
    through the prep raster: same transform `preflight._uncovered_findings`
    inverts (x_px = x_mm * px_per_mm + art-box centre)."""
    h, w = p.bg_mask.shape
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    fx0, fy0, fx1, fy1 = frac
    return ((fx0 * w - cx) / p.px_per_mm, (fy0 * h - cy) / p.px_per_mm,
            (fx1 * w - cx) / p.px_per_mm, (fy1 * h - cy) / p.px_per_mm)


def _tier_of(plan, region_ids: set[str]) -> dict[str, list[str]]:
    """region id -> run kinds sewn for it, read through preflight's own
    ownership rule (a blend band's `-blend<i>` runs belong to their region)."""
    from digitizer_core import preflight as pf
    kinds: dict[str, set] = {}
    for _b, r in plan.iter_runs():
        # `jump` on a run means "jump to its start", not "no thread": the
        # 1895 digits' bean runs all carry it.
        if r.shape_id and r.points:
            own = pf._owning_region_id(r.shape_id, region_ids)
            if own is not None:
                kinds.setdefault(own, set()).add(r.kind)
    return {k: sorted(v) for k, v in kinds.items()}


# A letter on this logo is tan or black on a WHITE patch that sews as one
# fill under everything, so "is the ink covered by thread" is true almost
# everywhere and says nothing. Letter ink is the non-white artwork, and it
# counts as sewn only where NON-WHITE thread lands on it.
WHITE_MIN = 215          # a channel minimum at or above this is the white patch
STRAY_MM = 0.4           # how far off the ink a non-white needle point is "stray"


def _thread_rgb(region, plan) -> tuple[int, int, int]:
    for b in plan.blocks:
        if b.thread_number == region.thread_number:
            return tuple(int(v) for v in b.rgb)
    try:
        from digitizer_core.threads import CHART
        return tuple(int(v) for v in CHART[region.thread_index].rgb)
    except Exception:       # noqa: BLE001 - a census column, not a gate
        return (0, 0, 0)


def _non_white_plan(plan):
    from digitizer_core.stitches import StitchPlan
    keep = [b for b in plan.blocks if min(b.rgb) < WHITE_MIN]
    return StitchPlan(blocks=keep, palette=plan.palette, warnings=[],
                      design_size_mm=plan.design_size_mm)


def roi_census(run: dict) -> dict:
    """Per ROI: letter-ink area (non-white, non-background artwork), how much
    of it no non-white thread covers (`ink_bare_mm2`, coverage below
    preflight's floor), how much no region polygon even claims
    (`ink_unclaimed_mm2`: lost before stitching, at stages 1-4), the shapes
    there (tier, colour, Column lane, size against the two small-detail
    floors), the ARTWORK_UNCOVERED share named on those shapes, and the
    stitches / trims whose needle points fall inside."""
    import numpy as np
    from digitizer_core import machine
    from digitizer_core import preflight as pf
    from shapely.geometry import Point, box
    from shapely.ops import unary_union

    p = run["gen"].p
    plan, result = run["plan"], run["result"]
    cfg_detail_mm2 = run["cfg"].min_detail_mm ** 2
    cell = pf._UNCOVERED_CELL_MM
    grid, (gx0, gy0) = pf._coverage_map(_non_white_plan(plan), cell_mm=cell)
    covered = grid >= pf._COVERAGE_FLOOR_UNITS
    ny, nx = grid.shape
    h, w = p.bg_mask.shape
    ax0, ay0, ax1, ay1 = p.art_bbox
    cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
    ink = (~p.bg_mask) & (p.rgb.min(axis=2) < WHITE_MIN)
    region_ids = {r.shape_id for r in result.regions}
    tiers = _tier_of(plan, region_ids)
    non_white_regions = [r for r in result.regions
                         if min(_thread_rgb(r, plan)) < WHITE_MIN]
    taken = set(run["taken"])
    unc = {}
    for f in (run["preflight"] or {}).get("findings", []):
        if f.get("code") == pf.ARTWORK_UNCOVERED:
            unc = {s["shape_id"]: s["missing_mm2"] for s in f.get("shapes", [])}

    # needle points, in design mm (adapter writes x = 10 x_mm, y = -10 y_mm)
    from digitizer_core.stitches import iter_machine_commands, CMD_STITCH, CMD_TRIM
    pts, trims_at = [], []
    last = None
    for cmd, pt in iter_machine_commands(plan):
        if cmd == CMD_STITCH:
            pts.append(pt)
            last = pt
        elif cmd == CMD_TRIM and last is not None:
            trims_at.append(last)
    pts = np.asarray(pts, float)
    trims_at = np.asarray(trims_at, float).reshape(-1, 2)

    # Stray thread: non-white needle points that land off the artwork's
    # non-white ink by more than STRAY_MM -- an accent, a tick or a loop is
    # exactly that. Read per run so the owning shape and run kind are named.
    import cv2
    k = max(1, int(round(STRAY_MM * p.px_per_mm)))
    near_ink = cv2.dilate(ink.astype(np.uint8), np.ones((2 * k + 1, 2 * k + 1), np.uint8)) > 0
    dark_pts = []          # (x, y, shape_id, kind)
    for b, r in plan.iter_runs():
        if min(b.rgb) >= WHITE_MIN:
            continue
        for (x, y) in r.points:
            dark_pts.append((x, y, r.shape_id, r.kind))

    def stray_in(bx0, by0, bx1, by1):
        hits: dict[str, int] = {}
        n_dark = 0
        for (x, y, sid, kind) in dark_pts:
            if not (bx0 <= x <= bx1 and by0 <= y <= by1):
                continue
            n_dark += 1
            px = int(np.clip(x * p.px_per_mm + cx, 0, w - 1))
            py = int(np.clip(y * p.px_per_mm + cy, 0, h - 1))
            if not near_ink[py, px]:
                key = f"{sid}:{kind}"
                hits[key] = hits.get(key, 0) + 1
        return n_dark, hits

    out = {}
    for name, frac in ROIS.items():
        bx0, by0, bx1, by1 = roi_mm(p, frac)
        # ink, sampled at each coverage cell centre inside the box
        ix0 = max(0, int((bx0 - gx0) / cell)); ix1 = min(nx, int((bx1 - gx0) / cell) + 1)
        iy0 = max(0, int((by0 - gy0) / cell)); iy1 = min(ny, int((by1 - gy0) / cell) + 1)
        gy, gx = np.mgrid[iy0:iy1, ix0:ix1]
        xm = (gx + 0.5) * cell + gx0
        ym = (gy + 0.5) * cell + gy0
        inside = (xm >= bx0) & (xm <= bx1) & (ym >= by0) & (ym <= by1)
        sx = np.clip((xm * p.px_per_mm + cx).astype(int), 0, w - 1)
        sy = np.clip((ym * p.px_per_mm + cy).astype(int), 0, h - 1)
        ink_c = ink[sy, sx] & inside
        cov_c = covered[iy0:iy1, ix0:ix1]
        bx = box(bx0, by0, bx1, by1)
        claim = unary_union([r.polygon for r in non_white_regions
                             if r.polygon.intersects(bx)] or [box(0, 0, 0, 0)])
        claimed_c = np.zeros_like(ink_c)
        for (j, i) in zip(*np.nonzero(ink_c)):
            claimed_c[j, i] = claim.contains(Point(float(xm[j, i]), float(ym[j, i])))
        shapes = []
        for r in result.regions:
            c = r.polygon.representative_point()
            if not bx.contains(c):
                continue
            m = r.meta or {}
            area, perim = float(r.polygon.area), float(r.polygon.exterior.length)
            shapes.append({
                "shape_id": r.shape_id, "thread": r.thread_number,
                "rgb": list(_thread_rgb(r, plan)),
                "area_mm2": round(area, 2),
                "perimeter_mm": round(perim, 2),
                "w_mm": round(r.polygon.bounds[2] - r.polygon.bounds[0], 2),
                "h_mm": round(r.polygon.bounds[3] - r.polygon.bounds[1], 2),
                "holes": len(r.polygon.interiors),
                "tier": "+".join(tiers.get(r.shape_id, [])) or "UNSEWN",
                "column_lane": r.shape_id in taken,
                "text_candidate": bool(m.get("text_candidate")),
                "lettering_group": bool(m.get("lettering_group")),
                "ink_stray": bool(m.get("lettering_ink_stray")),
                # The two small-detail rules (stage 4's run-tier floor,
                # stage 7's run routing): is this shape under either?
                "under_run_loop_floor": perim < machine.RUN_MIN_LOOP_MM,
                "under_run_area_floor": area < machine.RUN_MIN_AREA_MM2,
                "under_min_detail_mm2": area < cfg_detail_mm2,
                "uncovered_mm2": unc.get(r.shape_id, 0.0),
            })
        in_pts = 0
        if len(pts):
            px, py = pts[:, 0], pts[:, 1]
            in_pts = int(((px >= bx0) & (px <= bx1) & (py >= by0) & (py <= by1)).sum())
        in_trims = 0
        if len(trims_at):
            tx, ty = trims_at[:, 0], trims_at[:, 1]
            in_trims = int(((tx >= bx0) & (tx <= bx1) & (ty >= by0) & (ty <= by1)).sum())
        n_dark, stray = stray_in(bx0, by0, bx1, by1)
        out[name] = {
            "box_mm": [round(v, 2) for v in (bx0, by0, bx1, by1)],
            "dark_points": n_dark,
            "stray_points": sum(stray.values()),
            "stray_by_run": dict(sorted(stray.items(), key=lambda kv: -kv[1])),
            "ink_mm2": round(float(ink_c.sum()) * cell * cell, 2),
            "ink_bare_mm2": round(float((ink_c & ~cov_c).sum()) * cell * cell, 2),
            "ink_unclaimed_mm2": round(float((ink_c & ~claimed_c).sum()) * cell * cell, 2),
            "artwork_uncovered_mm2": round(sum(s["uncovered_mm2"] for s in shapes), 2),
            "stitches": in_pts, "trims": in_trims,
            "shapes": shapes,
        }
    return out


def arm_summary(arm: str, run: dict) -> dict:
    from digitizer_core import preflight as pf
    s = run["plan"].stats
    design = run["design"]
    pre = run["preflight"] or {}
    unc = next((f for f in pre.get("findings", []) if f.get("code") == pf.ARTWORK_UNCOVERED), None)
    colours = len({tuple(b.rgb) for b in run["plan"].blocks})
    import digitizer_core
    return {
        "arm": arm,
        "core": str(Path(digitizer_core.__file__).parent),
        "request": run["cfg_dict"], "overrides": ARMS[arm],
        "fixture": str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "secs": run["secs"], "secs_to_plan": run.get("secs_to_plan"),
        "stitches": s.stitch_count, "trims": s.trims, "jumps": s.jumps,
        "color_changes": s.color_changes, "colours": colours,
        "size_mm": [round(v, 1) for v in s.size_mm],
        "design_records": len(design["stitches"]),
        "n_regions": len(run["result"].regions),
        "design_class": run["result"].design_class,
        "lane_taken": len(run["taken"]),
        "artwork_uncovered": None if unc is None else {
            "total_mm2": unc.get("total_mm2"), "worst_mm2": unc.get("worst_mm2"),
            "shapes": unc.get("shapes")},
        "uncovered_metrics": {k: v for k, v in (pre.get("metrics") or {}).items()
                              if k.startswith("uncovered_")},
        "rois": roi_census(run),
    }


# --- panels ------------------------------------------------------------------

def _render(design: dict, px_per_mm: float, pad: float = 2.0):
    from digitizer_core import stitchviz
    img = stitchviz.render_design(design, px_per_mm=px_per_mm, pad_mm=pad)
    b = stitchviz._bounds(design["stitches"])
    ux0, uy1 = b[0], b[3]

    def to_px(xm, ym):
        return (xm - ux0 / 10.0 + pad) * px_per_mm, (uy1 / 10.0 + ym + pad) * px_per_mm
    return img, to_px


def _crop(img, to_px, box_mm, margin_mm=0.6):
    x0, y0, x1, y1 = box_mm
    ax, ay = to_px(x0 - margin_mm, y0 - margin_mm)
    bx, by = to_px(x1 + margin_mm, y1 + margin_mm)
    h, w = img.shape[:2]
    ax, bx = int(max(0, min(ax, bx))), int(min(w, max(ax, bx)))
    ay, by = int(max(0, min(ay, by))), int(min(h, max(ay, by)))
    return img[ay:by, ax:bx]


def _label(img, text, width=None):
    import cv2
    import numpy as np
    w = width or img.shape[1]
    if img.shape[1] < w:
        img = np.pad(img, ((0, 0), (0, w - img.shape[1]), (0, 0)), constant_values=255)
    bar = np.full((22, w, 3), 235, np.uint8)
    cv2.putText(bar, text, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def _source_crop(frac, height_px):
    import cv2
    import numpy as np
    src = cv2.imread(str(FIXTURE), cv2.IMREAD_UNCHANGED)
    h, w = src.shape[:2]
    rgb = src[..., :3].astype(float)
    a = src[..., 3:4].astype(float) / 255.0
    flat = (rgb * a + np.array([145, 128, 120]) * (1 - a)).astype(np.uint8)   # slate fabric
    fx0, fy0, fx1, fy1 = frac
    mx = 0.006
    c = flat[int(max(0, fy0 - mx) * h):int(min(1, fy1 + mx) * h),
             int(max(0, fx0 - mx) * w):int(min(1, fx1 + mx) * w)]
    s = height_px / c.shape[0]
    return cv2.resize(c, (max(1, int(c.shape[1] * s)), height_px), interpolation=cv2.INTER_AREA)


def _hstack(imgs, gap=6):
    import numpy as np
    hh = max(i.shape[0] for i in imgs)
    out = []
    for k, i in enumerate(imgs):
        i = np.pad(i, ((0, hh - i.shape[0]), (0, 0), (0, 0)), constant_values=255)
        out.append(i)
        if k < len(imgs) - 1:
            out.append(np.full((hh, gap, 3), 255, np.uint8))
    return np.hstack(out)


def panels(out: Path, renders: Path, px_per_mm: float = 40.0) -> list[Path]:
    """One panel per red circle (artwork | main), the EST/1895 bisect strip
    (artwork | each arm), and a full-design render of main. Reads the saved
    `<arm>.json` / `<arm>_design.json`; digitizes nothing."""
    import cv2
    import numpy as np
    renders.mkdir(parents=True, exist_ok=True)
    arms = {}
    for arm in ARM_ORDER:
        j, d = out / f"{arm}.json", out / f"{arm}_design.json"
        if j.exists() and d.exists():
            arms[arm] = (json.loads(j.read_text()), json.loads(d.read_text()))
    if "main" not in arms:
        raise SystemExit("run --arm main first")
    written = []
    main_sum, main_design = arms["main"]
    full, _ = _render(main_design, 12.0)
    p = renders / "main_full.png"
    cv2.imwrite(str(p), _label(full, f"main, Studio request at {KENT_WIDTH_MM:g} mm (Hat): "
                                     f"{main_sum['stitches']:,} stitches, {main_sum['colours']} colours"))
    written.append(p)
    big, to_px = _render(main_design, px_per_mm)
    for key, title in CIRCLES:
        r = main_sum["rois"][key]
        crop = _crop(big, to_px, r["box_mm"])
        src = _source_crop(ROIS[key], crop.shape[0])
        panel = _hstack([_label(src, "artwork"),
                         _label(crop, f"main: {r['ink_bare_mm2']:.1f} of {r['ink_mm2']:.1f} mm2 ink bare")])
        panel = _label(panel, title)
        p = renders / f"circle_{CIRCLES.index((key, title)) + 1}_{key}.png"
        cv2.imwrite(str(p), panel)
        written.append(p)
    # bisect strip: EST and 1895 side by side, one row per arm
    rows = []
    for arm, (summ, design) in arms.items():
        img, tp = _render(design, px_per_mm)
        e, n = summ["rois"]["est"], summ["rois"]["1895"]
        box = (min(e["box_mm"][0], n["box_mm"][0]), min(e["box_mm"][1], n["box_mm"][1]),
               max(e["box_mm"][2], n["box_mm"][2]), max(e["box_mm"][3], n["box_mm"][3]))
        crop = _crop(img, tp, box)
        txt = (f"{arm}: {summ['stitches']:,} st, {summ['trims']} trims | EST bare "
               f"{e['ink_bare_mm2']:.1f}/{e['ink_mm2']:.1f} mm2 | 1895 bare "
               f"{n['ink_bare_mm2']:.1f}/{n['ink_mm2']:.1f} mm2")
        rows.append(_label(crop, txt))
    fr = (ROIS["est"][0], ROIS["est"][1], ROIS["1895"][2], ROIS["1895"][3])
    src = _label(_source_crop(fr, rows[0].shape[0] - 22), "artwork")
    w = max(r.shape[1] for r in rows + [src])
    strip = np.vstack([np.pad(r, ((0, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255)
                       for r in [src] + rows])
    p = renders / "bisect_est_1895.png"
    cv2.imwrite(str(p), strip)
    written.append(p)
    return written


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", choices=ARM_ORDER)
    ap.add_argument("--core", help="old digitizer dir (for --arm pre863); must also lead PYTHONPATH")
    ap.add_argument("--width", type=float, default=KENT_WIDTH_MM)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reuse", action="store_true",
                    help="re-read <arm>.pkl from --out instead of digitizing again")
    ap.add_argument("--panels", action="store_true")
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    if a.core:
        sys.path.insert(0, a.core)
    sys.path.insert(1 if a.core else 0, str(ROOT))
    a.out.mkdir(parents=True, exist_ok=True)
    if a.arm:
        if (a.arm == "pre863") != bool(a.core):
            raise SystemExit("--arm pre863 needs --core, and only it")
        import pickle
        stem = a.arm if a.width == KENT_WIDTH_MM else f"{a.arm}_{a.width:g}mm"
        pk = a.out / f"{stem}.pkl"
        if a.reuse and pk.exists():
            run = pickle.loads(pk.read_bytes())     # our own scratch file
        else:
            run = run_arm(a.arm, a.width, a.core)
            pk.write_bytes(pickle.dumps(run))
        summ = arm_summary(a.arm, run)
        (a.out / f"{stem}.json").write_text(json.dumps(summ, indent=1))
        (a.out / f"{stem}_design.json").write_text(json.dumps(run["design"]))
        print(json.dumps({k: v for k, v in summ.items() if k not in ("rois", "request")}, indent=1))
        for name, r in summ["rois"].items():
            sh = ", ".join(f"{s['shape_id']}:{s['tier']}{'/COL' if s['column_lane'] else ''}"
                           for s in r["shapes"])
            print(f"{name:13s} ink {r['ink_mm2']:7.1f} bare {r['ink_bare_mm2']:6.1f} "
                  f"unclaimed {r['ink_unclaimed_mm2']:6.1f} AU {r['artwork_uncovered_mm2']:5.1f} "
                  f"st {r['stitches']:5d} tr {r['trims']:3d} | {sh}")
    if a.panels:
        for p in panels(a.out, a.renders or a.out / "renders"):
            print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
