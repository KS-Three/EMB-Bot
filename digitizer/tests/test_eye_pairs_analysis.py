import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import analysis as an  # noqa: E402
from tools.eye_pairs.pairs import BASE, REF_ARM  # noqa: E402


def world(n, agree, metric="ragged_mm", arm_value=0.1, base_value=0.2,
          refused=()):
    """`n` live pairs, one fixture each (fx<i>), arm 'a'. Kent alternates
    arm / base so his pick marginal is balanced; the metric AGREES with him
    on the first `agree` pairs and disagrees on the rest. When the metric
    prefers the arm, the arm reads `arm_value`; when it prefers the base, the
    arm reads the mirror value on the other side of `base_value`.

    This used to be one constant answer — the metric preferred the arm on
    every pair — and the naive 2a-1 rule credited it. A marginal-corrected
    chance floor correctly gives a constant metric nothing, so the fixture
    had to carry information to test anything (review finding 2026-09-17).
    """
    sealed, picks, feats = {}, {}, {}
    mirror = 2 * base_value - arm_value
    for i in range(n):
        pid, fx = f"P{i:03d}", f"fx{i}"
        left_is_arm = i % 2 == 0
        kent_arm = i % 2 == 0
        sealed[pid] = {"fixture": fx, "kind": "live", "repeat_of": None,
                       "left_arm": "a" if left_is_arm else BASE,
                       "right_arm": BASE if left_is_arm else "a"}
        picks[pid] = {"pair": pid, "choice": "L" if kent_arm == left_is_arm else "R"}
        metric_arm = kent_arm if i < agree else not kent_arm
        feats[fx] = {BASE: {metric: base_value, "refusals": {}},
                     "a": {metric: arm_value if metric_arm else mirror,
                           "refusals": {metric: "ink ambiguous"} if fx in refused else {}}}
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


def skewed_world(n_arm_picks=20, n_base_picks=60, metric_arm_within_arm=5,
                 metric_arm_within_base=15):
    """One fixture per pair so the metric's preference is set PER PAIR. Kent
    picks the arm on `n_arm_picks` pairs and the base on `n_base_picks`; the
    metric prefers the arm on a chosen count inside each of those groups.
    With 5 of 20 and 15 of 60 the metric's preference is INDEPENDENT of the
    pick (25% either way) — zero information — while both lean to shipped."""
    sealed, picks, feats = {}, {}, {}
    n = n_arm_picks + n_base_picks
    for i in range(n):
        pid, fx = f"P{i:03d}", f"fx{i}"
        kent_arm = i < n_arm_picks
        metric_arm = (i < metric_arm_within_arm) if kent_arm else \
            (i < n_arm_picks + metric_arm_within_base)
        sealed[pid] = {"fixture": fx, "kind": "live", "repeat_of": None,
                       "left_arm": "a", "right_arm": BASE}
        picks[pid] = {"pair": pid, "choice": "L" if kent_arm else "R"}
        feats[fx] = {BASE: {"ragged_mm": 0.2, "refusals": {}},
                     "a": {"ragged_mm": 0.1 if metric_arm else 0.3, "refusals": {}}}
    return sealed, picks, feats


def test_an_independent_metric_under_a_shared_lean_is_not_agreement():
    """Review finding 2026-09-17: 2a-1 fixes the chance floor at 0.5. With
    both marginals at 25% arm, an INDEPENDENT metric scores a = 0.625 and
    Wilson's lower bound clears 0.5 at n = 80 — so the old rule said
    "agrees". The floor must come from the observed marginals."""
    sealed, picks, feats = skewed_world()
    r = an.sign_agreement(an.decided_rows(sealed, picks, ref=False), feats, "ragged_mm")
    assert (r["n"], r["k"]) == (80, 50)
    assert r["a"] == pytest.approx(0.625)
    assert r["lo"] > 0.5                      # the trap: the naive rule fires
    assert r["p_pick"] == pytest.approx(0.25) and r["p_metric"] == pytest.approx(0.25)
    assert r["pe"] == pytest.approx(0.625)
    assert r["kappa_marginal"] == pytest.approx(0.0, abs=1e-9)
    assert r["verdict"] == "no evidence"
    assert r["skewed"] is True


