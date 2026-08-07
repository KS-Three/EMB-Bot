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

## Candidate filters (classical connected-component / Stroke Width
Transform literature, added after the above shipped)

`_candidates` originally compared only each shape's MEAN stroke half-width
for cross-shape similarity, discarding the per-pixel distribution
`shapefield.build_shape_field` already computes. Three more, cheap,
classical-CV filters tighten the same function, all measured against the
real benchmark fixture (`enthusiast_logo.png` @ 90 mm, PRE-regularization —
`_candidates` runs inside `detect_text_clusters`, which is called before
`regularize_text_clusters` ever redraws a member's polygon, so that is the
geometry these thresholds had to be calibrated against, not the
already-regularized, artificially-uniform-width result):

- **Stroke-width coefficient of variation** (`STROKE_CV_MAX`): a shape whose
  per-pixel stroke half-width varies a lot relative to its own mean is more
  likely a part-letter/part-blob fragment than a real, evenly-stroked glyph
  — the Stroke Width Transform literature's own signal (Epshtein/Ofek/Wexler
  2010), applied here to a shape's internal consistency rather than as a
  transform in its own right. The fixture's 14 real letters measure CV
  0.027-0.235; three sibling rescued shapes that are NOT part of that word
  (segmentation fragments riding inside real letters' bounding boxes — see
  the nesting filter below) measure 0.401-0.461, a clean gap.
- **Aspect-ratio bounds** (`ASPECT_RATIO_MIN`/`MAX`): the same 14 real
  letters are all portrait, width/height 0.107-0.964 (every glyph in this
  word is taller than wide, as expected of Latin uppercase); the same three
  non-member fragments are landscape, 1.778-2.125. The bounds leave real
  margin on both sides of the measured letter range (room for a thinner
  "I"/"l" stroke or a wider "M"/"W" than this fixture happens to contain)
  while staying well clear of the measured non-letter fragments.
- **Bbox-nesting exclusion** (`_drop_nested`): a candidate whose bbox is
  fully contained inside another candidate's (larger) bbox is dropped. Real
  letters in a row sit side by side, never nested inside a sibling's
  footprint; on the real fixture, the same three non-member fragments above
  each nest inside one of the 14 real letters' bboxes — a THIRD, independent
  confirmation that they are segmentation artifacts, not glyphs of their own
  (they are also already excluded by height/CV/aspect on this fixture, but
  nesting catches the shape of the failure directly rather than relying on
  those other signals happening to agree).

Synthetic axis-aligned rectangles (this module's own test fixtures, and any
future one) score noticeably WORSE on stroke-width CV than a real font
glyph of similar proportions: a solid rectangle's medial axis is one
straight segment, so the taper at its two ends (universal to any stroke's
free tip) is a much larger fraction of its total skeleton length than a
real letter's — a real letter typically has more total skeleton material
(corners, serifs, multiple joined strokes) diluting the same taper effect.
Measured directly: a 0.9x1.8mm synthetic rectangle scores CV 0.458, well
above even the real fixture's non-letter fragments. This module's test
fixtures use thinner rectangles (~0.15-0.35mm wide at 1.8mm tall, CV
0.21-0.29) specifically so they clear `STROKE_CV_MAX` — not because letters
are always that thin, but because a plain rectangle is not a faithful
stand-in for a real glyph's stroke-consistency signal at the width this
module previously used, and the alternative (loosening `STROKE_CV_MAX`
enough for a 0.9mm-wide rectangle to pass) would raise the real threshold
above the real fixture's own measured non-letter fragments, making the
filter unable to catch the one concrete case it exists for.

## MSER — investigated, deliberately NOT built (measured, not assumed)

`cv2.MSER_create()` was investigated as a possible companion signal, per
scene-text-detection literature's use of Maximally Stable Extremal Regions:
does a candidate remain a stable blob across a SWEEP of intensity
thresholds, a property real letterform strokes exhibit under uniform thread
color. Two possible fits were considered — upstream, in
`stage3_segment.resolve_small_regions`, to catch lettering that merged into
a bigger neighbor's mask before ever becoming its own `rescued_small_shape`
region; and as a direct per-shape confidence signal here (`detect_text_
clusters` already receives `p: Prep`, whose `p.rgb` is the real prepped
raster — the plumbing to read source pixels already exists, unused until
now).

Measured directly against `enthusiast_logo.png` — both `p.rgb` (the prepped
raster `detect_text_clusters` actually receives) and the raw source PNG
before any pipeline processing, at the default `MSER_create()` parameters
and at `delta`/`min_area` swept down to 1px — `cv2.MSER_create().
detectRegions()` returns **zero** regions everywhere. The reason is
structural, not a fixture accident: the raw source file itself has exactly
3 unique grayscale values (`np.unique`), and the subline text region
specifically has exactly 2 (pure foreground/background, no antialiasing
gradient at all). MSER's whole mechanism is tracking how a thresholded
blob's area changes as the threshold sweeps across a RANGE of levels; with
only 1-2 meaningful threshold crossings in the entire image, there is no
multi-level intensity landscape for that sweep to measure stability across,
and the algorithm's own internal stability check (`_max_variation`) has
nothing to pass or fail — MSER isn't weakly effective here, it structurally
cannot fire.

