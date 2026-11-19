"""`tools/prime_grader.py`'s pure helpers: no engine, no pictures."""
import json

import pytest

from tools import prime_grader as pg

ITEM = {"id": "L_x", "size": "60 x 40 mm on hat_front", "w_mm": 60.0, "h_mm": 40.0,
        "tiles": [{"name": "A1"}, {"name": "A2"}]}


def verdict(**over):
    v = {"item": "L_x", "grade": "Okay", "whole": [], "reason": "edges are rough",
         "tiles_read": ["A1", "A2"],
         "faults": [{"x_mm": 10, "y_mm": 5, "what": "jagged", "severity": "noticeable",
                     "note": "the border stair-steps", "seen_in": "A1"}]}
    v.update(over)
    return v


def test_the_rubric_is_the_pinned_one():
    # A changed rubric is a new dated version: bump RUBRIC_VERSION and the sha together.
    assert pg.rubric_sha() == pg.RUBRIC_SHA256
    assert pg.RUBRIC_VERSION in pg.RUBRIC.read_text(encoding="utf-8").splitlines()[0]


def test_the_rubric_names_every_kind_grade_and_tick():
    text = pg.RUBRIC.read_text(encoding="utf-8")
    for word in (*pg.WHATS, *pg.WHOLE, *pg.SEVERITIES, *pg.GRADES):
        assert word in text, word


def test_every_kind_has_a_class():
    assert set(pg.CLASS_OF) == set(pg.WHATS)


def test_tile_grid_covers_the_design_and_respects_the_cap():
    for w, h in ((102.0, 64.7), (20.0, 12.0), (300.0, 200.0), (114.0, 42.0)):
        tiles = pg.tile_grid(w, h)
        assert 1 <= len(tiles) <= pg.MAX_TILES
        assert min(t["x0"] for t in tiles) == 0 and min(t["y0"] for t in tiles) == 0
        assert max(t["x1"] for t in tiles) == pytest.approx(w, abs=0.02)
        assert max(t["y1"] for t in tiles) == pytest.approx(h, abs=0.02)
        assert len({t["name"] for t in tiles}) == len(tiles)
    assert pg.tile_grid(20.0, 12.0)[0]["name"] == "A1"


def test_clean_verdict_keeps_a_good_one():
    rec = pg.clean_verdict(verdict(), ITEM)
    assert rec["grade"] == "Okay" and rec["faults"][0]["what"] == "jagged"


@pytest.mark.parametrize("over, word", [
    ({"grade": "Fine"}, "grade"),
    ({"whole": ["ugly"]}, "whole"),
    ({"reason": " "}, "reason"),
    ({"tiles_read": ["A1"]}, "tiles_read"),
    ({"item": "L_y"}, "item"),
    ({"faults": [{"x_mm": 500, "y_mm": 5, "what": "jagged", "severity": "ruins", "note": "n", "seen_in": "A1"}]},
     "off the design"),
    ({"faults": [{"x_mm": 5, "y_mm": 5, "what": "ugly", "severity": "ruins", "note": "n", "seen_in": "A1"}]}, "what"),
    ({"faults": [{"x_mm": 5, "y_mm": 5, "what": "gap", "severity": "bad", "note": "n", "seen_in": "A1"}]}, "severity"),
    ({"faults": [{"x_mm": 5, "y_mm": 5, "what": "gap", "severity": "ruins", "note": "", "seen_in": "A1"}]}, "note"),
    ({"faults": [{"x_mm": 5, "y_mm": 5, "what": "gap", "severity": "ruins", "note": "n", "seen_in": "Z9"}]}, "seen_in"),
])
def test_clean_verdict_refuses_what_the_rubric_does_not_allow(over, word):
    with pytest.raises(ValueError, match=word):
        pg.clean_verdict(verdict(**over), ITEM)


def _kit_and_readings():
    kit = {"items": [ITEM, {**ITEM, "id": "L_y"}]}
    readings = {"items": {
        "L_x": pg.clean_verdict(verdict(), ITEM),
        "L_y": pg.clean_verdict(verdict(item="L_y", grade="Bad", faults=[
            {"x_mm": 1, "y_mm": 1, "what": "wavy", "severity": "ruins", "note": "n", "seen_in": "A1"},
            {"x_mm": 2, "y_mm": 2, "what": "pen_flow", "severity": "nitpick", "note": "n", "seen_in": "A2"}]),
            {**ITEM, "id": "L_y"})}}
    return kit, readings


