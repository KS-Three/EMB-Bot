"""Hair reach: does the line route reach hair on the Studio's own route? (2026-10-13)

    python -m tools.hair_reach census --image owl_kent --width 127 --grid 8
    python -m tools.hair_reach run    --image owl_kent --arm off|region|lines|lines_st
    python -m tools.hair_reach drawn                  # hair_strands, hair_fine: the A/B bar's baselines
    python -m tools.hair_reach table  [--out DIR]
    python -m tools.hair_reach render --image owl_kent [--out DIR]
    python -m tools.hair_reach size [--widths 127 180 250] [--strand-test]   # 2026-10-15
    python -m tools.hair_reach sizetable | sizerender [--width 250 --probe side]

MEASURE ONLY. No core edit; the one thing forced here is
`stage6_hairline_lines.LINE_CLASSES`, monkeypatched in THIS tool (`lines_on`)
to add `gradient`, so `cfg.hairline_from_lines` fires on the lane the Studio
actually sends a photograph down.

Why. #876's `studio` route (the Studio's `detect_photographic` +
`faces_route_flat` flags; neither signal fires on `owl_kent.jpg`) sends the
owl to stage 0's own lane, `gradient`. #882 built the line route
(`cfg.hairline_from_lines`) for the photo lanes only and said so: "the
Studio's own route on this photo ... widening `LINE_CLASSES` to gradient
needs a measured A/B on the drawn fixtures first". #882 also named the next
lever: resolution ("a bigger photo, or a bigger design"). #897 added the
strand test (`cfg.hairline_lines_strand_test`). This tool answers two
questions with those pieces and nothing new in core:

(a) Reach. On the Studio route, with the line route forced onto `gradient`:
    strands sewn / dropped, strands that land in #882's bristle region
    (`ZONES["owl_kent"]["bristles"]`, the same box, as a fraction of the
    source), bare fabric new against OFF (`hairline_renders.bare_cells`, the
    instrument `tools/hairline_coverage.py` reads) and trims.
(b) Resolution. The same census at 127 / 180 / 250 mm design width and at a
    2x work grid (`cfg.work_px_per_mm`). Which lever moves bristle strands.

Two commands, because the two questions cost differently:

- `census`  stages 0-4 and `extract_strands` only; no plan. Minutes, not
            tens of minutes. Strands, dropped, per-zone counts, FDoG lines
            found / refused by the ridge test, and the raster the route read
            (`px_per_mm`, size). One row per (image, width, grid, strand test).
- `run`     the whole plan, one arm per process, OFF first for each
            (image, width, grid) because bare fabric compares against it.

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, preflight, stitchviz  # noqa: E402
from digitizer_core import stage6_hairline_lines as L  # noqa: E402
from digitizer_core.adapter import UNITS_PER_MM, plan_to_design  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools.hairline_renders import bare_cells, bare_new_mm2  # noqa: E402

PHOTO = ROOT / "testdata" / "photo"
SYN = ROOT / "testdata" / "synthetic"
IMAGES = {"owl_kent": PHOTO / "owl_kent.jpg", "photo_owl_pale": PHOTO / "photo_owl_pale.png",
          "hair_strands": SYN / "hair_strands.png", "hair_fine": SYN / "hair_fine.png"}
DRAWN = ("hair_strands", "hair_fine")        # 80 mm, 40 drawn strands each (the A/B bar)
DRAWN_WIDTH = 80.0
# The Studio's own settings (#876's `studio` route): the two photographic
# signals ON, no forced class. Stage 0 picks the lane.
STUDIO = {"detect_photographic": True, "faces_route_flat": True}
# Zones as fractions of the SOURCE raster (x0, y0, x1, y1), first match wins.
# owl_kent's are #882's `hairline_lines_trial.ZONES` verbatim. photo_owl_pale
# is a smooth synthetic owl with no hair in it: its "bristles" box is the
# face (eyes and beak), so the row reads as a control, not a target.
ZONES = {
    "owl_kent": {"bristles": (0.36, 0.18, 0.68, 0.48), "eyes": (0.25, 0.12, 0.75, 0.25),
                 "breast": (0.0, 0.55, 1.0, 1.0)},
    "photo_owl_pale": {"bristles": (0.15, 0.12, 0.75, 0.40)},
}
# arm -> (cfg.hairline, cfg.hairline_from_lines, cfg.hairline_lines_strand_test)
ARMS = {"off": (False, False, False), "region": (True, False, False),
        "lines": (True, True, False), "lines_st": (True, True, True)}
LABELS = {"off": "OFF", "region": "hairline ON (regions)",
          "lines": "hairline ON + from_lines (gradient forced)",
          "lines_st": "from_lines + strand test"}
EXTRA_CLASSES = ("gradient",)
DEBUG = ROOT / "debug_out" / "hair_reach"
OUT = ROOT.parent / "docs" / "renders" / "claude-hair-reach"
SIZE_OUT = ROOT.parent / "docs" / "renders" / "hair-reach-size-proof"
MAX_JPEG_BYTES = 400_000
# The levers (b): (width mm, work_px_per_mm). 8.0 is `PipelineConfig`'s default.
LEVERS = {"w127": (127.0, 8.0), "w180": (180.0, 8.0), "w250": (250.0, 8.0),
          "g16": (127.0, 16.0)}


@contextlib.contextmanager
def lines_on(extra=EXTRA_CLASSES):
    """`LINE_CLASSES` widened for the duration (the tool's own patch; core is
    untouched). `applies()` reads the module global at call time, and stage 5,
    stage 7 and the stage-1 raster capture all go through it."""
    saved = L.LINE_CLASSES
    L.LINE_CLASSES = tuple(saved) + tuple(c for c in extra if c not in saved)
    try:
        yield L.LINE_CLASSES
    finally:
        L.LINE_CLASSES = saved


def cfg_for(width: float = 127.0, grid: float = 8.0, arm: str = "off",
            wt: int = 40) -> PipelineConfig:
    on, lines, st = ARMS[arm]
    return PipelineConfig(target_width_mm=width, work_px_per_mm=grid, thread_wt=wt,
                          hairline=on, hairline_from_lines=lines,
                          hairline_lines_strand_test=st, **STUDIO)


def zone_of(image: str, fx: float, fy: float) -> str:
    for name, (x0, y0, x1, y1) in ZONES.get(image, {}).items():
        if x0 <= fx < x1 and y0 <= fy < y1:
            return name
    return "elsewhere"


def zone_counts(image: str, strands, sp) -> dict:
    """strands (dicts with `pts` in mm, `length_mm`) -> {zone: {n, mm}} by
    each strand's centroid as a fraction of the source raster."""
    h, w = sp.rgb.shape[:2]
    out = {z: {"n": 0, "mm": 0.0} for z in list(ZONES.get(image, {})) + ["elsewhere"]}
    for s in strands:
        q = np.array([sp.to_px(x, y) for x, y in s["pts"]]).mean(axis=0)
        z = zone_of(image, q[0] / w, q[1] / h)
        out[z]["n"] += 1
        out[z]["mm"] = round(out[z]["mm"] + s["length_mm"], 1)
    return out


