"""Region model, initial shape IDs, and ID carry-forward across regenerations.

The contract needs a shape identity that survives a stateless round-trip:
EMB-Bot sends `deleted_shape_ids` back with a re-digitize call, and those must
still name the same shapes. Two mechanisms, because one is not enough:

1. `assign_shape_ids` — deterministic content-derived label for a first
   generation. Same input, same IDs, every run.
2. `match_shape_ids` — carries IDs FORWARD from a previous generation by
   matching geometry (same thread, nearest centroid within a tolerance).

Why both: any hash of quantized geometry flips when a value lands on a bucket
boundary. Measured during step-1 development — a 0.95% area difference moved a
region across a 5% area bucket and changed its ID. Boundary refinement (the
SAM segmenter arriving in step 2) moves every centroid and area slightly, so
hashing alone would churn IDs exactly when stability matters most. The hash
therefore only labels NEW shapes; continuity comes from matching. Area is
deliberately absent from the hash for the same jitter reason.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from shapely.geometry import Polygon

# Two regions of the same thread whose centroids land in the same 0.5 mm
# bucket collide (deterministically suffixed); a real design does not put two
# same-color shapes concentrically at sub-mm distance.
CENTROID_BUCKET_MM = 0.5
# Carry-forward tolerance: a boundary refinement or a small parameter tweak
# moves a centroid by well under this; a genuinely different shape does not.
MATCH_TOLERANCE_MM = 2.5


@dataclass
class Region:
    shape_id: str
    polygon: Polygon          # mm, origin design-center, y-axis DOWN
    thread_index: int         # index into threads.CHART
    thread_number: str
    area_mm2: float
    source: str = "classical"  # segmenter provenance
    meta: dict = field(default_factory=dict)


def _bucket(v: float) -> float:
    return round(v / CENTROID_BUCKET_MM) * CENTROID_BUCKET_MM


def _raw_id(cx_mm: float, cy_mm: float, thread_number: str) -> str:
    key = f"{_bucket(cx_mm):.1f}:{_bucket(cy_mm):.1f}:{thread_number}".encode()
    return "S" + hashlib.blake2s(key, digest_size=4).hexdigest()


def assign_shape_ids(regions: list[Region]) -> None:
    """Set a deterministic shape_id on every region (in-place)."""
    order = sorted(
        range(len(regions)),
        key=lambda i: (
            regions[i].thread_number,
            round(regions[i].polygon.centroid.x, 3),
            round(regions[i].polygon.centroid.y, 3),
        ),
    )
    seen: dict[str, int] = {}
    for i in order:
        r = regions[i]
        c = r.polygon.centroid
        base = _raw_id(c.x, c.y, r.thread_number)
        n = seen.get(base, 0) + 1
        seen[base] = n
        r.shape_id = base if n == 1 else f"{base}-{n}"


def match_shape_ids(
    previous: list[Region],
    current: list[Region],
    tolerance_mm: float = MATCH_TOLERANCE_MM,
) -> dict[str, str]:
    """Carry IDs forward from `previous` onto `current` (mutates current).

    Greedy nearest-centroid matching among same-thread candidates, closest
    pairs first, each previous ID claimed at most once. Unmatched current
    regions keep whatever `assign_shape_ids` gave them. Returns the
    {new_id_before: carried_id} map for callers that need to translate
    their own stored references.
    """
    pairs: list[tuple[float, int, int]] = []
    for pi, pr in enumerate(previous):
        pc = pr.polygon.centroid
        for ci, cr in enumerate(current):
            if cr.thread_number != pr.thread_number:
                continue
            cc = cr.polygon.centroid
            d = ((pc.x - cc.x) ** 2 + (pc.y - cc.y) ** 2) ** 0.5
            if d <= tolerance_mm:
                pairs.append((d, pi, ci))
    # Deterministic: distance, then previous order, then current order.
    pairs.sort(key=lambda t: (t[0], t[1], t[2]))

    used_prev: set[int] = set()
    used_cur: set[int] = set()
    remap: dict[str, str] = {}
    for d, pi, ci in pairs:
        if pi in used_prev or ci in used_cur:
            continue
        used_prev.add(pi)
        used_cur.add(ci)
        old = current[ci].shape_id
        current[ci].shape_id = previous[pi].shape_id
        if old != previous[pi].shape_id:
            remap[old] = previous[pi].shape_id
        # Operator intent rides the identity, not just the label. Stage 4
        # rebuilds every Region's meta from scratch each generation, so a
        # review-screen decision stored there (today: the per-shape border
        # override) evaporates on re-digitize unless the match carries it —
        # which is exactly what the config docstring promises. Pipeline facts
        # (layer) stay the current generation's own.
        for key in ("border",):
            if key in previous[pi].meta and key not in current[ci].meta:
                current[ci].meta[key] = previous[pi].meta[key]
    return remap