def test_rollup_counts_gross_faults_by_class_and_design():
    ru = pg.rollup(*_kit_and_readings())
    assert ru["designs"] == 2 and ru["grades"]["Okay"] == 1 and ru["grades"]["Bad"] == 1
    assert ru["mean_step"] == 2.5
    assert ru["classes"] == {"edge": ["L_x", "L_y"]}          # the nitpick pen_flow is not gross
    assert ru["rows"][1]["ruins"] == 1 and ru["rows"][1]["nitpick"] == 1


def test_movement_reports_grade_steps_and_class_changes():
    kit, readings = _kit_and_readings()
    prev = {"rollup": pg.rollup(kit, readings)}
    assert pg.movement(pg.rollup(kit, readings), prev) == []
    readings["items"]["L_y"]["grade"] = "Good"
    readings["items"]["L_y"]["faults"] = []
    (m,) = pg.movement(pg.rollup(kit, readings), prev)
    assert m == {"id": "L_y", "was": "Bad", "grade": "Good", "steps": -2, "gained": [], "cleared": ["edge"]}
    assert pg.movement(pg.rollup(kit, readings), None) == []


def test_weighted_kappa():
    assert pg.weighted_kappa([0, 1, 2, 3, 4], [0, 1, 2, 3, 4]) == 1.0
    assert pg.weighted_kappa([0, 0, 4, 4], [4, 4, 0, 0]) == -1.0
    assert pg.weighted_kappa([2, 2], [2, 2]) is None
    k = pg.weighted_kappa([0, 1, 2, 3, 4, 2], [1, 1, 2, 4, 4, 3])
    assert 0 < k < 1


def test_pin_rows_separates_a_hit_from_a_same_class_hit():
    pins = [{"x_mm": 10, "y_mm": 5, "what": "wavy", "severity": "noticeable"},
            {"x_mm": 10, "y_mm": 5, "what": "colour", "severity": "ruins"},
            {"x_mm": 50, "y_mm": 30, "what": "jagged", "severity": "ruins"}]
    faults = [{"x_mm": 11, "y_mm": 6, "what": "jagged"}]
    rows = pg.pin_rows(pins, faults)
    assert [(r["hit"], r["hit_class"]) for r in rows] == [(True, True), (True, False), (False, False)]


def test_scorecard_markdown_states_what_it_is(tmp_path):
    kit, readings = _kit_and_readings()
    card = {"date": "2026-11-17", "rubric_version": pg.RUBRIC_VERSION, "rubric_sha256": pg.RUBRIC_SHA256,
            "tree_sha": "abcdef123456", "rollup": pg.rollup(kit, readings), "yardstick": {},
            "readings": readings["items"], "prev_date": None, "movement": []}
    md = pg.scorecard_markdown(card)
    assert "not a quality claim" in md and "`L_y`" in md and "the border stair-steps" in md
    json.dumps(card)


# ---- rubric 2026-11-18 and the kit's flat-ended renders ---------------------------------------

def test_the_rubric_is_the_2026_11_18_one_and_says_what_cannot_be_drawn():
    # Literal on purpose: the next change is a new dated version, not an edit of this one.
    assert pg.RUBRIC_VERSION == "2026-11-18"
    assert pg.RUBRIC_SHA256 == "9a169b10624376fc30dc5fa515bb347826565c2fc463855a9fd9b8f8dd2bd2ec"
    text = pg.RUBRIC.read_text(encoding="utf-8")
    assert "spaced satin" in text and "under about 1 mm" in text and "solid sewn line" in text


def _satin_design():
    from tools.satin_caps_demo import synthetic_design
    return synthetic_design()


def test_the_default_render_is_still_round_capped_and_butt_is_kit_only():
    import numpy as np
    from digitizer_core import stitchviz
    d = _satin_design()
    default = stitchviz.render_design(d, px_per_mm=12.0)
    assert np.array_equal(default, stitchviz.render_design(d, px_per_mm=12.0, caps="round"))
    assert not np.array_equal(default, stitchviz.render_design(d, px_per_mm=12.0, caps="butt"))
    assert stitchviz.render_design(d, px_per_mm=12.0, caps="butt").shape == default.shape