def run_zone_counts(image: str, runs, sp) -> dict:
    """Same, from sewn runs (points already in mm)."""
    strands = [{"pts": r.points, "length_mm": sum(math.dist(a, b) for a, b in
                                                  zip(r.points, r.points[1:]))}
               for r in runs]
    return zone_counts(image, strands, sp)


# ----------------------------------------------------------- the size probe
# The ridge test reads each line's sides at an offset in MILLIMETRES
# (`side0` = half `hairline_max_width_mm`, `side1` = `side0` + `_SIDE_REACH_PX`
# work pixels), on a raster whose pixel is the WORK pixel (`sp.px_per_mm` =
# `cfg.work_px_per_mm`, 8 by default, for any design size). A bristle is a
# fixed number of SOURCE pixels wide, so growing the design makes it wider in
# mm and the same mm offset lands inside it. The probe holds the side sample
# in SOURCE pixels instead: the footprint it has at the reference design
# width, scaled by source-pixels-per-mm. It changes the UNIT the offset is
# read in, not a value: at the reference width it is the identity, and no
# constant in core (`hairline_max_width_mm`, `_SIDE_REACH_PX`,
# `_PROFILE_STEP_WIDTHS`, `_SLIT_PX`) is touched.
PROBES = ("main", "side", "side_core")
REF_WIDTH_MM = 127.0


