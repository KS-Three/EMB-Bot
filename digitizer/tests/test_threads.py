import numpy as np

from digitizer_core.threads import CHART, nearest_thread_index, rgb_to_lab


def test_chart_is_complete_and_well_formed():
    assert len(CHART) >= 390
    for t in CHART:
        assert t.number and isinstance(t.number, str)
        assert t.name and isinstance(t.name, str)
        assert len(t.rgb) == 3
        assert all(isinstance(v, int) and 0 <= v <= 255 for v in t.rgb)
    assert len({t.number for t in CHART}) == len(CHART), "duplicate catalog numbers"


def test_every_chart_color_matches_itself():
    # A thread's own RGB must resolve back to that thread — the sanity floor
    # for any color-matching change.
    for i, t in enumerate(CHART):
        lab = rgb_to_lab(np.array([t.rgb], np.float64))[0]
        j = nearest_thread_index(lab)
        assert CHART[j].rgb == t.rgb, f"{t.number} {t.name} matched {CHART[j].number}"


def test_dark_navy_matches_a_navy_not_a_grey():
    # Regression: CIE76 sent this to grey "Concord Fog" (57,52,87). The
    # perceptual metric must keep dark saturated colors in their own family.
    lab = rgb_to_lab(np.array([[20, 40, 90]], np.float64))[0]
    t = CHART[nearest_thread_index(lab)]
    assert t.number == "3363", f"expected Midnight Blue, got {t.number} {t.name}"
    r, g, b = t.rgb
    assert b > r + 20, "matched thread is not blue-dominant"


def test_matching_is_deterministic():
    lab = rgb_to_lab(np.array([[128, 128, 128]], np.float64))[0]
    assert len({nearest_thread_index(lab) for _ in range(5)}) == 1
