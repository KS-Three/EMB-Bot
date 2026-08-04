"""Direction field (directionfield.py) — technique-menu row 6.

Every accuracy assertion here is against an ANALYTICALLY KNOWN orientation:
the fixtures are generated (parallel stripes at chosen angles, concentric
rings, seeded noise, flat color), so the truth is math, not a golden. The
field is judged from its own output arrays and the per-region summary —
never by re-reading the parameters it was computed with.

Fixture conventions: a "stripes at angle A" image has its stripe LINES
running along A (y-down, degrees) — intensity varies along A's normal, so
the tangent field's truth is A itself, mod 180. Rings vary along the
radius, so the tangent truth at any pixel is the local circle tangent,
perpendicular to the radius through it.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.directionfield import (
    COHERENCE_FALLBACK_MIN,
    compute_direction_field,
    region_direction,
    region_direction_for_polygon,
    write_debug_artifact,
)
from digitizer_core.stage6_blend import SourcePixels

HERE = Path(__file__).resolve().parent
PHOTO_DIR = HERE.parent / "testdata" / "photo"

_SIZE = 200
_PERIOD = 12.0


def _stripes(angle_deg: float, size: int = _SIZE, period: float = _PERIOD) -> np.ndarray:
    """Sinusoidal stripes whose LINES run along `angle_deg` (y-down)."""
    a = math.radians(angle_deg)
    nx, ny = -math.sin(a), math.cos(a)  # the normal: intensity varies along it
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    phase = 2.0 * math.pi * (xx * nx + yy * ny) / period
    return (127.5 + 127.5 * np.sin(phase)).astype(np.uint8)


def _rings(size: int = 300, period: float = 14.0) -> np.ndarray:
    c = size / 2.0
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    r = np.hypot(xx - c, yy - c)
    return (127.5 + 127.5 * np.sin(2.0 * math.pi * r / period)).astype(np.uint8)


def _inset_mask(size: int, margin: int = 15) -> np.ndarray:
    """Interior mask keeping the border out: the tensor window and the ETF
    disc both read zero-padded pixels near the edge, and the edge is not
    what any of these fixtures is testing."""
    m = np.zeros((size, size), bool)
    m[margin:-margin, margin:-margin] = True
    return m


def _angle_diff_deg(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _salted_stripes(angle_deg: float, noise_every: int = 4, seed: int = 11) -> np.ndarray:
    """The stripes fixture with seeded salt-and-pepper orientation noise:
    1 pixel in `noise_every` replaced by pure black or white, which gives
    the local gradient there an essentially random direction."""
    img = _stripes(angle_deg).copy()
    rng = np.random.default_rng(seed)
    n = img.size // noise_every
    ys = rng.integers(0, img.shape[0], n)
    xs = rng.integers(0, img.shape[1], n)
    img[ys, xs] = np.where(rng.random(n) < 0.5, 0, 255).astype(np.uint8)
    return img


# --- Synthetic fixtures, analytically known truth ---------------------------

@pytest.mark.parametrize("angle", [0.0, 30.0, 45.0, 90.0, 117.5, 150.0])
def test_stripes_recover_the_known_angle(angle):
    field = compute_direction_field(_stripes(angle))
    rd = region_direction(field, _inset_mask(_SIZE))
    assert _angle_diff_deg(rd.angle_deg, angle) <= 2.0, (
        f"stripes at {angle}: recovered {rd.angle_deg}"
    )
    assert rd.coherence > 0.9, f"stripes must read highly coherent, got {rd.coherence}"
    assert not rd.use_house_angle


def test_rings_are_locally_tangential():
    """At any ring pixel the field must run along the local circle tangent
    (perpendicular to the radius through that pixel) — spot-checked at
    points on four different radii, including an off-axis one whose truth
    is not a round number."""
    size, c = 300, 150
    field = compute_direction_field(_rings(size))
    for dx, dy in [(80, 0), (0, 80), (60, 60), (-70, 40)]:
        # Radius direction is (dx, dy); its perpendicular (the tangent) has
        # angle atan2(dx, -dy) — mod 180, like every angle here.
        expected = math.degrees(math.atan2(dx, -dy)) % 180.0
        got = field.angle_deg_at(c + dx, c + dy)
        assert _angle_diff_deg(got, expected) <= 5.0, (
            f"at offset ({dx},{dy}): tangent {got}, expected {expected}"
        )

    # And the region SUMMARY must refuse to name one angle for a shape
    # where every direction occurs equally — that is exactly the fallback
    # signal's job, distinct from the dense field being locally right.
    rd = region_direction(field, _inset_mask(size))
    assert rd.coherence < COHERENCE_FALLBACK_MIN
    assert rd.use_house_angle


def test_uniform_noise_reads_incoherent():
    rng = np.random.default_rng(5)
    noise = rng.integers(0, 256, size=(_SIZE, _SIZE), dtype=np.uint8)
    field = compute_direction_field(noise)
    rd = region_direction(field, _inset_mask(_SIZE))
    assert rd.coherence < COHERENCE_FALLBACK_MIN, (
        f"noise coherence {rd.coherence} must sit below the fallback threshold"
    )
    assert rd.use_house_angle


def test_flat_color_is_degenerate_not_a_crash():
    flat = np.full((100, 100, 3), 137, np.uint8)
    field = compute_direction_field(flat)
    rd = region_direction(field, np.ones((100, 100), bool))
    assert rd.coherence == pytest.approx(0.0, abs=0.05)
    assert rd.use_house_angle
    # The dense field must be all-zero tangents, not NaNs.
    assert np.isfinite(field.tangent).all()
    assert float(np.abs(field.tangent).max()) == 0.0


def test_empty_mask_is_degenerate_not_a_crash():
    field = compute_direction_field(_stripes(30.0))
    rd = region_direction(field, np.zeros((_SIZE, _SIZE), bool))
    assert rd.coherence == 0.0
    assert rd.use_house_angle


# --- Determinism -------------------------------------------------------------

def test_same_input_twice_is_identical():
    img = _salted_stripes(30.0)
    a = compute_direction_field(img)
    b = compute_direction_field(img)
    assert np.array_equal(a.tangent, b.tangent)
    assert np.array_equal(a.coherence, b.coherence)
    assert np.array_equal(a.magnitude, b.magnitude)
    m = _inset_mask(_SIZE)
    assert region_direction(a, m) == region_direction(b, m)


# --- ETF actually smooths ----------------------------------------------------

def test_etf_measurably_improves_a_noise_corrupted_field():
    """The point of reimplementing Kang 2007 at all: on stripes corrupted
    with salt-and-pepper orientation noise, the post-ETF field must be
    MEASURABLY more coherent than the raw structure-tensor field — an
    asserted improvement, not "it ran". sigma=1.0 keeps the tensor's own
    Gaussian from doing ETF's job for it (at the default 2.0 the raw field
    is already 0.93 coherent and the comparison measures almost nothing;
    measured at 1.0 the raw field drops to ~0.73 while ETF recovers ~0.98,
    a gap wide enough to assert with margin)."""
    img = _salted_stripes(30.0, noise_every=4)
    m = _inset_mask(_SIZE)
    raw = region_direction(
        compute_direction_field(img, sigma=1.0, etf_iterations=0), m)
    etf = region_direction(
        compute_direction_field(img, sigma=1.0, etf_iterations=3), m)

    assert etf.coherence >= raw.coherence + 0.15, (
        f"ETF must measurably raise coherence: raw {raw.coherence}, etf {etf.coherence}"
    )
    # And it must still land on the true angle, not a smoothed-over wrong one.
    assert _angle_diff_deg(etf.angle_deg, 30.0) <= 2.0


# --- The polygon + mm<->px API ----------------------------------------------

def test_polygon_api_agrees_with_the_mask_api():
    """A polygon region routed through the SourcePixels mm<->px mapping must
    summarize the same as the equivalent hand-built pixel mask — the check
    that the mapping convention (mm = (px - origin) / px_per_mm, y-down)
    was honored rather than reinvented."""
    angle = 117.5
    img = _stripes(angle)
    field = compute_direction_field(img)
    sp = SourcePixels(rgb=np.dstack([img] * 3), px_per_mm=4.0,
                      origin_px=(_SIZE / 2.0, _SIZE / 2.0))

    # A 30x20 mm rectangle centered on the origin -> pixel box 120x80 px
    # centered at (100, 100).
    poly = Polygon([(-15, -10), (15, -10), (15, 10), (-15, 10)])
    via_poly = region_direction_for_polygon(field, poly, sp)

    mask = np.zeros((_SIZE, _SIZE), bool)
    mask[60:140, 40:160] = True
    via_mask = region_direction(field, mask)

    assert _angle_diff_deg(via_poly.angle_deg, via_mask.angle_deg) <= 0.5
    assert via_poly.coherence == pytest.approx(via_mask.coherence, abs=0.02)
    assert _angle_diff_deg(via_poly.angle_deg, angle) <= 2.0


def test_mask_shape_mismatch_raises():
    field = compute_direction_field(_stripes(0.0))
    with pytest.raises(ValueError):
        region_direction(field, np.ones((10, 10), bool))


# --- Real art smoke + the debug artifact -------------------------------------

def test_drone_render_smoke_and_debug_artifact(tmp_path):
    """The field on real photographic art (the drone render, class
    `gradient`'s founding fixture): must run end to end, produce finite
    values in range, and write the stroke-overlay debug artifact when
    cfg.debug_dir is set — the human-review record for whether the field
    follows real structure. Downscaled to 512 wide: the field is
    resolution-local, and full res costs ~20 s of pure ETF for no extra
    assertion power here."""
    bgr = cv2.imread(str(PHOTO_DIR / "drone_render.png"))
    assert bgr is not None
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    scale = 512.0 / w
    rgb = cv2.resize(rgb, (512, int(round(h * scale))), interpolation=cv2.INTER_AREA)

    field = compute_direction_field(rgb)
    assert np.isfinite(field.tangent).all()
    assert float(field.coherence.min()) >= 0.0
    assert float(field.coherence.max()) <= 1.0 + 1e-9

    rd = region_direction(field, np.ones(rgb.shape[:2], bool))
    assert 0.0 <= rd.coherence <= 1.0
    assert 0.0 <= rd.angle_deg < 180.0

    cfg = PipelineConfig(debug_dir=str(tmp_path))
    write_debug_artifact(field, rgb, cfg)
    out = tmp_path / "direction_field.png"
    assert out.is_file()
    viz = cv2.imread(str(out))
    assert viz is not None
    assert viz.shape[:2] == rgb.shape[:2]
    # Strokes were actually drawn: the render is darker somewhere than the
    # dimmed-source floor it starts from.
    assert int(viz.min()) < 60


def test_debug_artifact_respects_an_unset_debug_dir(tmp_path):
    field = compute_direction_field(_stripes(45.0, size=64))
    cfg = PipelineConfig()  # debug_dir defaults to None
    write_debug_artifact(field, np.dstack([_stripes(45.0, size=64)] * 3), cfg)
    assert list(tmp_path.iterdir()) == []
