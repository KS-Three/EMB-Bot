"""A shape's own inlets, kept open at stitch time (`cfg.outline_inlets_kept`, ON since 2026-11-15).

Found 2026-11-14 tracing Kent's "shape detail lost" pins
(`docs/shape-detail-traced-2026-11-14.md`). An INLET is bare fabric the
art keeps inside a shape's own outer outline but open to the outside: a
gear's tooth gaps, a bird's open beak, a notch cut into a disc. Stage 4
traces it (the polygon has it) and then the stitches sew over it:

- a SATIN column draws its rails as a smoothed offset of the spine
  (`stage6_satin._rail_points`: a median over 5 stations, then 4 averaging
  passes), so a width profile that steps in and out every millimetre comes
  out as a ripple, and its crosses run across the gaps (Ahora's gear: 16
  square teeth sewn as a scalloped ring; the crest's beak: one column over
  the open mouth);
- a FILL is grown by the pull (`stage5_overlap._grow`), outward from both
  walls of a slot, so a slot under twice the pull closes (music's notch,
  0.6 mm across).

ON, both stop:

1. stage 5 keeps a fill's growth out of its own inlets (`kept_inlets`), as
   `growth_keeps_gaps` does for the gaps between shapes and for counters;
2. a satin shape whose crosses cover at least `SATIN_OVER_INLET_FRAC` of one
   of its inlets is planned again as a fill (`satin_over_inlets`), on a copy
   of the regions (the `tier="fill"` field every stage-5/7 reader honours),
   where the rows end at the inlet's walls.

A letter is never moved: its tier is the lettering lane's, and its
openings are what the per-stroke satin is built to keep.

`cfg.extra["outline_inlets_teeth"]` (built OFF, read only with the flag
above) sews a TOOTHED shape the pro's way instead of as one fill: its teeth
first, each a short fill square to its own axis, then its body over their
roots (`tooth_split`, `rebuild`, `bury_tooth_moves`; comment at "teeth").

Only WHERE thread goes changes. The pull itself (`Fabric.pull_comp_mm`) is
gate 1 and untouched; whether a kept inlet stays open on the cloth is the
sew-out's to settle.
"""
from __future__ import annotations

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polylabel, unary_union

FLAG = "outline_inlets_kept"
#: the narrowest inlet worth keeping (mm): two thread edges, each half a 40 wt
#: laid thread, meet across anything narrower anyway (the same floor as
#: `stage5_overlap.GAP_SEWABLE_MM`, restated to keep this module import-free)
INLET_MIN_MM = 0.5
#: inlets are found by closing the outline with a disc of this radius (mm):
#: an inlet narrower than twice it closes, so this is half of
#: `stage5_overlap.GAP_PROTECT_MM` (2.0 mm, the widest gap growth is kept
#: out of; past it the pull leaves the gap readable)
CLOSE_RADIUS_MM = 1.0
#: an inlet smaller than this (mm²) is a corner's fillet, not a feature
INLET_MIN_AREA_MM2 = 0.1
#: a satin covering at least this share of one inlet with its thread has
#: sewn over it: the column cannot draw that shape
SATIN_OVER_INLET_FRAC = 0.5
#: ... and only when the inlets it covers are a feature OF the shape: at
#: least this share of its area. Measured 2026-11-14: Ahora's gear 0.104
#: (all its inlets), Becker's black border 0.002 -- a band whose few dips
#: between letters the pro's own satin band sews over too, so it must not
#: move (the first build re-planned it as a fill)
SATIN_OVER_INLET_SHARE = 0.03
#: half a laid 40 wt thread (mm), the width a cross covers either side of
#: its centre line
THREAD_HALF_MM = 0.2

#: meta keys that make a region a letter (stage 2's text tags)
_LETTER_KEYS = ("text_candidate", "ocr_char", "text_cluster_id")


def enabled(cfg) -> bool:
    """`cfg.outline_inlets_kept` (ON since 2026-11-15, Kent's tick)."""
    return bool(getattr(cfg, FLAG, False))


def inscribed_width(poly: Polygon) -> float:
    """Twice the radius of the largest circle inside `poly` (mm)."""
    try:
        c = polylabel(poly, tolerance=0.01)
    except Exception:  # noqa: BLE001 -- a degenerate ring is no inlet
        return 0.0
    return 2.0 * float(poly.exterior.distance(c))


