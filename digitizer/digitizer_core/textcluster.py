"""Text-cluster detection — "does this group of rescued shapes look like a
word" — per `docs/superpowers/specs/2026-08-05-text-cluster-detection-design.md`
section 3.2.

Mirrors `stage4_vectorize.tag_enclosed_background`'s shape exactly: a
post-vectorization pass that mutates `Region.meta` in place, returns nothing,
and fails open on anything it isn't confident about. `stage3_segment
.resolve_small_regions` already rescues an isolated small shape from being
dropped (`rescued_small_shape` in `Region.meta`, Step 1 of this feature) but
treats every glyph as an independent noisy blob. This pass is the next, still
purely geometric, question: do several of those blobs, together, look like a
line of lettering rather than an arbitrary handful of small shapes?

No OCR, no character recognition — only position, size, and stroke width,
all read off `region.polygon` via `shapefield.build_shape_field`. This is a
THIRD independent consumer of that module (alongside `stage6_satin` and the
`shape_lens.py` instrument) — see `shapefield.py`'s own module docstring for
why those two stay independent of each other; this one is new, not a merge
of either.

`text_cluster_stroke_mm` is deliberately the raw `dist/scale` value (a
HALF-width / radius at skeletal pixels, not `shape_lens.DTStats`'s doubled
`mean_width_mm`) because `regularize_text_clusters` (Step 5, below) uses this
exact number as a skeleton-buffer RADIUS to regularize a cluster's stroke
width — buffering by a full width would double it.

## Regularization (Step 5, design doc section 3.3)

`regularize_text_clusters` redraws every tagged member's `region.polygon` as
a fixed-radius buffer around its OWN skeleton, sized to the cluster's shared
target half-width (`text_cluster_stroke_mm`, the cluster median, already
computed above). A rescued letter's apparent stroke weight is otherwise
whatever noisy width vectorization happened to leave it at; this makes every
member of a detected word read at one consistent weight, the same way real
satin lettering does, without introducing a font or OCR.

Turning a raster skeleton into a shapely line to buffer is genuine
computational geometry once branch points enter the picture (a letter like
"E", "T" or "R" does not reduce to one clean path). Rather than re-deriving
that from scratch, this reuses `stage6_satin`'s own tested skeleton-to-stroke
machinery — `_skeleton_edges` (decomposes a 1-px skeleton mask into edges
between nodes, plus closed loops) and `_merge_through_junctions` (welds the
two arms at a branch node that run straight through each other, so a T's bar
is one stroke, not two trimmed halves) — the exact tool `extract_strokes`
already uses to turn a glyph's medial axis into satin rails. Every resulting
chain (there may be several per glyph, sharing endpoints at unwelded branch
nodes) is converted to a shapely `LineString` in mm space and the WHOLE
cluster-member's chain set is buffered together as one `MultiLineString` —
since chains meet exactly at shared node pixels, their buffers overlap there
and the union comes back as one connected `Polygon` (verified against the
real benchmark fixture below, not assumed).

This module does NOT narrow to non-branching skeletons only: on
`testdata/photo/enthusiast_logo.png`'s real 14-member subline cluster, 10 of
14 members have a branching (multi-chain) skeleton after
`_merge_through_junctions`, and all 14 buffer into a single valid, sewable
`Polygon` — narrowing to non-branching-only would have skipped most of the
real fixture's own members. The fail-open guard below is what actually
protects against the cases that do NOT hold in general (a degenerate
skeleton with too little material to clear the sewability floor once
buffered, a buffer that returns more than one disconnected piece, or an
invalid result) rather than a scope restriction decided in advance.

## Selective regularization (2026-08-06 fix — Kent's real-render review)

Rendering the benchmark fixture's actual stitched output (`debugviz.stage6`,
not just checking that `regularize_text_clusters` runs without raising)
surfaced a real defect the plan above did not anticipate: buffering EVERY
tagged member unconditionally, even one whose own geometry was already
fine, actively made the subline WORSE, not better. Measured directly on
`enthusiast_logo.png`'s 14-member subline cluster at 90 mm (the same
fixture the docstring above already cites):

- **Most members did not need correction.** Each member's own
  `_stroke_stats_mm` value, measured BEFORE regularization, sits within
  9.5% coefficient-of-variation of the cluster median — 13 of 14 members
  within +-11%, one real outlier (a narrow "I"-like glyph) at +30%. This is
  nowhere near the design doc's motivating scenario (independently noisy
  glyphs genuinely differing in weight); it is a cluster of glyphs that
  `stage4_vectorize`'s sub-detail 0.5px-floor treatment already left
  reasonably consistent. Buffering all 14 anyway replaced 13 already-good
  polygons with cruder skeleton-buffer approximations for no corrective
  benefit, and a side-by-side render comparison (regularization forced off
  via the same monkeypatch `tests/test_pipeline.py` already uses, vs. the
  wired default) shows the un-regularized subline reads MORE cleanly as
  "ENTERPRISES INC" than the regularized one.
- **A skeleton-LINE buffer cannot represent a real interior hole.**
  Buffering a `MultiLineString` (the skeleton chains) can only enclose a
  hole by coincidence — the loop has to be wide enough, relative to the
  buffer radius, at every point along it, which a small letterform's
  counter (an "R" or "P" bowl at 1.9 mm cap height) is not. Three of this
  cluster's 14 members have a real interior ring in their PRE-regularization
  polygon (their own rescued/vectorized shape, from `stage4_vectorize`,
  already correctly traced the counter); post-regularization every one of
  those holes was gone, buffered solid.

The fix narrows `regularize_text_clusters` to only replace a member's
geometry when doing so is both SAFE and NEEDED, per the design doc's own
listed option ("skip regularization when the original shape is already
clean/valid"): a member already close to the cluster's target half-width is
left untouched (`_REGULARIZE_SKIP_TOLERANCE`, below), and a member whose
original polygon already has a real interior ring is always left untouched
regardless of width — a uniform-radius line buffer is never the right
primitive for reproducing a hole it did not measure, so the geometrically
honest move is to not attempt it, not to bolt on hole-reconstruction after
the fact. This is additive selectivity, not a rewrite of the buffer itself:
a member that genuinely IS inconsistent (the fixture's own 30%-outlier "I",
and the design doc's synthetic noisy-cluster test) still regularizes exactly
as before.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon

from . import machine
from .regions import Region
from .shapefield import ShapeField, build_shape_field
from .stage1_prep import Prep
from .stage6_satin import _merge_through_junctions, _prune_spurs, _skeleton_edges

# A group must clear this many members before it counts as "text": letters
# come in groups, and two similarly-sized small shapes near each other is
# common (a belt buckle's two rivets, a logo's two dots) without being
# lettering. Three is the smallest count that starts to look like a genuine
# run of glyphs rather than a coincidence of two, and it is also one short of
# the four-letter fixture (`test_run_tier.py`'s six-bar subline distilled to
# its geometry) this feature exists for, leaving margin either side of the
# real target rather than fitting it exactly.
MIN_CLUSTER_MEMBERS = 3

# Two candidates may join the same cluster only if their centroids are within
# this multiple of their own (larger) bbox height. The benchmark subline
# (`test_run_tier._subline_image`) spaces 1.8 mm letters about 2.3 mm apart
# centre-to-centre — a ratio of ~1.3 — so 3.0 leaves comfortable headroom
# above real intra-word spacing while still failing on shapes separated by
# more than a couple of letter-heights (a different word, a different logo
# element entirely).
PROXIMITY_HEIGHT_MULT = 3.0

# Two candidates may join the same cluster only if the smaller of their bbox
# heights (resp. stroke-width means) is at least this fraction of the larger
# — i.e. no more than a 2x difference either way. Letters in one word are cut
# from the same typeface at the same size, so real members should agree far
# more tightly than this; the loose 0.5 floor is deliberately permissive
# (simplification noise on sub-detail glyphs already measured at up to ~10%
# in this module's own test fixtures) so the gate catches a clearly
# different-scale neighbour without also splitting a real word over
# ordinary letter-to-letter geometry noise.
SIMILARITY_RATIO = 0.5

# A member's OWN pre-regularization stroke half-width, measured within this
# fraction of the cluster's shared target (`text_cluster_stroke_mm`), is left
# untouched by `regularize_text_clusters` rather than replaced by a skeleton
# buffer -- see the module docstring's "Selective regularization" section.
# 0.15 sits cleanly between the two real populations measured there: 13 of
# the benchmark subline's 14 real members fall within +-11% of their
# cluster's median (typographically indistinguishable noise from
# vectorization, not a real weight difference to correct), while the
# fixture's one genuine outlier (+30%) and the design doc's synthetic
# noisy-cluster test fixture (deliberately spread +-22%) both clear this
# tolerance and still regularize exactly as before.
_REGULARIZE_SKIP_TOLERANCE = 0.15


@dataclass(frozen=True)
class _Candidate:
    region: Region
    height_mm: float
    stroke_mean_mm: float
    cx: float
    cy: float


def _stroke_stats_mm(region: Region) -> float | None:
    """Mean stroke half-width (mm) at the shape's own skeleton, or None if
    the polygon is too degenerate to field (`build_shape_field`'s own guard)
    or somehow skeletonless (a mask with no medial axis at all)."""
    field = build_shape_field(region.polygon)
    if field is None or not field.skel.any():
        return None
    return float(np.mean(field.dist[field.skel])) / field.scale


def _candidates(regions: list[Region]) -> list[_Candidate]:
    out: list[_Candidate] = []
    for r in regions:
        if not r.meta.get("rescued_small_shape"):
            continue
        stroke_mm = _stroke_stats_mm(r)
        if stroke_mm is None:
            continue
        x0, y0, x1, y1 = r.polygon.bounds
        out.append(_Candidate(region=r, height_mm=y1 - y0, stroke_mean_mm=stroke_mm,
                               cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0))
    return out


def _similar(a: float, b: float, ratio: float) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    return hi > 0 and lo / hi >= ratio


def _linked(a: _Candidate, b: _Candidate) -> bool:
    """Symmetric by construction (every term is order-independent), which is
    what makes the union-find result in `_cluster` invariant to input order —
    the determinism this module is required to guarantee."""
    if not _similar(a.height_mm, b.height_mm, SIMILARITY_RATIO):
        return False
    if not _similar(a.stroke_mean_mm, b.stroke_mean_mm, SIMILARITY_RATIO):
        return False
    dist = math.hypot(a.cx - b.cx, a.cy - b.cy)
    return dist <= PROXIMITY_HEIGHT_MULT * max(a.height_mm, b.height_mm)


def _cluster(cands: list[_Candidate]) -> list[list[_Candidate]]:
    """Connected components of the `_linked` graph, via union-find. Grouping
    by graph connectivity (rather than e.g. greedy nearest-first merging)
    means the partition depends only on the SET of pairwise links, never on
    the order candidates were visited in — the property the determinism test
    pins down."""
    parent = {c.region.shape_id: c.region.shape_id for c in cands}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            if _linked(cands[i], cands[j]):
                union(cands[i].region.shape_id, cands[j].region.shape_id)

    groups: dict[str, list[_Candidate]] = {}
    for c in cands:
        groups.setdefault(find(c.region.shape_id), []).append(c)
    return list(groups.values())


def _text_cluster_id(shape_ids: list[str]) -> str:
    """Same blake2s-digest(4)-of-sorted-ids pattern as `regions._merge_shape_id`
    / `_split_shape_id`, copied rather than imported (it is three lines, and
    those are private to `regions.py`). "TC" cannot collide with either of
    theirs ("SM" prefix, "SP" prefix) or with `assign_shape_ids`'s plain "S".
    """
    key = ":".join(sorted(shape_ids)).encode()
    return "TC" + hashlib.blake2s(key, digest_size=4).hexdigest()


def detect_text_clusters(regions: list[Region], p: Prep) -> None:
    """Post-vectorization pass: tag every member of a qualifying group of
    rescued small shapes as a text candidate (`text_candidate`,
    `text_cluster_id`, `text_cluster_stroke_mm` in `Region.meta`).

    `p` is accepted, not read, so the signature matches
    `tag_enclosed_background`'s — a future revision that needs `Prep` (art
    bbox, resolution) does not have to change every call site again. Every
    input to today's algorithm already lives on `region.polygon`.

    Fails open throughout, same discipline as `tag_enclosed_background`: a
    degenerate candidate is silently excluded (not crashed on), and a group
    that doesn't clear `MIN_CLUSTER_MEMBERS` is left with NO new meta keys at
    all, exactly like an ordinary shape — absent means false, never an
    explicit False, matching `rescued_small_shape`/`enclosed_background`'s own
    convention.
    """
    for group in _cluster(_candidates(regions)):
        if len(group) < MIN_CLUSTER_MEMBERS:
            continue
        shape_ids = sorted(c.region.shape_id for c in group)
        cluster_id = _text_cluster_id(shape_ids)
        stroke_mm = float(np.median([c.stroke_mean_mm for c in group]))
        for c in group:
            c.region.meta["text_candidate"] = True
            c.region.meta["text_cluster_id"] = cluster_id
            c.region.meta["text_cluster_stroke_mm"] = stroke_mm


# --- Regularization (Step 5): redraw each member at a shared stroke width ---


def _skeleton_chains_mm(field: ShapeField) -> list[list[tuple[float, float]]]:
    """A tagged shape's skeleton, decomposed into stroke chains in mm space.

    Reuses `stage6_satin`'s own tested skeleton-to-stroke decomposition
    (`_skeleton_edges` + `_merge_through_junctions`, the same pair
    `extract_strokes` uses to build satin rails) rather than re-deriving a
    raster-skeleton-to-vector walk from scratch — see the module docstring
    for why this handles branching glyphs without a scope restriction.

    Pixel -> mm uses `field.ox/oy/scale`, pixel-CENTER convention
    (`+0.5`), matching `stage6_satin.extract_strokes`'s own `to_mm` exactly
    (not `shapefield.rasterize_polygon`'s corner convention — the skeleton
    pixels this walks are already on the `ShapeField`'s raster grid, same
    grid `extract_strokes` reads when routed through `build_shape_field`).

    Returns `[]` if the skeleton has no material left after spur pruning —
    the caller treats that as "cannot regularize," never as a crash.
    """
    if not field.skel.any():
        return []
    skel_mask = field.skel.astype(np.uint8).copy()  # _prune_spurs mutates in place
    half_px = float(field.dist[field.skel].mean())
    # Same spur-pruning threshold `extract_strokes` applies before walking a
    # skeleton into strokes: a raster medial axis grows short spurious twigs
    # at every junction, and left in they'd buffer into little toes sticking
    # out of an otherwise clean letterform.
    _prune_spurs(skel_mask, max(3.0, half_px * 1.6))
    if not skel_mask.any():
        return []

    def to_mm(pt: tuple[int, int]) -> tuple[float, float]:
        return (field.ox + (pt[0] + 0.5) / field.scale,
                field.oy + (pt[1] + 0.5) / field.scale)

    chains: list[list[tuple[float, float]]] = []
    for e in _merge_through_junctions(_skeleton_edges(skel_mask)):
        if len(e["pts"]) < 2:
            continue
        chains.append([to_mm(pt) for pt in e["pts"]])
    return chains


def _skeleton_buffer_polygon(field: ShapeField, radius_mm: float) -> Polygon | None:
    """Buffer `field`'s skeleton chains by `radius_mm` -> a single Polygon,
    or None if the result can't be trusted (empty/invalid, more than one
    disconnected piece, or below the sewability floor `boundary_override`
    already enforces on a hand-edited polygon — `machine.RUN_MIN_AREA_MM2`/
    `RUN_MIN_LOOP_MM`, `regions._check_sewable`'s own floor, duplicated here
    as a boolean check rather than imported since `_check_sewable` raises
    and this call site needs to fail open, not except a ValueError for
    control flow).
    """
    if radius_mm is None or radius_mm <= 0:
        return None
    chains = _skeleton_chains_mm(field)
    lines = [LineString(c) for c in chains if len(c) >= 2]
    if not lines:
        return None
    geom = lines[0] if len(lines) == 1 else MultiLineString(lines)
    try:
        buffered = geom.buffer(radius_mm)
    except Exception:
        return None
    if (not buffered.is_valid or buffered.is_empty
            or buffered.geom_type != "Polygon"
            or buffered.area < machine.RUN_MIN_AREA_MM2
            or buffered.exterior.length < machine.RUN_MIN_LOOP_MM):
        return None
    return buffered


def regularize_text_clusters(regions: list[Region], p: Prep) -> None:
    """Post-tagging pass (call immediately after `detect_text_clusters`):
    redraw every `text_cluster_id`-tagged region's polygon as a fixed-radius
    buffer around its own skeleton, sized to the cluster's shared target
    half-width (`meta["text_cluster_stroke_mm"]`, the cluster MEDIAN
    `detect_text_clusters` already computed and stored — a HALF-width/radius
    on purpose, see the module docstring, so buffering it does not double
    the stroke).

    `field = build_shape_field(region.polygon)` is called again here — a
    second call per tagged shape, not cached across this module's two
    passes. `detect_text_clusters` (Step 2) is intentionally left unmodified
    by this step (see the plan), so caching would mean either changing its
    return contract or keeping a side dict keyed by shape_id across two
    otherwise-independent functions for a handful of small letter rasters
    per design — not worth the complexity this pass's actual cost (a few
    cheap re-rasterizations of already-tiny glyph polygons) doesn't need.

    Fails OPEN, same discipline as every tagger in this codebase
    (`tag_enclosed_background`'s "uncertainty resolves to keep stitching
    it," restated here as "uncertainty resolves to no geometry change"): if
    the buffered result can't be trusted, `region.polygon` is left
    completely untouched and `meta["text_cluster_regularize_skipped"] =
    True` is set instead. Never raises, never crashes the pipeline.

    Two more cases leave the polygon untouched ON PURPOSE rather than by
    failure — see "Selective regularization" in the module docstring for the
    evidence behind both:

    - The member's own polygon already has a real interior ring (a true
      letterform hole/counter, already correctly traced by
      `stage4_vectorize`). A skeleton-LINE buffer has no way to reproduce
      that hole faithfully, so the honest move is not to attempt it.
    - The member's own pre-regularization stroke half-width is already
      within `_REGULARIZE_SKIP_TOLERANCE` of the cluster's shared target —
      nothing to correct, and replacing an already-good polygon with a
      cruder buffered approximation is a pure loss of fidelity for no
      consistency gain.

    Both set `meta["text_cluster_regularize_skipped"] = True` (the
    downstream contract is "was this polygon replaced," not "did replacement
    fail") plus `meta["text_cluster_regularize_skip_reason"]` naming which
    case, for diagnostics.

    `p` is accepted, not read — same reason `detect_text_clusters` accepts
    it: signature parity with this module's other post-vectorization pass,
    not because today's algorithm needs it.
    """
    for r in regions:
        if not r.meta.get("text_cluster_id"):
            continue

        if r.polygon.interiors:
            r.meta["text_cluster_regularize_skipped"] = True
            r.meta["text_cluster_regularize_skip_reason"] = "has_interior_hole"
            continue

        radius_mm = r.meta.get("text_cluster_stroke_mm")
        field = build_shape_field(r.polygon)
        if field is not None and radius_mm and field.skel.any():
            own_stroke_mm = float(np.mean(field.dist[field.skel])) / field.scale
            if abs(own_stroke_mm - radius_mm) <= _REGULARIZE_SKIP_TOLERANCE * radius_mm:
                r.meta["text_cluster_regularize_skipped"] = True
                r.meta["text_cluster_regularize_skip_reason"] = "already_consistent"
                continue

        new_poly = _skeleton_buffer_polygon(field, radius_mm) if field is not None else None
        if new_poly is None:
            r.meta["text_cluster_regularize_skipped"] = True
            r.meta["text_cluster_regularize_skip_reason"] = "buffer_failed"
            continue
        r.polygon = new_poly
        r.area_mm2 = new_poly.area
