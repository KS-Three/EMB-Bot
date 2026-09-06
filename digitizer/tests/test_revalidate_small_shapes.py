"""`cfg.revalidate_small_shapes` — let stage 4's re-ask reach the shapes
preflight condemns.

The defect (measured 2026-09-06, MASTER_SCOPE 28, `tools/revalidate_floor.py`):
`stage4_vectorize.THREAD_REVALIDATE_MIN_PX` is 200 and
`preflight._MIN_COLOR_PIXELS` is 50, so every shape of 50-199 px can be scored
and BLOCKED by preflight and never corrected by stage 4. On
`screenshot_phone_ui_golke` that band holds the design's worst thread finding:
`S43831dcd`, 177 px, `0111 Whale` at 32.7 dE00 where `0015 White` scores 1.4.

What these tests pin, in the order that matters:

1.  **The coupling.** `THREAD_REVALIDATE_MIN_PX_SMALL` must equal preflight's
    own floor. The whole argument for the flag is that the two instruments
    should agree on what is measurable; if someone tunes one, this fails.
2.  **Byte-identity OFF.** The flag defaults False and the shipped geometry is
    unchanged — the same contract every flag in this repo carries, and the
    reason this is a flag and not a lowered constant.
3.  **It actually fires**, and on the shape the measurement named.
4.  **The improvement gate still governs.** Lowering the pixel floor must not
    lower the 3.0 dE00 bar — that is the churn guard, and it is the one doing
    the real work.
"""

import hashlib

import pytest

from digitizer_core import preflight, run_stages
from digitizer_core.config import PipelineConfig
from digitizer_core.stage4_vectorize import (
    THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00,
    THREAD_REVALIDATE_MIN_PX,
    THREAD_REVALIDATE_MIN_PX_SMALL,
)
from digitizer_core.pipeline import plan_stitches
from digitizer_core.warnings_codes import THREAD_RESNAPPED_AFTER_DRIFT

from .conftest import TESTDATA

# The fixture the defect was traced on. Its worst thread finding is a 177-px
# shape — inside the band, and the largest single dE00 the corpus offers.
FIXTURE = "photo/screenshot_phone_ui_golke.jpg"

# Named because the assertions below are about THIS shape, not "some shape":
# 0.94 mm2, 177 px, artwork (252,252,252), wearing 0111 Whale.
DRIFTED = "S43831dcd"


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, **kw)


