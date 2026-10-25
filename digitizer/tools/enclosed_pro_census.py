#!/usr/bin/env python
"""enclosed_pro_census: every enclosed white of ours beside the pro's thread, registered.

WHAT IT IS FOR. `sew_enclosed_white` decides which enclosed areas sew;
`enclosed_white_keyline` and `sew_enclosed_white_fields_fill` decide how.
Kent re-rules those flips from this table. It rebuilds the 2026-10-23 census
(`docs/enclosed-white-like-pro-2026-10-23.md`, "Census tooling": its script
was session scratch and never committed) from that doc's recipe, so the
32/34 figure can be reproduced before a change is scored against it. It then
adds the construction numbers a flip needs: the white colour blocks, how the
Becker faces sew (row angle, underlay, block order) and the wall time.

HOW. Each job is digitized the Studio's way (`tools.pro_pair.digitize` at the
pro's width with the job's garment, `tools.pro_intake.pair_record` for the
files), once per ARM, and cached as `ours.dst` + `cell.json` (regions,
tags, runs per shape) under `--cache`. A cell that exists is not re-run.

`table` reads every DST with ONE reader (pystitch). Thread is a STITCH
following a STITCH; any JUMP, TRIM, COLOR_CHANGE or STOP between two
penetrations makes that step a move, not thread. Each file is read in its own
frame:

  rows ......... every `enclosed_background` region of our OFF cell
  pro thread ... our OFF DST registered to the pro's
                 (`tools/pro_parity/pairframe.register_pair`: one scale, a
                 y-flip search, a translation search); the region's polygon is
                 carried into his frame, eroded 0.35 mm, and the reading is
                 the share of it within 0.25 mm of one of his stitch lines
                 (a 10 px/mm raster with 0.5 mm lines)
  ours ......... the same reading of OUR DST for each arm, in our own frame
  calib ........ the pro-thread reading over our own sewn regions that are not
                 enclosed (the doc: 98.4-100% on every job). A job reading far
                 below that is a bad registration, not a finding.

A region reads SEWN at `SEWN_MIN` or more. Agreement is counted on the
calibration jobs except `UNREADABLE`, with Cohen's kappa beside the raw count
(ROADMAP gate 4).

  python -m tools.enclosed_pro_census run [--only SLUG ...] [--arms off,white,on] [--jobs 2]
  python -m tools.enclosed_pro_census table [--json OUT] [--md OUT]
  python -m tools.enclosed_pro_census time SLUG --width MM [--garment G] [--arms off,on]
  python -m tools.enclosed_pro_census one SLUG ARM [--width MM] [--garment G]
  python -m tools.enclosed_pro_census render SLUG --what whole|faces|band | --region ID --out X.jpg

`time` runs its arms one after another, each in a fresh process, and prints
the pipeline seconds `pro_pair.digitize` measures (art decode to plan, the
part a Studio job waits on), the CPU seconds of that same span, and the
process wall time. On a shared machine the wall time moves 2-3x from one run
to the next with the load; the CPU time is the one to compare arms by.

MFab needs rembg, whose venv a lane does not carry: a missing local venv is
pointed at the primary checkout's (`_rembg`). A row that cannot run is named
and skipped, never scored 0.

Nothing here changes an engine default; the flips are Kent's.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402

RES = 0.1               # raster pixel, mm (10 px/mm)
THREAD_MM = 0.5         # a stitch line drawn this wide: within 0.25 mm of it
ERODE_MM = 0.35         # a region is read inside this margin of its own edge
SEWN_MIN = 0.75         # thread share that reads as sewn (the doc: sewn ~1.0, open 0.1-0.52)
SPECK_MM2 = 2.5         # under this with no holder: a speck (the doc's class)
WHITE_MIN_MM2 = 20.0    # whites read as colour blocks only when this much sews (specks name noise)
ROW_MIN_MM = 1.0        # a fill row stitch is at least this long ...
ROW_COS = 0.99          # ... and parallel to a neighbour this closely
RING_MM = (0.2, 1.2)    # the outline of a face is read in this ring outside it
DEFAULT_CACHE = DIGITIZER / "debug_out" / "enclosed_pro_census"
GROUND_BGR = (128, 128, 128)  # renders: mid grey, so white thread and black both show

#: the arms: Studio-request fields laid over `tools.pro_pair.request`
WHITE3 = {"sew_enclosed_white": True, "enclosed_white_keyline": True,
          "sew_enclosed_white_fields_fill": True}
ARMS = {
    "off": {},
    "white": {"sew_enclosed_white": True},                    # the 2026-10-23 census's ON
    "white_keyline": {"sew_enclosed_white": True, "enclosed_white_keyline": True},
    # the keyline as #1059 measured it, before `border_from_outline` (ON since
    # 2026-10-24) took the band over
    "white_keyline_nobfo": {"sew_enclosed_white": True, "enclosed_white_keyline": True,
                            "border_from_outline": False},
    "on": dict(WHITE3),                                       # all three white switches
    "on_nobfo": {**WHITE3, "border_from_outline": False},
    "off_nobfo": {"border_from_outline": False},
}

#: (slug, width override, art override). Width None: the pro's file width.
_TD = DIGITIZER / "testdata"
JOBS = {
    "mfab_hat": (None, None),
    "mfab_lc": (None, None),
    "becker_hat_small": (None, None),
    "becker_chest_small": (None, None),
    "becker_hat_large": (None, None),
    "becker_lc_large": (None, None),
    # pro_intake registers this pair with To a T's beanie art; it is Becker's logo
    "becker_beanie": (None, _TD / "becker_marine_logo.png"),
    "gaulke_roofing_hat": (None, None),
    "hotel_fremont_hat": (92.5, None),       # the doc's width (Kent's), not the file's 92.6
    "hotel_fremont_patch": (None, None),
    "precision_drone": (None, None),
    "tires_hat_3d": (None, None),
    "golf_hat": (None, None),                # Golden Tee
}
#: the doc's seven jobs, in its order
CALIBRATION_JOBS = ["mfab_hat", "becker_hat_small", "becker_chest_small", "gaulke_roofing_hat",
                    "hotel_fremont_hat", "precision_drone", "tires_hat_3d"]
#: the pairs a white flip is scored on
SCORE_JOBS = ["becker_chest_small", "becker_hat_small", "becker_hat_large", "becker_lc_large",
              "becker_beanie", "mfab_hat", "mfab_lc", "tires_hat_3d", "hotel_fremont_patch",
              "golf_hat"]
UNREADABLE = {"precision_drone": "the pro redrew the design and relaid the text (rule R15): "
                                 "his thread over our specks says nothing about his whites",
              "becker_beanie": "both files sew a knockdown under the whole design (ours "
                               "`beanie_knockdown`, his first block covers it all), so every "
                               "enclosed region reads sewn on both sides; its faces still read"}
META_KEEP = ("enclosed_background", "enclosed_colour_unknown", "text_candidate", "lettering_group",
             "text_cluster_id", "word_id", "counter", "sew_enclosed_white", "tier", "stitched",
             "layer", "fill_angle_deg")


# ------------------------------------------------------------------ files
def job_files(slug: str) -> dict:
    from tools.pro_intake import pair_record
    if slug not in JOBS:
        raise SystemExit(f"{slug}: not a census job ({', '.join(JOBS)})")
    rec = pair_record(slug)
    if rec is None or rec.get("dst") is None:
        raise SystemExit(f"{slug}: not registered by tools.pro_intake (no pro DST found)")
    width, art = JOBS[slug]
    from tools.pro_pair import pro_counts
    return {"pro": Path(rec["dst"]), "art": Path(art or rec["art"]),
            "width": float(width or pro_counts(rec["dst"])["width_mm"]),
            "garment": rec.get("garment_id") or "hat_front"}


def cell_dir(cache: Path, slug: str, width: float, garment: str, arm: str) -> Path:
    return Path(cache) / f"{slug}@{width:g}_{garment}" / arm


def _rembg() -> str | None:
    """Point stage 1 at the primary checkout's rembg venv when this lane has none."""
    from digitizer_core import stage1_photo_prep as s1
    if s1.REMBG_VENV_PYTHON.is_file():
        return None
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=DIGITIZER,
                            capture_output=True, text=True).stdout.strip()
    venv = Path(common).resolve().parent / "digitizer" / "rembg_isolated" / "venv"
    for cand in (venv / "Scripts" / "python.exe", venv / "bin" / "python"):
        if cand.is_file():
            s1.REMBG_VENV_PYTHON = cand
            return str(cand)
    return None