def test_butt_caps_do_not_grow_the_footprint_past_round():
    """Flat ends draw the envelope the stitches sew: never more thread than the round draw's bumps."""
    import numpy as np
    from digitizer_core import stitchviz
    d = _satin_design()
    cloth = np.array(stitchviz.FABRIC_BGR)
    covered = lambda im: (np.abs(im.astype(int) - cloth).sum(-1) > 90).sum()  # noqa: E731
    assert covered(stitchviz.render_design(d, px_per_mm=30.0, caps="butt")) \
        < covered(stitchviz.render_design(d, px_per_mm=30.0, caps="round"))


def test_a_straight_satin_edge_is_flatter_with_butt_caps():
    import numpy as np
    from digitizer_core import stitchviz
    d = {"stitches": [{"type": "stitch", "x": round(i * 4), "y": 0 if i % 2 == 0 else 30}
                      for i in range(60)], "colors": [{"r": 0, "g": 0, "b": 0}]}
    cloth = np.array(stitchviz.FABRIC_BGR)

    def top_edge_roughness(caps):
        im = stitchviz.render_design(d, px_per_mm=30.0, caps=caps)
        ink = np.abs(im.astype(int) - cloth).sum(-1) > 150
        cols = slice(int(im.shape[1] * 0.2), int(im.shape[1] * 0.8))
        top = np.array([np.argmax(ink[:, c]) if ink[:, c].any() else 0 for c in range(im.shape[1])])[cols]
        return float(top.std())
    assert top_edge_roughness("butt") < top_edge_roughness("round")


def test_kit_defaults_to_butt_and_the_option_reaches_the_item_builder():
    import inspect
    assert pg.KIT_CAPS == "butt"
    assert inspect.signature(pg.build_item).parameters["caps"].default == "butt"
    assert inspect.signature(pg.travel_picture).parameters["caps"].default == "butt"


def test_a_card_after_a_different_rubric_says_not_comparable():
    kit, readings = _kit_and_readings()
    card = {"date": "2026-11-19", "rubric_version": pg.RUBRIC_VERSION, "rubric_sha256": pg.RUBRIC_SHA256,
            "tree_sha": "abcdef123456", "rollup": pg.rollup(kit, readings), "yardstick": {},
            "readings": readings["items"], "prev_date": "2026-11-18", "prev_rubric_version": "2026-11-17",
            "movement": [{"id": "L_y", "new": True, "grade": "Okay"}]}
    md = pg.scorecard_markdown(card)
    assert "Not comparable" in md and "first card under rubric 2026-11-18" in md
    assert "`L_y`: new" not in md
    card["prev_rubric_version"] = pg.RUBRIC_VERSION
    assert "Not comparable" not in pg.scorecard_markdown(card)


# ---- repeat: the grader's agreement with itself (2026-11-19) ----------------------------------

def _f(x, y, what="jagged", sev="noticeable"):
    return {"x_mm": x, "y_mm": y, "what": what, "severity": sev, "note": "n", "seen_in": "A1"}


def test_pooled_kappa_is_one_for_identical_readers_and_symmetric():
    g = [[0, 0, 0], [2, 2, 2], [4, 4, 4], [1, 1, 1]]
    assert pg.pooled_kappa(g) == 1.0
    g2 = [[0, 1, 0], [2, 2, 3], [4, 3, 4], [1, 1, 2]]
    k = pg.pooled_kappa(g2)
    assert 0 < k < 1
    assert pg.pooled_kappa([row[::-1] for row in g2]) == k        # reader order does not matter
    lo, hi = pg.pooled_kappa_ci(g2, boots=200)
    assert lo <= k <= hi


def test_pair_kappas_names_every_pair_with_n_and_its_widest_gap():
    rows = pg.pair_kappas([[0, 1, 0], [2, 2, 4], [4, 3, 4], [1, 1, 2]])
    assert [r["pair"] for r in rows] == [[1, 2], [1, 3], [2, 3]]
    assert all(r["n"] == 4 for r in rows)
    assert rows[1]["max_steps"] == 2 and rows[1]["same"] == 2


def test_second_reader_rows_counts_gross_faults_only_and_needs_the_same_class_for_hit_class():
    r1 = [_f(10, 10, "jagged"), _f(40, 30, "missing", "ruins"), _f(5, 5, "gap", "nitpick")]
    r2 = [_f(11, 11, "wavy", "nitpick"),          # edge class, 1.4 mm away: a same-class hit, not gross
          _f(41, 30, "colour", "noticeable")]     # different class: a hit, not a class hit
    rows = pg.second_reader_rows([r1, r2])
    mine = [r for r in rows if r["reader"] == 0]
    assert len(mine) == 2                         # the nitpick gap seeds nothing
    by = {r["class"]: r for r in mine}
    assert by["edge"]["hit_class"] and not by["edge"]["hit_class_gross"]
    assert by["missing"]["hit"] and not by["missing"]["hit_class"]
    assert len([r for r in rows if r["reader"] == 1]) == 1       # r2's one gross fault, against r1


