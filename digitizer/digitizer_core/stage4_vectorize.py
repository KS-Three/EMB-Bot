"""Stage 4 — masks to simplified mm-space polygons with holes.

Output coordinate system is the JSON contract's, pinned here so nothing
downstream has to guess:
    millimetres, floats, origin at the ARTWORK bbox center, **y-axis DOWN**.
Image space is already y-down, so no flip happens here. EMB-Bot's own engine
is +y UP, which makes the browser boundary the one place a mirror can creep
in — that conversion belongs to the integration adapter (step 10) and has a
golden test of its own.

Each RegionMask is a single connected component, so its contour hierarchy is
exactly one outer shell plus its holes (a same-color island inside a hole is
not connected to the shell, so it arrives as its own RegionMask). RETR_CCOMP
is therefore sufficient; nested-shell handling is not needed at this depth.
"""
from __future__ import annotations

import cv2
import numpy as np
from shapely.geometry import Polygon
from shapely.validation import make_valid

from . import machine
from .config import PipelineConfig
from .regions import Region, assign_shape_ids
from .stage1_prep import Prep
from .stage3_segment import RegionMask
from .threads import chart_for, rgb_to_lab
from .warnings_codes import THREAD_RESNAPPED_AFTER_DRIFT, warn

try:  # skimage's own spelling moved between versions; match the rest of the pkg
    from skimage.color import deltaE_ciede2000
except ImportError:  # pragma: no cover - defensive, matches stage2's own import
    from skimage.color.delta_e import deltaE_ciede2000

# A shape smaller than this cannot support a colour estimate worth re-snapping
# on, and at this size it is the run tier's problem, not the fill's. Measured
# against the fixture this fix was traced on: the drifted sliver there covers
# 1,990 px, comfortably clear.
THREAD_REVALIDATE_MIN_PX = 200

# Re-snap only when the newly-measured colour is at least this much closer to a
# different spool than to the one already assigned. Guards against churning
# thread assignments (and every golden) by fractions of a dE00 — this rule
# exists for the 20-plus dE00 desync the root-cause doc traced, not for the
# ordinary sub-unit wobble simplification puts on every shape in every design.
THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = 3.0

# Cap on how many of a region's pixels are scored against the chart. The score
# is a median over pixels, which converges long before a real region runs out
# of them, and the work is (samples x ~400 spools) per region.
THREAD_REVALIDATE_SAMPLE_PX = 256

# Mirrored, verbatim, from stage7_sequence.PHOTO_CLASSES — the same lockstep
# arrangement stage6_satin._PHOTO_CLASSES already keeps (there because the
# import would cycle; here because this early-stage module importing stage 7
# would drag every fill tier in behind one tuple). A membership change in
# stage7_sequence must land here too; tests/test_thread_revalidate_palette.py
# pins the lockstep so drift fails loud instead of quietly unbinding the
# resnap for a new photo class.
_PHOTO_CLASSES = ("photo_subject", "photo_scene")


def _to_mm(pts: np.ndarray, cx: float, cy: float, px_per_mm: float) -> np.ndarray:
    out = pts.astype(np.float64)
    out[:, 0] = (out[:, 0] - cx) / px_per_mm
    out[:, 1] = (out[:, 1] - cy) / px_per_mm
    return out


def _polygon_parts(geom) -> list[Polygon]:
    """Every Polygon inside `geom`, however deeply shapely nested it.

    `make_valid` on a self-intersecting ring does not return one shape of one
    type. Repairing a simple figure-eight gives a bare `MultiPolygon` whose
    members ARE polygons; repairing a ring that also sheds a dangling edge
    gives a `GeometryCollection` whose members are a `MultiPolygon` **and** a
    `LineString` — the polygons are one level deeper, and a flat
    `geom_type == "Polygon"` scan over the collection finds NONE of them.

    That is not hypothetical. On `owl_kent.jpg`, three masks self-intersect
    after `approxPolyDP`: the body repairs to a MultiPolygon and survives,
    while two regions of **944 mm² and 718 mm²** — 20% and 15% of the whole
    design — repair to GeometryCollections, scan as "no polygon parts", and
    were dropped outright. They took their thread colours with them
    (`EMPTY_THREAD_LAYER`) and left bare fabric in the owl's lower body.
    Recursing is the whole fix.
    """
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if hasattr(geom, "geoms"):
        return [q for g in geom.geoms for q in _polygon_parts(g)]
    return []


