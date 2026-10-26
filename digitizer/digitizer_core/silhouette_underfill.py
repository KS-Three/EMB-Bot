"""Fill the silhouette under a ring, then sew on top (`cfg.silhouette_underfill`, built OFF).

L9 (2026-10-24, Kent: "Build under-fill, OFF"). The cross-underlay lane read
MFab's black band and Becker's ring as satin where the pro "fills" them. Read
per shape (`tools/tier_census.py`, 21 paired jobs, 191 non-lettering shapes)
no width or area rule separates his fills from his satins: kappa 0.170 today,
0.198 for the best rule, which moves MFab's band alone. Read per COLOUR BLOCK
the jobs agree on something else:

  * MFab hat: his black block covers our band 1.00 and its holes (the M-FAB
    letters and the white keyline) 0.82 -- ONE fill of the band's outline,
    holes closed, with the white keyline sewn on top of it;
  * Becker beanie: his letter-colour blocks cover 0.91 of the BECKER
    silhouette, 0.74 of our ring included, and the ring is satin on top;
  * Hotel Fremont hat: his ground block covers 0.92 of the ground's outline
    -- the ground runs under the lettering.

So the construction is: a RING -- a shape with holes, those holes holding other
shapes -- gets its outline (holes closed) filled once, underneath, in the
colour that covers most of that outline (the ring counting for its own
colour); the ring and everything inside it then sew on top. Two cases fall
out of the colour:

  * the ring's colour covers most (MFab: black band and black letters;
    Fremont: the ground round its lettering): the ring itself becomes the
    under-fill -- it sews as a FILL of its outline -- and the inner shapes of
    its colour are merged into that fill (his black block reads FILL over
    MFab's letters; nothing black is sewn on them again);
  * another colour covers most (Becker with `sew_enclosed_white`: 958 mm2 of
    white letters in a 730 mm2 black ring): the largest inner shape of that
    colour sews the outline, the rest of that colour merge into it, and the
    ring sews as it did, on top.

Against it: the Precision Drone's ground (a gradient render) reads as a ring
here, and no block of his covers more than 0.51 of its outline.

The host shape keeps its own ARTWORK as its stage-5 footprint and sews the
outline through `stage5_overlap`'s ground-under path (`UNDERFILL_KEY`), the
one bean letters use: so nothing sewn later is clipped by the outline, and
the holes the outline covers are not held open. Its thread layer moves ahead
of the ring's and every inner colour's, on copies -- on MFab that puts the
white keyline ON TOP of the black, the reverse of `enclosed_white_keyline`'s
order (#1059), which stays Kent's flip.

Off: `apply` is never called; byte-identical.
"""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry import Polygon
from shapely.ops import unary_union

#: meta key: the outline (a Polygon) the host sews under everything else.
UNDERFILL_KEY = "silhouette_underfill"
#: meta key on the host: the ring it fills under (shape id), for reports.
UNDERFILL_OF_KEY = "silhouette_underfill_of"

#: a ring smaller than this is a letter with a counter, not a silhouette
RING_MIN_AREA_MM2 = 200.0
#: an inner shape lies this much inside the ring's outline ...
INSIDE_MIN = 0.9
#: ... and at most this much on the ring itself (the `fill_inside_satin_border` test)
ON_RING_MAX = 0.25
#: the holes must hold shapes: their sewn inner shapes cover this share of
#: the holes' area (MFab 0.8+, Becker with its letters sewn 0.9+)
HOLES_HELD_MIN = 0.5

#: every tag a lettering lane reads a shape by: a lettering RING (an O round
#: a dot) is the lettering lane's, never a silhouette
_LETTER_KEYS = ("text_candidate", "lettering_group", "word_id", "text_cluster_id",
                "bean_letter_spines", "text_cluster_widened_mm")

