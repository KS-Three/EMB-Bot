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
    .venv/Scripts/python -m tools.forbid_gap_bill --render bridge --out ../docs/renders/claude-wok44-bridge-forbid-gap

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
        self.pairs: list[dict] = []
        self.geoms: dict = {}          # shape_id -> the strip polygon it was handed

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
            spy.pairs = [dict(p) for p in pairs]
            spy.geoms = out
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
            x = f.get("extra", f)            # `preflight.finding` nests the extras
            shapes = x.get("shapes") or []
            mm2 = sum(s["missing_mm2"] for s in shapes) if shapes else x.get("total_mm2", 0.0)
            return int(x.get("count", len(shapes))), float(mm2)
    return 0, 0.0


def _slivers(plan, result) -> tuple[int, float]:
    """Every CLIP_DROPPED_SLIVER the plan carries (stage 5's clip and stage
    7's own count are separate warnings), summed."""
    ws = [w for w in (getattr(plan, "warnings", None) or []) if w.get("code") == CLIP_DROPPED_SLIVER]
    return (sum(int(w.get("count", 0)) for w in ws),
            sum(float(w.get("total_mm2", 0.0)) for w in ws))


def _open_mm2(result, cfg, gap_mm: float) -> tuple[int, float, dict]:
    """Bare fabric under `gap_mm` between two colours, read on the cloth."""
    cfg = apply_detection(cfg, result.detected_photographic)
    fabric = fabric_for(cfg)
    regions = [r for r in result.regions if r.meta.get("stitched", True)]
    planned, _ = stage5_overlap.resolve_overlaps(regions, fabric, cfg, result.design_class)
    gaps = narrow_gaps(regions, planned, gap_mm, take_back=cloth_take_back(planned, cfg, fabric))
    return (len(gaps), float(sum(g["open_mm2"] for g in gaps)),
            {p.shape_id: bool(p.satin_tier) for p in planned})


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
    open_n, open_mm2, satin = _open_mm2(result, cfg, read_gap_mm)
    pairs = [{**p, "earlier_satin": satin.get(p["earlier"]),
              "later_satin": satin.get(p["later"])} for p in spy.pairs]
    return {"pairs": pairs,"stitches": int(st.stitch_count), "trims": int(st.trims),
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


HEAD = ("| fixture | garment | stitches | trims | colour chg | pairs bridged | shapes welded ok / failed "
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
                px_per_mm: float = 7.0, crops: int = 4, crop_mm: float = 5.0,
                zoom_px_per_mm: float = 64.0) -> list[Path]:
    """Full view (both arms, one frame, one scale) plus `crops` zoom panels,
    each centred on one of the largest strips the rule built. Panel order:
    OFF, ON, OFF with the strip filled red — the gap the rule spans, which is
    under 1 mm wide and so only readable zoomed."""
    import cv2
    import numpy as np
    from digitizer_core import stitchviz
    from digitizer_core.adapter import plan_to_design

    path = TESTDATA / fixture
    designs: dict = {}
    base = dict(target_width_mm=width_mm, garment_id=garment)
    gen = build_generation(str(path), PipelineConfig(**base))
    strips: list[tuple[float, object, str]] = []        # (area, polygon, shape_id)
    for tag, forbid in (("off", None), ("on", gap_mm)):
        cfg = PipelineConfig(**base, forbid_gap_mm=forbid)
        result = finish_generation(gen.fork(), cfg)
        with _WeldSpy() as spy:
            plan = plan_stitches(result, cfg)
        designs[tag] = plan_to_design(plan, name=f"{fixture} {tag}")
        if forbid:
            for sid, g in spy.geoms.items():
                for part in getattr(g, "geoms", [g]):
                    strips.append((float(part.area), part, sid))
    out.mkdir(parents=True, exist_ok=True)

    # One frame for both: `render_design` frames each design on its own
    # stitch bounds, and ON's differ from OFF's by a stitch or two, which
    # would shift one picture against the other. Two leading jumps at the
    # union's corners (a jump draws nothing, it only counts in the bounds)
    # make the frames identical.
    ba = stitchviz._bounds(designs["off"]["stitches"])
    bb = stitchviz._bounds(designs["on"]["stitches"])
    ux0, ux1 = min(ba[0], bb[0]), max(ba[1], bb[1])
    uy0, uy1 = min(ba[2], bb[2]), max(ba[3], bb[3])
    for d in designs.values():
        d["stitches"] = ([{"x": ux0, "y": uy0, "type": "jump"},
                          {"x": ux1, "y": uy1, "type": "jump"}] + list(d["stitches"]))
    pad_mm = 2.0

    def to_px(x_mm: float, y_mm: float, s: float) -> tuple[float, float]:
        # `adapter` writes x = 10 x_mm, y = -10 y_mm; `stitchviz._frame` maps
        # that to pixels on the union box.
        return (x_mm - ux0 / 10.0 + pad_mm) * s, (uy1 / 10.0 + y_mm + pad_mm) * s

    full = {k: stitchviz.render_design(d, px_per_mm=px_per_mm, pad_mm=pad_mm)
            for k, d in designs.items()}
    assert full["off"].shape == full["on"].shape
    h, w = full["off"].shape[:2]

    # Crop centres: the largest strips, greedily, none within one crop of
    # another.
    picked: list[tuple[float, object, str]] = []
    for a, poly, sid in sorted(strips, key=lambda t: -t[0]):
        c = poly.centroid
        if all(np.hypot(c.x - q.centroid.x, c.y - q.centroid.y) > crop_mm for _, q, _ in picked):
            picked.append((a, poly, sid))
        if len(picked) == crops:
            break
    half = crop_mm / 2.0

    written = []
    marked = {}
    for k, img in full.items():
        m = img.copy()
        for j, (_, poly, _) in enumerate(picked):
            c = poly.centroid
            x0, y0 = to_px(c.x - half, c.y - half, px_per_mm)
            x1, y1 = to_px(c.x + half, c.y + half, px_per_mm)
            cv2.rectangle(m, (int(x0), int(y0)), (int(x1), int(y1)), (0, 0, 255), 2)
            cv2.putText(m, str(j + 1), (int(x0) + 4, int(y0) + 18), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 0, 255), 2)
        marked[k] = m
    side = np.hstack([marked["off"], np.full((h, 6, 3), 255, np.uint8), marked["on"]])
    p = out / f"{Path(fixture).stem}_full_off_vs_on.png"
    cv2.imwrite(str(p), side, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    written.append(p)

    zoom = {k: stitchviz.render_design(d, px_per_mm=zoom_px_per_mm, pad_mm=pad_mm)
            for k, d in designs.items()}
    zh, zw = zoom["off"].shape[:2]
    meta_crops = []
    for j, (area, poly, sid) in enumerate(picked):
        c = poly.centroid
        x0, y0 = (int(v) for v in to_px(c.x - half, c.y - half, zoom_px_per_mm))
        x0, y0 = max(0, min(zw - int(crop_mm * zoom_px_per_mm), x0)), max(0, min(zh - int(crop_mm * zoom_px_per_mm), y0))
        n = int(crop_mm * zoom_px_per_mm)
        crop = {k: zoom[k][y0:y0 + n, x0:x0 + n] for k in ("off", "on")}
        hi = crop["off"].copy()
        over = hi.copy()
        for _, q, _ in strips:
            if q.distance(poly) > crop_mm:
                continue
            ring = [to_px(x, y, zoom_px_per_mm) for x, y in q.exterior.coords]
            pts = np.array([[int(px) - x0, int(py) - y0] for px, py in ring], np.int32)
            cv2.fillPoly(over, [pts], (0, 0, 230))
        hi = cv2.addWeighted(over, 0.55, hi, 0.45, 0)
        bar = np.full((n, 6, 3), 255, np.uint8)
        pair = np.hstack([crop["off"], bar, crop["on"], bar, hi])
        p = out / f"{Path(fixture).stem}_crop{j + 1}_off_on_strip.png"
        cv2.imwrite(str(p), pair, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        written.append(p)
        meta_crops.append({"crop": j + 1, "shape_id": sid, "strip_mm2": round(area, 3),
                           "centre_mm": [round(float(c.x), 2), round(float(c.y), 2)]})
    meta = {"fixture": fixture, "garment": garment, "gap_mm": gap_mm,
            "px_per_mm": px_per_mm, "zoom_px_per_mm": zoom_px_per_mm, "crop_mm": crop_mm,
            "crops": meta_crops, "files": [q.name for q in written]}
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
    ap.add_argument("--out", default="../docs/renders/claude-wok44-bridge-forbid-gap")
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
