"""Kent's 2026-11-15 flips of the counters worker's gap flags ("Flip both,
value 0.5"): defaults, and the OFF arm pinned in `tests/conftest.py` PRE_FLIP."""
from digitizer_core.config import PipelineConfig
from tests.conftest import PRE_FLIP


def test_satin_push_keeps_gaps_is_half_a_millimetre_and_pinned_off():
    assert PipelineConfig().satin_push_keeps_gaps == 0.5
    assert PRE_FLIP["satin_push_keeps_gaps"] is None


def test_compact_satin_keeps_gaps_is_on_and_pinned_off():
    assert PipelineConfig().compact_satin_keeps_gaps is True
    assert PRE_FLIP["compact_satin_keeps_gaps"] is False
