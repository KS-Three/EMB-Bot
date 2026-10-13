"""Which shapes does the Column lane take, and are they letters?

The lane (`cfg.lettering_columns`, ON by default since 2026-10-12) takes any
shape `columns.is_lettering` admits: `meta.text_candidate` (the text cluster,
`textcluster.detect_text_clusters`) or `meta.lettering_group` (the house-angle
group, `textcluster._lettering_groups`). Neither asks whether the shape is a
LETTER; both ask whether a handful of shapes are glyph-sized, glyph-shaped and
alike. #863 found the twelve-patch colour grid of `test_preflight` is one such
"line of lettering". This counts, over the scorecard matrix, how many shapes
the lane takes and which of them are not text.

For each fixture it runs the pipeline twice (lane OFF, lane ON), records every
shape the lane actually built columns for (a wrapper on
`stage7_sequence.lettering_columns_shape`, nothing in the engine changes), and
prints the shape's size, the tags that admitted it, the OCR read where there
is one, the hand label where `testdata/lettering_truth.json` has one, and the
stitch / trim / colour-change difference ON vs OFF.

    .venv/Scripts/python -m tools.column_capture_census              # whole matrix
    .venv/Scripts/python -m tools.column_capture_census logo_alpha.png
    .venv/Scripts/python -m tools.column_capture_census --json out.json
    .venv/Scripts/python -m tools.column_capture_census --corpus --on-only         --guard lettering_columns_ink_link        # what a guard flag refuses
    .venv/Scripts/python -m tools.column_capture_census --signals         --base lettering_columns_skip_blobs lettering_columns_ink_link   # candidate margins

`--guard FLAG...` adds a third arm, lane ON with those flags ON too, and
lists the shapes the lane takes without them and not with them (`refused`),
each with its hand label: the census a guard is judged on. `--base FLAG...`
turns flags ON in every arm (a guard judged with the others already ON).
`--signals` measures each candidate signal for a new guard on the corpus:
the lane's NOT-LETTER house-group-only captures against every labelled
letter and every house-only shape taken on an unlabelled fixture, and the
gap between them (`margins`). OCR confidence is measured only where
`tesseract` is on PATH, and says so when it is not.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TESTDATA = ROOT / "testdata"
TRUTH = TESTDATA / "lettering_truth.json"

# The truth file names fixtures by corpus case; map to the scorecard file so a
# scorecard row can be scored against hand labels at the settings they were
# made on (`tools.thin_strokes.REAL_ART`: Studio's six colours).
TRUTH_CASE_FILE = {
    "becker": "becker_marine_logo.png",
    "tires": "logo_script_tires.png",
    "enthusiast": "photo/enthusiast_logo.png",
    "fremont": "photo/logo_hotel_fremont.webp",
    "bridge": "photo/logo_bridge_bar.jpg",
    "gaulke": "photo/logo_gaulke_roofing.png",
    "drone": "photo/drone_render.png",
    "screenshot": "photo/screenshot_phone_ui_golke.jpg",
}


def lane_takes(path, cfg):
    """Run the pipeline with `cfg` and return (result, plan, taken, declined).

    `taken`: shape ids the Column lane built columns for. `declined`: shape
    ids `is_lettering` admitted whose lane build came back empty (they fall
    to the ordinary ladder). Both come from a wrapper around the stage 7
    entry point; the engine is not touched."""
    from digitizer_core import stage7_sequence as s7
    from digitizer_core.pipeline import plan_stitches, run_stages

    taken: list[str] = []
    declined: list[str] = []
    real = s7.lettering_columns_shape

    def spy(poly, shape_id, **kw):
        runs, report = real(poly, shape_id, **kw)
        (declined if report.get("empty") else taken).append(shape_id)
        return runs, report

    s7.lettering_columns_shape = spy
    try:
        res = run_stages(path, cfg)
        plan = plan_stitches(res, cfg)
    finally:
        s7.lettering_columns_shape = real
    return res, plan, taken, declined


def shape_row(region, label=None):
    from digitizer_core.columns import skeleton_nodes
    m = region.meta or {}
    x0, y0, x1, y1 = region.polygon.bounds
    poly = region.polygon
    w_mean = 2.0 * poly.area / max(poly.length, 1e-9)       # mean stroke width, mm
    return {
        "stroke_over_h": round(w_mean / max(y1 - y0, x1 - x0, 1e-9), 3),
        "solidity": round(poly.area / max(poly.convex_hull.area, 1e-9), 3),
        "holes": len(getattr(poly, "interiors", []) or []),
        "skeleton_nodes": skeleton_nodes(poly),
        "shape_id": region.shape_id,
        "w_mm": round(x1 - x0, 2), "h_mm": round(y1 - y0, 2),
        "area_mm2": round(region.polygon.area, 2),
        "text_candidate": bool(m.get("text_candidate")),
        "text_cluster_id": m.get("text_cluster_id"),
        "lettering_group": bool(m.get("lettering_group")),
        "rescued": bool(m.get("rescued_small_shape")),
        "ocr_char": m.get("ocr_char"),
        "label": label,
    }


def census_one(fixture: str, cfg_kw: dict, truth_case: str | None = None,
               image=None, on_only: bool = False, guard: list[str] | None = None) -> dict:
    from digitizer_core import PipelineConfig

    path = TESTDATA / fixture if image is None else image
    out: dict = {"fixture": fixture, "cfg": cfg_kw}
    arms = {}
    for arm, on in (("off", False), ("on", True)):
        if on_only and not on:
            arms[arm] = {"stitches": 0, "trims": 0, "color_changes": 0, "jumps": 0,
                         "taken": [], "declined": [], "secs": 0}
            continue
        t = time.time()
        cfg = PipelineConfig(**cfg_kw, lettering_columns=on)
        res, plan, taken, declined = lane_takes(path, cfg)
        s = plan.stats
        arms[arm] = {"stitches": s.stitch_count, "trims": s.trims,
                     "color_changes": s.color_changes, "jumps": s.jumps,
                     "taken": taken, "declined": declined,
                     "secs": round(time.time() - t)}
        if on:
            by_id = {r.shape_id: r for r in res.regions}
            lab: dict[str, str] = {}
            ignore: set[str] = set()
            if truth_case:
                tr = json.loads(TRUTH.read_text())["fixtures"].get(truth_case)
                if tr:
                    lab = {sid: line for line, ids in tr["lines"].items() for sid in ids}
                    ignore = set(tr.get("ignore", []))
                    have = set(by_id)
                    if any(s_ not in have for s_ in lab):
                        lab, ignore = {}, set()   # STALE labels: do not score
                        out["truth"] = "stale"
            out["n_regions"] = len(res.regions)
            out["rows"] = [
                shape_row(by_id[sid],
                          None if not lab else ("letter" if sid in lab
                                                else ("ignored" if sid in ignore else "NOT-LETTER")))
                for sid in taken if sid in by_id]
            out["declined_rows"] = [shape_row(by_id[sid]) for sid in declined if sid in by_id]
            if lab:
                out["truth"] = "scored"
    if guard:
        cfg = PipelineConfig(**cfg_kw, lettering_columns=True, **{k: True for k in guard})
        res_g, plan_g, taken_g, _decl = lane_takes(path, cfg)
        s = plan_g.stats
        arms["guard"] = {"flags": list(guard), "stitches": s.stitch_count, "trims": s.trims,
                         "color_changes": s.color_changes, "jumps": s.jumps,
                         "taken": taken_g}
        kept = set(taken_g)
        out["refused"] = [x for x in out.get("rows", []) if x["shape_id"] not in kept]
        out["gained"] = sorted(set(taken_g) - set(arms["on"]["taken"]))
    out.update(arms)
    return out


# --- `--signals`: which shape signal separates a false capture from a letter?
#
# The candidates measured for `cfg.lettering_columns_icon_guard` (PR body
# has the table). Each is read off a tagged shape; `margins` then sets the
# lane's NOT-LETTER house-only captures against every hand-labelled letter
# and against the house-only shapes the lane takes on an unlabelled fixture
# (golden_tee's swashes, which are letters).

def _line_residual(region, mates) -> float | None:
    """Off the reading line: the smallest, over house-group mates of like
    height (0.8-1.25x), of the larger of the top and bottom offsets, over the
    shape's height. None with no like-height mate."""
    x0, y0, x1, y1 = region.polygon.bounds
    h = max(y1 - y0, 1e-9)
    best = None
    for o in mates:
        if o is region:
            continue
        ox0, oy0, ox1, oy1 = o.polygon.bounds
        if not 0.8 <= (oy1 - oy0) / h <= 1.25:
            continue
        d = max(abs(oy0 - y0), abs(oy1 - y1)) / h
        best = d if best is None else min(best, d)
    return best


