#!/usr/bin/env python
"""dark_ink_flip_sheet: `keep_dark_thin_strokes` OFF | ON on the repo's own fixtures.

WHAT IT IS FOR. PR #1160 built `cfg.keep_dark_thin_strokes` OFF and flagged
`testdata/photo/summit_badge.png` as the fixture to look at before any flip
(ON: 13 -> 11 colours). Kent judges stitch LAYOUT from renders (2026-10-22),
so this writes the side-by-side he flips from: OFF and ON at the Studio's
request (`tools.fremont_triage.studio_request(80.0)`, left_chest), the crop
where the needle points differ, the colour table of both arms and, for every
fixture, the DST md5 OFF and ON -- the whole blast radius, not one badge.

    .venv/bin/python -m tools.dark_ink_flip_sheet run [--fixtures F ...] [--cache DIR] [--jobs 3]
    .venv/bin/python -m tools.dark_ink_flip_sheet report [--cache DIR] [--out DIR]
                                                   [--before DIR --before-label TEXT] [--date D]

`--before` is a second cache from an earlier engine (a clean `git archive`
extract run with the same `run`), shown as a third arm "ON before" beside OFF
and ON, with its OFF md5 checked against this engine's -- the shape of the
2026-10-28 fixes sheet (`docs/renders/keep-dark-thin-strokes-fixes-2026-10-28`),
where OFF must be byte-identical across engines and ON before | after is the
comparison.

`tools.flip_sheet_renders` is the OFF | ON | pro sheet and needs a pro file
per job (`fixture_files`). These fixtures have none, so this tool reuses its
pieces -- `pro_pair.digitize`, the needle-point multiset diff, `best_window`,
`render_crop`, `where_image` -- and prints "no pro file" where that sheet
would draw the pro's panel, rather than inventing one.

`report` writes JPEG tiles (ours: our own fixtures may go under docs/) and ONE
self-contained `sheet.html` whose images are base64 data URIs, the shape the
desktop file pane can show (`flip-sheet-inline-2026-10-24`). Nothing here
changes an engine default; the flip was Kent's (2026-10-28, PR #1170: "Flip ON
now (worker's pick)"), and since it both arms set the flag explicitly: OFF is
the engine before the flip, ON the shipped default.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

FLAG = "keep_dark_thin_strokes"
WIDTH_MM = 80.0
GARMENT = "left_chest"
DATE = "2026-10-28"
# Both arms set the flag explicitly (since the 2026-10-28 flip ON): OFF is the
# engine before the flip, ON the shipped default, on whichever engine runs this.
ARMS = {"off": {FLAG: False}, "on": {FLAG: True}}
TESTDATA = DIGITIZER / "testdata"
DEFAULT_CACHE = DIGITIZER / "debug_out" / "dark_ink_flip_sheet"
DEFAULT_OUT = DIGITIZER.parent / "docs" / "renders" / f"keep-dark-thin-strokes-{DATE}"
HERO = "photo/summit_badge.png"
WHOLE_PPM = 6.0             # whole-design tiles: 80 mm -> 480 px
CHANGE_PPM = 20.0           # the changed area, all of it
TILE_JPEG_Q = 82
MAX_TILE_KB = 400           # the brief: keep each image under ~400 KB

#: Every image fixture in the repo (`testdata/photo/*`, `testdata/art/*`), relative
#: to testdata. The flag acts on the gradient class only (`pipeline.run_stages`:
#: `cfg.keep_dark_thin_strokes and classification.class_ == "gradient"`), so a
#: flat or photo fixture is byte-identical by construction; two ride along as
#: controls. `logo_mfab_hat.png` is photo_scene and needs the rembg venv: left out.
FIXTURES = [
    "photo/summit_badge.png",
    "photo/drone_render.png", "photo/logo_bridge_bar.jpg", "photo/logo_gaulke_roofing.png",
    "photo/logo_golden_tee.jpg", "photo/logo_hotel_fremont.webp", "photo/region_blobs.png",
    "photo/gradient_ramp_linear.png", "photo/gradient_ramp_radial.png",
    "photo/logo_drone_thermal_badge.png", "photo/owl_kent.jpg",
    "photo/repro_gradient_white_icon.png", "photo/screenshot_phone_ui_golke.jpg",
    "art/logo_golke_roofing.png", "art/logo_hotel_fremont_patch.png", "art/logo_mfab_lc.png",
    "art/logo_toat_beanie.png", "art/logo_toat_machine.png",
    # controls (not gradient)
    "photo/enthusiast_logo.png", "photo/photo_scene_stub.png",
]


def slug(fixture: str) -> str:
    return fixture.replace("/", "__").rsplit(".", 1)[0]


# --------------------------------------------------------------------- run
def digitize_cell(fixture: str, arm: str, cache: Path) -> dict:
    """One (fixture, arm): ours.dst, design.json, runs.json, regions.json, stats.json."""
    from tools import pro_pair as pp
    from digitizer_core.export import write_dst
    from digitizer_core.stage0_classify import classify
    out = cache / slug(fixture) / arm
    if (out / "stats.json").exists():
        return json.loads((out / "stats.json").read_text(encoding="utf-8"))
    art = TESTDATA / fixture
    cpu0 = time.process_time()
    d = pp.digitize(art, WIDTH_MM, GARMENT, dict(ARMS[arm]))
    cpu = time.process_time() - cpu0
    out.mkdir(parents=True, exist_ok=True)
    write_dst(d.plan, out / "ours.dst")
    (out / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
    runs = []
    for blk, run in d.plan.iter_runs():
        pts = run.points or []
        runs.append({"shape": str(run.shape_id), "kind": str(run.kind),
                     "role": str(getattr(run, "role", "") or ""), "n": len(pts),
                     "thread": blk.thread_number, "rgb": list(blk.rgb),
                     "trim": bool(getattr(run, "trim", False))})
    (out / "runs.json").write_text(json.dumps(runs), encoding="utf-8")
    names = {str(c.get("number")): str(c.get("name", "")) for c in d.result.palette}
    regions = [{"shape": r.shape_id, "thread": r.thread_number,
                "name": names.get(r.thread_number, ""), "area_mm2": round(r.area_mm2, 2),
                "bounds": [round(v, 2) for v in r.polygon.bounds], "wkt": r.polygon.wkt,
                "dark_ink": bool(r.meta.get("dark_ink")),
                "layer": r.meta.get("layer"), "source": r.source}
               for r in d.result.regions]
    (out / "regions.json").write_text(json.dumps(regions), encoding="utf-8")
    cls = classify(art, d.cfg)
    stats = {"fixture": fixture, "arm": arm, "sets": ARMS[arm], "class": cls.class_,
             "width_mm": WIDTH_MM, "garment": GARMENT, "secs": round(d.secs, 1),
             "cpu_s": round(cpu, 1), "regions": len(d.result.regions),
             "dark_ink_regions": sum(1 for r in regions if r["dark_ink"]),
             "plan_stitches": d.plan.stats.stitch_count, "plan_trims": d.plan.stats.trims,
             "blocks": len(d.plan.blocks), "threads": len({b.thread_number for b in d.plan.blocks}),
             "art_box_frac": list(d.result.art_box_frac) if d.result.art_box_frac else None,
             "design_size_mm": [round(v, 2) for v in d.result.design_size_mm],
             "md5": hashlib.md5((out / "ours.dst").read_bytes()).hexdigest()}
    (out / "stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


def _job(args):
    fixture, arm, cache = args
    try:
        s = digitize_cell(fixture, arm, Path(cache))
        return f"{fixture}/{arm}: {s['plan_stitches']} st, {s['plan_trims']} tr, {s['blocks']} col, {s['secs']} s"
    except Exception as e:  # noqa: BLE001 -- one cell failing must not sink the pass
        return f"{fixture}/{arm}: FAILED {type(e).__name__}: {e}"


def run_cmd(a) -> int:
    jobs = [(f, arm, str(a.cache)) for f in (a.fixtures or FIXTURES) for arm in ARMS]
    if a.jobs <= 1:
        for j in jobs:
            print(_job(j), flush=True)
    else:
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            for line in ex.map(_job, jobs):
                print(line, flush=True)
    return 0


# ------------------------------------------------------------------ report
def load_cell(path: Path) -> dict:
    from tools import flip_sheet_renders as fsr
    cell = {name: json.loads((path / f"{name}.json").read_text(encoding="utf-8"))
            for name in ("stats", "design", "runs", "regions")}
    cell["dst"] = path / "ours.dst"
    cell["stream"] = fsr.read_stream(cell["dst"])
    cell["counts"] = fsr.counts(cell["stream"])
    return cell


def block_table(cell: dict) -> list[dict]:
    """One row per colour block of the DESIGN (the Studio's previewer input):
    thread label, rgb, stitches sewn in it, regions on that thread."""
    design = cell["design"]
    colors = design.get("colors") or []
    per = [0] * len(colors)
    ci = 0
    for s in design.get("stitches") or []:
        t = s.get("type")
        if t == "color":
            ci += 1
        elif t == "stitch" and ci < len(per):
            per[ci] += 1
    by_thread: dict[str, int] = {}
    for r in cell["regions"]:
        by_thread[r["thread"]] = by_thread.get(r["thread"], 0) + 1
    rows = []
    for i, c in enumerate(colors):
        label = str(c.get("name", "")).strip()
        number = label.split(" ", 1)[0] if label else ""
        rows.append({"label": label or "(unnamed)", "rgb": [c.get("r", 0), c.get("g", 0), c.get("b", 0)],
                     "stitches": per[i], "regions": by_thread.get(number, 0)})
    return rows


def _polys(cell: dict):
    from shapely import wkt
    return [(r, wkt.loads(r["wkt"])) for r in cell["regions"]]


def moved_strokes(off: dict, on: dict) -> dict:
    """What ON changed, region by region. `dark`: each ON `dark_ink` region
    with the OFF regions (thread) it was cut from. `dropped`: each OFF thread
    missing from ON, with where its area went in ON (thread -> mm2)."""
    import shapely
    off_p, on_p = _polys(off), _polys(on)
    dark = []
    for r, p in on_p:
        if not r["dark_ink"]:
            continue
        hosts = {}
        for ro, po in off_p:
            a = p.intersection(po).area if p.intersects(po) else 0.0
            if a > 0.01:
                key = f"{ro['thread']} {ro['name']}".strip()
                hosts[key] = round(hosts.get(key, 0.0) + a, 2)
        dark.append({"shape": r["shape"], "thread": f"{r['thread']} {r['name']}".strip(),
                     "area_mm2": r["area_mm2"], "bounds": r["bounds"],
                     "from": dict(sorted(hosts.items(), key=lambda kv: -kv[1]))})
    off_threads = {r["thread"]: r["name"] for r in off["regions"]}
    on_threads = {r["thread"]: r["name"] for r in on["regions"]}
    dropped = []
    for t, name in off_threads.items():
        if t in on_threads:
            continue
        regs = [(ro, po) for ro, po in off_p if ro["thread"] == t]
        went: dict[str, float] = {}
        for _ro, po in regs:
            for rn, pn in on_p:
                a = po.intersection(pn).area if po.intersects(pn) else 0.0
                if a > 0.01:
                    key = f"{rn['thread']} {rn['name']}".strip()
                    went[key] = went.get(key, 0.0) + a
        area = sum(ro["area_mm2"] for ro, _ in regs)
        dropped.append({"thread": f"{t} {name}".strip(), "regions": len(regs),
                        "area_mm2": round(area, 2),
                        "bounds": [round(v, 2) for v in shapely.union_all([po for _, po in regs]).bounds],
                        "went_to": {k: round(v, 2) for k, v in sorted(went.items(), key=lambda kv: -kv[1])}})
    added = sorted(f"{t} {n}".strip() for t, n in on_threads.items() if t not in off_threads)
    return {"dark": dark, "dropped": dropped, "added": added,
            "blocks_gone": blocks_gone(off, on), "shapes_moved": shapes_moved(off, on)}


def blocks_gone(off: dict, on: dict) -> dict:
    """Colour BLOCKS (the DST's colour changes) by thread label: stitches per label
    OFF and ON, for labels whose block count or stitches differ."""
    def per(cell):
        out: dict[str, list[int]] = {}
        for r in block_table(cell):
            out.setdefault(r["label"], []).append(r["stitches"])
        return out
    a, b = per(off), per(on)
    return {k: {"off_blocks": len(a.get(k, [])), "off_stitches": sum(a.get(k, [])),
                "on_blocks": len(b.get(k, [])), "on_stitches": sum(b.get(k, []))}
            for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


def shapes_moved(off: dict, on: dict) -> list[dict]:
    """Shapes whose thread-by-thread stitch split differs OFF -> ON (a blend
    band that changed its thread, a stroke carved out): plan points per thread."""
    def per(cell):
        out: dict[str, dict[str, int]] = {}
        for r in cell["runs"]:
            if r["kind"] not in ("fill", "satin", "run", "bean", "travel"):
                continue
            sid = r["shape"].split("-blend")[0]
            d = out.setdefault(sid, {})
            d[r["thread"]] = d.get(r["thread"], 0) + r["n"]
        return out
    a, b = per(off), per(on)
    names = {}
    for c in (off, on):
        for row in block_table(c):
            num, _, name = row["label"].partition(" ")
            names[num] = name
    rows = []
    for sid in sorted(set(a) | set(b), key=lambda k: -(sum(a.get(k, {}).values()) + sum(b.get(k, {}).values()))):
        if a.get(sid) == b.get(sid):
            continue
        lab = lambda d: {f"{t} {names.get(t, '')}".strip(): n for t, n in sorted(d.items())}
        rows.append({"shape": sid, "off": lab(a.get(sid, {})), "on": lab(b.get(sid, {}))})
    return rows


def _jpeg_bytes(img, q: int = TILE_JPEG_Q) -> bytes:
    import cv2
    for qq in (q, 70, 60, 50):
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, qq])
        if ok and len(buf) <= MAX_TILE_KB * 1024:
            return bytes(buf)
    return bytes(buf)


def _art_tile(fixture: str, height_px: int):
    import cv2
    img = cv2.imread(str(TESTDATA / fixture), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 3 and img.shape[2] == 4:
        a = img[:, :, 3:4] / 255.0
        img = (img[:, :, :3] * a + 255 * (1 - a)).astype("uint8")
    elif img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    s = height_px / img.shape[0]
    return cv2.resize(img, (max(1, int(img.shape[1] * s)), height_px), interpolation=cv2.INTER_AREA)


def _crop_bbox(design: dict, pts, pad_mm: float, ppm: float):
    from tools import flip_sheet_renders as fsr
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    box = (min(xs) - pad_mm, min(ys) - pad_mm, max(xs) + pad_mm, max(ys) + pad_mm)
    return fsr.render_crop(design, box, ppm), box


def hero_tiles(fixture: str, off: dict, on: dict, out: Path, before: dict | None = None) -> dict:
    """The tiles for the fixture the sheet is about: art, OFF and ON whole, the
    changed area (all of it) OFF and ON, the 18 x 11 mm window where most points
    moved (40 px/mm) OFF and ON, and where that window sits. With `before` (the
    earlier engine's ON cell) a third whole and window tile; when ON is OFF byte
    for byte the window is where OFF and `before` differ instead, so the sheet
    shows what the fixes took back."""
    import cv2
    from digitizer_core import stitchviz
    from tools import flip_sheet_renders as fsr
    s = slug(fixture)
    tiles: dict[str, Path] = {}

    def put(name, img):
        p = out / f"{s}__{name}.jpg"
        p.write_bytes(_jpeg_bytes(img))
        tiles[name] = p
        return p
    whole_off = stitchviz.render_design(off["design"], px_per_mm=WHOLE_PPM)
    whole_on = stitchviz.render_design(on["design"], px_per_mm=WHOLE_PPM)
    put("whole_off", fsr._label(whole_off, "OFF (pre-flip)"))
    if before is not None:
        put("whole_before", fsr._label(stitchviz.render_design(before["design"], px_per_mm=WHOLE_PPM), "ON before the fixes"))
    put("whole_on", fsr._label(whole_on, f"ON ({FLAG})" + (", after the fixes" if before is not None else "")))
    art = _art_tile(fixture, whole_off.shape[0])
    if art is not None:
        put("art", fsr._label(art, "artwork"))
    diff = fsr.diff_points(fsr.needle_points(off["stream"]), fsr.needle_points(on["stream"]))
    info = {"diff_points": len(diff)}
    if before is not None:
        bdiff = fsr.diff_points(fsr.needle_points(off["stream"]), fsr.needle_points(before["stream"]))
        info["diff_points_before"] = len(bdiff)
        if not diff:
            diff = bdiff
    if diff:
        win = fsr.best_window(diff)
        info["window_mm"] = [round(v, 1) for v in win]
        put("where", fsr.where_image(off["design"], win, ppm=8.0))
        put("win_off", fsr._label(fsr.render_crop(off["design"], win), "OFF 18 x 11 mm, 40 px/mm"))
        if before is not None:
            put("win_before", fsr._label(fsr.render_crop(before["design"], win), "ON before the fixes"))
        put("win_on", fsr._label(fsr.render_crop(on["design"], win), "ON 18 x 11 mm, 40 px/mm" + (", after" if before is not None else "")))
        ch_off, box = _crop_bbox(off["design"], diff, 2.0, CHANGE_PPM)
        ch_on, _ = _crop_bbox(on["design"], diff, 2.0, CHANGE_PPM)
        info["changed_box_mm"] = [round(v, 1) for v in box]
        put("changed_off", fsr._label(ch_off, "OFF: every changed point, 20 px/mm"))
        if before is not None:
            put("changed_before", fsr._label(_crop_bbox(before["design"], diff, 2.0, CHANGE_PPM)[0], "ON before the fixes"))
        put("changed_on", fsr._label(ch_on, "ON: every changed point, 20 px/mm"))
    # The dark-ink regions ON; when ON carved none, the earlier engine's, so a
    # refused component is still shown against the artwork.
    dark_cell, dark_label = on, "ON"
    dark = [r for r in on["regions"] if r["dark_ink"]]
    if not dark and before is not None:
        dark_cell, dark_label = before, "ON before the fixes"
        dark = [r for r in before["regions"] if r["dark_ink"]]
    info["dark_tiles"] = []
    info["dark_tiles_arm"] = dark_label
    for i, r in enumerate(dark):
        x0, y0, x1, y1 = r["bounds"]
        pad = 3.0
        box = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        names = [put(f"dark{i}_off", fsr._label(fsr.render_crop(off["design"], box), f"OFF at {r['shape']}, 40 px/mm")),
                 put(f"dark{i}_on", fsr._label(fsr.render_crop(dark_cell["design"], box), f"{dark_label}: dark-ink region {r['shape']}"))]
        art_crop = _art_crop(fixture, dark_cell["stats"], box, fsr.PPM)
        if art_crop is not None:
            names.append(put(f"dark{i}_art", fsr._label(art_crop, "artwork, same window")))
        info["dark_tiles"].append([p.name for p in names])
    return {"tiles": tiles, **info}


def _art_crop(fixture: str, stats: dict, box_mm, ppm: float):
    """The artwork under a plan-mm window, resampled to `ppm`: design mm are
    centred on the art box (`PipelineResult.art_box_frac`, the whole image when
    a cell predates the field) and span `design_size_mm`."""
    import cv2
    raw = cv2.imread(str(TESTDATA / fixture), cv2.IMREAD_UNCHANGED)
    if raw is None:
        return None
    if raw.ndim == 3 and raw.shape[2] == 4:
        a = raw[:, :, 3:4] / 255.0
        raw = (raw[:, :, :3] * a + 255 * (1 - a)).astype("uint8")
    elif raw.ndim == 2:
        raw = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
    H, W = raw.shape[:2]
    fx0, fy0, fx1, fy1 = stats.get("art_box_frac") or (0.0, 0.0, 1.0, 1.0)
    dw, dh = stats.get("design_size_mm") or (WIDTH_MM, WIDTH_MM * (fy1 - fy0) * H / ((fx1 - fx0) * W))
    sx, sy = (fx1 - fx0) * W / dw, (fy1 - fy0) * H / dh      # px per mm on the art
    cx, cy = (fx0 + fx1) / 2 * W, (fy0 + fy1) / 2 * H
    x0, y0, x1, y1 = box_mm
    px = (int(round(cx + x0 * sx)), int(round(cy + y0 * sy)), int(round(cx + x1 * sx)), int(round(cy + y1 * sy)))
    crop = raw[max(0, px[1]):max(1, min(H, px[3])), max(0, px[0]):max(1, min(W, px[2]))]
    if crop.size == 0:
        return None
    return cv2.resize(crop, (max(1, int(round((x1 - x0) * ppm))), max(1, int(round((y1 - y0) * ppm)))),
                      interpolation=cv2.INTER_CUBIC)


def window_tiles(fixture: str, off: dict, on: dict, out: Path, before: dict | None = None) -> dict:
    """where | OFF | [ON before] | ON on the best window alone, for a fixture that
    is not the hero. The window is where OFF and ON differ, or where OFF and
    `before` differ when ON is OFF byte for byte."""
    from tools import flip_sheet_renders as fsr
    s = slug(fixture)
    tiles: dict[str, Path] = {}
    diff = fsr.diff_points(fsr.needle_points(off["stream"]), fsr.needle_points(on["stream"]))
    info = {"diff_points": len(diff), "tiles": tiles}
    if before is not None:
        bdiff = fsr.diff_points(fsr.needle_points(off["stream"]), fsr.needle_points(before["stream"]))
        info["diff_points_before"] = len(bdiff)
        if not diff:
            diff = bdiff
    if not diff:
        return info
    win = fsr.best_window(diff)
    info["window_mm"] = [round(v, 1) for v in win]
    panels = [("where", fsr.where_image(off["design"], win, ppm=8.0)),
              ("win_off", fsr._label(fsr.render_crop(off["design"], win), "OFF 18 x 11 mm, 40 px/mm"))]
    if before is not None:
        panels.append(("win_before", fsr._label(fsr.render_crop(before["design"], win), "ON before the fixes")))
    panels.append(("win_on", fsr._label(fsr.render_crop(on["design"], win), "ON 18 x 11 mm, 40 px/mm" + (", after" if before is not None else ""))))
    for name, img in panels:
        p = out / f"{s}__{name}.jpg"
        p.write_bytes(_jpeg_bytes(img))
        tiles[name] = p
    return info


def _data_uri(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _swatch(rgb) -> str:
    return (f'<span style="display:inline-block;width:14px;height:14px;border:1px solid #888;'
            f'vertical-align:middle;background:rgb({rgb[0]},{rgb[1]},{rgb[2]})"></span>')


def _blocks_html(rows: list[dict]) -> str:
    out = ["<table><tr><th></th><th>thread</th><th>stitches</th><th>regions</th></tr>"]
    for r in rows:
        out.append(f"<tr><td>{_swatch(r['rgb'])}</td><td>{r['label']}</td>"
                   f"<td>{r['stitches']:,}</td><td>{r['regions']}</td></tr>")
    out.append("</table>")
    return "".join(out)


def summary_row(fixture: str, off: dict, on: dict) -> dict:
    so, sn = off["stats"], on["stats"]
    co, cn = off["counts"], on["counts"]
    return {"fixture": fixture, "class": so["class"], "md5_off": so["md5"], "md5_on": sn["md5"],
            "identical": so["md5"] == sn["md5"],
            "off": {"regions": so["regions"], "stitches": co["stitches"], "trims": co["trims"],
                    "colours": so["blocks"], "threads": _threads(off)},
            "on": {"regions": sn["regions"], "stitches": cn["stitches"], "trims": cn["trims"],
                   "colours": sn["blocks"], "threads": _threads(on),
                   "dark_ink_regions": sn["dark_ink_regions"]}}


def _threads(cell: dict) -> int:
    return len({r["label"] for r in block_table(cell)})


def _arm_cells(cache: Path, f: str) -> tuple[dict, dict] | None:
    d = cache / slug(f)
    if not all((d / arm / "stats.json").exists() for arm in ARMS):
        return None
    return load_cell(d / "off"), load_cell(d / "on")


def _counts(c: dict) -> str:
    return f"{c['regions']} / {c['stitches']:,} / {c['trims']} / {c['colours']} / {c['threads']}"


def report_cmd(a) -> int:
    cache, out = Path(a.cache), Path(a.out)
    before = Path(a.before) if a.before else None
    out.mkdir(parents=True, exist_ok=True)
    rows, missing = [], []
    cells: dict[str, tuple[dict, dict]] = {}
    bcells: dict[str, tuple[dict, dict]] = {}
    for f in (a.fixtures or FIXTURES):
        got = _arm_cells(cache, f)
        if got is None:
            missing.append(f)
            continue
        off, on = got
        cells[f] = (off, on)
        row = summary_row(f, off, on)
        if before is not None:
            bgot = _arm_cells(before, f)
            if bgot is not None:
                bcells[f] = bgot
                boff, bon = bgot
                row["before"] = summary_row(f, boff, bon)["on"]
                row["md5_off_before"] = boff["stats"]["md5"]
                row["md5_on_before"] = bon["stats"]["md5"]
                row["off_identical_across_engines"] = boff["stats"]["md5"] == off["stats"]["md5"]
        rows.append(row)
    hero = a.hero if a.hero in cells else None
    sheet = {"date": a.date, "flag": FLAG, "width_mm": WIDTH_MM, "garment": GARMENT,
             "engine": _engine_sha(), "before": a.before_label if before is not None else None,
             "rows": rows, "missing": missing, "hero": hero}
    three = before is not None
    html = [f"<!doctype html><meta charset='utf-8'><title>{FLAG} OFF | ON</title>",
            "<style>body{font:14px system-ui,sans-serif;margin:16px;max-width:1500px}"
            "table{border-collapse:collapse;margin:8px 0}td,th{border:1px solid #ccc;padding:3px 8px;"
            "text-align:left;vertical-align:top}img{max-width:100%;height:auto;border:1px solid #ddd}"
            ".row{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start}"
            ".row>div{flex:1 1 300px}.id{color:#2a7}.mv{color:#b22}code{font-size:12px}</style>",
            f"<h1><code>{FLAG}</code> OFF | {'ON before | ON after' if three else 'ON'} -- {a.date}</h1>",
            f"<p>Studio request at {WIDTH_MM:g} mm, <code>{GARMENT}</code>, shipped defaults; "
            f"engine <code>{sheet['engine']}</code>. OFF is the engine before the 2026-10-28 flip (the flag "
            f"False); ON is the shipped default since it. "
            + (f"<b>ON before</b> is {a.before_label}; <b>ON after</b> is this engine. OFF is checked byte for "
               "byte across the two engines in the table at the end. " if three else "")
            + "<b>No pro file exists for any fixture here, so there is no pro column</b>: the flip is read "
            "OFF against ON on our own fixtures. Counts are the DST's own records (pystitch): stitches, "
            "TRIM records, colour blocks; regions from the plan.</p>"]
    if hero:
        off, on = cells[hero]
        bon = bcells[hero][1] if hero in bcells else None
        ht = hero_tiles(hero, off, on, out, before=bon)
        sheet["hero_tiles"] = {k: v.name for k, v in ht["tiles"].items()}
        moved = moved_strokes(off, on)
        sheet["moved"] = moved
        if bon is not None:
            sheet["moved_before"] = moved_strokes(off, bon)
        sheet["diff_points"] = ht["diff_points"]
        sheet["diff_points_before"] = ht.get("diff_points_before")
        sheet["window_mm"] = ht.get("window_mm")
        sheet["changed_box_mm"] = ht.get("changed_box_mm")
        r = summary_row(hero, off, on)
        rb = summary_row(hero, bcells[hero][0], bon)["on"] if bon is not None else None
        html.append(f"<h2>{hero}</h2>")
        html.append("<table><tr><th></th><th>OFF</th>" + ("<th>ON before</th><th>ON after</th>" if three else "<th>ON</th>") + "</tr>")
        for k in ("regions", "stitches", "trims", "colours", "threads"):
            label = k if k != 'colours' else 'colour blocks (DST colour changes + 1)'
            cells_html = ""
            if rb is not None:
                cells_html += f"<td class='{'id' if r['off'][k] == rb[k] else 'mv'}'>{rb[k]:,}</td>"
            cells_html += f"<td class='{'id' if r['off'][k] == r['on'][k] else 'mv'}'>{r['on'][k]:,}</td>"
            html.append(f"<tr><td>{label}</td><td>{r['off'][k]:,}</td>{cells_html}</tr>")
        html.append(f"<tr><td>DST md5</td><td><code>{r['md5_off']}</code></td>"
                    + (f"<td><code>{bon['stats']['md5']}</code></td>" if bon is not None else "")
                    + f"<td><code>{r['md5_on']}</code></td></tr>")
        html.append(f"<tr><td>dark-ink regions</td><td>-</td>"
                    + (f"<td>{rb['dark_ink_regions']}</td>" if rb is not None else "")
                    + f"<td>{r['on']['dark_ink_regions']}</td></tr>")
        html.append(f"<tr><td>needle points that differ from OFF (0.05 mm grid, multiset)</td><td>-</td>"
                    + (f"<td>{ht['diff_points_before']:,}</td>" if bon is not None else "")
                    + f"<td>{ht['diff_points']:,}</td></tr></table>")
        html.append("<div class='row'>" + "".join(
            f"<div><img src='{_data_uri(ht['tiles'][k])}'></div>" for k in ("art", "whole_off", "whole_before", "whole_on")
            if k in ht["tiles"]) + "</div>")
        if "where" in ht["tiles"]:
            which = ("OFF and ON after" if ht["diff_points"] else "OFF and ON before (ON after is OFF byte for byte)")
            html.append(f"<h3>Where the needle points changed</h3><p>Window {ht['window_mm']} mm (x0, y0, x1, y1, plan mm, y down) "
                        f"holds the most points that differ between {which}; the changed area as a whole is {ht['changed_box_mm']} mm.</p>")
            html.append("<div class='row'>" + "".join(
                f"<div><img src='{_data_uri(ht['tiles'][k])}'></div>" for k in ("changed_off", "changed_before", "changed_on")
                if k in ht["tiles"]) + "</div>")
            html.append("<div class='row'>" + "".join(
                f"<div><img src='{_data_uri(ht['tiles'][k])}'></div>" for k in ("where", "win_off", "win_before", "win_on")
                if k in ht["tiles"]) + "</div>")
            html.append("<p>pro: <b>no pro file for this fixture</b> (nothing to draw in a third panel).</p>")
        for names in ht.get("dark_tiles", []):
            html.append(f"<h3>The dark-ink region {ht['dark_tiles_arm']}, against the artwork</h3><div class='row'>" + "".join(
                f"<div><img src='{_data_uri(out / n)}'></div>" for n in names) + "</div>")
        html.append("<h3>Colour blocks</h3><div class='row'>")
        html.append("<div><b>OFF</b>" + _blocks_html(block_table(off)) + "</div>")
        if bon is not None:
            html.append("<div><b>ON before</b>" + _blocks_html(block_table(bon)) + "</div>")
        html.append(f"<div><b>ON{' after' if three else ''}</b>" + _blocks_html(block_table(on)) + "</div></div>")
        for title, mv in ((("What moved, OFF -> ON before", sheet["moved_before"]),) if bon is not None else ()) + (
                (f"What moved, OFF -> ON{' after' if three else ''}", moved),):
            html.append(f"<h3>{title}</h3>")
            if not any((mv["blocks_gone"], mv["shapes_moved"], mv["dropped"], mv["added"], mv["dark"])):
                html.append("<p>Nothing: byte-identical.</p>")
            if mv["blocks_gone"]:
                html.append("<p><b>Colour blocks whose count or stitches changed</b> (thread label: blocks / stitches OFF -> ON):</p><ul>")
                for k, v in mv["blocks_gone"].items():
                    html.append(f"<li><b>{k}</b>: {v['off_blocks']} block(s) / {v['off_stitches']:,} st -> "
                                f"{v['on_blocks']} / {v['on_stitches']:,}</li>")
                html.append("</ul>")
            if mv["shapes_moved"]:
                html.append("<p><b>Shapes whose thread split changed</b> (plan points per thread, OFF -> ON):</p><ul>")
                for rr in mv["shapes_moved"][:12]:
                    html.append(f"<li><code>{rr['shape']}</code>: {rr['off']} -> {rr['on']}</li>")
                html.append("</ul>")
            if mv["dropped"]:
                html.append("<p><b>Threads OFF sews that ON does not:</b></p><ul>")
                for d in mv["dropped"]:
                    went = ", ".join(f"{k} {v} mm&sup2;" for k, v in d["went_to"].items()) or "nowhere (unsewn)"
                    html.append(f"<li><b>{d['thread']}</b>: {d['regions']} region(s), {d['area_mm2']} mm&sup2; OFF, "
                                f"bounds {d['bounds']} mm; ON that area sews as {went}</li>")
                html.append("</ul>")
            if mv["added"]:
                html.append(f"<p>Threads ON sews that OFF does not: {', '.join(mv['added'])}</p>")
            if mv["dark"]:
                html.append("<p><b>ON's dark-ink regions</b> (carved out of the merge, `meta[\"dark_ink\"]`):</p><ul>")
                for d in mv["dark"]:
                    frm = ", ".join(f"{k} {v} mm&sup2;" for k, v in d["from"].items())
                    html.append(f"<li>{d['shape']} on <b>{d['thread']}</b>, {d['area_mm2']} mm&sup2;, bounds {d['bounds']} mm; "
                                f"OFF sewed that ground as {frm}</li>")
                html.append("</ul>")
            elif mv is moved:
                html.append("<p>ON carved no dark-ink region on this fixture.</p>")
    html.append("<h2>Every other fixture that moves ON</h2>")
    html.append("<p>Same window rule as above (18 x 11 mm, 40 px/mm, where most needle points moved); "
                "the where-picture marks it on OFF. No pro file for any of them.</p>")
    sheet["moved_fixtures"] = {}
    for f, (off, on) in cells.items():
        bon = bcells[f][1] if f in bcells else None
        if f == hero:
            continue
        if off["stats"]["md5"] == on["stats"]["md5"] and (bon is None or bon["stats"]["md5"] == off["stats"]["md5"]):
            continue
        r = summary_row(f, off, on)
        mt = window_tiles(f, off, on, out, before=bon)
        mv = moved_strokes(off, on)
        entry = {"row": r, "window_mm": mt.get("window_mm"), "diff_points": mt["diff_points"],
                 "dark": mv["dark"], "blocks_gone": mv["blocks_gone"], "shapes_moved": mv["shapes_moved"][:6]}
        if bon is not None:
            mvb = moved_strokes(off, bon)
            entry["before"] = {"diff_points": mt.get("diff_points_before"), "dark": mvb["dark"],
                               "blocks_gone": mvb["blocks_gone"], "shapes_moved": mvb["shapes_moved"][:6],
                               "md5": bon["stats"]["md5"]}
        sheet["moved_fixtures"][f] = entry
        o, n = r["off"], r["on"]
        line = f"<h3>{f}</h3><p>OFF {_counts(o)}"
        if bon is not None:
            rb = summary_row(f, bcells[f][0], bon)["on"]
            line += (f" -> ON before {_counts(rb)}; dark-ink regions {rb['dark_ink_regions']}; "
                     f"{mt.get('diff_points_before', 0):,} needle points differ from OFF")
        line += (f" -> ON{' after' if three else ''} {_counts(n)}; dark-ink regions {n['dark_ink_regions']}; "
                 f"{mt['diff_points']:,} needle points differ from OFF"
                 + (" (<span class='id'>byte-identical to OFF</span>)" if r["identical"] else "")
                 + (" (<span class='id'>ON unchanged by the fixes</span>)" if bon is not None and bon["stats"]["md5"] == on["stats"]["md5"] else "")
                 + ".</p>")
        html.append(line)
        show = mv if mv["dark"] else (moved_strokes(off, bon) if bon is not None else mv)
        if show["dark"]:
            html.append(("<p>ON before the fixes carved:</p>" if show is not mv else "") + "<ul>" + "".join(
                f"<li>{d['shape']} on <b>{d['thread']}</b>, {d['area_mm2']} mm&sup2; at {d['bounds']} mm; OFF sewed it as "
                + ", ".join(f"{k} {v} mm&sup2;" for k, v in d["from"].items()) + "</li>" for d in show["dark"]) + "</ul>")
        if show["blocks_gone"]:
            html.append("<p>Colour blocks changed (blocks / stitches OFF -> ON): " + "; ".join(
                f"<b>{k}</b> {v['off_blocks']} / {v['off_stitches']:,} -> {v['on_blocks']} / {v['on_stitches']:,}"
                for k, v in show["blocks_gone"].items()) + "</p>")
        html.append("<div class='row'>" + "".join(
            f"<div><img src='{_data_uri(mt['tiles'][k])}'></div>" for k in ("where", "win_off", "win_before", "win_on")
            if k in mt["tiles"]) + "</div>")
    html.append("<h2>Every fixture: DST md5 OFF and ON</h2>")
    html.append("<table><tr><th>fixture</th><th>stage 0</th><th>OFF regions / st / tr / blocks / threads</th>"
                + ("<th>OFF md5 across engines</th><th>ON before</th><th>ON after</th><th>DST</th></tr>" if three else
                   "<th>ON regions / st / tr / blocks / threads</th><th>DST</th></tr>"))
    for r in rows:
        o, n = r["off"], r["on"]
        if three and "before" in r:
            b = r["before"]
            same_off = ("<span class='id'>identical</span>" if r["off_identical_across_engines"]
                        else f"<span class='mv'>DIFFERS</span> <code>{r['md5_off_before'][:8]}</code>")
            if r["identical"]:
                verdict = "<span class='id'>ON after = OFF</span>"
            elif r["md5_on_before"] == r["md5_on"]:
                verdict = "moves, <span class='id'>unchanged by the fixes</span>"
            else:
                verdict = f"<span class='mv'>moves</span>, changed by the fixes <code>{r['md5_on_before'][:8]}</code> -> <code>{r['md5_on'][:8]}</code>"
            html.append(f"<tr><td>{r['fixture']}</td><td>{r['class']}</td><td>{_counts(o)} <code>{r['md5_off'][:8]}</code></td>"
                        f"<td>{same_off}</td><td>{_counts(b)} <code>{r['md5_on_before'][:8]}</code></td>"
                        f"<td>{_counts(n)} <code>{r['md5_on'][:8]}</code></td><td>{verdict}</td></tr>")
        else:
            verdict = ("<span class='id'>byte-identical</span>" if r["identical"]
                       else f"<span class='mv'>moves</span> <code>{r['md5_off'][:8]}</code> -> <code>{r['md5_on'][:8]}</code>")
            html.append(f"<tr><td>{r['fixture']}</td><td>{r['class']}</td><td>{_counts(o)}</td>"
                        + (f"<td>-</td><td>-</td>" if three else "")
                        + f"<td>{_counts(n)}</td><td>{verdict}</td></tr>")
    html.append("</table>")
    if missing:
        html.append(f"<p>Not run: {', '.join(missing)}</p>")
    (out / "sheet.html").write_text("\n".join(html), encoding="utf-8")
    (out / "sheet.json").write_text(json.dumps(sheet, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in sheet.items() if k != "rows"}, indent=1))
    for r in rows:
        print(f"{r['fixture']:45s} {r['class']:12s} {'identical' if r['identical'] else 'MOVES   '} "
              f"OFF {r['off']['regions']}/{r['off']['stitches']}/{r['off']['trims']}/{r['off']['colours']}  "
              + (f"BEFORE {r['before']['regions']}/{r['before']['stitches']}/{r['before']['trims']}/{r['before']['colours']}  " if "before" in r else "")
              + f"ON {r['on']['regions']}/{r['on']['stitches']}/{r['on']['trims']}/{r['on']['colours']}")
    return 0


def _engine_sha() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=DIGITIZER,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fixtures", nargs="*")
    r.add_argument("--cache", default=DEFAULT_CACHE)
    r.add_argument("--jobs", type=int, default=3)
    p = sub.add_parser("report")
    p.add_argument("--fixtures", nargs="*")
    p.add_argument("--cache", default=DEFAULT_CACHE)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--hero", default=HERO)
    p.add_argument("--before", default=None,
                   help="a second cache from an earlier engine: its ON is shown as 'ON before', its OFF md5 checked")
    p.add_argument("--before-label", default="the engine before the fixes",
                   help="how the sheet names the --before engine (e.g. 'main 09cfbaea, PR #1160 as merged')")
    p.add_argument("--date", default=DATE)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    a = parse_args(argv)
    return run_cmd(a) if a.cmd == "run" else report_cmd(a)


if __name__ == "__main__":
    sys.exit(main())
