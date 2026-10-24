"""column_harness: the Column lane on Fremont's grown ~4 mm letters, each
word drawn beside the same word cut from the pro's patch DST.

WHAT IT IS FOR. The pro raises Fremont's small words (EST 1895, THE, EAT |
STAY | PLAY) to ~4 mm bold satin letters. With `small_text_cap_mm` 4.0,
`small_text_cap_letter_gap_mm` 0.25, `small_text_cap_bold_scale` 1.45,
`small_text_cap_min_stroke_mm` 0.85 and `lettering_columns_small_bold` the
engine grows them to his size and hands each grown letter's polygon to the
Column lane (`columns.lettering_columns_shape`). This replays exactly those
calls -- the polygon and the keyword arguments stage 7 passed, captured
from the pipeline at 92.5 mm Hat -- through today's engine and draws what
the lane constructs, per letter: satin crosses dark, travel red, underlay
orange, the artwork outline grey. Stitch LAYOUT is judged in the preview
(Kent, 2026-10-22), so the sheet is the proof; only pull needs fabric.

Per letter it reads: columns, pieces the cut could not sew
(`columns_unsewn`), station fans (`outline_cut.pivot_sweep` past
`SMALL_BOLD_FAN_DEG`), the sewn judge's (folds, short legs, crossed legs)
(`outline_cut.sewn_knots`), the median satin cross (the sewn stroke width
before pull), crosses over 1.5 stroke widths, travel and trims.

The letters come from `testdata/fremont92_reset_letters.json` (the 21
grown letters as stage 7 handed them over, 2026-10-21) unless `--capture`
re-runs the pipeline (`tools.fremont_triage.run_arm`, ~8 minutes) and
writes a fresh set. `--before RUNS.json` draws a saved construction as a
third panel (`--save-runs` writes one), so an engine change is shown as
before | after | pro on one sheet per word.

The pro's words are read off `Embroidery Files.zip`'s Hotel Fremont Patch
DST with pystitch (`tools.small_text_columns.read_blocks`), in the file's
own frame, bands found from its letter pieces on 2026-10-23: block 8 holds
EST, 1895 and the tagline, block 7 THE.

    python -m tools.column_harness --out DIR                      # fixture letters, after | pro
    python -m tools.column_harness --out DIR --save-runs DIR/runs.json
    python -m tools.column_harness --out DIR --before runs.json   # before | after | pro
    python -m tools.column_harness --capture letters.json         # re-run the pipeline

DIR gets <word>.png (one sheet per word), letters.json (the per-letter
rows, every arm) and table.md.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402

LETTERS = DIGITIZER / "testdata" / "fremont92_reset_letters.json"
PPM = 40            # px/mm on the word sheets
FLAGS = {"small_text_cap_mm": 4.0, "small_text_cap_max_width_scale": 1.05,
         "small_text_cap_min_stroke_mm": 0.85, "small_text_cap_letter_gap_mm": 0.25,
         "small_text_cap_bold_scale": 1.45, "lettering_columns_small_bold": True}
#: word -> the letter's bounds (design mm, y down) that put it in the word
WORDS = {
    "EST": lambda b: b[1] < -11 and b[0] < 0,
    "1895": lambda b: b[1] < -11 and b[0] > 0,
    "THE": lambda b: -11 <= b[1] < -4,
    "TAGLINE": lambda b: b[1] > 5,
}
#: word -> (y0, y1, x0, x1) in the pro patch DST's own frame, and its block
PRO_BANDS = {"EST": (10.2, 15.0, 32.5, 42.7), "1895": (10.2, 15.0, 49.8, 61.0),
             "THE": (15.7, 20.4, 40.3, 52.0), "TAGLINE": (34.8, 39.5, 29.4, 65.2)}
PRO_BLOCK = {"EST": 8, "1895": 8, "THE": 7, "TAGLINE": 8}

# `--job` (2026-10-23, the corner-fold lane): the 5-10 mm words of the paired
# jobs, each letter as stage 7 handed it to the lane at the pro's design
# width through `tools.pro_pair.digitize` (the Studio's own request), beside
# the same word in the pro's HAT DST. `pro` is (file, blocks, band y0, y1,
# x0, x1) in the DST's own frame. The pro panel is his needle paths (1 px,
# needle dots), not a thread render: the construction is only visible there.
# `proseal`'s letters come from Kent's gitignored art and live beside it.
_PRO_DIR = None


def _pro_dir():
    global _PRO_DIR
    if _PRO_DIR is None:
        from tools import small_text_columns as stc
        _PRO_DIR = stc.PRO_DIR
    return _PRO_DIR


def jobs() -> dict:
    pd = _pro_dir()
    return {
        "fremont4": dict(letters=LETTERS, words=WORDS, pro_patch=True),
        "fremont": dict(letters=DIGITIZER / "testdata" / "fremont92_band_letters.json",
                        words={"HOTEL FREMONT": lambda b: -4.5 < b[1] < 4.5},
                        pro=(pd / "Hotel Fremont" / "Hotel Hat" / "HOTEL FREMONT HAT.DST", {7},
                             21.0, 30.0, 2.0, 91.0)),
        "drone": dict(letters=DIGITIZER / "testdata" / "drone62_band_letters.json",
                      words={"PRECISION": lambda b: 9.5 < b[1] < 11.0},
                      pro=(pd / "Precision Drone" / "PRECISION DRON HAT 2.DST", {3},
                           40.5, 48.5, -0.5, 63.5)),
        "mfab": dict(letters=DIGITIZER / "testdata" / "mfab105_band_letters.json",
                     words={"AND WELDING": lambda b: 0.5 < b[1] < 6.0},    # the MFAB letters above are 18 mm
                     pro=(pd / "MFAB" / "Mfab Hat & Polo" / "mf4b logo hat.DST", {2, 4},
                          23.5, 33.5, 7.0, 98.0)),
        "proseal": dict(letters=pd.parent / "proseal86_band_letters.json",
                        words={"PROSEAL": lambda b: True},
                        pro=(pd / "Proseal" / "PROSEALHAT.DST", {0}, 44.0, 55.0, 0.8, 83.0)),
    }


# --- letters ------------------------------------------------------------------

def load_letters(path: Path = LETTERS) -> dict:
    """shape_id -> (polygon, kwargs) as stage 7 handed them to the lane."""
    from shapely.geometry import Polygon
    out = {}
    for sid, v in json.loads(path.read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        if v.get("counter_holes"):
            kw["counter_holes"] = [Polygon(h) for h in v["counter_holes"]]
        out[sid] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def capture(out: Path, width_mm: float = 92.5) -> dict:
    """Run the pipeline with the growth flags and record every call the
    lane gets for a `small_text_enlarged` region -> the letters file."""
    from digitizer_core import stage7_sequence as s7
    from tools import fremont_triage as ft
    calls = []
    real = s7.lettering_columns_shape

    def spy(poly, shape_id, **kw):
        runs, report = real(poly, shape_id, **kw)
        calls.append((poly, shape_id, kw))
        return runs, report
    s7.lettering_columns_shape = spy
    try:
        run = ft.run_arm("main", width_mm, overrides=FLAGS, preflight=False)
    finally:
        s7.lettering_columns_shape = real
    meta = {r.shape_id: r.meta for r in run["result"].regions}
    data = {}
    for poly, sid, kw in calls:
        if not meta.get(sid, {}).get("small_text_enlarged"):
            continue
        row = {"exterior": [list(p) for p in poly.exterior.coords],
               "holes": [[list(p) for p in r.coords] for r in poly.interiors],
               "kw": {k: (list(v) if isinstance(v, tuple) else v)
                      for k, v in kw.items() if k != "counter_holes"}}
        if kw.get("counter_holes"):
            row["counter_holes"] = [[list(p) for p in h.exterior.coords] for h in kw["counter_holes"]]
        data[sid] = row
    out.write_text(json.dumps(data), encoding="utf-8")
    return data


# --- the lane, measured -------------------------------------------------------

def sew(letters: dict, **extra) -> dict:
    """shape_id -> (runs, report, columns) through today's engine. `extra`:
    keyword arguments laid over every call (`corner_fold=True`: the
    `--fold` arm)."""
    from digitizer_core import columns as C
    seen = []
    real = C.column_runs

    def spy(cols, poly, sid, **kw):
        r = real(cols, poly, sid, **kw)
        seen.append(cols)
        return r
    C.column_runs = spy
    out = {}
    try:
        for sid, (poly, kw) in letters.items():
            seen.clear()
            runs, rep = C.lettering_columns_shape(poly, sid, **{**kw, **extra})
            out[sid] = (runs, rep, seen[-1] if seen else [])
    finally:
        C.column_runs = real
    return out


def crosses(runs) -> list:
    from digitizer_core.stage6_satin import strip_splits
    from digitizer_core.stitches import strip_ties
    cr = []
    for r in runs:
        if r.kind != "satin":
            continue
        pts = np.asarray(strip_splits(strip_ties(list(r.points))), float)
        for i in range(0, len(pts) - 1, 2):
            cr.append((tuple(pts[i]), tuple(pts[i + 1])))
    return cr


def measure(poly, kw, runs, report, cols) -> dict:
    from digitizer_core.outline_cut import SMALL_BOLD_FAN_DEG, pivot_sweep, sewn_knots, stroke_width
    W = stroke_width(poly)
    L = [math.dist(a, b) for a, b in crosses(runs)]
    piv = [pivot_sweep(c.stations) for c in cols if c.kind != "ring"]
    folds, short, crossed = (int(v) for v in sewn_knots(runs))
    travel = [r for r in runs if r.kind == "travel"]
    return {"W": round(W, 2), "columns": len(cols), "unsewn": int(report.get("columns_unsewn", 0)),
            "fans": sum(1 for p in piv if p > SMALL_BOLD_FAN_DEG),
            "pivot_max": round(max(piv), 0) if piv else 0,
            "cross_med": round(float(np.median(L)), 2) if L else None,
            "over_1_5W": sum(1 for v in L if v > 1.5 * W),
            "folds": folds, "short": short, "crossed": crossed,
            "travel_mm": round(sum(math.dist(a, b) for r in travel
                                   for a, b in zip(r.points, r.points[1:])), 1),
            "trims": sum(1 for r in runs if r.trim or r.jump),
            "stitches": sum(len(r.points) for r in runs)}


# --- the same reader on both files ---------------------------------------------
# The 5-10 mm band's reader (`docs/lettering-5-10mm-2026-10-23.md`, "How it
# was read"), on needle-down point runs so ours (the lane's runs) and the
# pro's (his DST's runs in the band) are read by one rule:
#   column: stitches of 0.5 mm or more, consecutive ones anti-parallel and
#     within 0.5-2x in length, up to two short stitches skipped between
#     them; six crosses make a column. A FOLD stays inside one column.
#   butt: a column end within 0.8 W of another column's body (its cross
#     midpoints, away from that column's own ends); gap: the 0.4 mm thread
#     covers under 90% of a half-width disc at the meeting point.
#   fan: a column whose consecutive crosses share one end (within 0.45 mm,
#     the pro's inner-end spread) through more than 45 degrees.
#   travel: a needle-down stitch with neither end on a letter.
# W is the word's sewn width: the median cross of its columns.
CENSUS_PPM = 20


def census(point_runs: list, letters: list, trims: int, pitch: float = 0.4) -> dict:
    """point_runs: needle-down runs as point lists; letters: shapely polygons
    (ours: the artwork; the pro's: his letter pieces). -> the word's row."""
    import cv2
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    from digitizer_core.outline_cut import pivot_sweep
    cols = []
    for r in point_runs:
        cur, short, prev = [], 0, None
        for a, b in zip(r, r[1:]):
            L = math.dist(a, b)
            if L < 0.5:
                short += 1
                if short > 2 and cur:
                    if len(cur) >= 6:
                        cols.append(cur)
                    cur, prev = [], None
                continue
            short = 0
            d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            if prev is not None:
                pd, pL = prev
                if pd[0] * d[0] + pd[1] * d[1] < -0.2 and 0.5 <= L / pL <= 2.0:
                    cur.append((a, b))
                else:
                    if len(cur) >= 6:
                        cols.append(cur)
                    cur = [(a, b)]
            else:
                cur = [(a, b)]
            prev = (d, L)
        if len(cur) >= 6:
            cols.append(cur)
    widths = [math.dist(a, b) for c in cols for a, b in c]
    W = float(np.median(widths)) if widths else 1.0
    mids = [[((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in c] for c in cols]
    bodies = [LineString(m) if len(m) > 1 else None for m in mids]
    # the thread as sewn, for the gap read
    pts = np.array([q for r in point_runs for q in r])
    ox, oy = pts.min(0) - 1.0
    w, h = int((pts[:, 0].max() - ox + 1) * CENSUS_PPM) + 1, int((pts[:, 1].max() - oy + 1) * CENSUS_PPM) + 1
    mask = np.zeros((h, w), np.uint8)
    for r in point_runs:
        q = np.round((np.array(r) - (ox, oy)) * CENSUS_PPM).astype(np.int32)
        cv2.polylines(mask, [q], False, 255, max(1, int(round(0.4 * CENSUS_PPM))))
    disc_r = max(1, int(round(0.5 * W * CENSUS_PPM)))
    yy, xx = np.ogrid[-disc_r:disc_r + 1, -disc_r:disc_r + 1]
    disc = (xx * xx + yy * yy) <= disc_r * disc_r
    butts = gaps = 0
    for i, m in enumerate(mids):
        for end in (m[0], m[-1]):
            hit = None
            for j, body in enumerate(bodies):
                if j == i or body is None or body.length < 1.6 * W:
                    continue
                d = body.project(Point(end))
                if d < 0.8 * W or d > body.length - 0.8 * W:
                    continue
                q = body.interpolate(d).coords[0]
                if math.dist(q, end) <= 0.8 * W and (hit is None or math.dist(q, end) < hit[0]):
                    hit = (math.dist(q, end), q)
            if hit is None:
                continue
            butts += 1
            cx, cy = int(round((hit[1][0] - ox) * CENSUS_PPM)), int(round((hit[1][1] - oy) * CENSUS_PPM))
            y0, y1 = max(0, cy - disc_r), min(h, cy + disc_r + 1)
            x0, x1 = max(0, cx - disc_r), min(w, cx + disc_r + 1)
            sub = mask[y0:y1, x0:x1] > 0
            dsub = disc[y0 - (cy - disc_r):y1 - (cy - disc_r), x0 - (cx - disc_r):x1 - (cx - disc_r)]
            if dsub.sum() and (sub & dsub).sum() / dsub.sum() < 0.9:
                gaps += 1
    fans = sum(1 for c in cols if pivot_sweep(c, eps=0.45) > 45.0)
    ground = unary_union([p.buffer(0.3) for p in letters]) if letters else None
    travel = 0.0
    if ground is not None:
        for r in point_runs:
            for a, b in zip(r, r[1:]):
                if not ground.intersects(Point(a)) and not ground.intersects(Point(b)):
                    travel += math.dist(a, b)
    return {"columns": len(cols), "butts": butts, "gaps": gaps, "fans": fans,
            "width": round(W, 2), "travel_mm": round(travel, 1), "trims": trims,
            "stitches": sum(len(r) for r in point_runs)}


def ours_points(letters: dict, sewn: dict, ids: list) -> tuple[list, int]:
    """The word's needle-down runs (ties and splits stripped) and its
    trims, from the lane's runs."""
    from digitizer_core.stage6_satin import strip_splits
    from digitizer_core.stitches import strip_ties
    pr, trims = [], 0
    for sid in ids:
        runs, _rep, _cols = sewn[sid]
        for r in runs:
            if r.trim or r.jump:
                trims += 1
            pts = strip_splits(strip_ties(list(r.points))) if r.kind == "satin" else list(r.points)
            if len(pts) > 1:
                pr.append([tuple(p) for p in pts])
    return pr, trims


def pro_points(job: dict) -> tuple[list, list, int]:
    """The pro's band: its needle-down runs, letter pieces as polygons, and
    the trims (needle-up groups) between them."""
    from shapely.geometry import Point, box
    from tools import small_text_columns as stc
    path, blocks_keep, y0, y1, x0, x1 = job["pro"]
    blocks = stc.read_blocks(path)
    inside = lambda q: y0 <= q[1] <= y1 and x0 <= q[0] <= x1
    pcs = [p for p in stc.pieces(blocks) if p["block"] in blocks_keep
           and y0 <= (p["y0"] + p["y1"]) / 2 <= y1 and x0 <= (p["x0"] + p["x1"]) / 2 <= x1
           and (p["x1"] - p["x0"]) <= 3 * (p["y1"] - p["y0"])]
    boxes = [box(p["x0"] - 0.3, p["y0"] - 0.3, p["x1"] + 0.3, p["y1"] + 0.3) for p in pcs]

    def letter_of(q):
        return next((i for i, b in enumerate(boxes) if b.covers(Point(q))), None)
    # trims INSIDE a letter (needle up and down again in the same letter),
    # the lane's own count for ours; a hop from one letter to the next is
    # stage 7's on both sides and is left out
    runs, trims = [], 0
    for bi in blocks_keep:
        last_down = None
        up = False
        for q in blocks[bi]:
            if q is None:
                up = True
                continue
            if up and last_down is not None:
                a, b = letter_of(last_down), letter_of(q)
                if a is not None and a == b:
                    trims += 1
            up, last_down = False, q
        for r in stc._runs(blocks[bi]):
            if any(inside(q) for q in r):
                runs.append([q for q in r])
    return runs, [box(p["x0"], p["y0"], p["x1"], p["y1"]) for p in pcs], trims


def pro_paths_panel(job: dict, ppm: int = PPM):
    """The pro's band as needle paths: 1 px lines, needle dots."""
    import cv2
    runs, _pcs, _t = pro_points(job)
    _path, _blocks, y0, y1, x0, x1 = job["pro"]
    img = np.full((int((y1 - y0 + 2) * ppm) + 1, int((x1 - x0 + 2) * ppm) + 1, 3), 255, np.uint8)
    for r in runs:
        q = np.round((np.array(r) - (x0 - 1, y0 - 1)) * ppm).astype(np.int32)
        cv2.polylines(img, [q], False, (60, 60, 60), 1, cv2.LINE_AA)
        for x, y in q:
            cv2.circle(img, (int(x), int(y)), 1, (0, 0, 220), -1)
    return img


def runs_to_json(sewn: dict) -> dict:
    return {sid: {"runs": [{"kind": r.kind, "points": [[round(x, 4), round(y, 4)] for x, y in r.points]}
                           for r in runs],
                  "report": {k: v for k, v in rep.items() if isinstance(v, (int, float, bool))},
                  "stations": [[[list(a), list(b)] for a, b in c.stations] for c in cols],
                  "kinds": [c.kind for c in cols]}
            for sid, (runs, rep, cols) in sewn.items()}


def runs_from_json(data: dict) -> dict:
    """A saved construction -> shape_id -> (runs, report, columns-as-stations)."""
    from digitizer_core.stitches import StitchRun
    out = {}
    for sid, v in data.items():
        runs = [StitchRun(kind=r["kind"], points=[tuple(p) for p in r["points"]]) for r in v["runs"]]
        cols = [_Stations([(tuple(a), tuple(b)) for a, b in st], kind)
                for st, kind in zip(v["stations"], v["kinds"])]
        out[sid] = (runs, v["report"], cols)
    return out


class _Stations:
    def __init__(self, stations, kind):
        self.stations, self.kind = stations, kind


# --- drawing ------------------------------------------------------------------

def draw(poly, runs, box, ppm: int = PPM):
    """One letter: outline grey, satin dark, travel red, underlay orange."""
    import cv2
    from digitizer_core.stage6_satin import strip_splits
    from digitizer_core.stitches import strip_ties
    x0, y0, x1, y1 = box
    img = np.full((int((y1 - y0) * ppm) + 1, int((x1 - x0) * ppm) + 1, 3), 255, np.uint8)

    def P(p):
        return (int(round((p[0] - x0) * ppm)), int(round((p[1] - y0) * ppm)))
    for ring in [poly.exterior, *poly.interiors]:
        cv2.polylines(img, [np.array([P(p) for p in ring.coords], np.int32)], True,
                      (200, 200, 200), 1, cv2.LINE_AA)
    for r in runs:
        colour = {"satin": (40, 40, 40), "underlay": (0, 140, 230)}.get(r.kind, (0, 0, 230))
        pts = strip_splits(strip_ties(list(r.points))) if r.kind == "satin" else list(r.points)
        if len(pts) < 2:
            continue
        cv2.polylines(img, [np.array([P(p) for p in pts], np.int32)], False, colour,
                      2 if r.kind == "satin" else 1, cv2.LINE_AA)
    return img


def label(img, text):
    import cv2
    bar = np.full((22, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def hstack(imgs, gap: int = 20):
    h = max(i.shape[0] for i in imgs)
    cols = []
    for i in imgs:
        cols.append(np.vstack([i, np.full((h - i.shape[0], i.shape[1], 3), 255, np.uint8)]))
        cols.append(np.full((h, gap, 3), 255, np.uint8))
    return np.hstack(cols[:-1])


def pro_panel(word: str, ppm: int = PPM):
    """The pro's word, needle-down stitches drawn 0.4 mm wide (the
    `small_text_columns` reading), or None without the pro's file."""
    from tools import small_text_columns as stc
    path = stc.JOBS["fremont_patch"]["pro"]
    if not path.is_file():
        return None
    blocks = stc.read_blocks(path)
    return stc.render_band(blocks, PRO_BANDS[word], keep={PRO_BLOCK[word]}, ppm=ppm, pad_mm=0.5)


def sheets(letters: dict, arms: dict, out: Path, ppm: int = PPM, job: dict | None = None) -> dict:
    """arms: name -> sewn dict. Writes <word>.png; -> per-letter rows.
    `job` (a `jobs()` entry; None is `fremont4`): its words and its pro
    panel; a band job also gets `census.md`, the word read the same way on
    every arm and on the pro's DST (`census`)."""
    import cv2
    out.mkdir(parents=True, exist_ok=True)
    job = job or jobs()["fremont4"]
    rows = {}
    census_rows = []
    for word, pick in job["words"].items():
        ids = sorted((sid for sid, (poly, _kw) in letters.items() if pick(poly.bounds)),
                     key=lambda s: letters[s][0].bounds[0])
        if not ids:
            continue
        b = np.array([letters[s][0].bounds for s in ids])
        box = (b[:, 0].min() - 1, b[:, 1].min() - 1, b[:, 2].max() + 1, b[:, 3].max() + 1)
        panels = []
        for name, sewn in arms.items():
            img = np.full((int((box[3] - box[1]) * ppm) + 1, int((box[2] - box[0]) * ppm) + 1, 3),
                          255, np.uint8)
            for sid in ids:
                img = np.minimum(img, draw(letters[sid][0], sewn[sid][0], box, ppm))
            panels.append(label(img, f"{word}  {name}"))
            if "pro" in job:
                pr, trims = ours_points(letters, sewn, ids)
                census_rows.append((word, name, census(pr, [letters[s][0] for s in ids], trims)))
        if job.get("pro_patch"):
            pro = pro_panel(word, ppm)
            if pro is not None:
                panels.append(label(pro, f"{word}  PRO (patch DST)"))
        elif job["pro"][0].is_file():
            panels.append(label(pro_paths_panel(job, ppm), f"{word}  PRO (hat DST)"))
            runs, boxes, trims = pro_points(job)
            census_rows.append((word, "pro", census(runs, boxes, trims)))
        cv2.imwrite(str(out / f"{word.lower().replace(' ', '_')}.png"), hstack(panels))
        for i, sid in enumerate(ids):
            poly, kw = letters[sid]
            rows[sid] = {"word": word, "n": i + 1, "x": round(poly.bounds[0], 1),
                         **{name: measure(poly, kw, *sewn[sid]) for name, sewn in arms.items()}}
    if census_rows:
        keys = ("columns", "butts", "gaps", "fans", "width", "travel_mm", "trims", "stitches")
        md = ["| word | arm | " + " | ".join(keys) + " |", "|---|---|" + "---|" * len(keys)]
        md += [f"| {w} | {a} | " + " | ".join(str(c[k]) for k in keys) + " |" for w, a, c in census_rows]
        (out / "census.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        print("\n".join(md))
    return rows


KEYS = ("columns", "unsewn", "fans", "folds", "short", "crossed", "cross_med", "over_1_5W",
        "travel_mm", "trims", "stitches")


def table(rows: dict, arms: list[str]) -> str:
    """Markdown: one line per letter, each arm's numbers side by side."""
    head = "| word | # | shape | W | " + " | ".join(f"{k} ({a})" for k in KEYS for a in arms) + " |"
    lines = [head, "|" + "---|" * (4 + len(KEYS) * len(arms))]
    for sid, r in sorted(rows.items(), key=lambda kv: (kv[1]["word"], kv[1]["n"])):
        cells = [r["word"], str(r["n"]), sid, str(r[arms[0]]["W"])]
        cells += [str(r[a][k]) for k in KEYS for a in arms]
        lines.append("| " + " | ".join(cells) + " |")
    tot = ["| **all** | | | "]
    for k in KEYS:
        for a in arms:
            vals = [r[a][k] for r in rows.values() if r[a][k] is not None]
            tot.append(f"{round(float(np.median(vals)), 2)}" if k == "cross_med" else f"{sum(vals)}")
    lines.append(" | ".join(tot) + " |")
    return "\n".join(lines)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--letters", type=Path, default=LETTERS)
    ap.add_argument("--capture", type=Path, help="re-run the pipeline and write the letters here")
    ap.add_argument("--width", type=float, default=92.5)
    ap.add_argument("--out", type=Path, help="sheets, letters.json and table.md go here")
    ap.add_argument("--before", type=Path, help="a saved construction (--save-runs) as the before panel")
    ap.add_argument("--save-runs", type=Path, help="write today's construction for a later --before")
    ap.add_argument("--job", default="fremont4", choices=sorted(jobs()),
                    help="fremont4: the ~4 mm words (default); else a 5-10 mm band word, its letters "
                         "from that job's file, the pro's hat DST beside it")
    ap.add_argument("--fold", action="store_true",
                    help="arms off | fold: every call also with corner_fold=True "
                         "(`cfg.lettering_columns_corner_fold`)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    utf8_console(sys.stdout)
    args = parse_args(argv)
    job = jobs()[args.job]
    if args.capture:
        data = capture(args.capture, args.width)
        print(f"{len(data)} small-text letters -> {args.capture}")
        args.letters = args.capture
    elif args.job != "fremont4" and args.letters == LETTERS:
        args.letters = job["letters"]
    if not args.out and not args.save_runs:
        return 0
    letters = load_letters(args.letters)
    # only the job's words are sewn (a band file also holds the design's
    # other letters: MFab's 18 mm MFAB takes minutes a letter)
    letters = {s: v for s, v in letters.items() if any(pick(v[0].bounds) for pick in job["words"].values())}
    after = sew(letters)
    if args.save_runs:
        args.save_runs.write_text(json.dumps(runs_to_json(after)), encoding="utf-8")
    if not args.out:
        return 0
    arms = {}
    if args.before:
        arms["before"] = runs_from_json(json.loads(args.before.read_text(encoding="utf-8")))
    if args.fold:
        arms["off"] = after
        arms["fold"] = sew(letters, corner_fold=True)
    else:
        arms["after"] = after
    rows = sheets(letters, arms, args.out, job=job)
    (args.out / "letters.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    md = table(rows, list(arms))
    (args.out / "table.md").write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
