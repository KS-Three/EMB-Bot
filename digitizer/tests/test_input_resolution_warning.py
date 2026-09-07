"""`INPUT_LOW_RESOLUTION` fires on what the SOURCE delivered.

The warning existed, the Studio had it in `ATTENTION_WARNINGS`, and it could
not fire. Stage 1's test re-read `px_per_mm` AFTER the Lanczos rescue, and
with `upscale_cap` and `min_px_per_mm` both 4.0 the capped upscale lands any
source at or above 1.0 px/mm exactly ON the floor — so the condition was false
for every design a customer could send.

What it cost: `docs/kent-review-2026-09-03.md` reports two of its three
renders as settled before the engine ran — *"the source is 146 pixels wide for
a 100 mm design"*, *"a higher-resolution Becker source would change this
render more than any engine change"* — and neither run said so. Measured over
the scorecard's 26 fixtures, exactly **two** arrive under the floor:
`becker_marine_logo` at 1.81 px/mm and `logo_bridge_bar` at 3.49 (80 mm). Two
of 26 is a precise warning, not a noisy one, which is why firing it on the
source is safe.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.warnings_codes import INPUT_LOW_RESOLUTION

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
BECKER = TESTDATA / "becker_marine_logo.png"
BRIDGE = TESTDATA / "photo" / "logo_bridge_bar.jpg"
FREMONT = TESTDATA / "photo" / "logo_hotel_fremont.webp"


def _warning(path: Path, mm: float) -> dict | None:
    p = prep(path, PipelineConfig(target_width_mm=mm, garment_id="left_chest"))
    found = [w for w in p.warnings if w["code"] == INPUT_LOW_RESOLUTION]
    return found[0] if found else None


@pytest.mark.parametrize("path,mm", [(BECKER, 100.0), (BECKER, 80.0), (BRIDGE, 80.0)])
def test_a_source_under_the_floor_says_so(path, mm):
    """The two fixtures whose renders were decided by their own pixel count."""
    assert _warning(path, mm) is not None, f"{path.name} @ {mm} mm stayed silent"


def test_a_source_over_the_floor_stays_quiet(*_):
    assert _warning(FREMONT, 80.0) is None, "31 px/mm is not a low-resolution design"


def test_the_reported_number_is_the_SOURCE_not_the_upscale():
    """The old warning reported the post-upscale value, which is always the
    floor — a constant dressed as a measurement. `px_per_mm` is what the file
    gave; `upscaled_to` is what stage 1 made of it."""
    w = _warning(BECKER, 100.0)
    assert w is not None
    assert w["px_per_mm"] == pytest.approx(1.45, abs=0.05), w["px_per_mm"]
    assert w["upscaled_to"] == pytest.approx(4.0), w["upscaled_to"]
    assert w["min_px_per_mm"] == pytest.approx(4.0)


def test_the_message_carries_both_numbers():
    """An operator can act on "1.4 at 100 mm, needs 4"; they cannot act on
    "resolution is low"."""
    w = _warning(BECKER, 100.0)
    assert "1.4" in w["message"] and "100 mm" in w["message"]


def test_the_floor_is_reachable_only_by_enlargement():
    """The property that made the old condition dead, pinned so a future
    change to either constant cannot quietly restore it: with the cap equal
    to the floor, any source at or above 1.0 px/mm ends up exactly on the
    floor, so a post-upscale test can never fire."""
    cfg = PipelineConfig()
    assert cfg.upscale_cap == cfg.min_px_per_mm
    for src in (1.0, 1.81, 3.49, 3.99):
        want = min(cfg.upscale_cap, cfg.min_px_per_mm / src)
        assert src * want == pytest.approx(cfg.min_px_per_mm), src
