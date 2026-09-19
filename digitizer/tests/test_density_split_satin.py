"""`DENSITY_EXTREME`'s satin reading on a SPLIT satin column (2026-09-19).

`_satin_rail_advance_mm` reads the rail pitch as the distance between
points two apart — rails alternate A, B, A, B. A split satin column carries
extra penetrations along each cross, so with them in the list two apart is
a mid-cross hop: the lettering plan's 127 mm fixture under
`satin_lettering_split` read 1.09 mm against the 0.40 mm target and raised
`DENSITY_EXTREME` on columns sewn at 0.43. The reader now strips the splits
(`stage6_satin.strip_splits`, the same reader the coverage map uses) before
measuring; an unsplit run is unchanged.
"""
from __future__ import annotations

from digitizer_core import PipelineConfig, stitches
from digitizer_core.pipeline import (build_generation, finish_generation,
                                     plan_stitches)
from digitizer_core.preflight import (DENSITY_EXTREME, _satin_rail_advance_mm,
                                      run_preflight)

from .test_lettering_split import FIXTURE


def _zigzag(n: int, pitch: float, width: float, splits: int):
    """A satin column as the emitter lays it: rail penetrations alternate
    A, B, A, B across `width` and each advances half a `pitch` along y, so
    two apart is one rail pitch; `splits` extra penetrations are lerped
    along every cross, the way `_split_points` places them."""
    rails = [((0.0 if k % 2 == 0 else width), k * pitch / 2.0) for k in range(n)]
    pts = []
    for a, b in zip(rails, rails[1:]):
        pts.append(a)
        for k in range(1, splits + 1):
            t = k / (splits + 1)
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    pts.append(rails[-1])
    return pts


def _plan(points):
    run = stitches.StitchRun(points=points, kind=stitches.SATIN, shape_id="S")
    block = stitches.StitchBlock(thread_index=0, thread_number="1234", rgb=(0, 0, 0), runs=[run])
    return stitches.StitchPlan(blocks=[block], palette=[{"number": "1234", "name": "T"}])


def test_a_split_column_reads_its_rail_pitch_not_its_split_length():
    """Six millimetres across, split twice per cross, 0.4 mm pitch: the
    reader says 0.4, not the 2 mm hop between split penetrations."""
    plan = _plan(_zigzag(120, 0.4, 6.0, splits=2))
    assert abs(_satin_rail_advance_mm(plan) - 0.4) < 1e-6


def test_an_unsplit_column_is_unchanged():
    plan = _plan(_zigzag(120, 0.4, 3.0, splits=0))
    assert abs(_satin_rail_advance_mm(plan) - 0.4) < 1e-6


def test_the_split_lettering_fixture_raises_no_density_finding():
    """The finding this fix is for: MARINE traced at 127 mm under
    `satin_lettering_split` sews its letters as split satin at a 0.43 mm
    rail pitch and used to read 1.09."""
    cfg = PipelineConfig(target_width_mm=127.4, garment_id="left_chest",
                         max_colors=6, satin_lettering_split=True)
    gen = build_generation(str(FIXTURE), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    adv = _satin_rail_advance_mm(plan)
    assert adv is not None and adv < 0.6, adv
    pf = run_preflight(result, plan, cfg, image=str(FIXTURE))
    satin_density = [f for f in pf["findings"]
                     if f["code"] == DENSITY_EXTREME and f.get("extra", f).get("kind") == "satin"]
    assert not satin_density, satin_density