def inlets(poly) -> list[Polygon]:
    """The inlets of `poly`'s OUTER outline: what closing it with a
    `CLOSE_RADIUS_MM` disc adds, in pieces at least `INLET_MIN_MM` across
    and `INLET_MIN_AREA_MM2` in area. Holes are counters, not inlets
    (`growth_keeps_gaps` keeps those)."""
    if poly is None or poly.is_empty or poly.geom_type != "Polygon":
        return []
    shell = Polygon(poly.exterior)
    closed = shell.buffer(CLOSE_RADIUS_MM).buffer(-CLOSE_RADIUS_MM)
    bays = closed.difference(shell)
    out = []
    for g in getattr(bays, "geoms", [bays]):
        if g.is_empty or g.geom_type != "Polygon" or g.area < INLET_MIN_AREA_MM2:
            continue
        if inscribed_width(g) >= INLET_MIN_MM:
            out.append(g)
    return out


def kept_inlets(poly, grown, all_art, reach: float = 0.0):
    """`grown` less the inlets of `poly` that no artwork fills (stage 5,
    for a fill): the growth stays out of them, `poly` itself is kept whole.
    `reach` (the pull) carries the opening out through the growth band
    round the outline, or the band welds the inlet's MOUTH shut (music's
    notch, first cut: the slot stayed open inside and closed at the edge).

    Only a NOTCH (at most `NOTCH_MAX` inlets) or a regular row of teeth
    (`regular_teeth`) is kept: a feathered or lobed edge grows as before. On
    the heraldic crest at 53 mm, keeping all 22-56 inlets of its feathered
    fills cost 3.5x the plan's time (2026-11-15: each fill splits into many
    more sections, and the fill lane's travel ordering pays for every one)."""
    bays = inlets(poly)
    if not bays:
        return grown
    if len(bays) > NOTCH_MAX and not regular_teeth(poly):
        return grown
    bare = unary_union(bays).difference(all_art)
    if bare.area < INLET_MIN_AREA_MM2:
        return grown            # another colour's art fills it: a seam, not bare
    if reach > 0:
        bare = bare.buffer(reach).difference(all_art)
    return grown if bare.is_empty else grown.difference(bare).union(poly)


def is_letter(region) -> bool:
    meta = getattr(region, "meta", None) or {}
    return any(meta.get(k) for k in _LETTER_KEYS)


def satin_over_inlets(regions, plan) -> dict[str, float]:
    """{shape id: the share of its area that is inlet its satin thread
    covers} for every satin shape (not a letter, tier not hand-set) that
    covers at least `SATIN_OVER_INLET_FRAC` of one inlet and
    `SATIN_OVER_INLET_SHARE` of its area in all. The cover is the satin
    runs' needle path widened by `THREAD_HALF_MM`."""
    from .stitches import SATIN
    paths: dict[str, list] = {}
    for _blk, run in plan.iter_runs():
        if run.kind != SATIN or len(run.points or []) < 2:
            continue
        paths.setdefault(str(run.shape_id), []).append(LineString(run.points))
    out: dict[str, float] = {}
    for r in regions:
        lines = paths.get(str(r.shape_id))
        if not lines or is_letter(r) or str(r.meta.get("tier", "auto")).lower() != "auto":
            continue
        bays = inlets(r.polygon)
        if not bays:
            continue
        # only the needle path near the inlets is widened: a whole column's
        # zigzag, noded and buffered, cost minutes on Becker's border
        window = unary_union(bays).buffer(THREAD_HALF_MM)
        near = [ln.intersection(window) for ln in lines if ln.intersects(window)]
        near = [g for g in near if not g.is_empty]
        if not near:
            continue
        cover = unary_union([g.buffer(THREAD_HALF_MM) for g in near])
        shares = [cover.intersection(b).area / b.area for b in bays]
        covered = sum(s * b.area for s, b in zip(shares, bays))
        if max(shares) >= SATIN_OVER_INLET_FRAC and covered >= SATIN_OVER_INLET_SHARE * r.polygon.area:
            out[str(r.shape_id)] = round(float(covered / r.polygon.area), 3)
    return out


def as_fill(regions, ids) -> list:
    """`regions` with `ids` re-tiered to fill, on copies (the caller's
    regions are untouched and the plan stays re-runnable)."""
    from dataclasses import replace
    return [replace(r, meta={**r.meta, "tier": "fill", "inlet_satin_to_fill": True})
            if str(r.shape_id) in ids else r for r in regions]




