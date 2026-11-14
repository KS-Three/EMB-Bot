"""The art's own outline (`cfg.border_from_outline`, built OFF 2026-10-24).

The pro's border choice is not a stroke threshold (#1043 census, #1052):
MARINE and MFAB carry the same stroke and he satins one and borders the
other. What his bordered shapes share is an OUTLINE IN THE ART -- a thin
band of another colour drawn round the shape -- and his border is that
outline, sewn as one satin loop at 2.0-2.5 mm on top of the shape's fill:
BECKER's white faces inside their black keyline, MFab's black M-FAB inside
its white keyline.

An outline here is a region O with a hole that holds a BODY B:

  * B lies in the hole (`HOLD_FRAC` of its exterior, within `HOLD_PAD_MM`)
    and meets the hole's ring along `TOUCH_FRAC` of its edge, and the shapes
    that do fill at least `FILL_FRAC` of the hole -- so a letter's counter
    sitting inside a face is not a body of the face's keyline, and MFab's
    F and hyphen, touching in one hole, are both bodies;
  * B is not a COUNTER: not tagged `counter`, and not held by a letter at
    all, sewn or not -- the inside of a satin O is not a shape the pro
    borders, whatever colour it is (Hotel Fremont's O's hold white the field
    sews, and looping them sewed a spiked sun where he sews the letter);
  * B is wider than its outline is thick: B's stroke (2 x area / perimeter)
    is at least `machine.OUTLINE_BODY_RATIO` x the outline's band round it
    (O's area within `machine.OUTLINE_PROBE_MM` of B, per mm of B's edge).
    Measured on the census cache (`tools/outline_census.py`): BECKER's faces
    read 1.34-2.30, MFab's big letters 1.65-3.14; MFab's AND WELDING LLC
    inside the same keyline (0.50-0.87, sewn satin by the pro) and every
    letter in Fremont's white field (0.03-0.55) fall under it.

The hole ring must be a loop the border tier would sew
(`machine.BORDER_MIN_LOOP_MM`), and O must be a band: at least
`machine.OUTLINE_REACH_FRAC` of it within `OUTLINE_PROBE_MM` of its looped
holes (Becker's keyline 0.99-1.00, MFab's 1.00; Bridge's wheel, a ring with
spokes, 0.67-0.71). Pure: reads geometry and tags.

`cfg.border_from_outline_line_art_guard` (#1078, ON since 2026-10-25) refuses one
more class: LINE ART (`line_art_reading`). Bridge's bowl-and-waves drawing is
a band by the reach rule (0.99-1.00) and holds yellow cells of the disc it is
drawn on, so it read as an outline; sewn as one, its cells' tips fan spikes
and the drawing's stroke ends, beyond every loop and under the fill floor,
are dropped. An outline is line art when it is a hairline (under
`machine.OUTLINE_LINE_ART_FILL_SHARE` of it is `machine.MIN_FILL_WIDTH_MM`
across) AND its loops leave strokes (`machine.OUTLINE_LINE_ART_DROP_FRAC` of
it beyond the loop width and too thin to fill). Either alone is wrong:
To-a-T Machine's 0.8 mm frame is as thin as the bowl but is a pure ring the
pro widens to 2.0-2.3 mm; MFab's keyline leaves 0.038 of itself in slivers
along its outer edge but is a fill floor across over 0.74 of it.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from . import machine
from .columns import is_lettering

#: share of a body's exterior that must lie in the hole (the shapes are
#: vectorized separately; their edges disagree by simplification wobble).
HOLD_FRAC = 0.8
HOLD_PAD_MM = 0.3
#: share of the hole's area its bodies together must cover (MFab's F and
#: hyphen touch, and share one keyline hole).
FILL_FRAC = 0.5
#: share of a body's own edge that must run along the hole's ring: a letter's
#: counter inside a face is in the hole but never meets it.
TOUCH_FRAC = 0.25


def _counter(body, holder, cfg) -> bool:
    return bool((body.meta or {}).get("counter")) or is_lettering(holder, cfg)


def outline_measures(holder, body, hole: Polygon) -> tuple[float, float]:
    """(band, stroke) mm: the outline's thickness round `body` and the
    body's own stroke."""
    ext = Polygon(body.polygon.exterior)
    band = holder.polygon.intersection(ext.buffer(machine.OUTLINE_PROBE_MM)).area
    band /= max(ext.exterior.length, 1e-9)
    stroke = 2.0 * body.polygon.area / max(body.polygon.length, 1e-9)
    return band, stroke


