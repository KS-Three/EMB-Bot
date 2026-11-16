"""`_Sewn` asked about a footprint GEOS built invalid: answer, never raise.

A fill footprint is a buffered path (`stage6_fill._footprint`), and GEOS can
build that buffer invalid -- a self-intersecting MultiPolygon. Cutting a line
or a box by it then raised TopologyException ("side location conflict"), out
of `_reorder_for_cover`, and the whole digitize died. Hit 2026-11-15 on the
heraldic crest (Commons kit 1111) with `speck_prune` ON: the prune moved the
fill's paths onto that buffer. A digitize must never raise because of a pruned
shape (Director 2026-11-15), so `_Sewn._cut` makes the refused footprints
valid and asks again -- only then: a cut GEOS answers is the cut as before.

`testdata/sewn_invalid_footprint_crest.json` holds the line and the four
footprints from that run, captured at the raise.
"""
import json
from pathlib import Path

import shapely

from digitizer_core import stage6_fill as F

_FIX = json.loads((Path(__file__).resolve().parents[1] / "testdata"
                   / "sewn_invalid_footprint_crest.json").read_text())
LINE = shapely.from_wkb(_FIX["line_wkb"])
PARTS = [shapely.from_wkb(w) for w in _FIX["footprints_wkb"]]


def _sewn(parts):
    sewn = None
    for p in parts:
        sewn = F._sewn_add(sewn, p)
    return sewn


def _reference_on_line(line, parts):
    """Length of `line` over the union of the parts made valid, built the
    slow way: the set question `on_line` answers."""
    return shapely.intersection(line, shapely.union_all(shapely.make_valid(parts))).length


def test_the_fixture_holds_an_invalid_footprint():
    assert [p.is_valid for p in PARTS].count(False) == 1
    assert not shapely.is_valid(PARTS[3])


def test_on_line_answers_over_an_invalid_footprint():
    got = _sewn(PARTS).on_line(LINE)
    assert 0.0 <= got <= LINE.length + 1e-9
    assert abs(got - _reference_on_line(LINE, PARTS)) < 1e-6


def test_clipped_answers_over_an_invalid_footprint():
    x0, y0, x1, y1 = LINE.buffer(0.5).bounds
    got = _sewn(PARTS).clipped(x0, y0, x1, y1)
    want = shapely.intersection(shapely.union_all(shapely.make_valid(PARTS)),
                                shapely.box(x0, y0, x1, y1))
    assert got.is_valid
    assert abs(got.area - want.area) < 1e-6


def test_valid_footprints_are_cut_as_they_always_were():
    """With every footprint valid, no GEOS refusal: the parts are the very
    objects added (nothing repaired) and the answer is the plain cut's."""
    valid = PARTS[:3]
    sewn = _sewn(valid)
    got = sewn.on_line(LINE)
    assert all(a is b for a, b in zip(sewn._parts[:sewn._n], valid))
    assert abs(got - _reference_on_line(LINE, valid)) < 1e-9