# ---------------------------------------------------------------- teeth
# `cfg.extra["outline_inlets_teeth"]` (built OFF, with `outline_inlets_kept`):
# a TOOTHED edge sewn the pro's way. Re-planned whole as one fill (above),
# Ahora's gear -- a 1.1 mm ring with sixteen 0.85 mm teeth -- kept its teeth
# but sewed as short tatami rows with crossing travel, and read ragged
# (Director, 11-14). The pro has no gear on file; the nearest is Bridge's
# steering wheel, a ring with eight handles: ONE satin ring, and a separate
# short column per handle whose crosses run square to the handle, the ring's
# satin lying over the handles' feet. So a toothed shape splits into
# - its BODY, the shape inside the teeth's root, on its own tier (a ring
#   stays a smooth radial satin, now ending at the root), sewn LAST, and
# - one piece per TOOTH, sewn FIRST, round the shape in turn: a fill whose
#   rows run square to the tooth's own axis -- across a sub-millimetre tooth
#   a row is one stitch, the pro's cross -- reaching TOOTH_ROOT_MM under the
#   body down its own axis. Its sides are needle ends in a line, its tip one
#   flat row, and its root goes under the body.
# Measured on Ahora: the other orders read worse. Body first and teeth on
# top put the travel and the teeth's feet over the finished ring; one
# continuous satin run of teeth under the ring left 0.3 mm of each tooth
# showing past the ring's own pull. Teeth first left 26 needle-up moves
# between teeth that stage 7 cannot bury (the ring is the same colour, so
# not `covered_by`); `bury_tooth_moves` sews each as travel along the root,
# where the ring then covers it.

#: an edge is toothed when it has at least this many inlets (a notch or a
#: mouth is one or two: those re-plan as a fill, as above)
TEETH_MIN = 3
#: a tooth reaches this far under the body (mm), down its own axis, so no
#: seam opens at its root under the body sewn over it
TOOTH_ROOT_MM = 0.2
#: the inlets of one toothed edge are about one depth: the deepest may be at
#: most this many times the shallowest, or the edge is not a row of teeth
TEETH_DEPTH_SPREAD = 2.0
#: the disc (radius, mm) that closes a toothed outline from tip to tip: wide
#: against a tooth gap (a 1 mm gap sags it 0.04 mm), small against the shape
TIP_ENVELOPE_MM = 3.0
#: meta key a tooth piece carries: the shape it was cut from
TOOTH_OF_KEY = "inlet_tooth_of"
#: a fill keeps the inlets of a NOTCH, at most this many of them (dot_music's
#: slot reads one, or two at the tighter closing); more, and the edge must be
#: a regular row of teeth (`regular_teeth`), or it is feathered and grows as
#: before (2026-11-15, the crest's 3.5x)
NOTCH_MAX = 2
#: a row of TEETH is regular: the spread of the pieces' areas (standard
#: deviation over mean) at most this. Ahora's gear reads 0.07; a feathered
#: or lobed edge that splits reads far wider, and is left a satin
#: (2026-11-15, the crest's lobes; Director's pick: teeth only)
TEETH_AREA_CV_MAX = 0.35

#: a TOOTH is short against the body it stands on: how far it reaches out
#: from the body, at most this many times the body's inscribed width. A gear's
#: teeth are stubs on a ring; Bridge's eight handles (10.9 mm on a 2.65 mm
#: ring, 4.1x by their boxes) are spokes, and cut as teeth they lost their
#: taper to straight blocks (2026-11-16, the inlets flip's STOP). Ahora's
#: gear reads 0.82x by the same boxes. Set from the only two toothed shapes in
#: the 67 designs of the combined check: a shape reading, not a stitch value
#: (gate 1 does not apply).
TOOTH_LEN_OVER_BODY_MAX = 1.5


def toothed_satins(regions, cfg, design_class: str = "flat") -> set[str]:
    """Ids of the shapes `outline_inlets_kept` re-tiers before the plan: an
    auto-tier non-letter shape stage 7 would sew as a satin (the same
    `is_satin_candidate` call stage 5's `_comp_axis` makes), whose inlets are
    `SATIN_OVER_INLET_SHARE` of its area, and whose outline `tooth_split`
    reads as a REGULAR row of teeth (`TEETH_AREA_CV_MAX`). Geometry only: no
    plan is read, so the design is planned once."""
    from .config import satin_fill_hysteresis, satin_fill_vote, satin_floor_applies
    from .machine import satin_ceiling_mm
    from .stage6_satin import is_satin_candidate
    satin_max = satin_ceiling_mm(cfg)
    out: set[str] = set()
    for r in regions:
        if is_letter(r) or str(r.meta.get("tier", "auto")).lower() != "auto":
            continue
        bays = inlets(r.polygon)
        if len(bays) < TEETH_MIN or sum(b.area for b in bays) < SATIN_OVER_INLET_SHARE * r.polygon.area:
            continue
        try:
            if not is_satin_candidate(r.polygon, satin_max, design_class=design_class,
                                      per_stroke=cfg.satin_per_stroke,
                                      floor_applies=satin_floor_applies(cfg, design_class),
                                      vote=satin_fill_vote(cfg), hysteresis=satin_fill_hysteresis(cfg)):
                continue
        except Exception:  # noqa: BLE001 -- GEOS on a traced ring: left as it was
            continue
        if regular_teeth(r.polygon):
            out.add(str(r.shape_id))
    return out