def _sha() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=DIGITIZER,
                          capture_output=True, text=True).stdout.strip()


# ------------------------------------------------------------- digitizing
def digitize_cell(slug: str, arm: str, cache: Path, width: float | None = None,
                  garment: str | None = None) -> Path:
    """One job under one arm -> `<cell>/ours.dst` + `<cell>/cell.json`."""
    from shapely import wkt
    from digitizer_core import columns, enclosed_white, stitches
    from digitizer_core.export import write_dst
    from tools import pro_pair as pp

    job = job_files(slug)
    w = float(width or job["width"])
    g = garment or job["garment"]
    out = cell_dir(cache, slug, w, g, arm)
    out.mkdir(parents=True, exist_ok=True)
    rembg = _rembg()
    cpu0 = time.process_time()
    d = pp.digitize(job["art"], w, g, ARMS[arm])
    cpu = time.process_time() - cpu0
    write_dst(d.plan, out / "ours.dst")

    regions = d.result.regions
    white_cfg = replace(d.cfg, sew_enclosed_white=True)
    would = enclosed_white.plan_enclosed_white(regions, white_cfg)
    runs: dict[str, dict] = {}
    for bi, blk in enumerate(d.plan.blocks):
        for run in blk.runs:
            e = runs.setdefault(str(run.shape_id), {"kinds": {}, "blocks": []})
            k = str(run.kind)
            e["kinds"][k] = e["kinds"].get(k, 0) + len(run.points or [])
            if bi not in e["blocks"]:
                e["blocks"].append(bi)
    rows = []
    for r in regions:
        m = r.meta or {}
        row = {"id": r.shape_id, "thread": r.thread_number, "area": round(r.polygon.area, 3),
               "holes": len(r.polygon.interiors),
               "wkt": wkt.dumps(r.polygon, rounding_precision=3),
               "meta": {k: m[k] for k in META_KEEP if k in m},
               "is_letter": enclosed_white._is_letter(r, d.cfg),
               "is_lettering": bool(columns.is_lettering(r, d.cfg)),
               "would_sew": would.get(r.shape_id)}
        if m.get("enclosed_background"):
            h = enclosed_white._encloser(r, regions)
            row["holder"] = None if h is None else {
                "id": h.shape_id, "area": round(h.polygon.area, 1),
                "holes": len(h.polygon.interiors), "is_letter": enclosed_white._is_letter(h, d.cfg)}
        rows.append(row)

    first_plan = next((pt for cmd, pt in stitches.iter_machine_commands(d.plan)
                       if cmd == stitches.CMD_STITCH), None)
    first_dst = next(((x, y) for x, y, c in read_stream(out / "ours.dst") if c == _cmd("STITCH")),
                     None)
    # the DST is the plan in 0.1 mm units, so this is rounding unless the
    # writer moved the design; only a real move is applied to the polygons
    offset = [0.0, 0.0] if first_plan is None or first_dst is None else [
        round(first_dst[0] - first_plan[0], 3), round(first_dst[1] - first_plan[1], 3)]
    if math.hypot(*offset) <= 0.1:
        offset = [0.0, 0.0]
    cell = {"slug": slug, "arm": arm, "sets": ARMS[arm], "width": w, "garment": g,
            "art": job["art"].name, "pro": job["pro"].name, "engine": _sha(),
            "secs": round(d.secs, 1), "cpu_s": round(cpu, 1), "stitches": d.plan.stats.stitch_count,
            "trims": d.plan.stats.trims, "rembg": rembg, "dst_offset_mm": offset,
            "cfg": {k: getattr(d.cfg, k, None) for k in
                    ("sew_enclosed_white", "enclosed_white_keyline",
                     "sew_enclosed_white_fields_fill", "border_from_outline", "garment_id",
                     "fill_angle_deg", "target_width_mm")},
            "blocks": [{"thread": b.thread_number, "rgb": list(b.rgb)} for b in d.plan.blocks],
            "regions": rows, "runs": runs}
    (out / "cell.json").write_text(json.dumps(cell, default=str), encoding="utf-8")
    return out


