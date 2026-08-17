"""Region model, shape IDs and their carry-forward, and the review-screen
edits that ride them (the shape-layers contract v1).

The contract needs a shape identity that survives a stateless round-trip:
EMB-Bot sends `deleted_shape_ids` and `shape_overrides` back with a
re-digitize call, and those must still name the same shapes —
`apply_shape_edits` below is where that round-trip lands. Two identity
mechanisms exist:

1. `assign_shape_ids` — deterministic content-derived label from bucketed
   centroid plus thread number. Same input, same IDs, every run. **This is the
   one the product actually runs, and the only thing carrying edits forward
   today**: because the id is derived from content rather than remembered,
   re-digitizing the same art re-derives the same id, and a resent
   `shape_overrides` keyed by it lands on the same shape by plain id match.
2. `match_shape_ids` — carries IDs FORWARD from a previous generation by
   matching geometry (same thread, nearest centroid within a tolerance).
   **NOT WIRED: it has no production caller** (see its own docstring). Kept
   because it works and is tested, but nothing in `pipeline.run_stages` calls
   it, so do not reason about carry-forward as though it runs.

**Consequence, and the reason this was written down on 2026-08-17:** anything
that changes how `assign_shape_ids` derives an id changes carry-forward
behaviour directly, with no matching pass to absorb it. Comments across this
codebase used to name `match_shape_ids` as the mechanism — right about the
behaviour, wrong about what produces it, which is the combination that gets a
future optimisation pass into trouble.

Why the design has both: any hash of quantized geometry flips when a value lands
on a bucket boundary. Measured during step-1 development — a 0.95% area
difference moved a region across a 5% area bucket and changed its ID. Boundary
refinement (the SAM segmenter arriving in step 2) moves every centroid and area
slightly, so hashing alone would churn IDs exactly when stability matters most.
Matching was the intended continuity mechanism for that case; it was never
wired, and bucketing plus the deliberate absence of area from the hash has
carried the product so far.

A third case, deliberately NOT routed through either mechanism above: shape
identity edits (contract v1.5, `apply_shape_merges` / `apply_shape_splits`,
below). Merge and split change the SET of shapes, not one shape's geometry or
attributes, so "carry the old id forward" has no answer — a merged shape has
two ORIGINS, a split shape has one origin and two RESULTS. Both mechanisms
above exist to keep ONE shape's identity stable across a stateless re-digitize
of the SAME source image; they say nothing about a user *deliberately*
replacing a shape's identity, which is what merge/split are. So: brand new,
deterministic ids, hashed from the OPERATION's own inputs (source ids, or
source id + cut line) rather than from geometry — stable across a resubmit of
the identical merge/split request (so the cache and a repeat click behave),
but never confused with an `assign_shape_ids` or `match_shape_ids` output
(distinct prefixes, see `_merge_shape_id`/`_split_shape_ids` below).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from shapely.geometry import LineString, Polygon
from shapely.ops import split as shapely_split
from shapely.ops import unary_union
from shapely.validation import explain_validity

from . import machine
from .warnings_codes import (
    SHAPE_EDIT_UNKNOWN_ID,
    SHAPE_SPLIT_BY_USER,
    SHAPES_DELETED_BY_USER,
    SHAPES_MERGED_BY_USER,
    warn,
)

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

    **NO PRODUCTION CALLER — confirmed 2026-08-17 by grep over `digitizer_core`,
    `digitizer_service`, `app/src` and `src`.** The only callers are
    `tests/test_border.py`, `tests/test_pipeline.py` and
    `tests/test_shape_overrides.py`. `pipeline.run_stages` does not call it.
    Carry-forward in the shipped product comes from `assign_shape_ids` deriving
    the same id from the same content, so a resent `shape_overrides` matches by
    plain id — see the module docstring. Kept rather than deleted (Kent's call,
    2026-08-17) because the tolerance matching works, is tested, and has no
    replacement if boundary edits ever need it; but if you are reading this
    while changing how ids are derived, THIS function is not what protects you.

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
        # contract's per-shape tier, fill angle, within-layer sew order,
        # underlay style and hand-edited boundary alike. Pipeline facts
        # (layer) stay the current generation's own. `boundary_override`
        # carries only the record of the edit (`Region.meta`); nothing here
        # re-applies it to `current[ci].polygon` — the same stateless
        # contract as every other key: a caller resends `shape_overrides`
        # keyed by the stable content-derived id every request, and
        # `apply_shape_edits` is what actually replaces the geometry.
        for key in ("border", "applique", "tier", "fill_angle_deg",
                    "sew_order", "underlay_style", "boundary_override"):
            if key in previous[pi].meta and key not in current[ci].meta:
                current[ci].meta[key] = previous[pi].meta[key]
    return remap


# --- Review-screen shape edits (the shape-layers contract v1) ---------------

# "sketch" (contract v1.3, photo plan row 12) forces the sparse mono
# sketch rendering (stage6_sketch) on one shape; like every tonal tier it
# needs source pixels, which pipeline.run_stages carries whenever an
# override requests it, and it sews tatami when they are absent anyway.
# "streamline" (contract v1.6, Ember-research backlog item) forces the
# evenly-spaced streamline thread-paint tier (stage6_streamline) on one
# shape, same source-pixels-or-tatami-fallback contract as "sketch" — the
# per-shape form of a technique that used to be design-wide (or photo-
# pipeline) only. See stage7_sequence.stitch_one's streamline branch for
# the direction-field reasoning (raster structure tensor with a house-angle
# fallback, not a shape-geometry-derived field).
# "crosshatch" forces the two-pass angled tatami fill (stage6_fill.
# _crosshatch_fill_paths) on one shape — the per-shape form of a technique
# also reachable design-wide via fill_technique, mirroring "streamline"'s
# same dual reach. Unlike "streamline"/"sketch" it needs no source pixels
# (purely geometric), so it carries no raster-plumbing opt-in cost and
# falls back to plain tatami only when the shape itself is too thin, never
# for lack of pixels. See stage7_sequence.stitch_one's crosshatch branch.
# "wave"/"chevron"/"brick" force one of three more purely-geometric fill
# variants (stage6_fill._wave_row_points / _chevron_row_points /
# _brick_row_points) on one shape — the same per-shape reach "crosshatch"
# has above, each swapping only how ONE row's interior points get placed
# rather than adding a new pass, so none of them need source pixels either.
# See stage7_sequence.stitch_one's wave/chevron/brick branches, positioned
# the same way as its crosshatch branch.
_TIER_VALUES = {"auto", "satin", "fill", "run", "sketch", "streamline", "crosshatch",
                "wave", "chevron", "brick"}
_BORDER_VALUES = {"off", "auto", "bean"}
# fabrics.py's own vocabulary, verbatim (mirrored in digitizer_service.app's
# copy, which 400s the wire before this ever raises).
_UNDERLAY_VALUES = {"none", "edge_run", "center_run", "edge_zigzag", "edge_lattice",
                    "double_lattice", "zigzag"}

# `boundary_override` (contract v1.4): a hand-edited polygon replacing a
# shape's exterior ring outright, holes carried over unchanged from the
# shape's own current geometry. Higher risk than every other key here — a
# bad polygon can crash or corrupt stage 5 onward — so it gets the widest
# defensive check of the family. Mirrored (same bounds) in
# `digitizer_service.app`'s copy, which 400s the wire before this ever
# raises; this copy is the defense in depth for any other caller.
_MIN_BOUNDARY_POINTS = 3
_MAX_BOUNDARY_POINTS = 500


def _dedupe_ring(points: list) -> list:
    """Drop consecutive duplicate points, including an explicit closing
    point that repeats the first.

    `outline_mm` in the review payload is shapely's own `exterior.coords`,
    which always repeats the first point as the last — the natural shape for
    a client to hand back after editing it. A hand-rolled caller may instead
    send an open ring. Normalizing here means point-count and shape checks
    below see one canonical form regardless of which convention arrived.
    """
    out = []
    for pt in points:
        if out and out[-1] == pt:
            continue
        out.append(pt)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


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
    survivor's id, and a resent override still names the same shape it named
    last generation.

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

        if ov.get("sew_order") is not None:
            so = ov["sew_order"]
            if not isinstance(so, int) or isinstance(so, bool) or so < 0:
                raise ValueError(
                    f"shape_overrides[{sid!r}].sew_order {ov['sew_order']!r} "
                    "must be a non-negative integer"
                )
            r.meta["sew_order"] = so

        if ov.get("underlay_style") is not None:
            u = str(ov["underlay_style"]).lower()
            if u not in _UNDERLAY_VALUES:
                raise ValueError(
                    f"shape_overrides[{sid!r}].underlay_style {ov['underlay_style']!r} "
                    f"is not one of {sorted(_UNDERLAY_VALUES)}"
                )
            r.meta["underlay_style"] = u

        if ov.get("boundary_override") is not None:
            raw = ov["boundary_override"]
            if not isinstance(raw, (list, tuple)):
                raise ValueError(
                    f"shape_overrides[{sid!r}].boundary_override must be a "
                    "list of [x, y] points"
                )
            pts = _dedupe_ring(list(raw))
            if not _MIN_BOUNDARY_POINTS <= len(pts) <= _MAX_BOUNDARY_POINTS:
                raise ValueError(
                    f"shape_overrides[{sid!r}].boundary_override must have "
                    f"{_MIN_BOUNDARY_POINTS}..{_MAX_BOUNDARY_POINTS} distinct "
                    f"points (got {len(pts)})"
                )
            coords: list[tuple[float, float]] = []
            for pt in pts:
                if (not isinstance(pt, (list, tuple)) or len(pt) != 2
                        or any(isinstance(c, bool) or not isinstance(c, (int, float))
                               for c in pt)
                        or any(not math.isfinite(float(c)) for c in pt)):
                    raise ValueError(
                        f"shape_overrides[{sid!r}].boundary_override points "
                        "must be [x, y] pairs of finite numbers"
                    )
                coords.append((float(pt[0]), float(pt[1])))

            # Holes ride along unchanged — boundary editing is exterior-ring
            # only (contract v1.4 scope), never the shape's interior rings.
            holes = [list(hole.coords) for hole in r.polygon.interiors]
            try:
                new_poly = Polygon(coords, holes)
            except Exception as exc:  # a malformed ring shapely itself refuses
                raise ValueError(
                    f"shape_overrides[{sid!r}].boundary_override does not "
                    f"form a polygon: {exc}"
                ) from exc

            if not new_poly.is_valid or new_poly.is_empty:
                raise ValueError(
                    f"shape_overrides[{sid!r}].boundary_override is not a "
                    f"valid simple polygon ({explain_validity(new_poly)}) — "
                    "check for self-intersections or a hole poking outside "
                    "the new outline"
                )
            # Same sewability floor stage 4 already holds every auto-
            # digitized region to (see stage4_vectorize's run-tier rescue):
            # a loop the bean run can close, on a shape at least the
            # thread's own visual weight. A hand edit gets no free pass.
            if (new_poly.area < machine.RUN_MIN_AREA_MM2
                    or new_poly.exterior.length < machine.RUN_MIN_LOOP_MM):
                raise ValueError(
                    f"shape_overrides[{sid!r}].boundary_override is too "
                    f"small to sew ({new_poly.area:.4f} mm², floor "
                    f"{machine.RUN_MIN_AREA_MM2} mm²; perimeter "
                    f"{new_poly.exterior.length:.4f} mm, floor "
                    f"{machine.RUN_MIN_LOOP_MM} mm)"
                )
            r.polygon = new_poly
            r.area_mm2 = new_poly.area
            r.meta["boundary_override"] = coords

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


# --- Shape identity edits (contract v1.5): merge and split -------------------
#
# The other half of the original shape-recognition gap MASTER_SCOPE.md area 5
# used to flag as fully open: `boundary_override` (v1.4, above) reshapes ONE
# shape's outline; this pair changes the SET of shapes outright. Both mint
# brand NEW ids rather than trying to carry an old one forward — see the
# module docstring for why `assign_shape_ids`/`match_shape_ids` are the wrong
# tool here (their stability contract is about one shape surviving a
# stateless re-digitize of the SAME source image, not about a user
# *deliberately* replacing a shape's identity).
#
# v1 scope, deliberately narrow — documented here rather than silently
# missing, matching this file's "still open" convention:
#   - merge requires every source shape to already share one thread_number
#     (no cross-color merge — which color would the result take? a real
#     product question, deferred, not an accident) and none of them may have
#     a hole (shapely's own union handles holes correctly; the deferral is a
#     PRODUCT scope choice — what a merged shape's holes mean when two
#     different shapes' holes overlap or one shape's hole sits over the
#     other's fill is genuinely ambiguous, and "holeless shapes only" sidesteps
#     deciding it for a first landable slice).
#   - merge requires the union to reduce to ONE polygon: the source shapes
#     must already touch or overlap. Two disjoint shapes union to a
#     MultiPolygon, and a Region is one Polygon — rejected with a clear error
#     rather than silently keeping one piece or inventing a bridge between them.
#   - split is a single straight cut line (2 points, extended past the
#     shape's own bounding box so it fully crosses the exterior), producing
#     exactly two pieces — not an arbitrary polyline, not a multi-way cut. A
#     line that would pass through one of the shape's own holes is rejected
#     rather than silently turning the hole into a notch on both halves.
#   - Both are a warn-and-skip for a STALE id (the same "the art may have
#     changed under the edit" reasoning `apply_shape_edits` already uses for
#     `deleted_shape_ids`/`shape_overrides`) but a `ValueError` for a
#     GEOMETRICALLY bad request (mixed threads, a present hole, a
#     non-adjacent merge, an uncrossing or hole-crossing split line, or a
#     resulting piece under the sewability floor) — the same "stale warns,
#     bad geometry raises" split `boundary_override` already draws.

_MERGE_MIN_SHAPES = 2


def _merge_shape_id(source_ids: list, salt: int = 0) -> str:
    """Deterministic id for the shape a merge produces — hashed from the
    OPERATION's inputs (which shapes, sorted so argument order never matters),
    not from geometry. Stable across an identical resubmit (the job cache
    wants this, same as every other edit key); `salt` only breaks a
    same-request collision between two different merge groups (vanishingly
    unlikely at digest_size=4, handled anyway — the same defensive posture
    `assign_shape_ids` already takes with its own `-n` suffix). The "SM"
    prefix can never collide with an `assign_shape_ids` output (always
    "S" + hex) or a `_split_shape_id` output ("SP" + hex).
    """
    key = ":".join(sorted(source_ids)).encode()
    base = "SM" + hashlib.blake2s(key, digest_size=4).hexdigest()
    return base if salt == 0 else f"{base}-{salt}"


def _split_shape_id(source_id: str, line, index: int, salt: int = 0) -> str:
    """Deterministic id for one of the two shapes a split produces — hashed
    from the source id, the cut line's own endpoints, and which of the two
    pieces this is (0/1, assigned by centroid order in `apply_shape_splits`,
    never shapely's internal `split()` ordering, so it cannot flip between
    otherwise-identical runs)."""
    (x0, y0), (x1, y1) = line
    key = f"{source_id}:{x0:.4f},{y0:.4f}:{x1:.4f},{y1:.4f}:{index}".encode()
    base = "SP" + hashlib.blake2s(key, digest_size=4).hexdigest()
    return base if salt == 0 else f"{base}-{salt}"


# Per-shape styling worth carrying from a merge/split's source shape(s) onto
# the result — the same review-screen fields that survive an ordinary
# re-digitize on a stable id — MINUS two exclusions:
#   `applique` — its own piece-cutting model has identity assumptions this
#   pass did not audit; left untouched rather than guessed at.
#   `boundary_override` — that key describes a HAND-EDITED SHELL for a
#   SPECIFIC old polygon. The merge/split result is a different polygon by
#   construction, so carrying the key forward would silently reapply a stale
#   hand edit to the wrong shape — it is dropped, never migrated.
_CARRIED_META_KEYS = ("border", "tier", "fill_angle_deg", "sew_order", "underlay_style")


def _seed_meta(source: Region) -> dict:
    return {k: source.meta[k] for k in _CARRIED_META_KEYS if k in source.meta}


def _check_sewable(poly: Polygon, where: str) -> None:
    """The same sewability floor `boundary_override` holds a hand edit to —
    a valid, simple polygon at least the thread's own visual weight."""
    if not poly.is_valid or poly.is_empty:
        raise ValueError(f"{where} is not a valid simple polygon ({explain_validity(poly)})")
    if poly.area < machine.RUN_MIN_AREA_MM2 or poly.exterior.length < machine.RUN_MIN_LOOP_MM:
        raise ValueError(
            f"{where} is too small to sew ({poly.area:.4f} mm², floor "
            f"{machine.RUN_MIN_AREA_MM2} mm²; perimeter {poly.exterior.length:.4f} mm, "
            f"floor {machine.RUN_MIN_LOOP_MM} mm)"
        )


