"""Sew a fragment as part of the body of its own thread it lies against
(`cfg.extra["absorb_fragments"]`, built OFF 2026-10-25).

**Why.** Over five paired hat jobs, any order of our pieces is forced into
more cuts than the professional's (#1072, `tools/sequence_pro.py`), and the
part of that which is construction is MFab's: 22 pieces no order reaches
without a cut, against his 2 (`tools/isolated_pieces.py`,
`docs/isolated-pieces-2026-10-25.md`). Every one is a white FRAGMENT of the
logo's white keyline: a sub-floor region stage 3 kept because it contrasts
with the black around it (`rescued_small_shape`), 0.3-0.7 mm wide, lying
0.0-0.2 mm from the white field the keyline belongs to, a work-grid pixel or
two of black between them. The pro sews every one of those places as part of
his white band (17 inside his band's piece, 5 joined to it within reach).

`sew_enclosed_white` (Kent ruled it ON 2026-10-25) sews that field, and the
fragments stop being isolated (22 -> 1). They are still separate shapes,
though: each is sewn as its own run loop on top of the field, and stage 7
cuts between them -- 16 of MFab's 77 trims with the field sewn, every one a
cut from fragment to fragment (`tools/inpiece_cuts.py`'s shape-to-shape).

**What this does.** After stage 5, on its planned regions: a fragment -- a
region narrower everywhere than the pro's narrowest sewn satin column
(`PRO_MIN_SWING_MM`), not lettering -- lying within one thread (`GAP_MM`) of
a BODY of the SAME thread is unioned into that body, its artwork polygon
into the body's artwork and its sewing polygon into the body's, and is not
sewn on its own. A body is a shape in its own right: not narrow, not
lettering, not itself a sub-floor shape stage 3 rescued. One pass: fragments
do not chain (Fremont's clusters of 26 rescued specks would otherwise grow a
body out of a speck). Nothing is dropped: the fragment's area is sewn, as the
body's.

After stage 5, not before: run before it (built that way first), the union
changed the white field's outline, stage 5 re-planned the black round it
(underlap, cut-backs; one black letter's holes 6 -> 4), the black fill
re-sectioned, and MFab's exposed travel rose 25.0 -> 41.3 mm on one 17.4 mm
leg over finished black fill -- gate 3 refuses that. Here every other
colour's planned polygon is exactly stage 5's.

**Where the numbers come from.**

- `PRO_MIN_SWING_MM` 0.70: the pro's narrowest sewn satin column, p01 of a
  census of every satin column in his DSTs (`tools/isolated_pieces.py
  --census`: 28 files, 2,141 columns in 868 pieces, each read as its swing
  ACROSS the column, 2026-10-25). Below it sit eight pieces at 0.60-0.66
  (Fremont's small text, one Proseal column) and one 0.44 column, a single
  taper inside a 79.8 mm2 Drone piece. Compared as our DRAWN width against
  his needle swing, which carries his pull compensation, so it absorbs fewer
  than a like-for-like width would.
- `GAP_MM` 0.4: one thread, `tools/sequence_pro.THREAD_MM` -- the reader's
  own "touching": a gap one thread wide is covered by the thread beside it.

Off (the default) this returns its input untouched, and the plan is
byte-identical. Not a physical constant: both numbers are read from files
and geometry, and absorbing a piece is LAYOUT, judged from renders (Kent
2026-10-22).
"""
from __future__ import annotations

import dataclasses

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

KEY = "absorb_fragments"
PRO_MIN_SWING_MM = 0.70
GAP_MM = 0.4

#: a region carrying any of these is a letter (or a mark stage 3 kept on
#: purpose), never a fragment and never a body to absorb into
_KEEP_KEYS = ("text_candidate", "text_cluster_id", "lettering_group", "word_id", "bean_letter",
              "small_text_stray", "detail_spokes")


def enabled(cfg) -> bool:
    return bool((getattr(cfg, "extra", None) or {}).get(KEY))


