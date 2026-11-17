"""`cfg.small_text_reset_tight_word_space` (built OFF, ON since 2026-11-16, Kent): the re-set's
word-space floor read at 0.35 of the cap, not 0.5.

Measured: the USAID tagline "FROM THE AMERICAN PEOPLE" (cap 3.23 mm, median
gap 0.417 mm) has THE | AMERICAN at 0.484 of the cap, 3.75x the median, 0.053
mm under the 0.5 floor, so the re-set closed it up and sewed "THEAMERICAN".
The art is not in the repo; these lines are synthetic, built from the gaps
measured (in cap units). The 2x-median term is what keeps tracked text and
even-gapped lines whole, and what the floor stands in for when the median is
zero or negative (kerned serif pairs)."""
from __future__ import annotations

import inspect
from pathlib import Path

from digitizer_core import small_text as st
from digitizer_core.config import PipelineConfig

CAP = 3.23


def _spans(gaps_caps, width_caps=0.6):
    """x spans of letters `width_caps` wide, left to right, `gaps_caps` apart."""
    x, out = 0.0, []
    for g in [None, *gaps_caps]:
        if g is not None:
            x += g * CAP
        out.append((x, x + width_caps * CAP))
        x += width_caps * CAP
    return out


def _n(gaps_caps, tight):
    return len(st._words(_spans(gaps_caps), CAP, tight=tight))


def test_default_is_on_since_2026_11_16_and_the_pre_flip_dict_pins_it_off():
    from .conftest import TIGHT_WORD_SPACE_2026_11_16_OFF
    assert PipelineConfig().small_text_reset_tight_word_space is True
    assert PipelineConfig(**TIGHT_WORD_SPACE_2026_11_16_OFF).small_text_reset_tight_word_space is False


def test_the_tight_floor_is_a_third_of_the_cap_and_under_the_old_one():
    assert st.WORD_SPACE_CAP_TIGHT == 0.35 < st.WORD_SPACE_CAP == 0.5


def test_usaid_tagline_third_word_space_is_found_only_with_the_flag():
    gaps = [0.16, -0.03, 0.13, 0.52, 0.13, 0.23, 0.48, 0.13, 0.23, 0.16, 0.10, 0.19,
            0.06, 0.13, 0.71, 0.13, 0.13, 0.16, 0.13, 0.13]
    assert _n(gaps, tight=False) == 3       # the defect: THE | AMERICAN closed up
    assert _n(gaps, tight=True) == 4


def test_tracked_line_stays_unsplit_but_for_its_real_space():
    gaps = [0.67, 0.72, 0.82, 0.70, 0.75, 1.67, 0.69, 0.80, 0.71]
    assert _n(gaps, tight=False) == 2
    assert _n(gaps, tight=True) == 2


def test_kerned_line_with_a_non_positive_median_keeps_its_one_space():
    gaps = [0.06, -0.14, 1.45, 0.08, -0.12, -0.20]
    assert _n(gaps, tight=False) == 2
    assert _n(gaps, tight=True) == 2


def test_even_gaps_at_0_45_of_cap_are_one_word_the_median_guards_it():
    assert _n([0.45] * 8, tight=False) == 1
    assert _n([0.45] * 8, tight=True) == 1


def test_the_flag_is_wired_from_config_through_the_pipeline_to_the_item():
    assert "tight_word_space" in inspect.signature(st.enlarge_small_text).parameters
    root = Path(st.__file__).parent
    assert "cfg.small_text_reset_tight_word_space" in (root / "pipeline.py").read_text(encoding="utf-8")
    assert 'it.get("tight_word_space")' in (root / "small_text.py").read_text(encoding="utf-8")
