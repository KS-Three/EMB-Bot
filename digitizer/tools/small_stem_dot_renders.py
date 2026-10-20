#!/usr/bin/env python
"""Renders for MASTER_SCOPE item 52: the i/j dot and the small stem, OFF
beside ON, at the sizes Kent reads. Nothing here changes the engine or a
constant; it digitizes committed fixtures under the two built-OFF flags
(`cfg.lettering_columns_small_stem`, PR #896; `cfg.small_dot_rung`, PR #939,
with its lettering scope `cfg.small_dot_rung_lettering`, PR #975) and draws
what each arm sews, thread at its laid width (`digitizer_core.stitchviz`
through `tools/fremont_triage`'s panel helpers), so the flips can be decided
from a picture rather than from a count.

The five arms, every cell its own process (the corpus tools' rule):

    off    the shipped config
    stem   lettering_columns_small_stem ON
    dot    small_dot_rung ON
    both   both ON
    scope  both ON + small_dot_rung_lettering (the rung kept off photo specks)

The cases: the synthetic Aileron fixture (its lowercase i: a 0.57 mm stem
and a 0.75 mm dot at 80 mm) and the word "hijlij" drawn at runtime in the
same CC0 face (two i, two j), both `forced_class="flat"` as #896 and #939
measured them, at the 50 and 80 mm scales; Fremont on a Hat through the
Studio's own request (`fremont_triage.run_arm`) at 50 and 80 mm, read over
the EAT | STAY | PLAY tagline (no i or j in the art; the two "|" bars are
its thin stems); the three `sp_fremont_tagline` small-print cells of the
17-design corpus (the tagline crop at 2.5, 3 and 4 mm caps); and Becker at
50 and 80 mm, left chest, the Studio's six colours (a capital I, no dot: a
control).

    python -m tools.small_stem_dot_renders all --out DIR [--jobs 4] [--only NAME,..]
    python -m tools.small_stem_dot_renders cell CASE ARM --out DIR
    python -m tools.small_stem_dot_renders render --out DIR --renders DIR2
    python -m tools.small_stem_dot_renders tables --out DIR
    python -m tools.small_stem_dot_renders bisect CASE SHAPE_ID --out DIR --renders DIR2

`bisect` draws the crop round one shape from every arm's stitch stream cut at
each colour change, so a mark that is sewn but then covered by a later block
(Fremont's Wisconsin star under the rung: sewn in the first white block, the
black state over it) can be told from one that was never sewn.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

TESTDATA = ROOT / "testdata"
WORD = "hijlij"
WORD_PX_PER_MM_AT_80 = 28.125      # lowercase_aileron at 80 mm (tools/small_dot_rung.py)
WIDTHS = (50.0, 80.0)
SP_CAPS = (2.5, 3.0, 4.0)
BECKER = "becker_marine_logo.png"

# Every flag explicit per arm: all three are ON by default since 2026-10-20
# (Kent's flip), so "off" is the pre-flip engine, and the shipped default is
# now the "scope" arm.
_OFF = {"lettering_columns_small_stem": False, "small_dot_rung": False,
        "small_dot_rung_lettering": False}
ARMS = {
    "off": dict(_OFF),
    "stem": {**_OFF, "lettering_columns_small_stem": True},
    "dot": {**_OFF, "small_dot_rung": True},
    "both": {**_OFF, "lettering_columns_small_stem": True, "small_dot_rung": True},
    "scope": {"lettering_columns_small_stem": True, "small_dot_rung": True,
              "small_dot_rung_lettering": True},
}
ARM_LABEL = {"off": "OFF (pre-flip)", "stem": "small_stem ON", "dot": "small_dot_rung ON",
             "both": "both ON", "scope": "both ON + lettering scope (shipped)"}
FOCUS_PPM = 40.0
TIGHT_PPM = 120.0
TIGHT_MAX_MM2 = 30.0


def cases() -> dict[str, dict]:
    """name -> spec, in run order."""
    out: dict[str, dict] = {}
    for w in WIDTHS:
        out[f"aileron_{w:g}"] = {"kind": "fixture", "width_mm": w}
        out[f"hijlij_{w:g}"] = {"kind": "word", "scale_mm": w}
    for w in WIDTHS:
        out[f"fremont_hat_{w:g}"] = {"kind": "hat", "width_mm": w}
    for cap in SP_CAPS:
        out[f"sp_fremont_tagline_{cap:g}"] = {"kind": "small_print", "fixture": "fremont_tagline", "cap": cap}
    for w in WIDTHS:
        out[f"becker_{w:g}"] = {"kind": "logo", "path": str(TESTDATA / BECKER), "width_mm": w}
    return out


# --- one cell ------------------------------------------------------------------------

def _word_meta(out: Path) -> tuple[Path, dict]:
    from tools.stem_trace import word_image
    path = out / f"word_{WORD}.png"
    out.mkdir(parents=True, exist_ok=True)
    meta = word_image(WORD, path)
    return path, meta


def _word_width_mm(meta: dict, scale_mm: float) -> float:
    xs = [g["box"][0] for g in meta["glyphs"]] + [g["box"][2] for g in meta["glyphs"]]
    return round((max(xs) - min(xs)) * scale_mm / (WORD_PX_PER_MM_AT_80 * 80.0), 3)


def _digitize_case(name: str, over: dict, out: Path) -> dict:
    """-> {result, plan, cfg, meta?, source, image_wh}; `source` is how the
    render step reloads the artwork."""
    import cv2
    from digitizer_core import PipelineConfig, digitize
    from tools import small_lettering_compare as slc
    spec = cases()[name]
    kind = spec["kind"]
    if kind == "fixture":
        from tools.lowercase_angle import FIXTURE
        meta = json.loads(FIXTURE.with_suffix(".json").read_text(encoding="utf-8"))
        path = FIXTURE.with_suffix(".png")
        cfg = PipelineConfig(target_width_mm=spec["width_mm"], forced_class="flat", **over)
        result, plan = digitize(path, cfg)
        return dict(result=result, plan=plan, cfg=cfg, meta=meta, source=str(path),
                    image_wh=list(meta["image"]))
    if kind == "word":
        path, meta = _word_meta(out)
        cfg = PipelineConfig(target_width_mm=_word_width_mm(meta, spec["scale_mm"]),
                             forced_class="flat", **over)
        result, plan = digitize(path, cfg)
        return dict(result=result, plan=plan, cfg=cfg, meta=meta, source=str(path),
                    image_wh=list(meta["image"]))
    if kind == "hat":
        from tools import fremont_triage as ft
        run = ft.run_arm("main", spec["width_mm"], None, preflight=False, overrides=dict(over))
        src = cv2.imread(str(ft.FIXTURE), cv2.IMREAD_UNCHANGED)
        return dict(result=run["result"], plan=run["plan"], cfg=run["cfg"], meta=None,
                    source=str(ft.FIXTURE), image_wh=[src.shape[1], src.shape[0]])
    if kind == "logo":
        from tools.thin_strokes import STUDIO_MAX_COLORS
        run = slc._digitize(spec["path"], {"target_width_mm": spec["width_mm"], "garment_id": "left_chest",
                                           "max_colors": STUDIO_MAX_COLORS, **over})
        src = cv2.imread(spec["path"], cv2.IMREAD_UNCHANGED)
        return dict(result=run["result"], plan=run["plan"], cfg=run["cfg"], meta=None,
                    source=spec["path"], image_wh=[src.shape[1], src.shape[0]])
    if kind == "small_print":
        from tools import small_print
        run, _extra = slc._digitize_small_print(spec, over, out)
        img = small_print.load(spec["fixture"])
        src = out / f"sp_source_{spec['fixture']}.png"
        if not src.exists():
            cv2.imwrite(str(src), img)
        return dict(result=run["result"], plan=run["plan"], cfg=run["cfg"], meta=None,
                    source=str(src), image_wh=[img.shape[1], img.shape[0]])
    raise ValueError(kind)


def _px_maps(art_box_frac, design_size_mm, image_wh):
    """mm <-> source px (`lowercase_angle.mm_to_px`'s own transform)."""
    w, h = image_wh
    x0, y0, x1, y1 = art_box_frac
    s = (x1 - x0) * w / design_size_mm[0]
    cx, cy = (x0 + x1) / 2.0 * w, (y0 + y1) / 2.0 * h
    return (lambda x, y: (cx + x * s, cy + y * s)), (lambda px, py: ((px - cx) / s, (py - cy) / s)), s


def _sides(poly):
    import math
    rect = poly.minimum_rotated_rectangle
    pts = list(getattr(rect, "exterior", rect).coords)
    if len(pts) < 3:
        return 0.0, 0.0
    a = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
    b = math.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
    return round(max(a, b), 2), round(min(a, b), 2)


def gkey(bounds, area) -> str:
    """A shape by its geometry, not its id: an admitted part renumbers the
    shapes after it (PR #975), so ids alone overcount a change."""
    return "|".join(f"{v:.2f}" for v in bounds) + f"|{area:.3f}"


def run_cell(name: str, arm: str, out: Path) -> dict:
    from shapely.geometry import Polygon
    from digitizer_core import machine
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.columns import is_lettering, is_thin_stem
    from tools.hairline_logo_bill import shape_digests
    from tools.small_dot_rung import count_dot_rings, plan_md5
    from tools.stem_trace import _glyph_at
    t = time.time()
    with count_dot_rings() as rings:
        run = _digitize_case(name, ARMS[arm], out)
    result, plan, cfg = run["result"], run["plan"], run["cfg"]
    to_px, _to_mm, _s = _px_maps(result.art_box_frac, result.design_size_mm, run["image_wh"])
    sewn: dict[str, dict] = {}
    for _b, r in plan.iter_runs():
        d = sewn.setdefault(r.shape_id, {})
        d[r.kind] = d.get(r.kind, 0) + len(r.points)
    floor = cfg.min_detail_mm ** 2
    digests = shape_digests(plan)
    regions = {}
    for r in result.regions:
        poly = r.polygon
        ring = poly.exterior.length if isinstance(poly, Polygon) else None
        c = poly.centroid
        glyph = None
        if run["meta"] is not None:
            g = _glyph_at(run["meta"], *to_px(c.x, c.y))
            glyph = g["ch"] if g else None
        long_s, short_s = _sides(poly) if isinstance(poly, Polygon) else (0.0, 0.0)
        regions[r.shape_id] = dict(
            key=gkey(poly.bounds, poly.area), area_mm2=round(poly.area, 3),
            bounds_mm=[round(v, 2) for v in poly.bounds], ring_mm=(None if ring is None else round(ring, 2)),
            long_mm=long_s, short_mm=short_s, thread=r.thread_number, glyph=glyph,
            lettering=bool(is_lettering(r, cfg)), under_floor=bool(poly.area < floor),
            thin_stem=bool(isinstance(poly, Polygon) and is_thin_stem(poly, cfg.min_detail_mm)),
            dot_band=bool(ring is not None and machine.DOT_RUNG_MIN_LOOP_MM <= ring < machine.RUN_MIN_LOOP_MM),
            dot_rung=bool((r.meta or {}).get("dot_rung")),
            sewn=sewn.get(r.shape_id, {}), digest=digests.get(r.shape_id))
    codes: dict[str, int] = {}
    for w in list(result.warnings or []) + list(plan.warnings or []):
        codes[w.get("code")] = codes.get(w.get("code"), 0) + 1
    rec = dict(case=name, arm=arm, kind=cases()[name]["kind"], overrides=ARMS[arm],
               target_width_mm=cfg.target_width_mm, design_size_mm=[round(v, 2) for v in result.design_size_mm],
               stitches=plan.stats.stitch_count, trims=plan.stats.trims, md5=plan_md5(plan),
               shapes=len(result.regions), dot_rings=rings["dot_rings"],
               codes={k: v for k, v in codes.items() if k in ("SHAPE_NOT_STITCHED", "DROPPED_SMALL_SHAPES")},
               regions=regions, art_box_frac=list(result.art_box_frac), image_wh=run["image_wh"],
               source=run["source"], meta=run["meta"], secs=round(time.time() - t, 1))
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}__{arm}.json").write_text(json.dumps(rec, indent=1))
    (out / f"{name}__{arm}_design.json").write_text(json.dumps(plan_to_design(plan, name=name)))
    print(f"{name}__{arm}: {rec['stitches']:,} st, {rec['trims']} tr, md5 {rec['md5'][:8]}, "
          f"{rec['shapes']} shapes, {rec['dot_rings']} tack rings, {rec['secs']} s", flush=True)
    return rec


