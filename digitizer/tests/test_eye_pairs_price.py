"""`tools.eye_pairs_price`: the sitting's price table, from the render it sits on.

Synthetic designs only -- no engine. Pins the three rules a reader of the
table relies on: whole-design counts are the features module's definitions,
a shape is "changed" when its needles move (not only its count), and a trim
belongs to the shape the needle is trimmed INTO.
"""
from __future__ import annotations

import json

import pytest

from tools import eye_pairs_price as ep
from tools.eye_pairs import features as ft


def _design(shapes):
    """shapes: [(shape_id, [(x, y), ...])] sewn in order, a trim between each."""
    st, runs = [], []
    for k, (sid, pts) in enumerate(shapes):
        if k:
            st.append({"x": 0, "y": 0, "type": "trim"})
            st.append({"x": pts[0][0], "y": pts[0][1], "type": "jump"})
        i0 = len(st)
        st += [{"x": x, "y": y, "type": "stitch"} for x, y in pts]
        runs.append({"i0": i0, "i1": len(st) - 1, "kind": "satin", "shape": sid, "role": ""})
    st.append({"x": 0, "y": 0, "type": "end"})
    return {"stitches": st, "runs": runs,
            "colors": [{"r": 1, "g": 2, "b": 3}],
            "stitchCount": sum(1 for s in st if s["type"] == "stitch")}


A = ("A", [(0, 0), (1, 0), (2, 0)])
B = ("B", [(5, 5), (6, 5)])
B_MOVED = ("B", [(5, 5), (6, 6)])           # same count, one needle moved
B_SPLIT = [("B", [(5, 5)]), ("B", [(6, 5), (7, 5)])]


def test_records_match_the_features_definitions():
    d = _design([A, B])
    r = ep.records(d)
    f = ft._records(d)
    assert r["stitches"] == f["stitches"] == 5
    assert r["stops"] == f["stops"] and r["cones"] == f["cones"]
    assert r["trims"] == 1


def test_identical_designs_change_no_shape():
    assert ep.changed_shapes(_design([A, B]), _design([A, B])) == set()


def test_a_moved_needle_is_a_change_even_at_the_same_count():
    assert ep.changed_shapes(_design([A, B]), _design([A, B_MOVED])) == {"B"}


def test_trims_are_scoped_to_the_shape_trimmed_into():
    d = _design([A, *B_SPLIT])
    s = ep.scoped(d, {"B"})
    assert s == {"stitches": 3, "trims": 2}
    assert ep.scoped(d, {"A"}) == {"stitches": 3, "trims": 0}


def test_cell_reads_one_figure_when_equal():
    assert ep.cell(1200, 1200) == "1,200"
    assert ep.cell(1200, 1100) == "1,200 → 1,100"
    assert ep.cell(0.0123, 0.0123, "pct") == "1.23%"
    assert ep.cell(None, 0.5, "3dp") == "n/a → 0.500"


def test_table_from_a_render_directory(tmp_path):
    (tmp_path / "designs").mkdir()
    for fx, arm_design in (("one", _design([A, *B_SPLIT])), ("two", _design([A, B]))):
        (tmp_path / "designs" / f"{fx}__base.json").write_text(json.dumps(_design([A, B])))
        (tmp_path / "designs" / f"{fx}__flag.json").write_text(json.dumps(arm_design))
    feats = {"__sources__": {}, "one": {"base": {"lost_frac": 0.1}, "flag": {"lost_frac": 0.2}},
             "two": {"base": {}, "flag": {}}, "three": {"base": {}}}
    (tmp_path / "features.json").write_text(json.dumps(feats))
    out = tmp_path / "t.json"
    assert ep.main([str(tmp_path), "flag", "--out", str(out)]) == 0
    t = json.loads(out.read_text())["flag"]
    assert t["columns"] == ep.COLUMNS
    rows = {r[0]: r for r in t["rows"]}
    assert set(rows) == {"one", "two"}               # three has no arm design
    one = dict(zip(ep.COLUMNS, rows["one"]))
    assert one["on the page"] == "pair" and one["changed shapes"] == "1"
    assert one["trims"] == "1 → 2" and one["their trims"] == "1 → 2"
    assert one["lost_frac"] == "0.1000 → 0.2000"
    assert rows["two"][1] == "identical"


def test_refuses_an_arm_with_no_designs(tmp_path):
    (tmp_path / "designs").mkdir()
    (tmp_path / "features.json").write_text(json.dumps({"__sources__": {}}))
    with pytest.raises(SystemExit):
        ep.main([str(tmp_path), "nope"])
