"""How much ARTWORK stage 5's `_largest_polygon` throws away, and whether any
of it is left bare.

`resolve_overlaps` grows each shape, subtracts what is already sewn and the
openings it holds, and keeps only the LARGEST piece of the result. Its own
comment on `visible` warns that dropping a smaller half "would silently lose a
real visible piece" -- so this reads, per design, every split `_largest_polygon`
resolves: the artwork area in the pieces it dropped, the largest single dropped
piece against the `min_detail_mm` floor, and how much of the dropped artwork no
planned polygon (any colour, grown) covers -- the part that sews as bare fabric.

    python -m tools.stage5_split_loss [--width 80] IMAGE...

Report-only; changes nothing. Measured 2026-10-08 -- see the PR that added it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shapely.ops import unary_union

from digitizer_core import pipeline
from digitizer_core import stage5_overlap as s5
from digitizer_core.config import PipelineConfig


def measure(image: str, width_mm: float) -> dict:
    dropped = []
    planned_out = []
    orig_largest, orig_resolve = s5._largest_polygon, pipeline.resolve_overlaps

    def spy(geom):
        out = orig_largest(geom)
        if out is not None and geom.geom_type != "Polygon":
            art = sys._getframe(1).f_locals.get("poly")
            for g in getattr(geom, "geoms", []):
                if g.geom_type == "Polygon" and not g.equals(out) and art is not None:
                    piece = g.intersection(art)
                    if not piece.is_empty:
                        dropped.append(piece)
        return out

    def resolve(*a, **k):
        planned, warnings = orig_resolve(*a, **k)
        planned_out.extend(planned)
        return planned, warnings

    s5._largest_polygon, pipeline.resolve_overlaps = spy, resolve
    try:
        cfg = PipelineConfig()
        cfg.target_width_mm = width_mm
        pipeline.digitize(image, cfg)
    finally:
        s5._largest_polygon, pipeline.resolve_overlaps = orig_largest, orig_resolve
    floor = cfg.min_detail_mm ** 2
    sewn = unary_union([p.polygon for p in planned_out]) if planned_out else None
    lost = unary_union(dropped) if dropped else None
    bare = lost.difference(sewn) if (lost is not None and sewn is not None) else lost
    return {
        "image": Path(image).name,
        "pieces": len(dropped),
        "dropped_art_mm2": round(sum(p.area for p in dropped), 2),
        "largest_piece_mm2": round(max((p.area for p in dropped), default=0.0), 2),
        "pieces_over_floor": sum(1 for p in dropped if p.area >= floor),
        "bare_mm2": round(bare.area, 2) if bare is not None else 0.0,
        "floor_mm2": round(floor, 2),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("images", nargs="+")
    ap.add_argument("--width", type=float, default=80.0, help="design width, mm")
    args = ap.parse_args(argv)
    for img in args.images:
        print(measure(img, args.width), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
