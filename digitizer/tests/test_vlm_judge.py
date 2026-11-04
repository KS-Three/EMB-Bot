"""`tools.eye_pairs.vlm_judge`: the two frames, the sealed-key mapping, the
analysis on a made-up sitting whose answer is known, and the pin between the
module and its pre-registration. Nothing here touches the API."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.eye_pairs import pooled, vlm_judge as vj

REPO = Path(__file__).resolve().parents[2]
PREREG = REPO / "docs" / "eye-pairs-2026-11-04" / "vlm-judge" / "PRE-REGISTRATION.md"


@pytest.fixture(autouse=True)
def _few_resamples(monkeypatch):
    """The intervals are not under test; 10,000 resamples x 24 bootstraps per
    analyse() is seconds for nothing."""
    monkeypatch.setattr(pooled, "B", 200)


# ------------------------------------------------------------- the pin ----

def test_the_pre_registration_pins_this_module():
    text = PREREG.read_text(encoding="utf-8")
    s = vj.settings()
    assert s["prompt_sha256"] in text, "PRE-REGISTRATION.md does not carry the prompt's sha256"
    assert vj.PROMPT.splitlines()[0] in text, "the prompt is not quoted verbatim"
    assert f"`{s['effort']}`" in text and f"`max_tokens` {s['max_tokens']}" in text
    for model in s["models"]:
        assert f"`{model}`" in text, f"{model} is not named"
    assert "order B" in text and "swapped" in text


# ------------------------------------------------------------ the frames ----

def test_frame_a_swaps_only_order_b_sides():
    assert [vj.frame_a(c, "A") for c in ("L", "R", "tie")] == ["L", "R", "tie"]
    assert [vj.frame_a(c, "B") for c in ("L", "R", "tie")] == ["R", "L", "tie"]
    for c in ("L", "R", "tie"):           # its own inverse
        assert vj.frame_a(vj.frame_a(c, "B"), "B") == c


def test_to_label_reads_the_sealed_key():
    s = {"left_arm": "base", "right_arm": "lane_off"}
    assert [vj.to_label(c, s) for c in ("L", "R", "tie")] == ["before", "after", "tie"]
    s = {"left_arm": "lane_off", "right_arm": "base"}
    assert [vj.to_label(c, s) for c in ("L", "R", "tie")] == ["after", "before", "tie"]
    assert vj.to_label("L", {"left_arm": "base", "right_arm": "base"}) is None


def test_parse_verdict_takes_plain_json_and_a_stray_fence():
    v = vj.parse_verdict('{"choice": "L", "confidence": 4, "reason": "x"}')
    assert v["choice"] == "L" and v["confidence_in_range"]
    v = vj.parse_verdict('```json\n{"choice": "tie", "confidence": 9, "reason": "x"}\n```')
    assert v["choice"] == "tie" and not v["confidence_in_range"]
    with pytest.raises(ValueError):
        vj.parse_verdict('{"choice": "left", "confidence": 3, "reason": ""}')


# ------------------------------------------------- a sitting with an answer ----

def _sitting(n_live: int = 12) -> dict:
    """12 live pairs over four designs, Kent cycling L / R / tie, the base on
    the left in every other pair; one identical pair, one repeat of P001."""
    sealed, picks, design_of, expected = {}, {}, {}, {}
    arms = ("corner_fold_off", "lane_off")
    for i in range(n_live):
        pid, fx = f"P{i + 1:03d}", f"logo{i % 4}"
        design_of[fx] = f"d{i % 4}"
        base_left = i % 2 == 0
        sealed[pid] = {"fixture": fx, "kind": "live", "repeat_of": None, "design_only": False,
                       "left_arm": "base" if base_left else arms[i % 2],
                       "right_arm": arms[i % 2] if base_left else "base"}
        picks[pid] = ("L", "R", "tie")[i % 3]
        expected[pid] = "before" if i % 2 == 0 else "after"
    sealed["P013"] = {"fixture": "logo0", "kind": "identical", "repeat_of": None, "design_only": False,
                      "left_arm": "base", "right_arm": "base"}
    picks["P013"] = "tie"
    sealed["P014"] = dict(sealed["P001"], kind="repeat", repeat_of="P001")
    picks["P014"] = picks["P001"]
    return {"sealed": sealed, "picks": picks, "design_of": design_of,
            "passing_arms": ["corner_fold_off"], "expected": expected}


def _verdicts(sitting: dict, choose) -> dict:
    """choose(pid, order) -> the judge's choice IN THAT ORDER'S OWN FRAME."""
    out: dict = {"m": {"A": {}, "B": {}}}
    for order in ("A", "B"):
        for pid in sitting["sealed"]:
            c = choose(pid, order)
            out["m"][order][pid] = {"pair": pid, "order": order, "model": "m", "choice": c,
                                    "choice_frame_a": vj.frame_a(c, order), "confidence": 4,
                                    "reason": "r", "input_tokens": 10, "output_tokens": 1,
                                    "stop_reason": "end_turn"}
    return out


def _like_kent(kent):
    return lambda pid, order: kent[pid] if order == "A" else vj.frame_a(kent[pid], "B")


def test_a_judge_that_copies_kent_scores_kappa_one_in_both_orders():
    st = _sitting()
    rep = vj.analyse(st, _verdicts(st, _like_kent(st["picks"])))
    m = rep["models"]["m"]
    for order in ("A", "B"):
        r = m["orders"][order]["reads"]["live"]
        assert r["n_scored"] == 12 and r["n_kent_decided"] == 8 and r["n_decided"] == 8
        assert r["kappa_3way"] == pytest.approx(1.0) and r["kappa_sides"] == pytest.approx(1.0)
        assert m["orders"][order]["opposite_side"] == []
        assert m["orders"][order]["reads"]["passing_arms_only"]["n_scored"] == 6
        assert m["orders"][order]["reads"]["vs_kit_expected_label"]["n_scored"] == 12
    assert m["swap"] == {"pairs_in_both_orders": 14, "same_verdict_after_swap": 14,
                         "side_flipped_with_swap": 0}
    ctrl = m["orders"]["A"]["controls"]
    assert (ctrl["identical_called_tie"], ctrl["identical_answered"]) == (1, 1)
    assert (ctrl["repeat_consistent"], ctrl["repeat_answered"]) == (1, 1)
    assert rep["kent"] == {"identical_called_tie": 1, "identical_pairs": 1,
                           "repeat_consistent": 1, "repeat_pairs": 1,
                           "left_picks": 5, "right_picks": 4, "ties_live": 4}


def test_a_judge_on_the_other_side_scores_below_zero_and_lists_every_pair():
    st = _sitting()
    flip = {"L": "R", "R": "L", "tie": "tie"}
    other = lambda pid, order: _like_kent({p: flip[c] for p, c in st["picks"].items()})(pid, order)
    rep = vj.analyse(st, _verdicts(st, other))
    r = rep["models"]["m"]["orders"]["A"]["reads"]["live"]
    assert r["kappa_sides"] == pytest.approx(-1.0) and r["kappa_3way"] < 0
    assert len(rep["models"]["m"]["orders"]["A"]["opposite_side"]) == 8
    row = rep["models"]["m"]["orders"]["A"]["opposite_side"][0]
    assert set(row) == {"pair", "fixture", "arm", "kent", "judge", "confidence", "reason"}


def test_a_screen_side_habit_shows_in_the_swap_count_not_in_kappa_alone():
    st = _sitting()
    rep = vj.analyse(st, _verdicts(st, lambda pid, order: "L"))
    s = rep["models"]["m"]["swap"]
    assert s == {"pairs_in_both_orders": 14, "same_verdict_after_swap": 0,
                 "side_flipped_with_swap": 14}
    ctrl = rep["models"]["m"]["orders"]["A"]["controls"]
    assert ctrl["left_picks_own_frame"] == 14 and ctrl["identical_called_tie"] == 0


def test_a_judge_that_only_ties_earns_nothing():
    st = _sitting()
    rep = vj.analyse(st, _verdicts(st, lambda pid, order: "tie"))
    r = rep["models"]["m"]["orders"]["A"]["reads"]["live"]
    assert r["n_decided"] == 0 and r["kappa_sides"] is None
    assert r["kappa_3way"] is None or r["kappa_3way"] <= 0
    assert r["judge_silent_on_decided"] == 8


def test_markdown_carries_every_scope_and_the_controls():
    st = _sitting()
    md = vj.markdown(vj.analyse(st, _verdicts(st, _like_kent(st["picks"]))))
    for needle in ("passing_arms_only", "vs_kit_expected_label", "Judge controls",
                   "Swap:", "ceiling", "| **before** |"):
        assert needle in md, needle
    assert "% agree" not in md.lower() and "agreement rate" not in md.lower()


def test_record_appends_in_run_shape_and_refuses_a_second_verdict(tmp_path):
    rows = [{"pair": "P001", "choice": "L", "confidence": 4, "reason": "a"},
            {"pair": "P002", "choice": "tie", "confidence": 9, "reason": "b"}]
    assert vj.record_rows(tmp_path, rows) == 2
    got = vj.load_verdicts(tmp_path)[vj.SESSION_MODEL]["A"]
    assert got["P001"]["choice_frame_a"] == "L" and got["P001"]["confidence_in_range"]
    assert got["P002"]["choice"] == "tie" and not got["P002"]["confidence_in_range"]
    assert got["P001"]["prompt_sha256"] == vj.prompt_sha()
    assert got["P001"]["input_tokens"] == 0 and got["P001"]["stop_reason"] == "end_turn"
    with pytest.raises(SystemExit, match="already recorded"):
        vj.record_rows(tmp_path, [{"pair": "P001", "choice": "R", "confidence": 1, "reason": ""}])
    with pytest.raises(SystemExit, match="not in"):
        vj.record_rows(tmp_path, [{"pair": "P003", "choice": "left", "confidence": 1, "reason": ""}])
    assert len(vj.load_verdicts(tmp_path)[vj.SESSION_MODEL]["A"]) == 2


def test_exclude_drops_a_pair_from_every_read_and_control_and_one_order_reads_clean():
    st = _sitting()
    v = _verdicts(st, _like_kent(st["picks"]))
    v["m"].pop("B")                                  # the session judge: order A only
    rep = vj.analyse(st, v, exclude=frozenset({"P001", "P013", "P999"}))
    assert rep["excluded"] == ["P001", "P013"]
    assert list(rep["models"]["m"]["orders"]) == ["A"]
    r = rep["models"]["m"]["orders"]["A"]["reads"]["live"]
    assert r["n_scored"] == 11 and r["kappa_3way"] == pytest.approx(1.0)
    assert rep["kent"]["identical_pairs"] == 0
    assert rep["kent"]["repeat_pairs"] == 0          # P014 repeats P001, which is gone
    ctrl = rep["models"]["m"]["orders"]["A"]["controls"]
    assert ctrl["identical_answered"] == 0 and ctrl["repeat_answered"] == 0
    assert rep["models"]["m"]["swap"]["pairs_in_both_orders"] == 0
    md = vj.markdown(rep)
    assert "Excluded from every read" in md and "P001, P013" in md
    assert "Swap: not run (one order only)." in md and "no API spend" in md


# ------------------------------------------------- the committed sitting ----

def test_the_committed_sitting_loads_as_the_write_up_describes():
    st = vj.load_sitting()
    kinds = [s["kind"] for s in st["sealed"].values()]
    assert (kinds.count("live"), kinds.count("identical"), kinds.count("repeat")) == (56, 4, 4)
    assert len(st["picks"]) == 64 and len(st["expected"]) == 56
    assert st["passing_arms"] == ["corner_fold_off", "inside_stagger_off", "text_lean_off"]
    assert len(set(st["design_of"].values())) == 12
