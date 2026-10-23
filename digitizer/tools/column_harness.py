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

def sew(letters: dict) -> dict:
    """shape_id -> (runs, report, columns) through today's engine."""
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
            runs, rep = C.lettering_columns_shape(poly, sid, **kw)
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
            "trims": sum(1 for r in travel if math.dist(r.points[0], r.points[-1]) > kw["trim_at_mm"]),
            "stitches": sum(len(r.points) for r in runs)}


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


def sheets(letters: dict, arms: dict, out: Path, ppm: int = PPM) -> dict:
    """arms: name -> sewn dict. Writes <word>.png; -> per-letter rows."""
    import cv2
    out.mkdir(parents=True, exist_ok=True)
    rows = {}
    for word, pick in WORDS.items():
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
        pro = pro_panel(word, ppm)
        if pro is not None:
            panels.append(label(pro, f"{word}  PRO (patch DST)"))
        cv2.imwrite(str(out / f"{word.lower()}.png"), hstack(panels))
        for i, sid in enumerate(ids):
            poly, kw = letters[sid]
            rows[sid] = {"word": word, "n": i + 1, "x": round(poly.bounds[0], 1),
                         **{name: measure(poly, kw, *sewn[sid]) for name, sewn in arms.items()}}
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
    return ap.parse_args(argv)


def main(argv=None) -> int:
    utf8_console(sys.stdout)
    args = parse_args(argv)
    if args.capture:
        data = capture(args.capture, args.width)
        print(f"{len(data)} small-text letters -> {args.capture}")
        args.letters = args.capture
    if not args.out and not args.save_runs:
        return 0
    letters = load_letters(args.letters)
    after = sew(letters)
    if args.save_runs:
        args.save_runs.write_text(json.dumps(runs_to_json(after)), encoding="utf-8")
    if not args.out:
        return 0
    arms = {}
    if args.before:
        arms["before"] = runs_from_json(json.loads(args.before.read_text(encoding="utf-8")))
    arms["after"] = after
    rows = sheets(letters, arms, args.out)
    (args.out / "letters.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    md = table(rows, list(arms))
    (args.out / "table.md").write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
