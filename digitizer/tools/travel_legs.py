#!/usr/bin/env python
"""Where does each exposed travel leg come from, and what is it lying on?

`tools/travel_cover.py` totals the travel that no LATER thread covers. A total
cannot say who emitted a leg or what is under it, and those two facts decide
whether it is DOCTRINE gate 3's defect (needle-down thread on bare fabric) or
something else. This walks the same plan under the same config and answers
both, one row per TRAVEL run:

  emitter  the `digitizer_core` function that constructed the run. Read off
           the call stack by wrapping `StitchRun.__init__` for this process
           only -- a TRAVEL run carries no tier, and `shape_id` cannot tell a
           fill bridge from a satin walk. Nothing in the engine is changed.
  prev/next the runs either side, in sew order.
  grid     `travel_cover`'s own reading: later thread under 0.2 units in a
           1 mm cell.
  exact    no LATER sewn segment within half a thread width of the sample --
           the thread itself, no cell and no floor. Where grid < exact the
           1 mm cell is crediting a leg with the NEXT column's thread.
  under    what each exact-exposed sample lies on: `own-fill` the leg's OWN
           shape's finished fill, `top` any other finished top stitching of
           the same colour, `other` another colour's, `underlay` underlay
           only, `own-bare` its own shape with no thread at all, `art-bare`
           another shape's artwork with none, `FABRIC` no artwork.

    .venv/bin/python tools/travel_legs.py [case ...] [--width MM] [--order nearest|euler]
                                          [--set KEY=VALUE ...] [--rows]

Cases and config are `travel_cover.py`'s (the nine `REAL_ART` logos, 80 mm,
the case's garment, max_colors 6), except that the stroke order is the
SHIPPED default unless `--order` names one. `--set` puts any
`PipelineConfig` field on the config, which is how a default-OFF flag is
read with this instrument: `--set fill_bridge_cut=true`. `--rows` prints
every leg; the default is the per-emitter summary and each case's exposed
legs.

## What it found (2026-09-19, nine logos, 80 mm, `--order nearest`)

244.6 mm grid-exposed, `travel_cover`'s own figure: **239.0 mm (97.7%) is
`stage6_fill.stitch_shape`'s `emit`** -- the fill tier's bridge between two
columns of ONE shape -- and 5.6 mm is `stage6_satin.satin_shape`'s
between-stroke walk. Nothing from stage 7 (`chain_links` is OFF) or the
junction-cover walk (`satin_patch_junctions` is OFF). **Every exposed fill
sample is `own-fill`, 374.9 of 374.9 mm: the leg's own shape's finished fill,
in the same thread. None on bare fabric, none on unsewn artwork.** (The satin
walk's 6.1 mm: 3.9 on same-colour top stitching, 0.8 on another colour, 1.4
`own-bare` at column seams.) It is MASTER_SCOPE defect 21's residual --
`tools/fill_bridges.py` read the same bridges on 2026-09-11 -- not gate 3's
letter. And the grid UNDER-reads it: 374.9 mm by the exact test against 239.0.
`docs/scope-history.md`, 2026-09-19, "the exposed travel legs". (That entry
quotes 239.1 / 375.0 / 5.7 from a scratch run that summed per-leg roundings;
these are this tool's own sums.)
"""
from __future__ import annotations

import math
import sys
import traceback
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from shapely import STRtree  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from digitizer_core import PipelineConfig, machine, stitches  # noqa: E402

_init = stitches.StitchRun.__init__


def _recording_init(self, *a, **k):
    _init(self, *a, **k)
    if self.kind == stitches.TRAVEL:
        self._emitter = [(Path(f.filename).name, f.name, f.lineno)
                         for f in traceback.extract_stack()[:-1]
                         if "digitizer_core" in f.filename]


# Before the pipeline is imported, so every construction site is recorded.
stitches.StitchRun.__init__ = _recording_init

from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402

import travel_cover as tc  # noqa: E402

UNDER = ("own-fill", "top", "other", "underlay", "own-bare", "art-bare", "FABRIC")


