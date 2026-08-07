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

## OCR-suggested text (2026-08-07 — Studio "Convert to text" entry point)

Everything above this section is deliberately OCR-free — see the opening
paragraph's "No OCR, no character recognition." This section does not
relax that: cluster DETECTION still never looks at pixel content, only
position/size/stroke-width geometry. What it adds is a later, optional,
read-only pass that runs ONLY on shapes a cluster has ALREADY claimed
geometrically: once `detect_text_clusters` (and `regularize_text_clusters`,
if it ran) has decided "these members are probably a word," OCR is used to
guess WHAT word, so Studio's "Convert to text" flow can prefill an editable
textarea instead of handing the user a blank one.

This is a UX safety-critical feature, not a convenience shortcut — see
`docs/superpowers/specs/` and the design notes this shipped against:
automation-bias research on prefilled-vs-empty form fields found people
catch errors in a confident-looking wrong suggestion only ~30% of the time,
vs. ~75% when the system visibly hedges. Concretely, that means:

- This module NEVER decides whether to trust its own OCR read — it reports
  a raw per-member `(character, confidence)` pair and nothing more. The
  GATE (a confidence threshold, and what happens above/below it) is the
  Studio side's call (`app/src/lib/digitizer.js`'s `textClusterSeed`,
  `OCR_SUGGESTION_MIN_CONFIDENCE`) — this module has no opinion on "good
  enough," only a measurement.
- A member this pass can't read at all reports `(None, None)`
  ("measurement failed," this function's one "I don't know" case) rather
  than a fabricated low-confidence guess — the caller must treat that
  exactly like a below-threshold read, never differently.
- `fontKey` is never touched by anything downstream of this: OCR gives
  characters, never a typeface match.

Each member is scored independently (single-character `--psm 10`, the same
Tesseract page-segmentation choice `text-cluster-ocr-confidence-gate`'s
regularization-safety gate uses and for the same reason: a cluster member
is one rescued glyph, not a word Tesseract's own dictionary/layout model
should second-guess) — this module does not attempt word-level OCR across
a whole cluster's combined raster, both because a rescued cluster's members
are independently-vectorized shapes with no guaranteed shared baseline/
raster to hand Tesseract as one image, and because per-member scores are
what the gate above needs anyway (one weak glyph should not be masked by an
otherwise-confident cluster average — see `digitizer.js` for the aggregate
this feeds).

**This is an independent, separately-scoped consumer of the same
"rasterize a member's own polygon, run Tesseract, read `data['conf']`"
technique `text-cluster-ocr-confidence-gate`'s quality gate uses** (parallel
work, not yet merged as of this writing) — not a shared call path. That
gate's job is "would replacing this polygon read worse" (a boolean,
`data["text"]` never read, per its own module note); this pass's job is
"what does this polygon probably say" (the text and confidence both
surfaced, read-only, to the client). Reusing the technique, not the
decision.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract
from PIL import Image
from shapely.geometry import LineString, MultiLineString, Polygon

from . import machine
from .regions import Region
from .shapefield import ShapeField, build_shape_field, rasterize_polygon
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
        r.polygon = new_poly
        r.area_mm2 = new_poly.area


# --- OCR-suggested text (see module docstring's "OCR-suggested text" section) --

# Tesseract page-segmentation mode: "treat the image as a single character."
# A cluster member is exactly that — one rescued glyph, never a word or
# line — so this scores raw character-shape confidence without a
# dictionary/language model second-guessing an isolated letter. Same choice,
# same reasoning, as `text-cluster-ocr-confidence-gate`'s regularization
# safety gate (a parallel, independently-scoped consumer of the same
# rasterize-and-score technique — see the module docstring).
_OCR_PSM = 10

# A cluster member's own rasterized crop (`shapefield.rasterize_polygon`,
# ~6 px/mm) is far too small for Tesseract on its own — a 1.8 mm cap height
# is ~11 px there. Upscaled (nearest-neighbor, so no new edge information is
# invented) so its longer side lands near this many pixels, then padded with
# a white quiet zone Tesseract's own layout analysis expects.
_OCR_RASTER_TARGET_PX = 200
_OCR_RASTER_PAD_PX = 24


