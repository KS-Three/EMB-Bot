"""`revalidate_small_shapes` — let stage 4's re-ask reach the shapes
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
from functools import lru_cache
from typing import NamedTuple

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

from .conftest import PRE_FLIP, TESTDATA
from tests.conftest import own_thread_only

# The fixture the defect was traced on. Its worst thread finding is a 177-px
# shape — inside the band, and the largest single dE00 the corpus offers.
FIXTURE = "photo/screenshot_phone_ui_golke.jpg"

# Named because the assertions below are about THESE shapes, not "some shape" (re-pointed
# 2026-11-20 from the engine-before-the-folds' `S43831dcd`, 177 px, wearing 0111 Whale):
# 0.997 and 0.960 mm2, wearing 1776 off, 0020 on.
DRIFTED = ("Sf93252d9", "Sc68b9586")


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, **kw)


class _Case(NamedTuple):
    """Everything this file asks of one (fixture, flag) pipeline run.

    Plain, immutable values — never the `PipelineResult`, because the cache
    below shares one object across every test that asks for the same case and
    a mutable region list would let one test's edit corrupt another's.
    """
    digest: tuple           # (sha20 of the emitted stitches, stitch count)
    geometry: dict          # shape_id -> (area rounded 6, polygon WKT)
    threads: dict           # shape_id -> thread_number
    resnapped: dict         # shape_id -> thread_resnapped_de00, present only
    cones: frozenset        # thread_index the design ends up sewing
    entry_cones: frozenset  # ... and the set it carried at pass entry
    warning: tuple | None   # (min_px, count, frozenset(ids)) or None


@lru_cache(maxsize=None)
def _case(fixture: str, small: bool) -> _Case:
    """One pipeline run per (fixture, flag), reused by every test.

    WHY THE CACHE. Written straight through, this file ran `run_stages` about
    23 times over 8 distinct (fixture, flag) pairs — roughly 65% of the work
    repeated. That is not free: MASTER_SCOPE's "CI feedback speed" section
    records that GitHub's runners are 2-core, so `-n auto` gets two workers and
    *"the remaining lever is `--durations`, not parallelism"* — i.e. making
    each test cheaper is the only lever left, and this file is one of four
    added in a day that each re-digitize the corpus's heaviest fixtures.

    The entry-cone probe is installed here rather than in its own run for the
    same reason. It patches `pipeline.revalidate_threads`, NOT
    `stage4_vectorize`'s: `pipeline` binds the name at import, so patching the
    defining module does nothing (that cost a silent empty run when
    `tools/revalidate_floor.py` was written).
    """
    from digitizer_core import pipeline as pl

    real = pl.revalidate_threads
    seen: dict = {}

    def probe(regions, p, cfg, **kw):
        seen["entry"] = frozenset(r.thread_index for r in regions
                                  if not r.meta.get("enclosed_background"))
        # the pipeline always passes `small_shapes=True` (the switch was folded into
        # the code 2026-11-19); the OFF arm is the same call with it forced False
        return real(regions, p, cfg, **{**kw, "small_shapes": small})

    cfg = _cfg(**PRE_FLIP)
    pl.revalidate_threads = own_thread_only(probe, real)
    try:
        result = run_stages(TESTDATA / fixture, cfg)
    finally:
        pl.revalidate_threads = real
    plan = plan_stitches(result, cfg)

    coords = [
        (round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
        for _b, run in plan.iter_runs()
        for x, y in run.points
    ]
    warn = next((w for w in result.warnings
                 if w["code"] == THREAD_RESNAPPED_AFTER_DRIFT), None)
    return _Case(
        digest=(hashlib.sha256(repr(coords).encode()).hexdigest()[:20],
                len(coords)),
        geometry={r.shape_id: (round(r.area_mm2, 6), r.polygon.wkt)
                  for r in result.regions},
        threads={r.shape_id: r.thread_number for r in result.regions},
        resnapped={r.shape_id: r.meta["thread_resnapped_de00"]
                   for r in result.regions
                   if "thread_resnapped_de00" in r.meta},
        cones=frozenset(r.thread_index for r in result.regions),
        entry_cones=seen["entry"],
        warning=(None if warn is None
                 else (warn["min_px"], warn["count"], frozenset(warn["ids"]))),
    )


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


@pytest.mark.parametrize("fixture", [
    FIXTURE,
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
    assert _case(fixture, True).geometry == _case(fixture, False).geometry


@pytest.mark.parametrize("fixture", [
    FIXTURE,                      # 16 -> 16 cones
    # logo_bridge_bar dropped 2026-11-20: its OFF arm is not the pre-flip engine once the colour flags are folded
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
    off, on = _case(fixture, False), _case(fixture, True)
    assert off.entry_cones == on.entry_cones, \
        "the flag must not change anything upstream"
    extra = on.cones - off.cones
    assert extra <= on.entry_cones, sorted(extra - on.entry_cones)


# The screenshot case (`FIXTURE`, 16 -> 16 cones) was dropped 2026-11-20: it held on the engine
# without `small_glyph_keep`, which is in the code now (docs/flag-history/tier-b2-lettering.md);
# with it the flag reads 15 cones OFF and 16 ON there (one cone more, not asserted away).
@pytest.mark.parametrize("fixture", ["photo/logo_bridge_bar.jpg"])
def test_the_two_cause_3_fixtures_gain_no_cone_at_all(fixture):
    """The stronger statement where it actually holds. These are the two
    fixtures the F-wall decomposition attributes to the pixel floor (63 and 12
    refusals); on both the cone count is unchanged, which is the operator-side
    promise — no extra colour stop for a sub-1 mm2 shard."""
    assert len(_case(fixture, True).cones) == len(_case(fixture, False).cones)


def test_on_resnaps_the_shapes_the_measurement_named():
    """Two sub-200-px shapes wearing `1776` over 0020-coloured artwork.

    Asserted by SHAPE, not by count: a count would pass on any seven shapes
    moving, and the point of the flag is these.

    Re-pointed 2026-11-20 (bundle roll-forward, #1740/B3 folds): the original shape
    (`S43831dcd`, 177 px, `0111 Whale` over (252,252,252), re-snapped 32.7 dE00 -> `0015`)
    existed only on the engine before robust colour, edge snap, the dissolve and the
    colour cap were folded into the code. On today's engine the same two-spool band holds
    `Sf93252d9` (0.997 mm2) and `Sc68b9586` (0.960 mm2): `1776` OFF, `0020` ON, each
    re-snapped by 11.78 dE00; nothing re-snaps OFF. Re-captured 2026-11-20.
    """
    off, on = _case(FIXTURE, False), _case(FIXTURE, True)
    for sid in DRIFTED:
        assert sid in off.threads, "fixture drifted; re-derive from the tool"
        assert off.threads[sid] == "1776"
        assert on.threads[sid] == "0020"
        assert sid not in off.resnapped
        assert on.resnapped[sid] == pytest.approx(11.78, abs=0.05)


def test_on_reports_which_floor_produced_the_list():
    """Without `min_px` in the payload a reader cannot tell a design with no
    small drifted shapes from one whose small drifted shapes were never asked
    about."""
    off, on = _case(FIXTURE, False).warning, _case(FIXTURE, True).warning
    assert on is not None
    on_min_px, on_count, on_ids = on
    assert on_min_px == THREAD_REVALIDATE_MIN_PX_SMALL
    if off is not None:
        off_min_px, off_count, off_ids = off
        assert off_min_px == THREAD_REVALIDATE_MIN_PX
        assert on_count > off_count
        # Every shape the strict floor already re-snapped is still re-snapped:
        # a lower floor may only ADD shapes to the list.
        assert off_ids <= on_ids


def test_the_improvement_gate_is_untouched():
    """The pixel floor and the dE00 floor guard different things. This flag
    moves the first; nothing here may move the second, because that is the
    guard that stops sub-unit wobble churning every assignment in the design.
    """
    assert THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 == 3.0
    resnapped = _case(FIXTURE, True).resnapped
    assert resnapped, "flag fired nothing — the rest of this test proves nothing"
    for de00 in resnapped.values():
        assert de00 >= THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00