def test_fault_clusters_takes_one_fault_per_reader_and_does_not_chain():
    # Three readers along one border, 2.5 mm apart: A-B and B-C are within 3 mm, A-C is not.
    readers = [[_f(0, 0)], [_f(2.5, 0, sev="nitpick")], [_f(5, 0)]]
    cl = pg.fault_clusters(readers)
    assert sorted(c["readers"] for c in cl) == [1, 2]            # A+B, then C alone: no chain to all three
    same = [[_f(0, 0), _f(0.5, 0)], [_f(1, 0)], [_f(1, 1, "missing")]]
    cl = pg.fault_clusters(same)
    assert sorted(c["readers"] for c in cl) == [1, 1, 2]         # reader 1's second fault and the other class are places of their own


def test_repeat_report_end_to_end_without_chance():
    kit = {"items": [ITEM, {**ITEM, "id": "L_y"}]}
    v = lambda iid, grade, faults: pg.clean_verdict(verdict(item=iid, grade=grade, faults=faults),  # noqa: E731
                                                     ITEM if iid == "L_x" else {**ITEM, "id": "L_y"})
    sets = [{"L_x": v("L_x", "Okay", [_f(10, 5)]), "L_y": v("L_y", "Bad", [_f(30, 20, "missing", "ruins")])},
            {"L_x": v("L_x", "Okay", [_f(11, 5)]), "L_y": v("L_y", "Okay", [])},
            {"L_x": v("L_x", "Good", []), "L_y": v("L_y", "Bad", [_f(30, 21, "missing")])}]
    res = pg.repeat_report(kit, sets)
    assert res["readers"] == 3 and res["designs"] == 2
    d = {x["id"]: x for x in res["designs_detail"]}
    assert d["L_x"]["grades"] == ["Okay", "Okay", "Good"] and d["L_x"]["spread"] == 1
    assert d["L_x"]["places_found_by"] == {"3": 0, "2": 1, "1": 0}
    assert res["second_reader"]["rows"] == 8                     # 4 gross faults x 2 other readers
    assert res["second_reader"]["hit_class"] == 0.5
    assert "chance" not in res["second_reader"]
    text = pg.repeat_text(res)
    assert "kappa pooled" in text and "n 2 designs x 3 readers" in text
    json.dumps(res)


def test_repeat_is_a_subcommand(tmp_path, capsys):
    with pytest.raises(SystemExit):
        pg.main(["repeat", "--help"])
    assert "--verdicts" in capsys.readouterr().out


# ---- two readers per design (Kent 2026-11-19: "Two readers, twice a week") --------------------

def _rec(grade, faults, whole=()):
    return pg.clean_verdict(verdict(grade=grade, faults=faults, whole=list(whole)), ITEM)


def test_combine_two_keeps_only_faults_both_place_at_the_midpoint_and_the_lower_severity():
    a = _rec("Okay", [_f(10, 10, "jagged", "ruins"), _f(30, 20, "missing", "ruins"), _f(50, 30, "gap")])
    b = _rec("Okay", [_f(12, 10, "wavy", "noticeable"),   # edge class, 2 mm: agreed
                      _f(31, 20, "missing", "ruins"),      # agreed, both say ruins
                      _f(50, 30, "colour")])               # same spot, other class: not agreed
    rec = pg.combine_two(a, b)
    assert rec["grade"] == "Okay" and not rec["disagree"]
    got = {pg.CLASS_OF[f["what"]]: f for f in rec["faults"]}
    assert set(got) == {"edge", "missing"}
    assert (got["edge"]["x_mm"], got["edge"]["severity"]) == (11.0, "noticeable")   # lower of ruins / noticeable
    assert got["missing"]["severity"] == "ruins"                                      # both said it
    assert sorted((f["reader"], f["what"]) for f in rec["one_reader"]) == [(1, "gap"), (2, "colour")]


def test_combine_two_pairs_one_to_one():
    a = _rec("Okay", [_f(10, 10), _f(11, 10)])
    b = _rec("Okay", [_f(10.5, 10)])
    rec = pg.combine_two(a, b)
    assert len(rec["faults"]) == 1 and len(rec["one_reader"]) == 1


