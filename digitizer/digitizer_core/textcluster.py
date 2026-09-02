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

## OCR-confidence quality gate (2026-08-07 addition — additional safety layer)

The two checks above are geometric heuristics (own-width-vs-target, has a
ring). Both are proxies for "would replacing this polygon read worse," not
direct measurements of it. This adds a third, independent check that
measures the thing the other two only infer: for a member that clears BOTH
existing checks (genuinely off-target, no hole to protect) and is about to
be buffered, Tesseract is run on the member's own rasterized crop TWICE —
once on the original polygon, once on the proposed buffered replacement —
and if confidence drops by more than `_OCR_CONFIDENCE_DROP_THRESHOLD`
points, the buffer is discarded and the member falls back to its original
polygon, exactly like `buffer_failed`. This is no OCR added to the design
principle every other part of this module (and `textcluster.py`'s own
top-of-file docstring) holds to — see that section for why. **The decoded
text is never read**: only `data["conf"]` is touched, `data["text"]` is
never accessed, logged, or stored, and no OCR output of any kind persists
past the local comparison inside `_ocr_regularization_hurts_legibility`. The
prior-art pattern (score, transform, re-score, use the delta as a legibility
signal, discarding the decoded text entirely — PreP-OCR, arXiv:2505.20429;
OCRGenScore, arXiv:2507.15085) is what this reuses.

**Threshold calibration (measured, not assumed).** Two real sources, both
using the same rasterize -> upscale 200px longest side -> pad 24px -> invert
-> `pytesseract.image_to_data(..., config="--psm 10")` -> mean of
non-negative `conf` values (an empty/undetected result reads as confidence
0.0, the metric's floor, not as "no signal" — that would be
indistinguishable from "nothing changed"; a genuine measurement failure,
e.g. Tesseract missing, returns `None` and the gate fails open instead,
below):

- **The real benchmark fixture.** Of `enthusiast_logo.png`'s 14-member
  subline cluster at 90 mm, only the one true outlier (the same +30%-off "I"
  the module docstring above already cites) clears both existing checks and
  reaches the buffer. Measured directly: confidence 77.0 before, 0.0 after
  (Tesseract found no text at all in the buffered crop) — a 77-point drop.
- **A synthetic cluster of real font-rendered glyphs** (DejaVu Sans Bold,
  `E F H I L N S T Z` — holeless letters only, so the interior-ring check
  can't mask this signal — individually perturbed in stroke width so several
  genuinely clear `_REGULARIZE_SKIP_TOLERANCE` against their own median).
  Six members actually reached the buffer; measured deltas (before -> after,
  own-width deviation from target in parens): F +30.9% dev, 49.0 -> 0.0
  (-49); T +39.0% dev, 85.0 -> 58.0 (-27); I +49.5% dev, 26.0 -> 0.0 (-26);
  Z -27.1% dev, 76.0 -> 56.0 (-20); H -15.1% dev, 73.0 -> 68.0 (-5); N
  -27.2% dev, 80.0 -> 91.0 (+11, buffering genuinely IMPROVED this one, and
  the gate correctly does not block an improvement).

`_OCR_CONFIDENCE_DROP_THRESHOLD = 20.0` sits between the smallest real
"still fine" case (H, -5: a mild dip, 68% is still a confident read, the
letterform survived) and the smallest real "actually damaged" case (Z, -20:
comparable in size to I's -26 and clearly past the noise floor H
established). N's +11 (an improvement) and the real fixture's -77 and
synthetic F's -49 / T's -27 / I's -26 all land unambiguously on the correct
side of that line. Every OCR call is wrapped to fail open: if Tesseract
isn't installed, errors, or the crop is degenerate, `_ocr_confidence`
returns `None` and the gate treats that exactly like "no signal" —
regularization proceeds exactly as it did before this layer existed. This
gate can only ever make `regularize_text_clusters` MORE conservative, never
less: it has no path to replace a polygon the existing checks would have
left alone.
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
from bisect import bisect_left
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract
from PIL import Image
from shapely.geometry import LineString, MultiLineString, Polygon

from . import machine
from .regions import Region
from .shapecontext import shape_context_distance
from .shapefield import ShapeField, build_shape_field
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

# --- OCR-confidence quality gate (additional safety layer, see the module
# docstring's "OCR-confidence quality gate" section for the full evidence
# trail behind every constant below) ------------------------------------

# Tesseract page-segmentation mode: "treat the image as a single character."
# Each cluster member is exactly that -- one rescued glyph, not a word or
# line -- so the classifier is scored on raw character-shape confidence,
# without a dictionary/language model second-guessing an isolated letter.
_OCR_PSM = 10

