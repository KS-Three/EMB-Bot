"""The 2026-11-19 speed pass changes no number: each cut against the code it replaced.

Like `test_speed_exact_1116.py`: every function here was rewritten for speed
only, and each test holds the new form equal (`np.array_equal`, not approx) to
the old one, restated in the test.
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core import stage2_photo_segment as ps


def _snap_full_frame(labels, valid, lab_img, margin=ps.SNAP_MARGIN_LAB,
                     max_passes=ps.SNAP_MAX_PASSES):
    """`snap_region_edges` as it was until 2026-11-19: every pass reads the whole frame."""
    out = labels.copy()
    h, w = out.shape
    ids = out[valid]
    if ids.size == 0:
        return out
    n = int(ids.max()) + 1
    count = np.maximum(np.bincount(ids, minlength=n), 1)
    means = np.stack(
        [np.bincount(ids, weights=lab_img[..., c][valid], minlength=n) / count
         for c in range(3)], axis=1)
    pad_lab = np.pad(out, 1, constant_values=-1)
    pad_valid = np.pad(valid, 1, constant_values=False)
    for _ in range(max_passes):
        pad_lab[1:-1, 1:-1] = out
        edge = np.zeros((h, w), bool)
        for dy, dx in ps._NEIGHBOURS_8:
            nb = pad_lab[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            nbv = pad_valid[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            edge |= nbv & (nb != out)
        edge &= valid
        ys, xs = np.nonzero(edge)
        if ys.size == 0:
            break
        px = lab_img[ys, xs]
        own = out[ys, xs]
        best = own.copy()
        best_d = np.linalg.norm(px - means[own], axis=1)
        need = best_d - margin
        for dy, dx in ps._NEIGHBOURS_8:
            ny, nx = ys + dy + 1, xs + dx + 1
            ok = pad_valid[ny, nx]
            cand = pad_lab[ny, nx]
            ok &= cand != own
            if not ok.any():
                continue
            d = np.full(ys.size, np.inf)
            d[ok] = np.linalg.norm(px[ok] - means[cand[ok]], axis=1)
            take = ok & (d < need) & (d < best_d)
            best[take] = cand[take]
            best_d[take] = d[take]
        moved = best != own
        if not moved.any():
            break
        out[ys[moved], xs[moved]] = best[moved]
    return out


def _blocky_scene(seed, h, w, block, k, valid_frac):
    """Superpixel-like labels (blocks) over a smooth colour field: edges to snap."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    # true regions: a few discs and bands, coloured; noise on top
    truth = ((xx // 23 + yy // 17) % k).astype(np.int32)
    for _ in range(4):
        cy, cx, r = rng.integers(0, h), rng.integers(0, w), rng.integers(5, max(6, h // 3))
        truth[(yy - cy) ** 2 + (xx - cx) ** 2 < r * r] = rng.integers(0, k)
    palette = rng.random((k, 3)) * np.array([100.0, 120.0, 120.0]) - np.array([0.0, 60.0, 60.0])
    lab = palette[truth] + rng.normal(0, 3.0, (h, w, 3))
    # labels: majority truth per block (a superpixel's union of whole blocks)
    labels = np.empty((h, w), np.int32)
    for by in range(0, h, block):
        for bx in range(0, w, block):
            t = truth[by:by + block, bx:bx + block]
            labels[by:by + block, bx:bx + block] = np.bincount(t.ravel()).argmax()
    valid = rng.random((h, w)) > (1 - valid_frac) if valid_frac < 1 else np.ones((h, w), bool)
    return labels, valid, lab


@pytest.mark.parametrize("seed, h, w, block, k, valid_frac", [
    (1, 40, 50, 7, 3, 1.0),
    (2, 97, 83, 11, 5, 1.0),
    (3, 120, 140, 9, 4, 0.9),
    (4, 64, 64, 16, 2, 1.0),
    (5, 150, 90, 13, 6, 0.97),
])
@pytest.mark.parametrize("margin", [0.0, ps.SNAP_MARGIN_LAB, 8.0])
def test_snap_region_edges_is_the_full_frame_loop(seed, h, w, block, k, valid_frac, margin):
    labels, valid, lab = _blocky_scene(seed, h, w, block, k, valid_frac)
    want = _snap_full_frame(labels, valid, lab, margin=margin)
    got = ps.snap_region_edges(labels, valid, lab, margin=margin)
    assert np.array_equal(got, want)
    assert not np.array_equal(want, labels)            # the case moved pixels


@pytest.mark.parametrize("passes", [1, 2, 3])
def test_snap_region_edges_pass_cap_is_unchanged(passes):
    labels, valid, lab = _blocky_scene(7, 90, 90, 15, 4, 1.0)
    assert np.array_equal(ps.snap_region_edges(labels, valid, lab, max_passes=passes),
                          _snap_full_frame(labels, valid, lab, max_passes=passes))


def test_snap_region_edges_empty_valid():
    labels, _valid, lab = _blocky_scene(8, 20, 20, 5, 3, 1.0)
    none = np.zeros(labels.shape, bool)
    assert np.array_equal(ps.snap_region_edges(labels, none, lab), labels)


# --- stage 6 border: the corner relaxation's rolls ------------------------------------

from digitizer_core import stage6_border as border  # noqa: E402


@pytest.mark.parametrize("n", [1, 2, 7, 8, 33])
@pytest.mark.parametrize("s", [-40, -9, -1, 0, 1, 3, 8, 41])
def test_roll0_is_np_roll(n, s):
    a = np.random.default_rng(n * 100 + s + 50).random((n, 2))
    got = border._roll0(a, s)
    assert np.array_equal(got, np.roll(a, s, axis=0))
    assert got is not a


@pytest.mark.parametrize("n", [3, 8, 9, 17, 64, 301])
@pytest.mark.parametrize("k", [0, 1, 2, 4, 8, 75, 200])
@pytest.mark.parametrize("density", [0.0, 0.03, 0.3, 1.0])
def test_window_any_is_the_roll_loop(n, k, density):
    flag = np.random.default_rng(n * 7 + k).random(n) < density
    want = np.zeros(n, dtype=bool)
    for s in range(-k, k + 1):
        want |= np.roll(flag, s)
    assert np.array_equal(border._window_any(flag, k), want)


def _relax_corners_rolls(pts, r_corner, k):
    """`_relax_corners` as it was until 2026-11-19, with `np.roll` throughout."""
    n = len(pts)
    if n < 8:
        return pts
    p = np.asarray(pts, dtype=float)
    p0 = p.copy()

    def turn_radius(q):
        a, b, c = np.roll(q, k, axis=0), q, np.roll(q, -k, axis=0)
        ab = np.hypot(*(b - a).T)
        bc = np.hypot(*(c - b).T)
        ca = np.hypot(*(a - c).T)
        cross = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
                       - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(cross > 1e-12, ab * bc * ca / (2.0 * cross), np.inf)

    for _ in range(border._RELAX_ITERS):
        sharp = turn_radius(p) < r_corner
        if not sharp.any():
            break
        mask = np.zeros(n, dtype=bool)
        for s in range(-k, k + 1):
            mask |= np.roll(sharp, s)
        moved = 0.25 * np.roll(p, 1, axis=0) + 0.5 * p + 0.25 * np.roll(p, -1, axis=0)
        new = np.where(mask[:, None], moved, p)
        disp = new - p0
        d = np.hypot(disp[:, 0], disp[:, 1])
        over = d > border._BITE_MAX_MM
        if over.any():
            scale = (border._BITE_MAX_MM / np.where(d > 1e-12, d, 1.0))[:, None]
            new = np.where(over[:, None], p0 + disp * scale, new)
        if float(np.abs(new - p).max()) < 1e-5:
            p = new
            break
        p = new
    return [(float(x), float(y)) for x, y in p]


def _star(n_pts, r_out, r_in, step):
    from shapely.geometry import Polygon as P
    ang = np.linspace(0, 2 * np.pi, 2 * n_pts, endpoint=False)
    rad = np.where(np.arange(2 * n_pts) % 2 == 0, r_out, r_in)
    ring = P(np.c_[rad * np.cos(ang), rad * np.sin(ang)]).exterior
    m = max(8, int(round(ring.length / step)))
    return [ring.interpolate(ring.length * i / m).coords[0] for i in range(m)]


@pytest.mark.parametrize("shape", ["star", "square", "sliver", "circle"])
@pytest.mark.parametrize("r_corner, step", [(2.1, 0.25), (1.0, 0.1), (3.0, 0.5)])
def test_relax_corners_is_the_roll_loop(shape, r_corner, step):
    if shape == "star":
        pts = _star(5, 10.0, 4.0, step)
    elif shape == "square":
        pts = _star(2, 10.0, 10.0, step)          # a square on its corner: four right angles
    elif shape == "sliver":
        pts = _star(2, 12.0, 0.8, step)          # a thin diamond: two spike tips
    else:
        pts = _star(40, 8.0, 7.99, step)
    k = max(1, int(round(r_corner / step)))
    k = min(k, max(1, len(pts) // 4))
    got = border._relax_corners(pts, r_corner, k)
    assert got == _relax_corners_rolls(pts, r_corner, k)
    if shape != "circle":
        assert got != [tuple(map(float, q)) for q in pts]          # the case relaxed something
