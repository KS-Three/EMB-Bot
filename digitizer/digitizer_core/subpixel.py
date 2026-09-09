"""Sub-pixel, anti-alias-aware contour vertices — `cfg.subpixel_edges`.

PR 2 of `docs/superpowers/plans/2026-09-08-subpixel-edges.md` (§3). Stage 4
traces a LABEL mask, so every vertex it hands Douglas-Peucker is a pixel
centre and the polygon carries the staircase: half a pixel of deviation
either side of the true edge, and a half-pixel inward bias on every filled
shape (the pixel-centre trace sits inside the edge — the ladder's baseline,
scope-history 09-08). The information that locates the edge BELOW a pixel
is in the grey levels the mask threw away: every committed fixture is drawn
at 4x and downscaled with INTER_AREA so each edge carries a 1–2 px
anti-alias ramp, and real exports and photographs carry the same ramp. The
edge's true position is where the colour is halfway between the two sides,
readable to a fraction of a pixel.

`subpixel_contour` does that, per raw contour vertex, and nothing else — it
does not smooth (a measured negative, DOCTRINE) and it does not touch the
simplifier (`simplify_tol_mm` stays 0.2; PR 3 keys the curve refinement's
floor to the acceptance mask this returns):

1. the local normal from the neighbours `NORMAL_STEPS` either side, its
   sign fixed by the mask so that positive is OUTSIDE the shape;
2. the prepped image sampled along it in Lab (bilinear) at the seven
   `PROFILE_OFFSETS_PX`, plus a plateau sample two to two-and-a-half pixels
   inside and outside for the two side colours;
3. each sample projected onto the axis between the side colours, giving
   `t(s)` from 0 (inside) to 1 (outside);
4. ACCEPTED when the sides differ by at least `min_contrast_de` (a third
   label meeting at the vertex, or two labels the quantiser would have
   merged, fail this), `t` is monotonic over the window, sits on its two
   plateaus at the window's ends (`PLATEAU_TOL` — the whole ramp is inside
   the window) and crosses 0.5 exactly once; the vertex moves to the edge
   position AREA CONSERVATION gives: the inside fraction `1 - t` integrated
   across the window is the distance from the window's inner end to the
   edge, exact for any ramp symmetric about the edge and for the box-filter
   ramp an INTER_AREA downscale or a renderer's coverage leaves, whatever
   its width or the edge's angle. Measured 2026-09-09 against the 0.5
   crossing of the linearly interpolated profile, which is biased by up to
   ±0.09 px because the ramp's knots sit half a pixel off the pixel centres
   the samples interpolate between: on a straight edge at four sub-pixel
   positions the integral errs by -0.05 to +0.01 px against -0.10 to +0.09;
   on a disc rendered at 16x, 0.037 px of scatter and 0.014 of bias
   against 0.058 and 0.009. The move is refused past `ACCEPT_WINDOW_PX`.
   REJECTED — kept at the pixel centre — otherwise: JPEG ringing fails
   monotonicity, texture fails it, a ramp wider than the window (a heavy
   blur, a Lanczos upscale) fails the plateaus, and a stroke under about
   three pixels wide has no plateau between its two ramps at all (those
   strokes are the thin-stroke plan's, not this one's).

A hard edge with no ramp is accepted too: bilinear sampling makes a
one-pixel ramp between the last inside pixel and the first outside one, and
the edge lands on the pixel BOUNDARY, half a pixel out from the centre the
mask trace put there — which is where a hard edge is.

Returns the moved points (float, same order and count as the input) and
the accepted mask, so the caller can carry the share into the region's
meta and PR 3 can read it per chord.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import map_coordinates

# Two passes over each vertex, a narrow one and, only where it refuses, a
# wide one. Each is (half-width of the profile window, px; the two plateau
# offsets that give the side colours; the furthest the edge may sit from the
# pixel centre). The narrow pass (seven samples from 1.5 px inside to 1.5
# px outside, half a pixel apart) reads a stroke down to about three pixels
# wide, whose plateau is two pixels in. The wide pass exists for a LABEL
# that sits a pixel off its edge: stage 2's majority filter and blend
# dissolve hand a halo pixel to the darker cluster, so the white disc
# enclosed by the whitebg ring traces 0.8–1.0 px inside its anti-alias edge
# and the narrow pass refused 53% of its vertices (2026-09-09, the 400 px
# rung); the wide pass needs five pixels of plateau either side and so
# admits nothing the narrow pass would not, on a stroke.
PASSES = ((1.5, (2.0, 2.5), 0.75),
          (2.5, (3.0, 3.5), 1.25))
# Samples are half a pixel apart along the normal in every pass.
SAMPLE_STEP_PX = 0.5
# The narrow pass's profile offsets and window, kept by name for the tests
# and for PR 3's per-chord reading.
PROFILE_OFFSETS_PX = np.arange(-PASSES[0][0], PASSES[0][0] + 1e-9, SAMPLE_STEP_PX)
REFERENCE_OFFSETS_PX = PASSES[0][1]
ACCEPT_WINDOW_PX = PASSES[-1][2]          # the furthest any pass may move a vertex
# The local tangent is the chord between the vertices this many contour
# steps behind and ahead — the same window `_refine_curves` averages over.
NORMAL_STEPS = 2
# Corners. The one-dimensional ramp model holds where the boundary is
# straight or gently curved across the window; at a corner the two sides
# meet inside it and a vertex moved along one blended normal lands short of
# the corner (a 90 deg corner pixel moved along its diagonal reaches 0.5 px
# of the 0.71 it needs), bevelling every rectangle — measured 2026-09-09 on
# the 800 px rung: the bar's Hausdorff 0.09 -> 0.18 mm and its spread
# tripled while the curves improved. A vertex whose two side chords (this
# many steps back and ahead) turn by at least `CORNER_DEG` is read along
# EACH side's own normal and placed where the two offset side lines meet;
# a corner a side cannot be read at is kept at its pixel centre and never
# dropped. Read with the narrow pass only, and the meeting point may lie at
# most `CORNER_REACH_PX` from the pixel centre — the narrow window along
# both sides at once (a right angle whose sides both sit 0.75 px out, the
# most the window admits, meets 1.06 px away): a one-pixel protrusion of
# the label — quantisation noise on a curve — turns as sharply as a corner
# and its two side lines meet far outside the shape (2.4 px out on the 400
# px circle before this cap); refused, it is an ordinary rejected vertex
# and drops with the others. The steps are longer than `NORMAL_STEPS` so a
# shallow staircase (two along, one up) does not read as a corner at every
# step.
CORNER_STEPS = 3
CORNER_DEG = 60.0
CORNER_REACH_PX = PASSES[0][2] * math.sqrt(2.0)
# `t` may dip by this much between consecutive samples and still count as
# monotonic: bilinear interpolation of an ideal ramp is exactly monotonic,
# and this admits only sampling noise, not a halo.
MONOTONIC_TOL = 0.05
# How far from 0 (inside) and 1 (outside) the profile may sit at the
# window's two ends and still count as having its whole ramp inside the
# window — the condition the area integral needs.
PLATEAU_TOL = 0.15
# A run of this many or fewer REJECTED vertices between two accepted ones is
# dropped from the polyline before simplification: those vertices have no
# known edge position (an inner corner pixel of the 8-connected trace sits
# a full pixel inside the edge, past the window), and left in place each one
# is an inward spike the simplifier is obliged to keep — measured 2026-09-09
# on the 400 px circle: two such vertices took its Hausdorff from 0.18 to
# 0.24 mm and its roughness from 2.2 to 4.1 deg. Longer runs are a real
# unknown (a thin stroke, a third colour, texture) and stay as pixel centres.
DROP_REJECTED_RUN_MAX = 2


def _oriented_normals(raw: np.ndarray, steps: int, inside) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """-> (normal from the chord `steps` behind to the vertex, normal from the
    vertex to `steps` ahead, ok) — each unit length and pointing OUTSIDE,
    `ok` False where a chord is degenerate or the mask lies on both sides."""
    n = len(raw)
    idx = np.arange(n)

    def unit_normal(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        tang = b - a
        tlen = np.hypot(tang[:, 0], tang[:, 1])
        good = tlen > 1e-9
        tang = tang / np.where(good, tlen, 1.0)[:, None]
        normal = np.stack([tang[:, 1], -tang[:, 0]], axis=1)
        plus, minus = inside(raw + normal), inside(raw - normal)
        normal[plus & ~minus] *= -1.0          # positive along the normal is OUTSIDE
        return normal, good & (plus != minus)

    n_prev, ok_prev = unit_normal(raw[(idx - steps) % n], raw)
    n_next, ok_next = unit_normal(raw, raw[(idx + steps) % n])
    return n_prev, n_next, ok_prev & ok_next


def subpixel_contour(raw_xy: np.ndarray, lab: np.ndarray, mask: np.ndarray,
                     mask_origin: tuple[int, int], *,
                     min_contrast_de: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """-> (points (N, 2) float64, accepted (N,) bool, corner (N,) bool).

    `raw_xy`: a closed contour of pixel centres, (x, y) in the frame of
    `lab` ((H, W, 3) float CIELAB of the prepped image). `mask`: the
    shape's own pixels (nonzero = inside), a crop whose top-left pixel sits
    at `mask_origin` = (x, y) in the same frame; used only to orient the
    normals. `min_contrast_de`: the least CIE76 distance between the two
    side colours for an edge to be readable at all. `corner` marks the
    corners a side could not be read at, which `drop_isolated_rejects` must
    keep (see `CORNER_REACH_PX`).
    """
    raw = np.asarray(raw_xy, dtype=np.float64).reshape(-1, 2)
    n = len(raw)
    pts = raw.copy()
    accepted = np.zeros(n, dtype=bool)
    corner = np.zeros(n, dtype=bool)
    if n < 2 * CORNER_STEPS + 1:
        return pts, accepted, corner

    def inside(xy: np.ndarray) -> np.ndarray:
        xi = np.rint(xy[:, 0]).astype(int) - int(mask_origin[0])
        yi = np.rint(xy[:, 1]).astype(int) - int(mask_origin[1])
        within = (xi >= 0) & (yi >= 0) & (xi < mask.shape[1]) & (yi < mask.shape[0])
        out = np.zeros(len(xy), dtype=bool)
        out[within] = mask[yi[within], xi[within]] > 0
        return out

    idx = np.arange(n)
    # The blended normal every vertex is read along first.
    tang = raw[(idx + NORMAL_STEPS) % n] - raw[(idx - NORMAL_STEPS) % n]
    tlen = np.hypot(tang[:, 0], tang[:, 1])
    ok = tlen > 1e-9
    tang = tang / np.where(ok, tlen, 1.0)[:, None]
    normal = np.stack([tang[:, 1], -tang[:, 0]], axis=1)
    plus, minus = inside(raw + normal), inside(raw - normal)
    normal[plus & ~minus] *= -1.0
    ok &= plus != minus

    def read_edge(normals: np.ndarray, base_ok: np.ndarray,
                  passes=PASSES) -> tuple[np.ndarray, np.ndarray]:
        """The edge offset along `normals` for every vertex, and whether it
        was accepted — the narrow pass, then the wide one where refused."""
        s_star = np.zeros(n)
        got = np.zeros(n, dtype=bool)
        for half, refs, window in passes:
            profile_offsets = np.arange(-half, half + 1e-9, SAMPLE_STEP_PX)
            k = len(profile_offsets)
            r0, r1 = refs
            offsets = np.concatenate([profile_offsets, [-r1, -r0, r0, r1]])
            sample_xy = raw[:, None, :] + offsets[None, :, None] * normals[:, None, :]
            coords = [sample_xy[..., 1].ravel(), sample_xy[..., 0].ravel()]            # (row, col)
            vals = np.stack([map_coordinates(lab[..., c], coords, order=1, mode="nearest")
                             for c in range(3)], axis=-1).reshape(n, len(offsets), 3)
            profile = vals[:, :k]
            c_in = vals[:, k:k + 2].mean(axis=1)
            c_out = vals[:, k + 2:].mean(axis=1)
            axis = c_out - c_in
            contrast = np.hypot(np.hypot(axis[:, 0], axis[:, 1]), axis[:, 2])
            good = base_ok & ~got & (contrast >= min_contrast_de)
            denom = np.where(contrast > 0, contrast ** 2, 1.0)
            t = ((profile - c_in[:, None, :]) * axis[:, None, :]).sum(axis=-1) / denom[:, None]
            monotonic = (np.diff(t, axis=1) >= -MONOTONIC_TOL).all(axis=1)
            on_plateaus = (t[:, 0] <= PLATEAU_TOL) & (t[:, -1] >= 1.0 - PLATEAU_TOL)
            g = t - 0.5
            up = (g[:, :-1] < 0.0) & (g[:, 1:] >= 0.0)
            good &= monotonic & on_plateaus & (up.sum(axis=1) == 1)
            # Area conservation: the inside fraction integrated across the
            # window (trapezoid over the half-pixel samples) is how far the
            # edge sits from the window's inner end.
            inside_frac = np.clip(1.0 - t, 0.0, 1.0)
            s_pass = -half + np.trapezoid(inside_frac, dx=SAMPLE_STEP_PX, axis=1)
            good &= np.abs(s_pass) <= window
            s_star[good] = s_pass[good]
            got |= good
        return s_star, got

    # Corners: read along each side's own normal and intersect the two
    # offset side lines.
    n_prev, n_next, side_ok = _oriented_normals(raw, CORNER_STEPS, inside)
    cos_turn = np.clip((n_prev * n_next).sum(axis=1), -1.0, 1.0)
    corner = side_ok & (np.degrees(np.arccos(cos_turn)) >= CORNER_DEG)
    protect = np.zeros(n, dtype=bool)
    if corner.any():
        d_prev, ok_prev = read_edge(n_prev, corner, passes=PASSES[:1])
        d_next, ok_next = read_edge(n_next, corner, passes=PASSES[:1])
        both = corner & ok_prev & ok_next
        protect = corner & ~both               # a corner a side could not be read at
        # u . n_prev = d_prev, u . n_next = d_next
        det = n_prev[:, 0] * n_next[:, 1] - n_prev[:, 1] * n_next[:, 0]
        solvable = both & (np.abs(det) > 1e-6)
        ux = (d_prev * n_next[:, 1] - d_next * n_prev[:, 1]) / np.where(solvable, det, 1.0)
        uy = (n_prev[:, 0] * d_next - n_next[:, 0] * d_prev) / np.where(solvable, det, 1.0)
        reach = np.hypot(ux, uy)
        solvable &= reach <= CORNER_REACH_PX
        pts[solvable] = raw[solvable] + np.stack([ux, uy], axis=1)[solvable]
        accepted |= solvable

    s_star, got = read_edge(normal, ok & ~corner)
    pts[got] = raw[got] + s_star[got, None] * normal[got]
    accepted |= got
    return pts, accepted, protect


def drop_isolated_rejects(pts: np.ndarray, accepted: np.ndarray,
                          protect: np.ndarray | None = None,
                          max_run: int = DROP_REJECTED_RUN_MAX) -> tuple[np.ndarray, np.ndarray]:
    """`pts`/`accepted` (a closed ring) with every run of at most `max_run`
    rejected vertices that sits between two accepted ones removed — see
    `DROP_REJECTED_RUN_MAX`. A run holding a `protect`ed vertex (a corner)
    stays. A ring with no accepted vertex, or none rejected, comes back as
    it is."""
    n = len(accepted)
    if n == 0 or accepted.all() or not accepted.any():
        return pts, accepted
    start = int(np.argmax(accepted))                 # rotate so index 0 is accepted
    order = (np.arange(n) + start) % n
    rej = ~accepted[order]
    prot = np.zeros(n, dtype=bool) if protect is None else protect[order]
    keep = np.ones(n, dtype=bool)
    i = 1
    while i < n:
        if not rej[i]:
            i += 1
            continue
        j = i
        while j < n and rej[j]:
            j += 1
        # rej[0] is False, so a run reaching the end wraps onto an accepted
        # vertex: it is flanked whether j == n or not.
        if j - i <= max_run and not prot[i:j].any():
            keep[order[i:j]] = False
        i = j
    return pts[keep], accepted[keep]
