"""apex_walk_census: what `lettering_columns_apex_cut` costs the Column lane's
WALK, per letter, OFF | ON (today's walk) | ON (new walk) | pro (2026-10-27).

WHAT IT IS FOR. `apex_cut` (#1088/#1090) sews an acute tip -- the M's V, a W's
three apexes, an N's diagonal into its stem, PROSEAL's A -- as ONE column cut
off its strokes along the cross. OFF's mitre made a path through the point;
a merged tip is a dead end for `columns.column_runs`' walk, and ON paid for
it in travel, trims and travel laid on satin already sewn. This reads that
cost on #1088's seven jobs, one rule on every arm:

  trims      trims inside the letter (a cut between two runs of the letter)
  travel     needle-down TRAVEL in the letter, mm
  on satin   TRAVEL laid on satin the letter has already sewn, mm; `tip` the
             part of it on a tip piece's own satin (the bar: 0)
  crosses    the satin cross against the line of text at 30 / 60 / 85% of
             the way from each crotch to its tip, degrees (axial mean of the
             crosses within 0.15 mm of the point -- `italic_cross.axial_mean`)

The pro's trims are TRIM records inside the letter's box (his beanie is PES
only: none), his crosses `letter_pieces` crosses mapped into his letter by
the two letters' sewn boxes. His travel is not read: a needle-down run in his
file is not labelled travel, and the reader that splits it would be a new
instrument (n/a).

    python -m tools.apex_walk_census gen  JOB         # stages 1-4 once, pickled (~minutes)
    python -m tools.apex_walk_census arm  JOB ARM     # stages 5-7 for one arm off the pickle
    python -m tools.apex_walk_census table [--out MD] # per letter, every arm in the cache
    python -m tools.apex_walk_census render --out DIR # OFF | ON | ON new | pro per letter
    python -m tools.apex_walk_census fixture --out testdata/apex_walk_letters.json
                                                      # the test's letters, sewn by THIS checkout

ARM is `off`, `on` (today's walk: run it from a main checkout or before the
walk change) or `on_new`; `on` and `on_new` set the flag, the engine decides
the walk. JOB is one of `JOBS`. The cache (`--cache`, default
`debug_out/apex_walk`, gitignored) holds client art's geometry: nothing in it
is committed. Each arm records its git head, its `process_time`, the gate-3
instruments on the WHOLE plan (`hairline_travel.scan` bare thread,
`travel_cover.travel_exposure` exposed travel), the DST md5, and every call
stage 7 made to the Column lane (polygon and keyword arguments) so the walk
can be iterated offline (`lane_letters`).

The config is the Studio's request at the pro's width (`pro_pair.request`),
main's defaults otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402

CACHE = DIGITIZER / "debug_out" / "apex_walk"
#: job -> border_census PAIRS slug (#1088's seven jobs)
JOBS = {
    "marine76": "becker_hat_small",
    "marine80": "becker_beanie",
    "marine96": "becker_lc_large",
    "marine102": "becker_hat_large",
    "mfab105": "mfab_hat",
    "mfab97": "mfab_lc",
    "proseal86": "proseal_hat",
}
ARMS = {"off": False, "on": True, "on_new": True}
#: the same arms run by the new engine where the walk must NOT move: OFF's md5
CHECKS = {"off_new": False}
REMBG_TIMEOUT_S = 900.0
PRIMARY_REMBG = "rembg_isolated/venv/Scripts/python.exe"
NEAR_MM = 0.45          # a cross reads a point it passes this close to: a pitch and a hair
#: a tip, read off the cut's own stations (`columns._APEX_END_WIDTHS`,
#: `_APEX_CLOSED`; a test holds them equal) -- here too so the census runs on
#: an engine from before the walk change (the ON-today arm). The walk also
#: takes a blunt tip whose far end the merge radius would join to another
#: stroke (`columns._apex_tip_columns`); the census reads the tips the cut
#: makes, the same on every arm
TIP_END_WIDTHS = 0.25
TIP_CLOSED = 0.5
FRACS = (0.3, 0.6, 0.85)
#: the letters with a merged tip, by job and shape id (the table's rows, the
#: test fixture's labels)
NAMES = {
    ("mfab105", "S62dc1339"): "N", ("mfab105", "Sdae7f60c"): "W", ("mfab105", "S4cd9766d"): "E",
    ("mfab105", "S6bd1705f"): "IN", ("mfab105", "Sd2b8aef9"): "4",
    ("mfab97", "S4339d1ab"): "W", ("mfab97", "S37071f19"): "N", ("mfab97", "Sdf884531"): "4",
    ("proseal86", "S29dcc431"): "A", ("proseal86", "Sef34328d"): "N",
    ("marine76", "Sd13db8a7"): "M", ("marine80", "Saee8fbe5"): "M",
    ("marine96", "S32b446a3"): "M", ("marine102", "Se264484b"): "M",
}
#: the jobs whose art is in the repo (Becker's, MFab's crops): the fixture's.
#: PROSEAL's art is on Kent's laptop only, and its letters stay off it
FIXTURE_JOBS = ("marine76", "marine80", "marine96", "marine102", "mfab105", "mfab97")


# ------------------------------------------------------------------ setup
def _primary_digitizer() -> Path:
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=DIGITIZER,
                            capture_output=True, text=True).stdout.strip()
    return Path(common).resolve().parent / "digitizer"


def _rembg_from_primary():
    """A lane has no rembg venv: point stage 1 at the primary checkout's."""
    from digitizer_core import stage1_photo_prep as s1
    if s1.background_removal_unavailable_reason() is None:
        return
    cand = _primary_digitizer() / PRIMARY_REMBG
    if cand.is_file():
        s1.REMBG_VENV_PYTHON = cand


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=DIGITIZER,
                          capture_output=True, text=True).stdout.strip()


