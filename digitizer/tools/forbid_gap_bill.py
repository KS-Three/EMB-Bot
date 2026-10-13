#!/usr/bin/env python
"""WoK 44 bill: `cfg.forbid_gap_mm` OFF vs ON, over the scorecard corpus (2026-10-12).

Measure and render only: nothing here flips a default or touches the engine.
The value under test (0.8 mm by default) is ROADMAP gate 1's candidate, not a
measured constant.

Per fixture, one generation (stages 0-4 never read the flag), then stages
5-7 twice — OFF (`forbid_gap_mm=None`) and ON (`--gap`, default 0.8) — each
followed by `run_preflight`. `digitize` is exactly that (its tonal-split
re-plan is off by default), and the test pins the OFF row to it. One row per arm:

  * cost  — stitches, trims, colour changes, wall-clock seconds;
  * welds — read by spying `stage5_overlap.gap_bridges` / `_weld_part` for
    the duration of the run (nothing is changed): `strips` is the bridged
    pairs, `attempted` the shapes handed a strip to plan across, `failed` the
    ones whose strip-plus-artwork union stayed in pieces (`_weld_part` ran),
    `succeeded` the rest; `strip_mm2` is the fabric the settled strips hand
    to the colour sewn first. OFF must read 0 / 0 / 0 — that is the proof
    the OFF path never reaches the rule;
  * cloth — `open` mm² of bare fabric narrower than the gap between two
    stitched colours that no one colour covers, on the cloth
    (`seam_underlap.narrow_gaps`), OFF vs ON;
  * findings — `ARTWORK_UNCOVERED` (count and mm², preflight) and
    `CLIP_DROPPED_SLIVER` (count and mm², from the plan's own warnings).

    .venv/Scripts/python -m tools.forbid_gap_bill                # whole scorecard corpus
    .venv/Scripts/python -m tools.forbid_gap_bill photo/logo_bridge_bar.jpg
    .venv/Scripts/python -m tools.forbid_gap_bill --garment hat_front --md out.md
    .venv/Scripts/python -m tools.forbid_gap_bill --render bridge --out ../docs/renders/wok44-bridge-forbid-gap

`--render` draws the fixture OFF and ON as thread (`stitchviz`), a full view
with the differing regions boxed, and the largest differing crops, side by
side. A picture of where the thread lands, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core import stage5_overlap  # noqa: E402
from digitizer_core.pipeline import (apply_detection, build_generation,  # noqa: E402
                                     fabric_for, finish_generation, plan_stitches)
from digitizer_core.preflight import run_preflight  # noqa: E402
from digitizer_core.warnings_codes import CLIP_DROPPED_SLIVER  # noqa: E402
from tools.corpus_scorecard import FIXTURES, TESTDATA  # noqa: E402
from tools.seam_underlap import GAP_MM, cloth_take_back, narrow_gaps  # noqa: E402

GARMENTS = ("left_chest", "hat_front")
WIDTH_MM = 80.0


class _WeldSpy:
    """Counts what the forbid-gap rule does inside stage 5, changing nothing."""

    def __init__(self):
        self.calls = 0
        self.strips = 0
        self.attempted = 0
        self.strip_mm2 = 0.0
        self.failed = 0

    def __enter__(self):
        self._gap, self._weld = stage5_overlap.gap_bridges, stage5_overlap._weld_part
        spy = self

        def gap_bridges(regions, gap_mm):
            out, pairs = spy._gap(regions, gap_mm)
            # Last call wins: stage 5 may run again (e.g. a whole-design
            # re-plan); the bill reads the plan that was kept, not a sum.
            spy.calls += 1
            spy.strips = len(pairs)
            spy.attempted = len(out)
            spy.strip_mm2 = float(sum(g.area for g in out.values()))
            spy.failed = 0
            return out, pairs

        def weld_part(joined, art):
            spy.failed += 1
            return spy._weld(joined, art)

        stage5_overlap.gap_bridges, stage5_overlap._weld_part = gap_bridges, weld_part
        return self

    def __exit__(self, *exc):
        stage5_overlap.gap_bridges, stage5_overlap._weld_part = self._gap, self._weld

    def row(self) -> dict:
        return {"calls": self.calls, "strips": self.strips, "attempted": self.attempted,
                "failed": self.failed, "succeeded": self.attempted - self.failed,
                "strip_mm2": round(self.strip_mm2, 3)}


def _finding(report: dict, code: str) -> tuple[int, float]:
    """(count, mm2 of artwork with no thread): the sum of the named shapes'
    `missing_mm2`, which is what PR #857's census called the finding's mm2."""
    for f in report["findings"]:
        if f["code"] == code:
            shapes = f.get("shapes") or []
            mm2 = sum(s["missing_mm2"] for s in shapes) if shapes else f.get("total_mm2", 0.0)
            return int(f.get("count", len(shapes) or 1)), float(mm2)
    return 0, 0.0


