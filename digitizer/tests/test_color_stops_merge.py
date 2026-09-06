"""`COLOR_STOPS_HEAVY` says WHICH two colors to merge.

The remedy has read *"Merge similar colors"* since it was written, without
ever naming a pair — the same shape as `THREAD_MATCH_POOR` telling an operator
to "pick a closer thread" without consulting the design's own cone list (fixed
2026-09-06; this is the same fix one check over). The answer is a pairwise
CIEDE2000 over the cones the plan actually sews, and it is nearly free: no
pixels, and the corpus tops out around 25 cones.

On `logo_bridge_bar` the closest pair is **1.8 dE00** apart — below
`DELTA_E_VISIBLE`, i.e. two cones a person can barely tell apart, each costing
its own manual re-thread.

Severity does not move: this is message prose plus four payload fields.
"""

from functools import lru_cache

import numpy as np
import pytest
from skimage.color import deltaE_ciede2000

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.threads import rgb_to_lab

from .conftest import TESTDATA

HEAVY = "photo/logo_bridge_bar.jpg"     # 17 changes, 18 distinct cones
QUIET = "logo_alpha.png"                # far under COLOR_STOPS_MAX


@lru_cache(maxsize=None)
def _run(fixture: str):
    """One digitize + preflight per fixture, reused by every test here.
    Read-only; take an uncached run if one ever needs to mutate."""
    art = TESTDATA / fixture
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(art, cfg)
    report = pf.run_preflight(result, plan, cfg, image=art)
    hits = [f for f in report["findings"]
            if f.get("code") == pf.COLOR_STOPS_HEAVY]
    return hits, plan


def test_a_quiet_design_reports_nothing():
    """The control: under the threshold there is no finding to improve."""
    hits, plan = _run(QUIET)
    assert plan.stats.color_changes <= pf.COLOR_STOPS_MAX
    assert hits == []


def test_the_finding_names_a_pair():
    hits, _ = _run(HEAVY)
    assert len(hits) == 1
    f = hits[0]
    assert f["severity"] == "warn"          # unchanged
    assert "Merge similar colors" in f["message"]   # instruction kept
    a, b = f["extra"]["closest_pair"]
    assert a in f["message"] and b in f["message"]


def test_the_pair_really_is_the_closest_two_cones():
    """Re-derived here from `plan.palette` rather than trusting the finding —
    the check and its test must not share an implementation."""
    hits, plan = _run(HEAVY)
    extra = hits[0]["extra"]

    cones: dict[str, list] = {}
    for entry in plan.palette:                       # dedupe, keep first
        cones.setdefault(str(entry["number"]), entry["rgb"])
    nums = list(cones)
    labs = rgb_to_lab(np.asarray([cones[n] for n in nums], np.float64))
    best, want = None, None
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            d = float(deltaE_ciede2000(labs[i].reshape(1, 3),
                                       labs[j].reshape(1, 3))[0])
            if best is None or d < best:
                best, want = d, {nums[i], nums[j]}
    assert set(extra["closest_pair"]) == want
    assert extra["closest_pair_delta_e"] == pytest.approx(best, abs=0.05)


def test_the_pair_is_never_one_cone_with_itself():
    """`plan.palette` is one entry PER BLOCK, so without the dedupe a cone
    sewn twice is trivially its own closest pair at 0.0 dE00. That is the
    whole reason the dedupe exists, so it is asserted rather than assumed."""
    hits, _ = _run(HEAVY)
    a, b = hits[0]["extra"]["closest_pair"]
    assert a != b
    assert hits[0]["extra"]["closest_pair_delta_e"] > 0.0


def test_distinct_cones_is_not_the_block_count():
    """The payload reports the DISTINCT cone count, which is what an operator
    loads — `color_changes` counts machine stops and can exceed it."""
    hits, plan = _run(HEAVY)
    extra = hits[0]["extra"]
    assert extra["distinct_cones"] == len({str(p["number"])
                                           for p in plan.palette})
    assert extra["repeated_cones"] == []      # merge_duplicate_cones is ON


def test_the_closest_pair_is_closer_than_the_visible_threshold():
    """Why this is worth saying at all: the two cones the operator is being
    asked to load separately are closer than `DELTA_E_VISIBLE`, the same
    threshold `THREAD_MATCH_POOR` uses to decide a color is visibly off."""
    hits, _ = _run(HEAVY)
    assert hits[0]["extra"]["closest_pair_delta_e"] < pf.DELTA_E_VISIBLE
