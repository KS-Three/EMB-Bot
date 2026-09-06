"""`cfg.satin_patch_junctions` — sew what the satin tier missed. DEFAULT OFF.

Crosses are placed along a spine, perpendicular to one arm, sized by a ray
that measures THAT arm's width. Where several arms meet, each ray reads its
own arm's ~2 mm rather than the junction's 5+ mm, so the interior is covered
only by whatever overlap the arms happen to have — and on a five-arm junction
it does not close. Measured 2026-09-06: the K's crotch in
`becker_marine_logo` is bare, 37.2 mm2 at 80 mm, and it is the whole reason
that fixture grades B 76 instead of A 100.

Four cross-LENGTH knobs were measured against that hole and none reached it,
because none of them changes where a cross is PLACED (DOCTRINE 2026-09-06).
So this flag does not adjust a cross: it rasterizes the thread actually
emitted, finds the artwork that thread missed, and sews the patches as
tatami.

What these tests exist to guarantee: OFF changes nothing at all, ON actually
clears the grader's finding, and a patch never sews outside the artwork.
"""
from __future__ import annotations

from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.pipeline import digitize
from digitizer_core.preflight import run_preflight
from digitizer_core.stage6_satin import _uncovered_patches, satin_shape
from tests.conftest import TESTDATA

BECKER = TESTDATA / "becker_marine_logo.png"


def _points(plan) -> list:
    return [tuple(map(tuple, r.points)) for _b, r in plan.iter_runs()]


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


def test_the_flag_is_off_by_default():
    """It puts tatami sheen inside a satin letter, which is a look question a
    render answers and a number does not. The default lives here so a change
    to it is a visible diff rather than a quiet one."""
    assert PipelineConfig().satin_patch_junctions is False


def test_off_is_byte_identical_on_the_fixture_the_flag_moves():
    """On the ONE fixture where the flag is known to change the sewn result —
    a byte test on a fixture it cannot move would prove nothing."""
    _r1, p1 = digitize(BECKER, _cfg())
    _r2, p2 = digitize(BECKER, _cfg(satin_patch_junctions=False))
    assert _points(p1) == _points(p2), \
        "the default and an explicit False must be the same plan"


def test_on_clears_the_graders_finding_rather_than_merely_moving_a_number():
    """Proven on the emitted stitches through the grader that reported the
    defect, not on the patch geometry this module computed for itself.

    Measured 2026-09-06 at 80 mm: `ARTWORK_UNCOVERED` 23.8 -> 0.0 mm2,
    B 76 -> B 88, for +383 stitches (~7%). At 90 mm, 44.5 -> 0.0.
    """
    r_off, p_off = digitize(BECKER, _cfg())
    rep_off = run_preflight(r_off, p_off, _cfg(), image=BECKER)
    on = _cfg(satin_patch_junctions=True)
    r_on, p_on = digitize(BECKER, on)
    rep_on = run_preflight(r_on, p_on, on, image=BECKER)

    codes_off = {f["code"] for f in rep_off["findings"]}
    codes_on = {f["code"] for f in rep_on["findings"]}
    assert "ARTWORK_UNCOVERED" in codes_off, \
        "the fixture stopped exhibiting the defect these tests are about"
    assert "ARTWORK_UNCOVERED" not in codes_on
    assert rep_on["metrics"]["uncovered_total_mm2"] == 0.0
    assert rep_on["score"] > rep_off["score"]
    # It must cost SOMETHING — a patch that adds no thread covered nothing.
    assert p_on.stats.stitch_count > p_off.stats.stitch_count


def test_the_patch_sews_under_the_shapes_own_id():
    """Or preflight attributes the fix somewhere other than where it reported
    the defect, and `_owning_region_id` never links the two. The patch is FILL
    inside a shape whose other runs are SATIN, which is how it is recognised.
    """
    _r, plan = digitize(BECKER, _cfg(satin_patch_junctions=True))
    kinds: dict[str, set] = {}
    for _b, run in plan.iter_runs():
        if run.shape_id:
            kinds.setdefault(run.shape_id, set()).add(run.kind)
    patched = [s for s, k in kinds.items()
               if stitches.SATIN in k and stitches.FILL in k]
    assert patched, "no shape carries both satin and a patch fill"


def test_a_patch_never_sews_outside_the_artwork():
    """The patch is GROWN before sewing so its rows overlap the columns around
    it rather than butting against them; that growth is clipped to the
    polygon, and this is what pins the clip.
    """
    result, plan = digitize(BECKER, _cfg(satin_patch_junctions=True))
    by_id = {r.shape_id: r.polygon for r in result.regions}
    checked = 0
    for _b, run in plan.iter_runs():
        if run.kind != stitches.FILL or run.shape_id not in by_id:
            continue
        # A thread's own width of slack, and no more: the patch is clipped to
        # the polygon, but a stitch lands ON that boundary by construction.
        allowed = by_id[run.shape_id].buffer(machine.COVERAGE_THREAD_W_MM)
        outside = [p for p in run.points if not allowed.covers(Point(p))]
        assert not outside, \
            f"{run.shape_id} sews {len(outside)} patch stitches outside its artwork"
        checked += len(run.points)
    assert checked, "no patch runs to check — the flag stopped reaching them"


def test_a_fully_covered_shape_gets_no_patch():
    """The finder must answer "nothing" rather than "a sliver everywhere" on a
    shape the columns already cover — otherwise every satin shape in every
    design pays for a patch pass.
    """
    bar = Polygon([(0, 0), (24, 0), (24, 3), (0, 3)])
    runs, _report = satin_shape(bar, "Sbar", underlay_style="none",
                                trim_at_mm=machine.TRIM_AT_MM)
    assert runs, "the fixture stopped sewing as satin"
    assert _uncovered_patches(bar, runs) == []


def test_both_call_sites_forward_the_flag():
    """`satin_shape` has two callers and a flag wired to one of them is a flag
    that silently does nothing on the other route. Read off the source: a
    keyword this specific cannot appear by accident, and asserting on the
    behaviour of the applique route would need an applique fixture.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "digitizer_core"
    for name in ("stage7_sequence.py", "stage6_applique.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert "patch_junctions=cfg.satin_patch_junctions" in src, \
            f"{name} does not forward cfg.satin_patch_junctions"


def test_a_design_with_no_hole_pays_nothing_for_the_flag():
    """The claim the corpus sweep licenses, pinned rather than asserted in
    prose: 2 of 255 satin shapes leave any bare cloth, so on the other 253
    the pass must find nothing and add nothing.

    `logo_alpha` is one of them — A 100 with 0.0 uncovered at 80/85/90/95/100
    mm. Byte-identity here is the real test of the 5.0 mm2 floor: this pass
    uses a STRICTER coverage test than preflight (no erosion, a finer cell),
    so a floor set too low would find slivers in every clean design and
    charge every one of them for a patch nobody grades.
    """
    art = TESTDATA / "logo_alpha.png"
    _r1, p1 = digitize(art, _cfg())
    _r2, p2 = digitize(art, _cfg(satin_patch_junctions=True))
    assert _points(p1) == _points(p2), \
        "the patch pass changed a design that has no hole to patch"