def _slivers(plan, result) -> tuple[int, float]:
    for w in list(getattr(plan, "warnings", []) or []) + list(result.warnings or []):
        if w.get("code") == CLIP_DROPPED_SLIVER:
            return int(w.get("count", 0)), float(w.get("total_mm2", 0.0))
    return 0, 0.0


def _open_mm2(result, cfg, gap_mm: float) -> tuple[int, float]:
    """Bare fabric under `gap_mm` between two colours, read on the cloth."""
    cfg = apply_detection(cfg, result.detected_photographic)
    fabric = fabric_for(cfg)
    regions = [r for r in result.regions if r.meta.get("stitched", True)]
    planned, _ = stage5_overlap.resolve_overlaps(regions, fabric, cfg, result.design_class)
    gaps = narrow_gaps(regions, planned, gap_mm, take_back=cloth_take_back(planned, cfg, fabric))
    return len(gaps), float(sum(g["open_mm2"] for g in gaps))


def arm(gen, path: Path, base: dict, forbid: float | None, read_gap_mm: float) -> dict:
    """One arm off a shared generation (stages 0-4 do not read `forbid_gap_mm`)."""
    cfg = PipelineConfig(**base, forbid_gap_mm=forbid)
    t0 = time.perf_counter()
    result = finish_generation(gen.fork(), cfg)
    with _WeldSpy() as spy:
        plan = plan_stitches(result, cfg)
    secs = time.perf_counter() - t0
    report = run_preflight(result, plan, cfg, image=path)
    st = plan.stats
    unc_n, unc_mm2 = _finding(report, "ARTWORK_UNCOVERED")
    sl_n, sl_mm2 = _slivers(plan, result)
    open_n, open_mm2 = _open_mm2(result, cfg, read_gap_mm)
    return {"stitches": int(st.stitch_count), "trims": int(st.trims),
            "color_changes": int(st.color_changes), "seconds": round(secs, 1),
            **spy.row(), "open_n": open_n, "open_mm2": round(open_mm2, 2),
            "uncovered_n": unc_n, "uncovered_mm2": round(unc_mm2, 2),
            "slivers_n": sl_n, "slivers_mm2": round(sl_mm2, 3)}


def bill_row(fixture: str, garment: str = "left_chest", width_mm: float = WIDTH_MM,
             gap_mm: float = GAP_MM) -> dict:
    """OFF and ON off one generation. `seconds` is stages 5-7 only (the
    shared stages 0-4 are paid once and not billed to either arm)."""
    path = TESTDATA / fixture
    base = dict(target_width_mm=width_mm, garment_id=garment)
    gen = build_generation(str(path), PipelineConfig(**base))
    return {"fixture": fixture, "garment": garment,
            "off": arm(gen, path, base, None, gap_mm),
            "on": arm(gen, path, base, gap_mm, gap_mm)}


HEAD = ("| fixture | garment | stitches | trims | colour chg | strips | welds ok / failed "
        "| strip mm² | open mm² | UNCOVERED n (mm²) | SLIVER n (mm²) | s |")
RULE = "|---|---|---|---|---|---|---|---|---|---|---|---|"