def vectorize(
    region_masks: list[RegionMask],
    thread_indices: list[int],
    p: Prep,
    cfg: PipelineConfig,
) -> tuple[list[Region], list[float]]:
    """-> (regions, dropped_areas_mm2).

    A mask can still vanish here: simplification collapses a sliver below
    three points or below a sewable area. Those drops are RETURNED, never
    swallowed — the pipeline folds them into the same warning stage 3 uses,
    because a shape disappearing with no trace is the failure mode that
    makes an auto-digitizer untrustworthy.

    Masks below the min-detail area (stage 3's run-tier rescues) get two
    special treatments, both measured on the benchmark subline (1.9 mm
    letters at 90 mm target width):

    - **A sub-pixel simplify eps.** The stage tolerance is sized for shapes
      with room to spare — 0.2 mm is 3 px at benchmark resolution, and on
      29 px glyphs it deleted both "I"s outright and mangled the rest into
      "ENTERPR SES NC". A sub-detail shape's features ARE tolerance-sized,
      so it gets the 0.5 px floor: de-staircasing only, no simplification.
    - **The run-tier floor instead of the sliver floor.** The sliver floor
      (min detail squared, quartered) sits above the thinnest real letter
      (0.56 vs 0.50 mm²). What the run tier needs is exactly what it can
      sew: a loop the bean run can close, on a shape at least the thread's
      own visual weight. Anything under that is still noted as dropped.
    """
    chart = chart_for(cfg)
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    eps_px = max(0.5, cfg.simplify_tol_mm * p.px_per_mm)
    min_area_mm2 = (cfg.min_detail_mm ** 2) * 0.25  # a sliver after simplification
    min_detail_px2 = (cfg.min_detail_mm * p.px_per_mm) ** 2

    regions: list[Region] = []
    dropped: list[float] = []

    def note_drop(rm: RegionMask) -> None:
        dropped.append(float(rm.area) / (p.px_per_mm ** 2))

    for rm in region_masks:
        # Trace the CROP, not a frame-sized mask (2026-08-24). The one-pixel
        # background pad reproduces the full-frame neighbourhood exactly: a
        # crop is bbox-tight, so every border row and column carries set
        # pixels, and tracing it bare would lean on findContours' own
        # out-of-image convention instead of on a real background ring. The
        # `offset` puts contours straight back into frame coordinates
        # (offset is (x, y) where origin is (y, x)), so everything
        # downstream — `_to_mm`, the hole hierarchy, the area floors — is
        # unchanged.
        y0, x0 = rm.origin
        padded = np.zeros((rm.crop.shape[0] + 2, rm.crop.shape[1] + 2), np.uint8)
        padded[1:-1, 1:-1] = rm.crop
        contours, hierarchy = cv2.findContours(
            padded, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE,
            offset=(x0 - 1, y0 - 1),
        )
        if not contours or hierarchy is None:
            note_drop(rm)
            continue
        hier = hierarchy[0]

        # Outer contours have no parent; each may own holes as children.
        outers = [i for i in range(len(contours)) if hier[i][3] == -1]
        if not outers:
            note_drop(rm)
            continue
        # A single connected component yields one meaningful shell; if
        # simplification splintered it, keep the largest.
        outer = max(outers, key=lambda i: cv2.contourArea(contours[i]))

        # Sub-detail masks are simplified at the floor only — see docstring.
        sub_detail = (cfg.small_shape_rescue
                      and cv2.contourArea(contours[outer]) < min_detail_px2)
        eps = 0.5 if sub_detail else eps_px

        shell_px = cv2.approxPolyDP(contours[outer], eps, True).reshape(-1, 2)
        if len(shell_px) < 3:
            note_drop(rm)
            continue
        shell = _to_mm(shell_px, cx, cy, p.px_per_mm)

        holes = []
        for i in range(len(contours)):
            if hier[i][3] != outer:
                continue
            h_px = cv2.approxPolyDP(contours[i], eps, True).reshape(-1, 2)
            if len(h_px) < 3:
                continue
            ring = _to_mm(h_px, cx, cy, p.px_per_mm)
            if Polygon(ring).area >= min_area_mm2:
                holes.append(ring)

        poly = Polygon(shell, holes)
        # A self-intersecting ring does not repair into ONE shape. Where the
        # boundary crossed itself the repair pinches the mask into several
        # disjoint polygons — all of them the same mask, the same colour, the
        # same artwork. Keeping only the largest and discarding the rest is
        # what left bare fabric in the owl's lower body: the body mask repairs
        # to 4 parts, and the 30 mm² piece that is NOT the largest was thrown
        # away, so nothing ever sewed there. Every part that clears the same
        # sewable floor a whole region must clear is kept, each as its own
        # region — which is what they now are.
        parts = [poly] if poly.is_valid else _polygon_parts(make_valid(poly))

        thread = chart[thread_indices[rm.layer]]
        kept = 0
        for part in parts:
            if part.is_empty:
                continue
            if part.area < min_area_mm2:
                # The run-tier floor, now on real geometry: stage 3's proxy was
                # a lower bound, so this is the authoritative test of whether
                # the bean run has a sewable loop and the shape outweighs the
                # thread.
                rescueable = (sub_detail
                              and part.area >= machine.RUN_MIN_AREA_MM2
                              and part.exterior.length >= machine.RUN_MIN_LOOP_MM)
                if not rescueable:
                    continue
            meta = {"layer": rm.layer}
            if sub_detail:
                meta["rescued_small_shape"] = True
            regions.append(
                Region(
                    shape_id="",
                    polygon=part,
                    thread_index=thread_indices[rm.layer],
                    thread_number=thread.number,
                    area_mm2=float(part.area),
                    source=rm.source,
                    meta=meta,
                )
            )
            kept += 1
        if not kept:
            note_drop(rm)
            continue

    assign_shape_ids(regions)
    # Stable output order: largest first within a layer, layers in sew order.
    regions.sort(key=lambda r: (r.meta["layer"], -r.area_mm2, r.shape_id))
    return regions, dropped