# --- what changed ----------------------------------------------------------------------

def load_cells(out: Path) -> dict[str, dict[str, dict]]:
    cells: dict[str, dict[str, dict]] = {}
    for p in sorted(out.glob("*__*.json")):
        if p.name.endswith("_design.json") or p.name.startswith("sp_ref"):
            continue
        d = json.loads(p.read_text())
        cells.setdefault(d["case"], {})[d["arm"]] = d
    return cells


def _by_key(rec: dict) -> dict[str, dict]:
    return {r["key"]: dict(r, shape_id=sid) for sid, r in rec["regions"].items()}


def changed(base: dict, arm: dict) -> list[dict]:
    """The shapes `arm` lays differently from `base`, by geometry: a key in
    one arm only (admitted or retired), or the same key with other runs."""
    b, a = _by_key(base), _by_key(arm)
    rows = []
    for k in sorted(set(b) | set(a), key=lambda k: (a.get(k) or b[k])["bounds_mm"]):
        rb, ra = b.get(k), a.get(k)
        if rb is not None and ra is not None and rb["digest"] == ra["digest"]:
            continue
        r = ra or rb
        rows.append(dict(key=k, status=("new" if rb is None else "gone" if ra is None else "relaid"),
                         shape_id=r["shape_id"], glyph=r.get("glyph"), area_mm2=r["area_mm2"],
                         bounds_mm=r["bounds_mm"], ring_mm=r["ring_mm"], long_mm=r["long_mm"],
                         short_mm=r["short_mm"], lettering=r["lettering"], thin_stem=r["thin_stem"],
                         under_floor=r["under_floor"], dot_band=r["dot_band"], dot_rung=r.get("dot_rung"),
                         before=(rb or {}).get("sewn", {}), after=(ra or {}).get("sewn", {})))
    return rows


