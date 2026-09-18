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


def test_both_values_or_nothing_and_what_a_tie_means_is_the_callers_call():
    """Review 2026-09-17: fetch-base / fetch-arm / skip-if-missing was written
    out three times, and the three did not treat a tie alike — on purpose in
    the fit, invisibly everywhere. One helper; `ties` is a required word."""
    feats = {"fx": {BASE: {"artfid": 80.0, "ragged_mm": 0.2, "lost_frac": None},
                    "a": {"artfid": 81.0, "ragged_mm": 0.2, "lost_frac": 0.1}}}
    row = {"fixture": "fx", "arm": "a"}
    assert an._both(feats, row, "artfid", ties=False) == (80.0, 81.0)
    assert an._both(feats, row, "ragged_mm", ties=False) is None       # equal: no say
    assert an._both(feats, row, "ragged_mm", ties=True) == (0.2, 0.2)  # the fit's zero delta
    for ties in (True, False):
        assert an._both(feats, row, "lost_frac", ties=ties) is None    # missing on one arm
        assert an._both(feats, row, "thin_recall", ties=ties) is None  # missing on both
    with pytest.raises(TypeError):
        an._both(feats, row, "artfid")                                 # never defaulted


def test_a_tie_is_no_say_for_a_verdict_and_a_zero_delta_for_the_fit():
    """The divergence, pinned in one place so it stays deliberate."""
    sealed, picks, feats = world(12, agree=12, metric="stitches",
                                 arm_value=5000, base_value=4000)
    feats["fx3"]["a"]["stitches"] = feats["fx3"][BASE]["stitches"]
    rows = an.decided_rows(sealed, picks, ref=False)
    assert an.lean(rows, feats, "stitches")["n"] == 11
    sealed, picks, feats = world(12, agree=12)
    feats["fx3"]["a"]["ragged_mm"] = feats["fx3"][BASE]["ragged_mm"]
    rows = an.decided_rows(sealed, picks, ref=False)
    assert an.sign_agreement(rows, feats, "ragged_mm")["n"] == 11
    assert len(an.exit_clause(rows, feats, "ragged_mm")) == 0
    assert "fx3" not in an.per_fixture_sign(rows, feats, "ragged_mm")["fixtures"]
    # ... while the fit keeps every all-tie row of `lean_world`: 60 of 60.
    sealed, picks, feats = lean_world()
    assert an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats)["n"] == 60


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


def test_design_only_rows_are_kept_apart_from_flag_rows_by_the_stored_flag():
    sealed, picks, feats = world(4, agree=4)
    # NOT named like REF_ARM — the stored flag is what decides the bucket.
    sealed["P900"] = {"fixture": "fx0", "kind": "live", "repeat_of": None,
                      "left_arm": BASE, "right_arm": "ref_0901", "design_only": True}
    picks["P900"] = {"pair": "P900", "choice": "L"}
    # Named like the ref arm but NOT design-only: stays in the flag bucket.
    sealed["P901"] = {"fixture": "fx1", "kind": "live", "repeat_of": None,
                      "left_arm": BASE, "right_arm": REF_ARM, "design_only": False}
    picks["P901"] = {"pair": "P901", "choice": "R"}
    assert [r["pair"] for r in an.decided_rows(sealed, picks, ref=True)] == ["P900"]
    flag = [r["pair"] for r in an.decided_rows(sealed, picks, ref=False)]
    assert "P900" not in flag and "P901" in flag


def env(main=False, ref=False, reqs=False):
    return {"ref": "25da2fe", "rembg_venv_main": main, "rembg_venv_ref": ref,
            "requirements_differ": reqs}


def test_a_photo_fixture_is_not_confounded_when_neither_engine_had_rembg():
    """Review 2026-09-17: `confounded` was `design_class in PHOTO_CLASSES` —
    an inference. On a checkout with no rembg venv (every worktree) today's
    engine skipped photo prep exactly as the old one did, so the proxy
    flagged a confound that was not there."""
    out = an.ref_confound(env(main=False, ref=False), photo_class=True)
    assert out == {"confounded": False, "why": []}


def test_the_rembg_fact_fires_only_on_an_asymmetry_and_only_on_photo_fixtures():
    out = an.ref_confound(env(main=True, ref=False), photo_class=True)
    assert out["confounded"] is True
    assert len(out["why"]) == 1 and "rembg" in out["why"][0]
    assert "today's engine only" in out["why"][0]
    # A flat logo never reaches photo prep, whatever the venvs are.
    assert an.ref_confound(env(main=True, ref=False), photo_class=False)["confounded"] is False
    # Both present is as symmetric as both absent.
    assert an.ref_confound(env(main=True, ref=True), photo_class=True)["confounded"] is False


def test_changed_pins_confound_every_fixture_and_say_so():
    for photo in (True, False):
        out = an.ref_confound(env(reqs=True), photo_class=photo)
        assert out["confounded"] is True and "requirements.txt" in out["why"][0]
    both = an.ref_confound(env(main=True, reqs=True), photo_class=True)
    assert len(both["why"]) == 2                     # every fact that fired is named


