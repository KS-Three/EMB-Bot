"""`cfg.keyline_under_face` (built OFF 2026-11-19): a dark keyline layer sews under the faces it borders.

Golden Tee's GOLF and GT: the art's burnt-orange keyline is 0.37-0.48 mm; it sews as satin at
about 1.2-1.3 mm (satin floor + pull, ROADMAP gate 1, untouched here) and, because
`borders_last_layers` puts every satin-dominated layer after the fills, it sews LAST, over the
gold and pumpkin faces it fences, so its excess caps them. Moved before those faces, stage 5
plans the overlap against the order actually sewn and the face covers the keyline's inner
excess: the red shows at about the art's width. Order only; no width, floor, pull or cover value.

A layer qualifies when (area-weighted, stitched regions) at least `LAYER_BAND_FRAC` of it is bands
(mean width 2A/P <= `BAND_MAX_MM`) and its thread is dark (L* <= `DARK_L_MAX`). It moves to just
before the earliest layer that holds a FACE (2A/P > `BAND_MAX_MM`, lighter than the keyline)
within `TOUCH_MM` of one of its bands, when that layer sews after it.
"""
from __future__ import annotations

BAND_MAX_MM = 0.8       # `stage4_vectorize.CAP_MERGED_BAND_MAX_MM`, the same band rule
DARK_L_MAX = 40.0       # burnt orange (155,48,28) is 33; the cap rule's 35 sat just under it
LAYER_BAND_FRAC = 0.8
TOUCH_MM = 0.3


def _width(r) -> float:
    per = r.polygon.length
    return 2.0 * r.polygon.area / per if per > 0 else 0.0


def keylines_under_face(regions, thread_indices: list[int], chart) -> list[int]:
    """Mutates `meta["layer"]`, returns `thread_indices` permuted to match (the
    `borders_last_layers` contract); no qualifying layer: the input, untouched."""
    from shapely.strtree import STRtree
    if not regions:
        return list(thread_indices)
    layers = sorted({r.meta["layer"] for r in regions})
    members = {L: [r for r in regions if r.meta["layer"] == L] for L in layers}
    sewn = {L: [r for r in m if r.meta.get("stitched", True)] or m for L, m in members.items()}
    lum = {L: float(chart.lab[thread_indices[L]][0]) for L in layers}

    def is_key(L: int) -> bool:
        b = sewn[L]
        tot = sum(r.area_mm2 for r in b)
        if tot <= 0 or lum[L] > DARK_L_MAX:
            return False
        return sum(r.area_mm2 for r in b if _width(r) <= BAND_MAX_MM) >= LAYER_BAND_FRAC * tot

    darkest = min(lum.values())
    # the design's darkest ink is the drawn outline itself (Golden Tee's black swoosh and tee
    # edge): a face over it erased the thin black arc, so it stays where it was
    keys = [L for L in layers if is_key(L) and lum[L] > darkest + 1e-6]
    if not keys:
        return list(thread_indices)
    faces = [r for r in regions if _width(r) > BAND_MAX_MM and r.meta.get("stitched", True)]
    if not faces:
        return list(thread_indices)
    tree = STRtree([f.polygon for f in faces])
    order = list(layers)
    moved = False
    for K in keys:
        best = None
        for r in sewn[K]:
            if _width(r) > BAND_MAX_MM:
                continue
            for j in tree.query(r.polygon.buffer(TOUCH_MM)):
                f = faces[int(j)]
                F = f.meta["layer"]
                if F == K or lum[F] <= lum[K] or F in keys:
                    continue
                if r.polygon.distance(f.polygon) > TOUCH_MM:
                    continue
                if order.index(F) > order.index(K):
                    continue            # already sews before this face: it is under it
                if best is None or order.index(F) < order.index(best):
                    best = F
        if best is not None:
            order.remove(K)
            order.insert(order.index(best), K)
            moved = True
    if not moved:
        return list(thread_indices)
    remap = {old: new for new, old in enumerate(order)}
    for r in regions:
        r.meta["layer"] = remap[r.meta["layer"]]
    regions.sort(key=lambda r: (r.meta["layer"], -r.area_mm2, r.shape_id))
    return [thread_indices[L] for L in order]
