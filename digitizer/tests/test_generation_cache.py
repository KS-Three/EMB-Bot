"""The stage 0-4 generation split and the service's generation cache.

Why this exists (area 5's measured table, 2026-08-13): a boundary edit used
to cost a full stage 0-7 re-run because `jobs.content_key` folds
`shape_overrides` into the config — every geometry edit was a guaranteed
cache miss. Stages 0-4 never read the four review-edit keys
(`deleted_shape_ids`, `shape_overrides`, `merge_shape_ids`, `split_shapes`
— they are applied between stage 4 and the palette), so the expensive
prefix can be cached across edits and only `finish_generation` +
`plan_stitches` re-run.

The property that must never break, and the reason these tests compare
whole stitch plans rather than spot-checking: **a cached generation must
produce byte-for-byte the stitches a cold run produces.** A stale or
cross-contaminated cache serving wrong stitches is strictly worse than the
slowness the cache removes.
"""
from __future__ import annotations

import json
from pathlib import Path

from digitizer_core.adapter import plan_to_design
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import (
    build_generation,
    digitize,
    finish_generation,
    plan_stitches,
    run_stages,
)
from digitizer_service.jobs import EDIT_KEYS, GenerationCache, generation_key

ART = Path(__file__).resolve().parents[1] / "testdata" / "logo_whitebg.png"


def _design_bytes(result, plan) -> bytes:
    """The whole observable output, canonicalized: the design a machine
    would sew plus the review payload's shape identity. Byte comparison —
    not a stitch-count spot check — because the failure mode being guarded
    is subtle geometry drift, not gross breakage."""
    design = plan_to_design(plan, name="t")
    ids = [r.shape_id for r in result.regions]
    return json.dumps({"design": design, "ids": ids}, sort_keys=True).encode()


def _first_shape_id(image, cfg=None) -> str:
    result = run_stages(image, cfg or PipelineConfig())
    return result.regions[0].shape_id


def test_split_composes_to_exactly_what_digitize_produces():
    """build_generation + finish_generation + plan_stitches must be the
    identical pipeline `digitize` runs — including with review edits in the
    config, since the split's whole claim is that edits only touch the
    finish half."""
    art = ART.read_bytes()
    sid = _first_shape_id(art)
    cfg = PipelineConfig(deleted_shape_ids=[sid])

    cold_result, cold_plan = digitize(art, cfg)

    gen = build_generation(art, cfg)
    split_result = finish_generation(gen.fork(), cfg)
    split_plan = plan_stitches(split_result, cfg)

    assert _design_bytes(split_result, split_plan) == _design_bytes(
        cold_result, cold_plan
    )


def test_one_generation_serves_different_edits_without_cross_talk():
    """The cache's real workload: one expensive generation, many edited
    finishes. Each finish must equal its own cold run, and a later finish
    must not see an earlier finish's edits (fork isolation — Region objects
    are mutated in place by apply_shape_edits, so a leaked reference would
    poison every subsequent request)."""
    art = ART.read_bytes()
    sid = _first_shape_id(art)
    gen = build_generation(art, PipelineConfig())

    cfg_edit = PipelineConfig(shape_overrides={sid: {"fill_angle_deg": 71.0}})
    cfg_plain = PipelineConfig()

    edited = finish_generation(gen.fork(), cfg_edit)
    edited_plan = plan_stitches(edited, cfg_edit)
    plain = finish_generation(gen.fork(), cfg_plain)
    plain_plan = plan_stitches(plain, cfg_plain)

    cold_edit_r, cold_edit_p = digitize(art, cfg_edit)
    cold_plain_r, cold_plain_p = digitize(art, cfg_plain)

    assert _design_bytes(edited, edited_plan) == _design_bytes(cold_edit_r, cold_edit_p)
    # The plain finish ran AFTER the edited one from the same generation —
    # if fork isolation leaked, the 71° angle would show up here.
    assert _design_bytes(plain, plain_plan) == _design_bytes(cold_plain_r, cold_plain_p)


def test_repeated_finishes_do_not_accumulate_warnings():
    """finish_generation appends to warning lists (PHOTO_AUTO_TIER, edit
    warnings); a fork that shared list containers would grow the cached
    generation's warnings on every hit."""
    art = ART.read_bytes()
    gen = build_generation(art, PipelineConfig())
    first = finish_generation(gen.fork(), PipelineConfig())
    second = finish_generation(gen.fork(), PipelineConfig())
    assert [w["code"] for w in first.warnings] == [w["code"] for w in second.warnings]


def test_generation_key_ignores_exactly_the_edit_keys():
    img = b"not-really-an-image"
    base = {"target_width_mm": 80.0, "preflight": False}
    with_edits = dict(
        base,
        deleted_shape_ids=["S1"],
        shape_overrides={"S2": {"tier": "run"}},
        merge_shape_ids=[["S3", "S4"]],
        split_shapes={"S5": [[0.0, 0.0], [1.0, 1.0]]},
    )
    assert generation_key(img, base) == generation_key(img, with_edits)
    # ...and nothing else: any non-edit field is part of the generation.
    assert generation_key(img, base) != generation_key(
        img, dict(base, target_width_mm=90.0)
    )
    # The key set itself is pinned so a new edit key being added to the
    # contract forces a decision here rather than silently invalidating.
    assert EDIT_KEYS == {
        "deleted_shape_ids",
        "shape_overrides",
        "merge_shape_ids",
        "split_shapes",
    }


def test_generation_cache_is_a_bounded_lru():
    cache = GenerationCache(max_entries=2)
    cache.put("a", "gen-a")
    cache.put("b", "gen-b")
    assert cache.get("a") == "gen-a"  # touch: a is now most-recent
    cache.put("c", "gen-c")           # evicts b, not a
    assert cache.get("b") is None
    assert cache.get("a") == "gen-a"
    assert cache.get("c") == "gen-c"
    assert cache.stats()["entries"] == 2
    cache.clear()
    assert cache.stats()["entries"] == 0