# --- Panels (`cfg.silhouette_underfill_panels`, 2026-10-25, built OFF) ----------
#
# The pro's MFab (hat and LC agree): black tatami under the whole silhouette,
# the white keyline as satin loops round each M-FAB letter ON it, and the small
# second line (AND WELDING, LLC) as black satin sewn AFTER the white on a white
# panel that is CLOSED under them (white under them 1.000; black fill under
# them 0.12-0.18). Under-fill alone merged those small letters into the black.
# A RIDER is a text-tagged shape in the host's thread, sitting INSIDE_MIN in a
# hole of a white field (`sew_enclosed_white == "field"`), whose word is mostly
# NOT the art outline's bodies (WELDING's I is a body; its word is not). Riders
# are never merged, sew in a layer of their own right after the field's, and
# the field fills its rider holes as one closed panel under them.
#: meta on a white field: the holes holding its riders, [Polygon]
RIDER_HOLES_KEY = "underfill_rider_holes"
#: meta on a rider: the field (shape id) it rides on
RIDER_OF_KEY = "underfill_rider_of"
#: a word rides when MORE than this share of its letters are not outline bodies
WORD_NONBODY_MIN = 0.5

#: meta on a white field (`cfg.keyline_fold_slivers`): the sliver ids folded in
FOLDED_KEY = "keyline_folded"


def fold_keyline_slivers(regions):
    """`cfg.keyline_fold_slivers` (built OFF 2026-10-26): every sliver of a
    sewn white field's own thread folds back into the field. -> (regions,
    {field id: [sliver ids]}): copies where changed, the list itself when
    nothing folds.

    MFab's keyline is drawn with a dark hairline along its inner edge, so the
    tracer returns it as the field plus 31 (hat) / 51 (LC) white slivers,
    0.1-0.3 mm wide, on the letters' side of the hairline, each sewn as its
    own run with a cut either side. The professional sews one keyline: his
    satin's rail is on the letter, and every one of our sliver stitches lies
    within 0.3 mm of his white. Ours rides the field's hole -- the hairline's
    outer edge -- so its crosses never reach the slivers.

    A sliver here is a region in the field's thread that
    `apply_enclosed_white` did not route (no `sew_enclosed_white`), is no
    text, measured narrower than a thread (`stitch_width_measured_mm` under
    `COVERAGE_THREAD_W_MM`), and lies within a thread of the field: a gap no
    thread fits in. It folds in with the strip between them (each side grown
    by half a thread, where both reach), so the field's hole moves onto the
    letter and the loop crosses the sliver and the hairline as the pro's
    does. A fold that would not come out one polygon is not made. No new
    constant. Before `_art_outlines`, so the outline's holes, widths and
    loops are read on the folded field."""
    from . import machine
    half = machine.COVERAGE_THREAD_W_MM / 2.0
    fields = [r for r in regions
              if r.meta.get("sew_enclosed_white") == "field" and r.meta.get("stitched", True)]
    if not fields:
        return regions, {}
    gone: dict[str, str] = {}
    grown: dict[str, Polygon] = {}
    for f in fields:
        poly = f.polygon
        for r in regions:
            if (r is f or r.shape_id in gone or r.thread_index != f.thread_index
                    or not r.meta.get("stitched", True) or r.meta.get("sew_enclosed_white")
                    or r.meta.get("text_cluster_id") is not None):
                continue
            w = r.meta.get("stitch_width_measured_mm")
            if w is None or w >= machine.COVERAGE_THREAD_W_MM:
                continue
            if r.polygon.distance(poly) > machine.COVERAGE_THREAD_W_MM:
                continue
            bridge = r.polygon.buffer(half).intersection(poly.buffer(half))
            joined = unary_union([poly, r.polygon, bridge]).buffer(0)
            if joined.geom_type != "Polygon":
                continue
            # the strip leaves slits where the two edges part (the sliver's
            # ends): a hole thinner than a thread (2 * area / perimeter)
            # within a thread of the sliver is part of the same gap
            reach = r.polygon.buffer(machine.COVERAGE_THREAD_W_MM)
            keep = []
            for ring in joined.interiors:
                h = Polygon(ring)
                if (2.0 * h.area / max(h.length, 1e-9) < machine.COVERAGE_THREAD_W_MM
                        and h.intersects(reach)):
                    continue
                keep.append(ring)
            poly = Polygon(joined.exterior, keep)
            gone[r.shape_id] = f.shape_id
        if poly is not f.polygon:
            grown[f.shape_id] = poly
    if not gone:
        return regions, {}
    folded: dict[str, list[str]] = {}
    for sid, fid in gone.items():
        folded.setdefault(fid, []).append(sid)
    out = []
    for r in regions:
        if r.shape_id in gone:
            continue
        if r.shape_id in grown:
            g = grown[r.shape_id]
            r = replace(r, polygon=g, area_mm2=g.area,
                        meta={**r.meta, FOLDED_KEY: sorted(folded[r.shape_id])})
        out.append(r)
    return out, folded


