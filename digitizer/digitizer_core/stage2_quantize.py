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

from . import deadline
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
    # `cfg.flat_page_fringe_soft_ramp`: a JPEG edge is a ramp about three
    # source pixels deep, not one, so the band reaches that many upscaled.
    if p.input_px_per_mm and p.px_per_mm > p.input_px_per_mm:
        ramp = float(cfg.flat_page_fringe_ramp_src_px) if cfg.flat_page_fringe_soft_ramp else 1.0
        f_px = max(f_px, int(np.ceil(ramp * p.px_per_mm / p.input_px_per_mm)) + 1)
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


def outline_inner_blend(labels, lab_full, valid, centers, exclude, d_px, thin_px, cfg):
    """The blend between a THIN DARK OUTLINE and the fill beside it
    (`cfg.flat_page_fringe_exclude`), found per pixel -> (mask, target label)
    or None.

    The outline is read off the labels: the darkest label (L* of its centre),
    when at least half of its pixels lie within `thin_px / 2` of a pixel that is
    not its own (thin: its widest part is under `thin_px`; the caller passes
    `cfg.flat_outline_max_mm * px_per_mm`), plus any other thin label within
    10 L* of it. A pixel is fringe when it is within `d_px` of that outline,
    is not itself an outline label, and (the keyline guard) its Lab colour lies
    on the chord outline-centre -> adjacent-fill-centre (0.1 < t < 0.9, within
    2 x `merge_delta_e`) AND nearer that chord than to any OTHER palette
    centre: a colour of its own (a light keyline; the sheen beside an outline)
    keeps its vote. Its target is the outline for t < 0.5, the fill otherwise:
    never the label its own blended colour would pick.

    Why the phantom dissolve does not catch it: it tests a whole CLUSTER (an
    edge fraction, then betweenness), and a blend population that a real pale
    region anchors (the pot's sheen) is not mostly edge, so it passes as real.
    """
    k = len(centers)
    n_of = [int((valid & (labels == j)).sum()) for j in range(k)]
    live = [j for j in range(k) if n_of[j]]
    if len(live) < 3:
        return None
    light = {j: float(centers[j][0]) for j in live}
    darkest = min(live, key=lambda j: light[j])
    thin = []
    for j in live:
        m = valid & (labels == j)
        dt = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 3)
        if float((dt[m] <= thin_px / 2.0).mean()) >= 0.5:
            thin.append(j)
    if darkest not in thin:
        return None
    outline = [j for j in thin if light[j] <= light[darkest] + 10.0]
    o_mask = valid & np.isin(labels, outline)
    dist_o = cv2.distanceTransform((~o_mask).astype(np.uint8), cv2.DIST_L2, 5)
    cand = valid & ~o_mask & ~exclude & (dist_o <= d_px)
    src = valid & ~o_mask & ~cand & ~exclude
    if not cand.any() or not src.any():
        return None
    h, w = labels.shape
    cy, cx = np.nonzero(cand)
    o_lab = labels.reshape(-1)[_nearest_source(o_mask)[cy, cx]]
    f_lab = labels.reshape(-1)[_nearest_source(src)[cy, cx]]
    oc, fc = centers[o_lab], centers[f_lab]
    c = lab_full[cy, cx]
    ab = fc - oc
    ll = (ab * ab).sum(1)
    safe = np.where(ll > 0, ll, 1.0)
    t = ((c - oc) * ab).sum(1) / safe
    resid = np.linalg.norm(c - (oc + t[:, None] * ab), axis=1)
    own = np.full(len(cy), np.inf)
    for j in live:
        d = np.linalg.norm(c - centers[j], axis=1)
        own = np.where((o_lab != j) & (f_lab != j), np.minimum(own, d), own)
    hit = ((np.sqrt(ll) > 2.0 * cfg.merge_delta_e) & (t > 0.1) & (t < 0.9)
           & (resid < 2.0 * cfg.merge_delta_e) & (resid < own))
    if not hit.any():
        return None
    mask = np.zeros((h, w), bool)
    target = np.full((h, w), -1, np.int32)
    mask[cy[hit], cx[hit]] = True
    target[cy[hit], cx[hit]] = np.where(t[hit] < 0.5, o_lab[hit], f_lab[hit])
    return mask, target


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
        deadline.check("stage 2")
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
        deadline.check("stage 2")
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
        deadline.check("stage 2")
        edge = _edge_mask(out, valid)
        if not edge.any():
            break
        interior = valid & ~edge
        counts = np.empty((k,) + labels.shape, np.float32)
        for j in range(k):
            deadline.check("stage 2")
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


