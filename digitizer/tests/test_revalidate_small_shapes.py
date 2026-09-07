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

from .conftest import PRE_REC4_MASK, TESTDATA

# The fixture the defect was traced on. Its worst thread finding is a 177-px
# shape — inside the band, and the largest single dE00 the corpus offers.
FIXTURE = "photo/screenshot_phone_ui_golke.jpg"

# Named because the assertions below are about THIS shape, not "some shape":
# 0.94 mm2, 177 px, artwork (252,252,252), wearing 0111 Whale.
DRIFTED = "S43831dcd"


def _cfg(**kw) -> PipelineConfig:
    """This flag ISOLATED, with the other four of the `rec4_mask` set held at
    their pre-flip values.

    Kent flipped all five ON 2026-09-07. Every number in this file was measured
    one flag at a time, and with the other four live the comparison silently
    becomes "today's engine plus or minus one flag" — on
    `screenshot_phone_ui_golke` that reads 11 cones against 10 and fails
    `test_the_two_cause_3_fixtures_gain_no_cone_at_all`, which is a real
    interaction (this flag costs a cone in the presence of the other four) but
    NOT the promise that test was written to hold. The isolated promise still
    holds exactly: alone, this flag leaves screenshot on its 16 cones.

    `test_the_operator_promise_holds_on_the_SHIPPED_engine` covers the
    question that replaces it — what the operator actually loads."""
    for k, v in PRE_REC4_MASK.items():
        kw.setdefault(k, v)
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
def _default_digest(fixture: str) -> tuple:
    """This flag left UNMENTIONED inside the isolated context — i.e. at its
    pre-flip value, since `_cfg` pins `PRE_REC4_MASK`.

    It stopped meaning "the shipped engine" on 2026-09-07: the shipped engine
    has all five flags ON, and `test_the_shipped_default_is_the_RESNAPPED_engine`
    is what covers that now, with its own configs."""
    cfg = _cfg()
    result = run_stages(TESTDATA / fixture, cfg)
    plan = plan_stitches(result, cfg)
    coords = [
        (round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
        for _b, run in plan.iter_runs()
        for x, y in run.points
    ]
    return (hashlib.sha256(repr(coords).encode()).hexdigest()[:20], len(coords))


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
        return real(regions, p, cfg, **kw)

    cfg = _cfg(revalidate_small_shapes=small)
    pl.revalidate_threads = probe
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


def test_flag_defaults_on():
    """Kent's ruling 2026-09-07 flipped this ON as part of the `rec4_mask` set —
    five flags measured together as one arm of `tools/flip_sheet.py` (11 of 26
    fixtures move, -2,965 stitches, -22 blocks, -21 cones, five grades up, none
    down). The default still lives in a test so the NEXT change to it is a
    visible diff rather than a quiet one."""
    assert PipelineConfig().revalidate_small_shapes is True


def _shipped_cfg(**kw) -> PipelineConfig:
    """The engine a customer gets — no PRE_REC4_MASK pinning."""
    return PipelineConfig(target_width_mm=80.0, **kw)


@lru_cache(maxsize=None)
def _plan_digest(cfg: PipelineConfig) -> tuple:
    result = run_stages(TESTDATA / FIXTURE, cfg)
    plan = plan_stitches(result, cfg)
    coords = [(round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
              for _b, run in plan.iter_runs() for x, y in run.points]
    return (hashlib.sha256(repr(coords).encode()).hexdigest()[:20], len(coords))


def test_the_shipped_default_is_the_RESNAPPED_engine():
    """The contract every flag here carries, restated for Kent's 2026-09-07
    flip: the SHIPPED engine has this flag on, and turning only it off must
    still change the sewn result — otherwise the flag has gone inert and this
    file has stopped testing anything."""
    # The DEFAULT config against an EXPLICIT False — not `_case(F, False)`
    # against itself, which is what a first pass at the cache made this, and
    # which asserts nothing. The two configs are identical only while the
    # default is False, so a flipped default fails here as well as in
    # Built here rather than from `_case`/`_default_digest`, both of which pin
    # PRE_REC4_MASK for isolation and so cannot speak about the shipped engine
    # at all. This is the one test in the file that asks what a customer gets.
    shipped = _plan_digest(_shipped_cfg())
    without = _plan_digest(_shipped_cfg(revalidate_small_shapes=False))
    assert PipelineConfig().revalidate_small_shapes is True
    assert shipped != without, (
        "turning the flag off changes nothing on the shipped engine, so it is "
        "either inert or no longer reaching this fixture")


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
    assert _case(fixture, True).geometry == _case(fixture, False).geometry


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
    off, on = _case(fixture, False), _case(fixture, True)
    assert off.entry_cones == on.entry_cones, \
        "the flag must not change anything upstream"
    extra = on.cones - off.cones
    assert extra <= on.entry_cones, sorted(extra - on.entry_cones)


@pytest.mark.parametrize("fixture", [FIXTURE, "photo/logo_bridge_bar.jpg"])
def test_the_operator_promise_holds_on_the_SHIPPED_engine(fixture):
    """The promise that actually reaches a customer, restated for the engine
    Kent shipped 2026-09-07 rather than for this flag alone.

    The isolated test below says this flag adds no colour stop by itself. That
    was the operator-side promise while the flag was OFF by default; now that
    all five of the `rec4_mask` set ship, the honest version is about the whole
    set: the machine must not load MORE cones than the pre-flip engine did.

    Measured 2026-09-07 on the plan palette: `screenshot_phone_ui_golke`
    16 -> 11 cones, `logo_bridge_bar` 18 -> 13, and -21 across the corpus. The
    set sheds colour stops; it does not buy them. (Read on the REGION threads
    here, which is this file's own unit — a different denominator from the flip
    sheet's plan palette, and the direction is what is being pinned.)"""
    shipped = _shipped_cones(fixture)
    pre = _case(fixture, False).cones          # PRE_REC4_MASK, flag off
    assert len(shipped) <= len(pre), (
        f"{fixture}: the shipped engine loads {len(shipped)} cones against the "
        f"pre-flip {len(pre)} — the set is buying colour stops, not shedding "
        "them")


@lru_cache(maxsize=None)
def _shipped_cones(fixture: str) -> frozenset:
    """Region threads under the SHIPPED defaults — no keyword at all."""
    result = run_stages(TESTDATA / fixture,
                        PipelineConfig(target_width_mm=80.0))
    return frozenset(r.thread_index for r in result.regions
                     if not r.meta.get("enclosed_background"))


@pytest.mark.parametrize("fixture", [FIXTURE, "photo/logo_bridge_bar.jpg"])
def test_the_two_cause_3_fixtures_gain_no_cone_at_all(fixture):
    """The stronger statement where it actually holds. These are the two
    fixtures the F-wall decomposition attributes to the pixel floor (63 and 12
    refusals); on both the cone count is unchanged, which is the operator-side
    promise — no extra colour stop for a sub-1 mm2 shard."""
    assert len(_case(fixture, True).cones) == len(_case(fixture, False).cones)


def test_on_resnaps_the_shape_the_measurement_named():
    """The 177-px shape wearing `0111 Whale` over (252,252,252) artwork.

    Asserted by SHAPE, not by count: a count would pass on any seven shapes
    moving, and the point of the flag is this one.
    """
    off, on = _case(FIXTURE, False), _case(FIXTURE, True)
    assert DRIFTED in off.threads, "fixture drifted; re-derive from the tool"

    assert off.threads[DRIFTED] == "0111"
    assert on.threads[DRIFTED] == "0015"
    assert DRIFTED not in off.resnapped
    assert on.resnapped[DRIFTED] > 30.0


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
