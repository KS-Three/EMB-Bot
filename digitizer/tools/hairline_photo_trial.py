"""The hairline tier on a REAL photograph (2026-10-12).

    python -m tools.hairline_photo_trial [--routes photo classical studio]
        [--rembg-python PATH] [--out ../docs/renders/claude-hairline-photo-trial]

Until this, `cfg.hairline` (PRs #848 #850 #851 #861) had been measured only
on drawn fixtures (`hair_strands`, `hair_fine`, `thin_script`). This runs the
one real photograph in the corpus, `testdata/photo/owl_kent.jpg` (Kent's own
snowy owl, cleared as a fixture 2026-08-12: facial bristles round the beak,
wispy feather edges, dark barring — the closest thing to hair the corpus
holds), through three routes:

- `photo`     — `forced_class="photo_subject"`, the photo lane with its
                stage-1 prep and the rembg subject cutout. On a worktree the
                isolated rembg venv does not exist (COOKBOOK "Running
                things"); pass `--rembg-python` (the primary checkout's
                `digitizer/rembg_isolated/venv/...`). The row records whether
                `PHOTO_BACKGROUND_REMOVED` actually fired, i.e. which pipeline
                ran.
- `classical` — the same class with `photo_prep=False`: byte-identical to
                what a machine without the rembg venv runs (pipeline.py's
                cutout-failed rule), so it reproduces anywhere — this is the
                route the done-test pins.
- `studio`    — the Studio's own settings (`detect_photographic`,
                `faces_route_flat`). Neither signal fires on this file (no
                EXIF, no face), so it takes stage 0's own lane.

and five arms per route: `off40` (today), `on40`, `on40g` (with
`cfg.hairline_over_ground`), `on60`, `on60g`. Stages 0-4 run once per route;
only 5-7 differ by arm.

Per arm: stitches, trims, colour changes, thread laid, stitches under the
needle's 1.0 mm floor (not counting the 0.8 mm lock legs), what the tier
sewed (shapes / strands / dropped, from `HAIRLINE_TIER_SEWN`), the stitches
and thread of the shapes it touched (against the same shapes OFF), and bare
fabric (`hairline_renders.bare_cells`, preflight's uncovered-artwork
instrument summed over every cell) with the part OFF covered.

Per route and weight, the gate's census: candidates, ground fragments,
branches sewn as runs vs left to the ladder, and — the diagnosis — how many
branches the gate refused for showing no LINE in the photograph
(`stage6_hairline._LINE_MIN_CONTRAST`, docs/hairline-photo-trial-2026-10-12.md).

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, preflight, stitchviz  # noqa: E402
from digitizer_core import stage1_photo_prep, stage6_hairline  # noqa: E402
from digitizer_core.adapter import UNITS_PER_MM, plan_to_design  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from digitizer_core.stage6_hairline import hairline_candidates  # noqa: E402
from tools.hairline_renders import bare_cells, bare_new_mm2  # noqa: E402

PHOTO = ROOT / "testdata" / "photo" / "owl_kent.jpg"
WIDTH_MM = 127.0
ROUTES = {
    # The rembg worker's timeout raised: on a loaded machine the default
    # timed out and the route silently became `classical` (pipeline.py's
    # cutout-failed rule) — the 2026-10-12 arm run did exactly that.
    "photo": {"forced_class": "photo_subject",
              "photo_prep_background_removal_timeout_s": 900.0},
    "classical": {"forced_class": "photo_subject", "photo_prep": False},
    "studio": {"detect_photographic": True, "faces_route_flat": True},
}
# arm -> (cfg.hairline, cfg.thread_wt, cfg.hairline_over_ground)
ARMS = {"off40": (False, 40, False), "on40": (True, 40, False),
        "on40g": (True, 40, True), "off60": (False, 60, False),
        "on60": (True, 60, False), "on60g": (True, 60, True),
        # The gate as it was before the line test (`_LINE_MIN_CONTRAST`
        # disabled for this plan only): the line test's own before/after.
        "on40_noline": (True, 40, False)}
# What the 2026-10-12 trial ran (the full set took ~25 min an arm on a loaded
# laptop; the rest are one `--arms` away).
DEFAULT_ARMS = ["off40", "on40", "on40g", "on40_noline"]
RENDER_ARMS = {"off40": "OFF (40 wt)", "on40": "hairline ON (40 wt)",
               "on40g": "ON + over_ground (40 wt)"}
GATE_ARMS = {"off40": "OFF (40 wt)", "on40_noline": "ON, width gate only (before)",
             "on40": "ON, with the line test (after)"}
MAX_JPEG_BYTES = 290_000
# Zoom boxes as fractions of the SOURCE photo (x0, y0, x1, y1): the facial
# bristles round the beak, and the barred breast feathers lower left.
ZOOMS = {"beak": (0.36, 0.18, 0.68, 0.48), "bars": (0.06, 0.60, 0.40, 0.94)}
RENDER_PX_PER_MM = 4.0
ZOOM_PX_PER_MM = 16.0


def route_cfg(route: str, **kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=WIDTH_MM, **ROUTES[route], **kw)


def stage_result(route: str):
    return run_stages(PHOTO, route_cfg(route))


def pipeline_ran(result) -> str:
    codes = {w.get("code") for w in getattr(result, "warnings", []) or []
             if isinstance(w, dict)}
    if "PHOTO_BACKGROUND_REMOVED" in codes:
        return "photo lane + prep + rembg cutout"
    if "PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE" in codes:
        return "photo lane, cutout UNAVAILABLE -> classical (no prep)"
    if "PHOTO_PREP_APPLIED" in codes:
        return "photo lane + prep, no cutout"
    return f"{result.design_class} lane, no photo prep"


def _short_stitches(plan, ids: set | None = None) -> tuple[int, int]:
    """-> (stitches 0.01-1.0 mm that are not 0.8 mm lock legs, lock legs),
    over the whole plan or only runs whose shape is in `ids`."""
    short = legs = 0
    for b in plan.blocks:
        for r in b.runs:
            if ids is not None and r.shape_id not in ids:
                continue
            for a, c in zip(r.points, r.points[1:]):
                d = math.dist(a, c)
                if 0.01 < d < machine.MIN_STITCH_MM:
                    if abs(d - machine.TIE_STITCH_MM) < 1e-6:
                        legs += 1
                    else:
                        short += 1
    return short, legs


def _shape_totals(plan, ids: set) -> tuple[int, float]:
    n, mm = 0, 0.0
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id in ids:
                n += len(r.points)
                mm += sum(math.dist(a, c) for a, c in zip(r.points, r.points[1:]))
    return n, round(mm / 1000.0, 3)


def census(result, route: str, wt: int) -> dict:
    """The gate's verdict on this photo at `wt`, before anything is sewn."""
    stitched = [r for r in result.regions if r.meta.get("stitched", True)]
    cfg = route_cfg(route, hairline=True, thread_wt=wt)
    c = hairline_candidates(stitched, cfg, ink=result.ink_source)
    area = {r.shape_id: r.polygon.area for r in stitched}
    hair = [e for m in c.values() for e in m["hair_edges"]]
    thick = [e for m in c.values() for e in m["thick_edges"]]
    no_line = [e for e in thick if e.get("refused") == "no_line"]
    widths = sorted(e["w"] for e in hair)
    return {
        "regions": len(stitched),
        "candidates": len(c),
        "fragments": len(c.fragments),
        # The drop guard (#879): admitted shapes handed back whole because
        # their walk would drop strands.
        "guarded": len(getattr(c, "guarded", {})),
        "candidate_area_mm2": round(sum(area[s] for s in c), 1),
        "branches_run": len(hair),
        "branches_ladder": len(thick),
        "branches_refused_no_line": len(no_line),
        "rest_mm2": round(sum(m["rest"].area for m in c.values()
                              if m.get("rest") is not None), 1),
        "run_branch_width_median_mm": (round(widths[len(widths) // 2], 3)
                                       if widths else None),
        "run_branch_length_m": round(sum(
            sum(math.dist(a, b) for a, b in zip(e["pts"], e["pts"][1:]))
            for e in hair) / 1000.0, 3),
        "_ids": sorted(c),
    }


def measure_arm(plan, ids: set) -> dict:
    st = plan.stats
    short, legs = _short_stitches(plan)
    hs, hlegs = _short_stitches(plan, ids)
    n, m = _shape_totals(plan, ids)
    w = next(({k: x.get(k) for k in ("shapes", "strands", "dropped")}
              for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"), None)
    rest = [x for x in plan.warnings if x["code"] == "CLIP_DROPPED_SLIVER"
            and x.get("source") == "hairline_rest"]
    thread_mm = sum(math.dist(a, c) for b in plan.blocks for r in b.runs
                    for a, c in zip(r.points, r.points[1:]))
    return {
        "stitches": st.stitch_count,
        "trims": st.trims,
        "color_changes": st.color_changes,
        "thread_m": round(thread_mm / 1000.0, 2),
        "under_1mm": short,
        "lock_legs": legs,
        "hairline_sewn": w,
        "rest_slivers": (rest[0].get("count") if rest else 0),
        "touched_stitches": n,
        "touched_thread_m": m,
        "touched_under_1mm": hs,
    }


def _src_to_mm(ink, fx: float, fy: float) -> tuple[float, float]:
    h, w = ink.rgb.shape[:2]
    sx, sy = ink.upscale
    cx, cy = ink.origin_px
    X = (fx * w + 0.5) * sx - 0.5
    Y = (fy * h + 0.5) * sy - 0.5
    return (X - cx) / ink.px_per_mm, (Y - cy) / ink.px_per_mm


def render(design, ink, thread_mm: float, out: Path, stem: str) -> None:
    """Lossless parts (whole design, and each `ZOOMS` box) into `out` — the
    gitignored parts folder; `compose` builds the committed strips from them."""
    img = stitchviz.render_design(design, px_per_mm=RENDER_PX_PER_MM, thread_mm=thread_mm)
    cv2.imwrite(str(out / f"{stem}.png"), img)
    big = stitchviz.render_design(design, px_per_mm=ZOOM_PX_PER_MM, thread_mm=thread_mm)
    _size, to_px = stitchviz._frame(design.get("stitches") or [], ZOOM_PX_PER_MM, 2.0)
    for name, (fx0, fy0, fx1, fy1) in ZOOMS.items():
        (mx0, my0), (mx1, my1) = _src_to_mm(ink, fx0, fy0), _src_to_mm(ink, fx1, fy1)
        a = to_px({"x": mx0 * UNITS_PER_MM, "y": -my0 * UNITS_PER_MM})
        b = to_px({"x": mx1 * UNITS_PER_MM, "y": -my1 * UNITS_PER_MM})
        x0, x1 = sorted((max(a[0], 0), max(b[0], 0)))
        y0, y1 = sorted((max(a[1], 0), max(b[1], 0)))
        crop = big[y0:y1, x0:x1]
        if crop.size:
            cv2.imwrite(str(out / f"{stem}_{name}.png"), crop)


def strip(parts: Path, panels: list[tuple[str, str]], dest: Path) -> None:
    """Labelled panels (files in `parts`) side by side -> `dest`, kept under
    `MAX_JPEG_BYTES`."""
    tiles = []
    for fname, label in panels:
        img = cv2.imread(str(parts / fname))
        if img is None:
            return
        band = np.full((30, img.shape[1], 3), 255, np.uint8)
        cv2.putText(band, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (30, 30, 30), 2, cv2.LINE_AA)
        tiles.append(np.vstack([band, img]))
    h = min(t.shape[0] for t in tiles)
    sep = np.full((h, 6, 3), 255, np.uint8)
    parts = []
    for t in tiles:
        parts += [t[:h], sep]
    img = np.hstack(parts[:-1])
    write_jpeg(dest, img)


def write_jpeg(path: Path, img) -> None:
    """JPEG under `MAX_JPEG_BYTES` (docs renders are committed): lower the
    quality, then the size, until it fits."""
    q = 85
    while True:
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
        if len(buf) <= MAX_JPEG_BYTES or (q <= 60 and img.shape[1] < 400):
            break
        if q > 60:
            q -= 8
        else:
            img = cv2.resize(img, (img.shape[1] * 4 // 5, img.shape[0] * 4 // 5),
                             interpolation=cv2.INTER_AREA)
    path.write_bytes(buf.tobytes())


def compose(parts: Path, out: Path, route: str) -> None:
    """OFF | hairline | hairline + ground at 60 wt (OFF at 60 wt, so the only
    difference is the tier), per zoom and for the whole design."""
    for zoom in list(ZOOMS) + [None]:
        sfx = f"_{zoom}" if zoom else ""
        strip(parts, [(f"{route}_{arm}{sfx}.png", RENDER_ARMS[arm]) for arm in RENDER_ARMS],
              out / f"compare_{route}{sfx or '_full'}.jpg")
        if zoom:
            strip(parts, [(f"{route}_{arm}{sfx}.png", GATE_ARMS[arm]) for arm in GATE_ARMS],
                  out / f"gate_before_after_{route}{sfx}.jpg")


def candidate_sheet(result, route: str, wt: int, dest: Path, cols: int = 8) -> None:
    """Every shape the gate admits at `wt`, on the SOURCE it read (nearest-
    neighbour, so a photo pixel stays a pixel): branches sewn as runs green,
    refused by the line test red, left to the ladder for width blue; the
    shape's outline grey. Largest first. This is what "does it catch real
    hair, or JPEG and blur edges" was judged on."""
    stitched = [r for r in result.regions if r.meta.get("stitched", True)]
    c = hairline_candidates(stitched, route_cfg(route, hairline=True, thread_wt=wt),
                            ink=result.ink_source)
    ink = result.ink_source
    src = ink.rgb
    by_id = {r.shape_id: r for r in stitched}
    T = 200
    tiles = []
    for sid in sorted(c, key=lambda s: -by_id[s].polygon.area):
        r, m = by_id[sid], c[sid]
        x0, y0, x1, y1 = r.polygon.bounds
        b = ink.to_src(np.array([[x0 - 0.8, y0 - 0.8], [x1 + 0.8, y1 + 0.8]]))
        sx0, sy0 = np.maximum(np.floor(b[0]).astype(int), 0)
        sx1 = min(int(np.ceil(b[1][0])), src.shape[1])
        sy1 = min(int(np.ceil(b[1][1])), src.shape[0])
        crop = src[sy0:sy1, sx0:sx1]
        if crop.size == 0:
            continue
        k = T / max(crop.shape[:2])
        big = cv2.resize(crop, (max(1, int(crop.shape[1] * k)), max(1, int(crop.shape[0] * k))),
                         interpolation=cv2.INTER_NEAREST)
        big = cv2.cvtColor(big, cv2.COLOR_RGB2BGR)

        def P(pts):
            s = ink.to_src(np.asarray(pts, float))
            return np.round(np.column_stack([(s[:, 0] - sx0 + 0.5) * k,
                                             (s[:, 1] - sy0 + 0.5) * k])).astype(np.int32)
        for part in (r.polygon.geoms if hasattr(r.polygon, "geoms") else [r.polygon]):
            cv2.polylines(big, [P(part.exterior.coords)], True, (150, 150, 150), 1)
        for e in m["thick_edges"]:
            col = (0, 0, 230) if e.get("refused") else (230, 120, 0)
            cv2.polylines(big, [P(e["pts"])], False, col, 2)
        for e in m["hair_edges"]:
            cv2.polylines(big, [P(e["pts"])], False, (0, 190, 0), 2)
        tile = np.full((T + 18, T, 3), 255, np.uint8)
        tile[:big.shape[0], :big.shape[1]] = big[:T, :T]
        cv2.putText(tile, f"{r.polygon.area:.1f} mm2  {len(m['hair_edges'])} run",
                    (3, T + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(tile)
    if not tiles:
        return
    blank = np.full_like(tiles[0], 255)
    rows = [np.hstack(tiles[i:i + cols] + [blank] * (cols - len(tiles[i:i + cols])))
            for i in range(0, len(tiles), cols)]
    write_jpeg(dest, np.vstack(rows))


def source_figure(result, route: str, dest: Path, zoom: str = "beak", k: int = 3) -> None:
    """The photograph | what the gate reads (`ink_source`: the prepped
    raster on the photo lane) | the traced regions over it, on one `ZOOMS`
    box — where the strands go before the hairline tier ever sees a shape."""
    orig = cv2.imread(str(PHOTO))
    ink = result.ink_source
    src = cv2.cvtColor(ink.rgb, cv2.COLOR_RGB2BGR)
    fx0, fy0, fx1, fy1 = ZOOMS[zoom]
    h, w = orig.shape[:2]
    x0, y0, x1, y1 = int(fx0 * w), int(fy0 * h), int(fx1 * w), int(fy1 * h)
    a = cv2.resize(orig[y0:y1, x0:x1], None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
    hs, ws = src.shape[:2]
    sx0, sy0, sx1, sy1 = int(fx0 * ws), int(fy0 * hs), int(fx1 * ws), int(fy1 * hs)
    kk = a.shape[1] / max(sx1 - sx0, 1)
    b = cv2.resize(src[sy0:sy1, sx0:sx1], (a.shape[1], a.shape[0]), interpolation=cv2.INTER_NEAREST)
    c = b.copy()
    for r in result.regions:
        for part in (r.polygon.geoms if hasattr(r.polygon, "geoms") else [r.polygon]):
            s = ink.to_src(np.asarray(part.exterior.coords, float))
            s = np.round((s - [sx0, sy0] + 0.5) * kk).astype(np.int32)
            cv2.polylines(c, [s], True, (0, 0, 255), 1)
    strip_img = []
    for img, label in ((a, "the photograph"), (b, "what the gate reads"),
                       (c, f"traced regions ({route})")):
        band = np.full((30, img.shape[1], 3), 255, np.uint8)
        cv2.putText(band, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 2,
                    cv2.LINE_AA)
        strip_img += [np.vstack([band, img]), np.full((img.shape[0] + 30, 6, 3), 255, np.uint8)]
    write_jpeg(dest, np.hstack(strip_img[:-1]))


def run_route(route: str, out: Path | None, arms=DEFAULT_ARMS,
              parts: Path | None = None) -> dict:
    """One route through every arm -> its table row. With `out`, renders:
    lossless parts into `parts` (default `out`), strips into `out`."""
    parts = parts or out
    result = stage_result(route)
    row = {"pipeline": pipeline_ran(result), "design_class": result.design_class,
           "regions": len(result.regions), "census": {}, "arms": {}}
    for wt in (40, 60):
        cen = census(result, route, wt)
        row["census"][wt] = {k: v for k, v in cen.items() if k != "_ids"}
        row["census"][wt]["_ids"] = cen["_ids"]
    p = preflight.prep(PHOTO, route_cfg(route), design_class=result.design_class) \
        if out is not None else None
    print(f"{route}: {row['pipeline']} (class {row['design_class']})", flush=True)
    base_bare: dict[int, tuple] = {}
    for arm in arms:
        on, wt, ground = ARMS[arm]
        cfg = route_cfg(route, hairline=on, thread_wt=wt, hairline_over_ground=ground)
        keep = stage6_hairline._LINE_MIN_CONTRAST
        if arm.endswith("_noline"):
            stage6_hairline._LINE_MIN_CONTRAST = -math.inf
        try:
            plan = plan_stitches(result, cfg)
        finally:
            stage6_hairline._LINE_MIN_CONTRAST = keep
        # The shapes this weight's gate admits, measured in every arm of that
        # weight — the OFF arm of the same weight is each ON arm's baseline
        # (a 60 wt plan re-spaces every satin, hairline or not).
        ids = set(row["census"][wt]["_ids"])
        r = measure_arm(plan, ids)
        if p is not None:
            bare = bare_cells(plan, result, p)
            r["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
            base_bare.setdefault(wt, bare)
            r["bare_new_mm2"] = round(bare_new_mm2(bare, base_bare[wt]), 2)
        if out is not None and (arm in RENDER_ARMS or arm in GATE_ARMS):
            design = plan_to_design(plan, name=f"owl {route} {arm}")
            render(design, result.ink_source, machine.thread_profile(wt).width_mm,
                   parts, f"{route}_{arm}")
        row["arms"][arm] = r
        print(f"{route}/{arm}: {json.dumps(r)}", flush=True)
    for wt in (40, 60):
        row["census"][wt].pop("_ids")
    if out is not None:
        compose(parts, out, route)
    return row


def markdown(table: dict) -> str:
    lines = []
    for route, row in table.items():
        lines.append(f"### {route} — {row['pipeline']} (class `{row['design_class']}`, "
                     f"{row['regions']} regions)\n")
        lines.append("| gate census | 40 wt | 60 wt |")
        lines.append("|---|---|---|")
        c40, c60 = row["census"]["40"], row["census"]["60"]
        for k, label in (("candidates", "shapes admitted (any branch a hairline)"),
                         ("fragments", "ground fragments handed back"),
                         ("candidate_area_mm2", "admitted shapes' area (mm2)"),
                         ("branches_run", "branches sewn as runs"),
                         ("branches_ladder", "branches left to the ladder"),
                         ("branches_refused_no_line", "  of those, refused: no line in the photo"),
                         ("rest_mm2", "area left to the ladder (mm2)"),
                         ("run_branch_width_median_mm", "run branches' median width (mm)"),
                         ("run_branch_length_m", "run branches' length (m)")):
            lines.append(f"| {label} | {c40.get(k)} | {c60.get(k)} |")
        lines.append("")
        arms = list(row["arms"])
        lines.append("| | " + " | ".join(arms) + " |")
        lines.append("|---|" + "---|" * len(arms))

        def fmt(a, fn):
            try:
                v = fn(row["arms"][a])
            except (KeyError, TypeError):
                return "-"
            return "-" if v is None else str(v)
        spec = [
            ("stitches", lambda r: f"{r['stitches']:,}"),
            ("trims", lambda r: r["trims"]),
            ("colour changes", lambda r: r["color_changes"]),
            ("thread laid (m)", lambda r: r["thread_m"]),
            ("stitches < 1.0 mm (excl. lock legs)", lambda r: r["under_1mm"]),
            ("hairline shapes / strands / dropped",
             lambda r: "{} / {} / {}".format(*[r["hairline_sewn"][k]
                                               for k in ("shapes", "strands", "dropped")])),
            ("rest slivers dropped", lambda r: r["rest_slivers"]),
            ("admitted shapes: stitches", lambda r: f"{r['touched_stitches']:,}"),
            ("admitted shapes: thread (m)", lambda r: r["touched_thread_m"]),
            ("admitted shapes: stitches < 1.0 mm", lambda r: r["touched_under_1mm"]),
            ("bare fabric, total (mm2)", lambda r: r["bare_mm2"]),
            ("bare fabric, new vs OFF (mm2)", lambda r: r["bare_new_mm2"]),
        ]
        for label, fn in spec:
            lines.append(f"| {label} | " + " | ".join(fmt(a, fn) for a in arms) + " |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--routes", nargs="*", default=list(ROUTES))
    ap.add_argument("--rembg-python", default=None,
                    help="the isolated rembg venv's python (a worktree has none)")
    ap.add_argument("--out", default=str(ROOT.parent / "docs" / "renders"
                                         / "claude-hairline-photo-trial"))
    ap.add_argument("--parts", default=str(ROOT / "debug_out" / "hairline_photo_trial"),
                    help="lossless per-arm renders (gitignored); strips go to --out")
    ap.add_argument("--arms", nargs="*", default=DEFAULT_ARMS, choices=list(ARMS),
                    help="OFF arms first: each ON arm's bare-fabric baseline is the "
                         "first arm of its weight")
    ap.add_argument("--sheets-only", action="store_true",
                    help="only the candidate sheets (`candidate_sheet`, 60 wt): a minute a route")
    args = ap.parse_args(argv)
    if args.rembg_python:
        stage1_photo_prep.REMBG_VENV_PYTHON = Path(args.rembg_python)
    out, parts = Path(args.out), Path(args.parts)
    out.mkdir(parents=True, exist_ok=True)
    parts.mkdir(parents=True, exist_ok=True)
    if args.sheets_only:
        for route in args.routes:
            result = stage_result(route)
            candidate_sheet(result, route, 60, out / f"candidates_{route}_60wt.jpg")
            source_figure(result, route, out / f"source_{route}_beak.jpg")
        return 0
    # One file per route, so routes can run as separate processes; the
    # combined table is rebuilt from whatever routes are present.
    for route in args.routes:
        row = run_route(route, out, arms=args.arms, parts=parts)
        (out / f"table_{route}.json").write_text(json.dumps(row, indent=1) + "\n",
                                                 encoding="utf-8")
    table = {r: json.loads((out / f"table_{r}.json").read_text(encoding="utf-8"))
             for r in ROUTES if (out / f"table_{r}.json").exists()}
    (out / "table.md").write_text(markdown(table), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