def _inlet_depth(bay: Polygon, envelope: Polygon) -> float:
    """How far the inlet reaches in from the closed outline (mm)."""
    ring = envelope.exterior
    return max(ring.distance(Point(c)) for c in bay.exterior.coords)


def _teeth_geometry(poly):
    """-> (body polygon, [tooth pieces]) when `poly`'s outer edge is a row of
    teeth (comment at TEETH_MIN), else None. Geometry only."""
    bays = inlets(poly)
    if len(bays) < TEETH_MIN:
        return None
    # The tips' envelope: the outline closed by a disc wide enough that it
    # runs straight from tip to tip (an inlet's closing disc sags into the
    # gap and reads the teeth short: 0.71 of 0.80 mm on the synthetic gear).
    shell = Polygon(poly.exterior)
    envelope = shell.buffer(TIP_ENVELOPE_MM).buffer(-TIP_ENVELOPE_MM)
    depths = sorted(_inlet_depth(b, envelope) for b in bays)
    if depths[0] <= 0 or depths[-1] > TEETH_DEPTH_SPREAD * depths[0]:
        return None
    # The root: the envelope taken in by a depth; the body is the shape
    # inside it, the teeth what lies outside. Traced gaps do not all reach
    # one radius (Ahora's: 0.60-0.68 mm deep), so the deepest root that still
    # parts EVERY tooth from its neighbours is taken: from the shallowest
    # inlet's depth down, the first that gives the most pieces.
    best = None
    for f in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.6, 0.5, 0.4):
        root = envelope.buffer(-depths[0] * f, join_style=2)
        if root.is_empty:
            continue
        inner = poly.intersection(root)
        parts = [g for g in getattr(inner, "geoms", [inner]) if g.geom_type == "Polygon"]
        if not parts:
            continue
        body = max(parts, key=lambda g: g.area)
        if body.area < 0.4 * poly.area:
            continue
        rest = poly.difference(body)
        pieces = [g for g in getattr(rest, "geoms", [rest])
                  if g.geom_type == "Polygon" and g.area >= INLET_MIN_AREA_MM2]
        if best is None or len(pieces) > len(best[1]):
            best = (body, pieces)
    if best is None or len(best[1]) < max(TEETH_MIN, len(bays)):
        return None
    return best


def regular_teeth(poly) -> bool:
    """`poly`'s outer edge is a REGULAR row of teeth: `_teeth_geometry`
    splits it, its pieces' areas are alike (`TEETH_AREA_CV_MAX`), and they
    are short against the body (`TOOTH_LEN_OVER_BODY_MAX`)."""
    import statistics
    try:
        g = _teeth_geometry(poly)
    except Exception:  # noqa: BLE001 -- GEOS on a traced ring: not teeth
        return False
    if g is None:
        return False
    body, teeth = g
    areas = [t.area for t in teeth]
    if statistics.pstdev(areas) > TEETH_AREA_CV_MAX * statistics.mean(areas):
        return False
    return tooth_length(teeth) <= TOOTH_LEN_OVER_BODY_MAX * inscribed_width(body)


def tooth_length(teeth) -> float:
    """The mean long side of the teeth's boxes (mm): how long a tooth is,
    the way `TOOTH_LEN_OVER_BODY_MAX` was measured."""
    import statistics
    return statistics.mean(max(t.bounds[2] - t.bounds[0], t.bounds[3] - t.bounds[1]) for t in teeth)


