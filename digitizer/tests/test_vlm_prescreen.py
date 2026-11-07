"""`tools.eye_pairs.vlm_prescreen`: the three classes at the threshold, the
screen on a made-up sitting whose answer is known, and the pin between the
module and PRESCREEN-PRE-REGISTRATION.md. Arithmetic only."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.eye_pairs import pooled, vlm_prescreen as vp

REPO = Path(__file__).resolve().parents[2]
PREREG = REPO / "docs" / "eye-pairs-2026-11-04" / "vlm-judge-100" / "PRESCREEN-PRE-REGISTRATION.md"


@pytest.fixture(autouse=True)
def _few_resamples(monkeypatch):
    monkeypatch.setattr(pooled, "B", 200)


def test_the_pre_registration_pins_the_threshold():
    text = PREREG.read_text(encoding="utf-8")
    assert vp.THRESHOLD == 4
    assert "The threshold is **4 and only 4**" in text
    assert "`confidence >= 4`" in text and "`confidence <= 3`" in text
    assert "20261104" in text and str(vp.SEED) == "20261104"


@pytest.mark.parametrize("row, cls", [
    ({"choice": "tie", "confidence": 1}, vp.NOTHING),
    ({"choice": "tie", "confidence": 5}, vp.NOTHING),
    ({"choice": "L", "confidence": 4}, vp.DAMAGED),
    ({"choice": "R", "confidence": 5}, vp.DAMAGED),
    ({"choice": "L", "confidence": 3}, vp.LOOK),
    ({"choice": "R", "confidence": 1}, vp.LOOK),
    ({"choice": None, "parse_error": "x"}, vp.LOOK),
    ({"choice": "L"}, vp.LOOK),
    (None, vp.LOOK),
])
def test_classes(row, cls):
    assert vp.classify(row) == cls


def _sitting(n_per: int = 6):
    """Live pairs, base always on the left; Kent's pick and the judge's row
    chosen per pair so the expected counts are known."""
    sealed, picks, rows = {}, {}, {}
    plan = ([("tie", "tie", 2)] * n_per          # both tie
            + [("L", "L", 5)] * n_per            # Kent base, judge base sure
            + [("R", "R", 4)] * n_per            # Kent arm, judge arm sure
            + [("R", "L", 2)] * n_per)           # Kent arm, judge base unsure -> look
    for i, (kent, judge, conf) in enumerate(plan):
        p = f"P{i:03d}"
        sealed[p] = {"kind": "live", "left_arm": "base", "right_arm": "arm", "fixture": f"f{i % 3}"}
        picks[p] = kent
        rows[p] = {"choice": judge, "choice_frame_a": judge, "confidence": conf, "reason": "r"}
    sealed["PI"] = {"kind": "identical", "left_arm": "arm", "right_arm": "arm", "fixture": "f0"}
    rows["PI"] = {"choice": "L", "choice_frame_a": "L", "confidence": 4, "reason": "r"}
    sitting = {"sealed": sealed, "picks": picks, "design_of": {f"f{k}": f"f{k}" for k in range(3)}}
    return sitting, rows, n_per


def test_screen_on_a_known_sitting():
    sitting, rows, n = _sitting()
    rep = vp.screen(sitting, rows)
    w = rep["workload"]
    assert w["n_live"] == 4 * n and w["n_kent_has_to_look"] == n and w["n_settled"] == 3 * n
    assert w["kent_side_picks"] == 3 * n and w["kent_side_picks_in_look"] == n
    assert rep["primary_settled"]["kappa_3way"] == pytest.approx(1.0)
    assert rep["damaged_class"]["n"] == 2 * n and "sides" in rep["damaged_class"]
    assert rep["tie_class"]["kappa"] == pytest.approx(1.0) and rep["tie_class"]["n"] == 4 * n
    assert rep["identical_controls"]["not_nothing_to_choose"] == ["PI"]


def test_small_damaged_class_is_listed_not_scored():
    sitting, rows, _ = _sitting(n_per=2)
    dam = vp.screen(sitting, rows)["damaged_class"]
    assert dam["n"] == 4 and "sides" not in dam and len(dam["pairs"]) == 4


def test_exclusion_leaves_every_read():
    sitting, rows, n = _sitting()
    rep = vp.screen(sitting, rows, exclude=frozenset({"P000", "P001"}))
    assert rep["n_live"] == 4 * n - 2