def job_files(job: str):
    """(pro, art, garment, his width). MFab's art is on Drive only: without
    G: the committed crop the flip sheet uses (`flip_sheet_renders.ART_FALLBACK`),
    and `gen.json` says which file it was."""
    from tools import border_census as bc
    from tools import flip_sheet_renders as fs
    from tools import pro_pair as pp
    row = next(r for r in bc.PAIRS if r[0] == JOBS[job])
    pro, art = bc.find_pair(*row[:3])
    if art is None and fs.ART_FALLBACK.get(row[0], Path()).is_file():
        art = fs.ART_FALLBACK[row[0]]
    if pro is None or art is None:
        raise SystemExit(f"{job}: missing {'pro' if pro is None else 'art'} file")
    return pro, art, row[3], pp.pro_counts(pro)["width_mm"]


def config(width: float, garment: str, apex: bool):
    from digitizer_core import PipelineConfig
    from digitizer_service.app import _parse_config
    from tools import pro_pair as pp
    req = pp.request(width, garment, {"photo_prep_background_removal_timeout_s": REMBG_TIMEOUT_S})
    cfg = PipelineConfig(**_parse_config(json.dumps(req)))
    return replace(cfg, lettering_columns_apex_cut=apex)


# -------------------------------------------------------------------- gen
def gen(job: str, cache: Path) -> dict:
    """Stages 1-4 once (the expensive part, rembg included), pickled. The
    arms differ only in stage 7, so every arm plans off this one result."""
    from digitizer_core.pipeline import build_generation, finish_generation
    from digitizer_service.app import _decode as svc_decode
    _rembg_from_primary()
    pro, art, garment, width = job_files(job)
    cfg = config(width, garment, False)
    data = Path(art).read_bytes()
    t0, c0 = time.time(), time.process_time()
    g = build_generation(svc_decode(data), cfg, exif_source=data)
    result = finish_generation(g.fork(), cfg)
    out = cache / job
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.pkl").write_bytes(pickle.dumps(result))
    warns = [w.get("code") if isinstance(w, dict) else str(w) for w in getattr(result, "warnings", []) or []]
    info = {"job": job, "slug": JOBS[job], "pro": str(pro), "art": str(art), "garment": garment,
            "width_mm": width, "head": _head(), "wall_s": round(time.time() - t0, 1),
            "process_s": round(time.process_time() - c0, 1), "warnings": warns,
            "rembg_unavailable": any("BACKGROUND_REMOVAL_UNAVAILABLE" in str(w) for w in warns)}
    (out / "gen.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return info


# -------------------------------------------------------------------- arm
def _plan_md5(plan) -> str:
    h = hashlib.md5()
    for _b, r in plan.iter_runs():
        h.update(f"{r.kind}|{int(r.jump)}{int(r.trim)}|{r.shape_id}|".encode())
        for x, y in r.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def arm(job: str, name: str, cache: Path) -> dict:
    """Stages 5-7 for one arm off the pickled result: the plan's runs, the
    Column lane's inputs, the gate-3 instruments and the DST."""
    from digitizer_core import stage7_sequence as s7
    from digitizer_core.export import write_dst
    from digitizer_core.pipeline import plan_stitches
    from tools import hairline_travel, travel_cover
    out = cache / job
    info = json.loads((out / "gen.json").read_text(encoding="utf-8"))
    result = pickle.loads((out / "result.pkl").read_bytes())
    cfg = config(info["width_mm"], info["garment"], {**ARMS, **CHECKS}[name])
    calls = []
    real = s7.lettering_columns_shape

    def spy(poly, shape_id, **kw):
        runs, report = real(poly, shape_id, **kw)
        calls.append((poly, shape_id, kw, report))
        return runs, report
    s7.lettering_columns_shape = spy
    c0, t0 = time.process_time(), time.time()
    try:
        plan = plan_stitches(result, cfg)
    finally:
        s7.lettering_columns_shape = real
    secs = time.process_time() - c0
    wall = time.time() - t0
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    write_dst(plan, d / "ours.dst")
    letters = {}
    for poly, sid, kw, report in calls:
        row = {"exterior": [list(p) for p in poly.exterior.coords],
               "holes": [[list(p) for p in r.coords] for r in poly.interiors],
               "kw": {k: (list(v) if isinstance(v, tuple) else v)
                      for k, v in kw.items() if k != "counter_holes"},
               "report": {k: v for k, v in report.items() if isinstance(v, (int, float, bool))}}
        if kw.get("counter_holes"):
            row["counter_holes"] = [[list(p) for p in h.exterior.coords] for h in kw["counter_holes"]]
        letters[sid] = row
    (d / "letters.json").write_text(json.dumps(letters), encoding="utf-8")
    runs = [{"sid": str(r.shape_id), "kind": str(r.kind), "jump": bool(r.jump), "trim": bool(r.trim),
             "pts": [[round(x, 4), round(y, 4)] for x, y in r.points]} for _b, r in plan.iter_runs()]
    (d / "runs.json").write_text(json.dumps(runs), encoding="utf-8")
    bare = hairline_travel.scan(plan)
    expo = travel_cover.travel_exposure(plan)
    meta = {"job": job, "arm": name, "head": _head(), "apex_cut": {**ARMS, **CHECKS}[name],
            "process_s": round(secs, 1), "wall_s": round(wall, 1),
            "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
            "plan_md5": _plan_md5(plan),
            "dst_md5": hashlib.md5((d / "ours.dst").read_bytes()).hexdigest(),
            "thread_bare_mm": round(bare["thread"], 3), "flight_bare_mm": round(bare["flight"], 3),
            "travel_mm": round(expo["travel_mm"], 3), "exposed_mm": round(expo["exposed_mm"], 3),
            "worst_exposed_leg_mm": round(expo["worst_leg_mm"], 3),
            "lane_letters": len(letters), "rembg_unavailable": info.get("rembg_unavailable")}
    (d / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


# ------------------------------------------------------------- per letter
def lane_letters(job: str, name: str, cache: Path = CACHE) -> dict:
    """shape_id -> (polygon, kwargs) as stage 7 handed them to the lane."""
    from shapely.geometry import Polygon
    out = {}
    path = cache / job / name / "letters.json"
    for sid, v in json.loads(path.read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        if v.get("counter_holes"):
            kw["counter_holes"] = [Polygon(h) for h in v["counter_holes"]]
        out[sid] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def apex_tips(poly, kw: dict | None = None) -> list[dict]:
    """The letter's merged tips as the cut reads them under the flag:
    [{crotch, tip, cross, piece}]. A tip is a column the cut stations on an
    apex cross that has closed at its far end (the walk's own reading,
    `columns._APEX_CLOSED`); its point is its piece's vertex farthest from
    the cross, its crotch the cut's crotch (the stub's start, or the
    vertex a cross split at its crotch shares), else the cross's middle."""
    from shapely.geometry import LineString, Point
    from digitizer_core import outline_cut as oc
    kw = kw or {}
    lane = {k: True for k in ("fold_cuts", "rail_axis", "corner_fold", "small_bold") if kw.get(k)}
    if kw.get("square_ends"):
        lane["mitre_ends"] = True
    with oc.apex_cut_scope(True):
        cut = oc.letter_columns(poly, kw.get("spacing_mm", 0.4), **lane)
    xs = [(c[0], c[1]) for c in cut.cuts if c[2] == "apex"]
    stubs = [c for c in cut.cuts if c[2] == "apex_stub"]
    out = []
    for c in cut.columns:
        if len(c.stations) < 2 or oc._apex_tip_piece(c.piece, xs) is None:
            continue
        lines = [LineString(x) for x in xs]
        d0 = min(ln.distance(Point(c.start)) for ln in lines)
        d1 = min(ln.distance(Point(c.end)) for ln in lines)
        cut_end = 0 if d0 <= d1 else -1
        tol = kw.get("spacing_mm", 0.4) + TIP_END_WIDTHS * cut.W
        if (min(d0, d1) > tol
                or math.dist(*c.stations[-1 - cut_end]) > TIP_CLOSED * math.dist(*c.stations[cut_end])):
            continue
        m = Point(c.start if cut_end == 0 else c.end)
        mine = [x for x, ln in zip(xs, lines) if ln.distance(m) <= tol]
        ends = [tuple(e) for x in mine for e in x]
        shared = [e for e in ends if ends.count(e) > 1]
        stub = next((st for st in stubs if any(LineString(x).distance(Point(st[1])) < 1e-6 for x in mine)), None)
        crotch = (tuple(stub[0]) if stub is not None else shared[0] if shared
                  else ((mine[0][0][0] + mine[0][1][0]) / 2, (mine[0][0][1] + mine[0][1][1]) / 2))
        edge = unary_lines(mine)
        tip = max(c.piece.exterior.coords, key=lambda q: edge.distance(Point(q)))
        out.append({"crotch": crotch, "tip": tuple(tip), "cross": mine, "piece": c.piece})
    return out


def unary_lines(segs):
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    return unary_union([LineString(s) for s in segs])


#: `stage6_satin.strip_splits` finds a split point on its cross to 1e-6 mm;
#: an arm's runs are stored to 1e-4 mm, so it found none, and a plan's split
#: satin read its half stitches as crosses (PROSEAL's A at 85%: 15.3 deg, the
#: lane's own run 10.1). Rails turn by tenths of a millimetre: 1e-3 is safe
SPLIT_EPS_MM = 1e-3


def _strip(pts):
    from digitizer_core.stage6_satin import _on_segment
    from digitizer_core.stitches import strip_ties
    pts = strip_ties([tuple(p) for p in pts])
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        if not _on_segment(out[-1], pts[i], pts[i + 1], SPLIT_EPS_MM):
            out.append(pts[i])
    out.append(pts[-1])
    return out


def _deg(a, b) -> float:
    from tools.italic_cross import fold
    return fold(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])))


