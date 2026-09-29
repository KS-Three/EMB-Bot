"""The crop path itself must be lossless.

Identity at crop=None is deliberately NOT tested here: a default
PipelineConfig and crop=None are the same value, so comparing them only tests
determinism. Engine-wide identity at None is carried by `apply_crop` returning
the SAME objects on None (tests/test_crop.py::
test_none_is_a_no_op_and_returns_the_same_objects) plus the existing
golden-hash tests, which run unchanged in the full suite. (No new golden is
captured: goldens here are per-platform.)

What is tested here is the case None short-circuits past: a full-frame crop
takes the crop code path and must change nothing observable.
"""
import hashlib
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, digitize
from tests.test_generation_cache import _design_bytes

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
    """Hash the design BYTES -- the canonicalization test_generation_cache.py
    trusts for its own must-never-drift comparisons -- not bare coordinates.
    Coordinates alone miss a block's thread colour, a run's jump/trim/kind/
    role and the design's reported size."""
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest", **kw)
    result, plan = digitize(ROOT / "testdata" / rel, cfg)
    h = hashlib.sha256(_design_bytes(result, plan))
    return h.hexdigest(), len(result.regions), plan.stats.stitch_count


@pytest.mark.parametrize("rel,width_mm", FIXTURES)
def test_full_frame_crop_changes_nothing_observable(rel, width_mm):
    """A (0,0,1,1) crop is the whole image. It takes the crop code path --
    unlike None, which short-circuits -- so this is the test that the path
    itself is lossless, not merely skipped."""
    assert _digest(rel, width_mm) == _digest(rel, width_mm, crop=(0.0, 0.0, 1.0, 1.0))
