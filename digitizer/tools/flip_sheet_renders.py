#!/usr/bin/env python
"""flip_sheet_renders: one page Kent flips layout flags from -- OFF | ON | pro.

WHAT IT IS FOR. Kent ruled 2026-10-22 that stitch LAYOUT is judged in the
preview and only pull weight and compensation need fabric. So every parked
flag that moves where stitches go is decided from pictures beside the
professional's file for the same job, not from a sew-out. This tool makes
that page: for each flag, on each paired fixture, the same crop three ways
at a zoom where single stitches show, with the crop chosen where the flag
actually changes something, and under it the stitch count, the trim count
and one number the flag is about -- for OFF, ON and the pro.

    .venv/Scripts/python -m tools.flip_sheet_renders run [--flags A B] [--fixtures S ...]
        [--engine DIR] [--cache DIR] [--jobs 3]
    .venv/Scripts/python -m tools.flip_sheet_renders report [--out DOCS_MD] [--renders DIR]

HOW. `run` digitizes each fixture the Studio's way (`tools.pro_pair.digitize`,
the hat preset at the pro's width) once OFF and once per flag ON, writes
each as a DST (`digitizer_core.export.write_dst`, the file a customer gets)
and caches it with the plan's design and run roles under `--cache`
(resumable: a cell that exists is not re-run). `report` reads every DST --
ours and the pro's -- with ONE reader per number (pystitch), diffs OFF and
ON by needle-down points (0.05 mm grid), slides a 18 x 11 mm window over the
points that differ and crops all three renders there, 40 px/mm. A cell whose
diff is zero prints "no change" with the count that proves it instead of
three identical pictures.

A flag that is not on `main` yet is run from its PR branch: pass `--engine
DIR` (a checkout root) and that checkout's `digitizer_core` is imported in
place of this one; the cache records the engine's commit, and the OFF cell
is cached PER ENGINE so a branch flag is diffed against its own OFF.

NUMBERS. Every metric is read off the DST so OFF, ON and the pro are read
by the same rule; where a number needs the plan's run roles (edge-cap rings)
the pro's cell says so. The readers are the repo's own: `tools.
pro_fill_underlay` (fills BARE), `tools.trim_classes` (hops under later
thread), `tools.small_text_columns` (letter pieces), and -- on the branch
that carries it -- `tools.pro_satin_underlay` (short columns bare).

Nothing here changes an engine default; the flips are Kent's.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402

DATE = "2026-10-23"
PPM = 40.0                  # crop renders: 0.4 mm thread = 16 px
PAD_MM = 2.0                # stitchviz.render_design's pad
WINDOW_MM = (18.0, 11.0)    # the crop, mm (w, h)
GRID_MM = 0.05              # needle-point grid for the OFF/ON diff
LOCK_LEG_MM = 1.0           # a lock's legs are at most this
DEFAULT_CACHE = DIGITIZER / "debug_out" / "flip_sheet"
DEFAULT_DOC = DIGITIZER.parent / "docs" / f"flip-sheet-{DATE}.md"
DEFAULT_RENDERS = DIGITIZER.parent / "docs" / "renders" / f"flip-sheet-{DATE}"

#: (slug in `tools.border_census.PAIRS`, width mm or None for the pro's).
#: Fremont at 92.5: Kent's own job width (`fremont_triage.KENT_WIDTH_MM`),
#: 0.1 mm under the pro's extents.
FIXTURES: list[tuple[str, float | None]] = [
    ("hotel_fremont_hat", 92.5),
    ("becker_hat_small", None),
    ("mfab_hat", None),
]

#: The flags. `sets` is laid over the Studio request (`--set` in pro_pair);
#: `metric` names a reader below; `about` is the column heading; `pr` the PR
#: that built it. Add a row here and the next `run`/`report` carries it.
FLAGS: dict[str, dict] = {
    "fill_turn_slant": {
        "sets": {"fill_turn_slant": True}, "metric": "sub_half_mm",
        "about": "stitches under 0.5 mm", "pr": 1036,
        "note": "PR #1036 was RED on CI when rendered (tests/test_cut_every_jump.py "
                "test_off_is_byte_identical_to_base[earlier-0], an OFF md5 pin stale after main "
                "moved); rendered from its branch, diffed against that branch's own OFF."},
    "fill_underlay_cross": {
        "sets": {"fill_underlay_cross": True}, "metric": "fill_underlay", "xray": True,
        "about": "underlay read under each fill (verdict: fills)", "pr": 1033},
    "cut_every_jump": {
        "sets": {"cut_every_jump": True}, "metric": "uncut_jumps",
        "about": "uncut jumps", "pr": 1035,
        "note": "PR #1035 was RED on CI when rendered (the same OFF md5 pin as #1036); rendered "
                "from its branch, diffed against that branch's own OFF."},
    "sew_enclosed_white": {
        "sets": {"sew_enclosed_white": True}, "metric": "white_stitches",
        "about": "stitches in white thread", "pr": 1031},
    "trim_bury_under_later": {
        "sets": {"trim_bury_under_later": True}, "metric": "under_later",
        "about": "trims whose hop later thread covers", "pr": 1030},
    "compact_solids_satin": {
        "sets": {"compact_solids_satin": True}, "metric": "rings",
        "about": "edge-cap rings (plan roles)", "pr": 1040},
    "small_solids_satin": {
        "sets": {"small_solids_satin": True}, "metric": "rings",
        "about": "edge-cap rings (plan roles)", "pr": 1023},
    "tie_in_off": {
        "sets": {"tie_in_off": True}, "metric": "locks",
        "about": "run starts that lock", "pr": 1042},
    "satin_underlay_short_columns": {
        "sets": {"satin_underlay_short_columns": True}, "metric": "short_bare", "xray": True,
        "about": "satin columns under 5 mm sewn bare", "pr": 1044},
    "small_text_set": {
        "sets": {"small_text_cap_mm": 4.0, "small_text_cap_max_width_scale": 1.05,
                 "small_text_cap_min_stroke_mm": 0.85, "small_text_cap_letter_gap_mm": 0.25,
                 "small_text_cap_bold_scale": 1.45, "lettering_columns_small_bold": True},
        "metric": "letter_height", "about": "median small-letter height, mm", "pr": 1029},
}


# ------------------------------------------------------------------ engine
def engine_root() -> Path:
    """The checkout whose `digitizer_core` is imported: `--engine`'s, else ours."""
    return Path(os.environ.get("FLIP_SHEET_ENGINE") or DIGITIZER.parent)


