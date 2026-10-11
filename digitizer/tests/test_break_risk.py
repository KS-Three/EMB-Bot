"""The thread-break findings say so, and name a shape the Studio can show.

Three checks already measure what breaks thread -- `STITCHES_TOO_SHORT`,
`DENSITY_STACKED`, `SAME_HOLE_HEAVY` -- and each reached the review step as
one more sentence in a flat list. Two of them located themselves only as a
plan-mm coordinate, which nothing in the Studio can draw: the canvas
highlights a SHAPE (`EmbroideryField`'s `focusShape`), not a point.

So `run_preflight` now tags those findings `extra.break_risk` and gives each
an `extra.show_shape_ids` list, worst first, in the ids the Studio already
holds. No threshold moved and no finding was added: this is the same three
verdicts, grouped and pointable.

**What is deliberately NOT here: a "stitches under 0.5 mm" finding.** Measured
2026-10-01 on `logo_whitebg` at 80 mm, a fixture with ZERO findings: 573 of
its 4,129 fill steps are under `TINY_STITCH_MM`, because a fill's row advance
IS its row pitch and that was ruled to the professional's 0.15 mm on
2026-09-03. A warning at 0.5 mm would fire on every filled design ever
scored. The count rides out as a metric (`tiny_steps`,
`tiny_step_fraction`) and judges nothing.

Synthetic plans only -- no pipeline, no corpus.
"""

from digitizer_core import machine, preflight as pf
from digitizer_core import stitches as st
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

from .conftest import cfg


def _plan(*runs: StitchRun) -> StitchPlan:
    block = StitchBlock(thread_index=0, thread_number="1704",
                        rgb=(230, 60, 60), runs=list(runs))
    return StitchPlan(blocks=[block], palette=[])


def _column(crosses: int, width_mm: float, shape_id: str,
            x0: float = 0.0, spacing_mm: float = 0.4) -> StitchRun:
    pts = []
    for i in range(crosses):
        pts.append((x0 + i * spacing_mm, 0.0))
        pts.append((x0 + i * spacing_mm, width_mm))
    return StitchRun(points=pts, kind=st.SATIN, shape_id=shape_id)


def _square_fill(side_mm: float, cx: float, cy: float, shape_id: str) -> StitchRun:
    pts: list[tuple[float, float]] = []
    row, y = 0, cy - side_mm / 2
    while y <= cy + side_mm / 2:
        xs = [cx - side_mm / 2 + 2.0 * i for i in range(int(side_mm / 2.0) + 1)]
        if row % 2:
            xs.reverse()
        pts.extend((x, y) for x in xs)
        row += 1
        y += machine.FILL_ROW_MM
    return StitchRun(points=pts, kind=st.FILL, shape_id=shape_id)


def _pitted(shape_id: str, at=(50.0, 50.0), n: int = 40) -> StitchRun:
    """A line sewn out and back over its own holes, with one spot struck more.

    The rate counts repeat POINTS, so one deep pit alone never trips it; the
    retrace does, and the extra strikes make `at` the deepest.
    """
    line = [(at[0] + 2.0 * i, at[1]) for i in range(n)]
    pts = line + line[::-1]
    for _ in range(4):
        pts += [(at[0] + 2.0, at[1]), at]
    return StitchRun(points=pts, kind=st.RUN, shape_id=shape_id)


def _hit(report: dict, code: str) -> dict | None:
    for f in report["findings"]:
        if f["code"] == code:
            return f
    return None


def test_short_satin_is_a_break_risk_showing_its_carriers_worst_first():
    plan = _plan(_column(60, 0.6, "Sbad", x0=0.0),
                 _column(20, 0.6, "Slesser", x0=40.0),
                 _column(20, 3.0, "Sfine", x0=80.0))
    f = _hit(pf.run_preflight(None, plan, cfg()), pf.STITCHES_TOO_SHORT)
    assert f is not None
    assert f["extra"]["break_risk"] is True
    assert f["extra"]["show_shape_ids"][:2] == ["Sbad", "Slesser"]
    assert "Sfine" not in f["extra"]["show_shape_ids"]


def test_a_stack_shows_the_shapes_piled_at_its_worst_patch_and_no_others():
    stack = [_square_fill(14.0, 30.0, 30.0, f"Fstack{i}") for i in range(4)]
    plan = _plan(*stack, _square_fill(14.0, 90.0, 30.0, "Ffar"))
    f = _hit(pf.run_preflight(None, plan, cfg()), pf.DENSITY_STACKED)
    assert f is not None
    assert f["extra"]["break_risk"] is True
    shown = f["extra"]["show_shape_ids"]
    assert shown and set(shown) <= {f"Fstack{i}" for i in range(4)}
    assert "Ffar" not in shown


def test_a_same_hole_pit_shows_the_shape_that_strikes_it():
    far = StitchRun(points=[(2.0 * i, 5.0) for i in range(10)],
                    kind=st.RUN, shape_id="Sfar")
    plan = _plan(_pitted("Spit"), far)
    f = _hit(pf.run_preflight(None, plan, cfg()), pf.SAME_HOLE_HEAVY)
    assert f is not None
    assert f["extra"]["worst_at_mm"][1] == 50.0        # on Spit's line, not Sfar's
    assert f["extra"]["break_risk"] is True
    assert f["extra"]["show_shape_ids"] == ["Spit"]


def test_a_shade_band_is_shown_as_the_region_the_studio_knows():
    """A blend run's id is `<region>-blend<i>`; the canvas holds the region."""
    ids = pf._show_ids(["S1-blend0", "S1-blend1", "S2", "", "Sgone-blend0"],
                       {"S1", "S2"})
    assert ids == ["S1", "S2"]


def test_without_regions_the_ids_pass_through_deduped():
    assert pf._show_ids(["Sa", "Sa", "", "Sb"], None) == ["Sa", "Sb"]


def test_other_findings_are_not_break_risks():
    """Trims cost machine time and tails to clip. They do not break thread."""
    runs = []
    for i in range(12):
        r = _column(6, 3.0, f"S{i}", x0=i * 20.0)
        r.jump = r.trim = i > 0
        runs.append(r)
    report = pf.run_preflight(None, _plan(*runs), cfg())
    f = _hit(report, pf.TRIM_HEAVY)
    assert f is not None
    assert "break_risk" not in f.get("extra", {})


def test_tiny_steps_are_counted_and_never_judged():
    """A clean fill is full of sub-0.5 mm steps: its row advance is 0.15 mm."""
    plan = _plan(_square_fill(14.0, 30.0, 30.0, "Fclean"))
    report = pf.run_preflight(None, plan, cfg())
    assert report["findings"] == []
    assert report["metrics"]["tiny_steps"] > 0
    assert 0.0 < report["metrics"]["tiny_step_fraction"] < 1.0
