"""tools.eye_pairs.pro_pooled: each pro-pair figure is read as a distance to
the pro, the statistics are pooled.py's, and the builder pairs the right
designs. A tiny synthetic sitting throughout; no engine, no pro file."""
from __future__ import annotations

import json

import pytest

from tools.eye_pairs import pooled, pro_pooled, pro_pooled_build as pb


def _pair(i, label, before_cuts, after_cuts, pro_cuts=10, fixture="becker", **more):
    p = {"id": f"s:a:{i}", "arm": "a", "fixture": fixture, "label": label, "judged": "2026-11-01",
         "before": {"cuts": before_cuts}, "after": {"cuts": after_cuts}, "pro": {"cuts": pro_cuts}}
    p.update(more)
    return p


def _inputs(pairs):
    return {"schema": 1, "sittings": {"s": {"date": "2026-11-01", "pairs": pairs}}}


def test_distance_reads_each_kind():
    assert pro_pooled.distance("cuts", 30, 10) == 20.0
    assert pro_pooled.distance("cuts", 4, 10) == 6.0                     # below the pro is also a distance
    assert pro_pooled.distance("needle_up_mm", 500.5, 400.0) == pytest.approx(100.5)
    assert pro_pooled.distance("sttype_kappa", 0.40, None) == pytest.approx(0.60)   # the pro is 1
    assert pro_pooled.distance("word_cc", 0.70, 0.90) == pytest.approx(0.20)
    assert pro_pooled.distance("cuts", None, 10) is None
    assert pro_pooled.distance("cuts", 30, None) is None                  # a count needs the pro's


def test_cost_reading_has_no_pro_and_negates_kappa_and_cc():
    assert pro_pooled.cost("cuts", 30) == 30.0
    assert pro_pooled.cost("sttype_kappa", 0.4) == pytest.approx(-0.4)
    assert pro_pooled.cost("word_cc", 0.9) == pytest.approx(-0.9)
    assert pro_pooled.cost("columns", None) is None


def test_pro_side_reading_wins_over_the_pro_file():
    p = {"pro": {"columns": 50}, "pro_side": {"before": {"columns": 48}}}
    assert pro_pooled.pro_value(p, "before", "columns") == 48
    assert pro_pooled.pro_value(p, "after", "columns") == 50
    assert pro_pooled.pro_value(p, "after", "cuts") is None


def test_distance_and_cost_disagree_when_the_arms_straddle_the_pro():
    # before 5 cuts, after 15, the pro 12: fewer cuts says BEFORE, nearer the pro says AFTER
    inp = _inputs([_pair(0, "after", 5, 15, pro_cuts=12)])
    (d,) = pro_pooled.transformed_pairs(inp, "distance")
    (c,) = pro_pooled.transformed_pairs(inp, "signed")
    assert (d["before"]["cuts"], d["after"]["cuts"]) == (7.0, 3.0)
    assert pooled.instrument_pick("cuts", d["before"]["cuts"], d["after"]["cuts"],
                                  directions=pro_pooled.DISTANCE_DIRECTIONS) == "after"
    assert pooled.instrument_pick("cuts", c["before"]["cuts"], c["after"]["cuts"],
                                  directions=pro_pooled.COST_DIRECTIONS) == "before"


def test_kappa_from_a_synthetic_sitting_is_the_textbook_value(monkeypatch):
    monkeypatch.setattr(pooled, "B", 200)
    # Kent 'after' x5, 'before' x5; the instrument (distance to the pro's 10 cuts)
    # agrees on 4 of each: po 0.8, pe 0.5, kappa 0.6 -- the same table as
    # tests/test_eye_pairs_pooled.py, now built from readings and a pro.
    pairs = []
    i = 0
    for _ in range(4):
        pairs.append(_pair(i, "after", 30, 12, fixture=f"f{i % 3}")); i += 1        # after nearer
    pairs.append(_pair(i, "after", 12, 30, fixture=f"f{i % 3}")); i += 1             # before nearer
    for _ in range(4):
        pairs.append(_pair(i, "before", 12, 30, fixture=f"f{i % 3}")); i += 1
    pairs.append(_pair(i, "before", 30, 12, fixture=f"f{i % 3}")); i += 1
    rep = pro_pooled.full_report(_inputs(pairs))
    r = rep["instruments"]["cuts"]
    assert r["n_scored"] == 10 and r["n_decided"] == 10
    assert r["kappa_decided"] == pytest.approx(0.6)
    assert r["ci2_lo"] <= 0.6 <= r["ci2_hi"]
    assert len(rep["worse"]["cuts"]) == 2
    # the other instruments have no reading: zero, named, not missing
    assert rep["instruments"]["hops"]["n_scored"] == 0
    assert set(rep["instruments"]) == set(pro_pooled.INSTRUMENTS)
    # markdown renders for every table
    for text in (pro_pooled.kappa_table_markdown(rep), pro_pooled.sensitivity_markdown(rep),
                 pro_pooled.worse_markdown(rep)):
        assert "`cuts`" in text


