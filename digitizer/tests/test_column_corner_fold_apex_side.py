"""`cfg.lettering_columns_corner_fold_apex_side` (built OFF 2026-11-14): the
corner fold counts only the pieces on the apex side of a corner.

Kent on #1490's Becker pin #14 sheet: "notice how the pro makes a nice corner
with the thread andc continues the stitch to the right". The pro's E sews its
stem and arm as one column fanned round the corner; ours butted them, because
Becker's traced E has slots that narrow to a point and the arm across the
slot touches each slot's tip, which refused the fold. Read on Becker
MARINE's six letters as stage 7 hands them to the lane at 80 mm
(`testdata/becker80_lane_letters.json`), with the lane flags stage 7 passes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, columns, outline_cut, stitches

BECKER = Path(__file__).resolve().parent.parent / "testdata" / "becker80_lane_letters.json"
PRODUCTION = dict(fold_cuts=True, square_ends=True, rail_axis=True, corner_fold=True,
                  inside_stagger=True, inside_connectors=True)
E = "5"


def _letters():
    out = {}
    for key, v in json.loads(BECKER.read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        out[key] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def _key(runs):
    return [(r.points, r.kind, r.jump, r.trim) for r in runs]


@pytest.fixture(scope="module")
def sewn():
    rows = {}
    for key, (poly, kw) in _letters().items():
        rows[key] = {arm: columns.lettering_columns_shape(poly, "pin", **kw, **PRODUCTION, **extra)
                     for arm, extra in (("off", {}), ("false", {"corner_fold_apex_side": False}),
                                        ("on", {"corner_fold_apex_side": True}))}
    return rows


def test_on_by_default():
    # Kent's flip 2026-11-14 ("Flip ON"); PRE_FLIP keeps the OFF arm
    assert PipelineConfig().lettering_columns_corner_fold_apex_side is True


def test_off_is_the_cut_as_it_was(sewn):
    for arms in sewn.values():
        assert _key(arms["off"][0]) == _key(arms["false"][0])


def _kinds(poly, on):
    with outline_cut.fold_apex_side_scope(on):
        cut = outline_cut.letter_columns(poly, pitch_mm=0.4, fold_cuts=True, mitre_ends=True,
                                         rail_axis=True, corner_fold=True)
    return [c.kind for c in cut.columns]


def test_the_e_folds_round_both_corners():
    poly, _kw = _letters()[E]
    off, on = _kinds(poly, False), _kinds(poly, True)
    assert "folded" not in off and len(off) == 4         # stem, three arms: butted
    # one column, top arm -> stem -> bottom arm, and the middle arm on its own
    assert on.count("folded") == 1 and len(on) == 2


def test_only_the_e_moves(sewn):
    for key, arms in sewn.items():
        same = _key(arms["off"][0]) == _key(arms["on"][0])
        assert same == (key != E), key


def test_the_folded_e_needs_no_trim(sewn):
    runs = sewn[E]["on"][0]
    assert sum(bool(r.trim) for r in runs) < sum(bool(r.trim) for r in sewn[E]["off"][0])
    assert sum(bool(r.trim) for r in runs) == 0
    assert any(r.kind == stitches.SATIN for r in runs)


HAT_LARGE_E = Path(__file__).resolve().parent.parent / "testdata" / "becker_hat_large_lane_E.json"


def _hat_large_e():
    v = json.loads(HAT_LARGE_E.read_text(encoding="utf-8"))["E"]
    kw = {k: (tuple(x) if isinstance(x, list) else x) for k, x in v["kw"].items()}
    return Polygon(v["exterior"], v["holes"]), kw


def test_kents_pin_14_e_at_hat_large_size():
    # Becker hat large's own E (101.9 mm), as stage 7 handed it to the lane:
    # its slot tips turn 120-121 deg, past the fold's 110, and are shared
    # by two arms. ON: one column, top arm -> stem -> bottom arm, fanned
    # round both corners (Kent's #14 is the bottom one), no trim in it
    poly, kw = _hat_large_e()
    assert "folded" not in _kinds(poly, False)
    on = _kinds(poly, True)
    assert on.count("folded") == 1 and len(on) == 2
    off_runs, _r = columns.lettering_columns_shape(poly, "pin", **kw)
    on_runs, _r = columns.lettering_columns_shape(poly, "pin", **kw, corner_fold_apex_side=True)
    assert sum(bool(r.trim) for r in on_runs) == 0 < sum(bool(r.trim) for r in off_runs)
    # Kent 2026-11-18 ("Flip on, but make sure the MARINE strokes match the pros"):
    # `lettering_columns_block_butt` is ON by default and REPLACES this fold on
    # a heavy block letter (stroke >= 3.5 mm; this E is 5.3). The assertions
    # above are the apex-side fold as built (block_butt OFF, the `PRE_FLIP` arm);
    # under the default the E is a stem and three arms, butted, none folded
    with outline_cut.block_butt_scope(True):
        butted = _kinds(poly, True)
    assert butted == ["straight"] * 4


def test_apex_side_half_plane():
    hp = outline_cut._apex_side((0.0, 0.0), (-1.0, 1.0), 4.0)
    assert hp.contains(Point(-0.5, 0.5))         # toward the apex
    assert not hp.contains(Point(0.5, -0.5))     # across the corner from it