def _is_letter(r) -> bool:
    m = r.meta or {}
    return any(m.get(k) for k in _LETTER_KEYS)


def _ring_candidates(regions):
    for r in regions:
        p = r.polygon
        if (p is None or p.geom_type != "Polygon" or not p.interiors
                or p.area < RING_MIN_AREA_MM2
                or str(r.meta.get("tier", "auto")).lower() != "auto"
                or _is_letter(r)):
            continue
        yield r


def _inner(ring, regions, used: set[str]):
    """Stitched shapes inside the ring's outline and not on the ring."""
    outline = Polygon(ring.polygon.exterior)
    out = []
    for r in regions:
        if r is ring or r.shape_id in used:
            continue
        p = r.polygon
        if p is None or p.is_empty or p.area <= 0 or not p.intersects(outline):
            continue
        if (p.intersection(outline).area >= INSIDE_MIN * p.area
                and p.intersection(ring.polygon).area <= ON_RING_MAX * p.area):
            out.append(r)
    return outline, out


def plan(regions, unsewn=(), riders=()):
    """-> [(ring, host, outline, merged ids, inner shapes)] for every ring
    this reads, the biggest first; a shape serves one ring at most.

    `unsewn` are the shapes left as garment on purpose (enclosed background,
    a review `stitched: false`): the outline is cut back off them, so the
    under-fill never sews over fabric the design shows -- MFab's white
    keyline without `sew_enclosed_white`. They never count as holding a hole.

    `riders` (shape ids, `cfg.silhouette_underfill_panels`) are never merged:
    they sew on their own, on top. Empty: as before."""
    used: set[str] = set()
    out = []
    for ring in sorted(_ring_candidates(regions), key=lambda r: -r.polygon.area):
        if ring.shape_id in used:
            continue
        outline, inner = _inner(ring, regions, used)
        holes = outline.area - ring.polygon.area
        bare = [u.polygon for u in unsewn
                if u.polygon is not None and u.polygon.intersects(outline)]
        if bare:
            outline = outline.difference(unary_union(bare))
        if not inner or holes <= 0:
            continue
        if sum(r.polygon.area for r in inner) < HOLES_HELD_MIN * holes:
            continue
        # the colour covering most of the OUTLINE: the ring counts for its own
        # colour -- Fremont's ground (2,131 mm2 round 162 letters) fills under
        # its lettering, Becker's 730 mm2 ring loses to 958 mm2 of letters
        by_thread: dict[int, float] = {ring.thread_index: ring.polygon.area}
        for r in inner:
            by_thread[r.thread_index] = by_thread.get(r.thread_index, 0.0) + r.polygon.area
        colour = max(by_thread, key=lambda t: (by_thread[t], -t))
        # a shape with a review tier is an instruction: it sews as told, on
        # top, never merged and never the host
        same = [r for r in inner if r.thread_index == colour
                and str(r.meta.get("tier", "auto")).lower() == "auto"
                and r.shape_id not in riders]
        if ring.thread_index != colour and not same:
            continue
        if ring.thread_index == colour:
            host = ring
            merged = [r.shape_id for r in same]
        else:
            host = max(same, key=lambda r: r.polygon.area)
            merged = [r.shape_id for r in same if r is not host]
        out.append((ring, host, outline, merged, inner))
        used.update({ring.shape_id, host.shape_id, *(r.shape_id for r in inner)})
    return out


