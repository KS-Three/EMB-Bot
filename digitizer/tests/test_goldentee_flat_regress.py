"""Why the flat lane over-stitches Golden Tee and reads Fremont's small words
worse after `stage0_scale_relative_grad` (#1301) routed both flat
(`docs/goldentee-flat-regress-2026-11-07.md`). Measurement only: nothing here
moves a default or calibrates a gate.

Pinned, as instrument readings on the two committed artworks at the pro's
size through the Studio's request:

1. Stage 0 routes both FLAT with the switch on and GRADIENT with it off, and
   it is the switch's own read that decides: tonal share under its gate, the
   old smoothness read over its own.
2. Golden Tee on the flat lane: global k-means leaves stage 3 thousands of
   masks, and the two sub-floor rescues (the chain rescue and the
   `keep_thin_strokes` contrast rescue) keep about twice the masks the plain
   absorb would. Those kept specks are the per-region table's largest row
   (+37 shapes, +951 stitches, +12 of the plan's +12 trims).
3. Fremont on the flat lane: stage 2 returns no dark-ink labels. On the
   gradient lane those labels are what tags the tan small text `dark_ink`
   and sews it as a bean (`thin_ink.bean_dark_ink`); without them the words
   go the small-text re-set path and read 0.903 -> 0.605.

Counts carry headroom (a Linux runner's k-means need not land on Windows'
exact numbers); the doc has the exact readings.
"""
from __future__ import annotations

import dataclasses
import json

import pytest

from digitizer_core import PipelineConfig, two_tone
from digitizer_core import stage0_classify as s0
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_quantize import quantize
from digitizer_core.stage3_segment import ClassicalSegmenter, resolve_small_regions
from digitizer_core.threads import rgb_to_lab

from .conftest import TESTDATA

#: slug -> (art, garment, the pro's width mm), as `tools.pro_baseline.JOBS`
JOBS = {
    "goldentee_hat": (TESTDATA / "photo" / "logo_golden_tee.jpg", "hat_front", 74.9),
    "hotel_fremont_hat": (TESTDATA / "photo" / "logo_hotel_fremont.webp", "hat_front", 92.6),
}


def _cfg(slug: str) -> PipelineConfig:
    from digitizer_service.app import _parse_config
    from tools import pro_pair as pp
    _art, garment, width = JOBS[slug]
    return PipelineConfig(**_parse_config(json.dumps(pp.request(width, garment))))


def _pixels(slug: str):
    from digitizer_service.app import _decode
    return _decode(JOBS[slug][0].read_bytes())


def test_the_jobs_match_the_tripwire_population():
    from tools.pro_baseline import JOBS as PB
    for slug, (art, garment, width) in JOBS.items():
        g, w, spec, *_ = PB[slug]
        assert (g, w) == (garment, width)
        assert spec == "testdata:" + art.relative_to(TESTDATA).as_posix()


@pytest.mark.parametrize("slug", sorted(JOBS))
def test_stage0_routes_both_jobs_flat_on_and_gradient_off(slug):
    cfg = _cfg(slug)
    assert cfg.stage0_scale_relative_grad is True
    px = _pixels(slug)
    on = s0.classify(px, cfg)
    off = s0.classify(px, dataclasses.replace(cfg, stage0_scale_relative_grad=False))
    assert (on.class_, off.class_) == ("flat", "gradient")
    # The switch's read is under its gate (Golden Tee 0.020, Fremont 0.000),
    # the old one over its own (0.082, 0.304 against 0.0015).
    assert on.signals["tonal_frac"] < s0.TONAL_GRADIENT_MIN / 2
    assert on.signals["gradient_smoothness"] >= s0.GRAD_VAR_GRADIENT_MIN


def _flat_stage3(slug: str):
    cfg = _cfg(slug)
    p = prep(_pixels(slug), cfg, design_class="flat")
    if cfg.two_tone_snap:
        two_tone.apply(p)
    q = quantize(p, cfg)
    return cfg, p, q


@pytest.fixture(scope="module")
def goldentee_flat():
    return _flat_stage3("goldentee_hat")


def _resolve(cfg, p, q, *, chain: bool, contrast: bool) -> int:
    masks = ClassicalSegmenter().segment(q, p, cfg)
    c = cfg if contrast else dataclasses.replace(cfg, keep_thin_strokes=False)
    kept, _w = resolve_small_regions(
        masks, c, p.px_per_mm, p.enclosed_mask, chain_rescue=chain,
        layer_lab=rgb_to_lab(q.cluster_rgb), page_fringe=getattr(q, "page_fringe", None))
    return len(kept)


def test_golden_tee_flat_lane_shatters_into_thousands_of_stage3_masks(goldentee_flat):
    cfg, p, q = goldentee_flat
    # 2,038 on the flat lane against 66 from the gradient lane's SLIC+RAG.
    assert len(ClassicalSegmenter().segment(q, p, cfg)) >= 1000


def test_golden_tee_specks_are_kept_by_the_two_rescues(goldentee_flat):
    """Default 167 masks out of stage 3; chain rescue off 129, contrast rescue
    off 144, both off 84. Every one of those 83 is a sub-floor speck (a bevel
    or sweep step, 0.04-0.4 mm wide) that the plain absorb would fold into its
    neighbour; on the gradient lane stage 3 keeps 65 of 66."""
    cfg, p, q = goldentee_flat
    default = _resolve(cfg, p, q, chain=True, contrast=True)
    no_chain = _resolve(cfg, p, q, chain=False, contrast=True)
    no_contrast = _resolve(cfg, p, q, chain=True, contrast=False)
    neither = _resolve(cfg, p, q, chain=False, contrast=False)
    assert neither < no_chain < default
    assert neither < no_contrast < default
    assert default - neither >= 60
    assert default >= 1.5 * neither


def test_fremont_flat_lane_has_no_dark_ink_read():
    """The gradient lane's stage 2 (`photo_segment`, dark population) returns
    dark-ink labels {2, 3} on Fremont (the tan small text and the rope; 33 s,
    so read in the doc, not here). The flat lane's `quantize` returns none,
    so `bean_dark_ink` has nothing to sew as a bean."""
    _cfg_, _p, q = _flat_stage3("hotel_fremont_hat")
    assert not q.dark_ink_labels