def source_scale(image: str, width: float, ref_width: float = REF_WIDTH_MM) -> float:
    """mm-per-source-pixel at `width` over mm-per-source-pixel at
    `ref_width`: how many times wider a source pixel is in mm."""
    w_px = cv2.imread(str(IMAGES[image]), cv2.IMREAD_UNCHANGED).shape[1]
    return (w_px / ref_width) / (w_px / width)


@contextlib.contextmanager
def ridge_probe(mode: str, k: float):
    """`L.ridge_contrast` wrapped for the length of a `with` block (the tool's
    own patch; core is untouched, restored on exit, errors included).
    `side`: the side sample's offset and reach x `k`. `side_core`: the core
    window's half-width too. `main`: no wrapper."""
    if mode not in PROBES:
        raise ValueError(f"probe {mode!r} not in {PROBES}")
    saved = L.ridge_contrast
    if mode != "main":
        def wrapped(pts, light, sp, *, polarity, core_mm, side0_mm, side1_mm, step_mm):
            reach = (side1_mm - side0_mm) * k
            side0_mm = side0_mm * k
            if mode == "side_core":
                core_mm = core_mm * k
            return saved(pts, light, sp, polarity=polarity, core_mm=core_mm,
                         side0_mm=side0_mm, side1_mm=side0_mm + reach, step_mm=step_mm)
        L.ridge_contrast = wrapped
    try:
        yield saved
    finally:
        L.ridge_contrast = saved


def census(image: str, width: float, grid: float, strand_test: bool, wt: int = 40,
           probe: str = "main", result=None) -> dict:
    """Stages 0-4 and the line route's extraction on the Studio route, no
    plan. The strands are what `strand_blocks` would sew (`_sewable`).
    `probe` reads the ridge test's side sample in source pixels (see
    `ridge_probe`); `result` is a `run_stages` result to reuse (the stages do
    not depend on the probe)."""
    t0 = time.time()
    arm = "lines_st" if strand_test else "lines"
    cfg = cfg_for(width, grid, arm, wt)
    with lines_on():
        if result is None:
            result = run_stages(IMAGES[image], cfg)
        sp = result.source_pixels
        row = {"image": image, "width_mm": width, "work_px_per_mm": grid,
               "strand_test": strand_test, "thread_wt": wt, "probe": probe,
               "design_class": result.design_class}
        if sp is None:
            row.update(reached=False, note="no source pixels captured on this lane")
            return row
        k = source_scale(image, width)
        row["side_scale"] = round(k, 4) if probe != "main" else 1.0
        with ridge_probe(probe, k):
            strands, cen = L.extract_strands(sp, cfg)
        keep, dropped = [], 0
        for pol in ("dark", "light"):
            k2, d = L._sewable([s for s in strands if s["polarity"] == pol], cfg, cfg.thread_wt)
            keep += [s for s, _ in k2]
            dropped += d
    h, w = sp.rgb.shape[:2]
    row.update(
        reached=True, raster_px=[w, h], px_per_mm=round(float(sp.px_per_mm), 3),
        found=cen["found"], refused_no_ridge=cen["refused_no_ridge"],
        **({"refused_bar": cen["refused_bar"]} if "refused_bar" in cen else {}),
        ridge_lines=len(strands), strands=len(keep), dropped=dropped,
        strand_mm=round(sum(s["length_mm"] for s in keep), 1),
        light=sum(1 for s in keep if s["polarity"] == "light"),
        zones=zone_counts(image, keep, sp), seconds=round(time.time() - t0))
    return row