def _ocr_raster(poly: Polygon) -> Image.Image | None:
    """`poly` rasterized, upscaled and padded into an OCR-ready crop: black
    ink on a white field, matching what Tesseract is tuned against. `None`
    for a degenerate polygon that rasterizes to nothing (mirrors
    `build_shape_field`'s own guard).

    Uses `shapefield.rasterize_polygon` — the SAME rasterizer
    `build_shape_field` uses internally — so the crop this scores is
    geometrically the same raster the rest of this module already reasons
    about, not a second, independently-tuned rendering path.
    """
    mask, _scale, _ox, _oy = rasterize_polygon(poly)
    if not mask.any():
        return None
    h, w = mask.shape
    up = max(1, _OCR_RASTER_TARGET_PX // max(h, w))
    big = cv2.resize(mask, (w * up, h * up), interpolation=cv2.INTER_NEAREST)
    pad = _OCR_RASTER_PAD_PX
    canvas = np.zeros((big.shape[0] + 2 * pad, big.shape[1] + 2 * pad), np.uint8)
    canvas[pad:pad + big.shape[0], pad:pad + big.shape[1]] = big
    return Image.fromarray(255 - canvas)  # mask: 255=ink -> invert to black-on-white


def _ocr_glyph_guess(poly: Polygon) -> tuple[str | None, float | None]:
    """-> `(character, confidence)` for `poly`'s own rasterized crop.

    `character` is Tesseract's own single best-guess character (its first
    non-blank detected token, truncated to one character — a `--psm 10` crop
    should already yield at most one token, but this never trusts that
    unconditionally); `None` when nothing was detected — an empty read is a
    real, low-information result, not unlike `confidence`'s 0.0 floor, but
    there is no meaningful "empty character" to report, so `None` is both
    "not detected" and "no character" here (unlike `confidence`, only one
    empty case exists for `character`).

    `confidence` is the mean of Tesseract's own non-negative `data["conf"]`
    values (0..100); a crop with no detected text at all reads as 0.0 — the
    metric's floor, a real (if low) measurement, NOT the same as "couldn't
    measure." `None` for `confidence` (and `character`) together is this
    function's ONLY "I don't know" case: a degenerate crop, or Tesseract
    itself missing/erroring. The caller (`ocr_suggest_text`, and ultimately
    the Studio-side gate) must treat that exactly like a below-threshold
    read, never as a signal of its own.
    """
    img = _ocr_raster(poly)
    if img is None:
        return None, None
    try:
        data = pytesseract.image_to_data(
            img, config=f"--psm {_OCR_PSM}", output_type=pytesseract.Output.DICT)
    except Exception:
        return None, None
    confs = [float(c) for c in data["conf"] if float(c) >= 0]
    confidence = sum(confs) / len(confs) if confs else 0.0
    texts = [t for t in data["text"] if t and t.strip()]
    character = texts[0].strip()[:1] if texts else None
    return character, confidence


def ocr_suggest_text(regions: list[Region], p: Prep) -> None:
    """Post-regularization pass (call after `regularize_text_clusters`, so
    this reads whichever polygon the design will actually sew/export — see
    the module docstring's "OCR-suggested text" section for the full
    rationale): for every `text_cluster_id`-tagged member, stamp
    `Region.meta["ocr_char"]`/`Region.meta["ocr_confidence"]` with a
    per-glyph OCR read of the member's own final polygon.

    Read-only metadata, exactly like `text_candidate`/`text_cluster_id`
    before it — never fed back into detection, regularization, or any other
    geometry decision. An untagged region gets no new meta keys at all
    (absent means "no suggestion," the same "absent key = default"
    convention `text_candidate` already follows); a tagged region whose
    measurement fails gets both keys explicitly set to `None`, matching
    `_ocr_glyph_guess`'s own "I don't know" contract — never raises, never
    crashes the pipeline.

    `p` is accepted, not read — same reason every other pass in this module
    does: signature parity with a future revision that needs `Prep`.
    """
    for r in regions:
        if not r.meta.get("text_cluster_id"):
            continue
        character, confidence = _ocr_glyph_guess(r.polygon)
        r.meta["ocr_char"] = character
        r.meta["ocr_confidence"] = confidence
