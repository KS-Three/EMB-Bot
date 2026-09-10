"""One stitch direction for the design's shapes that have no house of their
own -- `cfg.design_angle` (quality review 2026-09-08 item 7, built
2026-09-09). Metadata only: `Region.meta["design_angle_deg"]`.

What it answers. A flat design's non-lettering fills each chose their own
row angle by their own column count (`stage6_fill.best_fill_angle_deg`),
so adjacent shapes landed on different angles -- on Becker Marine at the
pro's own 95.7 mm our nine fills spread to a resultant of 0.15 over the
half-circle while the professional's file holds ONE fill angle at every
size it was sewn at (18-21 deg on the 1,223 mm2 slab, 13-14 on the small
fills, three files at three sizes, `tools/design_direction.py --pro`).
Non-lettering satin got no cross angle at all: each stroke followed its
own spine tangent, with none of the lean rule lettering has.

What the angle is, in order:

1. **The lettering house angle**, where `textcluster.set_lettering_house_angle`
   set one (`Region.meta["satin_angle_deg"]`) and the lines that carry it
   agree within the lean cap (`SATIN_HOUSE_MIN_SPAN_DEG`'s complement, the
   30 deg the stitch-angle rule adopted): the area-weighted doubled-angle
   mean across those lines. Lines that disagree past the cap are not one
   house, and the fills fall through to rules 2 and 3. This is the review's own
   proposal ("extend the house angle to all fills as one design angle"),
   and on the Becker files it is the constant-free choice nearest the
   pro's: 2 deg against the pro's 13-21, where the per-shape column
   objective picks 90 (the slab fragments least along its own edges: 50
   columns at 90 deg, 58 at 0, 202 at the pro's 22.5).
2. **The gradient lane's own shared angle** where the design holds one
   (`Generation.design_row_angle_deg`: the design ramp's row angle, or the
   legacy whole-design fit; gradient class only). That lane's fills sew at
   it whatever the metadata says -- `stage6_blend` reads
   `SourcePixels.design_row_angle_deg`, never this key -- so the one
   direction the design already has is the one its satin leans to.
   Deriving another from rule 3 leaned `repro_gradient_white_icon`'s
   four strokes to the objective's 0 deg against ramp rows at 134 (the
   first 80 mm corpus sweep, 2026-09-09), the opposite of the point. A
   gradient design whose ramp the fit refuses has no lane angle and takes
   rule 3, as drone does.
3. **The one row direction that cuts the design's fill shapes into the
   fewest columns in total** -- `best_fill_angle_deg`'s sixteen candidates
   plus the shapes' area-weighted principal axis (the per-shape function
   carries its own PCA angle as a seventeenth candidate for the same
   reason), its objective summed over every fill-tier shape instead of
   scored per shape. Ties go to the candidate nearest that principal axis,
   then the smaller angle, as the per-shape function's do -- so on one
   polygon at one row spacing a lone fill gets exactly the per-shape
   answer, and more fills can only tie or beat the sum of their separate
   counts at that angle. Through the pipeline the pass reads the stage-4
   polygon (it must run before stage 5, whose comp axis reads the key)
   where stage 7 scores the compensated one, so a near-round fill whose
   axis is ill-defined can still land elsewhere (script tires' 15.7 mm2
   blob of aspect 1.05: 160 deg per shape, 126 by the pass -- a tie at
   every angle either way).

No new constant: the candidates, the row spacing, the tie rule and the cap
are the ones that already exist. No per-shape override on aspect either --
the review asked for one "only on strong aspect", and the pro's files
answered: the slab of aspect 2.5 and the small fills of aspect 1.5-2.0 hold
the same angle (plan doc 4). A review-screen `fill_angle_deg` and the house
angle both beat it (stage 7's precedence; stage 5's `_comp_axis` reads the
same order), and a shape whose tier is neither fill nor satin is left alone.

Who reads it: stage 7 for every fill-tier shape without a review or house
angle (before the directional-comp axis and the per-shape derivation) and
for every satin-tier shape without a house angle (before the per-stroke
tangent, so `_clamp_to_span` gives non-lettering satin the lean rule);
stage 5's `_comp_axis`, so directional comp compensates along the axis the
shape sews. Absent the key everything is byte-identical.
"""
from __future__ import annotations