def test_worse_pairs_are_the_ones_kent_pick_is_farther_from_the_pro():
    # Kent 'after'; after is 20 from the pro, before 2: his pick scores worse by 18
    rows = pro_pooled.transformed_pairs(_inputs([_pair(0, "after", 12, 30), _pair(1, "after", 30, 12)]))
    w = pooled.worse_pairs(rows, "cuts", directions=pro_pooled.DISTANCE_DIRECTIONS)
    assert [(r["pair"], r["margin"]) for r in w] == [("s:a:0", 18.0)]


def test_no_raw_agreement_in_the_result():
    rep = pro_pooled.full_report(_inputs([_pair(0, "after", 30, 12), _pair(1, "before", 12, 30)]))
    banned = {"a", "k", "agree", "agreement", "raw", "accuracy", "share", "pct", "percent"}
    for r in rep["instruments"].values():
        assert not banned & set(r)


def test_refuses_readings_without_a_pro_and_an_unknown_label():
    bad = _inputs([_pair(0, "after", 30, 12)])
    del bad["sittings"]["s"]["pairs"][0]["pro"]
    with pytest.raises(pooled.LabelVocabularyError, match="no `pro`"):
        pro_pooled.validate(bad)
    with pytest.raises(pooled.LabelVocabularyError):
        pro_pooled.transformed_pairs(_inputs([_pair(0, "meh", 30, 12)]))
    # a pair with no designs at all is judged, kept, and simply unscored
    inp = _inputs([{"id": "s:a:9", "arm": "a", "fixture": "becker", "label": "same", "before": {}, "after": {}}])
    rep = pro_pooled.full_report(inp)
    assert rep["n_judged_pairs"] == 1 and rep["n_with_both_designs"] == 0
    assert rep["unscored"][0]["pair"] == "s:a:9"


def test_both_bad_and_tires_sensitivities_change_the_n():
    pairs = [_pair(0, "after", 30, 12), _pair(1, "both_bad", 30, 12), _pair(2, "same", 12, 30, fixture="tires")]
    rep = pro_pooled.full_report(_inputs(pairs))
    r = rep["instruments"]["cuts"]
    assert r["n_scored"] == 3
    assert r["sens_both_bad_dropped"]["n_scored"] == 2
    assert r["sens_no_tires"]["n_scored"] == 2
    assert r["sens_signed_cost"]["n_scored"] == 3


# ---------------------------------------------------------------- the builder

SYNTH_SITTINGS = {
    "s": {"tree": "aaaaaaaa", "base": {"x": 1},
          "arms": {"flag": {"f": True}, "old": {"__ref__": "bbbbbbbb"}}},
}


def _labelled(monkeypatch):
    monkeypatch.setattr(pb, "SITTINGS", SYNTH_SITTINGS)
    inputs = {"schema": 1, "sittings": {"s": {"date": "d", "pairs": [
        {"id": "s:flag:becker", "arm": "flag", "fixture": "becker", "label": "after", "before": {}, "after": {}},
        {"id": "s:old:becker", "arm": "old", "fixture": "becker", "label": "same", "before": {}, "after": {}},
        {"id": "s:flag:drone", "arm": "flag", "fixture": "drone", "label": "before", "before": {}, "after": {}},
        {"id": "s:flag:enthusiast", "arm": "flag", "fixture": "enthusiast", "label": "after", "before": {}, "after": {}},
        {"id": "s:gone:becker", "arm": "gone", "fixture": "becker", "label": "after", "before": {}, "after": {}},
        {"id": "s:flag:bridge", "arm": "flag", "fixture": "bridge", "label": None, "before": {}, "after": {}}]}}}
    return inputs, pb.labelled_pairs(inputs)


def test_labelled_pairs_pair_the_right_designs(monkeypatch):
    _inp, pairs = _labelled(monkeypatch)
    by = {p["id"]: p for p in pairs}
    assert set(by) == {"s:flag:becker", "s:old:becker", "s:flag:drone", "s:gone:becker"}   # no pro file: enthusiast; unjudged: bridge
    # a flag arm: before is the tree's base (with the sitting's base kwargs), after adds the arm's change
    assert by["s:flag:becker"]["before_design"] == ("aaaaaaaa", "base", {"x": 1})
    assert by["s:flag:becker"]["after_design"] == ("aaaaaaaa", "flag", {"x": 1, "f": True})
    # a ref arm: before is the OLD engine's base, after the sitting's own base
    assert by["s:old:becker"]["before_design"] == ("bbbbbbbb", "base", {})
    assert by["s:old:becker"]["after_design"] == ("aaaaaaaa", "base", {"x": 1})
    assert "unscored_why" in by["s:gone:becker"] and "before_design" not in by["s:gone:becker"]


