"""`cfg.satin_per_stroke` — PR 3 of the per-stroke satin plan, DEFAULT OFF.

`classify_ribbon` pools the distance transform over a whole region's skeleton,
so a branchy letterform fails `2 sigma < mu` as a unit even when every arm of
it is a clean ribbon. On this flag a region the pooled gate refused is taken
when enough of its stroke-partitioned area passes both gates PER STROKE.

Two things these tests exist to guarantee: OFF changes nothing at all, and ON
can only ever ADD satin — never take it away, and never past the machine cap
or Law 31's width floor.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize
from digitizer_core.stage6_satin import classify_ribbon, is_satin_candidate
from tests.conftest import TESTDATA

BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])


def _points(plan) -> list:
    return [tuple(map(tuple, r.points)) for _b, r in plan.iter_runs()]


def test_the_flag_is_off_by_default():
    """ROADMAP gate 3 — a default-OFF tier is not flipped on without Kent, and
    the flip for this one wants a render first. The default lives here so a
    change to it is a visible diff rather than a quiet one."""
    assert PipelineConfig().satin_per_stroke is False


def test_off_is_byte_identical_on_a_fixture_the_flag_moves():
    """The invariant the plan (§4) names first, on the ONE fixture where the
    flag is known to change the sewn result — `becker_marine_logo` at 100 mm,
    where it takes the crossing share 2.2% -> 35.0%. A byte test on a fixture
    the flag cannot move would prove nothing.
    """
    art = TESTDATA / "becker_marine_logo.png"
    base = PipelineConfig(target_width_mm=100.0, garment_id="left_chest")
    _r1, p1 = digitize(art, base)
    _r2, p2 = digitize(art, PipelineConfig(target_width_mm=100.0,
                                           garment_id="left_chest",
                                           satin_per_stroke=False))
    assert _points(p1) == _points(p2), \
        "the default and an explicit False must be the same plan"


def test_on_moves_the_sewn_result_where_the_measurement_said_it_would():
    """Not a tautology: this pins that the flag reaches the STITCHES, which is
    this repo's rule (`tools/sewn_compensation.py`, `tools/satin_columns.py` —
    prove it on the stitches, never on the plan).

    Measured 2026-09-06 at 100 mm: four shapes go fill -> satin and the design
    sheds a quarter of its stitches, because a satin column covers the same
    ribbon far more cheaply than fill rows do.
    """
    art = TESTDATA / "becker_marine_logo.png"
    kw = dict(target_width_mm=100.0, garment_id="left_chest")
    _off_r, off = digitize(art, PipelineConfig(**kw))
    _on_r, on = digitize(art, PipelineConfig(**kw, satin_per_stroke=True))

    def kinds(plan):
        out: dict[str, set] = {}
        for _b, run in plan.iter_runs():
            if run.shape_id:
                out.setdefault(run.shape_id, set()).add(str(run.kind))
        return out

    k_off, k_on = kinds(off), kinds(on)
    gained = [s for s in k_on
              if "satin" in k_on[s] and "satin" not in k_off.get(s, set())]
    lost = [s for s in k_off
            if "satin" in k_off[s] and "satin" not in k_on.get(s, set())]
    assert gained, "the flag must reach the emitted stitches"
    assert not lost, f"promotion-only: no shape may LOSE satin, got {lost}"

    # PENETRATIONS, not runs. The flag ADDS runs (a promoted region gains its
    # own underlay) while removing stitches, so counting runs measures the
    # opposite of the claim: 145 -> 147 runs against 11,374 -> 11,206 stitches.
    def stitches(plan):
        return sum(len(r.points) for _b, r in plan.iter_runs())

    assert stitches(on) < stitches(off), (
        f"satin covers a ribbon more cheaply than fill rows do: "
        f"{stitches(off):,} -> {stitches(on):,}")


def test_on_never_takes_satin_away_from_a_shape_that_had_it():
    """Promotion-only, at the unit. DOCTRINE records what a replacement costs:
    15 regions demoted across the corpus, one of them 638.8 mm2, most of them
    `promoted_ribbon` shapes the `explained` path had deliberately rescued.
    The rung sits on the `dt_irregular` branch alone so it cannot reach them.
    """
    for design_class in ("flat", "gradient", "photo_scene"):
        for poly in (BAR, Polygon([(0, 0), (40, 0), (40, 8), (0, 8)])):
            off = classify_ribbon(poly, machine.SATIN_MAX_WIDTH_MM,
                                  design_class=design_class)
            on = classify_ribbon(poly, machine.SATIN_MAX_WIDTH_MM,
                                 design_class=design_class, per_stroke=True)
            if off.satin:
                assert on.satin, (
                    f"{design_class}: the rung took satin away "
                    f"({off.reason} -> {on.reason})")


def test_the_rung_cannot_reach_a_shape_the_machine_cap_refused():
    """`dt_p90_cap` stays out of the rung's reach on purpose. DOCTRINE's
    measured negative: a stroke wider than the cap sewn anyway gets capped
    crosses from `_rail_points`' per-station guard and leaves bare cloth down
    the middle of it.
    """
    too_wide = Polygon([(0, 0), (60, 0), (60, 9), (0, 9)])
    off = classify_ribbon(too_wide, machine.SATIN_MAX_WIDTH_MM)
    on = classify_ribbon(too_wide, machine.SATIN_MAX_WIDTH_MM, per_stroke=True)
    assert not off.satin and not on.satin, \
        f"a 9 mm bar is past the 5 mm cap either way: {off.reason} / {on.reason}"
    assert on.reason in ("width_cap", "dt_p90_cap"), on.reason


def test_the_cap_is_a_veto_not_a_vote_and_leaves_no_bare_cloth():
    """The correction the RENDER forced, 2026-09-06.

    Scoring the machine cap per stroke and then letting an area majority
    outvote it is NOT the same rule as refusing an over-cap stroke, and the
    difference is bare cloth. Measured on `becker_marine_logo` at 100 mm with
    the cap as a mere vote: `S92a90056` (1,022 mm2) passed at frac 0.79 while
    carrying 97.5 mm2 of over-cap strokes, one of them **9.32 mm against the
    5.0 mm cap**. `_rail_points`' per-station guard holds every cross to the
    cap, so the middle of that stroke got no thread — preflight's
    `uncovered_total_mm2` went 0.0 -> 28.0 with a 22.2 mm2 worst patch and
    ARTWORK_UNCOVERED appeared. DOCTRINE had already recorded that shape of
    failure as a measured negative.

    So the flag must not open a coverage hole the flag-off plan does not have.
    This is the guard, stated as the property that matters rather than as the
    implementation: turning it on may not make coverage worse.
    """
    from digitizer_core.pipeline import plan_stitches, run_stages
    from digitizer_core.preflight import run_preflight

    art = TESTDATA / "becker_marine_logo.png"
    got = {}
    for on in (False, True):
        cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest",
                             satin_per_stroke=on)
        result = run_stages(str(art), cfg)
        plan = plan_stitches(result, cfg)
        m = run_preflight(result, plan, cfg, image=str(art))["metrics"]
        got[on] = (m["uncovered_total_mm2"], m["uncovered_worst_mm2"])

    off_total, off_worst = got[False]
    on_total, on_worst = got[True]
    assert on_total <= off_total + 1e-9, (
        f"the flag left {on_total:.1f} mm2 of artwork bare against "
        f"{off_total:.1f} with it off — an over-cap stroke is sewing as satin")
    assert on_worst <= max(off_worst, 1.0) + 1e-9, \
        f"worst bare patch grew {off_worst:.1f} -> {on_worst:.1f} mm2"


def test_a_region_holding_an_over_cap_stroke_is_refused_outright():
    """The veto at the unit: one stroke past the cap refuses the whole region,
    however much of its area passes. `dt_irregular` strokes stay outvotable by
    area — pooled irregularity is the artifact the rung exists to correct —
    but a stroke wider than the needle can hold is not an artifact.
    """
    from digitizer_core.stage6_satin import _stroke_rung_takes, classify_strokes

    # A T: a long thin stem (well inside the cap) meeting a UNIFORM fat bar
    # (well past it). Two things this fixture has to get right, both learned
    # by probing rather than guessing:
    #
    #   * the arms must meet at a JUNCTION, not end to end — butting a wide
    #     bar onto a thin one gives ONE stroke whose radii run 1.25 to 4.5, so
    #     it reads `dt_irregular` (outvotable) instead of `dt_p90_cap`;
    #   * the thin arm must carry most of the AREA, or the fraction refuses
    #     the region on its own and the veto is never exercised.
    #
    # Measured: frac 0.81, so the area vote WOULD take it, and one stroke at
    # p90 9.10 mm against the 5.0 mm cap.
    bar = Polygon([(0, 0), (30, 0), (30, 9), (0, 9)])
    stem = Polygon([(13.75, 9), (16.25, 9), (16.25, 409), (13.75, 409)])
    shape = bar.union(stem)
    v = classify_strokes(shape, machine.SATIN_MAX_WIDTH_MM)
    capped = [s for s in v.strokes if s.reason == "dt_p90_cap"]
    assert capped, (
        "fixture must contain an over-cap stroke: "
        f"{[(s.reason, round(s.stats.p90_mm, 2) if s.stats else 0) for s in v.strokes]}")
    assert v.passing_frac >= 0.75, (
        f"fixture must PASS the area vote so the veto is what refuses it, "
        f"got {v.passing_frac:.2f}")
    assert not _stroke_rung_takes(shape, machine.SATIN_MAX_WIDTH_MM, "flat"), \
        f"one over-cap stroke must veto the region (frac was {v.passing_frac:.2f})"


def test_is_satin_candidate_forwards_the_flag():
    """The three call sites (`stage5_overlap._comp_axis`,
    `stage7_sequence._sews_satin`, and `stitch_one`'s ladder) must all be able
    to reach the same verdict, or compensation and routing disagree about
    which shapes are satin — the exact failure `_comp_axis`' docstring warns
    about.
    """
    art = TESTDATA / "becker_marine_logo.png"
    result, _plan = digitize(art, PipelineConfig(target_width_mm=100.0,
                                                 garment_id="left_chest"))
    smax = machine.SATIN_MAX_WIDTH_MM
    moved = [r.shape_id for r in result.regions
             if is_satin_candidate(r.polygon, smax)
             != is_satin_candidate(r.polygon, smax, per_stroke=True)]
    assert moved, "this fixture is chosen because the flag moves verdicts on it"
    for r in result.regions:
        if r.shape_id in moved:
            assert is_satin_candidate(r.polygon, smax, per_stroke=True), \
                "every moved verdict must be a PROMOTION"
