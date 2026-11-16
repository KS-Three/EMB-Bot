"""`cfg.extra["edge_walk_judge_off_walk"]` (built OFF 2026-11-16): under
`cfg.lettering_columns_connectors_edge_walk` (ON since #1533), the fold-cut
judge reads each cut candidate on the walk OFF sews.

The integration check of 11-14 against 11-15 found one design that read worse:
and_pizza at 80 mm left chest. Its p's bowl opened a slit at the top right and
its top-left shoulder was cut flat; with only the edge-walk OFF the design was
md5-identical to 11-14. Under the edge walk the judge reads every candidate on
`connectors_buried`'s walk; the walk sets each column's sewing direction and
`sewn_knots` reads the zigzag's station legs, so the p took a 4-column cut
where OFF takes 2. The flag moves the judge to OFF's walk. Which walk the
judge reads is a coin the cut depends on, not a fix for it: on OFF's walk
Gaulke's hat "&" takes a cut with a hairline slit at its waist that buried's
walk avoids, and Bukit Asam's 3 mm script "d" reads less legibly
(legibility_worst 0.571 -> 0.0), so the flag is built OFF and Kent rules it
from the sheet (eye_pairs_out/flips-1115/edge-walk-p).

The p is recorded as stage 7 hands it to the lane
(`testdata/pizza80_lane_p.json`, &pizza logo, Wikimedia Commons, public
domain; edge-walk OFF at record time).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import columns, stitches

FIXTURE = Path(__file__).resolve().parent.parent / "testdata" / "pizza80_lane_p.json"


def _p():
    v = json.loads(FIXTURE.read_text(encoding="utf-8"))["p"]
    kw = dict(v["kw"])
    for k in ("start_near", "end_near"):
        if kw.get(k) is not None:
            kw[k] = tuple(kw[k])
    return Polygon(v["exterior"], v["holes"]), kw


@pytest.fixture(scope="module")
def sewn():
    poly, kw = _p()
    arms = (("off", {}),                                        # edge walk OFF
            ("edge", {"edge_walk": True}),                      # today's main
            ("judge_off", {"edge_walk": True, "edge_walk_judge_off": True}))
    return {arm: columns.lettering_columns_shape(poly, "p", **kw, **extra) for arm, extra in arms}


def _columns(runs):
    return [len(r.points) for r in runs if r.kind == stitches.SATIN]


def _cover(runs):
    return columns.thread_cover_spill(runs, _p()[0])[0]


def test_flag_off_is_todays_cut(sewn):
    # main's p: 3 cuts, 4 satin columns, the slit and the flat shoulder bare
    (off, off_rep), (on, on_rep) = sewn["off"], sewn["edge"]
    assert len(_columns(off)) == 2                      # the bowl and the stem's foot
    assert on_rep["cuts"] == 3 and off_rep["cuts"] == 1
    assert len(_columns(on)) == 4
    assert _cover(on) == pytest.approx(0.9943, abs=1e-3)
    assert _cover(off) == pytest.approx(0.9998, abs=1e-3)


def test_flag_on_takes_the_cut_off_takes(sewn):
    (off, off_rep), (on, on_rep) = sewn["off"], sewn["judge_off"]
    assert on_rep["cuts"] == off_rep["cuts"]
    assert len(_columns(on)) == len(_columns(off))
    assert _cover(on) == pytest.approx(_cover(off), abs=1e-3)


def test_flag_on_sews_the_bowl_as_one_column(sewn):
    # the bowl and its stem sew as the one long column OFF sews (441
    # stations at record time), not cut where its top-right meets the stem
    off, on = sewn["off"][0], sewn["judge_off"][0]
    assert max(_columns(on)) >= 0.95 * max(_columns(off))


def test_flag_on_still_walks_the_edge(sewn):
    # the walk is still the edge walk's: the stem's foot is reached by a
    # trim, not by OFF's 6.1 mm travel over the bowl's finished satin
    off, on = sewn["off"][0], sewn["judge_off"][0]
    assert sum(r.trim for r in off) == 0
    assert sum(r.trim for r in on) == 1
