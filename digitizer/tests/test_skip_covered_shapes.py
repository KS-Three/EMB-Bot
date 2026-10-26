"""`cfg.skip_covered_shapes` (built OFF 2026-10-26): a shape whose whole thread
lies on thread of its OWN colour block that other shapes sew is not sewn.

With the MFab recipe on, the white keyline traces as the field plus 31 (hat) /
51 (LC) slivers 0.1-0.3 mm wide along its inner edge, each its own run with a
cut either side. The professional's keyline satin covers all of them; ours,
the field's loops and fill, already covers most -- sewn after the slivers on
the hat, before them on the LC (`docs/mfab-recipe-trims-2026-10-26.md`). This
file pins the rule on hand-built blocks: what counts as cover (same block,
another shape, the thread's whole width, before or after), that a dropped
shape's cover stays, and how the run after a dropped stretch lifts.
"""
from __future__ import annotations

from digitizer_core import stitches
from digitizer_core.stage7_sequence import _skip_covered_shapes
from digitizer_core.stitches import StitchBlock, StitchRun

from .test_silhouette_underfill_panels import ON, OUTLINES, _md5, _sew, panel

TRIM_AT = 3.0


def _rows(x0, x1, y0, y1, pitch=0.3, shape="Sfill", jump=True, trim=True):
    """A fill-like run: rows `pitch` apart from y0 to y1, x0..x1 (dense cover)."""
    pts, y, flip = [], y0, False
    while y <= y1 + 1e-9:
        a, b = (x1, x0) if flip else (x0, x1)
        pts += [(a, y), (b, y)]
        y += pitch
        flip = not flip
    return StitchRun(points=pts, kind=stitches.FILL, jump=jump, trim=trim, shape_id=shape)


def _line(x0, x1, y, shape, jump=True, trim=True):
    n = int(abs(x1 - x0)) + 1
    return StitchRun(points=[(x0 + (x1 - x0) * i / (n - 1), y) for i in range(n)],
                     kind=stitches.RUN, jump=jump, trim=trim, shape_id=shape)


def _block(*runs, thread=1):
    return StitchBlock(thread_index=thread, thread_number=str(4000 + thread), rgb=(255, 255, 255),
                       runs=list(runs))


def test_a_sliver_its_own_colour_covers_later_is_not_sewn():
    # the hat's order: the slivers first, the field after
    b = _block(_line(1, 9, 1.0, "Ssliver"), _rows(0, 10, 0, 2), _line(20, 30, 1.0, "Sfar"))
    assert _skip_covered_shapes([b], TRIM_AT) == ["Ssliver"]
    assert [r.shape_id for r in b.runs] == ["Sfill", "Sfar"]
    # the fill now opens the block: it takes the dropped sliver's opening lift
    assert b.runs[0].jump and b.runs[0].trim


def test_a_sliver_on_thread_sewn_before_is_not_sewn_either():
    # the LC's order: the field first, the slivers on top of it after
    b = _block(_rows(0, 10, 0, 2), _line(1, 9, 1.0, "Ssliver"), _line(20, 30, 1.0, "Sfar"))
    assert _skip_covered_shapes([b], TRIM_AT) == ["Ssliver"]
    assert [r.shape_id for r in b.runs] == ["Sfill", "Sfar"]
    # (10, 2.1) is where the rows end; (20, 1) is over trim_at away: a cut
    assert b.runs[1].jump and b.runs[1].trim


def test_a_sliver_reaching_past_the_cover_stays():
    b = _block(_line(1, 12, 1.0, "Ssliver"), _rows(0, 10, 0, 2))
    assert _skip_covered_shapes([b], TRIM_AT) == []
    assert [r.shape_id for r in b.runs] == ["Ssliver", "Sfill"]


def test_the_thread_edge_counts_not_just_the_centreline():
    # the sliver's centreline is a quarter thread past the last row: its
    # outer thread edge is further than half a thread from any row
    b = _block(_line(1, 9, 2.1 + 0.25, "Sedge"), _rows(0, 10, 0, 2.1))
    assert _skip_covered_shapes([b], TRIM_AT) == []


