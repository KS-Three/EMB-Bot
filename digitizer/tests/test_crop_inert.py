"""crop=None must be the pre-crop engine, byte for byte.

The whole feature is gated on this: a crop that changes output when nobody
asked for one is a regression on every design in the corpus, and the corpus
cannot see it because every fixture would move together.
"""
import hashlib
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, digitize

ROOT = Path(__file__).resolve().parents[1]

# The four REAL_ART logos whose artwork already fills its frame, so the
# Studio's proposal is a no-op on them (measured 2026-09-22, all 1.00 x 1.00).
FIXTURES = [
    ("becker_marine_logo.png", 100.0),
    ("photo/enthusiast_logo.png", 80.0),
    ("photo/logo_hotel_fremont.webp", 92.5),
    ("photo/logo_gaulke_roofing.png", 80.0),
]


def _digest(rel, width_mm, **kw):
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest", **kw)
    result, plan = digitize(ROOT / "testdata" / rel, cfg)
    h = hashlib.sha256()
    for blk in plan.blocks:
        for run in blk.runs:
            for x, y in run.points:
                h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest(), len(result.regions), plan.stats.stitch_count


@pytest.mark.parametrize("rel,width_mm", FIXTURES)
def test_crop_none_is_byte_identical_to_omitting_it(rel, width_mm):
    assert _digest(rel, width_mm) == _digest(rel, width_mm, crop=None)


@pytest.mark.parametrize("rel,width_mm", FIXTURES)
def test_full_frame_crop_changes_nothing_observable(rel, width_mm):
    """A (0,0,1,1) crop is the whole image. It takes the crop code path --
    unlike None, which short-circuits -- so this is the test that the path
    itself is lossless, not merely skipped."""
    assert _digest(rel, width_mm) == _digest(rel, width_mm, crop=(0.0, 0.0, 1.0, 1.0))