# The member's own rasterized crop (`shapefield.rasterize_polygon`, ~6
# px/mm) is far too small for Tesseract on its own -- a 1.8 mm cap height is
# ~11 px there. Upscaled (nearest-neighbor, so no new edge information is
# invented) so its longer side lands near this many pixels, then padded with
# a white quiet zone Tesseract's own layout analysis expects.
_OCR_RASTER_TARGET_PX = 200
_OCR_RASTER_PAD_PX = 24

# A crop's OCR confidence is the mean of Tesseract's own non-negative `conf`
# values (0..100); a crop with no detected text at all reads as 0.0 -- the
# metric's floor, not "no signal" (see module docstring). If the BEFORE and
# AFTER crops' confidence differs by at least this many points, the proposed
# buffer is treated as damaging and discarded (falls back to
# `buffer_failed`'s path). 20.0 sits between the smallest real "still fine"
# delta measured (-5, a mild dip that stayed clearly legible) and the
# smallest real "actually damaged" delta measured (-20) -- see the module
# docstring for the full real before/after numbers this was calibrated
# against, both from the real benchmark fixture and a constructed synthetic
# cluster of real font-rendered glyphs.
_OCR_CONFIDENCE_DROP_THRESHOLD = 20.0
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


def _linked(a: _Candidate, b: _Candidate,
            height_ratio: float = SIMILARITY_RATIO) -> bool:
    """Symmetric by construction (every term is order-independent), which is
    what makes the union-find result in `_cluster` invariant to input order —
    the determinism this module is required to guarantee.

    `height_ratio` defaults to `SIMILARITY_RATIO`, so every existing caller is
    byte-identical; `_lettering_groups` passes a tighter one to keep two lines
    of a logotype apart. See `SATIN_ANGLE_HEIGHT_RATIO`.
    """
    if not _similar(a.height_mm, b.height_mm, height_ratio):
        return False
    if not _similar(a.stroke_mean_mm, b.stroke_mean_mm, SIMILARITY_RATIO):
        return False
    dist = math.hypot(a.cx - b.cx, a.cy - b.cy)
    return dist <= PROXIMITY_HEIGHT_MULT * max(a.height_mm, b.height_mm)


def _cluster(cands: list[_Candidate],
             height_ratio: float = SIMILARITY_RATIO) -> list[list[_Candidate]]:
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
            if _linked(cands[i], cands[j], height_ratio):
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


def _spur_len_px(field: ShapeField) -> float:
    """The spur-pruning length (pixels) `extract_strokes` applies before
    walking a skeleton into strokes: a raster medial axis grows short spurious
    twigs at every junction, and left in they'd buffer into little toes
    sticking out of an otherwise clean letterform.

    Its own function because it is now read twice — once to prune, and once by
    `_cluster_house_angle_deg` to decide how much of a chain END is medial-axis
    artifact rather than stroke direction. Those are the same structure
    measured for two purposes, so they must not drift apart.
    """
    return max(3.0, float(field.dist[field.skel].mean()) * 1.6)


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
    _prune_spurs(skel_mask, _spur_len_px(field))
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


# --- OCR-confidence quality gate --------------------------------------------


