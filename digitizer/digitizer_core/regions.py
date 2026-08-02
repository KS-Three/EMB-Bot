"""Region model, shape IDs and their carry-forward, and the review-screen
edits that ride them (the shape-layers contract v1).

The contract needs a shape identity that survives a stateless round-trip:
EMB-Bot sends `deleted_shape_ids` and `shape_overrides` back with a
re-digitize call, and those must still name the same shapes —
`apply_shape_edits` below is where that round-trip lands. Two identity
mechanisms, because one is not enough:

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

from .warnings_codes import SHAPE_EDIT_UNKNOWN_ID, SHAPES_DELETED_BY_USER, warn

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
        # review-screen decision stored there evaporates on re-digitize unless
        # the match carries it — which is exactly what the config docstring
        # promises, for the border, the appliqué flag, and the shape-layers
        # contract's per-shape tier and fill angle alike. Pipeline facts
        # (layer) stay the current generation's own.
        for key in ("border", "applique", "tier", "fill_angle_deg"):
            if key in previous[pi].meta and key not in current[ci].meta:
                current[ci].meta[key] = previous[pi].meta[key]
    return remap


# --- Review-screen shape edits (the shape-layers contract v1) ---------------

_TIER_VALUES = {"auto", "satin", "fill", "run"}
_BORDER_VALUES = {"off", "auto", "bean"}


def apply_shape_edits(
    regions: list[Region],
    thread_indices: list[int],
    deleted_shape_ids: list[str],
    shape_overrides: dict,
    chart,
) -> tuple[list[Region], list[int], list[dict]]:
    """Deletions and per-shape overrides, applied right after stage 4.

    -> (surviving regions, thread indices incl. recolor targets, warnings).

    Runs BEFORE `compact_layers` on purpose, twice over:
    - deletion emptying a thread's last shape must drop that thread from the
      palette, which is exactly the job `compact_layers` already does;
    - a recolor to a thread nothing else sews appends that thread here, and
      compaction then numbers the layers as it always has.

    And it runs AFTER `assign_shape_ids` (stage 4's last act) so the ids were
    assigned against the FULL generation: deleting one shape can never churn a
    survivor's id, and `match_shape_ids` against a previous generation still
    sees everything the artwork produced.

    An id that matches nothing — deleted or overridden — is a warning, not an
    error: the art may have changed under the edit, and a review edit that no
    longer applies is news for the panel, not a reason to fail the job.
    """
    warnings: list[dict] = []
    if not deleted_shape_ids and not shape_overrides:
        return regions, thread_indices, warnings

    thread_indices = [int(t) for t in thread_indices]
    known = {r.shape_id for r in regions}

    removed = sorted({s for s in deleted_shape_ids if s in known})
    unknown = {s for s in deleted_shape_ids if s not in known}
    if removed:
        gone = set(removed)
        regions = [r for r in regions if r.shape_id not in gone]
        warnings.append(
            warn(
                SHAPES_DELETED_BY_USER,
                f"{len(removed)} shape{'s' if len(removed) != 1 else ''} "
                "hidden by you on the review screen.",
                count=len(removed),
                ids=removed,
            )
        )

    unknown |= {s for s in shape_overrides if s not in known}
    by_id = {r.shape_id: r for r in regions}
    # Sorted iteration: when two recolors both introduce new threads, the
    # palette order must not depend on dict insertion order.
    for sid in sorted(shape_overrides):
        r = by_id.get(sid)
        if r is None:
            continue  # unknown (warned) or deleted (already reported)
        ov = shape_overrides[sid] or {}

        if ov.get("thread_index") is not None:
            t = int(ov["thread_index"])
            if not 0 <= t < len(chart):
                raise ValueError(
                    f"shape_overrides[{sid!r}].thread_index {t} is outside "
                    f"the chart (0..{len(chart) - 1})"
                )
            r.thread_index = t
            r.thread_number = chart[t].number
            # The recolor changes which color BLOCK the shape sews in, and
            # layer is how stage 5 groups blocks — so the layer moves with it.
            if t in thread_indices:
                r.meta["layer"] = thread_indices.index(t)
            else:
                thread_indices.append(t)
                r.meta["layer"] = len(thread_indices) - 1

        if ov.get("fill_angle_deg") is not None:
            r.meta["fill_angle_deg"] = float(ov["fill_angle_deg"])

        if ov.get("tier") is not None:
            tier = str(ov["tier"]).lower()
            if tier not in _TIER_VALUES:
                raise ValueError(
                    f"shape_overrides[{sid!r}].tier {ov['tier']!r} is not one "
                    f"of {sorted(_TIER_VALUES)}"
                )
            if tier != "auto":
                r.meta["tier"] = tier

        if ov.get("border") is not None:
            b = ov["border"]
            if not isinstance(b, bool):
                b = str(b).lower()
                if b not in _BORDER_VALUES:
                    raise ValueError(
                        f"shape_overrides[{sid!r}].border {ov['border']!r} is "
                        f"not one of {sorted(_BORDER_VALUES)}"
                    )
            r.meta["border"] = b

    if unknown:
        missing = sorted(unknown)
        warnings.append(
            warn(
                SHAPE_EDIT_UNKNOWN_ID,
                f"{len(missing)} review edit{'s' if len(missing) != 1 else ''} "
                "no longer match a shape in this artwork and were skipped.",
                count=len(missing),
                ids=missing,
            )
        )

    # Restore stage 4's stable output order: a recolor can move a shape
    # between layers, and downstream (and the review payload) rely on
    # layer-then-size ordering.
    regions.sort(key=lambda r: (r.meta["layer"], -r.area_mm2, r.shape_id))
    return regions, thread_indices, warnings


def apply_layer_overrides(regions: list[Region], shape_overrides: dict) -> None:
    """Explicit sew-order layers, applied AFTER `compact_layers` (in place).

    Deliberately the one override that waits for compaction: meta["layer"] is
    both the palette index and the sew-order key, and moving a shape into
    another layer before compaction could empty its thread's own layer and
    drop a cone the design still uses from the color list. Applied here it
    only perturbs sew grouping — stage 5 sorts whatever layer numbers it is
    given, and stage 7 splits a mixed layer into per-thread blocks.
    """
    if not shape_overrides:
        return
    touched = False
    for r in regions:
        ov = shape_overrides.get(r.shape_id)
        if ov and ov.get("layer") is not None:
            r.meta["layer"] = int(ov["layer"])
            touched = True
    if touched:
        regions.sort(key=lambda r: (r.meta["layer"], -r.area_mm2, r.shape_id))