This is not specific to one fixture: this module's OWN scope is flat-lane
art (`MASTER_SCOPE.md`'s own text-cluster entry: "this feature only acts on
`rescued_small_shape`-flagged Regions, a flat-lane-only concept") — hard
vector-style edges, few solid colors, by construction of the "flat"
classification this pipeline already gates on (`stage0_classify.py`). MSER
earns its keep on photographs (camera noise, lighting gradients, JPEG
blur — smooth multi-level intensity landscapes with real thresholds to
sweep). A domain that is, by design, the opposite of that is not a
promising target for it, and the real measurement above confirms it, at
both the pre- and post-quantization stage, not just in theory. Per this
feature's own scoping conversation: "if any of the three turns out not to
be worth building once you're deep in it... it's fine to build the other
two well and document honestly why you left one out" — this is that case.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon

from . import machine
from .regions import Region
from .shapecontext import shape_context_distance
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

# A candidate's per-pixel stroke half-width, measured at every skeletal
# pixel `shapefield.build_shape_field` already gives us, must not vary by
# more than this fraction of its own mean (coefficient of variation =
# std/mean) to be considered an evenly-stroked glyph rather than a
# part-letter/part-blob fragment. See the module docstring's "Candidate
# filters" section for the real measurements this threshold sits between:
# the benchmark fixture's 14 real letters (0.027-0.235) and its 3 non-member
# fragments (0.401-0.461).
STROKE_CV_MAX = 0.32

# A candidate's bbox width/height ratio must fall in this range. See the
# module docstring: the benchmark fixture's 14 real letters measure
# 0.107-0.964 (portrait), its 3 non-member fragments 1.778-2.125
# (landscape) -- these bounds leave real margin either side of the letters'
# measured range while staying well clear of the fragments'.
ASPECT_RATIO_MIN = 0.05
ASPECT_RATIO_MAX = 1.4

# `regularize_text_clusters`'s before/after Shape Context distance
# (`shapecontext.shape_context_distance`) gate: a cluster member whose
# post-regularization polygon scores ABOVE this against its own
# pre-regularization polygon is judged to have been structurally changed
# (a corner dropped, a hole filled), not just visually smoothed to a
# consistent stroke weight, and the geometry replacement is skipped -- same
# fail-open discipline as every other guard in this function. Calibrated
# against real+synthetic measurements (not the fixture alone, since none of
# its 14 members happen to regularize badly): the benchmark fixture's 14
# members, which the existing test suite already asserts regularize
# cleanly, measure 0.033-0.106; a synthetic branching ("L") letterform
# regularized at its own correctly-matched target radius (a realistic
# healthy case, not a straight bar) measures 0.173; the same shape
# regularized at a radius mismatched by 2x from its true stroke half-width
# -- itself within what `SIMILARITY_RATIO`'s 0.5 floor already permits two
# clustered members to differ by -- measures 0.285 with its buffered area
# already 2.4x the original. 0.25 sits above every measured healthy case
# (with margin) and below every measured damaging one.
SHAPE_CONTEXT_MAX_DIST = 0.25


@dataclass(frozen=True)
class _Candidate:
    region: Region
    height_mm: float
    width_mm: float
    stroke_mean_mm: float
    stroke_cv: float
    cx: float
    cy: float


@dataclass(frozen=True)
class _StrokeStats:
    """Per-pixel stroke half-width statistics at a shape's own skeleton:
    MEAN (the original similarity/median signal) and CV = std/mean
    (coefficient of variation, the internal-consistency signal `_candidates`
    filters on -- see `STROKE_CV_MAX`)."""
    mean_mm: float
    cv: float


def _skeleton_stroke_stats(region: Region) -> _StrokeStats | None:
    """Mean and coefficient-of-variation of stroke half-width (mm) at the
    shape's own skeleton, from ONE `build_shape_field` call, or None if the
    polygon is too degenerate to field (`build_shape_field`'s own guard) or
    somehow skeletonless (a mask with no medial axis at all)."""
    field = build_shape_field(region.polygon)
    if field is None or not field.skel.any():
        return None
    widths = field.dist[field.skel] / field.scale
    mean = float(np.mean(widths))
    cv = float(np.std(widths) / mean) if mean > 0 else 0.0
    return _StrokeStats(mean_mm=mean, cv=cv)


def _stroke_stats_mm(region: Region) -> float | None:
    """Mean stroke half-width (mm) at the shape's own skeleton, or None if
    the polygon is too degenerate to field (`build_shape_field`'s own guard)
    or somehow skeletonless (a mask with no medial axis at all). Thin
    wrapper over `_skeleton_stroke_stats` kept as its own function: existing
    callers outside this module (`tests/test_pipeline.py`) import it
    directly for the mean alone."""
    stats = _skeleton_stroke_stats(region)
    return stats.mean_mm if stats is not None else None


def _drop_nested(cands: list[_Candidate]) -> list[_Candidate]:
    """Exclude a candidate whose bbox is fully contained within another,
    larger candidate's bbox. Real letters in a row sit side by side, never
    nested inside a sibling's footprint; a rescued small shape whose bbox
    nests inside another candidate's is far more likely a segmentation
    fragment riding inside a real glyph's footprint than an independent
    letter of its own -- see the module docstring's "Candidate filters"
    section for the real fixture evidence. Ties (identical bbox, so neither
    is strictly larger) exclude neither side -- there is no basis to prefer
    one over the other, and dropping both would silently lose real
    candidates over a coincidence.
    """
    def bounds(c: _Candidate) -> tuple[float, float, float, float]:
        return c.region.polygon.bounds

    def area(b: tuple[float, float, float, float]) -> float:
        x0, y0, x1, y1 = b
        return (x1 - x0) * (y1 - y0)

    boxes = [bounds(c) for c in cands]
    out: list[_Candidate] = []
    for i, c in enumerate(cands):
        bx0, by0, bx1, by1 = boxes[i]
        nested = False
        for j, other in enumerate(boxes):
            if i == j:
                continue
            ox0, oy0, ox1, oy1 = other
            if (ox0 <= bx0 and oy0 <= by0 and ox1 >= bx1 and oy1 >= by1
                    and area(other) > area(boxes[i])):
                nested = True
                break
        if not nested:
            out.append(c)
    return out


def _candidates(regions: list[Region]) -> list[_Candidate]:
    raw: list[_Candidate] = []
    for r in regions:
        if not r.meta.get("rescued_small_shape"):
            continue
        stats = _skeleton_stroke_stats(r)
        if stats is None:
            continue
        if stats.cv > STROKE_CV_MAX:
            continue
        x0, y0, x1, y1 = r.polygon.bounds
        width_mm, height_mm = x1 - x0, y1 - y0
        if height_mm <= 0 or width_mm <= 0:
            continue
        aspect = width_mm / height_mm
        if not (ASPECT_RATIO_MIN <= aspect <= ASPECT_RATIO_MAX):
            continue
        raw.append(_Candidate(region=r, height_mm=height_mm, width_mm=width_mm,
                               stroke_mean_mm=stats.mean_mm, stroke_cv=stats.cv,
                               cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0))
    return _drop_nested(raw)


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

    A SECOND, purely-geometric guard runs after the buffer already passed
    every check above: `shapecontext.shape_context_distance` between the
    ORIGINAL polygon and the candidate buffered replacement (a glyph-
    plausibility gate, Belongie/Malik/Puzicha 2002's Shape Context
    descriptor — see that module's own docstring). A valid, sewable buffer
    can still be a bad regularization: a target radius mismatched enough
    from a member's own true stroke width (already possible within
    `SIMILARITY_RATIO`'s 0.5 floor, see `SHAPE_CONTEXT_MAX_DIST`'s
    docstring) inflates or blows out real structure — a corner, a hole —
    while the buffer stays perfectly valid and comfortably sewable. This is
    NOT character recognition — a pure structural-similarity check between
    two versions of the SAME shape, the same "no OCR anywhere in this
    slice" discipline the module docstring states elsewhere. The measured
    distance is recorded either way (`meta["text_cluster_shape_context_dist"]`)
    for diagnostics, whether or not it crosses the gate.

    `p` is accepted, not read — same reason `detect_text_clusters` accepts
    it: signature parity with this module's other post-vectorization pass,
    not because today's algorithm needs it.
    """
    for r in regions:
        if not r.meta.get("text_cluster_id"):
            continue
        radius_mm = r.meta.get("text_cluster_stroke_mm")
        field = build_shape_field(r.polygon)
        new_poly = _skeleton_buffer_polygon(field, radius_mm) if field is not None else None
        if new_poly is None:
            r.meta["text_cluster_regularize_skipped"] = True
            continue
        sc_dist = shape_context_distance(r.polygon, new_poly)
        if sc_dist is not None:
            r.meta["text_cluster_shape_context_dist"] = sc_dist
        if sc_dist is not None and sc_dist > SHAPE_CONTEXT_MAX_DIST:
            r.meta["text_cluster_regularize_skipped"] = True
            r.meta["text_cluster_regularize_shape_changed"] = True
            continue
        r.polygon = new_poly
        r.area_mm2 = new_poly.area
