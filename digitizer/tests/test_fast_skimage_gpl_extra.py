"""Gap-fillers beside `test_fast_skimage.py` / `test_charts.py`: seeded random
comparisons of the remaining `fast_skimage` functions against their skimage
references, and `gpl.parse_gpl` basics."""
import numpy as np
import pytest
from skimage.color import deltaE_ciede2000
from skimage.color.delta_e import _cart2polar_2pi as sk_cart2polar_2pi
from skimage.morphology import medial_axis as sk_medial_axis

from digitizer_core.fast_skimage import (
    _cart2polar_2pi,
    deltaE_ciede2000_1,
    medial_axis,
)
from digitizer_core.gpl import parse_gpl


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_cart2polar_matches_skimage(seed):
    rng = np.random.default_rng(seed)
    pts = rng.normal(0, 50, (500, 2))
    pts[::50] = 0.0
    pts[1::50, 1] = -0.0
    for x, y in pts:
        r_ref, t_ref = sk_cart2polar_2pi(np.float64(x), np.float64(y))
        r, t = _cart2polar_2pi(np.float64(x), np.float64(y))
        assert float(r).hex() == float(r_ref).hex()
        assert float(t).hex() == float(t_ref).hex()


def test_deltae_accepts_list_and_column_shapes():
    rng = np.random.default_rng(11)
    for _ in range(200):
        a = rng.uniform([0, -128, -128], [100, 128, 128])
        b = rng.uniform([0, -128, -128], [100, 128, 128])
        ref = float(deltaE_ciede2000(a[None], b[None])[0])
        assert deltaE_ciede2000_1(list(a), list(b)).hex() == ref.hex()
        assert deltaE_ciede2000_1(a.reshape(1, 3), b.reshape(3, 1)).hex() == ref.hex()


def test_deltae_is_symmetric_like_skimage():
    rng = np.random.default_rng(5)
    for _ in range(200):
        a = rng.uniform([0, -128, -128], [100, 128, 128])
        b = rng.uniform([0, -128, -128], [100, 128, 128])
        ref = float(deltaE_ciede2000(b[None], a[None])[0])
        assert deltaE_ciede2000_1(b, a).hex() == ref.hex()


@pytest.mark.parametrize("dtype", [np.uint8, np.float64, bool])
def test_medial_axis_non_bool_input_and_default_rng(dtype):
    rng = np.random.default_rng(9)
    for _ in range(20):
        img = (rng.random((30, 41)) > 0.4).astype(dtype)
        ref = sk_medial_axis(img, rng=5)
        got = medial_axis(img, rng=5)
        assert ref.tobytes() == got.tobytes()


def test_medial_axis_degenerate_images():
    for img in (np.zeros((8, 8), bool), np.ones((8, 8), bool), np.ones((1, 9), bool)):
        ref = sk_medial_axis(img, return_distance=True, rng=0)
        got = medial_axis(img, return_distance=True, rng=0)
        for r, g in zip(ref, got):
            assert r.tobytes() == g.tobytes()


def test_parse_gpl_basics():
    text = "\r\n".join([
        "GIMP Palette", "Name: X", "Columns: 3", "#",
        "10 20 30 Red 100",
        "1 2 3 Plain name",
        "255 0 0 1234",
        "256 0 0 Too Big 5",
        "",
    ])
    assert parse_gpl(text) == [
        ("100", "Red", (10, 20, 30)),
        ("", "Plain name", (1, 2, 3)),
        ("", "1234", (255, 0, 0)),
    ]


def test_parse_gpl_empty_and_header_only():
    assert parse_gpl("") == []
    assert parse_gpl("GIMP Palette\nName: a\nColumns: 1\n# c\n") == []


def test_parse_gpl_line_endings_agree():
    body = ["GIMP Palette", "5 6 7 Foo 42", "8 9 10 Bar 43"]
    ref = parse_gpl("\n".join(body))
    assert len(ref) == 2
    assert parse_gpl("\r\n".join(body)) == ref
    assert parse_gpl("\r".join(body)) == ref
