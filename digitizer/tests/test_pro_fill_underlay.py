"""`tools/pro_fill_underlay.py` — what is sewn under a fill, read off a bare
stitch file.

The instrument the 2026-10-05 underlay audit rests on
(`docs/underlay-audit-2026-10-05.md`). Corpus law 26's instrument "lived in
scratchpad" and was lost, so nobody could say what it had measured when the
commissioned files turned out to disagree with it. This one is kept, with
its ground truth: fills sewn by our own engine at a KNOWN underlay, written
through the `/export` writer and read back as a stream with no tags.

The audit's full matrix was 154 cases; these are the ones that each failed a
version of the classifier, plus the plain styles.
"""
from __future__ import annotations

import io

import pystitch
import pytest
from shapely.geometry import Point, box

from digitizer_core import machine, stage6_fill
from digitizer_core.export import plan_to_pattern
from digitizer_core.stitches import StitchBlock, StitchPlan
from tools import pro_fill_underlay as pfu

SQUARE = box(5, 5, 45, 45)
PLATE = (box(5, 5, 65, 40).difference(Point(22, 22).buffer(6, 32))
         .difference(Point(48, 22).buffer(6, 32)))


def _sew(poly, style, *, angle=0.0, row=None, start=None, **kw):
    runs, _report = stage6_fill.stitch_shape(
        poly, "s", angle_deg=angle, row_mm=row or machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style=style,
        trim_at_mm=machine.TRIM_AT_MM, start_near=start, **kw)
    return runs


def _file(tmp_path, runs, ext="dst"):
    plan = StitchPlan(
        blocks=[StitchBlock(thread_index=0, thread_number="1000",
                            rgb=(30, 80, 200), runs=runs)],
        palette=[{}])
    buf = io.BytesIO()
    {"dst": pystitch.write_dst, "pes": pystitch.write_pes}[ext](plan_to_pattern(plan), buf)
    path = tmp_path / f"case.{ext}"
    path.write_bytes(buf.getvalue())
    return path


def _verdicts(path):
    return [verdict for verdict, _detail in pfu.classify_file(path, min_fill_mm=300.0)]


@pytest.mark.parametrize("ext", ["dst", "pes"])
@pytest.mark.parametrize("poly", [SQUARE, PLATE], ids=["square", "plate_two_holes"])
@pytest.mark.parametrize("style,expected", [
    ("none", "BARE"),
    ("edge_run", "RUNONLY"),
    ("zigzag", "CROSS"),
    ("edge_lattice", "CROSS"),
    ("double_lattice", "DIAG"),
])
def test_each_engine_style_is_read_for_what_it_is(tmp_path, poly, style, expected, ext):
    assert _verdicts(_file(tmp_path, _sew(poly, style), ext)) == [expected]


def test_an_edge_run_is_reported_beside_the_pass(tmp_path):
    (_v, with_edge), = pfu.classify_file(
        _file(tmp_path, _sew(SQUARE, "edge_lattice")), min_fill_mm=300.0)
    (_v, without), = pfu.classify_file(
        _file(tmp_path, _sew(SQUARE, "zigzag")), min_fill_mm=300.0)
    assert with_edge["edge"] is True
    assert without["edge"] is False


@pytest.mark.parametrize("row,stitch", [(1.0, 4.0), (0.75, 4.0), (1.5, 3.0)])
def test_a_pass_at_the_professionals_constants_is_found_and_measured(
        tmp_path, monkeypatch, row, stitch):
    """0.75 mm is the one that matters: the research note's 0.9 mm "sparse"
    bar sat on the professional's 0.94-1.00 mm pitch and dropped about half
    his rows. The bar is 0.7 here."""
    monkeypatch.setattr(machine, "UNDERLAY_ZIGZAG_MM", row)
    monkeypatch.setattr(machine, "UNDERLAY_STITCH_MM", stitch)
    (verdict, d), = pfu.classify_file(
        _file(tmp_path, _sew(SQUARE, "zigzag", angle=20.0, row=0.18)),
        min_fill_mm=300.0)
    assert verdict == "CROSS"
    assert d["sparse_pitch"] == pytest.approx(row, abs=0.05)
    assert d["sparse_stitch"] == pytest.approx(stitch, abs=0.1)
    assert d["angle_vs_top"] == pytest.approx(90.0, abs=2.0)


# --- What must NOT read as a crossing underlay pass ---------------------------

def test_a_two_pass_density_boost_is_not_an_underlay(tmp_path):
    runs = _sew(SQUARE, "none", density_boost=True)
    assert "CROSS" not in _verdicts(_file(tmp_path, runs))


def test_a_crosshatch_top_is_not_an_underlay(tmp_path):
    runs = _sew(SQUARE, "none", technique="crosshatch")
    assert "CROSS" not in _verdicts(_file(tmp_path, runs))


def test_two_top_passes_at_different_angles_are_not_an_underlay(tmp_path):
    first = _sew(SQUARE, "none", angle=0.0, row=0.36)
    second = _sew(SQUARE, "none", angle=60.0, row=0.36,
                  start=first[-1].points[-1])
    assert "CROSS" not in _verdicts(_file(tmp_path, first + second))


def test_a_sparse_pass_sewn_after_the_fill_is_not_under_it(tmp_path):
    fill = _sew(SQUARE, "none", angle=0.0)
    overlay = _sew(SQUARE, "none", angle=90.0, row=1.2,
                   start=fill[-1].points[-1])
    assert _verdicts(_file(tmp_path, fill + overlay)) == ["BARE"]


def test_a_light_layer_alone_is_not_a_fill(tmp_path):
    """A 1.0 mm crosshatch with no dense fill over it: nothing to be under."""
    runs = _sew(SQUARE, "none", technique="crosshatch", row=0.5)
    assert _verdicts(_file(tmp_path, runs)) == []


def test_two_fills_in_one_colour_block_are_judged_apart(tmp_path):
    bare = _sew(SQUARE, "none")
    laid = _sew(box(60, 5, 100, 45), "edge_lattice",
                start=bare[-1].points[-1])
    laid[0].jump = True
    laid[0].trim = True
    assert sorted(_verdicts(_file(tmp_path, bare + laid))) == ["BARE", "CROSS"]


def test_the_tracked_becker_files_read_as_the_audit_found():
    """The audit's own row: 10 large fills in the five tracked DSTs, every
    one with a crossing pass at the professional's pitch, stitch and share."""
    from pathlib import Path

    ref = Path(__file__).resolve().parent.parent / "testdata" / "reference"
    fills = [fill for path in sorted(ref.glob("becker_*.dst"))
             for fill in pfu.classify_file(path)]
    assert len(fills) == 10
    for verdict, d in fills:
        assert verdict == "CROSS"
        assert 0.90 <= d["sparse_pitch"] <= 1.00
        assert d["sparse_stitch"] == pytest.approx(3.99, abs=0.05)
        assert d["angle_vs_top"] >= 88.0
        assert 15.0 <= d["share"] <= 17.5
