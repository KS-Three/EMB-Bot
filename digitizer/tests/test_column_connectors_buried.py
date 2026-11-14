"""`cfg.lettering_columns_connectors_buried` (built OFF 2026-11-14): no
needle-down hop between two of a letter's runs left on satin the letter has
already finished.

Kent pinned "Random Cross over stitch shouldn't be here" on Becker hat large
(#14, #15): running stitch the Column lane laid across the E's finished arms,
sewn after them. Read on Becker MARINE's six letters as stage 7 hands them to
the lane at 80 mm (`testdata/becker80_lane_letters.json`), with the thread's
own footprint (0.4 mm) as the ground a satin covers.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, columns, stitches

BECKER = Path(__file__).resolve().parent.parent / "testdata" / "becker80_lane_letters.json"


def _letters():
    out = {}
    for key, v in json.loads(BECKER.read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        out[key] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def _on_top(runs) -> list[float]:
    """Per needle-down hop or travel run: mm on the footprint of satin sewn
    before it and under no satin sewn after it."""
    sat = [(k, LineString(r.points).buffer(0.2)) for k, r in enumerate(runs)
           if r.kind == stitches.SATIN and len(r.points) >= 2]
    out = []
    for k, r in enumerate(runs):
        if k == 0 or r.jump or not r.points:
            continue
        a = runs[k - 1].points[-1]
        path = [a, *r.points] if r.kind == stitches.TRAVEL else [a, r.points[0]]
        if math.dist(path[0], path[-1]) < 1e-9:
            continue
        done = unary_union([g for j, g in sat if j < k])
        later = unary_union([g for j, g in sat if j >= k])
        if done.is_empty:
            continue
        x = LineString(path).intersection(done)
        if not later.is_empty:
            x = x.difference(later)
        out.append(x.length)
    return out


@pytest.fixture(scope="module")
def sewn():
    rows = {}
    for key, (poly, kw) in _letters().items():
        rows[key] = {arm: columns.lettering_columns_shape(poly, "pin", **kw, **extra)
                     for arm, extra in (("off", {}), ("false", {"connectors_buried": False}),
                                        ("on", {"connectors_buried": True}))}
    return rows


def test_default_off():
    assert PipelineConfig().lettering_columns_connectors_buried is False


def test_off_is_the_walk_as_it_was(sewn):
    for arms in sewn.values():
        a, b = arms["off"][0], arms["false"][0]
        assert [(r.points, r.kind, r.jump, r.trim) for r in a] == \
               [(r.points, r.kind, r.jump, r.trim) for r in b]


def test_off_leaves_running_stitch_on_finished_satin(sewn):
    # the bug the flag answers: four of MARINE's six letters carry a hop
    # with more than 3.9 mm on their own finished satin
    worst = {k: max(_on_top(arms["off"][0]), default=0.0) for k, arms in sewn.items()}
    assert sum(w > 3.9 for w in worst.values()) == 4, worst


def test_on_leaves_none_past_the_limit(sewn):
    for key, arms in sewn.items():
        tops = _on_top(arms["on"][0])
        assert max(tops, default=0.0) <= columns._ON_TOP_MAX_MM, (key, tops)


def test_the_e_needs_no_cut(sewn):
    # Kent's pins #14/#15 are on MARINE's E: ending each arm on its other
    # rail buries every hop, and the letter gains no trim
    off, on = sewn["5"]["off"][0], sewn["5"]["on"][0]
    assert max(_on_top(off)) > 4.0
    assert max(_on_top(on)) <= columns._ON_TOP_MAX_MM
    assert sum(bool(r.trim) for r in on) == sum(bool(r.trim) for r in off)


def test_cuts_are_counted(sewn):
    extra = sum(sum(bool(r.trim) for r in arms["on"][0]) - sum(bool(r.trim) for r in arms["off"][0])
                for arms in sewn.values())
    cut = sum(arms["on"][1].get("connectors_cut", 0) for arms in sewn.values())
    assert 0 < extra <= 4
    assert cut <= extra