def _what(r: dict) -> str:
    tags = []
    if r.get("glyph"):
        tags.append(f"'{r['glyph']}'")
    if r["thin_stem"] and r["under_floor"] and r["lettering"]:
        tags.append("stem")
    elif r["under_floor"] and r["lettering"]:
        tags.append("lettering, under floor")
    if r["dot_band"]:
        tags.append("ring in the rung's band")
    if r.get("dot_rung"):
        tags.append("rung-admitted")
    return " ".join(tags) or "-"


def _kinds(d: dict) -> str:
    return ", ".join(f"{k} {n}" for k, n in sorted(d.items())) if d else "nothing"


def describe(r: dict) -> str:
    where = f"{r['area_mm2']:.3f} mm2, {r['long_mm']:.2f} x {r['short_mm']:.2f} mm"
    if r["status"] == "new":
        return f"+{r['shape_id']} ({_what(r)}; {where}): new, sews {_kinds(r['after'])}"
    if r["status"] == "gone":
        return f"-{r['shape_id']} ({_what(r)}; {where}): gone, sewed {_kinds(r['before'])}"
    return f"{r['shape_id']} ({_what(r)}; {where}): {_kinds(r['before'])} -> {_kinds(r['after'])}"


# --- tables --------------------------------------------------------------------------