def _cell(a, b, f="{}"):
    fa, fb = f.format(a), f.format(b)
    return fa if fa == fb else f"{fa} → {fb}"


def md_row(r: dict) -> str:
    o, n = r["off"], r["on"]
    return ("| {fx} | {g} | {st} | {tr} | {cc} | {sp} | {ok} / {fl} | {sm} | {op} | {un} | {sl} | {sec} |"
            .format(fx=r["fixture"], g=r["garment"],
                    st=_cell(o["stitches"], n["stitches"]),
                    tr=_cell(o["trims"], n["trims"]),
                    cc=_cell(o["color_changes"], n["color_changes"]),
                    sp=n["strips"], ok=n["succeeded"], fl=n["failed"],
                    sm=f"{n['strip_mm2']:.2f}",
                    op=_cell(o["open_mm2"], n["open_mm2"], "{:.2f}"),
                    un=f"{_cell(o['uncovered_n'], n['uncovered_n'])} "
                       f"({_cell(o['uncovered_mm2'], n['uncovered_mm2'], '{:.1f}')})",
                    sl=f"{_cell(o['slivers_n'], n['slivers_n'])} "
                       f"({_cell(o['slivers_mm2'], n['slivers_mm2'], '{:.2f}')})",
                    sec=f"{o['seconds']:.0f} / {n['seconds']:.0f}"))


# --- renders -------------------------------------------------------------

