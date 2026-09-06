"""`THREAD_MATCH_POOR` says how big the shape it is condemning is.

The check has **no area floor** — measured 2026-09-06 across the seven F-grade
fixtures, the worst shape behind a blocking finding runs min 0.58 mm², p50
3.17, max 1,648.5, and 12 of the 23 measurable ones are under 5 mm². So
`logo_gaulke_roofing` was told "do not sew" over 63.6 ΔE00 on **0.03%** of its
area in exactly the words `drone_render` gets for 14.1 ΔE00 over **54%** of
its own, and nothing in the finding let a reader tell those apart without
going and measuring the shape.

Whether the SEVERITY should have a floor is a product call that re-bases the
scorecard for at least four fixtures — recorded, not proposed. Saying the size
is not: this is message prose plus two `extra` fields, and
`corpus_scorecard.diff` compares `code:severity` while explicitly stating that
wording may change without a geometry change.

**The denominator is the SCORED regions** — the sewn, non-enclosed set
`_region_color_errors` builds rows from — not `result.regions`, which would
include background shapes nothing stitches and quietly shrink every share.
That is why `drone_render`'s worst reads 54.48% here where an all-regions
denominator gave 53.6%: a different, and better, denominator, not a drift.
"""

import re
from functools import lru_cache

import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.preflight import run_preflight

from .conftest import TESTDATA

# The two extremes the measurement named: a 0.58 mm² shard and a 1,648 mm²
# field, both emitting `block`.
TINY = "photo/logo_gaulke_roofing.png"
HUGE = "photo/drone_render.png"

_SIZE = re.compile(r"(\d+\.\d{2}) mm² — (\d+\.\d{2})% of the design")


@lru_cache(maxsize=None)
def _blocks(fixture: str):
    """One digitize + preflight per fixture, reused by every test here.

    WHY THE CACHE. Nine calls over two fixtures without it. MASTER_SCOPE's "CI
    feedback speed" section records that GitHub's runners are 2-core, so
    `-n auto` gets two workers and *"the remaining lever is `--durations`, not
    parallelism"*. Caching the same shape across the thread suites measured
    **19m52s -> 8m03s** on those three files and took the whole digitizer suite
    from 18m38s to 14m00s.

    Hands back the live `PipelineResult` because every test here only reads it.
    **If one ever needs to mutate, give it an uncached run** rather than making
    this return copies.
    """
    art = TESTDATA / fixture
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(art, cfg)
    report = run_preflight(result, plan, cfg, image=art)
    return [f for f in report["findings"]
            if f.get("code") == "THREAD_MATCH_POOR"
            and f.get("severity") == "block"], result


@pytest.mark.parametrize("fixture", [TINY, HUGE])
def test_every_blocking_finding_states_a_size(fixture):
    blocks, _result = _blocks(fixture)
    assert blocks, f"{fixture} no longer blocks; re-derive this test"
    for f in blocks:
        assert _SIZE.search(f["message"]), f["message"]


@pytest.mark.parametrize("fixture", [TINY, HUGE])
def test_the_message_and_the_payload_agree(fixture):
    """The prose is for a person, the `extra` fields are for a review screen;
    they must not drift apart."""
    blocks, _result = _blocks(fixture)
    for f in blocks:
        mm2, pct = _SIZE.search(f["message"]).groups()
        extra = f["extra"]
        assert float(mm2) == pytest.approx(extra["worst_shape_area_mm2"])
        assert float(pct) / 100.0 == pytest.approx(
            extra["worst_shape_area_frac"], abs=5e-5)


def test_the_two_extremes_are_now_distinguishable():
    """The point of the change, asserted as the contrast that motivated it."""
    tiny, _ = _blocks(TINY)
    huge, _ = _blocks(HUGE)
    tiny_worst = min(f["extra"]["worst_shape_area_frac"] for f in tiny)
    huge_worst = max(f["extra"]["worst_shape_area_frac"] for f in huge)
    assert tiny_worst < 0.001, tiny_worst          # 0.58 mm², ~0.03%
    assert huge_worst > 0.5, huge_worst            # 1,648 mm², ~54%


def test_the_fraction_is_over_the_scored_regions_not_all_of_them():
    """The denominator excludes enclosed background. `logo_gaulke_roofing`
    carries 46 such regions out of 56, so an all-regions denominator would put
    every share far lower — this fails if someone 'simplifies' it to
    `sum(r.area_mm2 for r in result.regions)`.
    """
    blocks, result = _blocks(TINY)
    assert blocks
    all_area = sum(r.area_mm2 for r in result.regions)
    enclosed = [r for r in result.regions if r.meta.get("enclosed_background")]
    assert enclosed, "fixture drift: this fixture is supposed to carry them"
    f = blocks[0]
    area = f["extra"]["worst_shape_area_mm2"]
    over_all = area / all_area
    assert f["extra"]["worst_shape_area_frac"] > over_all * 1.05


@pytest.mark.parametrize("fixture,expected", [(TINY, 2), (HUGE, 4)])
def test_no_severity_moved(fixture, expected):
    """Prose only. These counts are the ones on record before the message
    changed, so a severity shift shows up here rather than as a silent
    scorecard drift."""
    blocks, _result = _blocks(fixture)
    assert len(blocks) == expected