def _looped(poly: Polygon) -> list[Polygon]:
    return [Polygon(r) for r in poly.interiors
            if LineString(r.coords).length >= machine.BORDER_MIN_LOOP_MM]


def line_art_reading(holder, bodies: list[tuple[object, Polygon]]) -> tuple[float, float]:
    """(fill share, dropped share) of an outline: the share of it at least
    `machine.MIN_FILL_WIDTH_MM` across (an opening by half that), and the
    share its loops leave and the rest-fill drops -- further than the loop
    width (`outline_width_mm`) from every looped hole, in pieces too thin to
    fill, as `stage6_border.keyline_rest` reads the band stage 7 sews."""
    poly = holder.polygon
    half = machine.MIN_FILL_WIDTH_MM / 2.0
    fill = poly.buffer(-half).buffer(half).area / poly.area
    width = outline_width_mm(holder, bodies)
    rest = poly.difference(unary_union([h.buffer(width) for h in _looped(poly)]))
    parts = getattr(rest, "geoms", [rest])
    dropped = sum(p.area for p in parts
                  if p.geom_type == "Polygon" and not p.is_empty and p.buffer(-half).is_empty)
    return fill, dropped / poly.area


def _line_art(holder, bodies) -> bool:
    fill, dropped = line_art_reading(holder, bodies)
    return (fill < machine.OUTLINE_LINE_ART_FILL_SHARE
            and dropped >= machine.OUTLINE_LINE_ART_DROP_FRAC)


