"""`THREAD_MATCH_POOR` says how big the shape it is condemning is — and,
since 2026-09-10, no longer condemns a shard.

The check had **no area floor** — measured 2026-09-06 across the seven F-grade
fixtures, the worst shape behind a blocking finding ran min 0.58 mm², p50
3.17, max 1,648.5, and 12 of the 23 measurable ones were under 5 mm². So
`logo_gaulke_roofing` was told "do not sew" over 63.6 ΔE00 on **0.03%** of its
area in exactly the words `drone_render` gets for 14.1 ΔE00 over **54%** of
its own. Saying the size (this file's first job, 2026-09-06) let a reader tell
those apart; the floor (quality review 2026-09-08 item 11, built 2026-09-10 as
`_THREAD_MATCH_MIN_PATCH_MM2`, the uncovered check's 5.0 mm²) stops the
check from condemning the shard at all: a graded patch under the floor
cannot set a thread's severity, and a thread whose only offenders are
sub-floor emits nothing. Measured over the scorecard matrix
(`tools/thread_match_floor.py`, 52 pairs at 80 mm): 40 blocking findings
become 26, gaulke's one block rode a sub-floor shard and its grade reads
D 46 -> B 76, drone keeps the two that sit on 200 and 1,564 mm².

**The denominator is the SCORED regions** — the sewn, non-enclosed set
`_region_color_errors` builds rows from — not `result.regions`, which would
include background shapes nothing stitches and quietly shrink every share.
That is why `drone_render`'s worst reads 54.48% here where an all-regions
denominator gave 53.6%: a different, and better, denominator, not a drift.
"""

import re
from functools import lru_cache

import pytest

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.preflight import run_preflight

from .conftest import TESTDATA

# The two extremes the 2026-09-06 measurement named: a 0.58 mm² shard and a
# 1,648 mm² field, both emitting `block` then. Under the floor only the field
# does. HOLES has enclosed-background regions AND a block that survives the
# floor, which the denominator test needs.
TINY = "photo/logo_gaulke_roofing.png"
HUGE = "photo/drone_render.png"
HOLES = "photo/logo_golden_tee.jpg"

_SIZE = re.compile(r"(\d+\.\d{2}) mm² — (\d+\.\d{2})% of the design")


@lru_cache(maxsize=None)
def _report(fixture: str):
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
    return report, result


def _blocks(fixture: str):
    report, result = _report(fixture)
    return [f for f in report["findings"]
            if f.get("code") == "THREAD_MATCH_POOR"
            and f.get("severity") == "block"], result


def _thread_match(fixture: str):
    report, _result = _report(fixture)
    return [f for f in report["findings"] if f.get("code") == "THREAD_MATCH_POOR"]


def test_the_floor_is_the_uncovered_checks_number():
    """One constant, not two: a patch too small to be worth an uncovered
    finding is too small to condemn a spool over."""
    assert pf._THREAD_MATCH_MIN_PATCH_MM2 == pf._UNCOVERED_MIN_PATCH_MM2 == 5.0


@pytest.mark.parametrize("fixture", [HUGE, HOLES])
def test_every_blocking_finding_states_a_size(fixture):
    blocks, _result = _blocks(fixture)
    assert blocks, f"{fixture} no longer blocks; re-derive this test"
    for f in blocks:
        assert _SIZE.search(f["message"]), f["message"]


@pytest.mark.parametrize("fixture", [HUGE, HOLES])
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


def test_the_shard_no_longer_condemns_and_the_field_still_does():
    """The point of the floor, asserted as the contrast that motivated it:
    gaulke's 63.6 dE00 rode a 0.58 mm² shard and emits NOTHING now (no warn
    either — the shard was that thread's only offender), while drone's
    1,648 mm² field blocks exactly as before, with its size stated."""
    tiny, _ = _blocks(TINY)
    assert tiny == []
    assert _thread_match(TINY) == []
    huge, _ = _blocks(HUGE)
    assert huge
    huge_worst = max(f["extra"]["worst_shape_area_frac"] for f in huge)
    assert huge_worst > 0.5, huge_worst            # 1,648 mm², ~54%
    for f in huge:
        assert f["extra"]["worst_patch_mm2"] >= pf._THREAD_MATCH_MIN_PATCH_MM2


def test_a_judged_patch_is_never_under_the_floor_and_sub_floor_offenders_are_listed():
    """Every finding's judging patch sits at or above the floor; an offender
    under it is still in `regions`, flagged, and counted — never judging."""
    for fixture in (HUGE, HOLES):
        for f in _thread_match(fixture):
            x = f["extra"]
            assert x["worst_patch_mm2"] >= pf._THREAD_MATCH_MIN_PATCH_MM2
            listed_sub = [r for r in x["regions"] if r.get("sub_floor")]
            assert len(listed_sub) == x["sub_floor_count"]
            for r in listed_sub:
                assert r["footprint_mm2"] < pf._THREAD_MATCH_MIN_PATCH_MM2
            assert x["region_count"] + x["sub_floor_count"] <= x["regions_scored"]


def test_the_fraction_is_over_the_scored_regions_not_all_of_them():
    """The denominator excludes enclosed background. `logo_golden_tee`
    carries its white letter holes as enclosed regions, so an all-regions
    denominator would put every share lower — this fails if someone
    'simplifies' it to `sum(r.area_mm2 for r in result.regions)`.
    """
    blocks, result = _blocks(HOLES)
    assert blocks
    all_area = sum(r.area_mm2 for r in result.regions)
    enclosed = [r for r in result.regions if r.meta.get("enclosed_background")]
    assert enclosed, "fixture drift: this fixture is supposed to carry them"
    f = blocks[0]
    area = f["extra"]["worst_shape_area_mm2"]
    over_all = area / all_area
    assert f["extra"]["worst_shape_area_frac"] > over_all * 1.05


@pytest.mark.parametrize("fixture,expected", [(TINY, 0), (HUGE, 2), (HOLES, 1)])
def test_no_severity_moved(fixture, expected):
    """These counts are the ones on record under the floor (2026-09-10, the
    sweep in docs/superpowers/plans/2026-09-10-legibility-yardstick.md §4.1:
    gaulke 1 -> 0, drone 4 -> 2, golden_tee 2 -> 1 at 80 mm / left_chest),
    so a severity shift shows up here rather than as a silent scorecard
    drift. Before the floor TINY read 1 (re-pinned 2 -> 1 on 2026-09-09 with
    `subpixel_edges`; `test_thread_match_better_spool.py`'s SEVERITY note has
    that bisect) and HUGE 4."""
    blocks, _result = _blocks(fixture)
    assert len(blocks) == expected
