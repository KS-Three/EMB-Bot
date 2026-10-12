"""tools.eye_pairs.pooled: the kappa is the textbook one, the pool refuses a
vocabulary it does not know, and the committed inputs are readable."""
from __future__ import annotations

import json
from fractions import Fraction

import pytest

from tools.eye_pairs import pooled
from tools.eye_pairs.pooled import (LabelVocabularyError, agreement, instrument_pick,
                                    kappa_from_table, pooled_pairs, select, validate,
                                    worse_pairs)
from tools.eye_pairs.pooled_build import num, split_cell


def _pair(i, kent_label, inst, fixture="f"):
    """A pair whose `lost_frac` (lower is better) makes the instrument pick
    `inst` in {"before", "after", "tie"}."""
    b, a = {"before": (1.0, 2.0), "after": (2.0, 1.0), "tie": (1.0, 1.0)}[inst]
    return {"id": f"s:a:{i}", "sitting": "s", "arm": "a", "fixture": fixture,
            "label": kent_label, "kent": pooled.VOCABULARY[kent_label],
            "before": {"lost_frac": b}, "after": {"lost_frac": a}}


def _rows(spec):
    """spec: list of (kent_label, instrument_pick, count)."""
    rows, i = [], 0
    for lab, inst, n in spec:
        for _ in range(n):
            rows.append(_pair(i, lab, inst, fixture=f"fx{i % 3}"))
            i += 1
    return rows


def test_kappa_two_by_two_known_value():
    # Hand-made 10 rows: Kent chose 'after' 5 times and 'before' 5 times; the
    # instrument matched on 4 of each. po = 0.8, pe = 0.5, kappa = 0.6.
    rows = _rows([("after", "after", 4), ("after", "before", 1),
                  ("before", "before", 4), ("before", "after", 1)])
    assert len(rows) == 10
    r = agreement(rows, "lost_frac")
    assert r["kappa_decided"] == pytest.approx(0.6)
    assert r["n_decided"] == 10 and r["n_scored"] == 10
    assert kappa_from_table([[4, 1], [1, 4]]) == pytest.approx(0.6)


def test_kappa_three_way_weighted_known_value():
    # Rows Kent (before, tie, after) x instrument (before, tie, after):
    #   before: 2 1 0 / tie: 1 2 1 / after: 0 1 2   (n = 10)
    # Linear weights 1, 1/2, 0. po_w = 4/5, pe_w = 29/50, so
    # kappa_w = (4/5 - 29/50) / (1 - 29/50) = 11/21.
    rows = _rows([("before", "before", 2), ("before", "tie", 1),
                  ("same", "before", 1), ("same", "tie", 2), ("both_bad", "after", 1),
                  ("after", "tie", 1), ("after", "after", 2)])
    assert len(rows) == 10
    r = agreement(rows, "lost_frac")
    assert r["kappa_3way"] == pytest.approx(float(Fraction(11, 21)))
    # The decided table drops every tie on either side: 2 + 2 of 3 + 3 decided
    # pairs where the instrument also chose a side.
    assert r["n_decided"] == 4 and r["n_instrument_silent_on_decided"] == 2


def test_kappa_undefined_when_one_category_everywhere():
    # Instrument always says 'after', Kent always 'after': pe = 1, nothing to
    # correct for -- None, not 1.0.
    assert kappa_from_table([[0, 0], [0, 5]]) is None
    r = agreement(_rows([("after", "after", 6)]), "lost_frac")
    assert r["kappa_decided"] is None


def test_no_raw_agreement_in_the_result():
    r = agreement(_rows([("after", "after", 3), ("before", "before", 3)]), "lost_frac")
    banned = {"a", "k", "agree", "agreement", "raw", "accuracy", "share", "pct", "percent"}
    assert not banned & set(r)


def test_instrument_pick_direction_and_exact_ties():
    assert instrument_pick("lost_frac", 0.30, 0.25) == "after"        # lower is better
    assert instrument_pick("artfid", 80.0, 85.0) == "after"           # higher is better
    assert instrument_pick("lost_frac", 0.2500, 0.2500) == "tie"
    assert instrument_pick("stitches", 100, 99) == "after"            # cost reading


def test_unknown_label_refuses_the_whole_pool():
    inputs = {"schema": 1, "sittings": {"s": {"pairs": [
        {"id": "s:a:x", "arm": "a", "fixture": "x", "label": "after", "before": {}, "after": {}},
        {"id": "s:a:y", "arm": "a", "fixture": "y", "label": "meh", "before": {}, "after": {}}]}}}
    with pytest.raises(LabelVocabularyError, match="'meh'"):
        pooled_pairs(inputs)
    with pytest.raises(LabelVocabularyError):
        validate(inputs)
    inputs["sittings"]["s"]["pairs"][1]["label"] = None        # unjudged is fine
    assert len(pooled_pairs(inputs)) == 1


def test_refuses_a_schema_it_does_not_know():
    with pytest.raises(LabelVocabularyError):
        validate({"schema": 2, "sittings": {}})


def test_both_bad_is_a_tie_unless_dropped():
    pairs = [{**_pair(0, "both_bad", "after"), "label": "both_bad"},
             _pair(1, "after", "after"), _pair(2, "same", "tie")]
    assert [p["kent"] for p in pairs] == ["tie", "after", "tie"]
    assert len(select(pairs, both_bad="tie")) == 3
    assert len(select(pairs, both_bad="drop")) == 2


