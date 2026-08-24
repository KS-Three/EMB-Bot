"""Stage 6 — the shade DARKNESS AXIS (`cfg.shade_axis_normalize`).

`_shade_lab_colors` buckets samples against centres pinned at 0, 1/(n-1),
... 1, and `_shade_layers` centres its membership tents on the same absolute
positions. Measured per-shape darkness spans run median 0.21-0.38 (defect 1
of the 2026-08-23 region-identification diagnosis), so a span under 0.5
cannot reach both end buckets: empty buckets are structurally guaranteed, the
bucket falls back to the region's overall mean and mints a shade duplicating
its neighbour, and that shade's tent — peaked at a darkness the region never
contains — emits nothing.

Flag on min-max normalises the axis to the region's own span, for the colour
bucketing and the membership tents TOGETHER. These tests pin the defect, the
fix, the flat-region guard, and the byte-identity of flag-off.

Fixtures follow `test_shade_palette_bind.py`'s conventions — a grey ramp
rendered into `SourcePixels`, spools derived from the live chart.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import SourcePixels, _shade_lab_colors
from digitizer_core.stage6_streamline import (
    _SHADE_AXIS_MIN_SPAN,
    _darkness_sampler,
    _shade_layers,
)
from digitizer_core.threads import CHART

_PX_PER_MM = 4.0
_POLY = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])


def _source(gray: np.ndarray) -> SourcePixels:
    h, w = gray.shape[:2]
    return SourcePixels(rgb=np.dstack([gray] * 3).astype(np.uint8),
                        px_per_mm=_PX_PER_MM, origin_px=(w / 2.0, h / 2.0))


def _band_ramp(lo_val: int, hi_val: int, w_px: int = 320, h_px: int = 240):
    """A ramp confined to a NARROW luminance band — the real-artwork case.

    A full 5..250 ramp reaches every canonical bucket and hides the defect
    entirely; the measured photo regions do not, which is the whole point.
    """
    return np.tile(np.linspace(hi_val, lo_val, w_px), (h_px, 1)).astype(np.uint8)


def _region(poly=_POLY) -> Region:
    return Region(shape_id="Stest", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area,
                  meta={"layer": 0})


def _decompose(gray: np.ndarray, *, normalize: bool):
    source = _source(gray)
    darkness = _darkness_sampler(source)
    cfg = PipelineConfig(streamline_mode="layered",
                         shade_axis_normalize=normalize)
    return _shade_layers(_POLY, source, darkness, _region(), cfg), darkness


def _emitting(shades, darkness) -> int:
    """How many layers actually put thread down anywhere on the region."""
    xs = np.linspace(-34.0, 34.0, 240)
    return sum(1 for _t, _rgb, m in shades
               if max(m(float(x), 0.0) for x in xs) > 1e-9)


# --- 1. The defect ------------------------------------------------------------

def test_a_narrow_band_region_collapses_to_one_colour_on_the_absolute_axis():
    """The measured failure, stated as what actually happens.

    A mid-tone band (darkness ~0.25-0.53) reaches no end bucket, every bucket
    falls back to the region's overall mean, and all three shades snap to the
    SAME chart thread — a decomposition in name only, sewing one colour in
    three layers.

    Note what is deliberately NOT claimed: the tents still emit here. With
    n=3 the knot is 0.5 wide, so even a centre outside the span keeps a
    partial tent over it. The defect on this fixture is duplicate COLOUR, not
    a dead layer; asserting a dead layer would be asserting something this
    span does not produce.
    """
    gray = _band_ramp(120, 190)          # a mid-tone band, no black, no white
    shades, _darkness = _decompose(gray, normalize=False)

    rgbs = [rgb for _t, rgb, _m in shades]
    assert len(shades) >= 3
    assert len(set(rgbs)) == 1, (
        f"absolute axis should collapse this band to one colour, got {set(rgbs)}")


# --- 2. The fix ---------------------------------------------------------------

def test_normalising_the_axis_removes_the_duplicates_and_wakes_the_tents():
    """Same region, flag on: every shade is a distinct colour and every layer
    emits, because the centres now sit inside the span the region has."""
    gray = _band_ramp(120, 190)
    off, _ = _decompose(gray, normalize=False)
    on, darkness = _decompose(gray, normalize=True)

    assert len(on) == len(off), "the shade COUNT is chosen upstream, unchanged"
    rgbs = [rgb for _t, rgb, _m in on]
    assert len(rgbs) == len(set(rgbs)), "no mean-fallback duplicates left"
    assert _emitting(on, darkness) == len(on), "every layer must now emit"


def test_colour_and_membership_move_together():
    """The coupling that makes this one change rather than two.

    A shade's colour is the mean of the samples nearest its centre, so if the
    bucketing moved and the tents did not, a shade would be painted a colour
    sampled from somewhere its tent never covers. Checked by walking the
    region: at the point where a shade's tent peaks, that shade's own darkness
    must be closer to it than any other shade's.
    """
    gray = _band_ramp(120, 190)
    shades, darkness = _decompose(gray, normalize=True)
    xs = np.linspace(-34.0, 34.0, 240)

    for i, (_t, _rgb, m) in enumerate(shades):
        vals = [m(float(x), 0.0) for x in xs]
        peak_x = float(xs[int(np.argmax(vals))])
        if max(vals) <= 1e-9:
            continue
        # At its own peak, this shade must own the largest share of any.
        shares = [mm(peak_x, 0.0) for _tt, _rr, mm in shades]
        assert int(np.argmax(shares)) == i, (
            f"shade {i}'s tent peaks where shade {int(np.argmax(shares))} dominates")


# --- 3. Guards ----------------------------------------------------------------

def test_a_flat_region_keeps_the_absolute_axis():
    """Below `_SHADE_AXIS_MIN_SPAN` the range is sampling noise, not tone.
    Normalising it would stretch that noise across the whole axis and invent
    shade structure the artwork does not have, so the axis stays absolute and
    the decomposition is identical either way."""
    flat = np.full((240, 320), 150, np.uint8)
    off, _ = _decompose(flat, normalize=False)
    on, _ = _decompose(flat, normalize=True)

    assert [rgb for _t, rgb, _m in off] == [rgb for _t, rgb, _m in on]
    xs = np.linspace(-34.0, 34.0, 80)
    for (_t0, _r0, m0), (_t1, _r1, m1) in zip(off, on):
        assert [m0(float(x), 0.0) for x in xs] == [m1(float(x), 0.0) for x in xs]


def test_flag_off_is_byte_identical_on_a_full_ramp_too():
    """The byte-identity guarantee is arithmetic, not a second code path:
    lo=0.0 and span=1.0 make every expression reduce to the absolute axis.
    Pinned on the full ramp the layered suite already uses."""
    full = _band_ramp(5, 250)
    a, _ = _decompose(full, normalize=False)
    b, _ = _decompose(full, normalize=False)

    assert [rgb for _t, rgb, _m in a] == [rgb for _t, rgb, _m in b]
    assert [t for t, _rgb, _m in a] == [t for t, _rgb, _m in b]


def test_the_min_span_guard_sits_far_below_real_tonal_regions():
    """Lockstep with the measurement that set it: real per-shape spans run
    median 0.21-0.38, so the guard must stay an order of magnitude below the
    smallest of those or it would start excluding genuine tonal work."""
    assert _SHADE_AXIS_MIN_SPAN < 0.21 / 5


# --- 4. The bucketing primitive ----------------------------------------------

def test_shade_lab_colors_leaves_end_buckets_empty_on_a_narrow_span():
    """`_shade_lab_colors` itself, isolated: feeding it a narrow span
    reproduces the mean-fallback duplicate, and feeding it the normalised
    axis does not. This is the arithmetic the flag moves."""
    rng = np.random.default_rng(3)
    ts = rng.uniform(0.40, 0.70, 400)            # a median-width real span
    lab = np.column_stack([ts * 100.0, np.zeros(400), np.zeros(400)])

    raw = _shade_lab_colors(ts, lab, 4)
    lo, span = float(ts.min()), float(ts.max() - ts.min())
    normed = _shade_lab_colors((ts - lo) / span, lab, 4)

    raw_l = [round(float(c[0]), 6) for c in raw]
    normed_l = [round(float(c[0]), 6) for c in normed]
    assert len(set(raw_l)) < 4, "absolute axis must collapse at least one bucket"
    assert len(set(normed_l)) == 4, "normalised axis must fill all four"