def apply_shape_merges(
    regions: list[Region],
    merge_groups: list,
) -> tuple[list[Region], list[dict]]:
    """Union 2+ same-thread shapes into one new shape (contract v1.5).

    `merge_groups` is `[[shape_id, shape_id, ...], ...]` — each inner list at
    least `_MERGE_MIN_SHAPES` distinct ids to combine into one new Region.

    Runs BEFORE `apply_shape_edits` (right after stage 4 assigns ids), on the
    same reasoning that function's docstring already gives for running after
    `assign_shape_ids`: ids are consumed and minted against the FULL, stable
    generation, never a partially-edited one. A `shape_overrides` entry keyed
    on one of the merge's SOURCE ids simply goes unmatched afterwards (the
    ordinary `SHAPE_EDIT_UNKNOWN_ID` path) — the same "no free second write
    to a consumed id" posture a deletion already has.

    Returns (possibly-replaced regions list, warnings). See the module-level
    comment above for the full v1 scope and the warn-vs-raise split.
    """
    warnings: list[dict] = []
    if not merge_groups:
        return regions, warnings

    by_id = {r.shape_id: r for r in regions}
    new_regions: list[Region] = []
    consumed: set = set()
    merged_summaries: list[dict] = []
    seen_ids: set = set()

    for group in merge_groups:
        ids = list(dict.fromkeys(group))  # de-duplicate, preserve nothing else
        missing = [sid for sid in ids if sid not in by_id or sid in consumed]
        if missing:
            warnings.append(
                warn(
                    SHAPE_EDIT_UNKNOWN_ID,
                    f"A merge referencing {len(missing)} shape id"
                    f"{'s' if len(missing) != 1 else ''} that no longer "
                    "match this artwork was skipped.",
                    count=len(missing),
                    ids=sorted(missing),
                )
            )
            continue
        if len(ids) < _MERGE_MIN_SHAPES:
            raise ValueError(
                f"merge_shape_ids group {ids!r} needs at least "
                f"{_MERGE_MIN_SHAPES} distinct shapes"
            )

        sources = [by_id[sid] for sid in ids]
        threads = {r.thread_number for r in sources}
        if len(threads) != 1:
            raise ValueError(
                f"merge_shape_ids group {ids!r} mixes threads ({sorted(threads)}) "
                "— v1 only merges shapes in the same color layer"
            )
        with_holes = [sid for sid, r in zip(ids, sources) if r.polygon.interiors]
        if with_holes:
            raise ValueError(
                f"merge_shape_ids group {ids!r} includes shape(s) with a hole "
                f"({sorted(with_holes)}) — v1 only merges shapes without holes"
            )

        union = unary_union([r.polygon for r in sources])
        if union.geom_type != "Polygon":
            raise ValueError(
                f"merge_shape_ids group {ids!r} does not touch or overlap — "
                "the shapes must be adjacent to merge into one shape"
            )
        _check_sewable(union, f"merge_shape_ids group {ids!r}")

        primary = max(sources, key=lambda r: r.area_mm2)
        base_id = _merge_shape_id(ids)
        salt = 0
        new_id = base_id
        while new_id in seen_ids or new_id in by_id:
            salt += 1
            new_id = _merge_shape_id(ids, salt)
        seen_ids.add(new_id)

        meta = {"layer": primary.meta.get("layer", 0)}
        meta.update(_seed_meta(primary))
        new_regions.append(
            Region(
                shape_id=new_id,
                polygon=union,
                thread_index=primary.thread_index,
                thread_number=primary.thread_number,
                area_mm2=union.area,
                source=primary.source,
                meta=meta,
            )
        )
        consumed.update(ids)
        merged_summaries.append({"from": sorted(ids), "into": new_id})

    if merged_summaries:
        regions = [r for r in regions if r.shape_id not in consumed] + new_regions
        warnings.append(
            warn(
                SHAPES_MERGED_BY_USER,
                f"{len(merged_summaries)} merge{'s' if len(merged_summaries) != 1 else ''} "
                "combined shapes on the review screen.",
                count=len(merged_summaries),
                groups=merged_summaries,
            )
        )
    return regions, warnings


