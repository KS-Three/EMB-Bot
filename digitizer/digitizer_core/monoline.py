"""A monoline script stroke sews satin, never fill (`cfg.monoline_script_satin`,
built OFF 2026-10-24, L7).

THE PRO'S RULE. A script word written with one pen width -- Tires' joined
"ires", 919 mm², ribbon width 4.5 mm -- is satin columns end to end, even
where its joins and ball terminals widen past the 5 mm satin ceiling: 8.9 %
of his crosses there run over 5 mm (p90 4.93, max 6.79, `TIRES HAT 3D.DST`
read by `tools/script_census.py`). The classifier refuses that word on
`dt_p90_cap` alone (doubled-DT p90 5.37-5.43 mm against 5.0) and it sews a
45-degree tatami instead: 2,515 stitches under 1 mm where he has 43, and no
cross square to the stroke where 85 % of his are.

WHAT A MONOLINE IS. A shape the satin classifier refused ONLY at its p90
width -- ribbon width under the ceiling, the radii regular, aspect passed --
whose width is near-constant (`dt_cv` <= MONOLINE_CV_MAX) along a long stroke
(`elongation` >= MONOLINE_ELONGATION_MIN). Across the 21 pro-paired jobs
(L9's cache, 2026-10-24) the shapes refused on `dt_p90_cap` that are not
already text read: Tires' "ires" dt_cv 0.149 / elongation 42.4 (pro SATIN);
Golden Tee's two 0.40-0.43 / 12-21 and MFab's two 0.39-0.41 / 4.2 (pro FILL
all four). Every text member refused there reads 0.29-0.47 -- the lettering
split already takes those. One supporting row and four contradicting rows
the threshold leaves alone; read it as that, not as a rate.

WHAT IT DOES. `stage7_sequence._satin_ceiling_for` gives such a shape the
lettering split's own answer -- no width ceiling, the per-stroke rung and
the fold guard on -- so it reaches the satin tier and sews split where a
cross runs over the ceiling, exactly as a text-cluster member does under
`satin_lettering_split`. Nothing else moves.
"""
from __future__ import annotations

from functools import lru_cache

MONOLINE_CV_MAX = 0.25
MONOLINE_ELONGATION_MIN = 20.0


@lru_cache(maxsize=4096)
def _verdict(wkb: bytes, satin_max_mm: float, area_weighted: bool) -> bool:
    from shapely import wkb as _wkb
    from .stage6_satin import classify_ribbon
    v = classify_ribbon(_wkb.loads(wkb), satin_max_mm, area_weighted=area_weighted)
    m = v.metrics
    return (v.reason == "dt_p90_cap"
            and m["dt_cv"] <= MONOLINE_CV_MAX
            and m["elongation"] >= MONOLINE_ELONGATION_MIN)


def monoline_stroke(region, cfg, satin_max_mm: float) -> bool:
    """Is `region` a monoline script stroke the width ceiling alone refuses?"""
    return _verdict(region.polygon.wkb, float(satin_max_mm),
                    bool(getattr(cfg, "classify_area_weighted", False)))
