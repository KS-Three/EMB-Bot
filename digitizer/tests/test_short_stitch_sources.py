"""`tools/short_stitch_sources.py` -- which engine source emits short and stacked stitches.

The tool charges every short or stacked stitch to a source. These tests pin
that on plans small enough to count by hand, so a later edit cannot quietly
move a stitch from one source to another, and pin the two ways the tool could
silently lie: its labels drifting from the bytes the export writes, and its
counts drifting from the census they extend.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from digitizer_core import stitches
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun
from tools import short_stitch_sources as sss
from tools import stitch_difficulty_census as sdc

ROOT = Path(__file__).resolve().parents[1]
BECKER_DST = ROOT / "testdata" / "reference" / "becker_hat_polo_large_beckers_logo_hat.dst"


def _plan(*blocks: list[StitchRun]) -> StitchPlan:
    return StitchPlan(
        blocks=[StitchBlock(thread_index=i, thread_number=str(i), rgb=(0, 0, 0), runs=list(b))
                for i, b in enumerate(blocks)],
        palette=[{} for _ in blocks])


def _line(x0: float, step: float, n: int, y: float = 0.0):
    return [(x0 + i * step, y) for i in range(n)]


def _make_runs() -> list[StitchRun]:
    """Built in a named function so the creator tag has something to say."""
    return [StitchRun(points=_line(0.0, 0.3, 4), kind=stitches.SATIN, shape_id="s"),
            StitchRun(points=_line(20.0, 2.0, 4), kind=stitches.FILL, jump=True, shape_id="f")]


def _by_source(plan):
    stream, prov = sss.attributed_stream(plan)
    return stream, prov, sss.tally(stream, prov)


def test_a_short_stitch_is_charged_to_the_run_that_sewed_it_and_a_long_one_to_nobody():
    plan = _plan(_make_runs())
    _, _, t = _by_source(plan)
    sat = t["by_source"]["satin"]
    assert sat["pens"] == 4 and sat["lt_0p5"] == 3 and sat["0p5_1"] == 0
    fill = t["by_source"]["fill"]
    assert fill["pens"] == 4 and fill["lt_0p5"] == 0 and fill["0p5_1"] == 0


def test_the_creator_is_the_function_that_built_the_run():
    with sss.instrumented():
        plan = _plan(_make_runs())
    _, prov, t = _by_source(plan)
    assert any(c == "test_short_stitch_sources._make_runs" for _, c in filter(None, prov))
    assert "satin @ test_short_stitch_sources._make_runs" in t["by_creator"]


def test_instrumentation_is_undone_on_exit():
    from digitizer_core import stage7_sequence

    init, apply_, s7 = StitchRun.__init__, stitches.apply_ties, stage7_sequence._apply_ties
    with sss.instrumented():
        assert StitchRun.__init__ is not init and stitches.apply_ties is not apply_
    assert StitchRun.__init__ is init
    assert stitches.apply_ties is apply_
    assert stage7_sequence._apply_ties is s7


def test_a_folded_lock_is_its_own_source_not_the_runs_kind():
    with sss.instrumented():
        runs = [StitchRun(points=_line(0.0, 2.0, 5), kind=stitches.FILL, shape_id="f")]
        stitches.apply_ties(runs)
        plan = _plan(runs)
    _, prov, t = _by_source(plan)
    src = [p[0] for p in prov if p]
    # tie_run lays 4 points in front of the run; the lock's last 0.8 mm leg
    # arrives AT the run's first point, which is therefore the lock's too.
    # Behind the run it lays 4 more.
    assert src[:5] == ["tie_in"] * 5 and src[-4:] == ["tie_off"] * 4
    assert set(src[5:-4]) == {"fill"}
    # Each 0.8 mm leg is a 0.5-1 mm stitch; the run's own 2 mm stitches are not.
    assert t["by_source"]["tie_in"]["0p5_1"] == 4 and t["by_source"]["tie_off"]["0p5_1"] == 4
    assert t["by_source"]["fill"]["0p5_1"] == 0


def test_a_lock_applied_twice_is_counted_in_full():
    with sss.instrumented():
        runs = [StitchRun(points=_line(0.0, 2.0, 5), kind=stitches.FILL)]
        stitches.apply_ties(runs)
        stitches.apply_ties(runs)
    assert runs[0]._tie_head == 8 and runs[0]._tie_tail == 8


def test_two_runs_with_no_jump_between_them_are_joined_by_a_run_link():
    a = StitchRun(points=_line(0.0, 2.0, 3), kind=stitches.FILL)
    b = StitchRun(points=_line(4.3, 2.0, 3), kind=stitches.SATIN)       # no jump: a 0.3 mm link
    _, prov, t = _by_source(_plan([a, b]))
    assert [p[0] for p in prov if p] == ["fill"] * 3 + ["run_link"] + ["satin"] * 2
    assert t["by_source"]["run_link"]["lt_0p5"] == 1


def test_a_jump_is_not_a_stitch_so_the_first_point_after_one_is_not_charged():
    a = StitchRun(points=_line(0.0, 2.0, 3), kind=stitches.FILL)
    b = StitchRun(points=_line(30.0, 2.0, 3), kind=stitches.SATIN, jump=True)
    _, prov, t = _by_source(_plan([a, b]))
    assert "run_link" not in {p[0] for p in prov if p}
    assert t["lt_0p5"] == 0 and t["0p5_1"] == 0


def test_role_splits_a_kind_into_its_tier():
    run = StitchRun(points=_line(0.0, 0.8, 5), kind=stitches.RUN, role=stitches.ROLE_EDGE_CAP)
    _, _, t = _by_source(_plan([run]))
    assert t["by_source"]["run/edge_cap"]["0p5_1"] == 4


def test_a_stitch_that_lands_in_the_same_tenth_of_a_mm_is_a_zero_length_stitch():
    # 0.04 mm apart survives the plan's 0.01 mm dedupe, then rounds to one 0.1 mm hole.
    run = StitchRun(points=[(0.0, 0.0), (0.04, 0.0), (3.0, 0.0), (6.0, 0.0)], kind=stitches.FILL)
    _, _, t = _by_source(_plan([run]))
    assert t["zero"] == 1 and t["lt_0p5"] == 1


def test_stacked_penetrations_are_split_by_how_far_back_the_earlier_hole_is():
    # A bean pass: the 4th lands on the 1st (3 back), the 7th on the 4th ...
    bean = [(0, 0), (3, 0), (6, 0), (0.2, 0.1)]
    _, _, t = _by_source(_plan([StitchRun(points=bean, kind=stitches.BEAN)]))
    assert t["near"] == 1 and t["near_g5"] == 1
    # A neighbouring pass: row 2 sits 0.3 mm from row 1, 7 penetrations on.
    rows = ([(i * 3.0, 0.0) for i in range(7)]
            + [(18.0 - i * 3.0, 0.3) for i in range(7)])
    _, _, t2 = _by_source(_plan([StitchRun(points=rows, kind=stitches.FILL)]))
    # The fold-back is close behind at the turn (g5) and further back along the row.
    assert t2["near_g10"] >= 1 and t2["near_g20"] >= 1


def test_short_stitches_are_split_by_what_flanks_them():
    # long, short, long -> iso; a chain of three shorts -> chain; run ends -> edge.
    iso = [(0, 0), (3, 0), (3.3, 0), (6.3, 0), (9.3, 0)]
    _, _, t = _by_source(_plan([StitchRun(points=iso, kind=stitches.FILL)]))
    assert t["short_iso"] == 1 and t["short_chain"] == 0
    chain = _line(0.0, 0.3, 6)
    _, _, t2 = _by_source(_plan([StitchRun(points=chain, kind=stitches.RUN)]))
    assert t2["short_edge"] == 2 and t2["short_chain"] == 3


def test_the_counts_agree_with_the_census_on_a_stream_with_jumps_and_trims():
    plan = _plan([StitchRun(points=_line(0.0, 0.7, 12), kind=stitches.RUN),
                  StitchRun(points=_line(40.0, 2.5, 9), kind=stitches.FILL, jump=True, trim=True),
                  StitchRun(points=[(70, 0), (70.2, 0), (70.1, 0.2), (70.3, 0.1), (75, 0)],
                            kind=stitches.UNDERLAY, jump=True)],
                 [StitchRun(points=_line(0.0, 0.2, 7), kind=stitches.SATIN)])
    stream, prov = sss.attributed_stream(plan)
    t = sss.tally(stream, prov)            # raises if classify and census disagree
    ref = sdc.census(stream)
    assert t["sewn"] == ref["sewn_stitches"]
    assert t["near"] == round(ref["near_hole"] * ref["penetrations"])
    assert t["short"] == t["lt_0p5"] + t["0p5_1"]
    # Per-source rows add up to the design's total.
    for k in ("pens", "lt_0p5", "0p5_1", "near", "union"):
        whole = t["penetrations"] if k == "pens" else t[k]
        assert sum(r[k] for r in t["by_source"].values()) == whole


def test_labels_that_drift_from_the_export_raise(monkeypatch):
    plan = _plan(_make_runs())
    real = sss.attributed_commands
    monkeypatch.setattr(sss, "attributed_commands", lambda p: list(real(p))[:-1])
    with pytest.raises(ValueError):
        sss.attributed_stream(plan)


def test_the_pro_side_counts_a_real_dst_the_same_way_the_census_does():
    row = sss.pro_record("p01", "c01", BECKER_DST)
    ref = sdc.file_row(BECKER_DST)
    assert row["design"] == "p01" and row["cluster"] == "c01"
    assert row["sewn"] == ref["sewn_stitches"]
    assert row["lt_0p5"] / row["sewn"] == pytest.approx(ref["bins"]["lt_0p5"], abs=1e-4)
    assert row["near"] / row["penetrations"] == pytest.approx(ref["near_hole"], abs=1e-4)
    assert row["short"] == row["short_iso"] + row["short_chain"] + row["short_edge"]


def test_pro_files_honours_the_exclude_list(tmp_path):
    for rel in ("Client A/a.dst", "Client B/Test Files/b.dst", "Client B/c.dst", "Client A/notes.txt"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")
    names = [p.name for p in sss.pro_files(tmp_path, ["Test Files"])]
    assert names == ["a.dst", "c.dst"]


def test_bootstrap_ratio_is_the_pooled_ratio_with_an_interval_around_it():
    ours = [(20, 100)] * 6
    pro = [(10, 100), (10, 100), (10, 100), (10, 100)]
    ratio, lo, hi = sss.bootstrap_ratio(ours, pro, draws=500)
    assert ratio == pytest.approx(2.0)
    assert lo == pytest.approx(2.0) and hi == pytest.approx(2.0)      # no spread, no interval
    ours2 = [(10, 100), (30, 100), (20, 100), (40, 100)]
    r2, lo2, hi2 = sss.bootstrap_ratio(ours2, pro, draws=500)
    assert lo2 < r2 < hi2
    assert sss.bootstrap_ratio(ours2, pro, draws=500) == (r2, lo2, hi2)    # seeded, repeatable


def test_resampling_pro_by_customer_is_wider_than_by_design_when_files_are_variants():
    ours = [(20, 100), (22, 100), (18, 100)]
    pro = [(10, 100), (10, 100), (10, 100), (30, 100), (30, 100), (30, 100)]
    groups = ["a", "a", "a", "b", "b", "b"]
    _, lo, hi = sss.bootstrap_ratio(ours, pro, draws=2000)
    _, glo, ghi = sss.bootstrap_ratio(ours, pro, draws=2000, pro_groups=groups)
    assert (ghi - glo) > (hi - lo)


def test_the_report_renders_every_table():
    plan = _plan(_make_runs())
    stream, prov = sss.attributed_stream(plan)
    ours = [{"design": f"d{i}", **sss.tally(stream, prov)} for i in range(3)]
    pro = [{"design": f"p{i}", "cluster": f"c{i % 2}", **sss.tally(stream)} for i in range(4)]
    text = sss.report(ours, pro)
    for head in ("Pooled rate per 1000", "Source-agnostic split", "By source", "Top creators",
                 "Stacked: arrival source"):
        assert head in text
    assert "| satin |" in text


def test_the_tool_is_off_every_path():
    for pkg in ("digitizer_core", "digitizer_service"):
        for py in (ROOT / pkg).rglob("*.py"):
            assert "short_stitch_sources" not in py.read_text(encoding="utf-8"), py