#: `cfg.flat_blend_band_any_scale`: the ramp round's depth, in working px,
#: on a raster the grid did NOT enlarge. A JPEG's blend rim is made by its
#: compression and the art's anti-aliasing, not by resampling, so it has no
#: `flat_page_fringe_ramp_src_px` to scale. Measured 2026-11-14 on the
#: cluster that sews it (share of its pixels within this many px of a label
#: change, against the 0.9 gate): silhouette_logo's mint rim round its white
#: letters 0.98 at 1 px, its dark-green ring round the bear 0.72 at 1 and
#: 0.95 at 2; ProSeal's pale band over its teal bar 0.97 at 1. Two working px
#: (0.25 mm at 8 px/mm) is the smaller depth that reaches all three.
BLEND_BAND_PX = 2


def _rgb_chord_t(j: int, oa, ob, mean_rgb: dict, bg_edge_rgb, delta_e: float) -> float | None:
    """`band_mode`'s second reading of "is cluster `j` a blend of `oa` and
    `ob`" (None = the page): on the RGB segment between their mean colours,
    the space a blend is mixed in, with the residual judged in Lab against
    `delta_e` -- round one's `enlarged_past_line` test, for one pair.
    -> t on that segment when it is a blend inside (0.15, 0.85), else None.
    ProSeal's pale band over its teal bar sits 6.3 off the Lab chord from the
    page to the teal and on the RGB one."""
    def rgb(o):
        if o is None:
            return None if bg_edge_rgb is None else np.asarray(bg_edge_rgb, np.float64).reshape(3)
        return mean_rgb.get(o)
    ra, rb, rj = rgb(oa), rgb(ob), mean_rgb.get(j)
    if ra is None or rb is None or rj is None:
        return None
    ab = rb - ra
    L = float(np.dot(ab, ab))
    if L <= 0:
        return None
    t = float(np.dot(rj - ra, ab)) / L
    if not (0.15 < t < 0.85):
        return None
    on_chord = rgb_to_lab((ra + t * ab).reshape(1, 3))[0]
    lab_j = rgb_to_lab(rj.reshape(1, 3))[0]
    return t if float(np.linalg.norm(lab_j - on_chord)) < delta_e else None