def _title(name: str, rec: dict) -> str:
    spec = cases()[name]
    k = spec["kind"]
    if k == "fixture":
        return f"synthetic Aileron fixture, {spec['width_mm']:g} mm (forced flat)"
    if k == "word":
        return f"\"{WORD}\" at the {spec['scale_mm']:g} mm scale ({rec['target_width_mm']:g} mm wide, forced flat)"
    if k == "hat":
        return f"Fremont, Hat, the Studio's request at {spec['width_mm']:g} mm"
    if k == "small_print":
        return f"sp_fremont_tagline at {spec['cap']:g} mm caps ({rec['target_width_mm']:g} mm wide)"
    if k == "logo":
        return f"Becker, left chest, six colours, {spec['width_mm']:g} mm"
    return name


def candidates(rec: dict) -> list[dict]:
    """The shapes the flags look at in one arm: lettering stems under the
    floor (what `small_stem` sends to the lane) and rings in the rung's
    band (what `small_dot_rung` tack-rings or admits)."""
    rows = []
    for sid, r in rec["regions"].items():
        if (r["lettering"] and r["under_floor"]) or r["dot_band"] or r.get("dot_rung"):
            rows.append(dict(r, shape_id=sid))
    return rows


def material(r: dict) -> bool:
    """A change worth a picture: a shape admitted or retired, or one whose
    needle-down runs (satin, run, fill) moved. A neighbour that only re-walked
    its travel or underlay because the sew order shifted is not."""
    if r["status"] != "relaid":
        return True
    strip = lambda d: {k: v for k, v in d.items() if k not in ("travel", "underlay")}
    return strip(r["before"]) != strip(r["after"])