import math

from shapely import affinity

from . import machine
from .config import PipelineConfig
from .regions import Region
from .stage5_overlap import _comp_axis
from .stage6_fill import _FILL_ANGLE_CANDIDATES, _columns, _row_spans, principal_angle_deg
from .stage6_satin import SATIN_HOUSE_MIN_SPAN_DEG

META_KEY = "design_angle_deg"


def _doubled_mean(angles: list[float], weights: list[float]) -> tuple[float | None, float]:
    c = s = w = 0.0
    for a, wt in zip(angles, weights):
        t = math.radians(2.0 * a)
        c += wt * math.cos(t)
        s += wt * math.sin(t)
        w += wt
    if w <= 0.0:
        return None, 0.0
    return (math.degrees(0.5 * math.atan2(s / w, c / w))) % 180.0, math.hypot(c / w, s / w)


def _angular_dist(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def house_design_angle(regions: list[Region]) -> float | None:
    """Rule 1: the lettering lines' house angle, when they agree."""
    votes = [(float(r.meta["satin_angle_deg"]), max(r.polygon.area, 1e-9))
             for r in regions if r.meta.get("satin_angle_deg") is not None]
    if not votes:
        return None
    mean, _r = _doubled_mean([a for a, _w in votes], [w for _a, w in votes])
    if mean is None:
        return None
    cap = 90.0 - SATIN_HOUSE_MIN_SPAN_DEG          # the lean cap, 30 deg
    if any(_angular_dist(a, mean) > cap for a, _w in votes):
        return None
    return mean


def fewest_columns_angle(polys: list, row_mm: float) -> float | None:
    """Rule 3: the candidate row direction with the fewest monotone columns
    summed over `polys`, at the row spacing the fill will run at."""
    if not polys:
        return None
    cands = [i * (180.0 / _FILL_ANGLE_CANDIDATES) for i in range(_FILL_ANGLE_CANDIDATES)]
    pca_mean, _r = _doubled_mean([principal_angle_deg(p) for p in polys],
                                 [max(p.area, 1e-9) for p in polys])
    if pca_mean is not None:
        cands.append(pca_mean)           # the seventeenth, as best_fill_angle_deg's
    best = None
    best_key = None
    for angle in cands:
        total = 0
        for poly in polys:
            rotated = affinity.rotate(poly, -angle, origin=(0, 0), use_radians=False)
            total += len(_columns(_row_spans(rotated, row_mm)))
        if total == 0:
            continue
        key = (total, _angular_dist(angle, pca_mean) if pca_mean is not None else 0.0, angle)
        if best_key is None or key < best_key:
            best_key = key
            best = angle
    return best


def set_design_angle(regions: list[Region], cfg: PipelineConfig, design_class: str,
                     row_mm: float, lane_angle: float | None = None) -> float | None:
    """The pass. `lane_angle` is the gradient lane's shared fill-row angle
    when the design holds one (rule 2). -> the angle it wrote, or None when
    nothing took one."""
    satin_max = machine.satin_ceiling_mm(cfg)
    takers: list[Region] = []
    fill_polys = []
    for r in regions:
        if not r.meta.get("stitched", True):
            continue
        if r.meta.get("satin_angle_deg") is not None:
            continue                     # a line of lettering keeps its house
        if r.meta.get("fill_angle_deg") is not None:
            continue                     # review intent, or the house on the fill tier
        tier = str(r.meta.get("tier", "auto")).lower()
        if tier not in ("auto", "satin", "fill"):
            continue                     # run, sketch, streamline...: not a row angle
        _axis, is_satin = _comp_axis(r, cfg, satin_max, design_class)
        takers.append(r)
        if not is_satin:
            fill_polys.append(r.polygon)
    if not takers:
        return None
    angle = house_design_angle(regions)
    if angle is None and lane_angle is not None:
        angle = float(lane_angle) % 180.0
    if angle is None:
        angle = fewest_columns_angle(fill_polys, row_mm)
    if angle is None:
        return None
    for r in takers:
        r.meta.setdefault(META_KEY, float(angle))
    return float(angle)
