"""A colour change is a machine stop, so the plan must not add one where the
thread does not change. Two claims, measured on existing fixtures at the
shipped defaults:

1. No two blocks that are neighbours in sew order carry the same thread
   (a stop that buys nothing).
2. The stop count equals blocks - 1, and the thread count the operator loads
   is the number of DISTINCT threads sewn. A thread revisited later with other
   colours between is a legitimate extra stop only if the hoist declined it;
   that gap is pinned as an xfail below rather than hidden.

Specialty-step blocks (`step` set: appliqué placement/tack/cover) sew several
blocks on ONE thread on purpose, so they are excluded from both claims.
"""
from functools import lru_cache
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"

FLAT = ["logo_whitebg.png", "logo_alpha.png", "ribbon_curve.png",
        "art/logo_toat_machine.png", "art/logo_golke_roofing.png"]


@lru_cache(maxsize=None)
def _plan(name, photo=False):
    img = TESTDATA / name
    if not img.exists():
        pytest.skip(f"{name} not in checkout")
    _r, plan = digitize(img, PipelineConfig(target_width_mm=100.0, is_photographic=photo,
                                               photo_prep=False))
    return plan


def _threads(plan):
    assert all(b.step is None for b in plan.blocks), "specialty steps are out of scope here"
    return [b.thread_index for b in plan.blocks]


@pytest.mark.parametrize("name", FLAT)
def test_no_neighbouring_blocks_share_a_thread(name):
    seq = _threads(_plan(name))
    assert all(a != b for a, b in zip(seq, seq[1:])), f"needless stop between same-thread blocks: {seq}"


@pytest.mark.parametrize("name", FLAT)
def test_stop_count_is_blocks_minus_one(name):
    plan = _plan(name)
    assert plan.stats.color_changes == max(0, len(plan.blocks) - 1)
    assert len(plan.palette) == len(plan.blocks), "palette is one cone per block"


@pytest.mark.parametrize("name", FLAT)
def test_flat_artwork_sews_each_thread_once(name):
    seq = _threads(_plan(name))
    assert len(seq) == len(set(seq)), f"colour count {len(seq)} != distinct threads {len(set(seq))}: {seq}"


def test_owl_default_has_no_adjacent_same_thread_blocks():
    seq = _threads(_plan("photo/owl_kent.jpg", photo=True))
    assert all(a != b for a, b in zip(seq, seq[1:])), seq


@pytest.mark.xfail(strict=False, reason="photo lane revisits a cone with other colours between "
                   "(owl t4 at blocks 0/2/7, MERGE test docstring): stops exceed distinct threads")
def test_owl_stop_count_equals_distinct_threads():
    seq = _threads(_plan("photo/owl_kent.jpg", photo=True))
    assert len(seq) == len(set(seq)), f"{len(seq)} blocks over {len(set(seq))} threads"