def _paired(seq) -> list:
    """His zigzag -> [(stitch, cross angle)]: each stitch read as the axial
    mean of itself and the next. His two families lean +-atan(pitch / 2
    width) about the cross, and the pair cancels them."""
    from tools.italic_cross import axial_mean
    seq = [s for s in seq if math.dist(*s) >= 0.5]
    return [(s, axial_mean([_deg(*s), _deg(*t)])) for s, t in zip(seq, seq[1:])]


def _crosses(runs) -> list:
    """Our satin's CROSSES, [(stitch, angle)]: the lane sews a station rail
    to rail and then returns on the slant to the next (A1 B1 A2 B2, splits
    fused), so a run's even stitches are its stations and its odd ones lean
    the whole pitch. Read together, the mean leans half of it toward the
    return, and the return's lean flips with the rail the satin begins on
    and the way the walk sews it: MFab's 1.5 mm crosses moved 13 deg between
    two walks with the same stations. The stations are the cut's."""
    cr = []
    for r in runs:
        if r["kind"] == "satin":
            pts = _strip(r["pts"])
            cr += [((a, b), _deg(a, b)) for a, b in zip(pts[0::2], pts[1::2]) if math.dist(a, b) >= 0.5]
    return cr


def cross_vs_text(crosses, tip: dict, near: float = NEAR_MM) -> list:
    """Per `FRACS` point on the crotch -> tip line: the axial mean against
    the line of text (the x axis) of the paired crosses passing within
    `near` of it, degrees, or None where none does."""
    from shapely.geometry import LineString, Point
    from tools.italic_cross import axial_mean
    (cx, cy), (tx, ty) = tip["crotch"], tip["tip"]
    out = []
    for f in FRACS:
        p = Point(cx + f * (tx - cx), cy + f * (ty - cy))
        angs = [a for (s, a) in crosses if LineString(s).distance(p) <= near]
        out.append(round(abs(axial_mean(angs)), 1) if angs else None)
    return out