# Both the region's own footprint and the enclosed-mask component it best
# matches must be THIS covered by the overlap before a tag is applied.
# Picked, not derived — see `tag_enclosed_background`'s docstring for why
# 0.6 and not something stricter or looser.
ENCLOSED_TAG_OVERLAP_THRESHOLD = 0.6


def _region_footprint(r: Region, shape: tuple[int, int], cx: float, cy: float,
                      px_per_mm: float) -> np.ndarray:
    """The pixel mask a Region's FINAL polygon actually covers — exterior
    filled, interiors punched back out. The mm->px transform is the exact
    inverse of `_to_mm`'s, and the same one `tag_enclosed_background` uses."""
    h, w = shape

    def to_px(coords) -> np.ndarray:
        arr = np.asarray(coords, dtype=np.float64)
        px = np.empty_like(arr)
        px[:, 0] = arr[:, 0] * px_per_mm + cx
        px[:, 1] = arr[:, 1] * px_per_mm + cy
        return np.round(px).astype(np.int32)

    out = np.zeros((h, w), np.uint8)
    cv2.fillPoly(out, [to_px(r.polygon.exterior.coords)], 1)
    for interior in r.polygon.interiors:
        cv2.fillPoly(out, [to_px(interior.coords)], 0)
    return out.astype(bool)


def _sample_lab(lab: np.ndarray) -> np.ndarray:
    """At most `THREAD_REVALIDATE_SAMPLE_PX` of a region's Lab pixels, chosen
    deterministically. Evenly spaced over the pixel index, the same idiom
    `stage2_quantize._kmeans` uses for its own fit sample and for the same
    reason: a seeded RNG is one more thing that can silently move a golden,
    and an even stride over a region's raster order is already spatially
    spread. The cap is what keeps this rule's cost flat — the scoring below
    is (samples x chart), and the chart is ~400 spools."""
    if len(lab) <= THREAD_REVALIDATE_SAMPLE_PX:
        return lab
    idx = np.linspace(0, len(lab) - 1, THREAD_REVALIDATE_SAMPLE_PX).astype(np.int64)
    return lab[idx]


