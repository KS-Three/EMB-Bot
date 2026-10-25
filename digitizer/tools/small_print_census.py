#!/usr/bin/env python
"""Small print at 60 wt: the 40 wt vs 60 wt census for sew-out card block D.

Measure only. Nothing in `digitizer_core/` is read differently or changed:
this drives `tools/small_print.py` (`measure`, `render_line`) over the grid

    fixture (synthetic BOARD word, Fremont tagline crop)
  x cap height (2.5 / 3 / 4 mm)
  x thread weight (40 / 60, `cfg.thread_wt`)
  x `cfg.small_print_floor` (OFF / ON)

with every other flag at its shipped default, and adds the one column
`small_print.measure` does not report: the narrowest satin column, read off
the stream the way `docs/small-cap-census-2026-10-12`'s tool reads it -- a
satin run is cross, rail step, cross, so the even segments are the crosses; a
column's width is the median of its crosses; `col_min_mm` is the smallest over
columns of 5 or more crosses. `cross_min_mm` is the single shortest cross
(every column tapers to `SATIN_MIN_CROSS_MM` at its tips, so it ranks nothing).

Every number is a CANDIDATE (ROADMAP gate 1): nothing here was sewn.

Run, from `digitizer/`:

    .venv/Scripts/python tools/small_print_census.py --fixture synthetic --out OUTDIR
    .venv/Scripts/python tools/small_print_census.py --fixture fremont_tagline --out OUTDIR
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitches   # noqa: E402
from tools import small_print                                  # noqa: E402

CAPS = (2.5, 3.0, 4.0)
WEIGHTS = (40, 60)
FIXTURES = ("synthetic", "fremont_tagline")

# The neighbouring flags this census holds at their shipped defaults. Printed
# with every run so a table says which engine it was measured on. True size
# (`small_text_true_size`) is ON by default since 2026-10-14; the census's
# rows were measured before that, so it pins the switch OFF (`OFF_FLIPS`).
OFF_FLIPS = {"small_text_true_size": False}
PINNED = {"small_glyph_keep": True, "small_lettering_skeleton": False,
          "small_text_cap_mm": None, "small_text_restore_mm": None}

MIN_COLUMN_CROSSES = 5


def column_widths(plan, box) -> dict:
    """-> {col_min_mm, col_median_mm, cross_min_mm, columns} over the satin
    runs that start inside `box` (x0, y0, x1, y1): per run the median of its
    even segments (the crosses); `col_min_mm` over runs of at least
    `MIN_COLUMN_CROSSES` crosses. NaN where there is no such run."""
    widths, crosses = [], []
    for _blk, run in plan.iter_runs():
        pts = run.points
        if run.kind != stitches.SATIN or len(pts) < 2:
            continue
        x, y = pts[0][0], pts[0][1]
        if not (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
            continue
        cs = [float(np.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
              for i in range(0, len(pts) - 1, 2)]
        crosses += cs
        if len(cs) >= MIN_COLUMN_CROSSES:
            widths.append(statistics.median(cs))
    nan = float("nan")
    return dict(col_min_mm=min(widths) if widths else nan,
                col_median_mm=statistics.median(widths) if widths else nan,
                cross_min_mm=min(crosses) if crosses else nan,
                columns=len(widths))


def cell(image, ref: dict, cap: float, wt: int, on: bool):
    """One grid cell -> (row dict, (result, plan, art))."""
    cfg = PipelineConfig(target_width_mm=round(cap / ref["cap"], 2), thread_wt=wt,
                         small_print_floor=on, **OFF_FLIPS)
    for k, v in PINNED.items():
        assert getattr(cfg, k) == v, (k, getattr(cfg, k))
    m, (res, plan, art) = small_print.measure(image, cfg, ref)
    x0, y0, x1, y1 = art.bounds
    m.update(column_widths(plan, (x0 - 0.6, y0 - 0.6, x1 + 0.6, y1 + 0.6)))
    m.update(target_cap=cap, thread_wt=wt, floor=on)
    return m, (res, plan, art)


def census(name: str, caps=CAPS, weights=WEIGHTS, ref: dict | None = None, sheet_ppm=None,
           progress=None):
    """-> (ref, rows, sheet image or None). Rows are the grid in order cap,
    weight, floor OFF then ON."""
    _path, rank, ref_w = small_print.FIXTURES[name]
    image = small_print.load(name)
    if ref is None:
        ref = small_print.reference(image, PipelineConfig(target_width_mm=ref_w), rank)
    rows, panels = [], []
    for cap in caps:
        for wt in weights:
            pair, zoom = [], []
            tw = machine.thread_profile(wt).width_mm
            for on in (False, True):
                m, (_res, plan, art) = cell(image, ref, cap, wt, on)
                rows.append(m)
                if progress:
                    progress(m)
                if sheet_ppm:
                    tag = f"{'ON ' if on else 'OFF'} {cap:g} mm cap, {wt} wt"
                    pair.append(small_print._label(
                        small_print.render_line(plan, art, tw, sheet_ppm),
                        f"{tag}: {m['counters_shut']}/{m['counters']} shut, "
                        f"{m['counter_open']:.2f} open, narrowest col {m['col_min_mm']:.2f} mm"))
                    fb = small_print.focus_box(art)
                    if fb is not None:
                        zoom.append(small_print._label(
                            small_print.render_line(plan, art, tw, 2 * sheet_ppm, pad=0.5, box=fb),
                            f"{tag}, zoom {2 * sheet_ppm} px/mm"))
            if sheet_ppm:
                panels.append(small_print._hstack(pair))
                if zoom:
                    panels.append(small_print._hstack(zoom))
    img = None
    if sheet_ppm:
        body = small_print._vstack(panels)
        title = np.full((40, body.shape[1], 3), 255, np.uint8)
        cv2.putText(title, f"{name}: 2.5 / 3 / 4 mm caps, 40 vs 60 wt, small_print_floor OFF (left) vs ON "
                    f"(right), {sheet_ppm} px/mm, red = source outline",
                    (6, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 1, cv2.LINE_AA)
        img = np.vstack([title, body])
    return ref, rows, img


COLUMNS = ("fixture", "target_cap", "thread_wt", "floor", "cap_mm", "cap_traced_mm", "stitches",
           "dust", "counters", "counters_traced", "counters_shut", "counter_open", "covered",
           "spill", "col_min_mm", "col_median_mm", "cross_min_mm", "columns", "trims", "jumps",
           "tiers", "seconds")


def table(rows) -> str:
    """The grid as a markdown table (ASCII)."""
    head = ["fixture", "cap", "wt", "floor", "stitches", "dust", "counters shut", "open",
            "covered", "spill", "narrowest col mm", "cross min mm", "trims"]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join([
            r["fixture"], f"{r['target_cap']:g}", str(r["thread_wt"]), "ON" if r["floor"] else "OFF",
            str(r["stitches"]), f"{r['dust']:.3f}", f"{r['counters_shut']}/{r['counters']}",
            f"{r['counter_open']:.2f}", f"{r['covered']:.2f}", f"{r['spill']:.2f}",
            f"{r['col_min_mm']:.2f}", f"{r['cross_min_mm']:.2f}", str(r["trims"])]) + " |")
    return "\n".join(out)


def write(out: Path, name: str, ref: dict, rows, img) -> None:
    out.mkdir(parents=True, exist_ok=True)
    flat = [dict(r, fixture=name, tiers=json.dumps(r["tiers"], sort_keys=True)) for r in rows]
    with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(flat)
    (out / f"{name}.json").write_text(json.dumps(
        dict(fixture=name, pinned=PINNED, ref_cap_per_width=ref["cap"],
             rows=[{k: v for k, v in r.items() if k != "per_counter"} for r in rows]),
        indent=1, default=float), encoding="utf-8")
    (out / f"{name}-table.txt").write_text(table(flat) + "\n", encoding="ascii")
    if img is not None:
        cv2.imwrite(str(out / f"{name}-sheet.png"), img)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True, choices=FIXTURES)
    ap.add_argument("--caps", default=",".join(f"{c:g}" for c in CAPS))
    ap.add_argument("--weights", default=",".join(str(w) for w in WEIGHTS))
    ap.add_argument("--out", required=True, help="directory for the csv / json / table / sheet")
    ap.add_argument("--ref", help="a reference JSON (testdata/small_print_synthetic_ref.json)")
    ap.add_argument("--ppm", type=int, default=30, help="sheet px/mm (0: no sheet)")
    a = ap.parse_args(argv)
    ref = json.loads(Path(a.ref).read_text()) if a.ref else None
    t0 = time.time()
    print(f"# pinned: {PINNED}", flush=True)
    ref, rows, img = census(
        a.fixture, [float(c) for c in a.caps.split(",")], [int(w) for w in a.weights.split(",")],
        ref, a.ppm or None,
        progress=lambda m: print(f"# cap {m['target_cap']:g} wt {m['thread_wt']} floor "
                                 f"{'ON' if m['floor'] else 'OFF'} [{m['seconds']} s]", flush=True))
    write(Path(a.out), a.fixture, ref, rows, img)
    print(table([dict(r, fixture=a.fixture) for r in rows]))
    print(f"# {len(rows)} cells, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
