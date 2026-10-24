"""The Column lane's connectors over its own finished satin:
`cfg.lettering_columns_cover_connectors` (2026-10-20).

The Becker survey (2026-10-20) saw strands laid across MARINE's letters in
the render: travel the Euler walk ran ON TOP of columns the letter had
already finished. The walk orders spans at NODE resolution, and a node is
every column end within `merge_r` (1.3 stroke widths + pad + pull: 6.8 mm on
Becker's 4.75 mm strokes), so two legs that meet "at one node" can end and
start 7 mm apart with a finished column between; the hop between them is a
straight connector across it. ON, a connector chain whose part on earlier
satin that no later satin buries passes `trim_at_mm` (the strand the
sew-or-jump rule already tolerates) is cut: a jump, a trim past `trim_at_mm`.

`tools/column_travel_cover.py` is the instrument (`over_mm` is the survey's
`travel_over.py` reading; `exposed_mm` subtracts what later satin covers).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, columns
from tests.conftest import PRE_FLIP, own_thread_only
from tools import column_ends as ce
from tools.column_travel_cover import shape_travel

BECKER = Path(__file__).resolve().parent.parent / "testdata" / "becker80_lane_letters.json"
TODAY = dict(fold_cuts=True, square_ends=True, inside_connectors=True)


@pytest.fixture(scope="module")
def becker():
    return ce.load_letters(BECKER)


@pytest.fixture(scope="module")
def arms(becker):
    return {"off": _sum(becker), "on": _sum(becker, cover_connectors=True)}


def _sum(letters, **arm):
    tot = {"exposed_mm": 0.0, "cut_candidates": 0, "trims": 0}
    for poly, kw in letters.values():
        runs, _rep = columns.lettering_columns_shape(poly, "pin", **kw, **TODAY, **arm)
        t = shape_travel(runs, kw["trim_at_mm"])
        tot["exposed_mm"] += t["exposed_mm"]
        tot["cut_candidates"] += t["cut_candidates"]
        tot["trims"] += sum(1 for r in runs if r.trim)
    return tot


def test_the_flag_is_built_off():
    """Built OFF (the cut connectors cost trims: Becker 95.7 mm lc 27 -> 32);
    the flip is Kent's. Not flipped, so no `PRE_FLIP` entry, and not in
    `flagcost.FLAGS` (its list of default-ON flags)."""
    from tools.pro_parity.flagcost import FLAGS
    assert PipelineConfig().lettering_columns_cover_connectors is False
    assert "lettering_columns_cover_connectors" not in PRE_FLIP
    assert "lettering_columns_cover_connectors" not in FLAGS


def test_becker_marine_strands_over_finished_satin_are_cut(arms):
    """MARINE at 80 mm, today's lane: OFF four of the six letters (A, R, N,
    E) leave 22.0 mm of travel on satin they already sewed that nothing
    sewn later covers, four connector chains each past the 3 mm trim
    distance. ON no chain is past it; what stays (the N's 2.6 mm) is under
    the limit, and the four cut chains cost four trims."""
    off, on = arms["off"], arms["on"]
    assert off["cut_candidates"] == 4
    assert off["exposed_mm"] == pytest.approx(22.0, abs=0.1)
    assert on["cut_candidates"] == 0
    assert on["exposed_mm"] == pytest.approx(2.6, abs=0.1)
    assert on["trims"] - off["trims"] == 4


def test_off_never_reaches_the_new_code(becker, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("cover_connectors code reached with the flag off")
    monkeypatch.setattr(columns, "_cut_exposed_connectors",
                        own_thread_only(boom, columns._cut_exposed_connectors))
    for poly, kw in becker.values():
        columns.lettering_columns_shape(poly, "off", **kw, **TODAY)


def test_stage7_passes_the_flag(monkeypatch):
    """The stage 7 call carries `cover_connectors` exactly when the flag is on."""
    from digitizer_core import digitize
    from digitizer_core import stage7_sequence as s7
    from tools import lowercase_angle as la
    seen = []
    real = s7.lettering_columns_shape

    def spy(poly, shape_id, **kw):
        seen.append(kw.get("cover_connectors"))
        return real(poly, shape_id, **kw)

    monkeypatch.setattr(s7, "lettering_columns_shape", own_thread_only(spy, real))
    digitize(la.FIXTURE.with_suffix(".png"),
             PipelineConfig(target_width_mm=80.0, forced_class="flat",
                            lettering_columns_cover_connectors=True))
    assert seen and all(v is True for v in seen)
    seen.clear()
    digitize(la.FIXTURE.with_suffix(".png"), PipelineConfig(target_width_mm=80.0, forced_class="flat"))
    assert seen and all(v is None for v in seen)