def _digest(fixture: str, **kw) -> tuple[str, int]:
    """A stitch-level fingerprint. The cardinal repo rule is prove it on the
    emitted stitches, so byte-identity is asserted there and not on the plan."""
    result = run_stages(TESTDATA / fixture, _cfg(**kw))
    plan = plan_stitches(result, _cfg(**kw))
    coords = [
        (round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
        for _b, run in plan.iter_runs()
        for x, y in run.points
    ]
    h = hashlib.sha256(repr(coords).encode()).hexdigest()[:20]
    return h, len(coords)


def _resnap_warning(result):
    return next((w for w in result.warnings
                 if w["code"] == THREAD_RESNAPPED_AFTER_DRIFT), None)


def test_small_floor_is_preflights_floor():
    """The coupling is the argument. Quoted, not imported — preflight imports
    the pipeline, and stage 4 is upstream of it — so it needs a test."""
    assert THREAD_REVALIDATE_MIN_PX_SMALL == preflight._MIN_COLOR_PIXELS
    assert THREAD_REVALIDATE_MIN_PX_SMALL < THREAD_REVALIDATE_MIN_PX


def test_the_gap_between_the_two_floors_is_the_defect():
    """Documents the band in a form that fails if either number moves toward
    the other by accident — the defect is that they are 4x apart, and a future
    reader should be told by a test, not only by a comment."""
    assert THREAD_REVALIDATE_MIN_PX > preflight._MIN_COLOR_PIXELS, (
        "if stage 4's floor ever drops to preflight's, this flag is redundant "
        "and MASTER_SCOPE 28 should be closed rather than this test loosened"
    )


def test_flag_defaults_off():
    assert PipelineConfig().revalidate_small_shapes is False


def test_off_is_byte_identical_to_the_shipped_engine():
    """The contract every flag here carries. Explicit False against the
    default, so a change to the default is caught as a difference rather than
    silently agreeing with itself."""
    assert _digest(FIXTURE) == _digest(FIXTURE, revalidate_small_shapes=False)


@pytest.mark.parametrize("fixture", [
    FIXTURE,
    "photo/logo_bridge_bar.jpg",   # 63 refusals — the other cause-3 fixture
    "logo_alpha.png",              # flat lane: nothing to re-ask, a control
])
def test_on_never_changes_a_shape_id_or_its_geometry(fixture):
    """Threads only, never geometry — the invariant `revalidate_threads`'
    docstring states (*"the polygon that came out of simplification is the one
    that sews well"*). Lowering its pixel floor must not touch a single
    outline, so the flag can only ever be a colour change.

    Compared as a shape_id -> area MAP, not as two lists in order. The ORDER
    is expected to move and moving it is correct: `rehome_resnapped_regions`
    puts a re-snapped region in the layer that declares its new cone, so one
    spool sews at one position (defect 16's remainder, 2026-08-31). A
    positional comparison here failed on exactly that and would have read as
    a geometry change.
    """
    off = run_stages(TESTDATA / fixture, _cfg())
    on = run_stages(TESTDATA / fixture, _cfg(revalidate_small_shapes=True))
    assert {r.shape_id: round(r.area_mm2, 6) for r in on.regions} == \
           {r.shape_id: round(r.area_mm2, 6) for r in off.regions}
    assert {r.shape_id: r.polygon.wkt for r in on.regions} == \
           {r.shape_id: r.polygon.wkt for r in off.regions}


def _cones_at_pass_entry(fixture: str, small: bool) -> tuple[set, set]:
    """(cones the design carried when `revalidate_threads` began, cones it
    ends with). Probes `pipeline.revalidate_threads` — patched on `pipeline`,
    NOT on `stage4_vectorize`, because `pipeline` binds the name at import and
    patching the defining module does nothing (that cost a silent empty run
    when `tools/revalidate_floor.py` was written)."""
    from digitizer_core import pipeline as pl

    real = pl.revalidate_threads
    seen: dict = {}

    def probe(regions, p, cfg, **kw):
        seen["entry"] = {r.thread_index for r in regions
                         if not r.meta.get("enclosed_background")}
        return real(regions, p, cfg, **kw)

    pl.revalidate_threads = probe
    try:
        result = run_stages(TESTDATA / fixture,
                            _cfg(revalidate_small_shapes=small))
    finally:
        pl.revalidate_threads = real
    return seen["entry"], {r.thread_index for r in result.regions}


@pytest.mark.parametrize("fixture", [
    FIXTURE,                      # 16 -> 16 cones
    "photo/logo_bridge_bar.jpg",  # 18 -> 18 (22 under the first construction)
    "photo/drone_render.png",     # 19 -> 20, and the reason this is not "<="
])
def test_a_small_shape_can_only_take_a_cone_the_design_already_carried(fixture):
    """The rule the corpus forced, and the reason this flag is not simply a
    lowered constant.

    Off the photo route the argmin runs over the WHOLE chart, so the first
    build re-snapped crowds of shards onto brand-new spools — `bridge_bar`
    18 -> 22 cones, `drone_render` 19 -> 21 — and every new spool is another
    row `THREAD_MATCH_POOR` scores: drone_render went 4 -> 5 blocks on cones
    it did not previously carry. A shard admitted only by the lowered floor is
    now restricted to `loaded`, the cone list snapshotted at pass entry.

    **The invariant is NOT `on <= off`, and drone_render is why.** Measured
    2026-09-06: its extra cone is `0674`, which WAS in the entry set and which
    the shipped pass VACATES with the flag off — the last region wearing it
    re-snaps away. With the flag on a shard lands on it instead and keeps it
    alive. So the honest statement is that the flag can never introduce a cone
    the design did not already carry, which is what this asserts.
    """
    entry_off, end_off = _cones_at_pass_entry(fixture, False)
    entry_on, end_on = _cones_at_pass_entry(fixture, True)
    assert entry_off == entry_on, "the flag must not change anything upstream"
    assert (end_on - end_off) <= entry_on, sorted(end_on - end_off - entry_on)


@pytest.mark.parametrize("fixture", [FIXTURE, "photo/logo_bridge_bar.jpg"])
def test_the_two_cause_3_fixtures_gain_no_cone_at_all(fixture):
    """The stronger statement where it actually holds. These are the two
    fixtures the F-wall decomposition attributes to the pixel floor (63 and 12
    refusals); on both the cone count is unchanged, which is the operator-side
    promise — no extra colour stop for a sub-1 mm2 shard."""
    off = run_stages(TESTDATA / fixture, _cfg())
    on = run_stages(TESTDATA / fixture, _cfg(revalidate_small_shapes=True))
    assert len({r.thread_index for r in on.regions}) == \
           len({r.thread_index for r in off.regions})


def test_on_resnaps_the_shape_the_measurement_named():
    """The 177-px shape wearing `0111 Whale` over (252,252,252) artwork.

    Asserted by SHAPE, not by count: a count would pass on any seven shapes
    moving, and the point of the flag is this one.
    """
    off = run_stages(TESTDATA / FIXTURE, _cfg())
    on = run_stages(TESTDATA / FIXTURE, _cfg(revalidate_small_shapes=True))
    by_id_off = {r.shape_id: r for r in off.regions}
    by_id_on = {r.shape_id: r for r in on.regions}
    assert DRIFTED in by_id_off, "fixture drifted; re-derive from the tool"

    assert by_id_off[DRIFTED].thread_number == "0111"
    assert by_id_on[DRIFTED].thread_number == "0015"
    assert "thread_resnapped_de00" not in by_id_off[DRIFTED].meta
    assert by_id_on[DRIFTED].meta["thread_resnapped_de00"] > 30.0


def test_on_reports_which_floor_produced_the_list():
    """Without `min_px` in the payload a reader cannot tell a design with no
    small drifted shapes from one whose small drifted shapes were never asked
    about."""
    off = _resnap_warning(run_stages(TESTDATA / FIXTURE, _cfg()))
    on = _resnap_warning(
        run_stages(TESTDATA / FIXTURE, _cfg(revalidate_small_shapes=True)))
    assert on is not None
    assert on["min_px"] == THREAD_REVALIDATE_MIN_PX_SMALL
    if off is not None:
        assert off["min_px"] == THREAD_REVALIDATE_MIN_PX
        assert on["count"] > off["count"]
        # Every shape the strict floor already re-snapped is still re-snapped:
        # a lower floor may only ADD shapes to the list.
        assert set(off["ids"]) <= set(on["ids"])


def test_the_improvement_gate_is_untouched():
    """The pixel floor and the dE00 floor guard different things. This flag
    moves the first; nothing here may move the second, because that is the
    guard that stops sub-unit wobble churning every assignment in the design.
    """
    assert THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 == 3.0
    on = run_stages(TESTDATA / FIXTURE, _cfg(revalidate_small_shapes=True))
    resnapped = [r for r in on.regions if "thread_resnapped_de00" in r.meta]
    assert resnapped, "flag fired nothing — the rest of this test proves nothing"
    for r in resnapped:
        assert r.meta["thread_resnapped_de00"] >= \
            THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00