def test_another_colour_is_not_cover():
    b0 = _block(_line(1, 9, 1.0, "Ssliver"), _line(20, 30, 1.0, "Sfar"), thread=1)
    b1 = _block(_rows(0, 10, 0, 2), thread=2)
    assert _skip_covered_shapes([b0, b1], TRIM_AT) == []


def test_a_shapes_own_runs_are_not_its_cover():
    # a fill's underlay under its own rows is the shape's, never dropped
    under = StitchRun(points=[(1, 1), (9, 1)], kind=stitches.UNDERLAY, jump=True, trim=True,
                      shape_id="Sfill")
    b = _block(under, _rows(0, 10, 0, 2, jump=False, trim=False))
    assert _skip_covered_shapes([b], TRIM_AT) == []


def test_a_dropped_shapes_cover_is_kept():
    # Sl lies on Se; Se lies under the wider Sm. Sl goes first (judged last
    # first) and pins Se, so Se is not dropped after it: Sl's place stays sewn
    se = _rows(0, 10, 0, 2, shape="Se")
    sl = _line(1, 9, 1.0, "Sl")
    sm = _rows(-1, 11, -0.6, 2.6, shape="Sm")
    b = _block(se, sl, sm)
    assert _skip_covered_shapes([b], TRIM_AT) == ["Sl"]
    assert [r.shape_id for r in b.runs] == ["Se", "Sm"]


def test_two_covered_slivers_in_a_row_both_go_and_the_cover_lifts_once():
    b = _block(_line(1, 4, 1.0, "Sa"), _line(6, 9, 1.5, "Sb"), _rows(0, 10, 0, 2))
    assert sorted(_skip_covered_shapes([b], TRIM_AT)) == ["Sa", "Sb"]
    assert [r.shape_id for r in b.runs] == ["Sfill"]
    assert b.runs[0].jump and b.runs[0].trim


def test_the_run_after_a_dropped_stretch_lifts_from_what_now_precedes_it():
    first = _line(0, 9, 10.0, "Sfirst")
    mid = _line(1, 9, 1.0, "Smid")
    fill = _rows(0, 10, 0, 2, jump=False, trim=False)   # chained on from the sliver
    b = _block(first, mid, fill)
    assert _skip_covered_shapes([b], TRIM_AT) == ["Smid"]
    # Sfirst ends at (9, 10); the fill starts at (0, 0): over trim_at, so a cut
    assert b.runs[1].shape_id == "Sfill" and b.runs[1].jump and b.runs[1].trim
    b = _block(_line(5, -1, -1.5, "Snear"), _line(1, 9, 1.0, "Smid"),
               _rows(0, 10, 0, 2, jump=False, trim=False))
    assert _skip_covered_shapes([b], TRIM_AT) == ["Smid"]
    # Snear ends at (-1, -1.5), outside the rows; the fill starts at (0, 0):
    # 1.8 mm, under trim_at -> a jump, no cut
    assert b.runs[1].shape_id == "Sfill" and b.runs[1].jump and not b.runs[1].trim


def test_tier_runs_and_shapes_in_two_blocks_are_never_dropped():
    cap = _line(1, 9, 1.0, "__edge_cap__")
    split = _line(1, 9, 1.0, "Ssplit")
    b0 = _block(cap, split, _rows(0, 10, 0, 2))
    b1 = _block(_line(20, 30, 1.0, "Ssplit"), thread=2)
    assert _skip_covered_shapes([b0, b1], TRIM_AT) == []


def test_on_a_plan_with_nothing_covered_it_changes_nothing():
    # the panel fixture (the recipe on a synthetic MFab) has no covered shape
    on = _sew(panel(), OUTLINES, silhouette_underfill_panels=True, skip_covered_shapes=True, **ON)[3]
    off = _sew(panel(), OUTLINES, silhouette_underfill_panels=True, **ON)[3]
    assert _md5(on) == _md5(off)