def _ocr_raster(poly: Polygon) -> Image.Image | None:
    """`poly` rasterized, upscaled and padded into an OCR-ready crop: black
    ink on a white field, matching what Tesseract is tuned against (its own
    native rasterization is dark text on a light page). None for a
    degenerate polygon that rasterizes to nothing (mirrors
    `build_shape_field`'s own guard; same fixture class, same reason).

    Uses `shapefield.rasterize_polygon` — the SAME rasterizer
    `build_shape_field` uses internally — so the crop this gate scores is
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


def _ocr_confidence(poly: Polygon) -> float | None:
    """Mean Tesseract confidence (0..100) on `poly`'s own rasterized crop, or
    `None` if that can't be measured (degenerate crop, Tesseract missing or
    erroring) — `None` is this function's ONLY "I don't know" value; an
    empty read (Tesseract found no text at all) is a real, low measurement
    (0.0), not a `None` — see the module docstring for why that distinction
    is load-bearing for the gate below.

    Reads ONLY `data["conf"]`. `data["text"]` — the decoded characters — is
    never accessed here or anywhere else in this module: this function's
    return value is the sole channel by which anything Tesseract produces
    leaves this call, and it is a float, never a string.
    """
    img = _ocr_raster(poly)
    if img is None:
        return None
    try:
        data = pytesseract.image_to_data(
            img, config=f"--psm {_OCR_PSM}", output_type=pytesseract.Output.DICT)
    except Exception:
        return None
    confs = [float(c) for c in data["conf"] if float(c) >= 0]
    return sum(confs) / len(confs) if confs else 0.0


def _ocr_regularization_hurts_legibility(original_poly: Polygon, candidate_poly: Polygon) -> bool:
    """True only if OCR confidence measurably DROPS from `original_poly` to
    `candidate_poly` — the additional safety layer on top of
    `_REGULARIZE_SKIP_TOLERANCE`/hole-preservation above (module docstring,
    "OCR-confidence quality gate").

    Fails open by construction: either measurement returning `None` (OCR
    unavailable or inconclusive) makes the drop-check itself unreachable, so
    a missing Tesseract install degrades this gate to a no-op rather than
    blocking every regularization in the codebase. Both confidence values
    are local to this call and never escape it — nothing from either OCR
    pass is stored, logged, or returned beyond this one boolean.
    """
    before = _ocr_confidence(original_poly)
    after = _ocr_confidence(candidate_poly)
    if before is None or after is None:
        return False
    return (before - after) >= _OCR_CONFIDENCE_DROP_THRESHOLD


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

    A third case — `ocr_confidence_drop` — leaves the polygon untouched for
    the same "safe and needed" reason, but measured rather than inferred:
    see the module docstring's "OCR-confidence quality gate" section. It
    only ever fires on a member that ALREADY cleared both cases above (a
    genuine outlier, no hole to protect), so it can only make this pass more
    conservative, never less.

    Both set `meta["text_cluster_regularize_skipped"] = True` (the
    downstream contract is "was this polygon replaced," not "did replacement
    fail") plus `meta["text_cluster_regularize_skip_reason"]` naming which
    case, for diagnostics.
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

        if _ocr_regularization_hurts_legibility(r.polygon, new_poly):
            r.meta["text_cluster_regularize_skipped"] = True
            r.meta["text_cluster_regularize_skip_reason"] = "ocr_confidence_drop"
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


# --- The house cross angle for a detected word (Step 6) -----------------------
#
# Kent, on a sewn Becker Marine logo: *"When doing lettering, fill angle should
# be the same (for almost every block style font like this). Why is the 'N'
# running Vertically?"* `stage6_satin` grew the machinery to answer that on
# 2026-08-26 -- `satin_shape(angle_deg=...)`, held loosely by `_clamp_to_span`
# -- and `config.satin_angle_deg` / `Region.meta["satin_angle_deg"]` carry it.
# NOTHING EVER SET EITHER. The lever was built and left at None, which is
# today's per-stroke-tangent behaviour, so the sewn output never changed.
# This pass is what pulls it.
#
# WHY A DERIVED ANGLE AND NOT A CONSTANT. A wordmark is not always horizontal
# (arcs, slanted logotypes, a badge's rotated sub-line), so a hardcoded 0 deg
# would be right on the fixture and wrong on the next logo. The angle is read
# off the artwork instead: the direction the cluster's own strokes mostly run,
# turned 90 deg to cross them.
#
# WHY LENGTH-WEIGHTED. `stage6_satin`'s own note on the pro's file reads the
# crosses as clustering near horizontal on stems "which for block letters
# largely FOLLOWS from vertical strokes carrying most of the area." Weighting
# each skeleton segment by its length reproduces that mechanism rather than
# assuming its result: in block capitals the vertical stems out-measure the
# arms, so the dominant tangent comes out vertical and the cross horizontal --
# and on a genuinely slanted wordmark the same arithmetic tracks the slant.
# Length alone, not length x width. `regularize_text_clusters` targets ONE
# shared half-width across a cluster, so within one word length is already a
# good proxy for area. A per-vote width factor would be strictly better on the
# members regularization SKIPS (they keep their own width) -- it is left out
# because it was never measured, not because it would be wrong, and the test
# that pins the weighting would not distinguish the two.
#
# The aggregation is `directionfield.region_direction`'s, deliberately: angles
# on a half-circle average in DOUBLED-ANGLE space, and that module already
# carries the repo's implementation and its rationale. Same move here, with
# skeleton segments as the votes instead of structure-tensor pixels.
#
# Doubling turns a 90 deg rotation into a 180 deg one -- a negation -- which
# leaves the resultant's LENGTH untouched. So aggregating tangents and adding
# 90 deg at the end is identical to aggregating the crosses themselves, and
# reads more directly against the skeleton the votes come from.
#
# WHY THE VOTES ARE PER RASTER SEGMENT and not resampled over one stroke width
# the way `_rail_points` measures ITS tangents. That correction exists because
# a raster staircase can only step in eight directions, so a pointwise tangent
# carries up to +/-22.5 deg of noise -- and `_rail_points` needs each cross's
# angle individually, where that noise is visible in the sewn column. This
# function needs one AGGREGATE over hundreds of length-weighted segments,
# where the same noise cancels. Both were built and measured here (2026-08-27):
# resampling changed the worst-case error by 0.4 deg (2.3 vs 2.7 over rotations
# and sizes) and a curved stroke by 0.35 deg, so it was removed rather than
# kept as unearned machinery. End-trimming below is what actually mattered.

# Letters on ONE line of a wordmark share a cap height almost exactly -- the
# six capitals of "MARINE" on Kent's Becker logo all measure 13.0 mm. The
# module's own `SIMILARITY_RATIO` (0.5) is deliberately looser than that,
# because it exists to link RESCUED BLOBS whose measured size is dominated by
# vectorization noise; for whole glyphs the size is the design's own.
#
# 0.5 is too loose here for a concrete reason, measured 2026-08-27: it merges
# "MARINE" with the arched "BECKER" above it (heights 18.0-26.8 mm) into one
# 11-member group whose strokes then cancel. Separating them needs a floor
# above 13.0/26.8 = 0.49; staying inside one line needs a floor below ~1.0.
# 0.8 sits in the middle of that empty band rather than on either edge.
#
# KNOWN LIMIT: this is right for the ALL-CAPS block lettering Kent named
# ("almost every block style font like this") and splits MIXED-case text into
# a caps group and an x-height group. That failure is benign -- each group
# derives its own angle, and on upright text those angles agree -- but it is
# not the same thing as being correct. One logo is the whole evidence base.
SATIN_ANGLE_HEIGHT_RATIO = 0.8


def _lettering_groups(regions: list[Region]) -> list[list[Region]]:
    """Groups of glyph-shaped regions that plausibly form one line of text.

    Deliberately NOT `detect_text_clusters`'s candidate set, which this pass
    originally rode and which is empty on real lettering for two reasons
    measured on Kent's Becker Marine logo (2026-08-27):

      * its first gate is `rescued_small_shape`, a Step-1 flag for glyphs that
        `resolve_small_regions` saved from being dropped as noise. Ordinary
        lettering is segmented normally and never carries it -- 0 of that
        logo's 17 regions do.
      * `STROKE_CV_MAX` (0.32) rejects real glyphs outright. All 17 regions
        score 0.36-0.68: a letter's skeleton runs through junctions and tapers
        that a rescued blob's does not, so its stroke-width variance is
        genuinely higher. That constant is calibrated for blobs and is not
        wrong there; it is measuring a different population here.

    So this keeps the geometric tests that do transfer -- aspect ratio, mutual
    stroke-width and height similarity, proximity, `_drop_nested`, and a
    minimum member count -- and drops the two that do not. `detect_text_
    clusters` is untouched: changing ITS candidate set would pull
    `regularize_text_clusters` onto real letters and redraw them at a shared
    stroke width, which is a much larger behaviour change than this pass wants
    to make.
    """
    raw: list[_Candidate] = []
    for r in regions:
        stats = _skeleton_stroke_stats(r)
        if stats is None:
            continue
        x0, y0, x1, y1 = r.polygon.bounds
        width_mm, height_mm = x1 - x0, y1 - y0
        if height_mm <= 0 or width_mm <= 0:
            continue
        if not (ASPECT_RATIO_MIN <= width_mm / height_mm <= ASPECT_RATIO_MAX):
            continue
        raw.append(_Candidate(region=r, height_mm=height_mm, width_mm=width_mm,
                              stroke_mean_mm=stats.mean_mm, stroke_cv=stats.cv,
                              cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0))
    return [[c.region for c in g]
            for g in _cluster(_drop_nested(raw), SATIN_ANGLE_HEIGHT_RATIO)
            if len(g) >= MIN_CLUSTER_MEMBERS]


# Is the dominant direction real, or is it noise? This was
# `directionfield.COHERENCE_FALLBACK_MIN` (0.25) on the reasoning that the two
# modules ask the identical question. Measured 2026-08-27, they do not: that
# constant grades a per-pixel STRUCTURE-TENSOR field, and against real glyph
# skeletons it rejects the exact case this feature exists for. Kent's own
# Becker Marine logo scores R = 0.197 on "MARINE" (six upright block capitals
# on one baseline, deriving a correct 171.2 deg) and R = 0.203 on the arched
# "BECKER" -- both below 0.25, so the whole feature was inert on the artwork
# the complaint came from.
#
# The raw resultant CANNOT do this job at any threshold. Three rings, which
# have no stroke direction at all, score R = 0.167 -- close enough to MARINE's
# 0.197 that no cut separates them. What separates them is SAMPLE SIZE: R
# falls toward zero as votes accumulate under a null of no direction, so a
# modest R over hundreds of segments means something a similar R over dozens
# does not. This is ROADMAP gate 4 in miniature ("raw moves when the mix
# moves"), and the fix it prescribes: use the chance-corrected figure.
#
# So the gate is Rayleigh's test for a non-uniform circular distribution,
# applied in the same doubled-angle space the votes are aggregated in. Under
# the null, n*R^2 is approximately exponential, so p ~ exp(-n R^2) and the
# critical value is -ln(alpha). Measured on the six cases available:
#
#     MARINE, real lettering       R 0.197  n_eff  562   nR^2  21.7  admit
#     BECKER, real lettering       R 0.203  n_eff 1043   nR^2  42.8  admit
#     5 parallel stems             R 0.388  n_eff  175   nR^2  26.3  admit
#     3 rings, no direction        R 0.167  n_eff   78   nR^2   2.2  reject
#     4 bars 45 deg apart          R 0.060  n_eff  125   nR^2   0.5  reject
#     8 bars spread over 180 deg   R 0.019  n_eff  290   nR^2   0.1  reject
#
# Rings and lettering are 10x apart chance-corrected and 1.2x apart raw.
#
# alpha = 0.001 rather than a conventional 0.05: this decides whether to
# OVERRIDE per-stroke geometry that is already correct-by-construction, so the
# burden belongs on the override. It is not tuned to the fixtures -- every
# admit above clears 6.9 by at least 3x and every reject misses it by at
# least 3x, so nothing here sits near the line.
#
# The null was checked rather than assumed, because a significance test is only
# as good as what it tests against. Circular annuli -- genuinely isotropic --
# score R = 0.0081 and stay rejected at every scale tried, up to 48 of them at
# n_eff ~ 20,000 (nR^2 = 1.3 against the 6.9 critical value). So the raster
# contributes no meaningful directional bias of its own, and R does fall toward
# zero under a true null the way the test requires.
#
# What DOES rise with sample count is a real weak grain. Twelve buffered SQUARE
# rings clear the gate (R = 0.167 held constant, nR^2 8.6) where three do not.
# That is not a false positive: a rounded square has 45 deg corner arcs and
# genuinely leans diagonal. It is the honest behaviour of a significance test —
# enough evidence of a small effect is still evidence — and `_clamp_to_span`
# bounds what it can cost, since a stroke that cannot span the house angle
# keeps its own.
#
# KNOWN LIMIT: only two real lettering groups exist in this repo's fixtures,
# both from one logo. The honest validation is a run over Kent's own client
# artwork and `scratch_corpus/`, neither of which reaches a cloud container.
SATIN_ANGLE_RAYLEIGH_ALPHA = 0.001

# The doubled-angle test above is BLIND to block lettering whose horizontals
# balance its verticals, and that is most slab-serif and many sans block
# faces. In doubled-angle space a vertical stem votes at 180 deg and a
# horizontal bar at 0 deg, so the two families cancel exactly and R falls to
# the noise floor however much lettering there is. Measured on the Hotel
# Fremont wordmark (`testdata/photo/logo_hotel_fremont.webp` @ 80 mm,
# 2026-09-02): twelve slab-serif capitals with 112 mm of vertical and 44 mm
# of horizontal skeleton read R = 0.055 over n_eff = 1554, nR^2 = 4.7 against
# the 6.9 bar -- rejected, and every horizontal element then sewed at its own
# angle while the stems sewed at theirs. The same population mistake this
# module has now made four times: a gate correct on one population (stems-
# dominated lettering) applied to one it had never seen (lettering with two
# orthogonal families).
#
# Four-fold angle space sees exactly that structure: quadrupled, a vertical
# and a horizontal both vote at 0 deg, so two orthogonal families REINFORCE
# instead of cancelling, and the same Rayleigh test at the same alpha admits
# them (Hotel Fremont on raw skeleton steps: R4 = 0.185, nR4^2 = 53.1; on the
# resampled votes the reading actually ships on, 0.444 and 90 -- see
# SATIN_HOUSE_CHORD_PX). Four bars 45 deg apart cancel in both spaces. The
# test is tried SECOND, only when the doubled-angle test found nothing, so
# every cluster that was admitted before is admitted at the identical angle.
#
# KNOWN BLIND SPOT, named now so the fifth instance is not a surprise:
# lettering rich in DIAGONALS (A, V, W, X, K, M, N, Y, Z) votes at 180 deg in
# four-fold space and cancels the orthogonals, so a word like AVIATION can
# fail both readings and sew per-stroke. Nothing here has measured one.
#
# Which cross angle, once two orthogonal families are found? The bisector,
# `axis + SATIN_HOUSE_BISECTOR_DEG`. It is the only choice that holds one
# angle across the whole word: a cross perpendicular to the stems (0 deg on
# these letters) is 90 deg off every horizontal bar, beyond
# `stage6_satin.SATIN_HOUSE_MIN_SPAN_DEG`, so `_clamp_to_span` rotates it
# back to +/-45 deg with the SIGN decided by sub-degree tangent noise -- and
# the smoothing pass then sweeps each bar's crosses through 90 deg between
# flips. Rendered at house = 0 on Hotel Fremont the bars came out worse than
# with no house angle at all. At exactly 45 deg the cross sits at the span
# limit for BOTH families and nothing is clamped or flipped; a derived
# bisector a degree or two off (Hotel Fremont: 42.8-44.4) nudges the
# family it is further from back to the 45 deg limit, same sign, no flip, so
# the two families sew within ~2 deg of each other with no fan at the
# corners -- which is the "same angle for the whole word" the feature exists
# to give.
# 45 vs 135 is a convention, not a measurement; the constant is where to
# change it. Two orthogonal families have TWO bisectors, 90 deg apart, and the
# family axis the votes return is only defined mod 90 -- so "axis + 45" is
# not a convention at all: Hotel Fremont's stems read 89.4 deg and got 134.4,
# drone_render's read 0.1 and got 45.1, the same upright lettering sewing at
# mirror-image angles on sub-degree tangent noise. `_bisector_deg` takes the
# bisector nearer this constant instead, so upright text always gets the
# same slant whichever way its axis rounds. The one genuine ambiguity is
# lettering rotated by exactly 45 deg, whose bisectors are 0 and 90.
SATIN_HOUSE_BISECTOR_DEG = 45.0


def _bisector_deg(axis_deg: float) -> float:
    """The bisector of the two orthogonal stroke families at `axis_deg`
    (mod 90) that lies nearest `SATIN_HOUSE_BISECTOR_DEG`, on [0, 180)."""
    a, b = (axis_deg + 45.0) % 180.0, (axis_deg + 135.0) % 180.0

    def gap(x: float) -> float:
        return abs((x - SATIN_HOUSE_BISECTOR_DEG + 90.0) % 180.0 - 90.0)
    return a if gap(a) <= gap(b) else b

# The four-fold reading cannot vote on raw skeleton pixel steps the way the
# doubled reading does. An 8-connected walk only ever steps in the eight
# compass directions, and that staircase is itself four-fold symmetric: it
# cancels in doubled space (24 rasterised annuli read R = 0.008 there) and
# does NOT cancel in quadrupled space, where the same annuli read R4 = 0.160
# at exactly 45 deg and four bars 45 deg apart -- which should cancel -- read
# 0.527. Measured 2026-09-02. So the four-fold votes come from each chain
# resampled at `SATIN_HOUSE_CHORD_PX` pixels: over a four-pixel chord the
# walk can express directions between the compass points, and the grain
# collapses (annuli 0.051, the four bars 0.127) while two real orthogonal
# families keep their signal (Hotel Fremont's twelve capitals 0.444, its
# three tiny "THE" glyphs 0.657, six synthetic I-beams 0.903). Four is the
# shortest chord that does this; at three the annuli still read 0.064 and at
# six the real cases lose votes faster than the grain does. A raster
# resolution, not a fabric number. The doubled reading stays on raw steps so
# every angle it already derives is unchanged.
SATIN_HOUSE_CHORD_PX = 4.0

# What resampling leaves behind on a true circle is a residual grain of
# ~0.04-0.06 that a significance test alone cannot reject: it is small but
# SYSTEMATIC, so enough annuli make it "significant" (24 of them: nR4^2 =
# 8.0 against 6.9; 48 larger ones: 15.9). Under a biased null a
# significance test answers the wrong question, so the four-fold reading
# also asks for an EFFECT: R4 at least this much. 0.25 is five times the
# residual and under six-tenths of the weaker of the TWO real wordmarks
# measured (Hotel Fremont 0.444, its "THE" 0.657; one synthetic 0.903), so
# nothing measured sits near it; `test_the_four_fold_grain_stays_well_under_
# the_floor` pins the margin. It is a floor against a known bias in the
# null, and it is still a raw floor calibrated on two cases -- the diagonal
# blind spot above is where it would first be found wanting. The principled
# replacement is a test against the measured biased null, n_eff * max(0,
# R4 - grain)^2 >= critical, with the grain pinned by the annuli test; that
# changes the gate's shape and is Kent's call.
SATIN_HOUSE_FOURFOLD_MIN_R = 0.25


def _resample_chain(chain: list[tuple[float, float]],
                    step_mm: float) -> list[tuple[float, float]]:
    """`chain` re-sampled at `step_mm` intervals of arc, keeping both ends."""
    if step_mm <= 0.0 or len(chain) < 2:
        return chain
    out = [chain[0]]
    acc = 0.0
    for a, b in zip(chain, chain[1:]):
        d = math.dist(a, b)
        while d > 0.0 and acc + d >= step_mm:
            t = (step_mm - acc) / d
            a = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            out.append(a)
            d = math.dist(a, b)
            acc = 0.0
        acc += d
    if out[-1] != chain[-1]:
        out.append(chain[-1])
    return out


def _trim_ends(chain: list[tuple[float, float]],
               end_mm: float) -> list[tuple[float, float]]:
    """`chain` with `end_mm` of arc dropped from each end, or [] if that
    leaves nothing.

    A stroke's medial axis is not a clean centreline near its ENDS: a
    rectangle's is an I-beam, with 45 deg arms reaching to each corner, and
    `_merge_through_junctions` can weld one of those arms onto the main chain.
    Measured on a rotated-bar fixture (2026-08-27), that pulls the chain's
    direction toward the diagonal: a 6 mm bar yields 7.17 mm of skeleton whose
    chord reads 113.9 deg where the bar runs at 105. Worst-case bias over
    rotations and sizes was 8.2 deg untrimmed and 2.3 deg trimmed.

    `end_mm` is `_spur_len_px` in mm rather than a new number: that threshold
    already exists to decide how far a junction artifact reaches into this
    same skeleton. A short arm survives it (a 2.5 mm arm at 1 mm stroke keeps
    2.0 mm of its 3.3 mm), so trimming suppresses the artifact without
    silently discarding real short strokes.
    """
    if end_mm <= 0.0 or len(chain) < 2:
        return chain
    cum = [0.0]
    for a, b in zip(chain, chain[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    total = cum[-1]
    if total <= 2.0 * end_mm:
        return []
    i = bisect_left(cum, end_mm)
    j = bisect_left(cum, total - end_mm)
    return chain[i:j + 1] if j > i else []


def _house_chains(members: list[Region]) -> list[tuple[list[tuple[float, float]], float]]:
    """(end-trimmed skeleton chain in mm, raster px/mm) for every chain of
    every member -- the one vote set both readings below draw from.

    Fails open the way the rest of this module does: a member that will not
    field, or has no skeleton, contributes nothing instead of raising.
    """
    out: list[tuple[list[tuple[float, float]], float]] = []
    for r in members:
        field = build_shape_field(r.polygon)
        if field is None or not field.skel.any():
            continue
        # `_spur_len_px` in mm: how far the medial-axis end artifact reaches
        # into this chain. Each member gets its OWN field, and
        # `build_shape_field` normalises raster SIZE rather than resolution,
        # so px/mm differs per member -- the conversion is per member too.
        end_mm = _spur_len_px(field) / field.scale
        for chain in _skeleton_chains_mm(field):
            out.append((_trim_ends(chain, end_mm), field.scale))
    return out


def _fourfold_votes(chains: list[tuple[list[tuple[float, float]], float]],
                    chord_px: float = SATIN_HOUSE_CHORD_PX,
                    ) -> tuple[float, float, float] | None:
    """(R4, n_eff, stroke axis in degrees mod 90) over `chains` (from
    `_house_chains`) resampled at `chord_px` pixels -- 0 votes on the raw
    skeleton steps, which is how the grain was measured -- or None with
    nothing to vote on."""
    c4 = s4 = total = sq_weight = 0.0
    for chain, scale in chains:
        pts = _resample_chain(chain, chord_px / scale) if chord_px > 0 else chain
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy)
            if length <= 0.0:
                continue
            theta = math.atan2(dy, dx)
            c4 += length * math.cos(4.0 * theta)
            s4 += length * math.sin(4.0 * theta)
            total += length
            sq_weight += length * length
    if total <= 0.0:
        return None
    n_eff = (total * total) / sq_weight
    resultant = math.hypot(c4, s4) / total
    axis = math.degrees(0.25 * math.atan2(s4, c4)) % 90.0
    return resultant, n_eff, axis


def _cluster_house_angle_deg(members: list[Region]) -> float | None:
    """The dominant CROSS angle over a text cluster's strokes, in degrees on
    [0, 180), or None when the strokes carry no dominant direction.

    Two readings, tried in order. One dominant stroke direction (a row of
    stems, an arched word) gives the cross perpendicular to it. Failing
    that, two ORTHOGONAL families -- block lettering whose bars balance its
    stems, which cancel to nothing in the first reading -- give the cross
    that bisects them; see `SATIN_HOUSE_BISECTOR_DEG` for why the bisector
    and not the stems' perpendicular.

    Votes are the segments of every member's pruned, end-trimmed skeleton
    chains, weighted by length in mm. `_skeleton_chains_mm` prunes with the same
    threshold `extract_strokes` applies before building satin rails, so these
    are the strokes that will actually sew, not a different reading of the
    glyph.

    Fails open the way the rest of this module does: a member that will not
    field, or has no skeleton, contributes nothing instead of raising.
    """
    chains = _house_chains(members)
    c2 = s2 = total = sq_weight = 0.0
    for trimmed, _scale in chains:
        for (x0, y0), (x1, y1) in zip(trimmed, trimmed[1:]):
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy)
            if length <= 0.0:
                continue
            # Unit tangent, so (tx^2 - ty^2, 2 tx ty) is exactly
            # (cos 2t, sin 2t) -- see directionfield.region_direction.
            tx, ty = dx / length, dy / length
            c2 += length * (tx * tx - ty * ty)
            s2 += length * (2.0 * tx * ty)
            total += length
            sq_weight += length * length
    if total <= 0.0:
        return None
    c2 /= total
    s2 /= total
    # Rayleigh: n_eff * R^2 against -ln(alpha). `n_eff` is Kish's effective
    # sample size for weighted votes, (sum w)^2 / sum w^2 -- NOT the segment
    # count, which would credit a thousand hair-length raster steps as a
    # thousand independent observations of direction.
    n_eff = (total * total) / sq_weight if sq_weight > 0.0 else 0.0
    critical = -math.log(SATIN_ANGLE_RAYLEIGH_ALPHA)
    resultant = math.hypot(c2, s2)
    if n_eff * resultant * resultant >= critical:
        tangent = math.degrees(0.5 * math.atan2(s2, c2))
        return (tangent + 90.0) % 180.0
    # No single direction. Two orthogonal ones? Same test in four-fold space,
    # on grain-free votes, and with an effect-size floor -- see
    # SATIN_HOUSE_CHORD_PX and SATIN_HOUSE_FOURFOLD_MIN_R for both.
    votes = _fourfold_votes(chains)
    if votes is None:
        return None
    resultant4, n_eff4, axis = votes
    if resultant4 < SATIN_HOUSE_FOURFOLD_MIN_R:
        return None
    if n_eff4 * resultant4 * resultant4 < critical:
        return None
    return _bisector_deg(axis)


def set_lettering_house_angle(regions: list[Region], p: Prep) -> None:
    """Post-regularization pass: give every member of one line of lettering
    ONE house cross angle, so its letters agree instead of each following its
    own spine tangent (`satin_angle_deg` in `Region.meta`).

    Groups with `_lettering_groups`, NOT with `detect_text_clusters`'
    `text_cluster_id`. That was the original wiring and it made this pass
    inert on real artwork -- see `_lettering_groups` for the two gates that
    empty its candidate set on an ordinary logo.

    `p` is accepted, not read, matching `detect_text_clusters` and
    `regularize_text_clusters` for the same reason: a future revision that
    needs `Prep` should not have to change every call site again.

    Runs AFTER `regularize_text_clusters` because that pass redraws member
    polygons, and the angle has to describe the strokes that will sew rather
    than the ones vectorization happened to leave behind.

    Fails open throughout, same discipline as the passes above: a cluster
    whose strokes carry no dominant direction gets NO new meta key at all,
    and absent means "per-stroke tangent, exactly as before". An angle a
    caller already set on a shape is left alone -- per-shape intent beats a
    derived default, the same precedence `config.satin_angle_deg`'s own
    comment describes.

    NOT carried forward between generations, and deliberately so.
    `config.satin_angle_deg`'s comment says the per-shape key rides
    `regions.match_and_carry`'s deterministic-id carry-forward; it does not --
    `satin_angle_deg` is absent from that key tuple (checked 2026-08-27), and
    nothing outside this pass writes it, so there is no operator intent to
    preserve yet. Adding it there would be actively wrong while this pass is
    the only writer: carry-forward fires only when the key is MISSING from the
    current generation, which is exactly the case where new artwork stopped
    being coherent enough to angle -- it would resurrect the previous
    generation's angle for a word that no longer supports one. If a review
    screen ever lets a user set this per shape, that is when the key earns its
    place in the tuple, and this pass should skip shapes carrying an
    operator-set value rather than a derived one.
    """
    for members in _lettering_groups(regions):
        angle = _cluster_house_angle_deg(members)
        if angle is None:
            continue
        for r in members:
            r.meta.setdefault("satin_angle_deg", angle)
            # The SAME angle on the fill tier, because a word does not get to
            # pick its tier: `classify_ribbon` routes each letter on its own
            # width, so one word's glyphs routinely split across satin and
            # fill. Measured on Kent's Becker logo (2026-08-27), 7 of its 11
            # lettering regions sew as FILL, and `best_fill_angle_deg` chose
            # each one's rows by minimising THAT SHAPE's column count -- which
            # put two adjacent, near-identical capitals at 22.5 and 90.0 deg.
            # That is the same "each shape chooses in isolation" disease the
            # satin half of this pass exists to cure, one tier over, and it is
            # the half his complaint actually names.
            #
            # One value for both tiers: satin's is a CROSS angle and fill's a
            # ROW angle, but both describe the direction thread is laid across
            # the glyph, so matching them is what makes a word read as one
            # piece whichever tier each letter took.
            r.meta.setdefault("fill_angle_deg", angle)

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