def test_an_unrecorded_environment_is_unknown_not_clean():
    for missing in (None, {}):
        out = an.ref_confound(missing, photo_class=True)
        assert out["confounded"] is None and "not recorded" in out["why"][0]


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


def test_the_fit_reports_both_accuracies_against_the_majority_baseline():
    """ROADMAP gate 4 (review 2026-09-17): the two accuracies were returned
    and printed raw. An accuracy only means something beside what always
    guessing Kent's commoner pick would score, and with its interval."""
    sealed, picks, feats = fit_world(9, 6)
    rows = an.decided_rows(sealed, picks, ref=False)
    out = an.exploratory_fit(rows, feats)
    share = sum(r["picked_is_arm"] for r in rows) / len(rows)
    base = max(share, 1 - share)
    assert out["label"] == "EXPLORATORY"
    assert out["majority_baseline"] == pytest.approx(base)
    assert out["lofo_n"] == 54
    assert out["lofo_accuracy"] == pytest.approx(out["lofo_hits"] / out["lofo_n"])
    assert out["lofo_wilson"] == pytest.approx(list(an.wilson(out["lofo_hits"], out["lofo_n"])))
    assert out["lofo_above_baseline"] == pytest.approx((out["lofo_accuracy"] - base) / (1 - base))
    assert out["lofo_beats_baseline"] is True       # a separable world clears it
    best = out["best_single"]
    assert best["above_baseline"] == pytest.approx((best["accuracy"] - base) / (1 - base))
    lo, hi = best["wilson"]
    assert lo <= best["accuracy"] <= hi


def lean_world(n_fixtures=10, arms_per_fixture=6, arm_picks=6):
    """Kent picks shipped on 54 of 60 pairs and NO metric has any say — every
    delta is zero — so the only thing there is to learn is his lean."""
    sealed, picks, feats = {}, {}, {}
    same = {"artfid": 80.0, "lost_elements": 5.0, "ragged_mm": 0.20,
            "roughness_deg": 4.0, "refusals": {}}
    i = 0
    for f in range(n_fixtures):
        fx = f"fx{f}"
        feats[fx] = {BASE: dict(same)}
        for a in range(arms_per_fixture):
            arm, pid = f"arm{a}", f"P{i:03d}"
            i += 1
            feats[fx][arm] = dict(same)
            sealed[pid] = {"fixture": fx, "kind": "live", "repeat_of": None,
                           "left_arm": BASE, "right_arm": arm}
            # One arm-pick in each of the first `arm_picks` fixtures, so every
            # leave-one-fixture-out training fold still holds both classes.
            picks[pid] = {"pair": pid, "choice": "R" if (a == 0 and f < arm_picks) else "L"}
    return sealed, picks, feats


def test_a_fit_that_only_learned_kents_lean_earns_nothing():
    """The trap gate 4 names: raw 0.90 reads like a result. It is the floor —
    a model with no information predicts "shipped" every time and is right
    on exactly the share of pairs where Kent picked shipped."""
    sealed, picks, feats = lean_world()
    out = an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats)
    assert out["lofo_accuracy"] == pytest.approx(0.9)
    assert out["majority_baseline"] == pytest.approx(0.9)
    assert out["lofo_above_baseline"] == pytest.approx(0.0, abs=1e-9)
    assert out["lofo_beats_baseline"] is False
    # A metric with no say earns half credit a pair: far UNDER the floor.
    assert out["best_single"]["accuracy"] == pytest.approx(0.5)
    assert out["best_single"]["above_baseline"] == pytest.approx(-4.0)


def test_a_skipped_fold_cannot_flatter_the_fit():
    """Every arm-pick sits in ONE fixture. Holding that fixture out leaves a
    single answer to learn from, so the fold is skipped — and the 54 rows
    LOFO does score are all "shipped". 1.00 on those rows is their FLOOR.
    Held to the floor over all 60 rows (59/60) it read "+1.00 above
    baseline" for a model that learned nothing: the accuracy and its
    baseline have to be taken over the same rows."""
    sealed, picks, feats = lean_world(arm_picks=1)
    out = an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats)
    assert (out["n"], out["lofo_n"]) == (60, 54)
    assert out["lofo_accuracy"] == 1.0
    assert out["lofo_baseline"] == 1.0
    assert out["lofo_above_baseline"] is None and out["lofo_beats_baseline"] is False
    # `best_single` scores every row, so it is still held to the all-row floor.
    assert out["majority_baseline"] == pytest.approx(59 / 60)


def test_with_no_fold_skipped_the_two_floors_are_one_number():
    sealed, picks, feats = fit_world(9, 6)
    out = an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats)
    assert out["lofo_n"] == out["n"]
    assert out["lofo_baseline"] == pytest.approx(out["majority_baseline"])


def test_a_one_sided_sitting_has_no_corrected_figure_rather_than_a_crash():
    sealed, picks, feats = lean_world(arm_picks=0)      # Kent never picks an arm
    out = an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats)
    assert out["majority_baseline"] == 1.0
    assert out["lofo_accuracy"] is None and out["lofo_above_baseline"] is None
    assert out["lofo_beats_baseline"] is False
    assert out["best_single"]["above_baseline"] is None