def test_designs_needed_shares_bases_and_puts_decided_pairs_first(monkeypatch):
    _inp, pairs = _labelled(monkeypatch)
    all_designs = pb.designs_needed(pairs)
    keys = [(t, f, s) for t, f, s, _k in all_designs]
    # becker's base on tree a is ONE design though two pairs need it
    assert keys.count(("aaaaaaaa", "becker", "base")) == 1
    assert set(keys) == {("aaaaaaaa", "becker", "base"), ("aaaaaaaa", "becker", "flag"),
                         ("aaaaaaaa", "drone", "base"), ("aaaaaaaa", "drone", "flag"),
                         ("bbbbbbbb", "becker", "base")}
    # the old engine's base serves only the tie pair, so it comes last and leaves with --decided-only
    assert keys[-1] == ("bbbbbbbb", "becker", "base")
    decided = [(t, f, s) for t, f, s, _k in pb.designs_needed(pairs, decided_only=True)]
    assert ("bbbbbbbb", "becker", "base") not in decided and len(decided) == 4


def test_build_assembles_readings_and_keeps_the_pro_per_side(monkeypatch, tmp_path):
    inputs, _pairs = _labelled(monkeypatch)
    runs = tmp_path / "runs"

    def measured(tree, fixture, side, **row):
        d = pb.design_dir(runs, tree, fixture, side)
        d.mkdir(parents=True)
        (d / "ours.dst").write_bytes(b"")
        (d / "measure.json").write_text(json.dumps({"job": pb.FIXTURE_JOB[fixture], "tree": tree, **row}),
                                        encoding="utf-8")
    measured("aaaaaaaa", "becker", "base", cuts=30, hops=40, needle_up_mm=500.0, stitches=1, colour_changes=1,
             sttype_kappa=0.3, columns=60, word_cc=0.8, pro_board={"columns": 50, "word_cc": 0.9})
    measured("aaaaaaaa", "becker", "flag", cuts=20, hops=30, needle_up_mm=400.0, stitches=1, colour_changes=1,
             sttype_kappa=0.4, columns=55, word_cc=0.85, pro_board={"columns": 51, "word_cc": 0.9})
    measured("aaaaaaaa", "drone", "base", cuts=100, hops=120, needle_up_mm=900.0, stitches=1, colour_changes=1)
    (runs / "pro.json").write_text(json.dumps({"becker_hat_large": {"cuts": 10, "hops": 13, "needle_up_mm": 416.1},
                                               "precision_drone": {"cuts": 59, "hops": 80, "needle_up_mm": 900.6}}),
                                   encoding="utf-8")
    data = pb.build(runs, tmp_path / "out.json", inputs)
    by = {p["id"]: p for p in data["sittings"]["s"]["pairs"]}
    p = by["s:flag:becker"]
    assert p["before"]["cuts"] == 30 and p["after"]["cuts"] == 20 and p["pro"]["cuts"] == 10
    assert p["pro_side"] == {"before": {"columns": 50, "word_cc": 0.9}, "after": {"columns": 51, "word_cc": 0.9}}
    assert "unscored_why" not in p
    # drone's flag arm was never rendered: the pair is kept, named, and scored on nothing
    assert by["s:flag:drone"]["before"]["cuts"] == 100 and by["s:flag:drone"]["after"] == {}
    assert "not rendered" in by["s:flag:drone"]["unscored_why"]
    assert "not in SITTINGS" in by["s:gone:becker"]["unscored_why"]
    # and the built file feeds the pool: distances per side, the per-side pro for the board figures
    rows = pro_pooled.transformed_pairs(json.loads((tmp_path / "out.json").read_text(encoding="utf-8")))
    r = {q["id"]: q for q in rows}["s:flag:becker"]
    assert r["before"]["columns"] == 10.0 and r["after"]["columns"] == 4.0
    assert r["before"]["sttype_kappa"] == pytest.approx(0.7) and r["after"]["word_cc"] == pytest.approx(0.05)


def test_committed_inputs_validate_and_report(monkeypatch):
    monkeypatch.setattr(pooled, "B", 100)
    assert pro_pooled.INPUTS.exists(), "docs/eye-pairs-2026-11-01/pro-pair-inputs.json is missing"
    inputs = json.loads(pro_pooled.INPUTS.read_text(encoding="utf-8"))
    rep = pro_pooled.full_report(inputs)
    assert rep["n_with_both_designs"] > 0
    assert set(rep["instruments"]) == set(pro_pooled.INSTRUMENTS)
    for r in rep["instruments"].values():
        assert not {"a", "k", "agree", "accuracy", "raw"} & set(r)
    # every pair in the pool is one the fidelity pool also holds, with the same label
    fid = {p["id"]: p["label"] for p in pooled.pooled_pairs(json.loads(pooled.INPUTS.read_text(encoding="utf-8")))}
    for s in inputs["sittings"].values():
        for p in s["pairs"]:
            assert fid.get(p["id"]) == p["label"], p["id"]