def shape_signals(regions, ocr: bool) -> dict[str, dict]:
    """Every candidate signal for every tagged shape, by shape id."""
    import cv2
    import numpy as np
    from digitizer_core import textcluster as tc
    from digitizer_core.columns import skeleton_nodes
    from digitizer_core.shapefield import rasterize_polygon

    mates = {}
    for g in tc._lettering_groups(regions):
        for r in g:
            mates[r.shape_id] = g
    out = {}
    for r in regions:
        m = r.meta or {}
        if not (m.get("text_candidate") or m.get("lettering_group")):
            continue
        p = r.polygon
        x0, y0, x1, y1 = p.bounds
        mask, *_ = rasterize_polygon(p) if p.geom_type == "Polygon" else (None,)
        hu1 = None
        if mask is not None and mask.any():
            v = float(cv2.HuMoments(cv2.moments(mask, binaryImage=True))[0, 0])
            hu1 = round(-np.sign(v) * np.log10(abs(v)), 3) if v else 0.0
        conf = tc._ocr_glyph_guess(p)[1] if ocr else None
        res = _line_residual(r, mates[r.shape_id]) if r.shape_id in mates else None
        out[r.shape_id] = {
            "skeleton_nodes": skeleton_nodes(p),
            "stroke_over_h": 2.0 * p.area / max(p.length, 1e-9) / max(x1 - x0, y1 - y0, 1e-9),
            "solidity": p.area / max(p.convex_hull.area, 1e-9),
            "holes": len(getattr(p, "interiors", []) or []),
            "hu1": hu1,
            "line_residual": res,
            "ocr_confidence": conf,
        }
    return out