def apply_shape_splits(
    regions: list[Region],
    split_lines: dict,
) -> tuple[list[Region], list[dict]]:
    """Cut one shape into two along a straight line (contract v1.5).

    `split_lines` is `{shape_id: [[x0, y0], [x1, y1]]}` — a two-point cut line
    in the same design-center, y-down mm space `boundary_override` already
    uses. The line is extended well past the shape's own bounding box before
    cutting (shapely's `split()` requires the splitter to cross the target's
    exterior, not just graze the interior), so the caller may send exactly
    the two points a drawn line's endpoints landed on — no client-side
    extension needed.

    Same warn-vs-raise split as `apply_shape_merges` (see the module comment
    above): an unknown/stale shape id is a warning and that split is skipped;
    a geometrically bad request (a line that does not divide the shape into
    exactly two sewable pieces, or a cut that would pass through one of the
    shape's own holes) is a `ValueError`.
    """
    warnings: list[dict] = []
    if not split_lines:
        return regions, warnings

    by_id = {r.shape_id: r for r in regions}
    out = list(regions)
    split_summaries: list[dict] = []
    seen_ids: set = set()

    for sid, line in split_lines.items():
        source = by_id.get(sid)
        if source is None:
            warnings.append(
                warn(
                    SHAPE_EDIT_UNKNOWN_ID,
                    "A split referencing a shape id that no longer matches "
                    "this artwork was skipped.",
                    count=1,
                    ids=[sid],
                )
            )
            continue

        # Canonicalize the two endpoints' order (lexicographic on (x, y))
        # before anything else: the cut line the two points describe is
        # identical either way (extending symmetrically past both ends below
        # makes the clipped segment direction-independent), but the id hash
        # (`_split_shape_id`) is not — without this, submitting the same drag
        # with its two points in the opposite order would mint a DIFFERENT
        # pair of shape ids for the identical cut, which would also defeat
        # the job cache (two spellings of one edit must collapse to one key,
        # the same reasoning `digitizer_service.app`'s own canonicalization
        # gives for `deleted_shape_ids`/`merge_shape_ids`).
        line = sorted([tuple(line[0]), tuple(line[1])])
        (x0, y0), (x1, y1) = line
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-6:
            raise ValueError(f"split_shapes[{sid!r}] line has zero length")

        minx, miny, maxx, maxy = source.polygon.bounds
        diag = math.hypot(maxx - minx, maxy - miny) or 1.0
        # Extend the segment 10x the shape's own diagonal past each end so it
        # fully crosses the exterior no matter where inside the shape the
        # user's two dragged points landed.
        ux, uy = dx / length, dy / length
        ext = diag * 10.0
        cut = LineString([
            (x0 - ux * ext, y0 - uy * ext),
            (x1 + ux * ext, y1 + uy * ext),
        ])

        for hole in source.polygon.interiors:
            if cut.intersects(Polygon(hole)):
                raise ValueError(
                    f"split_shapes[{sid!r}] line crosses one of this shape's "
                    "own holes — move the cut so it does not touch a hole"
                )

        pieces_geom = shapely_split(source.polygon, cut)
        pieces = [g for g in pieces_geom.geoms if g.geom_type == "Polygon" and not g.is_empty]
        if len(pieces) != 2:
            raise ValueError(
                f"split_shapes[{sid!r}] line does not divide this shape into "
                f"exactly two pieces (got {len(pieces)}) — drag the line so it "
                "crosses the shape once, edge to edge"
            )
        for p in pieces:
            _check_sewable(p, f"split_shapes[{sid!r}] piece")

        # Deterministic piece order regardless of shapely's internal split()
        # ordering: leftmost-then-topmost centroid first.
        pieces.sort(key=lambda p: (round(p.centroid.x, 3), round(p.centroid.y, 3)))

        meta = {"layer": source.meta.get("layer", 0)}
        meta.update(_seed_meta(source))
        new_pieces: list[Region] = []
        for i, p in enumerate(pieces):
            base_id = _split_shape_id(sid, line, i)
            salt = 0
            new_id = base_id
            while new_id in seen_ids or new_id in by_id:
                salt += 1
                new_id = _split_shape_id(sid, line, i, salt)
            seen_ids.add(new_id)
            new_pieces.append(
                Region(
                    shape_id=new_id,
                    polygon=p,
                    thread_index=source.thread_index,
                    thread_number=source.thread_number,
                    area_mm2=p.area,
                    source=source.source,
                    meta=dict(meta),
                )
            )

        out = [r for r in out if r.shape_id != sid] + new_pieces
        by_id = {r.shape_id: r for r in out}
        split_summaries.append({"from": sid, "into": [r.shape_id for r in new_pieces]})

    if split_summaries:
        warnings.append(
            warn(
                SHAPE_SPLIT_BY_USER,
                f"{len(split_summaries)} shape{'s' if len(split_summaries) != 1 else ''} "
                "cut into two on the review screen.",
                count=len(split_summaries),
                groups=split_summaries,
            )
        )
    return out, warnings