def _spawn(slug: str, arm: str, cache: Path, width=None, garment=None) -> dict:
    cmd = [sys.executable, "-m", "tools.enclosed_pro_census", "one", slug, arm,
           "--cache", str(cache)]
    if width:
        cmd += ["--width", str(width)]
    if garment:
        cmd += ["--garment", garment]
    t = time.time()
    p = subprocess.run(cmd, cwd=DIGITIZER, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return {"slug": slug, "arm": arm, "rc": p.returncode, "wall": round(time.time() - t, 1),
            "tail": (p.stdout + p.stderr)[-600:]}


def run_cmd(a) -> int:
    jobs = a.only or sorted(set(CALIBRATION_JOBS) | set(SCORE_JOBS),
                            key=lambda s: list(JOBS).index(s))
    todo = []
    for slug in jobs:
        try:
            jf = job_files(slug)
        except SystemExit as e:
            print(f"SKIP {slug}: {e}", flush=True)
            continue
        for arm in a.arms:
            if not (cell_dir(a.cache, slug, jf["width"], jf["garment"], arm) / "cell.json").exists():
                todo.append((slug, arm))
    print(f"{len(todo)} cells to run", flush=True)
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for res in ex.map(lambda sa: _spawn(sa[0], sa[1], a.cache), todo):
            ok = "ok" if res["rc"] == 0 else f"FAILED rc={res['rc']}\n{res['tail']}"
            print(f"{res['slug']} {res['arm']}: {res['wall']} s {ok}", flush=True)
    return 0


def time_cmd(a) -> int:
    """Each arm in its own fresh process, one after another."""
    rows = []
    for arm in a.arms:
        res = _spawn(a.slug, arm, a.cache, a.width, a.garment)
        jf = job_files(a.slug)
        cd = cell_dir(a.cache, a.slug, float(a.width or jf["width"]), a.garment or jf["garment"], arm)
        cell = json.loads((cd / "cell.json").read_text(encoding="utf-8")) if res["rc"] == 0 else {}
        row = {"slug": a.slug, "arm": arm, "width": cell.get("width"), "garment": cell.get("garment"),
               "pipeline_s": cell.get("secs"), "cpu_s": cell.get("cpu_s"),
               "process_s": res["wall"], "rc": res["rc"],
               "stitches": cell.get("stitches"), "trims": cell.get("trims"),
               "engine": cell.get("engine"), "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        rows.append(row)
        print(json.dumps(row), flush=True)
        if res["rc"]:
            print(res["tail"], flush=True)
    for r in rows:
        if r["pipeline_s"]:
            print(f"{r['arm']:>10}: {r['pipeline_s']:7.1f} s pipeline wall, {r['cpu_s']:7.1f} s cpu, "
                  f"{r['process_s']:7.1f} s process", flush=True)
    log = Path(a.cache) / "timings.jsonl"
    with log.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return 0


# ----------------------------------------------------------------- readers
def _cmd(name: str) -> int:
    import pystitch
    return getattr(pystitch, name)


def read_stream(path) -> list[tuple[float, float, int]]:
    """(x mm, y mm y-down, command) per record, as pystitch reads the file."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    m = pystitch.COMMAND_MASK
    return [(x / 10.0, y / 10.0, c & m) for x, y, c in pat.stitches]


def thread_steps(stream) -> list[tuple[float, float, float, float, int]]:
    """(x0, y0, x1, y1, block) for each STITCH that directly follows a STITCH
    in the same block -- thread on the cloth. A move is never thread."""
    S, CC = _cmd("STITCH"), _cmd("COLOR_CHANGE")
    out, prev, block = [], None, 0
    for x, y, c in stream:
        if c == S:
            if prev is not None:
                out.append((prev[0], prev[1], x, y, block))
            prev = (x, y)
        else:
            prev = None
            if c == CC:
                block += 1
    return out


def penetrations(stream) -> list[tuple[float, float, int]]:
    S, CC = _cmd("STITCH"), _cmd("COLOR_CHANGE")
    out, block = [], 0
    for x, y, c in stream:
        if c == S:
            out.append((x, y, block))
        elif c == CC:
            block += 1
    return out


class Grid:
    """A 10 px/mm raster over a file's own extents (mm, y-down)."""

    def __init__(self, steps, pad=3.0):
        xs = [v for s in steps for v in (s[0], s[2])] or [0.0]
        ys = [v for s in steps for v in (s[1], s[3])] or [0.0]
        self.x0, self.y0 = min(xs) - pad, min(ys) - pad
        self.w = int((max(xs) + pad - self.x0) / RES) + 1
        self.h = int((max(ys) + pad - self.y0) / RES) + 1

    def px(self, x, y):
        return int(round((x - self.x0) / RES)), int(round((y - self.y0) / RES))

    def thread(self, steps, blocks=None):
        import cv2
        import numpy as np
        m = np.zeros((self.h, self.w), np.uint8)
        th = max(1, int(round(THREAD_MM / RES)))
        for x0, y0, x1, y1, b in steps:
            if blocks is not None and b not in blocks:
                continue
            cv2.line(m, self.px(x0, y0), self.px(x1, y1), 1, th)
        return m > 0

    def poly(self, geom):
        import cv2
        import numpy as np
        m = np.zeros((self.h, self.w), np.uint8)
        for p in getattr(geom, "geoms", [geom]):
            if p.is_empty or p.geom_type != "Polygon":
                continue
            ring = lambda r: np.array([self.px(x, y) for x, y in r.coords], np.int32)  # noqa: E731
            cv2.fillPoly(m, [ring(p.exterior)], 1)
            for hole in p.interiors:
                cv2.fillPoly(m, [ring(hole)], 0)
        return m > 0


def share(thread_mask, poly_mask) -> float | None:
    n = int(poly_mask.sum())
    return None if n == 0 else round(float((thread_mask & poly_mask).sum()) / n, 3)


def kappa(pairs) -> float | None:
    """Cohen's kappa of (ours, pro) booleans."""
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe >= 1.0 else round((po - pe) / (1 - pe), 3)


def row_angles(steps, geom, block: int) -> list[float]:
    """Undirected angle (deg, file frame y-down, mod 180) of every fill-row
    stitch of `block` inside `geom`: at least `ROW_MIN_MM` and parallel to
    the stitch before or after it on the same pass."""
    from shapely import prepared
    from shapely.geometry import Point
    inside = prepared.prep(geom)
    out = []
    for i, (x0, y0, x1, y1, b) in enumerate(steps):
        if b != block:
            continue
        L = math.hypot(x1 - x0, y1 - y0)
        if L < ROW_MIN_MM:
            continue
        par = False
        for j in (i - 1, i + 1):
            if not 0 <= j < len(steps) or steps[j][4] != b:
                continue
            q = steps[j]
            joined = (q[2], q[3]) == (x0, y0) if j < i else (q[0], q[1]) == (x1, y1)
            Lj = math.hypot(q[2] - q[0], q[3] - q[1])
            dot = abs((x1 - x0) * (q[2] - q[0]) + (y1 - y0) * (q[3] - q[1]))
            if joined and Lj >= ROW_MIN_MM and dot >= ROW_COS * L * Lj:
                par = True
        if par and inside.contains(Point(x0, y0)) and inside.contains(Point(x1, y1)):
            out.append(math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0)
    return out


def angle_summary(angles) -> dict:
    import numpy as np
    if not angles:
        return {"rows": 0}
    a = np.asarray(angles)
    bins = np.floor(a / 5.0) * 5.0
    vals, counts = np.unique(bins, return_counts=True)
    top = int(np.argmax(counts))
    a2 = np.radians(a * 2.0)
    mean = (math.degrees(math.atan2(float(np.sin(a2).mean()), float(np.cos(a2).mean()))) / 2.0) % 180.0
    return {"rows": int(len(a)), "axial_mean_deg": round(mean, 1),
            "top_bin_deg": f"{vals[top]:g}-{vals[top] + 5:g}",
            "top_bin_share": round(float(counts[top]) / len(a), 3)}


# -------------------------------------------------------------- analysis
def _load(cache: Path, slug: str, arm: str) -> tuple[dict, Path] | None:
    try:
        jf = job_files(slug)
    except SystemExit:
        return None
    cd = cell_dir(cache, slug, jf["width"], jf["garment"], arm)
    if not (cd / "cell.json").exists():
        return None
    return json.loads((cd / "cell.json").read_text(encoding="utf-8")), cd / "ours.dst"


def _geom(row, offset):
    from shapely import affinity, wkt
    g = wkt.loads(row["wkt"])
    return affinity.translate(g, offset[0], offset[1]) if any(offset) else g


def registration(pro_path: Path, off_dst: Path):
    """`pairframe.register_pair(pro, our OFF DST)`, cached beside the OFF cell
    until that DST changes (the search is the slow part of a table)."""
    from tools.pro_parity.pairframe import Reg, register_pair
    f = Path(off_dst).parent.parent / "reg.json"
    key = {"pro": str(pro_path), "size": off_dst.stat().st_size, "mtime": off_dst.stat().st_mtime}
    if f.exists():
        got = json.loads(f.read_text(encoding="utf-8"))
        if got.get("key") == key:
            return Reg(**got["reg"])
    reg = register_pair(pro_path, off_dst)
    f.write_text(json.dumps({"key": key, "reg": reg.as_dict()}), encoding="utf-8")
    return reg


def _role(row) -> str:
    h = row.get("holder")
    if row.get("is_letter"):
        return "letter body"
    if h is None:
        return "speck" if row["area"] < SPECK_MM2 else "field"
    if h["is_letter"]:
        return "counter"
    return "band" if row["holes"] >= 2 else "hole in untagged shape"


def analyse_job(cache: Path, slug: str, arms: list[str]) -> dict | None:
    import numpy as np
    from shapely import affinity
    from shapely.ops import unary_union
    from tools.pro_fill_underlay import analyse_block, passes_of

    def classify_file(path, min_fill_mm, block):
        blocks = passes_of(path)
        return analyse_block(blocks[block], min_fill_mm) if block < len(blocks) else []

    off = _load(cache, slug, "off")
    if off is None:
        return None
    off_cell, off_dst = off
    jf = job_files(slug)
    pro_path = jf["pro"]
    reg = registration(pro_path, off_dst)
    M = reg.matrix()
    pro_stream = read_stream(pro_path)
    pro_steps = thread_steps(pro_stream)
    pg = Grid(pro_steps)
    pro_thread = pg.thread(pro_steps)

    def to_pro(g):
        return affinity.affine_transform(g, M)

    off_off = off_cell["dst_offset_mm"]
    regions = {r["id"]: r for r in off_cell["regions"]}
    sewn_ids = {sid for sid, e in off_cell["runs"].items()
                if any(k not in ("travel", "jump") for k in e["kinds"])}
    calib_geom = unary_union([_geom(r, off_off) for r in off_cell["regions"]
                              if r["id"] in sewn_ids and not r["meta"].get("enclosed_background")])
    calib = share(pro_thread, pg.poly(to_pro(calib_geom).buffer(-ERODE_MM)))

    arm_cells = {}
    for arm in arms:
        got = _load(cache, slug, arm)
        if got is not None:
            cell, dst = got
            st = read_stream(dst)
            steps = thread_steps(st)
            g = Grid(steps)
            arm_cells[arm] = {"cell": cell, "dst": dst, "stream": st, "steps": steps, "grid": g,
                              "thread": g.thread(steps),
                              "regions": {r["id"]: r for r in cell["regions"]}}

    rows = []
    for r in off_cell["regions"]:
        if not r["meta"].get("enclosed_background"):
            continue
        g = _geom(r, off_off)
        h = r.get("holder")
        row = {"id": r["id"], "area": r["area"], "holes": r["holes"], "role": _role(r),
               "holder": None if h is None else f"{h['id']} {h['area']} mm2"
                                               f"{' letter' if h['is_letter'] else ''}",
               "min_dim_mm": round(2.0 * _inradius(g), 2),
               "would_sew": r["would_sew"],
               "pro": share(pro_thread, pg.poly(to_pro(g).buffer(-ERODE_MM))), "ours": {}}
        for arm, ac in arm_cells.items():
            go = _geom(r, ac["cell"]["dst_offset_mm"])
            ar = ac["regions"].get(r["id"]) or {}
            row["ours"][arm] = {"thread": share(ac["thread"], ac["grid"].poly(go.buffer(-ERODE_MM))),
                                "kind": (ar.get("meta") or {}).get("sew_enclosed_white"),
                                "lettering": ar.get("is_lettering")}
        rows.append(row)

    # the white colour blocks, one rule on both sides
    blocks = {}
    pro_white_geom = unary_union([to_pro(_geom(regions[x["id"]], off_off)) for x in rows
                                  if x["pro"] is not None and x["pro"] >= SEWN_MIN])
    n_pro = 1 + sum(1 for *_xy, c in pro_stream if c == _cmd("COLOR_CHANGE"))
    blocks["pro"] = white_blocks(pg, pro_stream, pro_steps, pro_white_geom,
                                 pes_colours(pro_path, n_pro))
    for arm, ac in arm_cells.items():
        white = [_geom(ar, ac["cell"]["dst_offset_mm"]) for ar in ac["cell"]["regions"]
                 if (ar.get("meta") or {}).get("sew_enclosed_white")]
        n = 1 + sum(1 for *_xy, c in ac["stream"] if c == _cmd("COLOR_CHANGE"))
        rgbs = [b["rgb"] for b in ac["cell"]["blocks"]]
        blocks[arm] = (white_blocks(ac["grid"], ac["stream"], ac["steps"], unary_union(white),
                                    rgbs if len(rgbs) == n else None) if white else None)

    # the Becker faces: construction, ours (each arm) and the pro's; a side
    # whose faces do not read sewn is reported as not sewn
    faces = [x for x in rows if x["role"] == "letter body"]
    face_rep = None
    if faces:
        face_geom = unary_union([_geom(regions[x["id"]], off_off) for x in faces])
        pro_face = to_pro(face_geom)
        pro_sewn = all(x["pro"] is not None and x["pro"] >= SEWN_MIN for x in faces)
        face_rep = {"faces": [{"id": x["id"], "area": x["area"]} for x in faces],
                    "pro": (construction(pro_path, pro_stream, pro_steps, pg, pro_face,
                                         classify_file)
                            if pro_sewn else {"sewn": False})}
        for arm, ac in arm_cells.items():
            fg = unary_union([_geom(ac["regions"][x["id"]], ac["cell"]["dst_offset_mm"])
                              for x in faces if x["id"] in ac["regions"]])
            sewn = all((x["ours"].get(arm) or {}).get("thread") is not None
                       and x["ours"][arm]["thread"] >= SEWN_MIN for x in faces)
            c = (construction(ac["dst"], ac["stream"], ac["steps"], ac["grid"], fg,
                              classify_file)
                 if sewn else {"sewn": False})
            kinds: dict[str, int] = {}
            for x in faces:
                for k, n in (ac["cell"]["runs"].get(x["id"]) or {}).get("kinds", {}).items():
                    kinds[k] = kinds.get(k, 0) + n
            c["run_points"] = kinds
            c["house_angle_deg"] = sorted({(ac["regions"].get(x["id"]) or {}).get("meta", {})
                                           .get("fill_angle_deg") for x in faces}, key=str)
            face_rep[arm] = c

    totals = {"pro": counts(pro_stream)}
    for arm, ac in arm_cells.items():
        totals[arm] = {**counts(ac["stream"]), "secs": ac["cell"]["secs"],
                       "cpu_s": ac["cell"].get("cpu_s"),
                       "engine": ac["cell"]["engine"]}
    return {"slug": slug, "width": off_cell["width"], "garment": off_cell["garment"],
            "reg": reg.as_dict(), "calib": calib, "rows": rows, "blocks": blocks,
            "faces": face_rep, "totals": totals, "unreadable": UNREADABLE.get(slug),
            "arms": sorted(arm_cells)}


def _inradius(g) -> float:
    try:
        from shapely import maximum_inscribed_circle
        return float(maximum_inscribed_circle(g).length)
    except Exception:  # noqa: BLE001 -- a degenerate sliver reads 0
        return 0.0


def counts(stream) -> dict:
    cmds = [c for *_, c in stream]
    return {"stitches": sum(1 for c in cmds if c == _cmd("STITCH")),
            "trims": sum(1 for c in cmds if c == _cmd("TRIM"))}


def pes_colours(dst: Path, n_blocks: int) -> list | None:
    """The thread colours of the PES beside a DST, one per block, when the
    two files carry the same number of blocks (a DST carries none)."""
    import pystitch
    pes = next((q for q in Path(dst).parent.iterdir()
                if q.stem == Path(dst).stem and q.suffix.lower() == ".pes"), None)
    if pes is None:
        return None
    pat = pystitch.read(str(pes))
    if pat is None:
        return None
    n = 1 + sum(1 for *_xy, c in pat.stitches if (c & pystitch.COMMAND_MASK) == pystitch.COLOR_CHANGE)
    if n != n_blocks or len(pat.threadlist) < n:
        return None
    return [[t.get_red(), t.get_green(), t.get_blue()] for t in pat.threadlist[:n]]


def layers(grid, steps, mask) -> tuple[dict[int, float], dict[int, float]]:
    """-> (top, cover): the share of `mask` whose TOPMOST thread is each
    block (the last block sewn over a pixel is the colour the eye sees), and
    the share each block's thread covers at any depth."""
    import numpy as np
    n = int(mask.sum())
    if n == 0:
        return {}, {}
    last = np.full(mask.shape, -1, np.int32)
    cover = {}
    for b in sorted({q[4] for q in steps}):
        t = grid.thread(steps, {b})
        last[t] = b
        c = float((t & mask).sum()) / n
        if c > 0:
            cover[b] = round(c, 3)
    vals = last[mask]
    u, k = np.unique(vals[vals >= 0], return_counts=True)
    return {int(b): round(float(c) / n, 3) for b, c in zip(u, k)}, cover


def _block_stats(stream, steps, idx) -> dict:
    import numpy as np
    lens = np.array([math.hypot(q[2] - q[0], q[3] - q[1]) for q in steps if q[4] in idx])
    trims, block, n = 0, 0, 0
    for _x, _y, c in stream:
        if c == _cmd("COLOR_CHANGE"):
            block += 1
        elif block in idx:
            n += c == _cmd("STITCH")
            trims += c == _cmd("TRIM")
    return {"stitches": int(n), "under_1mm": int((lens < 1.0).sum()) if len(lens) else 0,
            "median_mm": round(float(np.median(lens)), 2) if len(lens) else None,
            "trims": int(trims)}


def white_blocks(grid, stream, steps, white_geom, rgbs: list | None) -> dict | None:
    """The colour blocks that sew the whites: the block whose thread is on
    TOP over most of `white_geom` (eroded `ERODE_MM`), and every block in its
    thread colour (a lone DST has no colours: that one block). `under` names
    the other blocks sewn first that cover at least half of it (the pro's
    black under the MFab band, rule R13)."""
    if white_geom is None or white_geom.is_empty or white_geom.area < WHITE_MIN_MM2:
        return None
    inner = white_geom.buffer(-ERODE_MM)
    top, cover = layers(grid, steps, grid.poly(inner if not inner.is_empty else white_geom))
    if not top:
        return {"blocks": [], "stitches": 0}
    vis = max(top, key=top.get)
    idx = ([b for b in range(len(rgbs)) if list(rgbs[b]) == list(rgbs[vis])]
           if rgbs and vis < len(rgbs) else [vis])
    under = {b: c for b, c in cover.items() if b not in idx and b < min(idx) and c >= 0.5}
    return {"blocks": idx, "rgb": list(rgbs[vis]) if rgbs and vis < len(rgbs) else None,
            "on_top": top.get(vis), "under": under, **_block_stats(stream, steps, set(idx))}


def construction(path, stream, steps, grid, face_geom, classify_file) -> dict:
    """How the face area sews: the block on top over it, the block on top in
    a ring just outside it (the outline), any block sewn under it, the row
    angle of the face block, and that block's fills' underlay verdict."""
    inner = face_geom.buffer(-ERODE_MM)
    ring = face_geom.buffer(RING_MM[1]).difference(face_geom.buffer(RING_MM[0]))
    top, cover = layers(grid, steps, grid.poly(inner))
    if not top:
        return {"sewn": False}
    face_b = max(top, key=top.get)
    rtop, _ = layers(grid, steps, grid.poly(ring))
    rtop.pop(face_b, None)
    ring_b = max(rtop, key=rtop.get) if rtop else None
    fills = [{"verdict": v, "area": d["area"], "dense_ax": d["dense_ax"],
              "pitch": d["dense_pitch"], "stitch": d["dense_stitch"]}
             for v, d in classify_file(path, 200.0, face_b)]
    st = _block_stats(stream, steps, {face_b})
    return {"sewn": True, "face_block": face_b, "on_top": top[face_b],
            "face_block_stitches": st["stitches"], "face_block_trims": st["trims"],
            "under": {b: c for b, c in cover.items() if b < face_b and c >= 0.5},
            "outline_block": ring_b,
            "under_outline": None if ring_b is None else face_b < ring_b,
            "rows": angle_summary(row_angles(steps, inner, face_b)), "fills": fills}


# ----------------------------------------------------------------- report
def _f(v, nd=2):
    return "—" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def table_cmd(a) -> int:
    utf8_console()
    arms = [x for x in ARMS if x != "off"]
    out = {}
    for slug in JOBS:
        t = time.time()
        rep = analyse_job(a.cache, slug, ["off"] + arms)
        if rep is not None:
            out[slug] = rep
            print(f"{slug}: read in {time.time() - t:.0f} s", file=sys.stderr, flush=True)
    lines = ["# enclosed_pro_census", ""]
    for title, jobs, arm in (("Calibration: the 2026-10-23 census, arm `white`", CALIBRATION_JOBS, "white"),
                             ("Score: `sew_enclosed_white` alone, arm `white`", SCORE_JOBS, "white"),
                             ("Score: all three white switches, arm `on`", SCORE_JOBS, "on"),
                             ("Score: arm `on_nobfo` (border_from_outline False)", SCORE_JOBS, "on_nobfo")):
        lines += [f"## {title}", "",
                  "| job | region | mm² | min dim | holes | holder | role | plan | pro | ours OFF | "
                  "ours | agree |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        pairs, misses, skipped = [], [], []
        for slug in jobs:
            rep = out.get(slug)
            if rep is not None and not rep["rows"]:
                lines.append(f"| {slug} ({rep['width']:g}) | none | | | | | | | | | | |")
                continue
            if rep is None or arm not in rep["arms"]:
                skipped.append(slug)
                continue
            for row in rep["rows"]:
                o = row["ours"].get(arm) or {}
                ours_t, pro_t = o.get("thread"), row["pro"]
                if ours_t is None or pro_t is None:
                    ag = "n/a (eroded away)"
                else:
                    ok = (ours_t >= SEWN_MIN) == (pro_t >= SEWN_MIN)
                    if rep["unreadable"]:
                        ag = "unreadable"
                    else:
                        ag = "yes" if ok else "**NO**"
                        pairs.append((ours_t >= SEWN_MIN, pro_t >= SEWN_MIN))
                        if not ok:
                            off_t = (row["ours"].get("off") or {}).get("thread")
                            misses.append(f"{slug} {row['id']} ({row['area']} mm², {row['role']}, "
                                          f"ours OFF {_f(off_t)})")
                lines.append(f"| {slug} ({rep['width']:g}) | {row['id']} | {row['area']:.1f} | "
                             f"{row['min_dim_mm']} | {row['holes']} | {row['holder'] or '—'} | "
                             f"{row['role']} | {o.get('kind') or 'open'} | {_f(pro_t)} | "
                             f"{_f((row['ours'].get('off') or {}).get('thread'))} | {_f(ours_t)} | {ag} |")
        agree = sum(1 for x, y in pairs if x == y)
        lines += ["", f"**{agree} of {len(pairs)} readable rows agree; Cohen's kappa "
                      f"{_f(kappa(pairs), 3)}.** Misses: {', '.join(misses) or 'none'}."
                      + (f" Not run: {', '.join(skipped)}." if skipped else ""), ""]
    lines += ["## Registration and calibration", "",
              "| job | width | garment | reg IoU | flip | calib (pro thread on our sewn regions) |",
              "|---|---|---|---|---|---|"]
    for slug, rep in out.items():
        lines.append(f"| {slug} | {rep['width']:g} | {rep['garment']} | {rep['reg']['iou']:.3f} | "
                     f"{rep['reg']['flip_y']} | {_f(rep['calib'], 3)} |")
    lines += ["", "## Stitches / trims (DST), white blocks", "",
              "| job | arm | stitches | trims | cpu s | white blocks (rgb) | on top | under | white st | "
              "white < 1 mm | white median mm | white trims |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for slug, rep in out.items():
        for arm in ["pro"] + rep["arms"]:
            t = rep["totals"].get(arm) or {}
            b = rep["blocks"].get(arm) or {}
            lines.append(f"| {slug} | {arm} | {_f(t.get('stitches'))} | {_f(t.get('trims'))} | "
                         f"{_f(t.get('cpu_s'), 1)} | {b.get('blocks', '—')} {b.get('rgb') or ''} | "
                         f"{_f(b.get('on_top'))} | {b.get('under') or '—'} | {_f(b.get('stitches'))} | "
                         f"{_f(b.get('under_1mm'))} | {_f(b.get('median_mm'))} | {_f(b.get('trims'))} |")
    lines += ["", "## The letter-body faces (Becker): how they sew", "",
              "| job | side | face block (on top) | sewn under it | outline block | under outline | "
              "face block st / trims | rows | row angle (axial mean, top 5° bin, share) | "
              "fills in the face block | run points |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for slug, rep in out.items():
        fr = rep.get("faces")
        if not fr:
            continue
        for side in ["pro"] + rep["arms"]:
            c = fr.get(side)
            if not c:
                continue
            if not c.get("sewn"):
                lines.append(f"| {slug} | {side} | not sewn | | | | | | | | {c.get('run_points', '')} |")
                continue
            rw = c["rows"]
            fills = "; ".join(f"{x['verdict']} ax {x['dense_ax']} pitch {x['pitch']} st {x['stitch']}"
                              for x in c["fills"]) or "—"
            lines.append(f"| {slug} | {side} | {c['face_block']} ({c['on_top']}) | {c['under'] or '—'} | "
                         f"{c['outline_block']} | "
                         f"{c['under_outline']} | {c['face_block_stitches']:,} / {c['face_block_trims']} | "
                         f"{rw.get('rows')} | {rw.get('axial_mean_deg', '—')}, {rw.get('top_bin_deg', '—')}, "
                         f"{rw.get('top_bin_share', '—')} | {fills} | {c.get('run_points', '')} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return 0


# ----------------------------------------------------------------- render
def _box(rows_geoms, what: str, pad: float = 2.0):
    """A crop in the pro's frame: `faces` = the three leftmost letter bodies
    (BEC of BECKER), `band` = the left 40% of the keyline band."""
    if what == "faces":
        faces = sorted((g for role, g in rows_geoms if role == "letter body"),
                       key=lambda g: g.bounds[0])[:3]
        if not faces:
            raise SystemExit("no letter-body faces in this job")
        x0 = min(g.bounds[0] for g in faces); y0 = min(g.bounds[1] for g in faces)
        x1 = max(g.bounds[2] for g in faces); y1 = max(g.bounds[3] for g in faces)
        return x0 - pad, y0 - pad, x1 + pad, y1 + pad
    bands = [g for role, g in rows_geoms if role == "band"]
    if not bands:
        raise SystemExit("no keyline band in this job")
    b = max(bands, key=lambda g: g.area)
    x0, y0, x1, y1 = b.bounds
    return x0 - pad, y0 - pad, x0 + 0.4 * (x1 - x0), y1 + pad


def render_cmd(a) -> int:
    """OFF | ON | pro on one canvas: ours carried into the pro's frame by the
    same registration the table reads, the pro drawn from his PES when one
    sits beside the DST (thread colours; centred on the DST), else the DST."""
    import cv2
    import pystitch
    from shapely import affinity
    from digitizer_core import stitchviz
    from digitizer_core.adapter import pattern_to_design
    from tools import pro_pair as pp
    from tools.pro_parity import pairframe, prep_all

    jf = job_files(a.slug)
    got = _load(a.cache, a.slug, "off")
    if got is None:
        raise SystemExit(f"{a.slug}: no OFF cell; `run --only {a.slug}` first")
    off_cell, off_dst = got
    reg = registration(jf["pro"], off_dst)
    sides = []
    for arm in a.arms:
        got = _load(a.cache, a.slug, arm)
        if got is None:
            raise SystemExit(f"{a.slug} {arm}: not run")
        cell, dst = got
        pat = pairframe._read_pattern(dst)
        pat.threadlist = []
        for b in cell["blocks"]:
            t = pystitch.EmbThread()
            t.set_color(*b["rgb"])
            pat.add_thread(t)
        c = counts(read_stream(dst))
        sides.append((f"ours {arm}: {c['stitches']:,} st, {c['trims']} trims",
                      pattern_to_design(pat, name=arm, transform_mm=reg.apply_xy,
                                        fallback_colors=prep_all.GREYS)))
    pro_pat = pairframe._read_pattern(jf["pro"])
    pes = next((q for q in jf["pro"].parent.iterdir()
                if q.stem == jf["pro"].stem and q.suffix.lower() == ".pes"), None)
    if pes is not None:
        pes_pat = pairframe._read_pattern(pes)
        d0, p0 = pro_pat.extents(), pes_pat.extents()
        ox, oy = ((d0[0] + d0[2]) - (p0[0] + p0[2])) / 20.0, ((d0[1] + d0[3]) - (p0[1] + p0[3])) / 20.0
        pro_design = pattern_to_design(pes_pat, name="pro", transform_mm=lambda x, y: (x + ox, y + oy),
                                       fallback_colors=prep_all.GREYS)
    else:
        pro_design = pattern_to_design(pro_pat, name="pro", fallback_colors=prep_all.GREYS)
    pc = counts(read_stream(jf["pro"]))
    sides.append((f"pro: {pc['stitches']:,} st, {pc['trims']} trims (DST)", pro_design))

    box = None
    if a.region:
        r = next((r for r in off_cell["regions"] if r["id"] == a.region), None)
        if r is None:
            raise SystemExit(f"{a.slug}: no region {a.region}")
        x0, y0, x1, y1 = affinity.affine_transform(_geom(r, off_cell["dst_offset_mm"]),
                                                   reg.matrix()).bounds
        box = (x0 - 4.0, y0 - 4.0, x1 + 4.0, y1 + 4.0)
    elif a.what != "whole":
        rg = [(_role(r), affinity.affine_transform(_geom(r, off_cell["dst_offset_mm"]), reg.matrix()))
              for r in off_cell["regions"] if r["meta"].get("enclosed_background")]
        box = _box(rg, a.what)
    ppm = a.ppm or (12.0 if box is None else 30.0)
    frame = pairframe.frame_for([d for _, d in sides], ppm)
    tiles = []
    for label, d in sides:
        img = stitchviz.render_design(pairframe.pin_frame(d, frame.bounds_units), px_per_mm=ppm,
                                      fabric_bgr=GROUND_BGR)
        if box is not None:
            (px0, py0), (px1, py1) = frame.to_px(box[0], box[1]), frame.to_px(box[2], box[3])
            img = img[max(0, int(py0)):int(py1), max(0, int(px0)):int(px1)]
        tiles.append(pp._label(img, label))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), pp._hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(out, f"reg iou {reg.iou:.3f}", f"box {box}" if box else "whole")
    return 0


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.enclosed_pro_census",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    arms = lambda s: [x for x in s.split(",") if x]  # noqa: E731

    p = sub.add_parser("run", help="digitize every job x arm not cached yet")
    p.add_argument("--only", nargs="*")
    p.add_argument("--arms", type=arms, default=["off", "white", "on", "on_nobfo"])
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--cache", type=Path, default=argparse.SUPPRESS)

    p = sub.add_parser("one", help="one cell (what run spawns)")
    p.add_argument("slug")
    p.add_argument("arm", choices=list(ARMS))
    p.add_argument("--width", type=float)
    p.add_argument("--garment")
    p.add_argument("--cache", type=Path, default=argparse.SUPPRESS)

    p = sub.add_parser("time", help="unprofiled wall time, one fresh process per arm")
    p.add_argument("slug")
    p.add_argument("--width", type=float)
    p.add_argument("--garment")
    p.add_argument("--arms", type=arms, default=["off", "on"])
    p.add_argument("--cache", type=Path, default=argparse.SUPPRESS)

    p = sub.add_parser("render", help="OFF | ON | pro, registered, one canvas")
    p.add_argument("slug")
    p.add_argument("--what", choices=["whole", "faces", "band"], default="whole")
    p.add_argument("--region", help="crop round this region of the OFF cell instead (4 mm pad)")
    p.add_argument("--arms", type=arms, default=["off", "on"])
    p.add_argument("--ppm", type=float)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cache", type=Path, default=argparse.SUPPRESS)

    p = sub.add_parser("table", help="analyse the cache")
    p.add_argument("--json", type=Path)
    p.add_argument("--md", type=Path)
    p.add_argument("--cache", type=Path, default=argparse.SUPPRESS)

    a = ap.parse_args(argv)
    if a.cmd == "run":
        return run_cmd(a)
    if a.cmd == "one":
        out = digitize_cell(a.slug, a.arm, a.cache, a.width, a.garment)
        print(out)
        return 0
    if a.cmd == "time":
        return time_cmd(a)
    if a.cmd == "render":
        return render_cmd(a)
    return table_cmd(a)


if __name__ == "__main__":
    raise SystemExit(main())