def use_engine(root: Path | None) -> None:
    if root is None:
        return
    d = Path(root).resolve() / "digitizer"
    if not (d / "digitizer_core").is_dir():
        raise SystemExit(f"--engine {root}: no digitizer/digitizer_core there")
    os.environ["FLIP_SHEET_ENGINE"] = str(d.parent)
    sys.path.insert(0, str(d))
    for name in list(sys.modules):
        if name.split(".")[0] in ("digitizer_core", "digitizer_service", "tools"):
            del sys.modules[name]


def engine_sha(root: Path | None = None) -> str:
    root = Path(root or engine_root())
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


# ---------------------------------------------------------------- fixtures
def fixture_files(slug: str) -> dict:
    """pro DST (preferred over PES: the PES reader reports a TRIM at every
    jump), pro PES if any (thread colours), art, garment, width."""
    from tools import border_census as bc
    from tools import pro_pair as pp
    row = next(r for r in bc.PAIRS if r[0] == slug)
    pro, art = bc.find_pair(*row[:3])
    if pro is None or art is None:
        raise SystemExit(f"{slug}: missing {'pro' if pro is None else 'art'} file")
    pes = pro if pro.suffix.lower() == ".pes" else None
    dst = bc.find(row[1][:-4] + ".DST") if row[1].upper().endswith(".PES") else pro
    width = dict(FIXTURES).get(slug)
    if width is None:
        width = pp.pro_counts(dst or pro)["width_mm"]
    return {"slug": slug, "garment": row[3], "art": Path(art), "pro_dst": Path(dst or pro),
            "pro_pes": Path(pes) if pes else None, "width_mm": float(width)}


# --------------------------------------------------------------------- run
def cell_dir(cache: Path, slug: str, arm: str, sha: str) -> Path:
    return cache / slug / (f"{arm}__{sha}" if arm == "off" else arm)