def summary(rows: list[dict]) -> str:
    new = [r for r in rows if r["status"] == "new"]
    gone = [r for r in rows if r["status"] == "gone"]
    moved = [r for r in rows if r["status"] == "relaid" and material(r)]
    walked = [r for r in rows if r["status"] == "relaid" and not material(r)]
    parts = []
    if new:
        parts.append(f"{len(new)} new ({', '.join(_what(r) for r in new)})")
    if gone:
        parts.append(f"{len(gone)} gone ({', '.join(_what(r) for r in gone)})")
    if moved:
        parts.append(f"{len(moved)} re-sewn ({', '.join(_what(r) for r in moved)})")
    if walked:
        parts.append(f"{len(walked)} re-walked only (travel/underlay)")
    return "; ".join(parts) or "0 (md5 moved, no shape)"


def tables(out: Path) -> str:
    cells = load_cells(out)
    lines = []
    for name in cases():
        arms = cells.get(name)
        if not arms or "off" not in arms:
            continue
        off = arms["off"]
        lines.append(f"### {_title(name, off)}\n")
        lines.append("| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |")
        lines.append("|---|---|---|---|---|---|---|")
        details = []
        for arm in ARMS:
            c = arms.get(arm)
            if not c:
                continue
            if arm == "off":
                ch = "-"
            elif c["md5"] == off["md5"]:
                ch = "**identical**"
            else:
                rows = changed(off, c)
                ch = summary(rows)
                mat = [describe(r) for r in rows if material(r)]
                if mat:
                    details.append(f"- **{ARM_LABEL[arm]}**: " + "; ".join(mat))
            md5 = f"`{c['md5'][:8]}`" + (" (= OFF)" if arm != "off" and c["md5"] == off["md5"] else "")
            lines.append(f"| {ARM_LABEL[arm]} | {c['stitches']:,} | {c['trims']} | {md5} | {c['shapes']} | "
                         f"{c['dot_rings']} | {ch} |")
        if details:
            lines.append("")
            lines.extend(details)
        cand = candidates(off)
        if cand:
            lines.append("")
            lines.append("What the flags see OFF (lettering shapes under the 2.25 mm2 floor, and rings in the "
                         "rung's 1.35 to 2.2 mm band):")
            lines.append("")
            lines.append("| shape | glyph | area mm2 | long x short mm | aspect | thin stem | ring mm | sewn OFF |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for r in cand:
                asp = (r["long_mm"] / r["short_mm"]) if r["short_mm"] else 0.0
                lines.append(f"| {r['shape_id']} | {r.get('glyph') or '-'} | {r['area_mm2']:.3f} | "
                             f"{r['long_mm']:.2f} x {r['short_mm']:.2f} | {asp:.1f} | {'yes' if r['thin_stem'] else 'no'} | "
                             f"{r['ring_mm']} | {_kinds(r['sewn'])} |")
        lines.append("")
    return "\n".join(lines)


# --- renders --------------------------------------------------------------------------

def _source_bgr(path: str):
    import cv2
    import numpy as np
    from digitizer_core.stitchviz import FABRIC_BGR
    src = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if src.ndim == 2:
        src = cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)
    if src.shape[2] == 4:
        rgb = src[..., :3].astype(float)
        a = src[..., 3:4].astype(float) / 255.0
        src = (rgb * a + np.array(FABRIC_BGR, float) * (1 - a)).astype(np.uint8)
    return src


