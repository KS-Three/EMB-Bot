"""`fast_skimage` must return what scikit-image returns, bit for bit — the
whole point of it is a faster call with byte-identical stitch output. These
are the tripwire for a `scikit-image` bump changing either function."""
import numpy as np
import pytest
from scipy import ndimage as ndi
from skimage.color import deltaE_ciede2000
from skimage.morphology import medial_axis as sk_medial_axis

from digitizer_core.fast_skimage import deltaE_ciede2000_1, medial_axis


def _pairs(n, seed=1):
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = np.array([rng.uniform(0, 100), rng.uniform(-128, 128), rng.uniform(-128, 128)])
        if k % 2:
            b = a + rng.normal(0, [1, 5, 30][k % 3], 3)
        else:
            b = np.array([rng.uniform(0, 100), rng.uniform(-128, 128), rng.uniform(-128, 128)])
        if k % 7 == 0:  # achromatic: the CC == 0 branches
            a[1] = a[2] = 0.0
        if k % 11 == 0:  # signed zero through arctan2
            b[1], b[2] = 0.0, -0.0
        yield a, b


def test_deltae_scalar_matches_skimage_bit_for_bit():
    for a, b in _pairs(20000):
        ref = float(deltaE_ciede2000(a.reshape(1, 3), b.reshape(1, 3))[0])
        assert deltaE_ciede2000_1(a, b).hex() == ref.hex(), (a, b)


def test_deltae_scalar_identical_colours_is_zero():
    a = np.array([50.0, 10.0, -20.0])
    assert deltaE_ciede2000_1(a, a) == float(deltaE_ciede2000(a[None], a[None])[0])


@pytest.mark.parametrize("kw", [
    {"rng": 0},
    {"rng": 0, "return_distance": True},
    {"rng": 7, "mask": "random"},
])
def test_medial_axis_matches_skimage_bit_for_bit(kw):
    rng = np.random.default_rng(3)
    for _ in range(60):
        img = rng.random((int(rng.integers(5, 70)), int(rng.integers(5, 70)))) > rng.uniform(0.2, 0.7)
        img = ndi.binary_closing(img, iterations=int(rng.integers(0, 3)))
        call = dict(kw)
        if call.get("mask") == "random":
            call["mask"] = rng.random(img.shape) > 0.2
        ref = sk_medial_axis(img, **call)
        got = medial_axis(img, **call)
        ref = ref if isinstance(ref, tuple) else (ref,)
        got = got if isinstance(got, tuple) else (got,)
        for r, g in zip(ref, got):
            assert r.dtype == g.dtype and r.shape == g.shape
            assert r.tobytes() == g.tobytes()