def test_a_genuinely_informative_metric_still_agrees_under_a_lean():
    # Same lean (25% arm picks), but the metric tracks Kent: prefers the arm
    # on 18 of his 20 arm picks and on only 6 of his 60 base picks.
    sealed, picks, feats = skewed_world(metric_arm_within_arm=18,
                                        metric_arm_within_base=6)
    r = an.sign_agreement(an.decided_rows(sealed, picks, ref=False), feats, "ragged_mm")
    assert r["k"] == 18 + 54
    assert r["lo"] > r["pe"]
    assert r["verdict"] == "agrees"
    assert r["kappa_marginal"] > 0.5


def test_balanced_marginals_reduce_to_the_pre_registered_rule():
    sealed, picks, feats = world(20, agree=18)
    r = an.sign_agreement(an.decided_rows(sealed, picks, ref=False), feats, "ragged_mm")
    assert r["p_pick"] == 0.5 and r["p_metric"] == 0.5 and r["pe"] == 0.5
    assert r["kappa_marginal"] == pytest.approx(r["kappa"]) == pytest.approx(0.8)
    assert r["skewed"] is False


def test_a_constant_metric_earns_no_credit_however_often_it_agrees():
    # The metric prefers the arm on EVERY pair; Kent picks the arm on 18 of
    # 20. Raw agreement is 0.9 and 2a-1 reads +0.8 — but a constant answer
    # cannot discriminate, and pe equals a exactly.
    sealed, picks, feats = {}, {}, {}
    for i in range(20):
        pid, fx = f"P{i:03d}", f"fx{i}"
        sealed[pid] = {"fixture": fx, "kind": "live", "repeat_of": None,
                       "left_arm": "a", "right_arm": BASE}
        picks[pid] = {"pair": pid, "choice": "L" if i < 18 else "R"}
        feats[fx] = {BASE: {"ragged_mm": 0.2, "refusals": {}},
                     "a": {"ragged_mm": 0.1, "refusals": {}}}
    r = an.sign_agreement(an.decided_rows(sealed, picks, ref=False), feats, "ragged_mm")
    assert r["kappa"] == pytest.approx(0.8)
    assert r["p_metric"] == 1.0 and r["pe"] == pytest.approx(0.9)
    assert r["kappa_marginal"] == pytest.approx(0.0, abs=1e-9)
    assert r["verdict"] == "no evidence"


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
    sealed, picks, feats = world(30, agree=30, refused={f"fx{i}" for i in range(10)})
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
    # Three fixtures, four pairs each, the metric agreeing on every pair.
    sealed, picks, feats = world(12, agree=12)
    for i in range(12):
        sealed[f"P{i:03d}"]["fixture"] = f"g{i % 3}"
    for g in range(3):
        feats[f"g{g}"] = {BASE: {"ragged_mm": 0.2, "refusals": {}},
                          "a": {"ragged_mm": 0.1, "refusals": {}}}
    # Kent alternates arm/base, so make the metric follow him per pair by
    # giving the base-picked pairs (odd i) their own fixture values.
    for i in range(1, 12, 2):
        sealed[f"P{i:03d}"]["fixture"] = f"h{i % 3}"
        feats[f"h{i % 3}"] = {BASE: {"ragged_mm": 0.2, "refusals": {}},
                              "a": {"ragged_mm": 0.3, "refusals": {}}}
    out = an.per_fixture_sign(an.decided_rows(sealed, picks, ref=False), feats, "ragged_mm")
    assert out["agree"] == 6 and out["disagree"] == 0
    assert out["fixtures"]["g0"] == {"n": 2, "k": 2}
    assert out["fixtures"]["h1"] == {"n": 2, "k": 2}


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
    # Kent picks the arm on even pairs (0, 2, 4), the base on 1 and 3; 5 tied.
    assert (t["wins"], t["losses"], t["ties"]) == (3, 2, 1)


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