def _artwork_crop(src, to_px, box_mm, size_wh, margin_mm):
    import cv2
    import numpy as np
    x0, y0, x1, y1 = box_mm
    ax, ay = to_px(x0 - margin_mm, y0 - margin_mm)
    bx, by = to_px(x1 + margin_mm, y1 + margin_mm)
    h, w = src.shape[:2]
    ax, bx = int(max(0, min(ax, bx))), int(min(w, max(ax, bx)))
    ay, by = int(max(0, min(ay, by))), int(min(h, max(ay, by)))
    if bx <= ax or by <= ay:
        return np.full((max(size_wh[1], 1), max(size_wh[0], 1), 3), 255, np.uint8)
    c = src[ay:by, ax:bx]
    return cv2.resize(c, (max(1, size_wh[0]), max(1, size_wh[1])), interpolation=cv2.INTER_AREA)


def _focus_boxes(name: str, rec: dict) -> list[tuple[str, list[float]]]:
    """(label, mm box) the 40 px/mm panel reads, per case."""
    spec = cases()[name]
    _to_px, to_mm, _s = _px_maps(rec["art_box_frac"], rec["design_size_mm"], rec["image_wh"])

    def gbox(glyphs):
        xs = [g["box"][0] for g in glyphs] + [g["box"][2] for g in glyphs]
        ys = [g["box"][1] for g in glyphs] + [g["box"][3] for g in glyphs]
        a, b = to_mm(min(xs), min(ys)), to_mm(max(xs), max(ys))
        return [a[0], a[1], b[0], b[1]]
    if spec["kind"] == "fixture":
        gl = [g for g in rec["meta"]["glyphs"] if g["line"] == 1 and g["ch"] in "siv"]
        return [("siv", gbox(gl)), ("i", gbox([g for g in gl if g["ch"] == "i"]))]
    if spec["kind"] == "word":
        gl = rec["meta"]["glyphs"]
        return [("word", gbox(gl)), ("ij", gbox(gl[1:3]))]
    if spec["kind"] == "hat":
        from tools import fremont_triage as ft
        w, h = rec["image_wh"]
        f = ft.ROIS["tagline"]
        a, b = to_mm(f[0] * w, f[1] * h), to_mm(f[2] * w, f[3] * h)
        return [("tagline", [a[0], a[1], b[0], b[1]])]
    bounds = [r["bounds_mm"] for r in rec["regions"].values()]
    box = [min(b[0] for b in bounds), min(b[1] for b in bounds), max(b[2] for b in bounds), max(b[3] for b in bounds)]
    return [("design", box)]