def test_kent_excluded_fixtures_leave_the_primary_scope():
    pairs = [_pair(0, "after", "after", fixture="screenshot"),
             _pair(1, "after", "after", fixture="gaulke"),
             _pair(2, "after", "after", fixture="becker")]
    assert [p["fixture"] for p in select(pairs)] == ["becker"]
    assert len(select(pairs, scope="all_fixtures")) == 3


def test_worse_pairs_margin_is_how_much_worse_kent_pick_scored():
    # Kent chose 'after' (2.0 on a lower-is-better metric) over 'before' (1.0).
    rows = [_pair(0, "after", "before"), _pair(1, "after", "after")]
    w = worse_pairs(rows, "lost_frac")
    assert len(w) == 1 and w[0]["pair"] == "s:a:0" and w[0]["margin"] == pytest.approx(1.0)
    # a higher-is-better metric flips the sign convention, not the meaning
    row = {**_pair(2, "before", "tie"), "before": {"artfid": 80.0}, "after": {"artfid": 90.0}}
    assert worse_pairs([row], "artfid")[0]["margin"] == pytest.approx(10.0)


def test_refused_pairs_are_left_out_and_counted():
    rows = _rows([("after", "after", 3), ("before", "before", 3)])
    rows[0]["refused"] = {"before": [], "after": ["lost_frac"]}
    assert agreement(rows, "lost_frac")["n_scored"] == 5
    assert agreement(rows, "lost_frac")["n_refused"] == 1
    assert agreement(rows, "lost_frac", include_refused=True)["n_scored"] == 6
    assert agreement(rows, "stitches")["n_refused"] == 0        # refusal is per metric


def test_reading_needs_n_and_both_intervals():
    assert pooled.reading(9, (0.2, 0.9), (0.3, 0.8)).startswith("n too small")
    assert pooled.reading(30, (0.2, 0.9), (0.3, 0.8)) == "above chance"
    assert pooled.reading(30, (-0.1, 0.9), (0.3, 0.8)) == "no evidence either way"
    assert pooled.reading(30, (-0.9, -0.2), (-0.8, -0.1)) == "below chance"
    assert pooled.reading(30, (None, None), (0.3, 0.8)) == "interval undefined"


def test_inventory_counts_judged_pairs_and_skips_unjudged():
    inputs = {"schema": 1, "sittings": {"s": {"date": "2026-10-11", "pairs": [
        {"id": "s:a:x", "arm": "a", "fixture": "x", "label": "after",
         "before": {"lost_frac": 1.0}, "after": {"lost_frac": 2.0}},
        {"id": "s:a:y", "arm": "a", "fixture": "y", "label": "both_bad", "before": {}, "after": {}},
        {"id": "s:a:z", "arm": "a", "fixture": "z", "label": None, "before": {}, "after": {}}]}}}
    (row,) = pooled.inventory(inputs)
    assert (row["judged"], row["unjudged"], row["after"], row["both_bad"]) == (2, 1, 1, 1)
    assert row["with_instruments"] == 1


def test_pair_tally_ranks_pairs_by_instruments_that_disagree():
    rep = {"worse": {"lost_frac": [{"pair": "p1", "kent": "after"}, {"pair": "p2", "kent": "after"}],
                     "ragged_mm": [{"pair": "p1", "kent": "after"}],
                     "stitches": [{"pair": "p3", "kent": "after"}]}}      # price: not fidelity
    tally = pooled.pair_tally(rep)
    assert [t["pair"] for t in tally] == ["p1", "p2"]
    assert tally[0]["instruments"] == ["lost_frac", "ragged_mm"]


def test_unscored_instrument_is_zero_not_missing():
    r = agreement(_rows([("after", "after", 3)]), "fan_census")
    assert r["n_scored"] == 0 and "not_computed" in r


def test_bootstrap_reports_an_interval_and_what_it_rests_on(monkeypatch):
    monkeypatch.setattr(pooled, "B", 300)
    rows = _rows([("after", "after", 6), ("after", "before", 2),
                  ("before", "before", 6), ("before", "after", 2)])
    r = agreement(rows, "lost_frac")
    assert r["ci2_lo"] <= r["kappa_decided"] <= r["ci2_hi"]
    assert r["ci2_resamples"] > 0 and r["n_decided"] == 16


def test_table_cell_parsers():
    assert num("2,093") == 2093.0 and num("5.80%") == pytest.approx(0.058)
    assert num("n/a") is None and num("identical") is None
    assert split_cell("2,093 → 2,119") == (2093.0, 2119.0)
    assert split_cell("21") == (21.0, 21.0)
    assert split_cell("—") is None and split_cell("no lettering") is None


def test_committed_inputs_validate_and_report(monkeypatch):
    monkeypatch.setattr(pooled, "B", 100)
    inputs = json.loads(pooled.INPUTS.read_text(encoding="utf-8"))
    pairs = pooled_pairs(inputs)
    assert pairs, "no judged pairs in the committed inputs"
    rep = pooled.full_report(inputs)
    assert rep["n_judged_pairs"] == len(pairs)
    assert set(rep["instruments"]) == set(pooled.INSTRUMENTS)
    assert rep["instruments"]["fan_census"]["n_scored"] == 0
    # every figure printed is chance-corrected: no raw agreement key anywhere
    for r in rep["instruments"].values():
        assert not {"a", "k", "agree", "accuracy", "raw"} & set(r)
