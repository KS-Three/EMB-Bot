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


def _assert_same_rag(ref, got):
    """Same nodes, adjacency, edges, attributes AND insertion orders —
    `merge_hierarchical` reads all of them."""
    assert got.max_id == ref.max_id and type(got.max_id) is type(ref.max_id)
    assert list(got.nodes) == list(ref.nodes)
    assert [type(n) for n in got.nodes] == [type(n) for n in ref.nodes]
    for n in ref.nodes:
        dr, dg = ref.nodes[n], got.nodes[n]
        assert list(dg) == list(dr), n
        for k, x in dr.items():
            y = dg[k]
            if isinstance(x, np.ndarray):
                assert x.dtype == y.dtype and x.tobytes() == y.tobytes(), (n, k)
            else:
                assert type(x) is type(y) and x == y, (n, k)
        assert list(got.adj[n]) == list(ref.adj[n]), n
    er, eg = list(ref.edges(data=True)), list(got.edges(data=True))
    assert [(u, v) for u, v, _ in eg] == [(u, v) for u, v, _ in er]
    for (_, _, x), (_, _, y) in zip(er, eg):
        assert list(x) == list(y) and float(x["weight"]).hex() == float(y["weight"]).hex()


def _label_images(n, seed=0):
    from skimage.segmentation import slic
    rng = np.random.default_rng(seed)
    for t in range(n):
        h, w = (int(v) for v in rng.integers(2, 90, 2))
        img = rng.random((h, w, 3)) * [100, 255, 255] - [0, 128, 128]
        if t % 3 == 0:  # salt: many tiny regions, every footprint slot used
            lab = rng.integers(0, 6, (h, w))
        elif t % 3 == 1:  # superpixels, the shape the pipeline feeds it
            lab = slic(rng.random((h, w, 3)), n_segments=30, start_label=0, channel_axis=-1)
        else:  # blocks with a masked-out label 0 sprinkled in, int32
            lab = (np.arange(h)[:, None] // 7 * 10 + np.arange(w)[None] // 9).astype(np.int32)
            lab[rng.random((h, w)) < 0.1] = 0
        yield img, lab


@pytest.mark.parametrize("connectivity", [1, 2])
@pytest.mark.parametrize("mode", ["distance", "similarity"])
def test_rag_mean_color_matches_skimage_exactly(connectivity, mode):
    from skimage.graph import rag_mean_color as sk_rag_mean_color
    from digitizer_core.fast_skimage import rag_mean_color
    compared = 0
    for img, lab in _label_images(45):
        try:
            ref = sk_rag_mean_color(img, lab, connectivity=connectivity, mode=mode)
        except KeyError:  # one label, no edges: skimage's loop has no node
            with pytest.raises(KeyError):
                rag_mean_color(img, lab, connectivity=connectivity, mode=mode)
            continue
        got = rag_mean_color(img, lab, connectivity=connectivity, mode=mode)
        _assert_same_rag(ref, got)
        compared += 1
    assert compared >= 30  # 33 of 45 on seed 0: slic on noise can give one label


def test_rag_mean_color_single_label_raises_like_skimage():
    from skimage.graph import rag_mean_color as sk_rag_mean_color
    from digitizer_core.fast_skimage import rag_mean_color
    img, lab = np.zeros((4, 5, 3)), np.ones((4, 5), int)
    with pytest.raises(KeyError):
        sk_rag_mean_color(img, lab)
    with pytest.raises(KeyError):
        rag_mean_color(img, lab)