def find_art_outlines(regions, cfg=None, *,
                      line_art_guard: bool | None = None,
                      group_decide=None) -> dict[str, list[tuple[str, Polygon]]]:
    """-> {outline shape_id: [(body shape_id, hole polygon), ...]} for every
    region whose hole holds a body under the rule above, bodies in input
    order. A body has at most one outline (the first holder that reads).
    `line_art_guard` (None: `cfg.border_from_outline_line_art_guard`) drops
    an outline that reads as line art, and frees its bodies.

    `group_decide` (None: `group_consistency.outline_body_decider` under
    `cfg.group_consistent_outline_body`, else the per-body test) takes the holder and
    its candidates, (body, hole, band, stroke) in hole then input order, and
    returns the (body, hole) pairs it keeps. The per-body test keeps those
    with stroke >= `machine.OUTLINE_BODY_RATIO` x band, exactly as before."""
    regions = list(regions)
    if line_art_guard is None:
        line_art_guard = bool(getattr(cfg, "border_from_outline_line_art_guard", False))
    if group_decide is None and getattr(cfg, "group_consistent_outline_body", False):
        from .group_consistency import outline_body_decider
        group_decide = outline_body_decider(machine.MIN_FILL_WIDTH_MM)
    out: dict[str, list[tuple[str, Polygon]]] = {}
    taken: set[str] = set()
    for o in regions:
        poly = o.polygon
        if poly is None or poly.is_empty or poly.geom_type != "Polygon" or not poly.interiors:
            continue
        holes = _looped(poly)
        if not holes:
            continue
        # a BAND: nearly all of it hugs its holes. Bridge's wheel (a ring
        # with eight spokes round the yellow disc) is a drawing that holds
        # the disc, 0.67-0.71 of it near the hole; every outline the pro
        # borders reads 0.99 and up.
        near = poly.intersection(unary_union(holes).buffer(machine.OUTLINE_PROBE_MM)).area
        if near < machine.OUTLINE_REACH_FRAC * poly.area:
            continue
        ox0, oy0, ox1, oy1 = poly.bounds
        inside = []
        for b in regions:
            if (b is o or b.shape_id in taken or b.polygon is None or b.polygon.is_empty
                    or b.polygon.geom_type != "Polygon"):
                continue
            bx0, by0, bx1, by1 = b.polygon.bounds
            if bx0 < ox0 or by0 < oy0 or bx1 > ox1 or by1 > oy1:
                continue
            inside.append(b)
        # Every candidate first, measured once: a body's band and stroke do
        # not depend on which of the holder's holes holds it, so a body the
        # test refuses in one hole is refused in any, and the first hole
        # that holds it is the one it is recorded in -- as the one-pass loop
        # this replaced did.
        cands = []
        cand_ids: set[str] = set()
        for hole in holes:
            ring = hole.exterior.buffer(HOLD_PAD_MM)
            pad = hole.buffer(HOLD_PAD_MM)
            held = []
            for b in inside:
                ext = Polygon(b.polygon.exterior)
                if ext.area <= 0 or pad.intersection(ext).area < HOLD_FRAC * ext.area:
                    continue
                if b.polygon.exterior.intersection(ring).length < TOUCH_FRAC * b.polygon.exterior.length:
                    continue
                held.append((b, ext))
            if sum(ext.area for _b, ext in held) < FILL_FRAC * hole.area:
                continue
            for b, _ext in held:
                if b.shape_id in taken or b.shape_id in cand_ids or _counter(b, o, cfg):
                    continue
                band, stroke = outline_measures(o, b, hole)
                cands.append((b, hole, band, stroke))
                cand_ids.add(b.shape_id)
        if group_decide is None:
            found = [(b, hole) for b, hole, band, stroke in cands
                     if stroke >= machine.OUTLINE_BODY_RATIO * band]
        else:
            found = list(group_decide(o, cands))
        taken.update(b.shape_id for b, _hole in found)
        if found and line_art_guard and _line_art(o, found):
            taken.difference_update(b.shape_id for b, _hole in found)
            continue
        for b, hole in found:
            out.setdefault(o.shape_id, []).append((b.shape_id, hole))
    return out


#: stations along a hole's ring where the band's thickness is read
_THICKNESS_STEP_MM = 0.3


def band_thickness(band, hole: Polygon) -> list[float]:
    """The band's thickness square to `hole`'s ring, read every
    `_THICKNESS_STEP_MM` along it: how far a ray from the ring runs through
    `band` before leaving it, capped just past `machine.SATIN_MAX_WIDTH_MM`
    (thicker than that is not one satin, whatever it is)."""
    from .stage6_border import _exact_cross

    ring = LineString(hole.exterior.coords)
    total = ring.length
    n = max(8, int(total / _THICKNESS_STEP_MM))
    cap = machine.SATIN_MAX_WIDTH_MM + 1.0
    out: list[float] = []
    for i in range(n):
        s = total * i / n
        p = ring.interpolate(s)
        a = ring.interpolate((s - 0.15) % total)
        b = ring.interpolate((s + 0.15) % total)
        tx, ty = b.x - a.x, b.y - a.y
        d = (tx * tx + ty * ty) ** 0.5
        if d < 1e-9:
            continue
        nx, ny = -ty / d, tx / d
        # one side of the ring is the hole (0), the other the band
        out.append(max(_exact_cross(p.x + nx * 1e-4, p.y + ny * 1e-4, nx, ny, cap, band),
                       _exact_cross(p.x - nx * 1e-4, p.y - ny * 1e-4, -nx, -ny, cap, band)))
    return out


