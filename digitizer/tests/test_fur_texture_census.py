"""`tools/fur_texture_census`: the signals read what they claim, on drawn patches.

Synthetic by design (a census test, not a corpus claim): a striped patch must
score above a flat patch on every texture signal, and above an isotropic noise
patch of the SAME strength on the two direction signals (so a signal that only
measures contrast fails). Deterministic: two reads agree to the last digit.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from tools import fur_texture_census as ftc

PPM = 8.0           # source px per mm, about the owl's 8.0
SIZE = 160          # 20 mm square


def _mask() -> np.ndarray:
    return np.ones((SIZE, SIZE), bool)


def _stripes(angle_deg: float = 20.0, amp: float = 12.0, period_mm: float = 1.2, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    th = math.radians(angle_deg)
    u = (x * math.cos(th) + y * math.sin(th)) / PPM
    return (60.0 + amp * np.sin(2 * math.pi * u / period_mm) + rng.normal(0, 0.3, (SIZE, SIZE))).astype(np.float32)


def _flat(seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (60.0 + rng.normal(0, 0.3, (SIZE, SIZE))).astype(np.float32)


def _noise(sd: float, seed: int = 3) -> np.ndarray:
    """Isotropic texture: Gaussian noise, lightly blurred, scaled to sd."""
    import cv2
    rng = np.random.default_rng(seed)
    n = cv2.GaussianBlur(rng.normal(0, 1, (SIZE, SIZE)).astype(np.float32), (0, 0), 2.0)
    return (60.0 + n * (sd / float(n.std()))).astype(np.float32)


def test_striped_patch_scores_above_flat_on_every_texture_signal():
    s = ftc.region_signals(_stripes(), _mask(), PPM)
    f = ftc.region_signals(_flat(), _mask(), PPM)
    assert s is not None and f is not None
    for sig in ("gabor_pm", "gabor_amp", "st_coh_0.5", "st_coh_1.0", "st_coh_2.0",
                "orient_rms", "grad_rms", "hf_pow"):
        assert s[sig] > f[sig], (sig, s[sig], f[sig])


def test_stripes_beat_isotropic_noise_of_equal_strength_on_direction():
    sd = float(_stripes().std())
    s = ftc.region_signals(_stripes(), _mask(), PPM)
    n = ftc.region_signals(_noise(sd), _mask(), PPM)
    assert s["gabor_pm"] > 1.5 * n["gabor_pm"], (s["gabor_pm"], n["gabor_pm"])
    assert s["st_coh_2.0"] > n["st_coh_2.0"] + 0.1, (s["st_coh_2.0"], n["st_coh_2.0"])
    assert s["st_gcoh"] > 2 * n["st_gcoh"], (s["st_gcoh"], n["st_gcoh"])


def test_gabor_amplitude_reads_the_stripe_amplitude():
    # The kernels are scaled so a matched sinusoid reads its amplitude.
    s = ftc.region_signals(_stripes(amp=10.0), _mask(), PPM)
    assert s["gabor_amp"] == pytest.approx(10.0, rel=0.15)


def test_signals_are_deterministic():
    a = ftc.region_signals(_stripes(), _mask(), PPM)
    b = ftc.region_signals(_stripes(), _mask(), PPM)
    assert a == b


def test_a_sliver_has_no_interior_and_no_reading():
    m = np.zeros((SIZE, SIZE), bool)
    m[:, 70:74] = True       # 0.5 mm wide: a stroke
    assert ftc.region_signals(_stripes(), m, PPM) is None


def test_the_region_boundary_is_not_texture():
    """A flat patch inside a very different surround: the colour step at the
    region's own edge must not read as texture (interior + extension)."""
    img = np.full((SIZE, SIZE), 95.0, np.float32)
    mask = np.zeros((SIZE, SIZE), bool)
    mask[30:130, 30:130] = True
    img[mask] = 20.0
    r = ftc.region_signals(img, mask, PPM)
    assert r is not None
    assert r["grad_rms"] < 0.5 and r["gabor_amp"] < 0.5, r


def test_auc_extremes_and_ties():
    assert ftc.auc([3, 4], [1, 2]) == 1.0
    assert ftc.auc([1, 2], [3, 4]) == 0.0
    assert ftc.auc([1], [1]) == 0.5


def test_bootstrap_auc_is_seeded_and_brackets_the_point_estimate():
    pos = [5.0, 6.0, 7.0, 8.0, 9.0]
    neg = list(np.linspace(0.0, 4.0, 20))
    a = ftc.bootstrap_auc(pos, neg, reps=300, seed=1)
    assert a == ftc.bootstrap_auc(pos, neg, reps=300, seed=1)
    assert a[0] == 1.0 and a[1] <= a[0] <= a[2]
    mixed = ftc.bootstrap_auc([1.0, 5.0], list(np.linspace(0.0, 6.0, 12)), reps=300, seed=1)
    assert mixed[1] < 0.9, "two positives straddling the negatives cannot clear 0.9"


def _fake_rows(owl_val: float, logo_vals: list[float], flat_val: float = 0.0) -> dict:
    """A rows.json-shaped dict with ONE value for every signal: the owl's plumage
    regions at `owl_val`, each logo's regions at `logo_vals`."""
    def reg(rid, v, width=4.0):
        return {"id": rid, "area_mm2": 100.0, "width_mm": width, **{s: v for s in ftc.SIGNALS}}
    rows = {"owl": {"erode_mm": 0.5,
                    "regions": [reg("S4666f9bf", owl_val, 7.0)] + [reg(i, 1.0) for i in ftc.FENCE["owl"]]},
            "owl_classical": {"erode_mm": 0.5,
                              "regions": [reg(i, owl_val) for i in ftc.FUR_POSITIVES["owl_classical"]]},
            "grass": {"erode_mm": 0.5, "regions": [reg("Sg", 2.0)]},
            "fur_ramp": {"erode_mm": 0.5, "regions": [reg("Sr", flat_val)]}}
    for k, name in enumerate(ftc.LOGOS):
        rows[name] = {"erode_mm": 0.5, "regions": [reg(f"L{k}{j}", v) for j, v in enumerate(logo_vals)]}
    return rows


def test_table_says_clears_only_when_the_owl_is_past_every_logo_region():
    above = ftc.table_rows(_fake_rows(10.0, [1.0, 2.0, 3.0, 4.0]))
    assert all(t["clears"] == "above" and t["auc_lo"] > ftc.CLEAR_AUC for t in above)
    below = ftc.table_rows(_fake_rows(0.5, [1.0, 2.0, 3.0, 4.0]))
    assert all(t["clears"] == "below" for t in below)
    # One logo region level with the owl: the margin is gone, nothing clears.
    tied = ftc.table_rows(_fake_rows(3.0, [1.0, 3.0, 5.0]))
    assert all(t["clears"] == "no" for t in tied)


def test_wide_only_drops_the_strokes():
    rows = _fake_rows(10.0, [1.0, 2.0])
    for name in ftc.LOGOS:
        rows[name]["regions"][0]["width_mm"] = 1.0       # a stroke
    full = ftc.table_rows(rows)[0]
    wide = ftc.table_rows(rows, wide_only=True)[0]
    assert wide["n_neg"] == full["n_neg"] // 2