def _clusters(boxes: list[list[float]], gap_mm: float = 1.0, cap: int = 6,
              max_side_mm: float = 12.0) -> list[list[float]]:
    """Merge boxes that touch within `gap_mm` while the merged box stays under
    `max_side_mm` a side (so a trail of specks does not merge into the whole
    design); the first `cap` clusters in reading order."""
    boxes = [list(b) for b in boxes]
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                u = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                if (a[0] - gap_mm <= b[2] and b[0] - gap_mm <= a[2] and a[1] - gap_mm <= b[3] and b[1] - gap_mm <= a[3]
                        and max(u[2] - u[0], u[3] - u[1]) <= max_side_mm):
                    boxes[i] = u
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    boxes.sort(key=lambda b: (b[1], b[0]))
    return boxes[:cap]


def _sheet(name: str, arms: dict[str, dict], designs: dict[str, dict], box: list[float], ppm: float,
           label: str, renders: Path, stem: str, src) -> Path:
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    off = arms["off"]
    to_px, _to_mm, _s = _px_maps(off["art_box_frac"], off["design_size_mm"], off["image_wh"])
    long_side = max(box[2] - box[0], box[3] - box[1], 1.0)
    ppm = min(ppm, (900.0 if label == "design" else 1800.0) / long_side)
    margin = 0.6 if ppm >= 60 else 1.0
    panes = []
    for arm in ARMS:
        c = arms.get(arm)
        if not c:
            continue
        img, tp = ft._render(designs[arm], ppm)
        crop = ft._crop(img, tp, box, margin_mm=margin)
        if not panes:
            art = _artwork_crop(src, to_px, box, (crop.shape[1], crop.shape[0]), margin)
            panes.append(ft._label(art, "artwork"))
        cap = f"{ARM_LABEL[arm]} | {c['stitches']:,} st, {c['trims']} tr, {c['md5'][:8]}"
        if arm != "off":
            cap += (" (= OFF)" if c["md5"] == off["md5"]
                    else f" | {sum(material(r) for r in changed(off, c))} shape(s) changed")
        panes.append(ft._label(crop, cap))
    wide = (box[2] - box[0]) > (box[3] - box[1])
    if wide:
        w = max(p.shape[1] for p in panes)
        sheet = np.vstack([np.pad(p, ((0, 6), (0, w - p.shape[1]), (0, 0)), constant_values=255) for p in panes])
    else:
        sheet = ft._hstack(panes)
    title = f"{name} | {label} at {ppm:g} px/mm; thread at its laid width, a picture of the file, not of cloth"
    sheet = ft._label(sheet, title, width=sheet.shape[1])
    renders.mkdir(parents=True, exist_ok=True)
    path = renders / f"{stem}.png"
    cv2.imwrite(str(path), sheet)
    return path


def render(out: Path, renders: Path, only=None) -> list[Path]:
    cells = load_cells(out)
    written = []
    for name in cases():
        if only and not any(o in name for o in only):
            continue
        arms = cells.get(name)
        if not arms or "off" not in arms:
            continue
        designs = {a: json.loads((out / f"{name}__{a}_design.json").read_text()) for a in arms}
        src = _source_bgr(arms["off"]["source"])
        for label, box in _focus_boxes(name, arms["off"]):
            ppm = TIGHT_PPM if label in ("i", "ij") else FOCUS_PPM
            written.append(_sheet(name, arms, designs, box, ppm, label, renders, f"{name}_{label}", src))
        # Tight crops for the small shapes a flag admitted, retired or re-sewn;
        # a big host whose outline moved by a hole's worth (Fremont's 657 mm2
        # white patch, -0.6 mm2 at 50 mm) is read from the table, not cropped.
        boxes = [r["bounds_mm"] for a in arms if a != "off"
                 for r in changed(arms["off"], arms[a]) if material(r) and r["area_mm2"] <= TIGHT_MAX_MM2]
        for k, box in enumerate(_clusters(boxes), 1):
            written.append(_sheet(name, arms, designs, box, TIGHT_PPM, f"changed shapes {k}", renders,
                                  f"{name}_changed_{k}", src))
    for p in written:
        print("wrote", p)
    return written