def render_pair(fixture: str, out: Path, garment: str, width_mm: float, gap_mm: float,
                px_per_mm: float = 10.0, crops: int = 3, crop_mm: float = 9.0,
                zoom_px_per_mm: float = 40.0) -> list[Path]:
    import cv2
    import numpy as np
    from digitizer_core import stitchviz
    from digitizer_core.adapter import plan_to_design

    path = TESTDATA / fixture
    designs = {}
    base = dict(target_width_mm=width_mm, garment_id=garment)
    gen = build_generation(str(path), PipelineConfig(**base))
    for tag, forbid in (("off", None), ("on", gap_mm)):
        cfg = PipelineConfig(**base, forbid_gap_mm=forbid)
        plan = plan_stitches(finish_generation(gen.fork(), cfg), cfg)
        designs[tag] = plan_to_design(plan, name=f"{fixture} {tag}")
    out.mkdir(parents=True, exist_ok=True)

    def draw(d, s):
        return stitchviz.render_design(d, px_per_mm=s, pad_mm=2.0)

    # Both renders share one frame: pad_mm is added to each design's own
    # bounds, so differing bounds would shift one. Draw the union by
    # padding the smaller image to the larger and checking the bounds agree.
    full = {k: draw(d, px_per_mm) for k, d in designs.items()}
    h = max(i.shape[0] for i in full.values())
    w = max(i.shape[1] for i in full.values())
    same_frame = len({i.shape for i in full.values()}) == 1
    for k, i in full.items():
        if i.shape[:2] != (h, w):
            pad = np.full((h, w, 3), stitchviz.FABRIC_BGR, np.uint8)
            pad[:i.shape[0], :i.shape[1]] = i
            full[k] = pad
    diff = (np.abs(full["off"].astype(int) - full["on"].astype(int)).sum(axis=2) > 60)
    diff = cv2.dilate(diff.astype(np.uint8), np.ones((int(crop_mm * px_per_mm / 3),) * 2, np.uint8))
    n_lab, lab, stats, cent = cv2.connectedComponentsWithStats(diff)
    order = sorted(range(1, n_lab), key=lambda k: -stats[k, cv2.CC_STAT_AREA])[:crops]
    boxes = []
    half = int(crop_mm * px_per_mm / 2)
    for k in order:
        cx, cy = (int(v) for v in cent[k])
        x0, y0 = max(0, min(w - 2 * half, cx - half)), max(0, min(h - 2 * half, cy - half))
        boxes.append((x0, y0, x0 + 2 * half, y0 + 2 * half))

    written = []
    marked = {}
    for k, img in full.items():
        m = img.copy()
        for j, (x0, y0, x1, y1) in enumerate(boxes):
            cv2.rectangle(m, (x0, y0), (x1, y1), (0, 0, 255), 2)
            cv2.putText(m, str(j + 1), (x0 + 4, y0 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 0, 255), 2)
        marked[k] = m
    side = np.hstack([marked["off"], np.full((h, 6, 3), 255, np.uint8), marked["on"]])
    p = out / f"{Path(fixture).stem}_full_off_vs_on.png"
    cv2.imwrite(str(p), side, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    written.append(p)

    zoom = {k: draw(d, zoom_px_per_mm) for k, d in designs.items()}
    s = zoom_px_per_mm / px_per_mm
    zh = max(i.shape[0] for i in zoom.values())
    zw = max(i.shape[1] for i in zoom.values())
    for k, i in zoom.items():
        if i.shape[:2] != (zh, zw):
            pad = np.full((zh, zw, 3), stitchviz.FABRIC_BGR, np.uint8)
            pad[:i.shape[0], :i.shape[1]] = i
            zoom[k] = pad
    for j, (x0, y0, x1, y1) in enumerate(boxes):
        a = [int(v * s) for v in (x0, y0, x1, y1)]
        crop = [zoom[k][a[1]:a[3], a[0]:a[2]] for k in ("off", "on")]
        pair = np.hstack([crop[0], np.full((crop[0].shape[0], 6, 3), 255, np.uint8), crop[1]])
        p = out / f"{Path(fixture).stem}_crop{j + 1}_off_vs_on.png"
        cv2.imwrite(str(p), pair, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        written.append(p)
    meta = {"fixture": fixture, "garment": garment, "gap_mm": gap_mm, "same_frame": same_frame,
            "px_per_mm": px_per_mm, "zoom_px_per_mm": zoom_px_per_mm,
            "boxes_px": boxes, "files": [q.name for q in written]}
    (out / f"{Path(fixture).stem}_render.json").write_text(json.dumps(meta, indent=1))
    return written


def _one(fixture, garment, width_mm, gap_mm):
    try:
        return bill_row(fixture, garment, width_mm, gap_mm)
    except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the run
        return {"fixture": fixture, "error": f"{type(exc).__name__}: {exc}"}


def _emit(r: dict, rows: list) -> None:
    if "error" in r:
        print(f"| {r['fixture']} | ERROR {r['error']} |", flush=True)
        return
    rows.append(r)
    print(md_row(r), flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*", help="paths under testdata/ (default: the scorecard corpus)")
    ap.add_argument("--garment", default="left_chest", choices=GARMENTS)
    ap.add_argument("--width", type=float, default=WIDTH_MM)
    ap.add_argument("--gap", type=float, default=GAP_MM)
    ap.add_argument("--jobs", type=int, default=1, help="fixtures in parallel (processes)")
    ap.add_argument("--md", help="write the markdown table here")
    ap.add_argument("--json", help="write the rows as JSON here")
    ap.add_argument("--render", help="fixture key or path: draw OFF vs ON as thread instead")
    ap.add_argument("--out", default="../docs/renders/wok44-bridge-forbid-gap")
    args = ap.parse_args(argv)

    if args.render:
        from tools.thin_strokes import REAL_ART
        fx = f"{REAL_ART[args.render][0]}" if args.render in REAL_ART else args.render
        for p in render_pair(fx, Path(args.out), args.garment, args.width, args.gap):
            print(p, p.stat().st_size // 1024, "KB")
        return 0

    names = args.fixtures or FIXTURES
    rows = []
    print(HEAD, RULE, sep="\n", flush=True)

    if args.jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(args.jobs) as ex:
            results = ex.map(_one, names, [args.garment] * len(names),
                             [args.width] * len(names), [args.gap] * len(names))
            for r in results:
                _emit(r, rows)
    else:
        for n in names:
            _emit(_one(n, args.garment, args.width, args.gap), rows)
    if args.md:
        Path(args.md).write_text("\n".join([HEAD, RULE] + [md_row(r) for r in rows]) + "\n",
                                 encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