def revalidate_threads(regions: list[Region], p: Prep,
                       cfg: PipelineConfig, *,
                       palette_indices: list[int] | None = None,
                       design_class: str = "flat") -> list[dict]:
    """Re-check every shape's thread against the pixels its FINAL polygon
    covers, and re-snap the ones that drifted. -> warnings.

    **The defect** (`docs/photo-quality-root-cause-2026-08-11.md`, fix #6.3,
    traced on `testdata/photo/repro_gradient_white_icon.png`): a thread is
    chosen at stage 2, from the pixels a region occupied THEN. Simplification
    here moves the boundary — `cfg.simplify_tol_mm` is 0.2mm, which is a
    rounding error on a 20mm shape and a large fraction of a 1.3mm-wide one.
    On that fixture a ~1.95 x 11.7mm sliver was measured at segmentation time
    as a genuine pinkish-white anti-alias blend, Lab (80.2, 25.1, 4.1), and
    `select_palette` matched it well (Azalea Pink, near-zero excess). By the
    time it was a simplified polygon it sat mostly over the solid white icon
    interior instead: re-sampling its final 1,990 pixels gives median
    (255, 255, 255), and the design ships a hot pink sliver through white
    linework at dE00 23.9 — the worst thread match in the whole corpus.
    Nothing between stage 2 and the machine ever re-asked the question.

    This is the missing re-ask. It is deliberately a RE-MATCH, not a geometry
    change: the polygon that came out of simplification is the one that sews
    well, so the honest correction is to give it the thread it now needs,
    not to push the outline back onto colour it no longer covers.

    Two gates, both to keep this from firing as noise:

    * `THREAD_REVALIDATE_MIN_PX` — a handful of pixels cannot support a
      colour estimate, and a shape that small is the run tier's problem.
    * `THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00` — re-snap only when the new
      spool is meaningfully better than the one already assigned. Without
      it this would churn thread assignments by fractions of a dE00 across
      the whole corpus for no visible gain, and every golden with it.

    **Photo classes re-snap WITHIN the selected palette** (2026-08-23).
    `select_palette` exists precisely to cap a photo's spool count, and this
    pass was the larger of its two escape hatches: the argmin here ran over
    the FULL chart, so every re-snap on the photo route pulled a brand-new
    spool into the design — measured live on a real portrait
    (`baby_deck_laugh`, `forced_class="photo_subject"`): 45 shapes resnapped
    onto 19 spools outside the 12-spool palette, and the design sewed 55
    block-level threads / 92 machine colour stops off a 12-cone colour list.
    When `design_class` is a photo class and `palette_indices` (the caller's
    `q.thread_indices`) is non-empty, the argmin is masked to that subset:
    the drifted shape still gets the best thread for the pixels it now
    covers, chosen from the spools the operator will actually load. Every
    other class keeps the unrestricted chart argmin, byte-identical to
    before this parameter existed — deliberately. The phase-4 spec pins the
    flat and gradient lanes byte-for-byte (their golden suites enforce it),
    and fix #6.3's own motivating case (`repro_gradient_white_icon.png`) is
    gradient-lane: nothing guarantees a gradient drift target sits inside
    the selected palette, and the escape was never the measured defect there
    (the same four portraits on the default/gradient route: 8/7/8/0 resnaps
    and 0-6 out-of-palette spools, vs 53/47/45/19 resnaps and 9-22 on the
    photo route). For honesty's sake: on the repro fixture itself the resnap
    target (`0015 White`) happens to sit INSIDE its own 6-spool palette
    (measured 2026-08-23), so that one fixture would survive binding — the
    byte-identity contract, not the fixture, is what makes the class gate
    load-bearing.

    **The error is measured PER PIXEL, and that choice is the whole fix.**
    A drifted sliver is bimodal by construction — part of it still sits on the
    colour its thread was chosen from, part has moved onto something else — and
    every summary statistic that collapses it to one colour first will hide
    that. Measured on the traced shape (2,333 px, thread `2560 Azalea Pink`):

        per-pixel dE00 to its thread   p10 23.9  p50 23.9  p90 25.2
        59.5% of its pixels are near-white (all channels >= 235)
        mean RGB (247, 183, 193)   -> dE00  5.54   <- almost no pixel is this
        median RGB (255, 255, 255) -> dE00 23.87

    The mean says this shape is fine. The pixels say a hot pink thread is
    sewing over white linework for most of its length. Taking the MEDIAN OF
    THE PER-PIXEL dE00 keeps the answer on real pixels and is what this
    function scores with — the same trap, in the same direction, that the
    root-cause doc documented for preflight's thread-match instrument
    (independent per-channel medians over a pooled population, producing a
    colour no actual pixel carries — fixed 2026-08-11: preflight now scores
    per region with this same estimator, `preflight._region_color_errors`).
    An earlier build of this function used
    the mean and scored the traced shape at 5.54, i.e. reported the defect it
    exists to find as absent.
    """
    if not regions:
        return []
    chart = chart_for(cfg)
    # The photo-route palette binding (docstring above). `None` — every
    # non-photo class, and any caller that passes no palette — is the
    # unrestricted chart argmin this function has always run.
    allowed: np.ndarray | None = None
    if design_class in _PHOTO_CLASSES and palette_indices is not None \
            and len(palette_indices) > 0:
        allowed = np.unique(np.asarray(list(palette_indices), dtype=np.int64))
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    shape = p.rgb.shape[:2]
    flat_lab = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(*shape, 3)

    resnapped: list[str] = []
    worst_before = worst_after = 0.0
    for r in regions:
        # An enclosed-background shape is unstitched by default and its
        # colour is the BACKGROUND's by definition — re-matching it to the
        # bg-coloured pixels it covers is both a no-op and a category error.
        if r.meta.get("enclosed_background"):
            continue
        fp = _region_footprint(r, shape, cx, cy, p.px_per_mm)
        n = int(fp.sum())
        if n < THREAD_REVALIDATE_MIN_PX:
            continue
        samples = _sample_lab(flat_lab[fp])
        # (S, K) — every sampled pixel against every spool in the chart, then
        # the median down the pixel axis: one honest error per spool.
        per_spool = np.median(
            deltaE_ciede2000(samples[:, None, :], chart.lab[None, :, :]), axis=0
        )
        before = float(per_spool[r.thread_index])
        best = (int(np.argmin(per_spool)) if allowed is None
                else int(allowed[np.argmin(per_spool[allowed])]))
        if best == r.thread_index:
            continue
        after = float(per_spool[best])
        if before - after < THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00:
            continue
        r.thread_index = best
        r.thread_number = chart[best].number
        r.meta["thread_resnapped_de00"] = round(before, 2)
        resnapped.append(r.shape_id)
        worst_before = max(worst_before, before)
        worst_after = max(worst_after, after)

    if not resnapped:
        return []
    return [warn(
        THREAD_RESNAPPED_AFTER_DRIFT,
        f"{len(resnapped)} shape(s) had moved off the colour their thread was "
        f"chosen from during outline simplification (worst dE00 "
        f"{worst_before:.1f}); each was re-matched to the colour it now covers "
        f"(worst dE00 now {worst_after:.1f}).",
        count=len(resnapped),
        ids=sorted(resnapped),
        worst_before_de00=round(worst_before, 2),
        worst_after_de00=round(worst_after, 2),
    )]