SIGNALS = ("skeleton_nodes", "stroke_over_h", "solidity", "holes", "hu1",
           "line_residual", "ocr_confidence")


def margins(captures: list[dict], letters: list[dict], keep: list[dict]) -> dict[str, dict]:
    """Per signal: the ranges, and the gap between captures and the shapes
    that must be kept (letters + `keep`), in whichever direction is wider.
    A gap <= 0 means no threshold on that signal alone separates them."""
    out = {}
    for k in SIGNALS:
        cv = [c[k] for c in captures if c.get(k) is not None]
        lv = [c[k] for c in letters + keep if c.get(k) is not None]
        if not cv or not lv:
            out[k] = {"gap": None, "why": "not measured"}
            continue
        above, below = min(cv) - max(lv), min(lv) - max(cv)
        out[k] = {"captures": [round(min(cv), 3), round(max(cv), 3)],
                  "kept": [round(min(lv), 3), round(max(lv), 3)],
                  "gap": round(max(above, below), 3),
                  "side": "captures above" if above >= below else "captures below"}
    return out


def signals_census(cases=None, base=None) -> dict:
    """Run each corpus case with the lane (and `base` flags) ON; return the
    three populations and `margins` over them."""
    import shutil
    from digitizer_core import PipelineConfig
    from tools.thin_strokes import corpus_cases

    ocr = shutil.which("tesseract") is not None
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))["fixtures"]
    captures, letters, keep = [], [], []
    for name, path, width, garment in corpus_cases():
        if cases and name not in cases:
            continue
        cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6,
                             lettering_columns=True, **{k: True for k in (base or [])})
        res, _plan, taken, _decl = lane_takes(path, cfg)
        sig = shape_signals(res.regions, ocr)
        by_id = {r.shape_id: r for r in res.regions}
        tr = truth.get(name)
        lab = {s for ids in tr["lines"].values() for s in ids} if tr else set()
        ign = set(tr.get("ignore", [])) if tr else set()
        if lab and not lab <= set(by_id):
            lab, ign = set(), set()                      # stale: not scored
        for sid, s in sig.items():
            m = by_id[sid].meta
            s = dict(s, case=name, shape_id=sid)
            house_only = m.get("lettering_group") and not m.get("text_candidate")
            if sid in lab:
                letters.append(s)
            elif lab and sid not in ign and sid in taken and house_only:
                captures.append(s)
            elif not tr and sid in taken and house_only:
                keep.append(s)
        print(f"  {name}: tagged {len(sig)} letters {len(lab & set(sig))}", flush=True)
    return {"ocr": ocr, "captures": captures, "letters": letters, "keep": keep,
            "margins": margins(captures, letters, keep)}