def shaped_width_mm(band, hole: Polygon) -> float | None:
    """The loop width for a SHAPED band round `hole`, or None when the band
    is not one (`cfg.border_from_outline_follow_shape`, built OFF 2026-11-13).

    The rule above sews an outline as a loop of ONE width: right for a band
    of one width (a keyline, a frame), and for one too thick to be a satin
    (Becker's drop shadow, sewn as a loop over a fill). It is wrong for a
    band whose OUTER edge has a shape of its own: Commons "Ahora" draws a
    white gear round a yellow disc, 17 teeth, and the loop on the disc's edge
    sewed a ring of spokes at every size (Kent, 2026-11-13: "its still a
    circle and not a gear like the image").

    A band is shaped when both hold, on `band_thickness`:

      * all of it fits one satin: never thicker than
        `machine.SATIN_MAX_WIDTH_MM`, so a cross from the hole's ring can
        reach the outer edge everywhere;
      * its thickness swings (p90 - p10) by at least
        `machine.SATIN_MIN_CROSS_MM`: the outer edge moves by more than the
        shortest stitch there is, so thread can show it.

    Measured 2026-11-13: the gear swings 0.54 mm at 60 mm wide (0.86 to 1.40,
    max 1.45) and 0.89 at 100 (max 2.40); at 40 mm 0.36, under a stitch, and
    it stays a ring. To-a-T Machine's frame swings 0.14 to 0.19 (a band of
    one width, which the pro widens). Becker's, MFab's and the Drone's bands
    all run past 7 mm somewhere. MFab's hat at 100 mm has two small loops
    that read shaped among its outline's eight; the caller asks for ALL of
    an outline's loops or none, so it is untouched. Plans compared with the
    flag on and off at 100 mm: MFab, Becker, To-a-T and `hed_p_e_logo`
    byte-identical, the gear alone changed.

    The width returned is the band's thickest reading: the caller cuts each
    cross where it leaves the ART (not the art widened), so a cross is as
    long as the band is thick where it stands -- long on a tooth, short in a
    root."""
    t = band_thickness(band, hole)
    if len(t) < 8:
        return None
    t = sorted(t)
    if t[-1] > machine.SATIN_MAX_WIDTH_MM:
        return None
    p10 = t[int(0.10 * (len(t) - 1))]
    p90 = t[int(0.90 * (len(t) - 1))]
    if p90 - p10 < machine.SATIN_MIN_CROSS_MM:
        return None
    return t[-1]


#: how finely `shaped_stations` reads the band to find where it steps
_STEP_READ_MM = 0.025