EXIT_MM = 0.45      # a hop leaving a tip's last stitch lies this far on it however it goes


def letter_cost(runs: list[dict], sid: str, tips: list[dict]) -> dict:
    """One letter's runs (plan order) -> trims inside it, its TRAVEL mm, the
    TRAVEL laid on satin it has already sewn, and the part of that on a tip
    piece's own satin, sewn after it (past `EXIT_MM` of the stitch the tip's
    satin ended on: a hop away from a tip starts on its last cross)."""
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    idx = [i for i, r in enumerate(runs) if r["sid"] == sid]
    trims = sum(1 for i in idx if runs[i]["trim"] and i > 0 and runs[i - 1]["sid"] == sid)
    travel = on_sat = on_tip = 0.0
    sewn = []
    tip_sewn = [None] * len(tips)       # (ground, exit point) once the tip's satin is down
    for i in idx:
        r = runs[i]
        pts = [tuple(p) for p in r["pts"]]
        if r["kind"] == "travel" and len(pts) >= 2:
            ln = LineString(pts)
            travel += ln.length
            if sewn:
                on_sat += ln.intersection(unary_union(sewn).buffer(-0.05)).length
            for ts in tip_sewn:
                if ts is not None:
                    ground, exit_pt = ts
                    on_tip += ln.intersection(ground.difference(Point(exit_pt).buffer(EXIT_MM))).length
        if r["kind"] == "satin":
            sp = _strip(pts)
            if len(sp) < 2:
                continue
            line = LineString(sp)
            sewn.append(line.buffer(0.2))
            for k, t in enumerate(tips):
                inside = line.intersection(t["piece"]).length
                if inside > 0.5 * line.length:
                    tip_sewn[k] = (line.buffer(0.2).intersection(t["piece"].buffer(0.05)), sp[-1])
    return {"trims": trims, "travel_mm": round(travel, 2), "on_satin_mm": round(on_sat, 2),
            "on_tip_mm": round(on_tip, 2)}


def read_arm(job: str, name: str, cache: Path = CACHE) -> dict | None:
    d = cache / job / name
    if not (d / "runs.json").is_file():
        return None
    runs = json.loads((d / "runs.json").read_text(encoding="utf-8"))
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    return {"runs": runs, "meta": meta, "letters": lane_letters(job, name, cache)}


# ------------------------------------------------------------------- the pro
def pro_read(path: Path) -> dict:
    """His file: letters (`letter_pieces.read`), his extents, and every
    TRIM's position, mm, y down. A PES carries no trims: its DST beside it,
    where there is one, is read instead (`border_census.find_pair` hands
    the PES first)."""
    import pystitch
    from tools import letter_pieces as LP
    path = Path(path)
    if path.suffix.lower() != ".dst":
        path = next((q for q in (path.with_suffix(".DST"), path.with_suffix(".dst")) if q.is_file()), path)
    res = LP.read(path)
    pat = pystitch.read(str(path))
    trims = [(x / 10.0, y / 10.0) for x, y, c in pat.stitches if (c & pystitch.COMMAND_MASK) == pystitch.TRIM]
    pts = [(x / 10.0, y / 10.0) for x, y, c in pat.stitches if (c & pystitch.COMMAND_MASK) == pystitch.STITCH]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return {"letters": res["letters"], "trims": trims, "box": (min(xs), min(ys), max(xs), max(ys)),
            "dst": str(path).lower().endswith(".dst")}