def colour_grid():
    """`test_preflight`'s twelve-patch colour grid (the constructed 11-stop
    negative): twelve solid patches, none of them a letter. Returns the image."""
    import numpy as np
    colors = [(230, 40, 40), (40, 180, 40), (40, 40, 230), (230, 230, 40),
              (230, 40, 230), (40, 230, 230), (140, 70, 20), (250, 140, 20),
              (120, 20, 160), (20, 120, 90), (90, 90, 90), (10, 10, 10)]
    patches = np.full((340, 460, 3), 255, np.uint8)
    for i, c in enumerate(colors):
        row, col = divmod(i, 4)
        y, x = 20 + row * 105, 20 + col * 110
        patches[y:y + 85, x:x + 90] = c
    return patches


def render_pair(name: str, source, cfg_kw: dict, out: Path, *, flags_on: dict | None = None,
                px_per_mm: float = 10.0, zoom_px_per_mm: float = 28.0, zoom_ids=None,
                guard: bool = False) -> list[Path]:
    """Lane OFF | lane ON thread renders, same frame and scale, plus a zoom
    panel pair on the lane-taken shape(s) (`zoom_ids`, else the first taken).
    `flags_on` lets the caller add a guard flag to the ON arm. `guard`: both
    arms run the lane, and only `flags_on` differs (guard OFF | guard ON);
    the zoom defaults to the shapes the guard refused."""
    import cv2
    import numpy as np
    from digitizer_core import PipelineConfig, stitchviz
    from digitizer_core.adapter import plan_to_design

    designs, takens, regions = {}, {}, {}
    for tag, kw in (("off", {"lettering_columns": guard}),
                    ("on", {"lettering_columns": True, **(flags_on or {})})):
        cfg = PipelineConfig(**cfg_kw, **kw)
        res, plan, taken, _decl = lane_takes(source, cfg)
        designs[tag] = plan_to_design(plan, name=f"{name} {tag}")
        takens[tag] = taken
        regions[tag] = {r.shape_id: r for r in res.regions}
    default = ([s for s in takens["off"] if s not in set(takens["on"])] if guard
               else takens["on"])
    ids = [s for s in (zoom_ids or default) if s in regions["on"]][:6]
    arm = ("guard", "Column lane ON, guard") if guard else ("lane", "Column lane")
    stem = f"{name}_guard" if guard else name
    ba = stitchviz._bounds(designs["off"]["stitches"])
    bb = stitchviz._bounds(designs["on"]["stitches"])
    ux0, ux1 = min(ba[0], bb[0]), max(ba[1], bb[1])
    uy0, uy1 = min(ba[2], bb[2]), max(ba[3], bb[3])
    for d in designs.values():
        d["stitches"] = ([{"x": ux0, "y": uy0, "type": "jump"},
                          {"x": ux1, "y": uy1, "type": "jump"}] + list(d["stitches"]))
    pad = 2.0

    def label(img, text):
        bar = np.full((24, img.shape[1], 3), 235, np.uint8)
        cv2.putText(bar, text, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1, cv2.LINE_AA)
        return np.vstack([bar, img])

    outs: list[Path] = []
    out.mkdir(parents=True, exist_ok=True)
    full = {k: stitchviz.render_design(d, px_per_mm=px_per_mm, pad_mm=pad) for k, d in designs.items()}
    panel = np.hstack([label(full["off"], f"{name}: {arm[1]} OFF ({len(takens['off'])} shapes)"),
                       label(full["on"], f"{name}: {arm[1]} ON ({len(takens['on'])} shapes)")])
    p = out / f"{stem}_full.png"
    cv2.imwrite(str(p), panel)
    outs.append(p)
    if ids:
        zoom = {k: stitchviz.render_design(d, px_per_mm=zoom_px_per_mm, pad_mm=pad)
                for k, d in designs.items()}
        polys = [regions["on"][s].polygon for s in ids]
        x0 = min(q.bounds[0] for q in polys) - 1.5
        x1 = max(q.bounds[2] for q in polys) + 1.5
        y0 = min(q.bounds[1] for q in polys) - 1.5
        y1 = max(q.bounds[3] for q in polys) + 1.5
        s = zoom_px_per_mm
        # `adapter` writes x = 10 x_mm, y = -10 y_mm; `stitchviz._frame` maps
        # that to pixels on the union box with `pad` around it.
        def to_px(xm, ym):
            return (xm - ux0 / 10.0 + pad) * s, (uy1 / 10.0 + ym + pad) * s
        ax, ay = to_px(x0, y0)
        bx, by = to_px(x1, y1)
        h, w = zoom["off"].shape[:2]
        ax, bx = int(max(0, min(ax, bx))), int(min(w, max(ax, bx)))
        ay, by = int(max(0, min(ay, by))), int(min(h, max(ay, by)))
        crops = [label(zoom[k][ay:by, ax:bx], f"zoom, {arm[0]} {k.upper()} ({', '.join(ids[:3])}{'...' if len(ids) > 3 else ''})")
                 for k in ("off", "on")]
        hh = max(c.shape[0] for c in crops)
        crops = [np.pad(c, ((0, hh - c.shape[0]), (0, 0), (0, 0)), constant_values=255) for c in crops]
        p = out / f"{stem}_zoom.png"
        cv2.imwrite(str(p), np.hstack(crops))
        outs.append(p)
    return outs


