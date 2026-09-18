import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import analysis as an  # noqa: E402
from tools.eye_pairs.pairs import BASE, REF_ARM  # noqa: E402


def world(n, agree, metric="ragged_mm", arm_value=0.1, base_value=0.2,
          refused=()):
    """`n` live pairs on fixture fx<i>, arm 'a'. The metric prefers the ARM
    (lower ragged_mm); Kent picks the arm on the first `agree` of them."""
    sealed, picks, feats = {}, {}, {}
    for i in range(n):
        pid, fx = f"P{i:03d}", f"fx{i % 3}"
        left_is_arm = i % 2 == 0
        sealed[pid] = {"fixture": fx, "kind": "live", "repeat_of": None,
                       "left_arm": "a" if left_is_arm else BASE,
                       "right_arm": BASE if left_is_arm else "a"}
        pick_arm = i < agree
        choice = "L" if pick_arm == left_is_arm else "R"
        picks[pid] = {"pair": pid, "choice": choice}
        feats.setdefault(fx, {})[BASE] = {metric: base_value, "refusals": {}}
        feats[fx]["a"] = {metric: arm_value,
                          "refusals": {metric: "ink ambiguous"} if fx in refused else {}}
    return sealed, picks, feats


def test_wilson_matches_hand_computed_values():
    lo, hi = an.wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=5e-4) and hi == pytest.approx(0.9433, abs=5e-4)
    lo, hi = an.wilson(18, 20)
    assert lo == pytest.approx(0.6990, abs=5e-4) and hi == pytest.approx(0.9721, abs=5e-4)
    assert an.wilson(0, 0) == (0.0, 1.0)


def test_lower_is_better_is_honoured_and_agreement_is_chance_corrected():
    sealed, picks, feats = world(20, agree=18)
    r = an.sign_agreement(an.decided_rows(sealed, picks, ref=False), feats, "ragged_mm")
    assert (r["n"], r["k"]) == (20, 18)
    assert r["kappa"] == pytest.approx(0.8)
    assert r["verdict"] == "agrees"


def test_higher_is_better_flips_the_preference():
    sealed, picks, feats = world(20, agree=18, metric="artfid",
                                arm_value=90.0, base_value=80.0)
    assert an.sign_agreement(an.decided_rows(sealed, picks, ref=False),
                             feats, "artfid")["k"] == 18
    sealed, picks, feats = world(20, agree=18, metric="artfid",
                                 arm_value=70.0, base_value=80.0)
    r = an.sign_agreement(an.decided_rows(sealed, picks, ref=False), feats, "artfid")
    assert r["k"] == 2 and r["verdict"] == "anti-agrees"


def test_the_three_verdicts_and_the_small_n_rule():
    rows = lambda w: an.decided_rows(w[0], w[1], ref=False)
    w = world(20, agree=11)
    assert an.sign_agreement(rows(w), w[2], "ragged_mm")["verdict"] == "no evidence"
    w = world(9, agree=9)
    assert an.sign_agreement(rows(w), w[2], "ragged_mm")["verdict"] == "n too small"


def test_ties_nulls_and_equal_values_are_not_counted():
    sealed, picks, feats = world(12, agree=12)
    picks["P000"]["choice"] = "tie"
    feats["fx1"]["a"]["ragged_mm"] = None
    rows = an.decided_rows(sealed, picks, ref=False)
    assert len(rows) == 11
    r = an.sign_agreement(rows, feats, "ragged_mm")
    assert r["n"] == 11 - sum(1 for x in rows if x["fixture"] == "fx1")
    feats["fx2"]["a"]["ragged_mm"] = feats["fx2"][BASE]["ragged_mm"]
    assert an.sign_agreement(rows, feats, "ragged_mm")["n"] < r["n"]


def test_refused_pairs_leave_the_headline_and_stay_in_the_all_pairs_row():
    sealed, picks, feats = world(30, agree=30, refused={"fx0"})
    rows = an.decided_rows(sealed, picks, ref=False)
    assert an.sign_agreement(rows, feats, "ragged_mm")["n"] == 20
    assert an.sign_agreement(rows, feats, "ragged_mm", include_refused=True)["n"] == 30


def test_the_exit_clause_lists_every_pair_picked_against_the_metric():
    sealed, picks, feats = world(10, agree=7)
    rows = an.decided_rows(sealed, picks, ref=False)
    bad = an.exit_clause(rows, feats, "ragged_mm")
    assert sorted(b["pair"] for b in bad) == ["P007", "P008", "P009"]
    assert bad[0]["picked"] == BASE and bad[0]["arm_value"] == 0.1


def test_per_fixture_sign_counts_fixtures_not_pairs():
    sealed, picks, feats = world(12, agree=12)
    out = an.per_fixture_sign(an.decided_rows(sealed, picks, ref=False), feats, "ragged_mm")
    assert out["agree"] == 3 and out["disagree"] == 0
    assert out["fixtures"]["fx0"] == {"n": 4, "k": 4}


