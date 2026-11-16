"""`cfg.lettering_columns_connectors_edge_walk` (ON since #1533) orders the
walk, not the cut (2026-11-15).

The integration check of 11-14 against 11-15 found one design that read worse:
and_pizza at 80 mm left chest. Its p's bowl opened a slit at the top right and
its top-left shoulder was cut flat; with only the edge-walk OFF the design was
md5-identical to 11-14. The fold-cut judge read every cut candidate on
`connectors_buried`'s walk when the edge-walk was on, and buried's rerouted
hops moved `sewn_knots`' reading: the p took a 4-column cut where OFF takes 2.
The judge now reads the walk OFF sews; the edge-walk still orders the walk.
Which walk the judge reads is a coin the cut depends on, not a fix for it:
on OFF's walk Gaulke's hat "&" takes a cut with a hairline slit that
buried's walk avoids (eye_pairs_out/flips-1115/edge-walk-p, 2026-11-16).

The p is recorded as stage 7 hands it to the lane
(`testdata/pizza80_lane_p.json`, edge-walk OFF at record time).
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
    return {arm: columns.lettering_columns_shape(poly, "p", **kw, **extra)
            for arm, extra in (("off", {}), ("edge", {"edge_walk": True}))}


def _columns(runs):
    return [len(r.points) for r in runs if r.kind == stitches.SATIN]


def test_the_edge_walk_keeps_the_cut_off_takes(sewn):
    (off, off_rep), (on, on_rep) = sewn["off"], sewn["edge"]
    assert len(_columns(off)) == 2                      # the bowl and the stem's foot
    assert on_rep["cuts"] == off_rep["cuts"]
    assert len(_columns(on)) == len(_columns(off))      # was 4: a slit at the bowl's top right


def test_the_p_is_covered_as_off_covers_it(sewn):
    (off, _), (on, _) = sewn["off"], sewn["edge"]
    poly, _ = _p()
    # buried's cut left 0.9943 of the p covered, OFF's 0.9998
    assert columns.thread_cover_spill(on, poly)[0] == pytest.approx(
        columns.thread_cover_spill(off, poly)[0], abs=1e-3)


def test_the_bowl_is_one_column_as_off_sews_it(sewn):
    # the bowl and its stem sew as the one long column OFF sews (441
    # stations at record time), not cut where its top-right meets the stem
    off, on = sewn["off"][0], sewn["edge"][0]
    assert max(_columns(on)) >= 0.95 * max(_columns(off))