def digitize_cell(slug: str, arm: str, cache: Path, engine: str | None) -> dict:
    """One (fixture, arm): ours.dst + design.json + runs.json + stats.json."""
    use_engine(Path(engine) if engine else None)
    from tools import pro_pair as pp
    from digitizer_core.export import write_dst
    sha = engine_sha()
    out = cell_dir(cache, slug, arm, sha)
    if (out / "stats.json").exists():
        return json.loads((out / "stats.json").read_text(encoding="utf-8"))
    fx = fixture_files(slug)
    sets = {} if arm == "off" else dict(FLAGS[arm]["sets"])
    d = pp.digitize(fx["art"], fx["width_mm"], fx["garment"], sets)
    out.mkdir(parents=True, exist_ok=True)
    write_dst(d.plan, out / "ours.dst")
    (out / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
    runs = []
    for bi, (blk, run) in enumerate(d.plan.iter_runs()):
        pts = run.points or []
        runs.append({"shape": str(run.shape_id), "kind": str(run.kind),
                     "role": str(getattr(run, "role", "") or ""), "n": len(pts),
                     "jump": bool(getattr(run, "jump", False)), "trim": bool(getattr(run, "trim", False)),
                     "rgb": list(blk.rgb)})
    (out / "runs.json").write_text(json.dumps(runs), encoding="utf-8")
    stats = {"slug": slug, "arm": arm, "sets": sets, "engine": sha,
             "engine_root": str(engine_root()), "width_mm": fx["width_mm"],
             "garment": fx["garment"], "secs": round(d.secs, 1),
             "plan_stitches": d.plan.stats.stitch_count, "plan_trims": d.plan.stats.trims}
    (out / "stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


def _job(args):
    slug, arm, cache, engine = args
    try:
        s = digitize_cell(slug, arm, Path(cache), engine)
        return f"{slug}/{arm}: {s['plan_stitches']} st, {s['plan_trims']} trims, {s['secs']} s [{s['engine']}]"
    except Exception as e:  # noqa: BLE001 -- one cell failing must not sink the pass
        return f"{slug}/{arm}: FAILED {type(e).__name__}: {e}"


def run_cmd(a) -> int:
    flags = a.flags or list(FLAGS)
    bad = [f for f in flags if f not in FLAGS]
    if bad:
        raise SystemExit(f"unknown flags: {bad}; known: {list(FLAGS)}")
    slugs = a.fixtures or [s for s, _ in FIXTURES]
    jobs = [(s, arm, str(a.cache), a.engine) for s in slugs for arm in ["off", *flags]]
    if a.jobs <= 1:
        for j in jobs:
            print(_job(j), flush=True)
    else:
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            for line in ex.map(_job, jobs):
                print(line, flush=True)
    return 0


# ----------------------------------------------------------------- readers
def read_stream(path: Path) -> list[tuple[float, float, int]]:
    """(x mm, y mm, command) per record, as pystitch reads the file."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    m = pystitch.COMMAND_MASK
    return [(x / 10.0, y / 10.0, c & m) for x, y, c in pat.stitches]


def counts(stream) -> dict:
    import pystitch
    cmds = [c for *_, c in stream]
    return {"stitches": sum(1 for c in cmds if c == pystitch.STITCH),
            "trims": sum(1 for c in cmds if c == pystitch.TRIM)}


def needle_points(stream) -> list[tuple[float, float]]:
    import pystitch
    return [(x, y) for x, y, c in stream if c == pystitch.STITCH]


def sub_half_mm(stream, _fx, _cell) -> int:
    """Needle-to-needle stitches under 0.5 mm (a fill's straight row turns)."""
    import pystitch
    n, prev = 0, None
    for x, y, c in stream:
        if c == pystitch.STITCH:
            if prev is not None and math.dist(prev, (x, y)) < 0.5:
                n += 1
            prev = (x, y)
        else:
            prev = None if c in (pystitch.TRIM, pystitch.COLOR_CHANGE) else prev
    return n


def fill_underlay(_stream, _fx, cell) -> str:
    """What `tools.pro_fill_underlay` reads under each fill: verdict counts
    (CROSS / DIAG / PARALLEL / MIXEDANG / RUNONLY / BARE)."""
    from collections import Counter
    from tools import pro_fill_underlay as pfu
    c = Counter(v for v, _ in pfu.classify_file(cell["dst"]))
    return " ".join(f"{k} {n}" for k, n in sorted(c.items())) or "no fills read"


def uncut_jumps(stream, _fx, _cell) -> int:
    """Needle-up hops (one or more JUMP records) between two penetrations
    with no TRIM or colour change around them."""
    import pystitch
    n, in_jump, cut = 0, False, False
    for _x, _y, c in stream:
        if c == pystitch.JUMP:
            in_jump = True
        elif c in (pystitch.TRIM, pystitch.COLOR_CHANGE):
            cut = True
        elif c == pystitch.STITCH:
            if in_jump and not cut:
                n += 1
            in_jump, cut = False, False
    return n


def white_stitches(_stream, fx, cell) -> str:
    """Stitches sewn in a near-white thread, from the file's own colours;
    a DST carries none."""
    design = cell.get("design")
    if design is None:
        return "n/a (no thread colours)"
    colors = design.get("colors") or []
    n, ci = 0, 0
    for s in design.get("stitches") or []:
        t = s.get("type")
        if t == "color":
            ci += 1
        elif t == "stitch" and ci < len(colors):
            c = colors[ci]
            if min(c.get("r", 0), c.get("g", 0), c.get("b", 0)) >= 230:
                n += 1
    return str(n)


def under_later(_stream, _fx, cell) -> int:
    from tools import trim_classes as tc
    return sum(1 for r in tc.classify(cell["dst"]) if r.get("cls") == "under_later")


def rings(_stream, _fx, cell) -> str:
    runs = cell.get("runs")
    if runs is None:
        return "n/a (DST has no roles)"
    return str(sum(1 for r in runs if r["role"] == "edge_cap"))


def locks(stream, _fx, _cell) -> int:
    """Run starts (after a trim, colour change or jump) whose first three
    stitches are all under LOCK_LEG_MM with a reversal among them."""
    import pystitch
    n, head, fresh = 0, [], True
    for x, y, c in stream:
        if c == pystitch.STITCH:
            head.append((x, y))
            if fresh and len(head) == 4:
                legs = [math.dist(a, b) for a, b in zip(head, head[1:])]
                vecs = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(head, head[1:])]
                rev = any(_dot(u, v) < 0 for u, v in zip(vecs, vecs[1:]))
                if all(l <= LOCK_LEG_MM for l in legs) and rev:
                    n += 1
                fresh = False
        elif c in (pystitch.TRIM, pystitch.COLOR_CHANGE, pystitch.JUMP):
            head, fresh = [], True
    return n


def _dot(u, v) -> float:
    return u[0] * v[0] + u[1] * v[1]


def _engine_module(name: str, cell: dict):
    """`tools.<name>` from this checkout, else from the engine the cell was
    run on (a branch reader the report's checkout lacks yet)."""
    import importlib
    import importlib.util
    try:
        return importlib.import_module(f"tools.{name}")
    except ImportError:
        pass
    root = cell.get("engine_root")
    path = Path(root) / "digitizer" / "tools" / f"{name}.py" if root else None
    if path is None or not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"_engine_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def short_bare(_stream, _fx, cell) -> str:
    psu = _engine_module("pro_satin_underlay", cell)
    if psu is None:
        return "n/a (reader not on this engine)"
    rows = psu.read_columns(psu.blocks_from_file(Path(cell["dst"])), 6)
    short = [r for r in rows if r["length"] < 5.0]
    if not short:
        return "0 short columns"
    sb = sum(1 for r in short if r["bare"])
    return f"{100.0 * sb / len(short):.1f}% ({sb} of {len(short)})"


def letter_height(_stream, _fx, cell) -> str:
    """Median height of letter-sized pieces (0.8-6 mm tall), the way
    `small_text_columns` cuts a file into letters."""
    from tools import small_text_columns as stc
    pcs = stc.pieces(stc.read_blocks(cell["dst"]))
    hs = sorted(p["y1"] - p["y0"] for p in pcs if 0.8 <= p["y1"] - p["y0"] <= 6.0)
    if not hs:
        return "no small pieces"
    return f"{hs[len(hs) // 2]:.2f} ({len(hs)} pieces)"


METRICS = {"sub_half_mm": sub_half_mm, "fill_underlay": fill_underlay, "uncut_jumps": uncut_jumps,
           "white_stitches": white_stitches, "under_later": under_later, "rings": rings,
           "locks": locks, "short_bare": short_bare, "letter_height": letter_height}


# ------------------------------------------------------------------- diff
def _grid(points):
    from collections import Counter
    return Counter((round(x / GRID_MM), round(y / GRID_MM)) for x, y in points)


def diff_points(off_pts, on_pts) -> list[tuple[float, float]]:
    """Grid cells whose needle COUNT differs, one entry per stitch of
    difference. A multiset, not a set: a lock walks over the run's own
    stations, so dropping it removes stitches without moving a point."""
    a, b = _grid(off_pts), _grid(on_pts)
    out = []
    for key in set(a) | set(b):
        n = abs(a.get(key, 0) - b.get(key, 0))
        out += [(key[0] * GRID_MM, key[1] * GRID_MM)] * n
    return out


def best_window(pts, w=WINDOW_MM[0], h=WINDOW_MM[1]) -> tuple[float, float, float, float] | None:
    """The w x h mm window holding the most changed points (1 mm steps)."""
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    best, bx, by = -1, x0, y0
    sx = [x0 + i for i in range(int(max(1, x1 - x0 - w + 2)))]
    sy = [y0 + j for j in range(int(max(1, y1 - y0 - h + 2)))]
    for cx in sx:
        for cy in sy:
            n = sum(1 for p in pts if cx <= p[0] <= cx + w and cy <= p[1] <= cy + h)
            if n > best:
                best, bx, by = n, cx, cy
    return (bx, by, bx + w, by + h)


# ---------------------------------------------------------------- renders
def _extents(stream):
    pts = needle_points(stream)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _design_frame(design: dict):
    """(x0 mm, y_top mm, w, h) of the render's drawn box in PLAN mm (y-down)."""
    from digitizer_core import stitchviz
    x0, x1, y0, y1 = stitchviz._bounds(design.get("stitches") or [])
    return x0 / 10.0, -y1 / 10.0, (x1 - x0) / 10.0, (y1 - y0) / 10.0


def render_crop(design: dict, box_mm, ppm=PPM):
    """`box_mm` in plan mm (y-down, absolute) -> BGR crop of the render."""
    from digitizer_core import stitchviz
    img = stitchviz.render_design(design, px_per_mm=ppm)
    fx, fy, _w, _h = _design_frame(design)
    x0, y0, x1, y1 = box_mm
    px = (int(round((x0 - fx + PAD_MM) * ppm)), int(round((y0 - fy + PAD_MM) * ppm)),
          int(round((x1 - fx + PAD_MM) * ppm)), int(round((y1 - fy + PAD_MM) * ppm)))
    h, w = img.shape[:2]
    return img[max(0, px[1]):max(1, min(h, px[3])), max(0, px[0]):max(1, min(w, px[2]))]


JPEG = [1, 90]   # cv2.IMWRITE_JPEG_QUALITY: 112 tiles at 40 px/mm are 18 MB as PNG, 3 as JPEG


def _write(path, img):
    import cv2
    cv2.imwrite(str(path), img, JPEG)


def _label(img, text):
    import cv2
    im = img.copy()
    cv2.rectangle(im, (0, 0), (im.shape[1], 30), (255, 255, 255), -1)
    cv2.putText(im, text, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2, cv2.LINE_AA)
    return im


def reversed_design(design: dict) -> dict:
    """The design with its sewing order reversed, block by block, so what was
    sewn FIRST (underlay) draws last, on top. A picture of what lies under
    the top thread; the renderer itself is untouched."""
    blocks, cur = [], []
    for s in design.get("stitches") or []:
        if s.get("type") == "color":
            blocks.append(cur)
            cur = []
        else:
            cur.append(s)
    blocks.append(cur)
    colors = list(design.get("colors") or [])
    out = []
    for i, blk in reversed(list(enumerate(blocks))):
        if out:
            out.append({**(out[-1]), "type": "color"})
        out += list(reversed(blk))
    return {**design, "stitches": out, "colors": list(reversed(colors[:len(blocks)])) or colors}


def where_image(design: dict, box_mm, ppm: float = 8.0):
    """The whole OFF design small, with the crop window drawn in red."""
    import cv2
    from digitizer_core import stitchviz
    img = stitchviz.render_design(design, px_per_mm=ppm).copy()
    fx, fy, _w, _h = _design_frame(design)
    x0, y0, x1, y1 = box_mm
    p0 = (int(round((x0 - fx + PAD_MM) * ppm)), int(round((y0 - fy + PAD_MM) * ppm)))
    p1 = (int(round((x1 - fx + PAD_MM) * ppm)), int(round((y1 - fy + PAD_MM) * ppm)))
    cv2.rectangle(img, p0, p1, (0, 0, 255), 2)
    return img


def pro_box(design_pro: dict, ours_frame, box_mm):
    """The same window on the pro's render: ours' box as fractions of our
    drawn extents, applied to the pro's (no registration, as pro_pair)."""
    fx, fy, fw, fh = ours_frame
    px, py, pw, ph = _design_frame(design_pro)
    x0, y0, x1, y1 = box_mm
    sx, sy = pw / fw, ph / fh
    return (px + (x0 - fx) * sx, py + (y0 - fy) * sy, px + (x1 - fx) * sx, py + (y1 - fy) * sy)


# ------------------------------------------------------------------ report
def load_cell(path: Path) -> dict:
    cell = {"dst": path / "ours.dst",
            "stats": json.loads((path / "stats.json").read_text(encoding="utf-8")),
            "design": json.loads((path / "design.json").read_text(encoding="utf-8")),
            "runs": json.loads((path / "runs.json").read_text(encoding="utf-8"))}
    cell["stream"] = read_stream(cell["dst"])
    return cell


def pro_cell(fx: dict) -> dict:
    from tools.pro_parity import pairframe
    cell = {"dst": fx["pro_dst"], "stream": read_stream(fx["pro_dst"]), "runs": None}
    # counts from the DST; the picture from the PES when there is one, so the
    # pro's crop draws in his thread colours rather than the grey fallback
    cell["design"] = (pairframe.design_for(fx["pro_pes"], None, None, fx["slug"])
                      if fx["pro_pes"] else None)
    cell["design_render"] = cell["design"] or pairframe.design_for(fx["pro_dst"], None, None, fx["slug"])
    return cell


def measure(flag: str, cell: dict, fx: dict) -> dict:
    out = counts(cell["stream"])
    fn = METRICS[FLAGS[flag]["metric"]]
    try:
        out["about"] = fn(cell["stream"], fx, cell)
    except Exception as e:  # noqa: BLE001 -- a reader that cannot read a file is a cell, not a crash
        out["about"] = f"reader failed: {type(e).__name__}"
    return out


def build_rows(cache: Path, renders: Path, flags: list[str], slugs: list[str]) -> list[dict]:
    import cv2
    renders.mkdir(parents=True, exist_ok=True)
    rows = []
    pros: dict[str, tuple[dict, dict]] = {}
    for slug in slugs:
        fx = fixture_files(slug)
        pros[slug] = (fx, pro_cell(fx))
    for flag in flags:
        for slug in slugs:
            fx, pro = pros[slug]
            on_dir = cache / slug / flag
            row = {"flag": flag, "fixture": slug, "width_mm": fx["width_mm"], "pr": FLAGS[flag]["pr"],
                   "about": FLAGS[flag]["about"], "sets": FLAGS[flag]["sets"],
                   "note": FLAGS[flag].get("note", "")}
            if not (on_dir / "stats.json").exists():
                row["status"] = "not run"
                rows.append(row)
                continue
            on = load_cell(on_dir)
            sha = on["stats"]["engine"]
            off_dir = cell_dir(cache, slug, "off", sha)
            if not (off_dir / "stats.json").exists():
                row["status"] = f"OFF cell missing for engine {sha}"
                rows.append(row)
                continue
            off = load_cell(off_dir)
            row["engine"] = sha
            row["engine_root"] = on["stats"]["engine_root"]
            for c in (off, on, pro):
                c["engine_root"] = row["engine_root"]
            row["off"] = measure(flag, off, fx)
            row["on"] = measure(flag, on, fx)
            row["pro"] = measure(flag, pro, fx)
            row["pro_file"] = fx["pro_dst"].name
            d = diff_points(needle_points(off["stream"]), needle_points(on["stream"]))
            row["diff"] = len(d)
            same_file = off["dst"].read_bytes() == on["dst"].read_bytes()
            row["byte_identical"] = same_file
            if not d:
                row["status"] = "no change"
                rows.append(row)
                continue
            box = best_window(d)
            row["box_mm"] = [round(v, 1) for v in box]
            row["in_window"] = sum(1 for p in d if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3])
            frame = _design_frame(off["design"])
            pbox = pro_box(pro["design_render"], frame, box)
            tiles = {"off": render_crop(off["design"], box), "on": render_crop(on["design"], box),
                     "pro": render_crop(pro["design_render"], pbox)}
            row["images"] = {}
            for side, img in tiles.items():
                m = row[side]
                name = f"{flag}__{slug}__{side}.jpg"
                _write(renders / name, _label(img, f"{side.upper()}: {m['stitches']} st, {m['trims']} tr"))
                row["images"][side] = name
            if FLAGS[flag].get("xray"):
                xr = {"off": render_crop(reversed_design(off["design"]), box),
                      "on": render_crop(reversed_design(on["design"]), box),
                      "pro": render_crop(reversed_design(pro["design_render"]), pbox)}
                for side, img in xr.items():
                    name = f"{flag}__{slug}__{side}_xray.jpg"
                    _write(renders / name, _label(img, f"{side.upper()} x-ray: first-sewn on top"))
                    row["images"][side + "_xray"] = name
            name = f"{flag}__{slug}__where.jpg"
            _write(renders / name, where_image(off["design"], box))
            row["images"]["where"] = name
            row["status"] = "rendered"
            rows.append(row)
            print(f"{flag}/{slug}: {len(d)} points differ, window {row['box_mm']}", flush=True)
    return rows


def _fmt(m: dict | None) -> str:
    return "-" if m is None else f"{m['stitches']:,} st / {m['trims']} tr / {m['about']}"


def markdown(rows: list[dict], renders: Path, doc: Path) -> str:
    rel = os.path.relpath(renders, doc.parent).replace("\\", "/")
    lines = [f"# Flip sheet {DATE}: OFF | ON | pro, one crop per flag and fixture", "",
             "Kent's ruling 2026-10-22: stitch layout is judged in the preview; only pull and "
             "comp need fabric. Every row here is a layout flag built OFF, rendered where it "
             "changes stitches, beside the professional's file for the same job. The flips are "
             "Kent's; nothing in this PR changes a default.", "",
             f"Open `{rel}/index.html` for the pictures side by side. Regenerate with "
             "`python -m tools.flip_sheet_renders run` then `report` (see the tool's docstring; "
             "a flag not on main runs with `--engine <checkout>`).", "",
             "Each cell: stitches / trims / the number the flag is about. Crops are 18 x 11 mm at "
             "40 px/mm, placed on the window holding the most changed needle points (OFF vs ON, "
             "0.05 mm grid); the pro's crop is the same window as a fraction of his extents, no "
             "registration. The hat preset at the pro's width (Fremont at Kent's 92.5).", "",
             "| flag (PR) | fixture | engine | OFF | ON | pro | changed points | crop |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tag = f"`{r['flag']}` (#{r['pr']})"
        if r.get("status") in ("not run", None) or r.get("status", "").startswith("OFF cell"):
            lines.append(f"| {tag} | {r['fixture']} | - | - | - | - | {r.get('status')} | - |")
            continue
        if r["status"] == "no change":
            why = "byte-identical DST" if r["byte_identical"] else "0 needle points differ"
            lines.append(f"| {tag} | {r['fixture']} | {r['engine']} | {_fmt(r['off'])} | {_fmt(r['on'])} | "
                         f"{_fmt(r['pro'])} | **no change** ({why}) | - |")
            continue
        im = r["images"]
        crop = " ".join(f"[{s}]({rel}/{im[s]})" for s in im)
        lines.append(f"| {tag} | {r['fixture']} | {r['engine']} | {_fmt(r['off'])} | {_fmt(r['on'])} | "
                     f"{_fmt(r['pro'])} | {r['diff']:,} ({r['in_window']:,} in crop) | {crop} |")
    lines += ["", "## What each number is", ""]
    for flag, spec in FLAGS.items():
        if any(r["flag"] == flag for r in rows):
            note = f" **{spec['note']}**" if spec.get("note") else ""
            lines.append(f"- `{flag}`: {spec['about']}. Sets `{json.dumps(spec['sets'])}`.{note}")
    lines += ["", "Readers: stitches and trims are pystitch records (the pro read as DST, never PES: "
              "the PES reader reports a TRIM at every jump). `stitches under 0.5 mm` are "
              "needle-to-needle. `fills read BARE` is `tools/pro_fill_underlay.py`. `uncut jumps` "
              "are needle-up hops with no TRIM or colour change round them. `white thread` reads "
              "the file's own colours (the pro's PES; a DST has none). `hops under later thread` "
              "is `tools/trim_classes.py`. `edge-cap rings` are plan run roles, so the pro has "
              "none. `run starts that lock`: the first three stitches after a cut, colour change "
              "or jump all at most 1.0 mm with a reversal. `short columns bare` is "
              "`tools/pro_satin_underlay.py` (PR #1044's branch). `letter height` is the median "
              "of `tools/small_text_columns.py`'s 0.8-6 mm pieces.", ""]
    return "\n".join(lines) + "\n"


def html(rows: list[dict]) -> str:
    out = ["<!doctype html><html><head><meta charset='utf-8'>",
           f"<title>Flip sheet {DATE}</title>",
           "<style>body{font-family:system-ui,sans-serif;margin:20px;background:#fafafa}"
           "h1{font-size:20px} .row{background:#fff;border:1px solid #ddd;border-radius:6px;"
           "padding:12px;margin:14px 0} .tiles{display:flex;gap:12px;flex-wrap:wrap}"
           ".tile{flex:1 1 300px} .tile img{width:100%;height:auto;border:1px solid #ccc;"
           "image-rendering:auto} .nums{font-size:14px;margin-top:6px} .nums b{display:inline-block;"
           "width:48px} code{background:#eee;padding:1px 4px;border-radius:3px}"
           ".nochange{color:#555} .flag{font-size:17px;margin:0 0 4px} .where{margin-top:10px;max-width:520px} .where img{width:100%;border:1px solid #ccc}</style></head><body>",
           f"<h1>Flip sheet {DATE} &mdash; OFF | ON | pro</h1>",
           "<p>Layout flags built OFF, each rendered where it changes stitches beside the "
           "professional's file for the same job (hat preset at the pro's width). 40 px/mm: a "
           "0.4 mm thread is 16 px. The flips are Kent's.</p>"]
    for r in rows:
        head = f"<p class='flag'><code>{r['flag']}</code> (PR #{r['pr']}) &middot; {r['fixture']} " \
               f"at {r['width_mm']} mm &middot; engine {r.get('engine', '-')}</p>"
        if r.get("note"):
            head += f"<p class='nochange'>&#9888; {r['note']}</p>"
        if r.get("status") not in ("rendered", "no change"):
            out.append(f"<div class='row'>{head}<p class='nochange'>{r.get('status')}</p></div>")
            continue
        nums = "".join(f"<div><b>{s.upper()}</b> {_fmt(r[s])}</div>" for s in ("off", "on", "pro"))
        if r["status"] == "no change":
            why = "byte-identical DST" if r["byte_identical"] else "0 needle points differ"
            out.append(f"<div class='row'>{head}<p class='nochange'><b>No change on this fixture</b> "
                       f"({why}).</p><div class='nums'>{nums}</div></div>")
            continue
        tiles = "".join(f"<div class='tile'><img src='{r['images'][s]}' alt='{s}'>"
                        f"<div class='nums'><b>{s.upper()}</b> {_fmt(r[s])}</div></div>"
                        for s in ("off", "on", "pro"))
        if "off_xray" in r["images"]:
            tiles += "".join(f"<div class='tile'><img src='{r['images'][s + '_xray']}' alt='{s} x-ray'>"
                             f"<div class='nums'><b>{s.upper()}</b> x-ray: sewing order reversed, "
                             f"underlay drawn on top</div></div>" for s in ("off", "on", "pro"))
        where = (f"<div class='where'><img src='{r['images']['where']}' alt='where'>"
                 f"<div class='nums'>where the crop sits (OFF, red box)</div></div>")
        out.append(f"<div class='row'>{head}<p>{r['about']}. {r['diff']:,} needle points differ, "
                   f"{r['in_window']:,} in this {WINDOW_MM[0]:g} x {WINDOW_MM[1]:g} mm crop at "
                   f"{r['box_mm']} mm (plan frame). Sets <code>{json.dumps(r['sets'])}</code>.</p>"
                   f"<div class='tiles'>{tiles}</div>{where}</div>")
    out.append("</body></html>")
    return "\n".join(out)


def report_cmd(a) -> int:
    flags = a.flags or list(FLAGS)
    slugs = a.fixtures or [s for s, _ in FIXTURES]
    rows = build_rows(Path(a.cache), Path(a.renders), flags, slugs)
    doc = Path(a.out)
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(markdown(rows, Path(a.renders), doc), encoding="utf-8")
    (Path(a.renders) / "index.html").write_text(html(rows), encoding="utf-8")
    (Path(a.renders) / "rows.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    print(f"wrote {doc} and {Path(a.renders) / 'index.html'} ({len(rows)} rows)")
    return 0


# -------------------------------------------------------------------- cli
def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.flip_sheet_renders",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "report"):
        p = sub.add_parser(name)
        p.add_argument("--flags", nargs="*", help="flag names (default: all in FLAGS)")
        p.add_argument("--fixtures", nargs="*", help="fixture slugs (default: FIXTURES)")
        p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
        if name == "run":
            p.add_argument("--engine", help="a checkout root whose digitizer_core runs the cells")
            p.add_argument("--jobs", type=int, default=3)
        else:
            p.add_argument("--out", type=Path, default=DEFAULT_DOC)
            p.add_argument("--renders", type=Path, default=DEFAULT_RENDERS)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    utf8_console(sys.stdout)
    a = parse_args(argv)
    return run_cmd(a) if a.cmd == "run" else report_cmd(a)


if __name__ == "__main__":
    raise SystemExit(main())