def test_a_directionless_metric_is_described_never_judged():
    assert an.METRICS["stitches"] == "none"
    sealed, picks, feats = world(10, agree=10, metric="stitches",
                                 arm_value=5000, base_value=4000)
    rows = an.decided_rows(sealed, picks, ref=False)
    assert an.sign_agreement(rows, feats, "stitches")["n"] == 0
    assert an.lean(rows, feats, "stitches") == {"metric": "stitches", "n": 10,
                                                "picked_higher": 10}


def test_ref_rows_are_kept_apart_from_flag_rows():
    sealed, picks, feats = world(4, agree=4)
    sealed["P900"] = {"fixture": "fx0", "kind": "live", "repeat_of": None,
                      "left_arm": BASE, "right_arm": REF_ARM}
    picks["P900"] = {"pair": "P900", "choice": "L"}
    assert [r["pair"] for r in an.decided_rows(sealed, picks, ref=True)] == ["P900"]
    assert "P900" not in [r["pair"] for r in an.decided_rows(sealed, picks, ref=False)]


def test_the_ceiling_is_kents_own_consistency():
    sealed = {
        "P001": {"fixture": "f", "kind": "live", "repeat_of": None, "left_arm": BASE, "right_arm": "a"},
        "P002": {"fixture": "f", "kind": "repeat", "repeat_of": "P001", "left_arm": "a", "right_arm": BASE},
        "P003": {"fixture": "g", "kind": "live", "repeat_of": None, "left_arm": "a", "right_arm": BASE},
        "P004": {"fixture": "g", "kind": "repeat", "repeat_of": "P003", "left_arm": BASE, "right_arm": "a"},
    }
    picks = {"P001": {"choice": "R"}, "P002": {"choice": "L"},      # arm, arm
             "P003": {"choice": "L"}, "P004": {"choice": "L"}}      # arm, base
    assert an.ceiling(sealed, picks) == {"n": 2, "consistent": 1, "share": 0.5}


def test_controls_report_tie_rate_and_side_bias():
    sealed = {f"P{i}": {"fixture": "f", "kind": "identical", "repeat_of": None,
                        "left_arm": BASE, "right_arm": BASE} for i in range(4)}
    picks = {"P0": {"choice": "tie"}, "P1": {"choice": "tie"},
             "P2": {"choice": "L"}, "P3": {"choice": "L"}}
    out = an.controls(sealed, picks)
    assert out["identical_n"] == 4 and out["identical_tie_rate"] == 0.5
    assert out["left_share_all"] == 1.0


def test_the_flag_table_counts_wins_for_the_arm():
    sealed, picks, _ = world(6, agree=4)
    picks["P005"]["choice"] = "tie"
    t = an.flag_table(sealed, picks)["a"]
    assert (t["wins"], t["losses"], t["ties"]) == (4, 1, 1)


def fit_world(n_fixtures, arms_per_fixture):
    """Kent's pick follows `artfid` exactly; the other three are noise."""
    import numpy as np
    rng = np.random.default_rng(3)
    sealed, picks, feats = {}, {}, {}
    i = 0
    for f in range(n_fixtures):
        fx = f"fx{f}"
        feats[fx] = {BASE: {"artfid": 80.0, "lost_elements": 5.0, "ragged_mm": 0.20,
                            "roughness_deg": 4.0, "refusals": {}}}
        for a in range(arms_per_fixture):
            arm, pid = f"arm{a}", f"P{i:03d}"
            i += 1
            d = float(rng.normal())
            feats[fx][arm] = {"artfid": 80.0 + 5 * d,
                              "lost_elements": 5.0 + float(rng.normal()),
                              "ragged_mm": 0.20 + 0.02 * float(rng.normal()),
                              "roughness_deg": 4.0 + float(rng.normal()),
                              "refusals": {}}
            sealed[pid] = {"fixture": fx, "kind": "live", "repeat_of": None,
                           "left_arm": BASE, "right_arm": arm}
            picks[pid] = {"pair": pid, "choice": "R" if d > 0 else "L"}
    return sealed, picks, feats


def test_the_fit_recovers_a_separable_world_leave_one_fixture_out():
    sealed, picks, feats = fit_world(9, 6)          # 54 decided pairs
    out = an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats)
    assert out["label"] == "EXPLORATORY" and out["n"] == 54
    assert out["lofo_accuracy"] >= 0.9
    assert out["best_single"]["metric"] == "artfid"
    assert len(out["weights"]) == 1 + len(an.EXPLORATORY)


def test_the_fit_refuses_to_run_under_forty_pairs():
    sealed, picks, feats = fit_world(13, 3)         # 39 decided pairs
    assert an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats) is None