def _norm(b, box):
    w, h = box[2] - box[0], box[3] - box[1]
    return (((b[0] + b[2]) / 2 - box[0]) / w, ((b[1] + b[3]) / 2 - box[1]) / h, (b[3] - b[1]) / h)


def pro_letter(pro: dict, ours_box, design_box) -> dict | None:
    """His letter in the same place: the nearest letter centre, each in its
    own design's extents, of a height within 30% of ours."""
    cx, cy, ch = _norm(ours_box, design_box)
    best = None
    for L in pro["letters"]:
        px, py, ph = _norm(L["bbox"], pro["box"])
        if not 0.7 <= ph / max(ch, 1e-9) <= 1.3:
            continue
        d = math.hypot(px - cx, py - cy)
        if best is None or d < best[0]:
            best = (d, L)
    return best[1] if best is not None and best[0] < 0.08 else None


def _pro_crosses(L: dict) -> list:
    """His letter's crosses, paired within each of his pieces (`_paired`)."""
    out = []
    for k in sorted(set(L["piece_of_cross"])):
        seq = [tuple(map(tuple, c)) for c, j in zip(L["crosses"], L["piece_of_cross"]) if j == k]
        out += _paired(seq)
    return out


def map_tip(tip: dict, ours_box, theirs_box) -> dict:
    """A tip carried into his letter by the two letters' sewn boxes."""
    def m(p):
        return (theirs_box[0] + (p[0] - ours_box[0]) * (theirs_box[2] - theirs_box[0]) / (ours_box[2] - ours_box[0]),
                theirs_box[1] + (p[1] - ours_box[1]) * (theirs_box[3] - theirs_box[1]) / (ours_box[3] - ours_box[1]))
    return {**tip, "crotch": m(tip["crotch"]), "tip": m(tip["tip"])}