def tag_enclosed_background(regions: list[Region], p: Prep) -> None:
    """Post-vectorization pass: mark `region.meta["enclosed_background"]`
    True for every Region that is (nearly) the same shape as one connected
    component of `Prep.enclosed_mask` — the bg-colored-but-not-border-
    connected pixels stage 1 found, before quantization ever ran.

    Why per-component, not "does this region touch the mask at all": stage
    1's `enclosed` mask is raw color + connectivity, computed BEFORE
    quantization; stage 2 re-clusters and stage 3 re-segments independently,
    so there is no structural guarantee that one `enclosed` connected
    component maps 1:1 onto one final Region (anti-aliasing, the majority
    filter, and small-region absorption can all nudge the boundary a few
    pixels either way, or occasionally split/merge a sliver). Simply asking
    "does this region overlap the mask at all" would tag an ordinary
    foreground shape that merely grazes an enclosed patch along one edge, so
    this measures, for the connected component the region overlaps most:

        overlap / region_footprint_area  -- is the region MOSTLY the mask?
        overlap / component_area         -- is the component MOSTLY this region?

    and only tags when the SAME component clears both ratios at
    `ENCLOSED_TAG_OVERLAP_THRESHOLD`. That rules out a small corner-graze
    (fails the first ratio) and a region that happens to swallow one small
    enclosed sliver among a lot of unrelated area (fails the second).

    THRESHOLD = 0.6, chosen empirically against this slice's two fixtures
    (`tests/test_stages.py`'s ring-hole donut and
    `testdata/photo/repro_gradient_white_icon.png`'s icon linework): a true
    match scores well above 0.9 on both axes on both fixtures (simplify's
    sub-pixel contour wobble is the only source of disagreement, and it is
    small), so 0.6 leaves wide headroom before a real match would ever miss
    it, while still being far enough above "touches along one edge" (which
    scores near 0) to refuse an accidental graze. Ambiguous cases — below
    threshold on either axis — fail OPEN: untagged, sewn by default. A
    tagger that silently hides a shape it mis-identified is worse than the
    original bug (a hole nobody can review), so uncertainty always resolves
    to "keep stitching it".
    """
    mask = p.enclosed_mask
    if mask is None or not mask.any():
        return
    h, w = mask.shape
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    px_per_mm = p.px_per_mm

    n_comp, comp_labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    comp_area = np.bincount(comp_labels.ravel(), minlength=n_comp)

    def _mm_ring_to_px(coords) -> np.ndarray:
        arr = np.asarray(coords, dtype=np.float64)
        px = np.empty_like(arr)
        px[:, 0] = arr[:, 0] * px_per_mm + cx
        px[:, 1] = arr[:, 1] * px_per_mm + cy
        return np.round(px).astype(np.int32)

    for r in regions:
        footprint = np.zeros((h, w), np.uint8)
        cv2.fillPoly(footprint, [_mm_ring_to_px(r.polygon.exterior.coords)], 1)
        for interior in r.polygon.interiors:
            cv2.fillPoly(footprint, [_mm_ring_to_px(interior.coords)], 0)
        region_area = int(footprint.sum())
        if region_area == 0:
            continue

        footprint_bool = footprint.astype(bool)
        touched = footprint_bool & (comp_labels > 0)
        if not touched.any():
            continue

        for lbl in np.unique(comp_labels[touched]):
            inter = int(np.count_nonzero(touched & (comp_labels == lbl)))
            region_ratio = inter / region_area
            comp_ratio = inter / int(comp_area[lbl])
            if (region_ratio >= ENCLOSED_TAG_OVERLAP_THRESHOLD
                    and comp_ratio >= ENCLOSED_TAG_OVERLAP_THRESHOLD):
                r.meta["enclosed_background"] = True
                # A hole found via ALPHA has no colour of its own: the RGB under
                # the transparency is whatever the exporter flattened there, and
                # on the Becker Marine artwork that is the enclosing ring's own
                # near-black — so switching the hole on sews a solid black letter
                # where the pro sewed a Gray interior inside a Black keyline
                # (docs/enclosed-background-verdict-2026-08-15.md §5.2). A hole
                # found by COLOUR is genuinely that colour and keeps it, which is
                # why `logo_whitebg.png`'s White hole is untouched here.
                #
                # This deliberately does NOT change the thread. Substituting some
                # other colour would be an equally arbitrary guess; the point is
                # that the inherited one stops reading as a decision.
                if p.bg_from_alpha:
                    r.meta["enclosed_colour_unknown"] = True
                break