def _word(r):
    m = r.meta or {}
    return m.get("text_cluster_id") or m.get("stitch_width_group") or r.shape_id


def _fields(regions):
    return [r for r in regions
            if (r.meta or {}).get("sew_enclosed_white") == "field"
            and r.polygon is not None and r.polygon.geom_type == "Polygon"
            and r.polygon.interiors]


def _hole_of(r, field):
    """The hole of `field` holding `INSIDE_MIN` of `r`, or None."""
    for ring in field.polygon.interiors:
        hole = Polygon(ring)
        if r.polygon.intersection(hole).area >= INSIDE_MIN * r.polygon.area:
            return hole
    return None


def find_riders(regions, unsewn=(), outlines=None) -> list[str]:
    """`cfg.silhouette_underfill_panels`: the shape ids that ride a white
    panel instead of merging into the under-fill (module note above).
    `outlines`: `art_outline.find_art_outlines`' {outline id: [(body id,
    hole, width)]} -- a body is lettering the keyline loops, not a rider."""
    fields = _fields(regions)
    if not fields:
        return []
    bodies = {b[0] for bs in (outlines or {}).values() for b in bs}
    words: dict = {}
    for r in regions:
        if _is_letter(r):
            words.setdefault(_word(r), []).append(r.shape_id)
    rides = {w for w, ids in words.items()
             if sum(1 for i in ids if i not in bodies) > WORD_NONBODY_MIN * len(ids)}
    out = []
    for _ring, host, _outline, _merged, inner in plan(regions, unsewn):
        for r in inner:
            if (r is host or r.thread_index != host.thread_index or not _is_letter(r)
                    or _word(r) not in rides):
                continue
            if any(_hole_of(r, f) is not None for f in fields):
                out.append(r.shape_id)
    return sorted(out)


def _panels(regions, riders: set[str], outlines, overlap_mm: float):
    """{field id: (panel, [rider holes], [rider ids])}: the white a field
    sews under its riders -- the parts no body loop reaches of the field with
    its rider holes closed (`keyline_rest`, the loops `outline_holes` makes,
    rider holes left out) that hold a rider hole, with those holes."""
    from . import machine
    from .stage6_border import keyline_rest, outline_holes
    by_id = {r.shape_id: r for r in regions}
    out = {}
    for field in _fields(regions):
        holes: dict = {}
        ids = []
        for rid in sorted(riders):
            r = by_id.get(rid)
            hole = None if r is None else _hole_of(r, field)
            if hole is not None:
                holes.setdefault(hole.exterior.wkb, hole)
                ids.append(rid)
        if not holes:
            continue
        closed = Polygon(field.polygon.exterior,
                         [ring for ring in field.polygon.interiors
                          if Polygon(ring).exterior.wkb not in holes])
        bodies = [(h, w) for _b, h, w in (outlines or {}).get(field.shape_id, [])]
        width = max((w for _h, w in bodies), default=machine.KEYLINE_WIDTH_MM)
        looped = [(h, w) for h, w in outline_holes(field.polygon, bodies, width)
                  if h.exterior.wkb not in holes]
        rest = keyline_rest(closed, 0.0, overlap_mm, machine.MIN_FILL_WIDTH_MM, looped=looped)
        held = [p for p in rest
                if any(p.intersection(h).area > 0.5 * h.area for h in holes.values())]
        out[field.shape_id] = (unary_union(held + list(holes.values())),
                               list(holes.values()), ids)
    return out


def apply_cfg(regions, unsewn, cfg, outlines):
    """`plan_stitches`' call, `cfg.silhouette_underfill` ON: -> (regions,
    report, outlines). With `cfg.silhouette_underfill_panels` (read only with
    `sew_enclosed_white` and `border_from_outline`) the riders are found,
    dropped from the outlines' body lists (a rider is no outline's body: no
    loop round it, no body fill) and passed on; with none, `apply` exactly
    as before and the outlines untouched."""
    riders = []
    if (getattr(cfg, "silhouette_underfill_panels", False) and cfg.sew_enclosed_white
            and cfg.border_from_outline):
        riders = find_riders(regions, unsewn, outlines)
    if not riders:
        out, report = apply(regions, unsewn)
        return out, report, outlines
    gone = set(riders)
    outlines = {oid: [b for b in bodies if b[0] not in gone]
                for oid, bodies in (outlines or {}).items()}
    outlines = {k: v for k, v in outlines.items() if v} or None
    out, report = apply(regions, unsewn, riders=riders, outlines=outlines,
                        overlap_mm=cfg.overlap_mm)
    return out, report, outlines


