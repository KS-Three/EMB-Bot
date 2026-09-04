"""The sew-out gate card — ONE hooping that settles every parameter question
currently gated on physical evidence (2026-07-31).

Five labeled blocks, one thread color each, A/B (or A/B/C) variants side by
side. Kent sews it once on the Tajima and reads the answers off the fabric
with the paper key (docs/sewout-card-2026-07-31.md).

  1  LOCK LENGTH   TIE_STITCH_MM 0.8 (ours) vs 0.45 (pro corpus median)
  2  FILL DENSITY  FILL_ROW_MM 0.40 | 0.20 | two 0.40 passes offset 0.20
  3  WIDE SATIN    columns at 3 / 4 / 5 mm, current emitter as-is
  4  TRAVEL RUN    running stitch 2.5 (ours) vs 2.0 (corpus 2.02), straight+curve
  5  SMALL TEXT    words at 4 / 5 / 6 mm cap height through the real pipeline

Everything is composed in plan space (mm, y-DOWN, like stage 4) and handed to
`adapter.plan_to_design`, which owns the one y-flip into the browser Design
contract (0.1 mm ints, +y UP). The DST itself is written by the BROWSER
encoder via tools/sewout_bridge.mjs — the browser codec is the one with sew
evidence on Kent's machine (docs/dst-axis-verdict-2026-07-31.md), and the two
codecs disagree on axis convention, so nothing here touches pystitch for
the machine file.

Constant plumbing, verified while building (probed, not assumed):

  * `tie_run` reads `machine.TIE_STITCH_MM` at CALL time, so the per-bar
    monkeypatch in block 1 works; the generator asserts the spliced tie leg
    actually equals the patched value before trusting the card.
  * stage7_sequence.py line 32 BAKES FILL_ROW_MM / FILL_STITCH_MM /
    SATIN_MAX_WIDTH_MM / TINY_STITCH_MM at import (`from .machine import`),
    so fill density is varied through `stitch_shape(row_mm=...)` — the same
    parameter `cfg.fill_row_mm` feeds — never by patching machine.FILL_ROW_MM.
  * Fill rows anchor to the polygon's own bounds (`_row_spans`:
    y = miny + row_mm*(i+0.5)), so the interleave pass is offset by extending
    the polygon 0.20 mm past its top edge (anchor spoof) — translating the
    polygon moves the anchor with it and offsets nothing. Probed below.

Usage (from digitizer/):
  PYTHONPATH=. .venv/Scripts/python tools/sewout_card.py            # generate
  PYTHONPATH=. .venv/Scripts/python tools/sewout_card.py --check-dst \
      debug_out/sewout/EMBBOT_SEWOUT_CARD.dst                       # pystitch sanity

Then, from the repo root:
  node tools/sewout_bridge.mjs   # encode with the browser codec + verify + preview
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import box

from digitizer_core import machine
from digitizer_core.adapter import design_size_mm, plan_to_design
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.stage6_fill import stitch_shape
from digitizer_core.stage6_satin import satin_shape
from digitizer_core.stage7_sequence import _apply_ties
from digitizer_core.stitches import (SATIN, TRAVEL, StitchBlock, StitchPlan,
                                     StitchRun, tie_run)
from digitizer_core.threads import CHART

ROOT = Path(__file__).resolve().parent.parent          # digitizer/
OUT = ROOT / "debug_out" / "sewout"
ART = OUT / "art"

# Default fabric (pique_knit) values, spelled out so the card does not shift
# under a future preset change: this file documents exactly what was sewn.
TRIM_AT = 3.0
FILL_UNDERLAY = "edge_lattice"
SATIN_UNDERLAY = "center_run"

# Regular weight: the honest small-text test. Arial on Kent's machine; a
# cloud/Linux build falls back to Liberation Sans, the metric-compatible
# Arial substitute — same advance widths, slightly different glyph outlines,
# so block 5's letterforms differ a hair between the two builds while every
# other block is byte-identical. A card sewn for block 5 specifically should
# be built where Arial lives.
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
import os as _os
FONT = next((f for f in _FONT_CANDIDATES if _os.path.exists(f)), None)
if FONT is None:
    raise SystemExit(
        "sewout_card: no usable font found; tried:\n  " + "\n  ".join(_FONT_CANDIDATES))


# --- small helpers ----------------------------------------------------------

def translate(runs: list[StitchRun], dx: float, dy: float) -> list[StitchRun]:
    for r in runs:
        r.points = [(x + dx, y + dy) for x, y in r.points]
    return runs


def link(prev_end: tuple[float, float] | None, runs: list[StitchRun]) -> None:
    """Stage 7's inter-shape rule: needle-up if the hop is real, cut if long."""
    if prev_end is None or not runs:
        return
    d = math.dist(prev_end, runs[0].points[0])
    if d >= machine.TINY_STITCH_MM:
        runs[0].jump = True
        runs[0].trim = d > TRIM_AT
    if d > TRIM_AT:
        runs[0].trim = True


