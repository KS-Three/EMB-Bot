"""Per-region fill-angle audit -- where adjacent same-colour fills disagree,
and where a long thin fill sews across its own length.

Reads `design_direction.scan`'s per-shape rows (the row direction each fill
actually SEWED, its area and aspect) and adds two findings per design:

* `flips`: pairs of fill shapes on the SAME thread whose stage-4 polygons
  touch (within `--touch-mm`) and whose sewn row angles differ by more than
  `--flip-deg` -- the seam a viewer reads as two pieces of one patch.
* `across`: fills of aspect >= `--aspect` whose sewn rows sit more than
  45 deg off the shape's own long axis -- short rows across a bar, the
  opposite of what `principal_angle_deg` argues for.

Measurement only: it changes nothing and gates nothing. `--flag` passes
config flags through exactly as `design_direction.py` does, so the same
design can be read OFF and ON (`--flag design_angle`).

Usage:
  python tools/fill_angle_audit.py [--widths W ...] [--flag NAME[=VALUE] ...]
                                   [--json PATH] [cases ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "pro_parity"))

import design_direction as dd                                               # noqa: E402
from curve_tiers import CASES                                               # noqa: E402
from digitizer_core.designangle import _angular_dist                        # noqa: E402
from digitizer_core.stage6_fill import principal_angle_deg                  # noqa: E402
from thin_strokes import parse_flags                                        # noqa: E402


def findings(shapes: list[dict], touch_mm: float, flip_deg: float, aspect: float) -> dict:
    """`shapes`: dicts with shape, thread, poly, sewn_deg, area_mm2, aspect."""
    live = [s for s in shapes if s["sewn_deg"] is not None]
    flips = []
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if a["thread"] != b["thread"]:
                continue
            if a["poly"].distance(b["poly"]) > touch_mm:
                continue
            d = _angular_dist(a["sewn_deg"], b["sewn_deg"])
            if d > flip_deg:
                flips.append({"a": a["shape"], "b": b["shape"], "thread": a["thread"],
                              "a_deg": a["sewn_deg"], "b_deg": b["sewn_deg"], "diff_deg": round(d, 1)})
    across = []
    for s in live:
        if s["aspect"] < aspect:
            continue
        axis = principal_angle_deg(s["poly"])
        off = _angular_dist(s["sewn_deg"], axis)
        if off > 45.0:
            across.append({"shape": s["shape"], "aspect": s["aspect"], "area_mm2": s["area_mm2"],
                           "sewn_deg": s["sewn_deg"], "axis_deg": round(axis, 1), "off_deg": round(off, 1)})
    return {"fills": len(live), "flips": flips, "across": across}


def audit(case: str, rel: str, kw: dict, width: float | None, flags: dict,
          touch_mm: float, flip_deg: float, aspect: float) -> dict:
    regions_by_id: dict = {}
    real = dd.digitize

    def spy(path, pc):
        result, plan = real(path, pc)
        regions_by_id.update({r.shape_id: r for r in result.regions})
        return result, plan

    dd.digitize = spy
    try:
        out = dd.scan(case, rel, kw, width, flags)
    finally:
        dd.digitize = real
    shapes = []
    for row in out["shapes"]:
        r = regions_by_id.get(row["shape"])
        if r is None:
            continue
        shapes.append({**row, "thread": r.thread_number, "poly": r.polygon})
    return {"case": case, "width_mm": out["width_mm"], "flags": flags,
            **findings(shapes, touch_mm, flip_deg, aspect)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--widths", type=float, nargs="*", default=[None])
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--touch-mm", type=float, default=0.5)
    ap.add_argument("--flip-deg", type=float, default=30.0)
    ap.add_argument("--aspect", type=float, default=2.5)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    flags = parse_flags(a.flag)
    cases = a.cases or sorted(CASES)
    rows = []
    for c in cases:
        if c not in CASES:
            raise SystemExit(f"unknown case {c!r}: not in curve_tiers.CASES")
        rel, kw = CASES[c]
        for w in a.widths:
            rec = audit(c, rel, kw, w, flags, a.touch_mm, a.flip_deg, a.aspect)
            rows.append(rec)
            print(f"{c:32s} w={rec['width_mm']}  fills={rec['fills']:3d}  "
                  f"flips={len(rec['flips']):2d}  across={len(rec['across']):2d}")
            for f in rec["flips"]:
                print(f"    flip  {f['a']} {f['a_deg']} / {f['b']} {f['b_deg']}  "
                      f"(thread {f['thread']}, {f['diff_deg']} deg)")
            for s in rec["across"]:
                print(f"    across {s['shape']} aspect {s['aspect']} rows {s['sewn_deg']} "
                      f"axis {s['axis_deg']} (off {s['off_deg']})")
    if a.json:
        a.json.write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
