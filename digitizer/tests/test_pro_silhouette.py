"""The silhouette-cap reading, pinned — including the bug that reversed it.

Quality review 2026-09-08 item 14. `cfg.edge_cap` is built, default OFF, and
held by ROADMAP gate 1 with "a sew-out settles which cap, if either". The
review proposes the pro's own files first, the evidence class that settled fill
row spacing, and `tools/pro_silhouette.py` reads them.

The measurement reversed itself once, which is why these assertions exist. Its
first version built the "cover" from whole runs, skipping any run that was an
area fill — and in this corpus a run is routinely BOTH a large fill and the
host of the satin columns bordering it (`border_pro`'s own report shows run#6
of the chest file as a 542.7 mm2 fill with eleven columns in it, three tracking
a fill edge). Skipping those runs hid exactly the caps being looked for and
read the pro as 76.7-100% UNCOVERED — the opposite of the truth, and an answer
that would have argued against a flag the pro's own work supports.

So: the cover must come from columns wherever they live, a fill's own rows
must never count as cover, and the pro must read as capped.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pro_silhouette                                          # noqa: E402
from border_pro import area_fills                              # noqa: E402
from study_pro import load_runs                                # noqa: E402

REFERENCE = Path(__file__).resolve().parent.parent / "testdata" / "reference"
CHEST = REFERENCE / "becker_chest_small_beckers_logo_lc_2_a.dst"

pytestmark = pytest.mark.skipif(
    not CHEST.exists(),
    reason="the commissioned reference files are not in this checkout")


@pytest.fixture(scope="module")
def chest():
    return pro_silhouette.silhouette(CHEST)


def test_the_professional_caps_his_silhouette(chest):
    """The item-14 finding, and the reason it is not a matter of taste.

    Not pinned to a decimal — the instrument may improve — but the ORDER OF
    MAGNITUDE is the whole point: single digits, against the 100% our own icon
    reads by the same definition. If this ever climbs past a third, either the
    reading broke or the claim in DOCTRINE is wrong, and both need a human.
    """
    assert chest["fills"] > 0
    assert chest["silhouette_mm"] > 100.0
    assert chest["uncovered_pct"] < 33.0, (
        f"the pro reads {chest['uncovered_pct']:.1f}% uncovered — the finding "
        "is that he caps; check `_cover` before believing this")


def test_a_fills_own_rows_are_never_cover():
    """The defect IS a row ending on the boundary, so a fill cannot cap itself.

    Without this the measurement is circular and every design reads capped.
    """
    runs, _t, _j = load_runs(CHEST)
    fills = area_fills(runs)
    assert fills, "no fill recovered — the assertion below would be vacuous"
    big = max(fills, key=lambda f: f["area"])
    only_that_fill = [runs[big["idx"]]]
    # Its columns may still contribute; its plain rows must not. With the run
    # marked as a fill, the segment pass is skipped entirely.
    cover = pro_silhouette._cover(only_that_fill, {0})
    rows_cover = pro_silhouette._cover(only_that_fill, set())
    assert rows_cover is not None
    assert cover is None or cover.area < rows_cover.area, (
        "marking a run as a fill must remove its rows from the cover")


def test_columns_sharing_a_run_with_a_fill_still_count(chest):
    """The bug that reversed the verdict, pinned from the other side.

    The chest file's cover has to be substantially larger than what the
    non-fill runs alone provide, because most of its border satin lives inside
    fill runs.
    """
    runs, _t, _j = load_runs(CHEST)
    fills = {f["idx"] for f in area_fills(runs)}
    full = pro_silhouette._cover(runs, fills)
    non_fill_runs = [r for i, r in enumerate(runs) if i not in fills]
    plain = pro_silhouette._cover(non_fill_runs, set())
    assert full is not None and plain is not None
    assert full.area > plain.area * 1.2, (
        "columns inside fill runs are not reaching the cover — this is the "
        "exact hole that read the pro as uncapped")