def zigzag_bar(x0: float, y0: float, length: float, width: float,
               spacing: float = machine.SATIN_SPACING_MM) -> list[tuple[float, float]]:
    """A plain horizontal satin column: crosses every `spacing` mm, no underlay.

    Deliberately naked — block 1 varies ONLY the lock stitch, so both bars
    must be identical everywhere else.
    """
    n = int(round(length / spacing))
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        x = x0 + i * (length / n)
        pts.append((x, y0))
        pts.append((x, y0 + width))
    return pts


def sine_path(x0: float, y0: float, span: float, amp: float,
              step: float) -> list[tuple[float, float]]:
    """One full S (sine period) resampled at constant arc length `step`."""
    t = np.linspace(0.0, 1.0, 4001)
    xs = x0 + span * t
    ys = y0 + amp * np.sin(2 * math.pi * t)
    seg = np.hypot(np.diff(xs), np.diff(ys))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(s[-1])
    n = max(2, int(math.ceil(total / step)))
    want = np.linspace(0.0, total, n + 1)
    px = np.interp(want, s, xs)
    py = np.interp(want, s, ys)
    return list(zip(px.tolist(), py.tolist()))


def runs_bbox(all_runs) -> tuple[float, float, float, float]:
    x0 = y0 = math.inf
    x1 = y1 = -math.inf
    for r in all_runs:
        for x, y in r.points:
            x0, y0 = min(x0, x), min(y0, y)
            x1, y1 = max(x1, x), max(y1, y)
    return x0, y0, x1, y1


def fill_row_ys(runs: list[StitchRun]) -> list[float]:
    """Distinct y levels of the FILL rows in a horizontal-angle fill."""
    ys: set[float] = set()
    for r in runs:
        if r.kind == "fill":
            for _, y in r.points:
                ys.add(round(y, 4))
    return sorted(ys)


# --- block builders (card space: mm, y-down, origin top-left) ---------------

def block1_lock() -> tuple[list[StitchRun], dict]:
    """Two identical naked satin bars; only TIE_STITCH_MM differs (0.8 vs 0.45).

    Ties are spliced manually (same fold `_apply_ties` uses) with
    machine.TIE_STITCH_MM monkeypatched per bar, and the resulting leg length
    is asserted — the probe that proves the constant is read at call time.
    """
    bars = [
        {"x0": 0.0, "tie": 0.80, "label": "A ours 0.8"},
        {"x0": 22.0, "tie": 0.45, "label": "B corpus 0.45"},
    ]
    runs: list[StitchRun] = []
    info = []
    default = machine.TIE_STITCH_MM
    for bar in bars:
        machine.TIE_STITCH_MM = bar["tie"]
        try:
            pts = zigzag_bar(bar["x0"], 1.0, 14.0, 2.2)
            run = StitchRun(points=pts, kind=SATIN, jump=True, trim=True,
                            shape_id=f"lock-{bar['label'][0]}")
            head = tie_run(run.points[0], run.points[1]).points
            run.points = head[:-1] + run.points
            tail = tie_run(run.points[-1], run.points[-2]).points
            run.points = run.points + tail[1:]
        finally:
            machine.TIE_STITCH_MM = default
        leg = math.dist(run.points[0], run.points[1])
        assert abs(leg - bar["tie"]) < 1e-6, (
            f"tie leg {leg:.3f} != patched {bar['tie']} — TIE_STITCH_MM no "
            "longer read at call time; card invalid")
        runs.append(run)
        info.append({"bar": bar["label"], "tie_mm": bar["tie"],
                     "tie_leg_measured": round(leg, 4), "points": len(run.points)})
    return runs, {"bars": info}