def _print_guard(r: dict) -> None:
    g = r.get("guard")
    if not g:
        return
    print(f"    guard {'+'.join(g['flags'])}: taken {len(r['on']['taken'])}->{len(g['taken'])} "
          f"st {r['on']['stitches']}->{g['stitches']} trims {r['on']['trims']}->{g['trims']} "
          f"refused {len(r['refused'])} gained {len(r['gained'])}", flush=True)
    for x in r["refused"]:
        print(f"      refused {x['shape_id']} {x['w_mm']}x{x['h_mm']} mm "
              f"tc={x['text_candidate']} lg={x['lettering_group']} label={x['label']}", flush=True)


def matrix(only: list[str] | None = None):
    from tools.corpus_scorecard import FIXTURES
    for f in FIXTURES:
        if only and f not in only:
            continue
        if not (TESTDATA / f).exists():
            continue
        yield f


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*")
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--max-colors", type=int, default=6, dest="max_colors")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--on-only", action="store_true", dest="on_only",
                    help="skip the lane-OFF arm (shape rows only; OFF columns read 0)")
    ap.add_argument("--ids", nargs="*", default=[], help="shape ids to zoom on in --render")
    ap.add_argument("--flag", nargs="*", default=[], help="config flags to turn ON in the render's ON arm")
    ap.add_argument("--guard", nargs="*", default=[],
                    help="config flags for a third arm (lane ON + these); prints what they refuse")
    ap.add_argument("--corpus",action="store_true",
                    help="the real-art corpus at the settings the hand labels were made at")
    ap.add_argument("--render", type=Path, help="write OFF|ON renders of the named fixtures here")
    ap.add_argument("--grid", action="store_true", help="the synthetic twelve-patch colour grid only")
    ap.add_argument("--base", nargs="*", default=[],
                    help="config flags ON in EVERY arm (e.g. the guards already flipped)")
    ap.add_argument("--signals", action="store_true",
                    help="corpus: each candidate signal's margin, false captures vs letters")
    args = ap.parse_args(argv)

    base = {k: True for k in args.base}
    if args.signals:
        r = signals_census(args.fixtures or None, args.base)
        print(f"OCR {'available' if r['ocr'] else 'UNAVAILABLE (tesseract not found): not measured'}")
        for name in ("captures", "keep"):
            for s in r[name]:
                print(f"  {name[:-1] if name == 'captures' else 'keep'} {s['case']} {s['shape_id']} "
                      + " ".join(f"{k}={s[k] if not isinstance(s[k], float) else round(s[k], 3)}"
                                 for k in SIGNALS))
        print(f"{len(r['captures'])} captures, {len(r['letters'])} labelled letters, "
              f"{len(r['keep'])} house-only shapes taken on unlabelled fixtures")
        for k, v in r["margins"].items():
            print(f"  {k:15s} {v}")
        if args.json:
            args.json.write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")
        return 0

    inv = {v: k for k, v in TRUTH_CASE_FILE.items()}
    results = []
    if args.corpus:
        # The settings the hand labels were made at (`tools.thin_strokes.corpus_cases`).
        from tools.thin_strokes import corpus_cases
        for name, path, width, garment in corpus_cases():
            if args.fixtures and name not in args.fixtures:
                continue
            rel = path.relative_to(TESTDATA).as_posix()
            kw = {"target_width_mm": width, "garment_id": garment, "max_colors": 6, **base}
            r = census_one(rel, kw, name if name in TRUTH_CASE_FILE else None, on_only=args.on_only,
                           guard=args.guard)
            r["case"] = name
            results.append(r)
            on, off = r["on"], r["off"]
            bad = [x for x in r["rows"] if x["label"] == "NOT-LETTER"]
            print(f"{name:11s} taken {len(on['taken']):3d} truth={r.get('truth', '-'):6s} "
                  f"false={len(bad)} st {off['stitches']}->{on['stitches']} "
                  f"trims {off['trims']}->{on['trims']} cc {off['color_changes']}->{on['color_changes']}",
                  flush=True)
            _print_guard(r)
            if args.json:
                args.json.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
        return 0
    if args.grid:
        r = census_one("colour_grid", {"target_width_mm": 100.0}, image=colour_grid())
        r["rows"] = [(x["shape_id"], x["w_mm"], x["h_mm"], x["text_candidate"], x["lettering_group"])
                     for x in r["rows"]]
        print(json.dumps(r, default=str))
        if args.render:
            for p in render_pair("colour_grid", colour_grid(), {"target_width_mm": 100.0},
                                 args.render, px_per_mm=6.0, zoom_px_per_mm=12.0):
                print(p)
        return 0
    if args.render:
        for f in matrix(args.fixtures):
            kw = {"target_width_mm": args.width, "garment_id": args.garment,
                  "max_colors": args.max_colors, **base}
            for p in render_pair(Path(f).stem, TESTDATA / f, kw, args.render,
                                 zoom_ids=args.ids or None,
                                 flags_on={k: True for k in (args.flag or args.guard)},
                                 guard=bool(args.guard)):
                print(p)
        return 0
    for f in matrix(args.fixtures):
        kw = {"target_width_mm": args.width, "garment_id": args.garment,
              "max_colors": args.max_colors, **base}
        try:
            r = census_one(f, kw, inv.get(f), on_only=args.on_only, guard=args.guard)
        except Exception as exc:  # noqa: BLE001
            print(f"{f}: ERROR {type(exc).__name__}: {exc}", flush=True)
            continue
        results.append(r)
        off, on = r["off"], r["on"]
        bad = [x for x in r["rows"] if x["label"] == "NOT-LETTER"]
        print(f"{f:44s} taken {len(on['taken']):3d} declined {len(on['declined']):2d}"
              f"  st {off['stitches']:6d}->{on['stitches']:6d}"
              f" trims {off['trims']:3d}->{on['trims']:3d}"
              f" cc {off['color_changes']:3d}->{on['color_changes']:3d}"
              f"  truth={r.get('truth', '-')} false={len(bad)}  {on['secs']}s", flush=True)
        _print_guard(r)
        if args.json:
            args.json.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
