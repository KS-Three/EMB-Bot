#!/usr/bin/env python
"""Does the fill column-order SCORER agree with what `emit` actually SEWS?

`stage6_fill._order_cost` prices a column order -- (cuts, travel stitches,
exposed travel stitches) -- and `_reorder_for_cover` keeps whichever order it
prices cheaper. `stitch_shape`'s `emit` then sews the winner. DOCTRINE
(2026-09-11, the fill-bridges entry) records that the two "can disagree about
what an order will sew" and says to make them agree before trusting any
order-level guard. This measures the disagreement instead of arguing it.

For every fill shape `stitch_shape` sews with `under_cover` on, it records
the final column order, prices it with `_order_cost` exactly as
`_reorder_for_cover` does, and reads the SAME three figures back off the runs
`emit` returned:

  cuts     fill-phase jump runs flagged `trim`
  travel   fill-phase TRAVEL points (`emit` appends `bridge[:-1]`)
  exposed  each TRAVEL run, with the needle's position before it and the next
           run's first point, measured against the footprint of the FILL runs
           sewn before it -- `_exposed_mm` minus the tolerance, as the scorer
           does -- in travel stitches

A shape AGREES when all three match to 1e-6. Nothing in the engine is
changed; the wrappers live in this process only.

    .venv/bin/python tools/fill_score_agreement.py [case ...] [--width MM]
                                                   [--set KEY=VALUE ...]
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, machine, stitches  # noqa: E402
from digitizer_core import stage6_fill as sf  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402

_records: list[dict] = []
_last_order: list = [None]

_orig_memoized = sf._memoized
_orig_stitch_shape = sf.stitch_shape


def _spy_memoized(key, compute):
    out = _orig_memoized(key, compute)
    _last_order[0] = [list(p) for p in out]
    return out


def _sewn_figures(runs, row_mm: float, trim_at_mm: float, emit_footprint=None):
    """(cuts, travel, exposed stitches) of the fill phase, read off the runs."""
    first = next((i for i, r in enumerate(runs) if r.kind == stitches.FILL), None)
    if first is None:
        return 0, 0.0, 0.0
    # The fill phase opens with the bridge from the underlay's last point.
    start = first
    while start > 0 and runs[start - 1].kind == stitches.TRAVEL:
        start -= 1
    fp = emit_footprint or (lambda pts: sf._footprint(pts, row_mm))
    cuts, travel, exposed_mm = 0, 0, 0.0
    sewn = None
    for i in range(start, len(runs)):
        r = runs[i]
        if r.kind == stitches.TRAVEL:
            travel += len(r.points)
            if sewn is not None and i + 1 < len(runs) and i > 0:
                route = [runs[i - 1].points[-1]] + list(r.points) + [runs[i + 1].points[0]]
                exposed_mm += max(0.0, sf._exposed_mm(route, sewn) - sf._EXPOSED_TOLERANCE_MM)
            continue
        if r.jump and r.trim and i > 0:
            cuts += 1
        if r.kind == stitches.FILL and len(r.points) > 1:
            f = fp(r.points)
            sewn = f if sewn is None else sewn.union(f)
    return cuts, float(travel), exposed_mm / machine.TRAVEL_STITCH_MM


def _spy_stitch_shape(poly, shape_id, **kw):
    _last_order[0] = None
    runs, report = _orig_stitch_shape(poly, shape_id, **kw)
    if not kw.get("under_cover") or _last_order[0] is None:
        return runs, report
    technique = kw.get("technique", "tatami")
    if technique != "tatami" or kw.get("density_boost"):
        return runs, report            # two-pass fills: out of this probe's scope
    row_mm, trim_at = kw["row_mm"], kw["trim_at_mm"]
    ring = sf._inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)
    first = next((i for i, r in enumerate(runs) if r.kind == stitches.FILL), None)
    if first is None:
        return runs, report
    j = first
    while j > 0 and runs[j - 1].kind == stitches.TRAVEL:
        j -= 1
    entry = runs[j - 1].points[-1] if j > 0 else kw.get("start_near")
    cut_bridges = bool(kw.get("cut_bridges"))
    scored = sf._order_cost(_last_order[0], poly, ring, slack, entry, trim_at,
                            row_mm, cut_bridges=cut_bridges)
    sewn = _sewn_figures(runs, row_mm, trim_at)
    _records.append(dict(shape=shape_id, paths=len(_last_order[0]),
                         scored=scored, sewn=sewn))
    return runs, report


def _value(text: str):
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return None if low == "none" else text


def main(argv: list[str]) -> None:
    from thin_strokes import corpus_cases  # noqa: E402
    sf._memoized = _spy_memoized
    sf.stitch_shape = _spy_stitch_shape
    import digitizer_core.stage7_sequence as s7
    import digitizer_core.stage6_blend as sb
    for mod in (s7, sb):
        if hasattr(mod, "stitch_shape"):
            mod.stitch_shape = _spy_stitch_shape
    width, extra, names = 80.0, {}, []
    it = iter(argv)
    for a in it:
        if a == "--width":
            width = float(next(it))
        elif a == "--set":
            k, _, v = next(it).partition("=")
            extra[k] = _value(v)
        else:
            names.append(a)
    grand = defaultdict(float)
    for name, path, _cw, garment in corpus_cases():
        if names and name not in names:
            continue
        sf.clear_fill_reorder_memo()
        _records.clear()
        cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                             max_colors=6, **extra)
        result = finish_generation(build_generation(str(path), cfg).fork(), cfg)
        plan = plan_stitches(result, cfg)
        bad = [r for r in _records
               if any(abs(a - b) > 1e-6 for a, b in zip(r["scored"], r["sewn"]))]
        d_exp = sum(r["sewn"][2] - r["scored"][2] for r in _records) * machine.TRAVEL_STITCH_MM
        sewn_exp = sum(r["sewn"][2] for r in _records) * machine.TRAVEL_STITCH_MM
        print(f"## {name}: st={plan.stats.stitch_count} trims={plan.stats.trims} "
              f"fill shapes={len(_records)} disagree={len(bad)} "
              f"sewn exposed={sewn_exp:.1f} mm (sewn - scored {d_exp:+.1f} mm)", flush=True)
        for r in bad:
            s, w = r["scored"], r["sewn"]
            print(f"   {r['shape']:>14s} paths={r['paths']:3d} scored=({s[0]}, {s[1]:.0f}, "
                  f"{s[2]:.2f}) sewn=({w[0]}, {w[1]:.0f}, {w[2]:.2f})")
        grand["shapes"] += len(_records)
        grand["bad"] += len(bad)
        grand["sewn_exp"] += sewn_exp
        grand["d_exp"] += d_exp
    print(f"\n=== all: fill shapes={grand['shapes']:.0f} disagree={grand['bad']:.0f} "
          f"sewn exposed={grand['sewn_exp']:.1f} mm (sewn - scored {grand['d_exp']:+.1f} mm)")


if __name__ == "__main__":
    main(sys.argv[1:])