def block2_fill() -> tuple[list[StitchRun], dict]:
    """Three 15x15 fill squares: 0.40 | 0.20 | 0.40 x2 interleaved (+0.20).

    All via stage 6's real emitter (`stitch_shape`) at a forced 0 deg angle so
    rows are horizontal and the three squares compare like for like. The
    interleave second pass runs on a polygon whose TOP edge is extended by
    exactly half a row spacing: rows anchor to poly.bounds, so the extension
    shifts every row -0.20 relative to pass 1 without moving the footprint
    (no row lands inside the 0.2 mm sliver: the first sits exactly on the
    original top edge). Probed below by measuring actual row y's.
    """
    y0 = 7.2
    sq = 15.0
    runs: list[StitchRun] = []
    cursor = None
    info = {}

    def emit(poly, row_mm, underlay, tag):
        nonlocal cursor
        r, rep = stitch_shape(poly, tag, angle_deg=0.0, row_mm=row_mm,
                              stitch_mm=machine.FILL_STITCH_MM,
                              underlay_style=underlay, trim_at_mm=TRIM_AT,
                              start_near=cursor)
        link(cursor, r)
        runs.extend(r)
        cursor = r[-1].points[-1]
        info[tag] = {"row_mm": row_mm, "underlay": underlay,
                     "points": sum(len(x.points) for x in r), "report": rep}
        return r

    emit(box(0.0, y0, sq, y0 + sq), 0.40, FILL_UNDERLAY, "fill-A-0.40")
    emit(box(20.0, y0, 20.0 + sq, y0 + sq), 0.20, FILL_UNDERLAY, "fill-B-0.20")

    # C: pass 1 exactly like A, pass 2 fill-only on the anchor-spoofed polygon.
    pass1 = emit(box(40.0, y0, 40.0 + sq, y0 + sq), 0.40, FILL_UNDERLAY, "fill-C-pass1")
    spoof = box(40.0, y0 - 0.20, 40.0 + sq, y0 + sq)
    pass2 = emit(spoof, 0.40, "none", "fill-C-pass2")

    ys1, ys2 = fill_row_ys(pass1), fill_row_ys(pass2)
    # Rows of pass 2 must sit half a spacing off pass 1's rows.
    off = [min(abs(y2 - y1) for y1 in ys1) for y2 in ys2[1:-1]]
    med = sorted(off)[len(off) // 2]
    assert 0.15 <= med <= 0.25, (
        f"interleave offset {med:.3f} mm, wanted ~0.20 — row anchoring changed; "
        "card invalid")
    info["interleave_offset_mm"] = round(med, 4)
    info["rows_pass1"] = len(ys1)
    info["rows_pass2"] = len(ys2)
    return runs, info


def block3_wide_satin() -> tuple[list[StitchRun], dict]:
    """Satin columns at 3 / 4 / 5 mm width, the current emitter untouched.

    All three genuinely classify as satin under SATIN_MAX_WIDTH_MM 5.0
    (ribbon widths 2.68 / 3.45 / 4.17); calling `satin_shape` directly skips
    only the classifier, not the emitter. Underlay is the fabric default —
    the emitter itself upgrades every column past SATIN_ZIGZAG_ABOVE_MM 2.5
    to zigzag, which is part of what the sew-out judges.
    """
    tops = [(27.2, 3.0), (35.2, 4.0), (44.2, 5.0)]
    runs: list[StitchRun] = []
    cursor = None
    info = []
    for top, w in tops:
        r, rep = satin_shape(box(0.0, top, 25.0, top + w), f"satin-{w:g}mm",
                             underlay_style=SATIN_UNDERLAY, trim_at_mm=TRIM_AT,
                             start_near=cursor)
        assert r, f"satin emitter produced nothing at {w} mm"
        link(cursor, r)
        runs.extend(r)
        cursor = r[-1].points[-1]
        info.append({"width_mm": w, "points": sum(len(x.points) for x in r),
                     "report": rep})
    return runs, {"bars": info}


def block4_travel() -> tuple[list[StitchRun], dict]:
    """Running paths at 2.5 (ours) vs 2.0 (corpus): a straight and an S each."""
    y = 54.2
    paths = [
        ("straight-A-2.5", [( (0.0 + i * 2.5), y) for i in range(13)]),
        ("straight-B-2.0", [( (0.0 + i * 2.0), y + 4.0) for i in range(16)]),
        ("curve-A-2.5", sine_path(36.0, y + 5.0, 30.0, 5.0, 2.5)),
        ("curve-B-2.0", sine_path(36.0, y + 17.0, 30.0, 5.0, 2.0)),
    ]
    runs: list[StitchRun] = []
    info = []
    for tag, pts in paths:
        runs.append(StitchRun(points=pts, kind=TRAVEL, jump=True, trim=True,
                              shape_id=tag))
        steps = [math.dist(pts[i - 1], pts[i]) for i in range(1, len(pts))]
        info.append({"path": tag, "points": len(pts),
                     "step_mm": round(sum(steps) / len(steps), 3)})
    return runs, {"paths": info}


def _word_art(word: str, cap_mm: float) -> tuple[Path, float]:
    """Render `word` and return (png path, target_width_mm for that cap height).

    All-caps sans ink height IS the cap height, so the scale factor is exact.
    """
    font = ImageFont.truetype(FONT, 280)
    img = Image.new("L", (1400, 500), 255)
    ImageDraw.Draw(img).text((60, 100), word, font=font, fill=0)
    arr = np.array(img)
    ink = arr < 128
    rows = np.where(ink.any(axis=1))[0]
    cols = np.where(ink.any(axis=0))[0]
    r0, r1, c0, c1 = rows[0], rows[-1], cols[0], cols[-1]
    pad = 40
    crop = img.crop((max(0, c0 - pad), max(0, r0 - pad),
                     min(img.width, c1 + pad + 1), min(img.height, r1 + pad + 1)))
    out = ART / f"word_{word}_{cap_mm:g}mm.png"
    crop.convert("RGB").save(out)
    ink_w_px = int(c1 - c0 + 1)
    ink_h_px = int(r1 - r0 + 1)
    return out, ink_w_px * cap_mm / ink_h_px


def block5_text() -> tuple[list[StitchRun], dict]:
    """Words at 4 / 5 / 6 mm cap height through the FULL pipeline, plus one at
    2.5 mm where the run-tier rescue actually engages.

    Whatever tier stage 7 routes each letter to (satin, fill fallback, or the
    run-tier rescue) is the finding — nothing is forced. Probed while
    building: with Arial regular the rescue floor sits at ~3 mm cap (3.0 mm =
    mixed run+satin, 2.5 mm = pure run tier, 4 mm and up = all thin satin) —
    so the 4/5/6 tiers judge thin-satin legibility and the 2.5 mm word is the
    run-tier specimen the "rescue vs satin" question needs on fabric. The
    word plans come back already tied and trimmed by the real stage 7, so
    this block must NOT go through `_apply_ties` again.
    """
    slots = [("SEW", 4.0, 0.0), ("OUT", 5.0, 17.0), ("EMB", 6.0, 36.0),
             ("INC", 2.5, 58.0)]
    base = 88.2   # shared baseline: bottoms align, size is the only variable
    runs: list[StitchRun] = []
    cursor = None
    info = []
    for word, cap, x_left in slots:
        art, target_w = _word_art(word, cap)
        result, plan = digitize(str(art), PipelineConfig(target_width_mm=target_w))
        wruns = [r for b in plan.blocks for r in b.runs if r.points]
        assert wruns, f"pipeline produced no stitches for {word} at {cap} mm"
        x0, y0, x1, y1 = runs_bbox(wruns)
        translate(wruns, x_left - x0, (base - cap) - y0)
        link(cursor, wruns)
        runs.extend(wruns)
        cursor = wruns[-1].points[-1]
        kinds = sorted({r.kind for r in wruns})
        info.append({
            "word": word, "cap_mm": cap, "target_width_mm": round(target_w, 2),
            "points": sum(len(r.points) for r in wruns),
            "run_kinds": kinds,
            "warnings": [w["code"] for w in plan.warnings],
        })
    return runs, {"words": info}


SEAM_RUNGS = (0.0, 0.25, 0.5, 1.0)   # how far A reaches under B, mm
_SEAM_Y = 91.0                        # below block 5's 88.2 baseline; card stays under 100 mm tall
_SEAM_W, _SEAM_H = 7.5, 6.0           # each half of a pair; four pairs + 2 mm gaps = 66 mm, the card's width


def _seam_pairs():
    """-> [(x_left, rung)] for the four abutting pairs, left to right."""
    return [(k * (2 * _SEAM_W + 2.0), d) for k, d in enumerate(SEAM_RUNGS)]


def block6_seam_a() -> tuple[list[StitchRun], dict]:
    """Four 7.5 x 6 mm fills, the LEFT half of four abutting pairs, sewn first.
    Each reaches under its right-hand partner by its rung: 0 / 0.25 / 0.5 /
    1.0 mm (stage 5's `overlap_mm` is 0.25 — pair 2 is what ships). Rows run
    horizontal, ACROSS the seam, so pull draws the row ends back from it:
    the case the underlap exists for."""
    runs: list[StitchRun] = []
    cursor = None
    info = {}
    for x, d in _seam_pairs():
        r, rep = stitch_shape(box(x, _SEAM_Y, x + _SEAM_W + d, _SEAM_Y + _SEAM_H), f"seam-A-{d:g}",
                              angle_deg=0.0, row_mm=machine.FILL_ROW_MM,
                              stitch_mm=machine.FILL_STITCH_MM, underlay_style=FILL_UNDERLAY,
                              trim_at_mm=TRIM_AT, start_near=cursor)
        link(cursor, r)
        runs.extend(r)
        cursor = r[-1].points[-1]
        info[f"A-{d:g}"] = {"underlap_mm": d, "points": sum(len(x_.points) for x_ in r), "report": rep}
    return runs, info


def block6_seam_b() -> tuple[list[StitchRun], dict]:
    """The RIGHT halves, sewn after A in a second colour, each to its exact
    artwork boundary — the later colour never grows back over the earlier."""
    runs: list[StitchRun] = []
    cursor = None
    info = {}
    for x, d in _seam_pairs():
        r, rep = stitch_shape(box(x + _SEAM_W, _SEAM_Y, x + 2 * _SEAM_W, _SEAM_Y + _SEAM_H), f"seam-B-{d:g}",
                              angle_deg=0.0, row_mm=machine.FILL_ROW_MM,
                              stitch_mm=machine.FILL_STITCH_MM, underlay_style=FILL_UNDERLAY,
                              trim_at_mm=TRIM_AT, start_near=cursor)
        link(cursor, r)
        runs.extend(r)
        cursor = r[-1].points[-1]
        info[f"B-{d:g}"] = {"partner_underlap_mm": d, "points": sum(len(x_.points) for x_ in r), "report": rep}
    return runs, info


# --- assembly ----------------------------------------------------------------

BLOCKS = [
    ("1 LOCK",   block1_lock,      (222, 36, 36),   True),   # ties pre-applied
    ("2 FILL",   block2_fill,      (36, 90, 210),   False),
    ("3 WSATIN", block3_wide_satin, (34, 150, 84),  False),
    ("4 TRAVEL", block4_travel,    (30, 30, 30),    False),
    ("5 TEXT",   block5_text,      (128, 52, 180),  True),   # pipeline tied them
    ("6 SEAMA",  block6_seam_a,    (222, 130, 40),  False),  # the earlier colour, reaching under
    ("6 SEAMB",  block6_seam_b,    (40, 120, 222),  False),  # the later colour, to its edge
]


def build_card() -> tuple[StitchPlan, dict]:
    blocks: list[StitchBlock] = []
    palette: list[dict] = []
    report: dict = {"blocks": {}}
    prev_end = None
    all_runs: list[StitchRun] = []

    snapped = CHART.snap_palette(np.array([rgb for _, _, rgb, _ in BLOCKS], float))
    for (name, builder, _rgb, self_tied), ti in zip(BLOCKS, snapped):
        runs, info = builder()
        link(prev_end, runs)
        runs[0].jump = True
        runs[0].trim = True
        if not self_tied:
            _apply_ties(runs)     # the real stage-7 tie pass, default TIE 0.8
        thread = CHART[ti]
        blocks.append(StitchBlock(thread_index=ti, thread_number=thread.number,
                                  rgb=tuple(thread.rgb), runs=runs))
        palette.append({"brand": "isacord", "number": thread.number,
                        "name": f"{name}", "rgb": list(thread.rgb)})
        prev_end = runs[-1].points[-1]
        all_runs.extend(runs)
        report["blocks"][name] = info

    # Recenter: the Design contract puts the origin at the design center.
    x0, y0, x1, y1 = runs_bbox(all_runs)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    for r in all_runs:
        r.points = [(x - cx, y - cy) for x, y in r.points]

    plan = StitchPlan(blocks=blocks, palette=palette,
                      design_size_mm=(x1 - x0, y1 - y0))
    return plan, report


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)

    plan, report = build_card()
    stats = plan.stats
    design = plan_to_design(plan, name="EMBBOT SEWOUT CARD 2026-07-31")

    (OUT / "EMBBOT_SEWOUT_CARD.design.json").write_text(
        json.dumps(design), encoding="utf-8")
    (OUT / "EMBBOT_SEWOUT_CARD.colors.json").write_text(
        json.dumps([list(b.rgb) for b in plan.blocks]), encoding="utf-8")

    w, h = design_size_mm(design)
    report["totals"] = {
        "stitch_count": stats.stitch_count,
        "color_blocks": len(plan.blocks),
        "color_changes": stats.color_changes,
        "trims": stats.trims,
        "size_mm_plan": [round(v, 2) for v in stats.size_mm],
        "size_mm_design": [round(w, 2), round(h, 2)],
        "design_records": len(design["stitches"]),
    }
    (OUT / "EMBBOT_SEWOUT_CARD.report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["totals"], indent=2))
    print("design ->", OUT / "EMBBOT_SEWOUT_CARD.design.json")
    print("next   -> node tools/sewout_bridge.mjs   (from the repo root)")


def check_dst(path: str) -> None:
    """pystitch sanity read of the finished DST.

    EXPECTED to disagree with the browser decode: pystitch reads the
    standard axis convention, our encoder writes the transposed one, so width
    and height come back SWAPPED — and the 0x43 color-change byte reads as a
    sequin toggle, so pystitch sees 0 color changes. That is the known
    codec dispute (docs/dst-axis-verdict-2026-07-31.md), reported here rather
    than "fixed".
    """
    import pystitch
    pat = pystitch.read_dst(path)
    xs = [s[0] for s in pat.stitches]
    ys = [s[1] for s in pat.stitches]
    colors = sum(1 for s in pat.stitches
                 if s[2] == pystitch.COLOR_CHANGE)
    print(json.dumps({
        "pystitch_size_mm": [round((max(xs) - min(xs)) / 10.0, 1),
                             round((max(ys) - min(ys)) / 10.0, 1)],
        "pystitch_color_changes": colors,
        "records": len(pat.stitches),
        "note": "expect W/H swapped vs browser decode + 0 color changes (0x43)",
    }, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--check-dst":
        check_dst(sys.argv[2])
    else:
        main()