def _short(plan) -> int:
    n = 0
    for b in plan.blocks:
        for r in b.runs:
            for a, c in zip(r.points, r.points[1:]):
                d = math.dist(a, c)
                if 0.01 < d < machine.MIN_STITCH_MM and abs(d - machine.TIE_STITCH_MM) > 1e-6:
                    n += 1
    return n


def measure(plan, image: str, sp) -> dict:
    st = plan.stats
    w = next((x for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"), None)
    line_runs = [r for b in plan.blocks for r in b.runs if r.shape_id == L.SHAPE_ID]
    return {
        "stitches": st.stitch_count, "trims": st.trims, "color_changes": st.color_changes,
        "thread_m": round(sum(math.dist(a, c) for b in plan.blocks for r in b.runs
                              for a, c in zip(r.points, r.points[1:])) / 1000.0, 2),
        "under_1mm": _short(plan),
        "hairline": ({k: w.get(k) for k in ("shapes", "strands", "dropped", "source",
                                            "found", "refused_no_ridge", "refused_bar")
                      if k in w} if w else None),
        "line_runs": len(line_runs),
        "line_thread_m": round(sum(math.dist(a, c) for r in line_runs
                                   for a, c in zip(r.points, r.points[1:])) / 1000.0, 3),
        "zones": run_zone_counts(image, line_runs, sp) if line_runs and sp is not None else None,
    }


def stem(image: str, width: float, grid: float) -> str:
    return f"{image}_w{width:g}_g{grid:g}"


def run_arm(image: str, width: float, grid: float, arm: str, wt: int = 40) -> dict:
    """One plan. OFF first: the bare-fabric read compares against it."""
    DEBUG.mkdir(parents=True, exist_ok=True)
    cfg = cfg_for(width, grid, arm, wt)
    t0 = time.time()
    with lines_on():
        result = run_stages(IMAGES[image], cfg)
        plan = plan_stitches(result, cfg)
    row = {"image": image, "width_mm": width, "work_px_per_mm": grid, "arm": arm,
           "design_class": result.design_class,
           **measure(plan, image, result.source_pixels)}
    p = preflight.prep(IMAGES[image], cfg, design_class=result.design_class)
    bare = bare_cells(plan, result, p)
    row["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
    npz = DEBUG / f"{stem(image, width, grid)}_off_bare.npz"
    if arm == "off":
        np.savez_compressed(npz, grid=bare[0], origin=np.array(bare[1]), cell=bare[2])
        row["bare_new_mm2"] = 0.0
    elif npz.exists():
        z = np.load(npz)
        row["bare_new_mm2"] = round(bare_new_mm2(
            bare, (z["grid"], tuple(z["origin"]), float(z["cell"]))), 2)
    row["seconds"] = round(time.time() - t0)
    design = plan_to_design(plan, name=f"{image} {arm}")
    (DEBUG / f"{stem(image, width, grid)}_{arm}_design.json").write_text(
        json.dumps(design), encoding="utf-8")
    (DEBUG / f"{stem(image, width, grid)}_{arm}.json").write_text(
        json.dumps(row, indent=1) + "\n", encoding="utf-8")
    return row


# --------------------------------------------------------------------- tables

def census_path(r: dict) -> Path:
    return DEBUG / (f"census_{stem(r['image'], r['width_mm'], r['work_px_per_mm'])}"
                    f"_{'st' if r['strand_test'] else 'plain'}.json")


def _zn(row: dict, z: str):
    return ((row.get("zones") or {}).get(z) or {}).get("n", "-")


def census_table(rows: list[dict]) -> str:
    out = ["| image | lever | class | raster px/mm | FDoG lines | ridge kept | strands sewn | "
           "dropped < 2.2 mm | light | bristle-zone strands | elsewhere | strand test |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if not r.get("reached"):
            out.append(f"| {r['image']} | {r['width_mm']:g} mm / grid {r['work_px_per_mm']:g} | "
                       f"{r['design_class']} | - | - | - | - | - | - | - | - | "
                       f"{'on' if r['strand_test'] else 'off'} |")
            continue
        f = sum(r["found"].values())
        out.append(f"| {r['image']} | {r['width_mm']:g} mm / grid {r['work_px_per_mm']:g} | "
                   f"{r['design_class']} | {r['px_per_mm']} | {f} | {r['ridge_lines']} | "
                   f"{r['strands']} | {r['dropped']} | {r['light']} | "
                   f"{_zn(r, 'bristles')} | {_zn(r, 'elsewhere')} | "
                   f"{'on' if r['strand_test'] else 'off'} |")
    return "\n".join(out)


def run_table(rows: list[dict]) -> str:
    out = ["| image / lever | arm | strands sewn | dropped | bristle-zone strands | stitches | "
           "trims | colour changes | thread (m) | bare new vs OFF (mm2) | bare total (mm2) |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        h = r.get("hairline") or {}
        z = r.get("zones")
        out.append(
            f"| {r['image']} {r['width_mm']:g} mm / grid {r['work_px_per_mm']:g} | "
            f"{LABELS[r['arm']]} | {h.get('strands', '-')} | {h.get('dropped', '-')} | "
            f"{(z or {}).get('bristles', {}).get('n', '-')} | {r['stitches']:,} | {r['trims']} | "
            f"{r['color_changes']} | {r['thread_m']} | {r.get('bare_new_mm2', '-')} | "
            f"{r['bare_mm2']} |")
    return "\n".join(out)


def load_rows(prefix: str) -> list[dict]:
    rows = []
    for f in sorted(DEBUG.glob(f"{prefix}*.json")):
        if f.name.endswith("_design.json"):
            continue
        rows.append(json.loads(f.read_text(encoding="utf-8")))
    return rows


def cmd_table(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    cen = load_rows("census_")
    runs = [r for r in load_rows("") if "arm" in r]
    order = {a: i for i, a in enumerate(ARMS)}
    runs.sort(key=lambda r: (r["image"], r["width_mm"], r["work_px_per_mm"], order[r["arm"]]))
    cen.sort(key=lambda r: (r["image"], r["width_mm"], r["work_px_per_mm"], r["strand_test"]))
    text = ("CENSUS (stages 0-4 + line extraction, no plan)\n\n" + census_table(cen)
            + "\n\nPLANS (whole pipeline, 40 wt)\n\n" + run_table(runs) + "\n")
    (out / "table.md").write_text(text, encoding="utf-8")
    (out / "table.json").write_text(json.dumps({"census": cen, "runs": runs}, indent=1) + "\n",
                                    encoding="utf-8")
    print(text)
    return 0


# -------------------------------------------------------------------- renders

def write_jpeg(path: Path, img) -> None:
    q = 88
    while True:
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
        if len(buf) <= MAX_JPEG_BYTES or q <= 50:
            break
        q -= 7
    path.write_bytes(buf.tobytes())


def strand_map(image: str, width: float, grid: float, out: Path, k: int = 2) -> None:
    """Every strand the route sews on the photo, over a washed-out copy of the
    raster the route read: dark red, light cyan, bristle-zone box in green."""
    cfg = cfg_for(width, grid, "lines")
    with lines_on():
        result = run_stages(IMAGES[image], cfg)
        sp = result.source_pixels
        strands, _cen = L.extract_strands(sp, cfg)
        keep = []
        for pol in ("dark", "light"):
            sewn, _dropped = L._sewable(
                [s for s in strands if s["polarity"] == pol], cfg, cfg.thread_wt)
            keep += [s for s, _pts in sewn]
    big = cv2.resize(cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2BGR), None, fx=k, fy=k,
                     interpolation=cv2.INTER_NEAREST)
    big = (0.55 * big + 0.45 * 255).astype(np.uint8)
    for s in keep:
        q = np.array([sp.to_px(x, y) for x, y in s["pts"]]) * k
        cv2.polylines(big, [np.round(q).astype(np.int32)], False,
                      (230, 160, 0) if s["polarity"] == "light" else (0, 0, 230), 2, cv2.LINE_AA)
    h, w = big.shape[:2]
    if "bristles" in ZONES.get(image, {}):
        x0, y0, x1, y1 = ZONES[image]["bristles"]
        cv2.rectangle(big, (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h)), (0, 150, 0), 2)
    out.mkdir(parents=True, exist_ok=True)
    write_jpeg(out / f"{stem(image, width, grid)}_strands.jpg", big)


def beak_crop(image: str, design: dict, sp_box, px_per_mm: float, wt: int):
    """The bristles box out of a rendered design. `sp_box` = (x0, y0, x1, y1)
    in mm in the plan's frame."""
    img = stitchviz.render_design(design, px_per_mm=px_per_mm,
                                  thread_mm=machine.thread_profile(wt).width_mm)
    _size, to_px = stitchviz._frame(design.get("stitches") or [], px_per_mm, 2.0)
    a = to_px({"x": sp_box[0] * UNITS_PER_MM, "y": -sp_box[1] * UNITS_PER_MM})
    b = to_px({"x": sp_box[2] * UNITS_PER_MM, "y": -sp_box[3] * UNITS_PER_MM})
    px0, px1 = sorted((max(a[0], 0), max(b[0], 0)))
    py0, py1 = sorted((max(a[1], 0), max(b[1], 0)))
    return img[py0:py1, px0:px1]


def cmd_render(image: str, width: float, grid: float, out: Path) -> int:
    """Strand map, plus OFF | region | lines strips over the bristles box at
    16 px/mm, from the saved designs (`run` first)."""
    out.mkdir(parents=True, exist_ok=True)
    strand_map(image, width, grid, out)
    if "bristles" not in ZONES.get(image, {}):
        return 0
    cfg = cfg_for(width, grid, "off")
    with lines_on():
        result = run_stages(IMAGES[image], cfg)
    sp = result.source_pixels
    h, w = sp.rgb.shape[:2]
    x0, y0, x1, y1 = ZONES[image]["bristles"]
    a, b = sp.to_mm(x0 * w, y0 * h), sp.to_mm(x1 * w, y1 * h)
    tiles = []
    for arm in ("off", "region", "lines"):
        f = DEBUG / f"{stem(image, width, grid)}_{arm}_design.json"
        if not f.exists():
            continue
        crop = beak_crop(image, json.loads(f.read_text(encoding="utf-8")),
                         (a[0], a[1], b[0], b[1]), 16.0, 40)
        band = np.full((34, crop.shape[1], 3), 255, np.uint8)
        cv2.putText(band, LABELS[arm][:46], (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (30, 30, 30), 2, cv2.LINE_AA)
        tiles.append(np.vstack([band, crop]))
    if tiles:
        hh = min(t.shape[0] for t in tiles)
        ww = min(t.shape[1] for t in tiles)
        sep = np.full((hh, 8, 3), 255, np.uint8)
        row = []
        for t in tiles:
            row += [t[:hh, :ww], sep]
        write_jpeg(out / f"{stem(image, width, grid)}_bristles_16pxmm.jpg", np.hstack(row[:-1]))
    return 0


# ----------------------------------------------------------------- size probe

SIZES = (127.0, 180.0, 250.0)
SIZE_ZONES = ("bristles", "breast")


def size_path(r: dict) -> Path:
    return DEBUG / (f"size_{r['image']}_w{r['width_mm']:g}_g{r['work_px_per_mm']:g}_"
                    f"{'st' if r['strand_test'] else 'plain'}_{r['probe']}.json")


def cmd_size(image: str, widths, grid: float, strand_test: bool, probes) -> int:
    """The size probe: per design width, stages 0-4 once, then the extraction
    once per probe on the SAME raster. One row per (width, probe)."""
    for width in widths:
        cfg = cfg_for(width, grid, "lines_st" if strand_test else "lines")
        with lines_on():
            result = run_stages(IMAGES[image], cfg)
        for probe in probes:
            r = census(image, width, grid, strand_test, probe=probe, result=result)
            size_path(r).write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
            print(json.dumps(r), flush=True)
    return 0


def size_table(rows: list[dict]) -> str:
    """Per size: how many ridge lines pass and what is sewn in the bristle box
    and on the breast, main vs probe. `side scale` = how many times wider the
    side offset is in mm than main's (a source pixel is that much wider)."""
    out = ["| design mm | strand test | reading | side scale | FDoG lines | ridge kept | "
           "strands sewn | bristle box | breast | elsewhere | light |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if not r.get("reached"):
            continue
        out.append(
            f"| {r['width_mm']:g} | {'on' if r['strand_test'] else 'off'} | {r['probe']} | "
            f"{r.get('side_scale', 1.0)} | {sum(r['found'].values())} | {r['ridge_lines']} | "
            f"{r['strands']} | {_zn(r, 'bristles')} | {_zn(r, 'breast')} | "
            f"{_zn(r, 'elsewhere')} | {r['light']} |")
    return "\n".join(out)


def verdict(rows: list[dict]) -> str:
    """One line per strand-test arm: bristle-box strands at each size, main
    vs probe, and whether the probe holds them flat. Flat = the probe's
    count at the largest size is at least 75% of its count at the smallest,
    AND main's is not (main lost more than a quarter)."""
    lines = []
    for st in (False, True):
        sel = [r for r in rows if r.get("reached") and r["strand_test"] == st]
        if not sel:
            continue
        parts = {}
        for probe in PROBES:
            by = {r["width_mm"]: _zn(r, "bristles") for r in sel if r["probe"] == probe}
            if by:
                parts[probe] = by
        lines.append(f"strand test {'on' if st else 'off'}: " + "; ".join(
            f"{p}: " + " / ".join(f"{int(w)} mm = {n}" for w, n in sorted(by.items()))
            for p, by in parts.items()))
    return "\n".join(lines)


def cmd_sizetable(out: Path) -> int:
    rows = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(DEBUG.glob("size_*.json"))]
    order = {p: i for i, p in enumerate(PROBES)}
    rows.sort(key=lambda r: (r["image"], r["strand_test"], r["width_mm"], order[r["probe"]]))
    out.mkdir(parents=True, exist_ok=True)
    text = size_table(rows) + "\n\n" + verdict(rows) + "\n"
    (out / "size_table.md").write_text(text, encoding="utf-8")
    (out / "size_table.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    print(text)
    return 0


def strand_panel(image: str, width: float, grid: float, probe: str, k: int = 2,
                 result=None):
    """-> BGR panel: the strands the route sews, `probe`'s reading, over a
    washed copy of the raster, bristle box in green (as `strand_map`)."""
    cfg = cfg_for(width, grid, "lines")
    with lines_on():
        if result is None:
            result = run_stages(IMAGES[image], cfg)
        sp = result.source_pixels
        with ridge_probe(probe, source_scale(image, width)):
            strands, _cen = L.extract_strands(sp, cfg)
        keep = []
        for pol in ("dark", "light"):
            sewn, _dropped = L._sewable(
                [s for s in strands if s["polarity"] == pol], cfg, cfg.thread_wt)
            keep += [s for s, _pts in sewn]
    big = cv2.resize(cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2BGR), None, fx=k, fy=k,
                     interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_NEAREST)
    big = (0.55 * big + 0.45 * 255).astype(np.uint8)
    for s in keep:
        q = np.array([sp.to_px(x, y) for x, y in s["pts"]]) * k
        cv2.polylines(big, [np.round(q).astype(np.int32)], False,
                      (230, 160, 0) if s["polarity"] == "light" else (0, 0, 230), 2, cv2.LINE_AA)
    h, w = big.shape[:2]
    x0, y0, x1, y1 = ZONES[image]["bristles"]
    cv2.rectangle(big, (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h)), (0, 150, 0), 2)
    z = zone_counts(image, keep, sp)
    band = np.full((40, w, 3), 255, np.uint8)
    cv2.putText(band, f"{probe} @ {width:g} mm: {len(keep)} strands, bristle box "
                f"{z['bristles']['n']}, breast {z['breast']['n']}", (8, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2, cv2.LINE_AA)
    return np.vstack([band, big])


def cmd_sizerender(image: str, width: float, grid: float, probe: str, out: Path) -> int:
    """Before | after at one size: main's reading beside the probe's, on the
    same raster. PNG: strands are 1-2 px lines and JPEG blurs them."""
    cfg = cfg_for(width, grid, "lines")
    with lines_on():
        result = run_stages(IMAGES[image], cfg)
    k = 0.4
    panels = [strand_panel(image, width, grid, p, k, result) for p in ("main", probe)]
    sep = np.full((panels[0].shape[0], 10, 3), 255, np.uint8)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{image}_w{width:g}_main_vs_{probe}.png"
    cv2.imwrite(str(f), np.hstack([panels[0], sep, panels[1]]),
                [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(f, f.stat().st_size)
    return 0


def cmd_drawn() -> int:
    """The A/B bar's two baselines: the drawn hair fixtures (80 mm, 40 wt,
    40 drawn strands each) with the region tier and with the line route
    forced onto `gradient`. On these the region tier already sews every
    strand as a shape (#876: 184 / 321 run branches), so a gradient-route
    flag must not lose any of it. OFF first, for bare fabric."""
    for image in DRAWN:
        for arm in ("off", "region", "lines", "lines_st"):
            r = run_arm(image, DRAWN_WIDTH, 8.0, arm)
            print(image, arm, json.dumps(r), flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("census", "run", "render"):
        p = sub.add_parser(name)
        p.add_argument("--image", choices=list(IMAGES), default="owl_kent")
        p.add_argument("--width", type=float, default=127.0)
        p.add_argument("--grid", type=float, default=8.0, help="cfg.work_px_per_mm")
        if name == "census":
            p.add_argument("--strand-test", action="store_true")
        if name == "run":
            p.add_argument("--arm", choices=list(ARMS), required=True)
        if name == "render":
            p.add_argument("--out", type=Path, default=OUT)
    sub.add_parser("drawn")
    t = sub.add_parser("table")
    t.add_argument("--out", type=Path, default=OUT)
    s = sub.add_parser("size", help="main vs source-pixel side sample at several design widths")
    s.add_argument("--image", choices=list(IMAGES), default="owl_kent")
    s.add_argument("--widths", type=float, nargs="+", default=list(SIZES))
    s.add_argument("--grid", type=float, default=8.0)
    s.add_argument("--strand-test", action="store_true")
    s.add_argument("--probes", choices=PROBES, nargs="+", default=list(PROBES))
    st = sub.add_parser("sizetable")
    st.add_argument("--out", type=Path, default=SIZE_OUT)
    sr = sub.add_parser("sizerender")
    sr.add_argument("--image", choices=list(IMAGES), default="owl_kent")
    sr.add_argument("--width", type=float, default=250.0)
    sr.add_argument("--grid", type=float, default=8.0)
    sr.add_argument("--probe", choices=PROBES[1:], default="side")
    sr.add_argument("--out", type=Path, default=SIZE_OUT)
    args = ap.parse_args(argv)
    DEBUG.mkdir(parents=True, exist_ok=True)
    if args.cmd == "census":
        r = census(args.image, args.width, args.grid, args.strand_test)
        census_path(r).write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(r), flush=True)
    elif args.cmd == "size":
        return cmd_size(args.image, args.widths, args.grid, args.strand_test, args.probes)
    elif args.cmd == "sizetable":
        return cmd_sizetable(args.out)
    elif args.cmd == "sizerender":
        return cmd_sizerender(args.image, args.width, args.grid, args.probe, args.out)
    elif args.cmd == "run":
        print(json.dumps(run_arm(args.image, args.width, args.grid, args.arm)), flush=True)
    elif args.cmd == "drawn":
        return cmd_drawn()
    elif args.cmd == "render":
        return cmd_render(args.image, args.width, args.grid, args.out)
    else:
        return cmd_table(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
