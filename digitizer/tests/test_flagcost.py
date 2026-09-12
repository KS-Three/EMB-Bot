"""`tools/pro_parity/flagcost.py` — what each default-ON flag costs in clock.

The harness's first version reported three provably-inert flags as costing
~13% of a design, because it timed the baseline before any other run and so
charged every flag for the process's warm-up. These tests pin the two things
that made the second version trustworthy: the flag list matching real config
fields, and the noise floor actually suppressing a difference smaller than the
run-to-run drift.
"""
from __future__ import annotations

from digitizer_core import PipelineConfig
from tools.pro_parity import flagcost as fc


def test_every_flag_is_a_real_config_field_with_a_different_off_value():
    """A typo here would set a stray attribute nothing reads and report the
    flag as free — the same silent-wrong-configuration failure `parity_config`
    guards against for its own env vars."""
    fields = PipelineConfig.__dataclass_fields__
    default = PipelineConfig()
    for flag, off in fc.FLAGS.items():
        assert flag in fields, flag
        assert getattr(default, flag) != off, (
            f"{flag}'s off value {off!r} IS the shipped default, so its arm "
            f"would measure nothing")


def test_the_off_value_is_accepted_by_the_config():
    """`parity_config` builds a real `PipelineConfig`; an off value of the
    wrong type would only surface deep in a stage, halfway through a sweep."""
    for flag, off in fc.FLAGS.items():
        cfg = PipelineConfig()
        setattr(cfg, flag, off)
        assert getattr(cfg, flag) == off


def test_width_mm_strips_the_padding_prep_all_added():
    """`prep_all` digitizes at the PRO bounds' width; `art_meta` records the
    padded raster. Getting this wrong rescales every design and every timing
    with it."""
    meta = {"size_px": [1046, 629], "pad_px": 60, "scale_px_per_mm": 10}
    assert fc._width_mm(meta) == 92.6


def test_a_difference_under_the_drift_is_not_reported_as_a_cost():
    """The bug the second version exists to prevent: a flag whose arm differs
    from the baseline by less than the baseline differs from ITSELF is not a
    measurement, and must not be ranked as one.

    The numbers are `machine_hat`'s own run — drift 1.85 s, with
    `enclosed_by_garment` at 1.44 s inside it and `fill_travel_under_cover` at
    54.60 s well outside.
    """
    assert fc.verdict(1.44, 1.85, same=True) == "under the noise floor"
    assert fc.verdict(1.44, 1.85, same=False) == "under the noise floor"
    assert fc.verdict(54.60, 1.85, same=False) == "changes output"
    assert fc.verdict(-2.98, 1.85, same=False) == "changes output"


def test_the_noise_floor_outranks_the_inert_reading():
    """"INERT here" claims two things — costs nothing AND does nothing. Under
    the floor only the second is known, so the floor has to win."""
    assert fc.verdict(0.3, 1.0, same=True) == "under the noise floor"
    assert fc.verdict(3.0, 1.0, same=True) == "INERT here"
