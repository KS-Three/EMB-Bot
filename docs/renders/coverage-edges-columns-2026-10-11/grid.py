"""Becker under the 2x2 grid: coverage_edges {off,on} x the Column lane
(lettering_columns + lettering_words) {off,on}, at 50 and 80 mm.

No new instrument. Every number is an existing one, read from ONE digitize
per cell:

- `tools.eye_pairs.features.features_design_only` -- `lost_frac` and its two
  halves (`unsewn_frac`, `overshoot_frac`), the colour-free
  `uncovered_ink_frac` / `uncovered_elements`, `ragged_mm`, `hausdorff_mm`
  (`dropped_elements` and `edge_smoothness` on one registration);
- `tools.fan_census` -- over-long and fan satin crosses per text-tagged
  letter, and bare satin-shape area carrying no thread of any kind
  (`bare_anatomy.components(all_thread=True)`), each split MARINE / BECKER
  by the letter's centroid;
- stitches, trims, and the pipeline's warning codes.

Run from `digitizer/` with the digitizer venv:

    python ../docs/renders/coverage-edges-columns-2026-10-11/grid.py OUTDIR

Writes OUTDIR/grid.json and OUTDIR/marine-<w>mm-thread.jpg and
-needle.jpg: the four MARINE crops as a 2x2 sheet, one cell per arm
(top: skeleton tier, bottom: Column lane; left: shipped outline, right:
coverage outline). Every crop is 1600 px for the design's width.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

DIG = Path.cwd()
sys.path.insert(0, str(DIG))
sys.path.insert(0, str(DIG / "tools"))

from digitizer_core.stitchviz import render_design, render_penetrations  # noqa: E402
from tools.bare_anatomy import components                                 # noqa: E402
from tools.eye_pairs.features import (base_cfg, digitize_once,             # noqa: E402
                                      features_design_only)
from tools.fan_census import crosses_of, fan_stats                         # noqa: E402

ART = DIG / "testdata" / "becker_marine_logo.png"
WIDTHS = (50.0, 80.0)
ARMS = {
    "shipped": {},
    "coverage_edges": {"coverage_edges": True},
    "columns_words": {"lettering_columns": True, "lettering_words": True},
    "coverage_columns": {"coverage_edges": True, "lettering_columns": True,
                         "lettering_words": True},
}
PAD_MM = 2.0
# MARINE is the lower line: its crop starts this far down the design's height.
MARINE_FROM = 0.62


def letter_rows(res, plan):
    letters = [r for r in res.regions if r.meta.get("text_candidate")]
    if not letters:
        return [], [], 0.0
    ys = [r.polygon.centroid.y for r in letters]
    mid = (min(ys) + max(ys)) / 2.0
    rows = []
    for r in letters:
        W = 2 * r.polygon.area / max(r.polygon.length, 1e-9)
        cr, _k = crosses_of(plan, r.shape_id)
        st = fan_stats(cr, W)
        st.pop("lengths"), st.pop("angles")
        st["shape_id"] = r.shape_id
        st["x"] = r.polygon.centroid.x
        # Stage coordinates run y DOWN: MARINE (the lower line) is the larger y.
        st["line"] = "MARINE" if r.polygon.centroid.y > mid else "BECKER"
        rows.append(st)
    comps = components({r.shape_id: r.polygon for r in res.regions}, plan, all_thread=True)
    return letters, rows, comps


def sums(rows, comps, line):
    sel = sorted((s for s in rows if s["line"] == line), key=lambda s: s["x"])
    ids = {s["shape_id"] for s in sel}
    tot = sum(s["thread"] for s in sel)
    return dict(
        letters=len(sel),
        # Left to right, one per tagged shape: which letters carry the long crosses.
        long_by_letter=[s["long_crosses"] for s in sel],
        crosses=sum(s["crosses"] for s in sel),
        long_crosses=sum(s["long_crosses"] for s in sel),
        long_share=round(float(sum(s["long_share"] * s["thread"] for s in sel)) / tot, 4) if tot else 0.0,
        fan_crosses=sum(s["fan_crosses"] for s in sel),
        fan_letters=sum(1 for s in sel if s["fan_share"] > 0.05 and s["fan_crosses"] >= 3),
        bare_mm2=round(sum(c[0] for c in comps if c[3] in ids), 2))


def main(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {}
    for width in WIDTHS:
        ppm = 1600.0 / width          # every crop the same pixel width
        thread_tiles, needle_tiles = [], []
        for arm, kw in ARMS.items():
            t = time.time()
            cfg = base_cfg(width, "left_chest", **kw)
            gen, res, plan, design = digitize_once(ART, cfg)
            row = features_design_only(ART, design)
            row.pop("notes", None)
            letters, rows, comps = letter_rows(res, plan)
            row["marine"] = sums(rows, comps, "MARINE")
            row["becker_line"] = sums(rows, comps, "BECKER")
            row["trims"] = plan.stats.trims
            row["warnings"] = dict(Counter(w.get("code") for w in res.warnings))
            row["secs"] = round(time.time() - t)
            report[f"{int(width)}mm/{arm}"] = row
            print(f"{int(width)}mm {arm:17} st {row['stitches']} trims {row['trims']} "
                  f"lost {row['lost_frac']} unsewn {row['unsewn_frac']} over {row['overshoot_frac']} "
                  f"uncov {row['uncovered_ink_frac']} ragged {row['ragged_mm']} "
                  f"haus {row['hausdorff_mm']} M {row['marine']} {row['secs']}s", flush=True)

            for render, tiles in ((render_design, thread_tiles),
                                  (render_penetrations, needle_tiles)):
                img = render(design, px_per_mm=ppm, pad_mm=PAD_MM)
                pad = int(PAD_MM * ppm)
                content = img.shape[0] - 2 * pad
                y0 = pad + int(MARINE_FROM * content) - pad // 2
                crop = img[y0:, :].copy()
                bar = np.full((34, crop.shape[1], 3), 235, np.uint8)
                cv2.putText(bar, f"{arm}  ({int(width)} mm)", (8, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2, cv2.LINE_AA)
                tiles.append(np.vstack([bar, crop]))
            (out / "grid.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

        for name, tiles in (("thread", thread_tiles), ("needle", needle_tiles)):
            H = max(t.shape[0] for t in tiles)
            Wd = max(t.shape[1] for t in tiles)
            tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, Wd - t.shape[1],
                                        cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
            gap = np.full((H, 10, 3), 120, np.uint8)
            top = np.hstack([tiles[0], gap, tiles[1]])
            bot = np.hstack([tiles[2], gap, tiles[3]])
            sheet = np.vstack([top, np.full((10, top.shape[1], 3), 120, np.uint8), bot])
            # JPEG: the four PNG sheets ran 6.9 MB in a public repo.
            cv2.imwrite(str(out / f"marine-{int(width)}mm-{name}.jpg"), sheet,
                        [cv2.IMWRITE_JPEG_QUALITY, 88])
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
