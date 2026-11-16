"""`cfg.extra["lettering_columns_judge_entry_free"]` (built OFF 2026-11-16):
`fold_cuts`' judge sews each candidate cut from no entry and to no exit.

`lettering_columns_shape`'s judge sewed every candidate with the letter's own
`start_near` / `end_near`. The walk follows them -- which column sews first,
so which end tucks under its neighbour and which butts it -- `sewn_knots` reads
the walk, and the judge picks the cut. So where stage 7 brought the needle in
decided how the letter was BUILT: Becker's hat-large A, its word sewn in
reading order (`lettering_columns_reading_order`), took another cut than main's
-- 489 needles against 441, 206 of them shared -- and read 13.6 -> 19.0 deg
against the pro (`tools/apex_pro.py`). The direction a letter is sewn may
follow the needle; its cut should not.

Read on the A as stage 7 handed it to the lane on main (bea3a79a), with the
two entries it was handed: main's and reading order's
(`testdata/becker_hat_large_lane_A_entries.json`, from the tracked Becker art).
"""
from __future__ import annotations

import contextvars
import importlib
import json
from pathlib import Path

import numpy as np
import pytest
from shapely import wkb

from digitizer_core import columns, stitches

FIXTURE = Path(__file__).resolve().parent.parent / "testdata" / "becker_hat_large_lane_A_entries.json"


def _dec(v):
    if isinstance(v, dict) and "__wkb__" in v:
        return wkb.loads(v["__wkb__"], hex=True)
    if isinstance(v, dict) and "__tuple__" in v:
        return tuple(_dec(x) for x in v["__tuple__"])
    if isinstance(v, list):
        return [_dec(x) for x in v]
    return v


def _needles(entry: str, free: bool) -> set:
    """The A's satin needles (direction-free), sewn from `entry`."""
    v = json.loads(FIXTURE.read_text(encoding="utf-8"))["A"]
    poly = wkb.loads(v["poly_wkb"], hex=True)
    kw = {k: _dec(x) for k, x in v["kw"].items()}
    start, end = (tuple(_dec(p)) for p in v["entries"][entry])

    def go():
        for key, val in v["context"].items():
            mod, var = key.split(".")
            getattr(importlib.import_module(f"digitizer_core.{mod}"), var).set(val)
        return columns.lettering_columns_shape(
            poly, v["shape_id"], start_near=start, end_near=end,
            **kw, **({"judge_entry_free": True} if free else {}))[0]
    runs = contextvars.copy_context().run(go)
    return {tuple(np.round(p, 3)) for r in runs if r.kind == stitches.SATIN for p in r.points}


@pytest.fixture(scope="module")
def sewn():
    return {(e, f): _needles(e, f) for e in ("main", "reading_order") for f in (False, True)}


def test_off_the_entry_changes_the_cut(sewn):
    """Today's judge, as main sews it: entered from reading order's side, the
    A is built on another cut."""
    a, b = sewn[("main", False)], sewn[("reading_order", False)]
    assert (len(a), len(b)) == (441, 489)
    assert len(a & b) < len(a) // 2


def test_on_the_a_is_built_the_same_from_either_entry(sewn):
    assert sewn[("main", True)] == sewn[("reading_order", True)]


def test_on_the_cut_is_the_one_main_takes_from_its_own_entry(sewn):
    """Freed from the entry, the judge picks the cut main already sews: the
    flag moves this letter only where an entry had moved it."""
    assert sewn[("main", True)] == sewn[("main", False)]