def test_a_disagreeing_design_leaves_the_grade_row_and_movement():
    kit = {"items": [ITEM, {**ITEM, "id": "L_y"}]}
    readings = {"items": {"L_x": pg.combine_two(_rec("Okay", []), _rec("Bad", [])),
                          "L_y": pg.combine_two(_rec("Bad", []), _rec("Bad", []))}}
    ru = pg.rollup(kit, readings)
    assert ru["disagree"] == ["L_x"]
    assert ru["grades"]["Bad"] == 1 and ru["grades"]["Okay"] == 0 and ru["mean_step"] == 3.0
    row = ru["rows"][0]
    assert row["grade"] == "Okay / Bad" and row["step"] is None
    prev = {"rollup": {"rows": [{**row, "grade": "Good", "step": 1, "disagree": False, "gross_by_class": {}},
                                {**ru["rows"][1], "grade": "Okay", "step": 2}]}}
    assert [m["id"] for m in pg.movement(ru, prev)] == ["L_y"]                 # L_x is not a move


def _two_reader_card(prev_readers):
    kit = {"items": [ITEM]}
    readings = {"items": {"L_x": pg.combine_two(_rec("Okay", [_f(10, 5)]), _rec("Bad", [_f(40, 30, "gap")]))}}
    return {"date": "2026-11-20", "rubric_version": pg.RUBRIC_VERSION, "rubric_sha256": pg.RUBRIC_SHA256,
            "tree_sha": "abcdef123456", "rollup": pg.rollup(kit, readings), "yardstick": {},
            "readings": readings["items"], "prev_date": "2026-11-19", "prev_rubric_version": pg.RUBRIC_VERSION,
            "movement": [], "readers": 2, "agreement_rule": pg.AGREEMENT_RULE, "prev_readers": prev_readers}


def test_the_two_reader_card_states_its_rule_and_lists_one_reader_faults_apart():
    md = pg.scorecard_markdown(_two_reader_card(1))
    assert "**Readers: 2.**" in md and "within 3 mm" in md
    assert "## Faults both readers place" in md and "## One reader only (not acted on)" in md and "reader 2: (40.0, 30.0) mm, gap" in md
    assert "Okay / Bad (readers disagree)" in md and "Readers disagree on 1 design" in md
    assert "first card of the two-reader series" in md                       # against a one-reader card
    assert "two-reader series" not in pg.scorecard_markdown(_two_reader_card(2))
    json.dumps(_two_reader_card(2))


def test_a_one_reader_card_reads_as_before():
    kit, readings = _kit_and_readings()
    card = {"date": "2026-11-17", "rubric_version": pg.RUBRIC_VERSION, "rubric_sha256": pg.RUBRIC_SHA256,
            "tree_sha": "abcdef123456", "rollup": pg.rollup(kit, readings), "yardstick": {},
            "readings": readings["items"], "prev_date": None, "movement": []}
    md = pg.scorecard_markdown(card)
    assert "One reader only" not in md and "Readers: 2" not in md and "A Claude session graded" in md


def test_scorecard_builds_one_card_from_two_verdict_folders(tmp_path, monkeypatch):
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()
    kit = {"rubric_version": pg.RUBRIC_VERSION, "rubric_sha256": pg.RUBRIC_SHA256, "kit_sha256": "k",
           "items": [ITEM]}
    (kit_dir / "kit.json").write_text(json.dumps(kit))
    for n, (grade, fx) in enumerate((("Okay", 10), ("Okay", 11)), 1):
        d = tmp_path / f"verdicts-r{n}"
        d.mkdir()
        (d / "L_x.json").write_text(json.dumps(verdict(grade=grade, faults=[_f(fx, 5)])))
    out = tmp_path / "out"
    assert pg.main(["scorecard", "--kit", str(kit_dir), "--out", str(out), "--date", "2026-11-20",
                    "--verdicts", str(tmp_path / "verdicts-r1"), str(tmp_path / "verdicts-r2")]) == 0
    card = json.loads((out / "latest.json").read_text())
    assert card["readers"] == 2 and card["readings"]["L_x"]["faults"][0]["x_mm"] == 10.5
    assert pg.main(["scorecard", "--kit", str(kit_dir), "--out", str(out),
                    "--verdicts", str(tmp_path / "verdicts-r1")]) == 2