def shaped_stations(band, hole: Polygon, density_mm: float) -> list[tuple[float, float]] | None:
    """Where a shaped band's loop puts its needle, round `hole`'s ring: the
    ring cut into stretches where the band is THICK (a tooth) and THIN (a
    root), and every stretch given the same kind of share -- a whole number
    of stitches, evenly spaced, none of them on the step between two
    stretches. -> ring points in ring order, or None when the band has no
    steps to lock to.

    Spaced evenly round the ring with no regard for the teeth, the gear at
    100 mm gave some teeth three long stitches and some two, and at 60 mm one
    or two: a gear with ragged teeth (Kent, 2026-11-13, on bean outlines:
    "building a swiss watch, and not a playhouse out of logs"; it holds for a
    satin edge as well). A loop's crosses alternate rails, so the outer edge
    is drawn by every SECOND station: a stretch gets `2 x round(length /
    density)` stations, never fewer than two, so each tooth and each root
    shows at least one stitch of its own length and all teeth of one size
    show the same number."""
    ring = LineString(hole.exterior.coords)
    total = ring.length
    if total <= 0:
        return None
    from .stage6_border import _exact_cross

    cap = machine.SATIN_MAX_WIDTH_MM + 1.0
    n = max(16, int(total / _STEP_READ_MM))
    read: list[float] = []
    for i in range(n):
        s = total * i / n
        p = ring.interpolate(s)
        a = ring.interpolate((s - 0.15) % total)
        b = ring.interpolate((s + 0.15) % total)
        tx, ty = b.x - a.x, b.y - a.y
        d = (tx * tx + ty * ty) ** 0.5
        if d < 1e-9:
            read.append(read[-1] if read else 0.0)
            continue
        nx, ny = -ty / d, tx / d
        read.append(max(_exact_cross(p.x + nx * 1e-4, p.y + ny * 1e-4, nx, ny, cap, band),
                        _exact_cross(p.x - nx * 1e-4, p.y - ny * 1e-4, -nx, -ny, cap, band)))
    ordered = sorted(read)
    mid = (ordered[int(0.10 * (n - 1))] + ordered[int(0.90 * (n - 1))]) / 2.0
    thick = [t >= mid for t in read]
    if all(thick) or not any(thick):
        return None
    # stretches, starting on a step so none straddles the ring's own seam
    first = next(i for i in range(n) if thick[i] != thick[i - 1])
    cuts = [i for i in range(first, first + n) if thick[i % n] != thick[(i - 1) % n]]
    # a stretch shorter than half a stitch is the reading's noise on a step:
    # it joins the stretch before it
    min_len = density_mm / 2.0
    kept = [cuts[0]]
    for c in cuts[1:]:
        if (c - kept[-1]) * total / n < min_len:
            kept.pop() if len(kept) > 1 else None
            continue
        kept.append(c)
    if len(kept) < 2:
        return None
    out: list[tuple[float, float]] = []
    # The stitches are counted on the band's OUTER edge, where a tooth shows
    # (law 4: the outer rail holds the density). The ring is the inner rail,
    # so the same stitches stand closer together on it: a stretch of ring
    # `length` long under a band `t` thick spans `length x (r + t) / r` out
    # there, `r` the ring's own radius (its length / 2 pi). Counted on the
    # ring, the gear's teeth fanned into pairs of spokes. Never so many that
    # two needle holes on the ring come within
    # `machine.SATIN_SHORT_STITCH_AT_MM` of each other.
    radius = total / (2.0 * math.pi)
    for a, b in zip(kept, kept[1:] + [kept[0] + n]):
        length = (b - a) * total / n
        thick_here = sorted(read[i % n] for i in range(a, b))[(b - a) // 2]
        outer = length * (radius + thick_here) / radius
        most = max(1, int(length / machine.SATIN_SHORT_STITCH_AT_MM))
        k = 2 * max(1, min(most, int(round(outer / density_mm))))
        for j in range(k):
            # reading `a` is the first of its stretch: the step itself lies
            # half a reading before it (taken at `a`, every stretch sat
            # 0.04 mm round the ring from its tooth)
            at = a - 0.5 + (b - a) * (j + 0.5) / k
            p = ring.interpolate((at * total / n) % total)
            out.append((p.x, p.y))
    return out if len(out) >= 8 else None


def outline_width_mm(holder, bodies: list[tuple[object, Polygon]]) -> float:
    """The pro's border width for one outline: the art's own outline
    thickness round its bodies (the median `outline_measures` band),
    clamped to `machine.OUTLINE_WIDTH_MM` -- his border is the outline
    widened, one width all round. Census cache: Becker large 2.45 -> his
    2.40, small 2.09 -> 2.00; MFab 2.02 / 1.92 against his 2.40 / 2.13 is the
    widest miss. By the body's size instead, Becker large sewed 1.7 against
    his 2.4. The 1.5 floor keeps a hairline keyline a column (Bridge's 1.08
    mm bowl drawing would sew at 1.08)."""
    import statistics
    band = statistics.median(outline_measures(holder, b, hole)[0] for b, hole in bodies)
    lo, hi = machine.OUTLINE_WIDTH_MM
    return min(hi, max(lo, band))
