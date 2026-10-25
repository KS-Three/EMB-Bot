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


def plan(regions, unsewn=()):
    """-> [(ring, host, outline, merged ids, inner shapes)] for every ring
    this reads, the biggest first; a shape serves one ring at most.

    `unsewn` are the shapes left as garment on purpose (enclosed background,
    a review `stitched: false`): the outline is cut back off them, so the
    under-fill never sews over fabric the design shows -- MFab's white
    keyline without `sew_enclosed_white`. They never count as holding a hole."""
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
                and str(r.meta.get("tier", "auto")).lower() == "auto"]
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


def apply(regions, unsewn=()):
    """`cfg.silhouette_underfill` ON: -> (regions as copies, report). The
    hosts carry `UNDERFILL_KEY` and the fill tier, merged shapes are gone,
    and each host's layer sews before its ring's and its inner colours'.
    `unsewn`: see `plan`."""
    rings = plan(regions, unsewn)
    if not rings:
        return regions, []
    host_meta: dict[str, dict] = {}
    dropped: set[str] = set()
    order = sorted({r.meta["layer"] for r in regions})
    moved = False
    report = []
    for ring, host, outline, merged, inner in rings:
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
    renum = {L: i for i, L in enumerate(order)} if moved else {L: L for L in order}
    out = []
    for i, r in sorted(enumerate(regions), key=lambda t: (renum[t[1].meta["layer"]], t[0])):
        if r.shape_id in dropped:
            continue
        meta = {**r.meta, "layer": renum[r.meta["layer"]]}
        meta.update(host_meta.get(r.shape_id, {}))
        out.append(replace(r, meta=meta))
    return out, report
