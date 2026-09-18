"""`analyse()` and `analyse_design()` must be the same measurement.

NOT a literal pin of the numbers: that would be a platform-bound golden, and
this repo's goldens already diverge between Windows and CI. Equality of the
two paths on ONE digitize is platform-independent, and it is the property the
split actually has to keep.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from tools import dropped_elements as de  # noqa: E402
from tools import edge_smoothness as es  # noqa: E402


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    img = np.full((160, 240, 3), 255, np.uint8)
    cv2.rectangle(img, (30, 40), (110, 120), (0, 0, 0), -1)
    cv2.circle(img, (170, 80), 35, (0, 0, 200), -1)
    path = tmp_path_factory.mktemp("splits") / "tiny.png"
    cv2.imwrite(str(path), img)
    return path


@pytest.fixture(scope="module")
def digitized(tiny):
    cfg = PipelineConfig(target_width_mm=40.0, garment_id="left_chest")
    result, plan = digitize(tiny, cfg)
    return cfg, result, plan_to_design(plan)


@pytest.mark.parametrize("tool", [es, de], ids=["edge_smoothness", "dropped_elements"])
def test_analyse_equals_analyse_design_on_the_same_digitize(tool, tiny, digitized):
    cfg, result, design = digitized
    assert tool.analyse(tiny, cfg) == tool.analyse_design(
        tiny, design, route=result.design_class)


@pytest.mark.parametrize("tool", [es, de], ids=["edge_smoothness", "dropped_elements"])
def test_analyse_design_never_digitizes(tool, tiny, digitized, monkeypatch):
    _cfg, _result, design = digitized

    def boom(*_a, **_k):
        raise AssertionError("analyse_design must not digitize")

    monkeypatch.setattr(tool, "digitize", boom)
    row = tool.analyse_design(tiny, design)
    assert row["route"] is None
    assert row["fixture"] == "tiny.png"