def _narrow(poly, width: float) -> bool:
    """Narrower than `width` everywhere: nothing survives an inset of half."""
    return poly.buffer(-width / 2.0).is_empty


def _kept(r) -> bool:
    m = r.meta or {}
    return any(m.get(k) for k in _KEEP_KEYS)


def _join(body: Polygon, frag):
    """One polygon `body` with `frag` unioned in, joined across the gap by
    the lens of points within half of `GAP_MM` of BOTH -- every stretch of a
    sliver lying within one thread of the body is joined, not only its
    nearest point, and nothing else of the body's outline moves. Specks of
    the lens touching neither shape are dropped. None if `frag` is still
    apart."""
    g = GAP_MM / 2.0 + 0.02
    bridge = frag.buffer(g).intersection(body.buffer(g))
    merged = unary_union([body, frag, bridge]).buffer(0)
    if not isinstance(merged, Polygon):
        parts = [p for p in getattr(merged, "geoms", []) if p.intersects(body) or p.intersects(frag)]
        if len(parts) != 1:
            return None
        merged = parts[0]
    # a pocket the join closed -- a hair of the colour beneath, walled in by
    # the fragment, the lens and the body, narrower than anything the pro
    # sews -- is not a hole of the body. A hole the body already had is kept
    # as it was; any other -- a new pocket, or a hair a bridge cut off one of
    # the body's own holes -- only if it is wide enough to sew.
    own = [Polygon(h) for h in body.interiors]
    keep = []
    for h in merged.interiors:
        hp = Polygon(h)
        if any(hp.equals(o) for o in own) or not _narrow(hp, PRO_MIN_SWING_MM):
            keep.append(h)
    return Polygon(merged.exterior, keep)


def _merge(body, frag):
    """`_join` into the part of `body` nearest `frag` (a body stage 5 left
    in parts keeps its other parts as they were). None if it cannot join."""
    parts = list(body.geoms) if isinstance(body, MultiPolygon) else [body]
    k = min(range(len(parts)), key=lambda i: parts[i].distance(frag))
    joined = _join(parts[k], frag)
    if joined is None:
        return None
    rest = parts[:k] + parts[k + 1:]
    return MultiPolygon([joined, *rest]) if rest else joined


def absorb(planned: list, cfg) -> list:
    """`planned` (stage 5's `PlannedRegion`s) with every fragment unioned
    into its body; the list is new, the entries it replaces are copies, and
    no other entry changes. Off: `planned` itself."""
    if not enabled(cfg):
        return planned
    regs = [p.region for p in planned]
    frags = [i for i, r in enumerate(regs) if not _kept(r) and _narrow(r.polygon, PRO_MIN_SWING_MM)]
    fset = set(frags)
    bodies = [i for i, r in enumerate(regs) if i not in fset and not _kept(r)
              and not (r.meta or {}).get("rescued_small_shape")]
    out = list(planned)
    for fi in frags:
        f = regs[fi]
        best = None
        for bi in bodies:
            b = regs[bi]
            if b.thread_index != f.thread_index or b.area_mm2 <= f.area_mm2:
                continue
            d = b.polygon.distance(f.polygon)
            if d <= GAP_MM and (best is None or d < best[0]):
                best = (d, bi)
        if best is None:
            continue
        b, fp = out[best[1]], planned[fi]
        art = _merge(b.region.polygon, f.polygon)
        sewn = _merge(b.polygon, fp.polygon)
        if art is None or sewn is None:
            continue
        visible = None
        if b.visible is not None and fp.visible is not None:
            added = sewn.difference(unary_union([b.polygon, fp.polygon]))
            visible = unary_union([b.visible, fp.visible, added])
        region = dataclasses.replace(
            b.region, polygon=art, area_mm2=float(art.area),
            meta={**b.region.meta,
                  "absorbed_fragments": [*b.region.meta.get("absorbed_fragments", []), f.shape_id]})
        out[best[1]] = dataclasses.replace(b, region=region, polygon=sewn, visible=visible)
        out[fi] = None
    return [p for p in out if p is not None]
