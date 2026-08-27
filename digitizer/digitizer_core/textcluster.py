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
from .directionfield import COHERENCE_FALLBACK_MIN
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

# Below this the strokes genuinely disagree and there is no house angle to
# find -- a circular monogram, a script face, a cluster of dingbats. Forcing
# one there would be worse than the per-stroke tangent it replaces, so the
# pass writes nothing and the shape keeps today's behaviour. Reused from
# `directionfield`, whose `use_house_angle` gates the identical question
# ("is this dominant direction real, or noise") on the identical statistic.
SATIN_ANGLE_MIN_COHERENCE = COHERENCE_FALLBACK_MIN


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


def _cluster_house_angle_deg(members: list[Region]) -> float | None:
    """The dominant CROSS angle over a text cluster's strokes, in degrees on
    [0, 180), or None when the strokes carry no dominant direction.

    Votes are the segments of every member's pruned, end-trimmed skeleton
    chains, weighted by length in mm. `_skeleton_chains_mm` prunes with the same
    threshold `extract_strokes` applies before building satin rails, so these
    are the strokes that will actually sew, not a different reading of the
    glyph.

    Fails open the way the rest of this module does: a member that will not
    field, or has no skeleton, contributes nothing instead of raising.
    """
    c2 = s2 = total = 0.0
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
            trimmed = _trim_ends(chain, end_mm)
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
    if total <= 0.0:
        return None
    c2 /= total
    s2 /= total
    if math.hypot(c2, s2) < SATIN_ANGLE_MIN_COHERENCE:
        return None
    tangent = math.degrees(0.5 * math.atan2(s2, c2))
    return (tangent + 90.0) % 180.0


def set_text_cluster_satin_angle(regions: list[Region], p: Prep) -> None:
    """Post-regularization pass: give every member of a detected word ONE
    house cross angle, so its letters agree instead of each following its own
    spine tangent (`satin_angle_deg` in `Region.meta`).

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
    by_cluster: dict[str, list[Region]] = {}
    for r in regions:
        cluster_id = r.meta.get("text_cluster_id")
        if cluster_id is not None:
            by_cluster.setdefault(cluster_id, []).append(r)

    for members in by_cluster.values():
        angle = _cluster_house_angle_deg(members)
        if angle is None:
            continue
        for r in members:
            r.meta.setdefault("satin_angle_deg", angle)

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
