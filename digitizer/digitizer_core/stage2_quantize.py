"""Stage 2 — Lab quantization, anti-alias handling, thread snapping.

Deliberate deviations from the blueprint's sketch, both for determinism:

1. **No elbow-based auto-k.** An elbow rule on near-tied inertia flips k on
   trivial input noise, and every golden in the suite would move with it.
   Instead: cluster at k = max_colors, then DISCOVER the real color count by
   merging — first clusters within `merge_delta_e` of each other (one flat
   color that k-means split), then clusters that snap to the same spool.
   Flat art has a true color count; merging finds it stably.

2. **Own k-means, not cv2.kmeans.** cv2's RNG behavior across versions/thread
   counts is not a determinism guarantee we control. This one seeds
   numpy's Generator explicitly, fits on a deterministic stride sample, and
   assigns in chunks — same input, same labels, every run.

Anti-alias handling: boundary pixels are blends of two real colors. A
majority filter reassigns them to a true neighbor, then any cluster that is
BOTH overwhelmingly edge pixels AND colorimetrically between two other
cluster centers is dissolved as a phantom blend. The collinearity test
matters: an edge-fraction test alone would also delete legitimately tiny
real-color features.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .config import PipelineConfig
from .stage1_prep import Prep
from .threads import chart_for, rgb_to_lab
from .warnings_codes import COLOR_CAP_APPLIED, warn

FIT_SAMPLE_MAX = 40_000


@dataclass
class Quant:
    labels: np.ndarray            # (H, W) int32; -1 = background
    thread_indices: list[int]     # label value -> index into threads.CHART
    cluster_rgb: np.ndarray       # (K, 3) float, the pre-snap cluster colors
    warnings: list[dict] = field(default_factory=list)
    # The FULL `select_palette` medoid set (chart indices), set ONLY when
    # stage-2 shade demand was fed into the selection
    # (cfg.shade_palette_demand, stage2_photo_segment.kept_masks_to_quant) —
    # None on every other path, this dataclass's whole life before the field
    # existed. It exists because demand can select ANCHOR spools no region's
    # own mean snaps to: those never enter `thread_indices` (label-mapped
    # spools only), yet they are precisely the spools the shade-palette bind
    # (stage7_sequence) must offer `_shade_layers`, so they ride here ->
    # Generation.quant_palette_spools -> PipelineResult.palette_spools.
    palette_spools: list[int] | None = None
    # The labels the lightness read of the thin population owns
    # (`thin_ink.find_dark_thin_ink`, `cfg.keep_dark_thin_strokes`), so the
    # colour cap can keep a dark stroke off its own ground's thread
    # (`stage4_vectorize.enforce_color_cap`). None on every other path.
    dark_ink_labels: frozenset[int] | None = None
    # `cfg.flat_page_fringe_exclude`: the figure's page-edge blend pixels
    # (`page_fringe`), so stage 3's chain rescue can tell a fringe ring from
    # content. None with the flag off, on every other path, and for an alpha
    # cut-out.
    page_fringe: np.ndarray | None = None


def _nearest_source(src: np.ndarray) -> np.ndarray:
    """(H, W) int64: the flat index of the nearest True pixel of `src` for
    every pixel. Euclidean distance transform with pixel labels; ties break
    the way OpenCV's scan does, which is deterministic. `src` must have a
    True pixel."""
    zero_idx = np.flatnonzero(src.reshape(-1))
    _dt, lbl = cv2.distanceTransformWithLabels(
        (~src).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
    )
    return zero_idx[lbl - 1]


def page_fringe(p: Prep, cfg: PipelineConfig, base_valid: np.ndarray) -> np.ndarray | None:
    """Figure pixels in the anti-alias ramp against the page
    (`cfg.flat_page_fringe_exclude`): within `cfg.flat_page_fringe_px` of
    `p.bg_mask` AND a blend of the page colour and the interior colour beside
    them. A blend = strictly between the two (0.15 < t < 0.85 along the Lab
    segment page -> nearest interior pixel) and within `cfg.merge_delta_e` of
    that segment: the phantom-blend test stage 2 applies to whole clusters,
    read per pixel. A band pixel that is NOT a blend (a light keyline: its
    colour is its own, off the chord) keeps its vote. None when nothing
    applies: an alpha cut-out has no page fringe, nor does an image with no
    page, no interior, or no page colour to blend with.
    """
    if p.bg_from_alpha or p.bg_edge_rgb is None:
        return None
    f_px = int(cfg.flat_page_fringe_px)
    # A source edge's one-pixel anti-alias ramp is `upscale` working pixels
    # wide once stage 1 has enlarged the raster (Pooh at 80 mm: x2.7; a 100 px
    # synthetic at 40 mm: x4), plus one for the resampling's own spread.
    # `flat_page_fringe_px` is the floor, so a source at the grid is unchanged.
    if p.input_px_per_mm and p.px_per_mm > p.input_px_per_mm:
        f_px = max(f_px, int(np.ceil(p.px_per_mm / p.input_px_per_mm)) + 1)
    bg = p.bg_mask
    if f_px < 1 or not bg.any():
        return None
    dist = cv2.distanceTransform((~bg).astype(np.uint8), cv2.DIST_L2, 5)
    band = base_valid & (dist <= f_px)
    interior = base_valid & ~band
    if not band.any() or not interior.any():
        return None
    h, w = bg.shape
    by, bx = np.nonzero(band)
    flat_rgb = p.rgb.reshape(-1, 3)
    c = rgb_to_lab(flat_rgb[by * w + bx])
    # The PAGE's colour is what the page is, the median of its pixels:
    # `bg_edge_rgb` averages the ring beside the figure, which the ramp has
    # already pulled toward the figure (231 against a 244 page on a synthetic
    # circle), and a pixel the ramp overshot past the page then read as far
    # from it.
    page = rgb_to_lab(np.median(p.rgb[bg].astype(np.float64), axis=0).reshape(1, 3))[0]
    # The colour the ramp climbs TOWARD: of the valid pixels within `reach`
    # that lie farther from the page than this one (across the edge, not
    # along it), the one farthest from the page in colour. The nearest
    # interior pixel would be wrong for a thin dark outline inside the band:
    # the ramp page -> outline is a chord to the OUTLINE, not to the fill
    # behind it. A pixel on the outline's inner blend finds the fill, the
    # chord misses it, and it keeps its vote (this flag leaves that edge to
    # the phantom dissolve).
    reach = f_px + 2
    dist_b = dist[by, bx]
    best_d = np.full(len(by), -1.0)
    inner = c.copy()
    lab_img = rgb_to_lab(flat_rgb).reshape(h, w, 3)
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            if dy * dy + dx * dx > reach * reach or (dy == 0 and dx == 0):
                continue
            yy, xx = by + dy, bx + dx
            ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            yy, xx = np.where(ok, yy, 0), np.where(ok, xx, 0)
            ok &= base_valid[yy, xx] & (dist[yy, xx] >= dist_b + 0.9)
            cand = lab_img[yy, xx]
            dd = np.where(ok, np.linalg.norm(cand - page, axis=1), -1.0)
            take = dd > best_d
            best_d = np.where(take, dd, best_d)
            inner = np.where(take[:, None], cand, inner)
    ab = inner - page
    ll = (ab * ab).sum(1)
    safe = np.where(ll > 0, ll, 1.0)
    t = ((c - page) * ab).sum(1) / safe
    resid = np.linalg.norm(c - (page + t[:, None] * ab), axis=1)
    # A pale interior beside a pale page has no ramp to speak of. No lower
    # bound on t: the page-like end of the ramp (a few dE off the page, still
    # outside stage 1's flood tolerance, or brighter than it from resampling
    # overshoot) is the whitest part of the fringe and what seeds a stray
    # pale cluster. A KEYLINE is the other thing a band can be: a colour of
    # its own, OFF the chord (`resid` over `merge_delta_e`), which keeps its
    # vote. (A grey keyline lying ON the page-to-interior chord reads as the
    # ramp it is indistinguishable from.)
    blend = (
        (np.sqrt(ll) > 2.0 * cfg.merge_delta_e)
        & (t < 0.85) & (resid < 2.0 * cfg.merge_delta_e)
    )
    # A pixel within two flood tolerances of the page is page's own halo
    # (resampling ringing overshoots the page by a few dE): a deliberate
    # keyline is a colour, not a hint of the page's.
    blend |= np.linalg.norm(c - page, axis=1) < 2.0 * cfg.bg_tolerance_lab
    out = np.zeros((h, w), bool)
    out[by[blend], bx[blend]] = True
    return out if out.any() else None


def _kmeans(pixels: np.ndarray, k: int, seed: int, iters: int = 60,
            drop: np.ndarray | None = None) -> np.ndarray:
    """Deterministic Lloyd's k-means with seeded k-means++ init. -> (k, 3) centers.

    `drop` (bool per row of `pixels`; None = as always): rows that take the
    init draws exactly as every other row does (same sample, same RNG calls,
    so the seeds land where they always did) but never vote in the Lloyd
    update, so no centre is pulled toward them.
    """
    n = len(pixels)
    fit = pixels
    ok = None
    if n > FIT_SAMPLE_MAX:
        idx = np.linspace(0, n - 1, FIT_SAMPLE_MAX).astype(np.int64)
        fit = pixels[idx]
        if drop is not None:
            drop = drop[idx]
    if drop is not None:
        ok = ~drop

    rng = np.random.default_rng(seed)
    centers = np.empty((k, 3), np.float64)
    centers[0] = fit[rng.integers(len(fit))]
    d2 = ((fit - centers[0]) ** 2).sum(1)
    for i in range(1, k):
        total = d2.sum()
        if total <= 0:
            centers[i] = centers[i - 1]
            continue
        centers[i] = fit[rng.choice(len(fit), p=d2 / total)]
        d2 = np.minimum(d2, ((fit - centers[i]) ** 2).sum(1))

    for _ in range(iters):
        lab = _assign(fit, centers)
        moved = False
        for j in range(k):
            sel = lab == j
            if ok is not None:
                sel = sel & ok
            if not sel.any():
                continue
            new = fit[sel].mean(0)
            if not np.allclose(new, centers[j], atol=1e-6):
                centers[j] = new
                moved = True
        if not moved:
            break
    return centers


def _assign(pixels: np.ndarray, centers: np.ndarray, chunk: int = 100_000) -> np.ndarray:
    out = np.empty(len(pixels), np.int32)
    for s in range(0, len(pixels), chunk):
        block = pixels[s : s + chunk]
        d = ((block[:, None, :] - centers[None, :, :]) ** 2).sum(2)
        out[s : s + chunk] = np.argmin(d, axis=1)
    return out


def _edge_mask(labels: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """True where a valid pixel has a differently-labelled valid 4-neighbor."""
    e = np.zeros(labels.shape, bool)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        shifted = np.roll(labels, (dy, dx), (0, 1))
        shifted_valid = np.roll(valid, (dy, dx), (0, 1))
        e |= valid & shifted_valid & (shifted != labels)
    return e


def _majority_filter(labels: np.ndarray, valid: np.ndarray, k: int, passes: int) -> np.ndarray:
    """Reassign edge pixels to the dominant label in their 3x3 non-edge
    neighborhood. Vectorized per label via box filtering."""
    out = labels.copy()
    for _ in range(passes):
        edge = _edge_mask(out, valid)
        if not edge.any():
            break
        interior = valid & ~edge
        counts = np.empty((k,) + labels.shape, np.float32)
        for j in range(k):
            m = ((out == j) & interior).astype(np.float32)
            counts[j] = cv2.boxFilter(m, -1, (3, 3), normalize=False)
        best = np.argmax(counts, axis=0).astype(np.int32)
        has = counts.max(axis=0) > 0
        out = np.where(edge & has, best, out)
    return out


def _merge_similar(centers: np.ndarray, weights: np.ndarray, tol: float) -> list[list[int]]:
    """Single-linkage agglomerate of cluster centers within `tol` CIE76.
    Returns groups of original cluster indices, ordered by descending weight."""
    k = len(centers)
    parent = list(range(k))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(k):
        for j in range(i + 1, k):
            if np.linalg.norm(centers[i] - centers[j]) <= tol:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)

    groups: dict[int, list[int]] = {}
    for i in range(k):
        groups.setdefault(find(i), []).append(i)
    out = list(groups.values())
    out.sort(key=lambda g: (-float(weights[g].sum()), min(g)))
    return out


def _quantize_population(
    flat_rgb: np.ndarray,
    valid: np.ndarray,
    h: int,
    w: int,
    cfg: PipelineConfig,
    bg_edge_rgb: np.ndarray | None,
    enlarged_past_line: bool = False,
    fringe: np.ndarray | None = None,
) -> tuple[np.ndarray, list[int], list[dict]]:
    """Fit -> assign -> anti-alias cleanup -> spool-snap, over exactly the
    pixels in `valid`. This is the entire body `quantize()` has always run,
    extracted verbatim so it can run TWICE against two DISJOINT populations
    (see `quantize`) without either one's clustering, majority-filter
    voting, or phantom-blend dissolve ever comparing against — or being
    reassigned into — a cluster the other population produced.

    `enlarged_past_line` (2026-10-02, the working grid's flip): the raster
    was enlarged past the source line, so a shape's edge is a resampling
    ramp several pixels deep instead of one anti-aliased pixel. That ramp is
    a straight line in RGB — the space the resize mixes in — and a CURVE in
    Lab, far enough off the chord for a saturated colour on a light ground
    that the Lab test below misses its middle (two-squares.png at 8 px/mm
    and six colours: the red square's ramp centre (222, 91, 91) sits 11.7 dE
    off the Lab chord from the red to the ground's edge colour and 4.7 off
    the RGB one — 14.2 and 0.1 against true white — and sewed as a 0.125 mm
    pink ring in its own thread). True adds the same betweenness test read
    along the RGB segment, the residual still judged in Lab against
    `merge_delta_e`. False is the test as it always was, byte-identical.

    `fringe` (`page_fringe`, `cfg.flat_page_fringe_exclude`; None = the body
    as it always was): pixels that do not vote in the fit (`_kmeans(drop=)`:
    same k, same seed, same init draws) and then take the label of their
    NEAREST non-fringe pixel, never one chosen by their own blended colour. The majority filter
    and the dissolve below then run over every valid pixel as before.

    -> (labels (h, w) int32, -1 outside `valid`; final spool indices, one
    per output label; warnings).
    """
    idx = np.nonzero(valid.reshape(-1))[0]
    lab = rgb_to_lab(flat_rgb[idx])

    k = max(1, min(cfg.max_colors, len(np.unique(flat_rgb[idx], axis=0))))
    centers = _kmeans(
        lab, k, cfg.seed,
        drop=None if fringe is None else fringe.reshape(-1)[idx],
    )
    lab_flat = np.full(h * w, -1, np.int32)
    lab_flat[idx] = _assign(lab, centers)
    labels = lab_flat.reshape(h, w)
    if fringe is not None:
        # A fringe pixel takes its nearest non-fringe pixel's label, not the
        # one its own blended colour picks.
        fy, fx = np.nonzero(fringe)
        labels[fy, fx] = lab_flat[_nearest_source(valid & ~fringe)[fy, fx]]

    # --- anti-alias: majority filter, then phantom-blend dissolve -----------
    labels = _majority_filter(labels, valid, k, cfg.aa_iterations)

    edge = _edge_mask(labels, valid)
    # Endpoint candidates for the blend test include the BACKGROUND's edge
    # color: the outermost halo of every shape is a blend of that shape and
    # whatever lies outside it, and background is excluded from clustering,
    # so without this endpoint those halos survive as phantom thread layers
    # (measured on the golden fixture: two extra pale "threads", plus ~30
    # sliver regions that then had to be absorbed downstream).
    bg_endpoint = (
        rgb_to_lab(np.asarray(bg_edge_rgb, np.float64).reshape(1, 3))[0]
        if bg_edge_rgb is not None
        else None
    )

    # Each cluster's mean RGB, for the RGB-segment test (`enlarged_past_line`).
    mean_rgb: dict[int, np.ndarray] = {}
    if enlarged_past_line:
        flat_labels = labels.reshape(-1)
        for j in range(k):
            members = flat_labels == j
            if members.any():
                mean_rgb[j] = flat_rgb[members].astype(np.float64).mean(axis=0)

    keep: list[int] = []
    phantom: list[int] = []
    for j in range(k):
        m = valid & (labels == j)
        n = int(m.sum())
        if n == 0:
            continue
        frac_edge = float((m & edge).sum()) / n
        if frac_edge < cfg.aa_phantom_edge_frac:
            keep.append(j)
            continue
        # High edge fraction: dissolve ONLY if this color is colorimetrically
        # BETWEEN two other colors (a true anti-alias blend). An edge-fraction
        # test alone would also delete legitimately tiny real-color features.
        others = [o for o in range(k) if o != j and (valid & (labels == o)).any()]
        endpoints = [centers[o] for o in others]
        if bg_endpoint is not None:
            endpoints.append(bg_endpoint)
        blend = False
        for a in range(len(endpoints)):
            for b in range(a + 1, len(endpoints)):
                ca, cb, cj = endpoints[a], endpoints[b], centers[j]
                ab = cb - ca
                L = float(np.dot(ab, ab))
                if L <= 0:
                    continue
                t = float(np.dot(cj - ca, ab)) / L
                if not (0.15 < t < 0.85):
                    continue
                if np.linalg.norm(cj - (ca + t * ab)) < cfg.merge_delta_e:
                    blend = True
                    break
            if blend:
                break
        if not blend and enlarged_past_line:
            ends_rgb = [mean_rgb[o] for o in others]
            if bg_edge_rgb is not None:
                ends_rgb.append(np.asarray(bg_edge_rgb, np.float64).reshape(3))
            rj = mean_rgb[j]
            lab_j = rgb_to_lab(rj.reshape(1, 3))[0]
            for a in range(len(ends_rgb)):
                for b in range(a + 1, len(ends_rgb)):
                    ra, rb = ends_rgb[a], ends_rgb[b]
                    ab = rb - ra
                    L = float(np.dot(ab, ab))
                    if L <= 0:
                        continue
                    t = float(np.dot(rj - ra, ab)) / L
                    if not (0.15 < t < 0.85):
                        continue
                    on_chord = rgb_to_lab((ra + t * ab).reshape(1, 3))[0]
                    if np.linalg.norm(lab_j - on_chord) < cfg.merge_delta_e:
                        blend = True
                        break
                if blend:
                    break
        (phantom if blend else keep).append(j)

    if phantom:
        keep_centers = centers[keep]
        for j in phantom:
            near = keep[int(np.argmin(np.linalg.norm(keep_centers - centers[j], axis=1)))]
            labels[labels == j] = near
    active = keep

    # --- merge split-but-identical colors, then merge same-spool colors -----
    weights = np.array([float((labels == j).sum()) for j in active])
    groups = _merge_similar(centers[active], weights, cfg.merge_delta_e)

    merged_centers: list[np.ndarray] = []
    merged_members: list[list[int]] = []
    for g in groups:
        members = [active[i] for i in g]
        wts = np.array([float((labels == m).sum()) for m in members])
        c = np.average(centers[members], axis=0, weights=np.maximum(wts, 1e-9))
        merged_centers.append(c)
        merged_members.append(members)

    # snap to spools; same spool -> same layer
    chart = chart_for(cfg)
    spool_of = [chart.nearest_index(c) for c in merged_centers]
    by_spool: dict[int, list[int]] = {}
    for i, s in enumerate(spool_of):
        by_spool.setdefault(s, []).append(i)

    final_spools: list[int] = []
    final_members: list[list[int]] = []
    for s, idxs in sorted(
        by_spool.items(),
        key=lambda kv: -sum(float((labels == m).sum()) for i in kv[1] for m in merged_members[i]),
    ):
        final_spools.append(s)
        final_members.append([m for i in idxs for m in merged_members[i]])

    warnings: list[dict] = []
    # `cfg.max_colors` is enforced per population, not on the combined total
    # (see `quantize`) — a rare simplification the enclosed-population call
    # can only ever exceed on its own if a single enclosed patch alone needs
    # more distinct colors than the whole design's budget, which does not
    # happen on either fixture this slice ships with.
    if len(final_spools) > cfg.max_colors:
        sizes = [
            sum(float((labels == m).sum()) for m in mem) for mem in final_members
        ]
        order = np.argsort(sizes)[::-1]
        kept = set(int(i) for i in order[: cfg.max_colors])
        kept_lab = np.array([merged_centers[final_members[i][0]] for i in sorted(kept)])
        remap: dict[int, int] = {}
        kept_sorted = sorted(kept)
        for i in range(len(final_spools)):
            if i in kept:
                continue
            nearest = kept_sorted[
                int(np.argmin(np.linalg.norm(kept_lab - merged_centers[final_members[i][0]], axis=1)))
            ]
            remap[i] = nearest
        new_spools, new_members = [], []
        for i in kept_sorted:
            mem = list(final_members[i])
            for src, dst in remap.items():
                if dst == i:
                    mem += final_members[src]
            new_spools.append(final_spools[i])
            new_members.append(mem)
        warnings.append(
            warn(
                COLOR_CAP_APPLIED,
                f"Artwork needed more than {cfg.max_colors} thread colors; the smallest "
                "areas were merged into their closest match.",
                dropped=len(remap),
            )
        )
        final_spools, final_members = new_spools, new_members

    out = np.full((h, w), -1, np.int32)
    for new_label, members in enumerate(final_members):
        for m in members:
            out[labels == m] = new_label

    return out, final_spools, warnings


def quantize(p: Prep, cfg: PipelineConfig) -> Quant:
    h, w = p.rgb.shape[:2]
    valid = ~p.bg_mask
    flat_rgb = p.rgb.reshape(-1, 3)

    # `Prep.enclosed_mask` pixels (BACKGROUND_ENCLOSED) are real content now
    # (stage 1, 2026-08-04) — but content the design's ORIGINAL foreground
    # never had to share ANY of this stage's decisions with. Running one
    # shared pass over both populations means the enclosed area's colors
    # can shift the k-means fit AND — the bigger effect, measured — can
    # supply a new "nearest keep cluster" for OTHER shapes' own outer
    # anti-alias halos during phantom-blend dissolve: every shape's edge
    # against the background is a blend toward roughly that background
    # color, and an enclosed patch is BY DEFINITION close to that same
    # color, so it competes to reabsorb halos that used to fold back into
    # their own shape. Measured on `logo_whitebg.png` with a single shared
    # pass: two rectangles nowhere near the enclosed ring-hole lost part of
    # their own boundary to the new "White" cluster, shrank by ~1-2%, and
    # that was enough to flip `2*area/perimeter` across the satin/fill cap
    # for both — tripling their stitch count from a change that has nothing
    # to do with satin vs. fill. That is exactly the antialiasing-noise
    # fragility `docs/superpowers/plans/2026-08-04-m0-shape-lens-
    # measurement.md` already flagged as a live, unresolved problem (the
    # DT-first migration's whole reason for existing) — this slice must not
    # newly trigger it. So the two populations run through
    # `_quantize_population` SEPARATELY and are merged only after each has
    # finished independently: the design's own pass sees exactly the pixels
    # it always did, byte-identical whether or not an enclosed region
    # exists anywhere else in the same image (and trivially so when there
    # is none — this reduces to one call, the pre-existing code path).
    enclosed = p.enclosed_mask
    has_enclosed = enclosed is not None and enclosed.any()
    base_valid = valid & ~enclosed if has_enclosed else valid

    # The working grid took this raster past the line a low-resolution source
    # was always enlarged to (`cfg.min_px_per_mm`): its edges are resampling
    # ramps, and the phantom-blend test reads them in RGB as well as Lab. A
    # source at or above the line, or one held on it, is exactly as before —
    # and so is a Prep built by hand, which records no input resolution (0.0).
    source_px = float(p.input_px_per_mm or 0.0)
    enlarged = source_px > 0.0 and float(p.px_per_mm) > max(source_px, float(cfg.min_px_per_mm)) + 1e-6

    # `cfg.flat_page_fringe_exclude`: the base population's page-edge blend
    # pixels, left out of the fit (None = the call as it always was).
    fringe = page_fringe(p, cfg, base_valid) if cfg.flat_page_fringe_exclude else None

    base_labels, base_spools, warnings = _quantize_population(
        flat_rgb, base_valid, h, w, cfg, p.bg_edge_rgb, enlarged_past_line=enlarged,
        fringe=fringe,
    )

    if has_enclosed:
        enc_labels, enc_spools, enc_warnings = _quantize_population(
            flat_rgb, enclosed, h, w, cfg, p.bg_edge_rgb, enlarged_past_line=enlarged
        )
        warnings = warnings + enc_warnings
        base_k = len(base_spools)
        combined = base_labels.copy()
        enc_valid = enc_labels >= 0
        combined[enc_valid] = enc_labels[enc_valid] + base_k
        labels_out = combined
        thread_indices = base_spools + enc_spools
    else:
        labels_out = base_labels
        thread_indices = base_spools

    chart = chart_for(cfg)
    return Quant(
        labels=labels_out,
        thread_indices=thread_indices,
        cluster_rgb=np.array([chart[s].rgb for s in thread_indices], np.float64),
        warnings=warnings,
        page_fringe=fringe,
    )