def _value(text: str):
    """`--set`'s right-hand side: true/false/none, a number, else the string."""
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    if low == "none":
        return None
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def legs(result, plan) -> list[dict]:
    """One dict per TRAVEL run of two or more points, in sew order."""
    flat = [(bi, run) for bi, b in enumerate(plan.blocks) for run in b.runs]
    runs = [run for _bi, run in flat]
    frame = tc._grid_frame(runs)
    if frame is None:
        return []
    x0, y0, nx, ny, cell = frame
    half = machine.COVERAGE_THREAD_W_MM / 2.0
    lines = []
    for run in runs:
        pts = stitches.strip_ties(run.points)
        lines.append(LineString(pts) if len(pts) >= 2 else None)
    regions = {r.shape_id: r.polygon.buffer(half) for r in result.regions}
    art = unary_union([r.polygon for r in result.regions
                       if r.meta.get("stitched", True)]).buffer(half)

    # `travel_cover.travel_exposure`'s map, snapshotted at each travel run.
    after_at: dict[int, np.ndarray] = {}
    after = np.zeros((ny, nx), np.float64)
    for i in range(len(runs) - 1, -1, -1):
        if runs[i].kind == stitches.TRAVEL:
            after_at[i] = after.copy()
        tc._add_ribbon(after, frame, stitches.strip_ties(runs[i].points))

    out: list[dict] = []
    for i, (bi, run) in enumerate(flat):
        pts = stitches.strip_ties(run.points)
        if run.kind != stitches.TRAVEL or len(pts) < 2:
            continue
        later = [ln for ln in lines[i + 1:] if ln is not None]
        earlier = [(j, ln) for j, ln in enumerate(lines[:i]) if ln is not None]
        ltree = STRtree(later) if later else None
        etree = STRtree([ln for _j, ln in earlier]) if earlier else None
        own = regions.get(run.shape_id)
        row = dict(idx=i, block=bi, shape=run.shape_id, n=len(pts), len_mm=0.0,
                   chord_mm=math.dist(pts[0], pts[-1]), grid_mm=0.0, exact_mm=0.0,
                   under=dict.fromkeys(UNDER, 0.0),
                   emitter=(getattr(run, "_emitter", None) or [("?", "?", 0)])[-1],
                   prev=runs[i - 1] if i else None,
                   next=runs[i + 1] if i + 1 < len(runs) else None)
        for x, y, L in tc._samples(pts):
            row["len_mm"] += L
            cx = min(nx - 1, max(0, int((x - x0) / cell)))
            cy = min(ny - 1, max(0, int((y - y0) / cell)))
            if after_at[i][cy, cx] < tc.MIN_UNITS:
                row["grid_mm"] += L
            pt = Point(x, y)
            if ltree is not None and later[ltree.nearest(pt)].distance(pt) <= half:
                continue
            row["exact_mm"] += L
            hits = etree.query(pt.buffer(half), predicate="intersects") if etree is not None else []
            under = [runs[earlier[h][0]] for h in hits]
            kinds = {(flat[earlier[h][0]][0] == bi, runs[earlier[h][0]].kind) for h in hits}
            top = {k for k in kinds if k[1] not in (stitches.UNDERLAY, stitches.TRAVEL)}
            if any(u.kind == stitches.FILL and u.shape_id == run.shape_id for u in under):
                where = "own-fill"
            elif any(same for same, _kind in top):
                where = "top"
            elif top:
                where = "other"
            elif any(kind == stitches.UNDERLAY for _same, kind in kinds):
                where = "underlay"
            elif own is not None and own.covers(pt):
                where = "own-bare"
            elif art.covers(pt):
                where = "art-bare"
            else:
                where = "FABRIC"
            row["under"][where] += L
        out.append(row)
    return out


def _run(r) -> str:
    if r is None:
        return "-"
    flag = " trim" if r.trim else (" jump" if r.jump else "")
    return f"{r.kind}[{len(r.points)}]{flag}"


def _under(d: dict) -> str:
    return " ".join(f"{k}={d[k]:.1f}" for k in UNDER if d[k] > 0.05) or "-"


def main(argv: list[str]) -> None:
    from thin_strokes import corpus_cases  # noqa: E402  (tools/ on sys.path)
    width, show_rows = 80.0, "--rows" in argv
    extra: dict = {}
    names: list[str] = []
    it = iter(a for a in argv if a != "--rows")
    for a in it:
        if a == "--width":
            width = float(next(it))
        elif a == "--order":
            extra["satin_stroke_order"] = next(it)
        elif a == "--set":
            key, _eq, val = next(it).partition("=")
            extra[key] = _value(val)
        else:
            names.append(a)
    grand: dict = defaultdict(lambda: defaultdict(float))
    totals = dict(stitches=0, trims=0)
    for name, path, _cw, garment in corpus_cases():
        if names and name not in names:
            continue
        cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                             max_colors=6, **extra)
        order = cfg.satin_stroke_order
        result = finish_generation(build_generation(str(path), cfg).fork(), cfg)
        plan = plan_stitches(result, cfg)
        rows = legs(result, plan)
        totals["stitches"] += plan.stats.stitch_count
        totals["trims"] += plan.stats.trims
        per: dict = defaultdict(lambda: defaultdict(float))
        for r in rows:
            key = f"{r['emitter'][0]}:{r['emitter'][1]}"
            for d in (per[key], grand[key]):
                d["legs"] += 1
                d["travel"] += r["len_mm"]
                d["grid"] += r["grid_mm"]
                d["exact"] += r["exact_mm"]
                for k in UNDER:
                    d[k] += r["under"][k]
        print(f"## {name} @ {width:g} mm ({order}"
              + "".join(f", {k}={v}" for k, v in extra.items() if k != "satin_stroke_order")
              + f"): st={plan.stats.stitch_count} trims={plan.stats.trims}, {len(rows)} legs, "
              f"grid-exposed {sum(r['grid_mm'] for r in rows):.1f} mm, "
              f"exact {sum(r['exact_mm'] for r in rows):.1f} mm", flush=True)
        for key, d in sorted(per.items()):
            print(f"   {key:32s} legs={int(d['legs']):3d} travel={d['travel']:7.1f} "
                  f"grid={d['grid']:6.1f} exact={d['exact']:6.1f} | {_under(d)}")
        for r in rows:
            if show_rows or r["grid_mm"] > 0.05 or r["exact_mm"] > 0.05:
                e = r["emitter"]
                print(f"     run#{r['idx']:<4d} {r['shape']:>12s} {e[0]}:{e[1]}:{e[2]} "
                      f"{_run(r['prev'])} -> travel[{r['n']}] {r['len_mm']:.1f} mm "
                      f"(chord {r['chord_mm']:.1f}) -> {_run(r['next'])} | "
                      f"grid={r['grid_mm']:.1f} exact={r['exact_mm']:.1f} | {_under(r['under'])}")
    print(f"\n=== all cases: st={totals['stitches']} trims={totals['trims']}, "
          f"grid-exposed {sum(d['grid'] for d in grand.values()):.1f} mm, "
          f"exact {sum(d['exact'] for d in grand.values()):.1f} mm")
    for key, d in sorted(grand.items()):
        print(f"   {key:32s} legs={int(d['legs']):3d} travel={d['travel']:7.1f} "
              f"grid={d['grid']:6.1f} exact={d['exact']:6.1f} | {_under(d)}")


if __name__ == "__main__":
    main(sys.argv[1:])
