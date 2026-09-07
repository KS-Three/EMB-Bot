"""`tools/cone_revisits.py` — the price of folding a cone sewn twice.

MASTER_SCOPE defect 16 records that `cfg.merge_duplicate_cones` leaves
survivors and calls each remaining merge "FREE (the cone is already loaded)".
That is true of THREAD cost. The tool exists because it is false of SEQUENCING
cost, and the measurement says by how much: over 26 fixtures x 2 garments,
4 combos sew a cone twice and **not one of the four is adjacent** — the gaps
are 7 and 11 blocks.

These tests are synthetic and instant. They pin the two things the tool has to
get right for that number to mean anything: the gap arithmetic, and the route
classification that separates the half a shipped flag already closes from the
half that is still open.
"""

import pytest

from digitizer_core import stitches as st
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

from tools.cone_revisits import revisits


class _Region:
    """The two fields `_block_routes` reads off a pipeline result."""

    def __init__(self, shape_id: str, resnapped: bool = False):
        self.shape_id = shape_id
        self.meta = {"thread_resnapped_de00": 4.2} if resnapped else {}


class _Result:
    def __init__(self, *regions: _Region):
        self.regions = list(regions)


def _block(num: str, *shape_ids: str) -> StitchBlock:
    return StitchBlock(
        thread_index=0, thread_number=num, rgb=(1, 2, 3),
        runs=[StitchRun(points=[(0.0, 0.0), (1.0, 1.0)], kind=st.FILL,
                        shape_id=s) for s in shape_ids])


def _plan(*pairs: tuple[str, tuple[str, ...]]) -> StitchPlan:
    """`plan.palette` is one entry PER BLOCK — the whole basis of the count."""
    return StitchPlan(
        blocks=[_block(num, *sids) for num, sids in pairs],
        palette=[{"number": num, "name": f"n{num}", "rgb": (1, 2, 3)}
                 for num, _sids in pairs])


def test_a_cone_sewn_once_is_not_a_revisit():
    plan = _plan(("0182", ("Sa",)), ("0020", ("Sb",)), ("1375", ("Sc",)))
    assert revisits(plan, _Result(_Region("Sa"), _Region("Sb"),
                                  _Region("Sc"))) == []


def test_the_gap_is_the_distance_between_the_two_blocks():
    """The number that prices the fold. `region_blobs` measures 11 — blocks 1
    and 12 — and a gap is what says whether folding is a nudge or a reorder
    through everything in between."""
    plan = _plan(("0020", ("Sa",)), ("0182", ("Sb",)), ("1375", ("Sc",)),
                 ("0111", ("Sd",)), ("0182", ("Se",)))
    got = revisits(plan, _Result(*[_Region(f"S{c}") for c in "abcde"]))
    assert len(got) == 1
    assert got[0]["cone"] == "0182"
    assert got[0]["blocks"] == [1, 4]
    assert got[0]["gap"] == 3


def test_a_band_block_is_read_off_its_derived_shape_ids():
    """Gradient bands are built in stage 6, long after the quantize-time fold,
    which is why they survive it. They are recognised by the `-blend`/`-shade`
    suffix and NOT by anything the fold can see."""
    plan = _plan(("0182", ("Sb971b1c2-blend2",)), ("0020", ("Sx",)),
                 ("0182", ("S0ad9734d-blend4",)))
    got = revisits(plan, _Result(_Region("Sb971b1c2"), _Region("Sx"),
                                 _Region("S0ad9734d")))
    assert [r["route"] for r in got] == ["band"]


def test_a_resnap_block_is_read_off_the_stage_4_stamp():
    """`revalidate_threads` can INVENT a cone no layer declares, so the fold's
    layer-time list cannot see it. The stamp is the only marker."""
    plan = _plan(("3971", ("Sa",)), ("0020", ("Sx",)), ("3971", ("Sb",)))
    got = revisits(plan, _Result(_Region("Sa", resnapped=True),
                                 _Region("Sx"), _Region("Sb")))
    assert [r["route"] for r in got] == ["resnap"]


def test_a_plain_duplicate_is_labelled_as_the_folds_own_territory():
    """Neither route. A survivor here would be a defect in
    `merge_duplicate_cones` rather than a gap in its reach — which is why it
    gets its own label instead of being lumped in with the two."""
    plan = _plan(("0182", ("Sa",)), ("0020", ("Sx",)), ("0182", ("Sb",)))
    got = revisits(plan, _Result(_Region("Sa"), _Region("Sx"), _Region("Sb")))
    assert [r["route"] for r in got] == ["plain"]


def test_both_routes_are_reported_when_both_apply():
    """A band whose parent region was also re-snapped is both, and hiding
    either would send a reader to the wrong fix."""
    plan = _plan(("0182", ("Sp-blend1",)), ("0020", ("Sx",)),
                 ("0182", ("Sq-blend3",)))
    got = revisits(plan, _Result(_Region("Sp", resnapped=True),
                                 _Region("Sx"), _Region("Sq")))
    assert got[0]["route"] == "band,resnap"


def test_a_missing_result_still_classifies_the_bands():
    """`revisits` is called on a stored plan in places that no longer have the
    pipeline result. The resnap stamp is then unknowable, and the tool must
    say `band`/`plain` rather than raise."""
    plan = _plan(("0182", ("Sa-blend1",)), ("0020", ("Sx",)),
                 ("0182", ("Sb-blend2",)))
    assert [r["route"] for r in revisits(plan, None)] == ["band"]


def test_three_blocks_of_one_cone_report_the_full_span():
    """The gap is first-to-last, not first-to-second: folding all three costs
    the whole span, and reporting the shorter hop would understate it."""
    plan = _plan(("0182", ("Sa",)), ("0182", ("Sb",)), ("0020", ("Sx",)),
                 ("1375", ("Sy",)), ("0182", ("Sc",)))
    got = revisits(plan, _Result(*[_Region(f"S{c}") for c in "abxyc"]))
    assert got[0]["blocks"] == [0, 1, 4]
    assert got[0]["gap"] == 4
