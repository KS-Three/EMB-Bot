"""`beanletters.INK_SHAPE_MAX_RATIO` (2026-10-14, a gate-1 CANDIDATE): a
member whose traced shape is far wider than its ink read is no bean letter.
Drone's chrome "PRECISION" read 0.28-0.35 mm of ink off the highlight between
its bevel lines while its traced letters are 1.6-2.0 mm wide, and sewed as
hollow outlines under the true-size arms (PR #944). The unit cases live in
`test_bean_letters_units.py`; this file pins that OFF is the engine as it was
(the flat-lane goldens' md5, as `test_small_dot_rung.py` pins them) and that
the gate moves nothing on those goldens with the true-size switch ON.
"""
from __future__ import annotations

import hashlib
import json
import math

import pytest

from digitizer_core import PipelineConfig, beanletters, digitize

from .conftest import TESTDATA

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _md5(fixture: str, **kw) -> str:
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none", **kw))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def test_the_candidate_sits_between_the_measured_populations():
    # every bean letter that should go read 0.66-1.34x; bridge's
    # counter-closed blobs 2.11-2.28x; drone's chrome letters 4.73-6.70x.
    assert 2.28 < beanletters.INK_SHAPE_MAX_RATIO < 4.73


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_off_is_byte_identical(fixture):
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    coords_md5 = hashlib.md5(json.dumps(golden["stitch_coords"]).encode()).hexdigest()
    assert coords_md5 == GOLDEN_MD5[fixture]
    assert _md5(fixture) == GOLDEN_MD5[fixture]


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_gate_moves_nothing_on_the_goldens_with_true_size_on(fixture, monkeypatch):
    on = _md5(fixture, small_text_true_size=True)
    monkeypatch.setattr(beanletters, "INK_SHAPE_MAX_RATIO", math.inf)     # the tagger before the gate
    assert _md5(fixture, small_text_true_size=True) == on