def tooth_split(region):
    """-> (body, [teeth]) as copies of `region`, or None when its outer edge
    is not a row of teeth. The body keeps the region's id and tier; tooth k
    is `<id>-t<k>`, tier fill, rows square to its axis (`fill_angle_deg`),
    in turn round the body."""
    import math
    from dataclasses import replace
    from shapely import affinity
    g = _teeth_geometry(region.polygon)
    if g is None:
        return None
    body, pieces = g
    c0 = body.centroid
    pieces.sort(key=lambda t: math.atan2(t.centroid.y - c0.y, t.centroid.x - c0.x))
    teeth = []
    for k, t in enumerate(pieces):
        t = t.buffer(0)                      # a difference's piece can be invalid
        c = t.centroid
        foot = body.exterior.interpolate(body.exterior.project(c))
        ax, ay = c.x - foot.x, c.y - foot.y
        n = math.hypot(ax, ay)
        if n < 1e-6:
            return None
        down = affinity.translate(t, -ax / n * TOOTH_ROOT_MM, -ay / n * TOOTH_ROOT_MM)
        try:
            tp = unary_union([t, down]).buffer(0)
        except Exception:  # noqa: BLE001 -- GEOS topology: the tooth as traced
            tp = t
        if tp.geom_type != "Polygon":
            tp = max(getattr(tp, "geoms", [tp]), key=lambda g: g.area)
        if tp.is_empty:
            return None
        angle = (math.degrees(math.atan2(ay, ax)) + 90.0) % 180.0
        teeth.append(replace(region, shape_id=f"{region.shape_id}-t{k}", polygon=tp,
                             area_mm2=float(tp.area),
                             meta={**region.meta, "tier": "fill", "fill_angle_deg": round(angle, 2),
                                   TOOTH_OF_KEY: region.shape_id, "sew_order": k}))
    body_r = replace(region, polygon=body, area_mm2=float(body.area),
                     meta={**region.meta, "inlet_teeth": len(teeth), "sew_order": len(teeth)})
    return body_r, teeth


def rebuild(regions, ids, teeth: bool):
    """-> (regions, {body id: body polygon}). Each of `ids` is re-planned:
    split into its teeth and its body when `teeth` and its edge is toothed
    (`tooth_split`; pinned within its colour, teeth first), else re-tiered
    to fill (`as_fill`). More than one toothed shape in a colour keeps one
    shape's pins together: each next shape's pins start after the last's."""
    from dataclasses import replace
    out = []
    fill_ids = set()
    bodies: dict[str, Polygon] = {}
    slot = 0
    for r in regions:
        sid = str(r.shape_id)
        if sid not in ids:
            out.append(r)
            continue
        try:
            split = tooth_split(r) if teeth else None
        except Exception:  # noqa: BLE001 -- GEOS on a traced ring: the fill path
            split = None
        if split is None:
            fill_ids.add(sid)
            out.append(r)
            continue
        body, tth = split
        for t in tth:
            out.append(replace(t, meta={**t.meta, "sew_order": slot + t.meta["sew_order"]}))
        out.append(replace(body, meta={**body.meta, "sew_order": slot + body.meta["sew_order"]}))
        slot += len(tth) + 1
        bodies[sid] = body.polygon
    return (as_fill(out, fill_ids) if fill_ids else out), bodies


def _walk(ring, a, b, step: float) -> list:
    """Points along the closed `ring` from the projection of `a` to that of
    `b`, the shorter way round, about `step` mm apart (ends included)."""
    L = ring.length
    s0, s1 = ring.project(Point(a)), ring.project(Point(b))
    d = (s1 - s0) % L
    if d > L / 2:
        d -= L
    n = max(1, int(abs(d) // step) + 1)
    return [(p.x, p.y) for p in (ring.interpolate((s0 + d * i / n) % L) for i in range(n + 1))]


def bury_tooth_moves(plan, bodies: dict, step: float) -> int:
    """Every needle-up move (a jump, not a trim) from a split shape's tooth
    to its next tooth or to its body is sewn instead, as travel down to the
    body's edge, along it, and up into the next piece: the body sews last
    and its satin covers that path. -> moves buried."""
    import math
    n = 0
    tracks = {}
    for sid, body in bodies.items():
        inset = body.buffer(-THREAD_HALF_MM)
        tracks[sid] = (inset if (not inset.is_empty and inset.geom_type == "Polygon") else body).exterior

    def owner(run):
        s = str(run.shape_id)
        for sid in bodies:
            if s == sid or s.startswith(sid + "-t"):
                return sid
        return None

    for blk in plan.blocks:
        prev = None
        for run in blk.runs:
            if not run.points:
                continue
            if (prev is not None and run.jump and not run.trim and not run.tie_in_pts
                    and owner(run) is not None and owner(run) == owner(prev)):
                track = tracks[owner(run)]
                a, b = prev.points[-1], run.points[0]
                path = _walk(track, a, b, step)
                lead = [p for p in path if math.dist(p, a) > 0.05 and math.dist(p, b) > 0.05]
                run.points = lead + list(run.points)
                run.jump = False
                n += 1
            prev = run
    return n
