"""`analyse()` and `analyse_design()` must be the same measurement.

NOT a literal pin of the numbers: that would be a platform-bound golden, and
this repo's goldens already diverge between Windows and CI. Equality of the
two paths on ONE digitize is platform-independent, and it is the property the
split actually has to keep.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from tools import dropped_elements as de  # noqa: E402
from tools import edge_smoothness as es  # noqa: E402

# `tiny_logo` is conftest's: the image this module used to hand-build.


@pytest.fixture(scope="module")
def digitized(tiny_logo):
    cfg = PipelineConfig(target_width_mm=40.0, garment_id="left_chest")
    result, plan = digitize(tiny_logo, cfg)
    return cfg, result, plan_to_design(plan)


@pytest.mark.parametrize("tool", [es, de], ids=["edge_smoothness", "dropped_elements"])
def test_analyse_equals_analyse_design_on_the_same_digitize(tool, tiny_logo, digitized):
    cfg, result, design = digitized
    assert tool.analyse(tiny_logo, cfg) == tool.analyse_design(
        tiny_logo, design, route=result.design_class)


@pytest.mark.parametrize("tool", [es, de], ids=["edge_smoothness", "dropped_elements"])
def test_a_precomputed_registration_gives_the_same_row_without_registering(
        tool, tiny_logo, digitized, monkeypatch):
    from tools.artfidelity_self import register_design
    _cfg, result, design = digitized
    own = tool.analyse_design(tiny_logo, design, route=result.design_class)
    reg = register_design(tiny_logo, design)

    def boom(*_a, **_k):
        raise AssertionError("must reuse the registration it was handed")

    monkeypatch.setattr(tool, "register", boom)
    assert tool.analyse_design(tiny_logo, design, route=result.design_class,
                               registered=reg) == own


@pytest.mark.parametrize("tool", [es, de], ids=["edge_smoothness", "dropped_elements"])
def test_analyse_design_never_digitizes(tool, tiny_logo, digitized, monkeypatch):
    _cfg, _result, design = digitized

    def boom(*_a, **_k):
        raise AssertionError("analyse_design must not digitize")

    monkeypatch.setattr(tool, "digitize", boom)
    row = tool.analyse_design(tiny_logo, design)
    assert row["route"] is None
    assert row["fixture"] == "tiny.png"