def bisect(out: Path, renders: Path, name: str, shape_id: str, margin_mm: float = 1.6) -> Path:
    """The crop round `shape_id` (its OFF bounds) from every arm, the stitch
    stream cut at each colour change: which block lays it, and which covers it."""
    import cv2
    from tools import fremont_triage as ft
    cells = load_cells(out)[name]
    r = cells["off"]["regions"][shape_id]
    x0, y0, x1, y1 = r["bounds_mm"]
    box = [x0 - margin_mm, y0 - margin_mm, x1 + margin_mm, y1 + margin_mm]
    panes = []
    for arm in ARMS:
        if arm not in cells:
            continue
        d = json.loads((out / f"{name}__{arm}_design.json").read_text())
        st = d["stitches"]
        cuts = [(f"to block {k}", i) for k, i in enumerate([i for i, s in enumerate(st) if s["type"] == "color"], 1)]
        for label, n in cuts + [("full", len(st))]:
            img, tp = ft._render(dict(d, stitches=st[:n]), TIGHT_PPM)
            panes.append(ft._label(ft._crop(img, tp, box, margin_mm=0.0), f"{ARM_LABEL[arm]} | {label} ({n:,} records)"))
    sheet = ft._label(ft._hstack(panes), f"{name} | {shape_id} at {TIGHT_PPM:g} px/mm, each arm's stream cut at every colour "
                                        "change; thread at its laid width, a picture of the file, not of cloth")
    renders.mkdir(parents=True, exist_ok=True)
    path = renders / f"{name}_{shape_id}_bisect.png"
    cv2.imwrite(str(path), sheet)
    print("wrote", path)
    return path


# --- driver ----------------------------------------------------------------------------

def _prep(out: Path):
    """The small-print reference trace, once, before the cells fan out."""
    from tools import small_lettering_compare as slc
    for name, spec in cases().items():
        if spec["kind"] == "small_print":
            ref = out / f"sp_ref_{spec['fixture']}.json"
            if not ref.exists():
                print(f"tracing the {spec['fixture']} reference line", flush=True)
                slc._digitize_small_print(spec, {}, out)      # writes sp_ref_*.json
            break


def run_all(out: Path, jobs: int, only=None, arms=None):
    out.mkdir(parents=True, exist_ok=True)
    _prep(out)
    todo = [(n, a) for n in cases() if not only or any(o in n for o in only)
            for a in ARMS if not arms or a in arms]
    todo = [(n, a) for n, a in todo if not (out / f"{n}__{a}.json").exists()]
    running: list[tuple[tuple[str, str], subprocess.Popen]] = []
    log = out / "cells.log"
    while todo or running:
        while todo and len(running) < jobs:
            n, a = todo.pop(0)
            p = subprocess.Popen([sys.executable, "-m", "tools.small_stem_dot_renders", "cell", n, a, "--out", str(out)],
                                 cwd=str(ROOT), stdout=log.open("a"), stderr=subprocess.STDOUT)
            running.append(((n, a), p))
        for item in list(running):
            if item[1].poll() is not None:
                running.remove(item)
                print(f"{item[0][0]}__{item[0][1]}: exit {item[1].returncode}", flush=True)
        time.sleep(2.0)


def main(argv: list[str]) -> int:
    from tools._console import utf8_console
    utf8_console()
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2

    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default
    out = Path(opt("--out", "out_small_stem_dot"))
    only = opt("--only")
    only = only.split(",") if only else None
    cmd = argv[0]
    if cmd == "cell":
        run_cell(argv[1], argv[2], out)
    elif cmd == "all":
        arms = opt("--arms")
        run_all(out, int(opt("--jobs", "4")), only, arms.split(",") if arms else None)
    elif cmd == "render":
        render(out, Path(opt("--renders", str(out / "renders"))), only)
    elif cmd == "tables":
        print(tables(out))
    elif cmd == "bisect":
        bisect(out, Path(opt("--renders", str(out / "renders"))), argv[1], argv[2])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