def _box(runs) -> tuple:
    pts = [p for r in runs if r["kind"] == "satin" for p in r["pts"]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def letter_rows(job: str, cache: Path = CACHE, pro: dict | None = None) -> list[dict]:
    """Every lane letter with a merged tip under the flag, each arm's cost
    and crosses, and the pro's trims and crosses in his letter."""
    arms = {a: read_arm(job, a, cache) for a in ARMS}
    base = arms.get("on") or arms.get("on_new") or arms.get("off")
    if base is None:
        return []
    if pro is None:
        info = json.loads((cache / job / "gen.json").read_text(encoding="utf-8"))
        pro = pro_read(Path(info["pro"]))
    allpts = [p for r in base["runs"] for p in r["pts"]]
    design_box = (min(p[0] for p in allpts), min(p[1] for p in allpts),
                  max(p[0] for p in allpts), max(p[1] for p in allpts))
    rows = []
    for sid, (poly, kw) in base["letters"].items():
        tips = apex_tips(poly, kw)
        if not tips:
            continue
        mine = [r for r in base["runs"] if r["sid"] == sid]
        if not any(r["kind"] == "satin" for r in mine):
            continue
        ob = _box(mine)
        row = {"job": job, "sid": sid, "bbox": [round(v, 2) for v in ob], "tips": len(tips), "arms": {}}
        for a, data in arms.items():
            if data is None:
                continue
            runs_a = [r for r in data["runs"] if r["sid"] == sid]
            cost = letter_cost(data["runs"], sid, tips)
            cost["crosses"] = [cross_vs_text(_crosses(runs_a), t) for t in tips]
            row["arms"][a] = cost
        L = pro_letter(pro, ob, design_box)
        # his letter's box; where `letter_pieces` cannot part his letters
        # (MFab's layered file reads as 3), ours carried into his design's
        # extents -- his trims there, his crosses n/a
        pb = L["bbox"] if L is not None else [
            pro["box"][0] + (v - design_box[i % 2]) * (pro["box"][2 + i % 2] - pro["box"][i % 2])
            / (design_box[2 + i % 2] - design_box[i % 2]) for i, v in enumerate(ob)]
        if L is not None or pro["dst"]:
            row["pro"] = {"bbox": [round(v, 2) for v in pb],
                          "trims": (sum(1 for x, y in pro["trims"]
                                        if pb[0] - 0.5 <= x <= pb[2] + 0.5 and pb[1] - 0.5 <= y <= pb[3] + 0.5)
                                    if pro["dst"] else None),
                          "crosses": ([cross_vs_text(_pro_crosses(L), map_tip(t, ob, pb)) for t in tips]
                                      if L is not None else [None] * len(tips))}
        rows.append(row)
    rows.sort(key=lambda r: (round(r["bbox"][1] / 5), r["bbox"][0]))
    return rows


def replay(job: str, name: str = "on", cache: Path = CACHE, on: bool = True) -> list[dict]:
    """The captured lane inputs of one arm sewn again through TODAY's engine,
    letter by letter, offline (seconds, no plan): the walk's iteration loop.
    -> per letter with a merged tip: the captured arm's cost beside today's."""
    from digitizer_core import columns as C
    from digitizer_core import outline_cut as oc
    data = read_arm(job, name, cache)
    out = []
    for sid, (poly, kw) in data["letters"].items():
        tips = apex_tips(poly, kw)
        if not tips:
            continue
        with oc.apex_cut_scope(on):
            runs, _rep = C.lettering_columns_shape(poly, sid, **kw)
        now = [{"sid": sid, "kind": str(r.kind), "jump": bool(r.jump), "trim": bool(r.trim),
                "pts": [list(p) for p in r.points]} for r in runs]
        was = [r for r in data["runs"] if r["sid"] == sid]
        out.append({"sid": sid, "bbox": [round(v, 1) for v in poly.bounds], "tips": len(tips),
                    "captured": letter_cost(was, sid, tips), "today": letter_cost(now, sid, tips),
                    "crosses": [[cross_vs_text(_crosses(x), t) for t in tips] for x in (was, now)]})
    return out


# ------------------------------------------------------- the test fixture
def runs_md5(runs) -> str:
    """The lane's runs (`StitchRun`s), kind and every point to a micron."""
    h = hashlib.md5()
    for r in runs:
        h.update(str(r.kind).encode())
        for x, y in r.points:
            h.update(f"{x:.6f},{y:.6f};".encode())
        h.update(b"|")
    return h.hexdigest()


def _rows(runs) -> list[dict]:
    return [{"sid": "x", "kind": str(r.kind), "jump": bool(r.jump), "trim": bool(r.trim),
             "pts": [list(p) for p in r.points]} for r in runs]


def crotch_bare(poly, kw: dict, rows: list[dict]) -> float:
    """mm2 of the letter within 0.6 mm of an apex cross that no satin stitch
    covers, each stitch grown by 0.2 mm (half a 40 wt thread)."""
    from shapely.geometry import LineString, MultiLineString
    from shapely.ops import unary_union
    from digitizer_core import outline_cut as oc
    with oc.apex_cut_scope(True):
        cut = oc.letter_columns(poly, kw.get("spacing_mm", 0.4))
    xs = [LineString(c[:2]) for c in cut.cuts if c[2] == "apex"]
    if not xs:
        return 0.0
    band = poly.intersection(unary_union(xs).buffer(0.6))
    segs = []
    for r in rows:
        if r["kind"] == "satin":
            pts = _strip(r["pts"])
            segs += [(a, b) for a, b in zip(pts, pts[1:]) if a != b]
    return round(band.difference(MultiLineString(segs).buffer(0.2)).area, 4) if segs else round(band.area, 4)


def letter_exposed(rows: list[dict]) -> float:
    """mm of the letter's TRAVEL no later thread of the letter covers
    (`travel_cover`'s rule, read on the letter alone)."""
    from types import SimpleNamespace
    import numpy as np
    from digitizer_core import stitches
    from tools import travel_cover as TC
    runs = [SimpleNamespace(points=[tuple(p) for p in r["pts"]],
                            kind=stitches.TRAVEL if r["kind"] == "travel" else r["kind"]) for r in rows]
    frame = TC._grid_frame(runs)
    if frame is None:
        return 0.0
    x0, y0, nx, ny, cell = frame
    after = np.zeros((ny, nx), np.float64)
    out = 0.0
    for run in reversed(runs):
        pts = stitches.strip_ties(run.points)
        if run.kind == stitches.TRAVEL and len(pts) >= 2:
            for x, y, L in TC._samples(pts):
                if after[min(ny - 1, max(0, int((y - y0) / cell))), min(nx - 1, max(0, int((x - x0) / cell)))] \
                        < TC.MIN_UNITS:
                    out += L
        TC._add_ribbon(after, frame, pts)
    return round(out, 2)


def letter_thread_bare(runs) -> float:
    """mm of the letter's travel thread further than half a thread from any
    stitch it lays (`hairline_travel.scan`, read on the letter alone)."""
    from types import SimpleNamespace
    from tools import hairline_travel as HT
    return round(HT.scan(SimpleNamespace(blocks=[SimpleNamespace(runs=list(runs))]))["thread"], 2)


def letter_numbers(poly, sid: str, kw: dict, on: bool) -> dict:
    """One letter through THIS checkout's lane, flag `on` or off: the md5 of
    its runs and every number the bar reads."""
    from digitizer_core import columns as C
    from digitizer_core import outline_cut as oc
    with oc.apex_cut_scope(on):
        runs, _rep = C.lettering_columns_shape(poly, sid, **kw)
    rows = _rows(runs)
    tips = apex_tips(poly, kw)
    out = letter_cost(rows, "x", tips)
    out.update(md5=runs_md5(runs), exposed_mm=letter_exposed(rows), thread_bare_mm=letter_thread_bare(runs),
               bare_mm2=crotch_bare(poly, kw, rows), crosses=[cross_vs_text(_crosses(rows), t) for t in tips])
    return out


def fixture(jobs, cache: Path = CACHE) -> dict:
    """Every lane letter with a merged tip in each job's captured ON arm,
    with OFF and ON as THIS checkout sews them (run it from the commit the
    numbers should pin) and his trims in the letter (None from a PES)."""
    out = {}
    for job in jobs:
        rows = {r["sid"]: r for r in letter_rows(job, cache)}
        raw = json.loads((cache / job / "on" / "letters.json").read_text(encoding="utf-8"))
        for sid, (poly, kw) in lane_letters(job, "on", cache).items():
            if sid not in rows:
                continue
            v = raw[sid]
            out[f"{job}_{NAMES.get((job, sid), sid)}"] = {
                "job": job, "shape_id": sid, "exterior": v["exterior"], "holes": v["holes"], "kw": v["kw"],
                **({"counter_holes": v["counter_holes"]} if v.get("counter_holes") else {}),
                "head": _head(), "pro_trims": (rows[sid].get("pro") or {}).get("trims"),
                "off": letter_numbers(poly, sid, kw, False), "on": letter_numbers(poly, sid, kw, True)}
    return out


def load_fixture(path: Path) -> dict:
    """label -> (polygon, shape id, kwargs, the record)."""
    from shapely.geometry import Polygon
    out = {}
    for lab, v in json.loads(Path(path).read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        if v.get("counter_holes"):
            kw["counter_holes"] = [Polygon(h) for h in v["counter_holes"]]
        out[lab] = (Polygon(v["exterior"], v["holes"]), v["shape_id"], kw, v)
    return out


def job_totals(job: str, cache: Path = CACHE) -> dict:
    """Per arm, the whole plan's gate-3 instruments and trims."""
    out = {}
    for a in {**ARMS, **CHECKS}:
        f = cache / job / a / "meta.json"
        if f.is_file():
            out[a] = json.loads(f.read_text(encoding="utf-8"))
    return out


def _fmt(v):
    return "–" if v is None else (f"{v:g}" if isinstance(v, (int, float)) else str(v))


def table_md(rows: list[dict], totals: dict, names: dict | None = None) -> str:
    """The per-letter table and the per-job gate-3 table, markdown."""
    names = names or {}
    arms = [a for a in ARMS]
    out = ["| job | letter | tips | trims OFF / ON / ON new / pro | travel mm OFF / ON / ON new"
           " | travel on satin mm OFF / ON / ON new | on a tip's own satin OFF / ON / ON new"
           " | cross vs text at 30/60/85% OFF / ON / ON new / pro |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        A = r["arms"]
        g = lambda k: " / ".join(_fmt(A[a][k]) if a in A else "–" for a in arms)
        pro = r.get("pro") or {}
        cr = []
        for k in range(r["tips"]):
            parts = ["/".join(_fmt(v) for v in A[a]["crosses"][k]) if a in A else "–" for a in arms]
            parts.append("/".join(_fmt(v) for v in pro["crosses"][k]) if pro and pro["crosses"][k] else "–")
            cr.append(" · ".join(parts))
        out.append(f"| {r['job']} | {names.get((r['job'], r['sid']), r['sid'])} | {r['tips']} | "
                   f"{g('trims')} / {_fmt(pro.get('trims'))} | {g('travel_mm')} | {g('on_satin_mm')} | "
                   f"{g('on_tip_mm')} | {'<br>'.join(cr)} |")
    out += ["", "| job | arm | head | trims | stitches | travel mm | exposed travel mm | bare thread mm"
            " | process s | DST md5 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for job, per in totals.items():
        for a, m in per.items():
            out.append(f"| {job} | {a} | {m['head']} | {m['trims']} | {m['stitches']} | {m['travel_mm']:.1f} | "
                       f"{m['exposed_mm']:.2f} | {m['thread_bare_mm']:.2f} | {m['process_s']} | "
                       f"`{m['dst_md5'][:10]}` |")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ renders
def _design(runs: list[dict]) -> dict:
    """Plan runs (mm, y down) -> a `stitchviz` design (units, y up)."""
    st = []
    for r in runs:
        if r["jump"] or r["trim"]:
            st.append({"type": "trim" if r["trim"] else "jump",
                       "x": r["pts"][0][0] * 10.0, "y": -r["pts"][0][1] * 10.0})
        st += [{"type": "stitch", "x": x * 10.0, "y": -y * 10.0} for x, y in r["pts"]]
    return {"stitches": st, "colors": [{"r": 30, "g": 30, "b": 30}]}


def _paths(runs: list[dict], ppm: float, box) -> "np.ndarray":
    """The needle path: satin dark, travel red, underlay orange, jumps blue."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = box
    pad = 1.0
    w, h = int((x1 - x0 + 2 * pad) * ppm), int((y1 - y0 + 2 * pad) * ppm)
    img = np.full((h, w, 3), 245, np.uint8)
    col = {"satin": (40, 40, 40), "travel": (0, 0, 230), "underlay": (0, 150, 255)}
    T = lambda p: (int(round((p[0] - x0 + pad) * ppm)), int(round((p[1] - y0 + pad) * ppm)))
    prev = None
    for r in runs:
        pts = [T(p) for p in r["pts"]]
        if prev is not None and (r["jump"] or r["trim"]):
            cv2.line(img, prev, pts[0], (230, 120, 0), 1, cv2.LINE_AA)
            cv2.circle(img, pts[0], max(3, int(ppm / 8)), (230, 120, 0), 2)
        for a, b in zip(pts, pts[1:]):
            cv2.line(img, a, b, col.get(r["kind"], (120, 120, 120)),
                     3 if r["kind"] == "travel" else 1, cv2.LINE_AA)
        prev = pts[-1]
    return img


def _label(img, text):
    import cv2
    out = img.copy()
    cv2.putText(out, text, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    return out


def _hstack(imgs, gap: int = 16):
    import numpy as np
    h = max(i.shape[0] for i in imgs)
    cols = []
    for k, i in enumerate(imgs):
        pad = np.full((h, i.shape[1], 3), 255, np.uint8)
        pad[:i.shape[0]] = i
        cols.append(pad)
        if k < len(imgs) - 1:
            cols.append(np.full((h, gap, 3), 255, np.uint8))
    return np.hstack(cols)


def render(rows: list[dict], out: Path, cache: Path = CACHE, names: dict | None = None) -> list[Path]:
    """Per letter: OFF | ON | ON new | pro, threads at 8 and 40 px/mm, and
    the needle paths (ours only: his file has no travel label) at 40."""
    import cv2
    from digitizer_core import stitchviz
    from tools import letter_pieces as LP
    names = names or {}
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for r in rows:
        arms = {a: read_arm(r["job"], a, cache) for a in ARMS}
        label = names.get((r["job"], r["sid"]), r["sid"])
        info = json.loads((cache / r["job"] / "gen.json").read_text(encoding="utf-8"))
        pro_runs = []
        if r.get("pro"):
            pb = r["pro"]["bbox"]
            for pr in LP.runs_of(Path(info["pro"])):
                keep = [p for p in pr["pts"].tolist()
                        if pb[0] - 0.3 <= p[0] <= pb[2] + 0.3 and pb[1] - 0.3 <= p[1] <= pb[3] + 0.3]
                if len(keep) >= 2:
                    pro_runs.append({"kind": "satin", "jump": True, "trim": False, "pts": keep})
        for ppm, tag in ((8.0, "view"), (40.0, "40ppm")):
            panels = []
            for a in ARMS:
                if arms[a] is None:
                    continue
                mine = [x for x in arms[a]["runs"] if x["sid"] == r["sid"]]
                panels.append(_label(stitchviz.render_design(_design(mine), px_per_mm=ppm), a))
            if pro_runs:
                panels.append(_label(stitchviz.render_design(_design(pro_runs), px_per_mm=ppm), "pro"))
            f = out / f"{r['job']}_{label}_{tag}.png"
            cv2.imwrite(str(f), _hstack(panels))
            written.append(f)
        box = r["bbox"]
        paths = [_label(_paths([x for x in arms[a]["runs"] if x["sid"] == r["sid"]], 40.0, box), a)
                 for a in ARMS if arms[a] is not None]
        f = out / f"{r['job']}_{label}_paths.png"
        cv2.imwrite(str(f), _hstack(paths))
        written.append(f)
    return written




# ------------------------------------------------------------------- main
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cache", type=Path, default=CACHE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("job", choices=sorted(JOBS))
    a = sub.add_parser("arm")
    a.add_argument("job", choices=sorted(JOBS))
    a.add_argument("arm", choices=sorted({**ARMS, **CHECKS}))
    r = sub.add_parser("replay")
    r.add_argument("job", choices=sorted(JOBS))
    r.add_argument("--arm", default="on", choices=sorted(ARMS))
    f = sub.add_parser("fixture")
    f.add_argument("--out", type=Path, required=True)
    f.add_argument("--jobs", nargs="*", default=list(FIXTURE_JOBS))
    for name in ("table", "render"):
        t = sub.add_parser(name)
        t.add_argument("--out", type=Path)
        t.add_argument("--json", type=Path)
        t.add_argument("--jobs", nargs="*", default=sorted(JOBS))
        t.add_argument("--names", type=Path, help="JSON {job: {shape_id: letter}} for the row labels")
    return ap.parse_args(argv)


def _names(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return dict(NAMES)
    return {(j, sid): lab for j, m in json.loads(path.read_text(encoding="utf-8")).items()
            for sid, lab in m.items()}


def main(argv=None) -> int:
    utf8_console()
    args = parse_args(argv)
    if args.cmd == "gen":
        print(json.dumps(gen(args.job, args.cache), indent=1))
    elif args.cmd == "arm":
        print(json.dumps(arm(args.job, args.arm, args.cache), indent=1))
    elif args.cmd == "replay":
        for row in replay(args.job, args.arm, args.cache, ARMS[args.arm]):
            print(json.dumps(row))
    elif args.cmd == "fixture":
        fx = fixture([j for j in args.jobs if (args.cache / j / "on" / "letters.json").is_file()], args.cache)
        args.out.write_text(json.dumps(fx, indent=1) + "\n", encoding="utf-8")
        print(f"{len(fx)} letters -> {args.out}")
    else:
        rows = [r for j in args.jobs if (args.cache / j / "gen.json").is_file()
                for r in letter_rows(j, args.cache)]
        names = _names(args.names)
        if args.json:
            args.json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        if args.cmd == "table":
            md = table_md(rows, {j: job_totals(j, args.cache) for j in args.jobs
                                 if (args.cache / j).is_dir()}, names)
            if args.out:
                args.out.write_text(md, encoding="utf-8")
            print(md)
        else:
            for f in render(rows, args.out or (args.cache / "renders"), args.cache, names):
                print(f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
