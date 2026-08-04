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


def _kmeans(pixels: np.ndarray, k: int, seed: int, iters: int = 60) -> np.ndarray:
    """Deterministic Lloyd's k-means with seeded k-means++ init. -> (k, 3) centers."""
    n = len(pixels)
    fit = pixels
    if n > FIT_SAMPLE_MAX:
        idx = np.linspace(0, n - 1, FIT_SAMPLE_MAX).astype(np.int64)
        fit = pixels[idx]

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
) -> tuple[np.ndarray, list[int], list[dict]]:
    """Fit -> assign -> anti-alias cleanup -> spool-snap, over exactly the
    pixels in `valid`. This is the entire body `quantize()` has always run,
    extracted verbatim so it can run TWICE against two DISJOINT populations
    (see `quantize`) without either one's clustering, majority-filter
    voting, or phantom-blend dissolve ever comparing against — or being
    reassigned into — a cluster the other population produced.

    -> (labels (h, w) int32, -1 outside `valid`; final spool indices, one
    per output label; warnings).
    """
    idx = np.nonzero(valid.reshape(-1))[0]
    lab = rgb_to_lab(flat_rgb[idx])

    k = max(1, min(cfg.max_colors, len(np.unique(flat_rgb[idx], axis=0))))
    centers = _kmeans(lab, k, cfg.seed)
    lab_flat = np.full(h * w, -1, np.int32)
    lab_flat[idx] = _assign(lab, centers)
    labels = lab_flat.reshape(h, w)

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
        endpoints = [centers[o] for o in range(k) if o != j and (valid & (labels == o)).any()]
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

    base_labels, base_spools, warnings = _quantize_population(
        flat_rgb, base_valid, h, w, cfg, p.bg_edge_rgb
    )

    if has_enclosed:
        enc_labels, enc_spools, enc_warnings = _quantize_population(
            flat_rgb, enclosed, h, w, cfg, p.bg_edge_rgb
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
    )