def apply(regions, unsewn=(), riders=(), outlines=None, overlap_mm: float = 0.0):
    """`cfg.silhouette_underfill` ON: -> (regions as copies, report). The
    hosts carry `UNDERFILL_KEY` and the fill tier, merged shapes are gone,
    and each host's layer sews before its ring's and its inner colours'.
    `unsewn`: see `plan`.

    `riders` (`cfg.silhouette_underfill_panels`, `find_riders`): never merged;
    each field holding some fills them a closed white panel (`_panels`,
    tagged `RIDER_HOLES_KEY`), the host's outline gives that panel up (shrunk
    by `overlap_mm`, so the black still tucks under its edge), and the riders
    sew in a layer of their own right after the field's -- black, white,
    black. Empty: as before, byte for byte."""
    rings = plan(regions, unsewn, riders)
    if not rings:
        return regions, []
    panels = _panels(regions, set(riders), outlines, overlap_mm) if riders else {}
    cut = (unary_union([p for p, _h, _i in panels.values()]).buffer(-overlap_mm)
           if panels else None)
    host_meta: dict[str, dict] = {}
    dropped: set[str] = set()
    order = sorted({r.meta["layer"] for r in regions})
    moved = False
    report = []
    for ring, host, outline, merged, inner in rings:
        if cut is not None and not cut.is_empty and outline.intersects(cut):
            outline = outline.difference(cut)
        host_meta[host.shape_id] = {UNDERFILL_KEY: outline, UNDERFILL_OF_KEY: ring.shape_id,
                                    "tier": "fill"}
        dropped.update(merged)
        # every other colour in play -- the ring's, when it is not the host's,
        # and each inner colour -- must sew after the host's layer
        ahead = [r.meta["layer"] for r in [ring, *inner]
                 if r.thread_index != host.thread_index]
        here = host.meta["layer"]
        first = min(ahead, default=here)
        if order.index(first) < order.index(here):
            order.remove(here)
            order.insert(order.index(first), here)
            moved = True
        report.append({"ring": ring.shape_id, "host": host.shape_id,
                       "outline_mm2": round(outline.area, 1), "merged": sorted(merged)})
    # riders: a layer of their own, right after their field's
    rider_layer: dict[str, tuple] = {}
    extra_meta: dict[str, dict] = {}
    if panels:
        by_id = {r.shape_id: r for r in regions}
        for fid, (panel, holes, ids) in sorted(panels.items()):
            f_layer = by_id[fid].meta["layer"]
            key = ("rider", f_layer)
            if key not in order:
                order.insert(order.index(f_layer) + 1, key)
                moved = True
            extra_meta.setdefault(fid, {})[RIDER_HOLES_KEY] = holes
            for rid in ids:
                rider_layer[rid] = key
                extra_meta.setdefault(rid, {})[RIDER_OF_KEY] = fid
            report.append({"field": fid, "panel_mm2": round(panel.area, 1), "riders": ids})
    renum = {L: i for i, L in enumerate(order)} if moved else {L: L for L in order}

    def layer_of(r):
        return renum[rider_layer.get(r.shape_id, r.meta["layer"])]
    out = []
    for i, r in sorted(enumerate(regions), key=lambda t: (layer_of(t[1]), t[0])):
        if r.shape_id in dropped:
            continue
        meta = {**r.meta, "layer": layer_of(r)}
        meta.update(host_meta.get(r.shape_id, {}))
        meta.update(extra_meta.get(r.shape_id, {}))
        out.append(replace(r, meta=meta))
    return out, report
