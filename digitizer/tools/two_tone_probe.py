#!/usr/bin/env python
"""Defect 58's instrument: does `cfg.two_tone_snap` take a black-and-white
logo to two cones, and what does it cost? Measures; changes nothing.

Two modes.

`--detect` runs stage 0 and stage 1 on every image under `testdata/`,
`testdata/art/` and `testdata/photo/` and prints what `two_tone.detect`
reads on each — chroma share, the two modes, the mid-grey share and the
largest 8-level mid-grey bin — and whether it fires. That is the check the
gate's constants were set from (2026-10-08): it must fire on every
black-and-white logo and on nothing else.

The default mode digitizes each fixture at the Studio's config twice —
`two_tone_snap` off, then on — and prints cones, stitches, trims and the
per-colour stitch blocks for both. `--render DIR` writes off | on thread
renders side by side, one PNG per fixture.

    .venv/bin/python -m tools.two_tone_probe --detect
    .venv/bin/python -m tools.two_tone_probe
    .venv/bin/python -m tools.two_tone_probe --fixture art/logo_mfab_lc.png --render build/two_tone
    .venv/bin/python -m tools.two_tone_probe --json build/two_tone.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from digitizer_core import two_tone
from digitizer_core.stage0_classify import classify
from digitizer_core.stage1_prep import prep
from tools._console import utf8_console
from tools.eye_pairs.features import base_cfg, digitize_once
from tools.stroke_colour_probe import _blocks

# The nine images `--detect` fires on (2026-10-08) — seven black-and-white
# logos, the tires script and one synthetic fixture — then the
# controls: the colour logo the per-region stroke rule harmed, and the
# grey-and-black logo the plateau gate exists for. (path under testdata/,
# width mm, garment) — sizes as `tools/thin_strokes.REAL_ART`.
FIXTURES: dict[str, tuple[float, str]] = {
    "art/logo_golke_roofing.png": (80.0, "left_chest"),
    "art/logo_mfab_lc.png": (80.0, "left_chest"),
    "art/logo_mfab_hat.png": (80.0, "left_chest"),
    "art/logo_toat_beanie.png": (80.0, "left_chest"),
    "art/logo_toat_machine.png": (80.0, "left_chest"),
    "photo/logo_gaulke_roofing.png": (80.0, "left_chest"),
    "photo/screenshot_phone_ui_golke.jpg": (80.0, "left_chest"),
    "logo_script_tires.png": (80.0, "left_chest"),
    "black_ground_holes.png": (80.0, "left_chest"),
    "photo/logo_bridge_bar.jpg": (80.0, "left_chest"),
    "photo/logo_hotel_fremont.webp": (92.5, "patch"),
}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def detect_row(path: Path) -> dict:
    cfg = base_cfg(80.0, "left_chest")
    c = classify(path, cfg)
    p = prep(path, cfg, design_class=c.class_)
    px = p.rgb.reshape(-1, 3).astype(np.int16)
    tt = two_tone.detect(p.rgb)
    g = px.mean(1)
    hist = np.bincount(g.astype(np.int32), minlength=256)
    dark, light = int(np.argmax(hist[:128])), 128 + int(np.argmax(hist[128:]))
    lo, hi = dark + 0.2 * (light - dark), dark + 0.8 * (light - dark)
    mid = (g > lo) & (g < hi)
    bins = np.bincount((g[mid] / 8).astype(np.int32), minlength=32)
    return {"class": c.class_,
            "chroma_frac": round(float(np.mean(px.max(1) - px.min(1) > two_tone.CHROMA)), 4),
            "modes": (dark, light), "mid_frac": round(float(mid.mean()), 4),
            "max_mid_bin": round(float(bins.max()) / len(g), 4) if mid.any() else 0.0,
            "fires": tt is not None,
            "inks": (tt.dark, tt.light) if tt else None}


def records(design: dict) -> dict:
    blocks = _blocks(design)
    st = design.get("stitches") or []
    n = sum(1 for s in st if s["type"] == "stitch")
    return {"cones": len({c for c, _ in blocks}), "stitches": n,
            "trims": sum(1 for s in st if s["type"] == "trim"),
            "stops": sum(1 for s in st if s["type"] == "color"),
            "blocks": blocks}


def main(argv: list[str]) -> int:
    utf8_console()
    from tests.conftest import TESTDATA

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--detect", action="store_true",
                    help="print the detector's reading on every testdata image and stop")
    ap.add_argument("--fixture", action="append", default=None,
                    help="path under testdata/ (repeatable); default: FIXTURES")
    ap.add_argument("--render", type=Path, default=None)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)

    out: dict = {}
    if args.detect:
        paths = sorted(q for d in (TESTDATA, TESTDATA / "art", TESTDATA / "photo")
                       for q in d.iterdir() if q.suffix.lower() in IMAGE_EXT)
        print("| image | class | chroma>40 | modes | mid grey | max mid bin | fires |")
        print("|---|---|---|---|---|---|---|")
        for q in paths:
            rel = q.relative_to(TESTDATA).as_posix()
            try:
                r = detect_row(q)
            except Exception as e:  # noqa: BLE001 — a probe reports, it does not stop
                print(f"| `{rel}` | error: {type(e).__name__} | | | | | |")
                continue
            out[rel] = r
            print(f"| `{rel}` | {r['class']} | {r['chroma_frac']:.4f} | "
                  f"{r['modes'][0]}/{r['modes'][1]} | {r['mid_frac']:.4f} | "
                  f"{r['max_mid_bin']:.4f} | {'**yes**' if r['fires'] else 'no'} |", flush=True)
    else:
        print("| fixture | cones off → on | stitches off → on | trims off → on |")
        print("|---|---|---|---|")
        for name in args.fixture or list(FIXTURES):
            width_mm, garment = FIXTURES.get(name, (80.0, "left_chest"))
            rows, designs = [], []
            for on in (False, True):
                _g, _r, _p, design = digitize_once(
                    TESTDATA / name, base_cfg(width_mm, garment, two_tone_snap=on))
                rows.append(records(design))
                designs.append(design)
            a, b = rows
            out[name] = {"off": a, "on": b}
            print(f"| `{Path(name).stem}` | {a['cones']} → {b['cones']} "
                  f"| {a['stitches']:,} → {b['stitches']:,} | {a['trims']} → {b['trims']} |",
                  flush=True)
            for label, row in (("off", a), ("on", b)):
                print(f"|   {label} | " + ", ".join(f"{c} {n}" for c, n in row["blocks"]) + " | | |")
            if args.render:
                from digitizer_core.stitchviz import render_design
                args.render.mkdir(parents=True, exist_ok=True)
                pans = []
                for d in designs:
                    img = render_design(d)
                    k = 700.0 / img.shape[0]
                    pans.append(cv2.resize(img, (max(1, int(img.shape[1] * k)), 700),
                                           interpolation=cv2.INTER_AREA))
                gap = np.full((700, 12, 3), 255, np.uint8)
                cv2.imwrite(str(args.render / f"{Path(name).stem}.png"),
                            np.hstack([pans[0], gap, pans[1]]))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(out, indent=1, default=list), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