def _quantize_population(
    flat_rgb: np.ndarray,
    valid: np.ndarray,
    h: int,
    w: int,
    cfg: PipelineConfig,
    bg_edge_rgb: np.ndarray | None,
    enlarged_past_line: bool = False,
    fringe: np.ndarray | None = None,
    inner: tuple[float, float] | None = None,
    ramp_px: int = 0,
    band_mode: bool = False,
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

    `ramp_px` (`cfg.flat_ramp_blend_dissolve`; 0 = the dissolve as it always
    was): on an enlarged raster a two-ink edge is a ramp `2 * ramp_px` deep.
    A cluster the one-pixel test keeps but which is edge within `ramp_px` of a
    label change is a second-round candidate: a blend when it lies on the Lab
    chord between two colours the first round KEPT (or one and the page), and
    it then joins the NEARER END of that chord, not whichever kept centre is
    nearest in Lab (Bridge's olive yellow-to-black ramp sits nearer its blue
    than black). The first round is unchanged.

    `band_mode` (`cfg.flat_blend_band_any_scale`, built OFF 2026-11-14; the
    caller passes it only for a raster NOT enlarged, with `ramp_px` =
    `BLEND_BAND_PX`): the same second round for a JPEG's blend rim on a
    source the grid shrank or kept, where no resampling ramp exists but
    compression and anti-aliasing leave one. A candidate is a blend on the
    Lab chord OR the RGB one (the round-one `enlarged_past_line` reading),
    and each of its pixels joins the label of the NEAREST pixel outside the
    band (a rim splits between what it touches; the page is never a target).
    False: the round as it always was.

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
    target = None
    if fringe is not None and inner is not None:
        # The outline's inner blend (`outline_inner_blend`), read off this
        # first assignment; its pixels join `fringe` IN PLACE (the caller reads
        # the union for stage 3) and the fit runs again without them. The init
        # still draws from every pixel, as in the first fit: dropping them
        # before the draw re-seeds the whole palette, so cluster ids stay put
        # and the first fit's targets name the same clusters.
        lab_full = np.zeros((h * w, 3), np.float64)
        lab_full[idx] = lab
        found = outline_inner_blend(labels, lab_full.reshape(h, w, 3), valid, centers,
                                    fringe, inner[0], inner[1], cfg)
        if found is not None:
            fringe |= found[0]
            target = found[1]
            centers = _kmeans(lab, k, cfg.seed, drop=fringe.reshape(-1)[idx])
            lab_flat[idx] = _assign(lab, centers)
            labels = lab_flat.reshape(h, w)
    if fringe is not None:
        # A fringe pixel takes its nearest non-fringe pixel's label, not the
        # one its own blended colour picks; an outline-inner blend takes the
        # outline or the fill by its place on their chord.
        fy, fx = np.nonzero(fringe)
        labels[fy, fx] = lab_flat[_nearest_source(valid & ~fringe)[fy, fx]]
        if target is not None:
            sel = target >= 0
            labels[sel] = target[sel]

    # --- anti-alias: majority filter, then phantom-blend dissolve -----------
    labels = _majority_filter(labels, valid, k, cfg.aa_iterations)

    edge = _edge_mask(labels, valid)
    # `ramp_px`: the edge as deep as the soft ramp, for the second test below.
    edge_ramp = None
    if ramp_px > 0:
        d = 2 * int(ramp_px) + 1
        edge_ramp = valid & cv2.dilate(edge.astype(np.uint8),
                                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))).astype(bool)
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

    # Each cluster's mean RGB, for the RGB-segment test (`enlarged_past_line`,
    # and the ramp round under `band_mode`).
    mean_rgb: dict[int, np.ndarray] = {}
    if enlarged_past_line or band_mode:
        flat_labels = labels.reshape(-1)
        for j in range(k):
            members = flat_labels == j
            if members.any():
                mean_rgb[j] = flat_rgb[members].astype(np.float64).mean(axis=0)

    keep: list[int] = []
    phantom: list[int] = []
    # `ramp_px`: clusters that are edge only once the edge is the ramp's depth.
    ramp_cand: list[int] = []
    for j in range(k):
        m = valid & (labels == j)
        n = int(m.sum())
        if n == 0:
            continue
        frac_edge = float((m & edge).sum()) / n
        if frac_edge < cfg.aa_phantom_edge_frac:
            if edge_ramp is not None and                     float((m & edge_ramp).sum()) / n >= cfg.aa_phantom_edge_frac:
                ramp_cand.append(j)
            else:
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

    # `ramp_px`: a cluster that is edge only at the ramp's depth is a blend
    # when it lies on the Lab chord between two KEPT colours (or a kept colour
    # and the page) -- never between two other blends, which a thin real ink
    # with its own ramps would be (fremont_patch's tan rope at x1.73 sits
    # between its own charcoal and sterling ramp clusters) -- and joins the
    # nearer end of that chord.
    chord_end: dict[int, int] = {}
    band_ids: list[int] = []
    if ramp_cand:
        base_keep = list(keep)
        ends = [(o, centers[o]) for o in base_keep]
        if bg_endpoint is not None:
            ends.append((None, bg_endpoint))
        pairs = [(a, b) for a in range(len(ends)) for b in range(a + 1, len(ends))]
        for j in ramp_cand:
            cj = centers[j]
            blend = False
            for a, b in pairs:
                (oa, ca), (ob, cb) = ends[a], ends[b]
                ab = cb - ca
                L = float(np.dot(ab, ab))
                if L <= 0:
                    continue
                t = float(np.dot(cj - ca, ab)) / L
                if not (0.15 < t < 0.85) or np.linalg.norm(cj - (ca + t * ab)) >= cfg.merge_delta_e:
                    if not band_mode:
                        continue
                    t = _rgb_chord_t(j, oa, ob, mean_rgb, bg_edge_rgb, cfg.merge_delta_e)
                    if t is None:
                        continue
                blend = True
                if band_mode:
                    band_ids.append(j)
                else:
                    end = oa if t < 0.5 else ob
                    if end is not None:
                        chord_end[j] = end
                break
            (phantom if blend else keep).append(j)
        keep.sort()
        phantom.sort()

    if phantom:
        keep_centers = centers[keep]
        for j in phantom:
            if j in band_ids:
                continue
            near = keep[int(np.argmin(np.linalg.norm(keep_centers - centers[j], axis=1)))]
            if j in chord_end:
                near = chord_end[j]
            labels[labels == j] = near
    if band_ids:
        # `band_mode`: each band pixel takes the label of the NEAREST pixel
        # outside the band -- a rim joins what it physically touches, half to
        # each side, and the page (never `valid`) is never a target. Folding
        # the whole cluster into one end painted every speck of that colour
        # elsewhere in the design with it: ProSeal's pale band went teal, and
        # so did the same pale JPEG ringing on its black lettering (a teal N).
        band = valid & np.isin(labels, band_ids)
        src = valid & ~band
        if src.any():
            near_idx = _nearest_source(src)
            by, bx = np.nonzero(band)
            labels[by, bx] = labels.reshape(-1)[near_idx[by, bx]]
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
    fringe = None
    inner = None
    if cfg.flat_page_fringe_exclude and not p.bg_from_alpha:
        fringe = page_fringe(p, cfg, base_valid)
        if fringe is None:
            fringe = np.zeros((h, w), bool)
        # The outline-inner blend's reach: the resampling ramp, `upscale`
        # working px wide (the page band's rule), and the widest an outline
        # may be to count as thin, `flat_outline_max_mm` in working px.
        up = (float(p.px_per_mm) / float(p.input_px_per_mm)) if p.input_px_per_mm else 1.0
        inner = (float(max(int(cfg.flat_page_fringe_px), int(np.ceil(max(up, 1.0))))),
                 float(cfg.flat_outline_max_mm) * float(p.px_per_mm))
    elif cfg.flat_page_fringe_soft_ramp and enlarged and not p.bg_from_alpha:
        # `cfg.flat_page_fringe_soft_ramp` on its own: the page fringe alone,
        # soft band, on an ENLARGED raster only (no outline-inner pass). A
        # source at or above the grid is the call as it always was.
        fringe = page_fringe(p, cfg, base_valid)

    # `cfg.flat_ramp_blend_dissolve`: half the soft edge's depth in working
    # px (`flat_page_fringe_ramp_src_px` source px, upscaled), on an enlarged
    # raster only; 0 = the phantom dissolve as it always was.
    ramp_px = 0
    band_mode = False
    if cfg.flat_ramp_blend_dissolve and enlarged:
        ramp_px = int(np.ceil(float(cfg.flat_page_fringe_ramp_src_px)
                              * float(p.px_per_mm) / source_px / 2.0))
    elif getattr(cfg, "flat_blend_band_any_scale", False) and not enlarged:
        # `cfg.flat_blend_band_any_scale` (built OFF 2026-11-14): the same
        # round on a raster the grid shrank or kept (`BLEND_BAND_PX`,
        # band pixels to their nearest non-band pixel). An enlarged raster
        # keeps the line above, ON or OFF.
        ramp_px = BLEND_BAND_PX
        band_mode = True

    base_labels, base_spools, warnings = _quantize_population(
        flat_rgb, base_valid, h, w, cfg, p.bg_edge_rgb, enlarged_past_line=enlarged,
        fringe=fringe, inner=inner, ramp_px=ramp_px,
        **({"band_mode": True} if band_mode else {}),
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
