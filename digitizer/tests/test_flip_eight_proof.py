"""`tools/flip_eight_proof.py`: the BEFORE arm of the 2026-10-23 flip is the
pre-flip engine, spelled once and agreed with the test suite's pin."""
from dataclasses import fields

from digitizer_core import PipelineConfig
from tests.conftest import FLIP_2026_10_23
from tools.flip_eight_proof import BEFORE, HELD_OFF


def test_before_is_the_suites_pre_flip_pin():
    assert BEFORE == FLIP_2026_10_23


def test_every_before_value_names_a_config_field_whose_default_moved():
    names = {f.name for f in fields(PipelineConfig)}
    cfg = PipelineConfig()
    for name, old in BEFORE.items():
        assert name in names, name
        assert getattr(cfg, name) != old, f"{name}: the default is still the pre-flip value"


def test_the_two_held_flags_are_still_off():
    # `HELD_OFF` is the 2026-10-23 sitting's record. One of the two has since
    # been flipped: `sew_enclosed_white` ON 2026-10-26 (Kent, #1112).
    cfg = PipelineConfig()
    for name in HELD_OFF:
        assert name not in BEFORE
    assert cfg.cut_every_jump is False
    assert cfg.sew_enclosed_white is True
