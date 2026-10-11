#!/usr/bin/env python
"""Contact sheet for default-OFF flags: the same real-art fixture digitized
with a flag OFF and ON, drawn side by side with `stitchviz.render_design`,
cropped to where the two differ, each panel labelled with the flag, fixture
and stitches / trims / colour changes OFF -> ON. Evidence only: it flips no
default.

    .venv/bin/python -m tools.off_flags_sheet --flag two_tone_snap OUT_DIR
    .venv/bin/python -m tools.off_flags_sheet --flag satin_tip_corner_gate OUT_DIR
    .venv/bin/python -m tools.off_flags_sheet --flag lettering_columns OUT_DIR
    .venv/bin/python -m tools.off_flags_sheet --json-pair off.json on.json \\
        --label "..." --fixture name OUT_DIR/x.png      # a design built elsewhere (the JS engine)

`--flag lettering_columns` turns `lettering_words` on with it (the column lane
reads its text groups from the tagger). Panel rows write
`OUT_DIR/<flag>/<fixture>.png` plus `OUT_DIR/<flag>/rows.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from digitizer_core.stitchviz import DEFAULT_PX_PER_MM, UNITS_PER_MM, render_design

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# flag -> (config overrides when ON, [(fixture name in REAL_ART or testdata path, width mm, garment)])
FLAGS: dict[str, tuple[dict, list[tuple[str, float, str]]]] = {
    "two_tone_snap": ({"two_tone_snap": True}, [
        ("art/logo_mfab_lc.png", 80.0, "left_chest"),
        ("art/logo_toat_machine.png", 80.0, "left_chest"),
        ("art/logo_golke_roofing.png", 80.0, "left_chest"),
        ("art/logo_toat_beanie.png", 80.0, "left_chest"),
        ("art/logo_mfab_hat.png", 80.0, "left_chest"),
    ]),
    "satin_tip_corner_gate": ({"satin_tip_corner_gate": True}, [
        ("becker_marine_logo.png", 100.0, "left_chest"),
        ("photo/enthusiast_logo.png", 80.0, "left_chest"),
        ("photo/logo_hotel_fremont.webp", 92.5, "patch"),
    ]),
    "lettering_columns": ({"lettering_columns": True, "lettering_words": True}, [
        ("becker_marine_logo.png", 100.0, "left_chest"),
        ("photo/enthusiast_logo.png", 80.0, "left_chest"),
        ("photo/logo_hotel_fremont.webp", 92.5, "patch"),
    ]),
}

PANEL_H = 620
FONT = cv2.FONT_HERSHEY_SIMPLEX


def counts(design: dict) -> dict:
    s = design.get("stitches") or []
    return {
        "stitches": sum(1 for r in s if r["type"] == "stitch"),
        "trims": sum(1 for r in s if r["type"] == "trim"),
        "colours": sum(1 for r in s if r["type"] == "color"),
    }


def _corners(designs: list[dict]) -> list[dict]:
    """Prepend two corner jumps spanning the union of the stitches, so both
    designs render on one frame (a jump draws nothing but sets the bounds)."""
    xs, ys = [], []
    for d in designs:
        for r in d["stitches"]:
            if r["type"] in ("stitch", "jump"):
                xs.append(r["x"]); ys.append(r["y"])
    c = [{"type": "jump", "x": min(xs), "y": min(ys)}, {"type": "jump", "x": max(xs), "y": max(ys)}]
    return [dict(d, stitches=c + d["stitches"]) for d in designs]


def diff_box(a: np.ndarray, b: np.ndarray) -> tuple[int, int, int, int]:
    """Box (x0, y0, x1, y1) round the biggest cluster of changed pixels, or the
    whole frame if nothing differs."""
    h, w = a.shape[:2]
    d = (np.abs(a.astype(int) - b.astype(int)).sum(axis=2) > 60).astype(np.uint8)
    if not d.any():
        return 0, 0, w, h
    k = int(DEFAULT_PX_PER_MM * 3)
    m = cv2.dilate(d, np.ones((k, k), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    # score components by changed pixels they hold, merge those within reach by
    # taking the box round every component holding >= 15% of the biggest's change
    held = [(int(d[lab == i].sum()), i) for i in range(1, n)]
    top = max(h_ for h_, _ in held)
    keep = [i for h_, i in held if h_ >= 0.15 * top]
    x0 = min(stats[i, 0] for i in keep); y0 = min(stats[i, 1] for i in keep)
    x1 = max(stats[i, 0] + stats[i, 2] for i in keep); y1 = max(stats[i, 1] + stats[i, 3] for i in keep)
    return int(x0), int(y0), int(x1), int(y1)


def _label(img: np.ndarray, lines: list[str], scale: float = 0.55) -> np.ndarray:
    pad = 8 + 22 * len(lines)
    bar = np.full((pad, img.shape[1], 3), 255, np.uint8)
    for i, t in enumerate(lines):
        cv2.putText(bar, t, (6, 22 + 22 * i), FONT, scale, (30, 30, 30), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def _mark_trims(img: np.ndarray, design: dict, frame_design: dict) -> None:
    """Ring every `trim` (a cut thread) in red, on the frame `frame_design` fixes."""
    from digitizer_core.stitchviz import _frame
    (_h, _w), to_px = _frame(frame_design["stitches"], DEFAULT_PX_PER_MM, 2.0)
    for r in design["stitches"]:
        if r["type"] == "trim":
            cv2.circle(img, to_px(r), 5, (0, 0, 220), 2, cv2.LINE_AA)


def _densest(a: np.ndarray, b: np.ndarray, mm: float) -> tuple[int, int, int, int]:
    d = (np.abs(a.astype(int) - b.astype(int)).sum(axis=2) > 60).astype(np.float32)
    k = int(mm * DEFAULT_PX_PER_MM)
    s = cv2.boxFilter(d, -1, (k, k), normalize=False)
    y, x = np.unravel_index(int(np.argmax(s)), s.shape)
    h, w = d.shape
    x0 = int(min(max(0, x - k // 2), max(0, w - k))); y0 = int(min(max(0, y - k // 2), max(0, h - k)))
    return x0, y0, min(w, x0 + k), min(h, y0 + k)


def sheet(flag: str, fixture: str, off: dict, on: dict, note: str = "",
          mark_trims: bool = False, zoom_mm: float = 0.0) -> tuple[np.ndarray, dict]:
    doff, don = _corners([off, on])
    a, b = render_design(doff), render_design(don)
    if mark_trims:
        _mark_trims(a, off, doff)
        _mark_trims(b, on, don)
    if zoom_mm:
        whole, _ = _sheet_panels(flag, fixture, off, on, a, b, (0, 0, a.shape[1], a.shape[0]), note + " | whole design")
        zoom, m = _sheet_panels(flag, fixture, off, on, a, b, _densest(a, b, zoom_mm), f"{note} | zoom: the {zoom_mm:g} mm window with most change")
        return stack([whole, zoom]), m
    return _sheet_panels(flag, fixture, off, on, a, b, diff_box(a, b), note)


def _sheet_panels(flag, fixture, off, on, a, b, box, note):
    x0, y0, x1, y1 = box
    h, w = a.shape[:2]
    pad = 0 if box == (0, 0, w, h) else int(DEFAULT_PX_PER_MM * 4)
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    ca, cb = off_c = counts(off), counts(on)
    panels = []
    for img, tag in ((a, "OFF"), (b, "ON")):
        crop = img[y0:y1, x0:x1]
        k = PANEL_H / crop.shape[0]
        crop = cv2.resize(crop, (max(1, int(crop.shape[1] * k)), PANEL_H), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
        cv2.rectangle(crop, (0, 0), (crop.shape[1] - 1, crop.shape[0] - 1), (160, 160, 160), 1)
        panels.append((crop, tag))
    width = panels[0][0].shape[1] + panels[1][0].shape[1] + 14
    lines = [f"{flag}  |  {fixture}"
             + (f"  |  {note}" if note else ""),
             f"stitches {ca['stitches']:,} -> {cb['stitches']:,}   trims {ca['trims']} -> {cb['trims']}   "
             f"colour changes {ca['colours']} -> {cb['colours']}"]
    gap = np.full((PANEL_H, 14, 3), 255, np.uint8)
    row = np.hstack([panels[0][0], gap, panels[1][0]])
    for (crop, tag), ox in zip(panels, (0, panels[0][0].shape[1] + 14)):
        cv2.putText(row, tag, (ox + 10, 28), FONT, 0.9, (0, 0, 200) if tag == "ON" else (60, 60, 60), 2, cv2.LINE_AA)
    # header at least as wide as the lines need
    need = 12 + 9 * max(len(s) for s in lines)
    if row.shape[1] < need:
        row = np.hstack([row, np.full((PANEL_H, need - row.shape[1], 3), 255, np.uint8)])
    return _label(row, lines), {"fixture": fixture, "off": ca, "on": cb}


def stack(rows: list[np.ndarray]) -> np.ndarray:
    w = max(r.shape[1] for r in rows)
    out = []
    for r in rows:
        if r.shape[1] < w:
            r = np.hstack([r, np.full((r.shape[0], w - r.shape[1], 3), 255, np.uint8)])
        out += [r, np.full((16, w, 3), 255, np.uint8)]
    return np.vstack(out[:-1])


def run_flag(flag: str, out: Path, only: list[str] | None) -> None:
    from tests.conftest import TESTDATA
    from tools.eye_pairs.features import base_cfg, digitize_once

    on_kw, fixtures = FLAGS[flag]
    d = out / flag
    d.mkdir(parents=True, exist_ok=True)
    meta = []
    for name, width, garment in fixtures:
        if only and name not in only:
            continue
        designs = []
        for on in (False, True):
            _g, _r, _p, design = digitize_once(TESTDATA / name, base_cfg(width, garment, **(on_kw if on else {})))
            designs.append(design)
        img, m = sheet(flag, name, *designs, note=f"{width:g} mm, {garment}")
        stem = Path(name).stem
        cv2.imwrite(str(d / f"{stem}.png"), img)
        json.dump({"off": designs[0], "on": designs[1]}, open(d / f"{stem}.designs.json", "w"))
        m["changed"] = designs[0] != designs[1]
        meta.append(m)
        print(flag, name, m, flush=True)
    (d / "rows.json").write_text(json.dumps(meta, indent=1))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--flag", choices=sorted(FLAGS))
    ap.add_argument("--only", action="append")
    ap.add_argument("--json-pair", nargs=2, type=Path)
    ap.add_argument("--label", default="")
    ap.add_argument("--fixture", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--mark-trims", action="store_true")
    ap.add_argument("--zoom-mm", type=float, default=0.0)
    a = ap.parse_args(argv)
    if a.json_pair:
        off, on = (json.loads(p.read_text()) for p in a.json_pair)
        img, m = sheet(a.label, a.fixture, off, on, a.note, a.mark_trims, a.zoom_mm)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(a.out), img)
        print(m)
        return 0
    run_flag(a.flag, a.out, a.only)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
