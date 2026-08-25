"""`cfg.is_photographic` — the declaration that separates "which fill tier"
from "is this photographic content".

Kent ruled 2026-08-25 that a photo sews FILLED. That routes real photographs
through the GRADIENT lane, where every photo-specific mechanism was gated off
by class name: the palette resnap bind, the shade bind, preflight's photo
yardstick. `owl_kent.jpg` is a real photograph, classifies `gradient`, and so
sewed 14 cones against a `max_colors` of 12 while being graded on the tatami
yardstick.

It is DECLARED rather than detected because stage 0's signals demonstrably
cannot tell the two apart — see `config.is_photographic`'s docstring for the
measurement (a real photograph reads LESS photographic than two gradient
logos on the primary gate).
"""
from __future__ import annotations

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.config import PHOTO_CLASSES, is_photographic
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.preflight import run_preflight
from tests.conftest import TESTDATA

OWL = TESTDATA / "photo" / "owl_kent.jpg"


def test_none_falls_back_to_the_class_exactly_as_before():
    """The default must be indistinguishable from the pre-flag behaviour —
    that is what keeps every existing lane byte-identical."""
    cfg = PipelineConfig()
    assert cfg.is_photographic is None
    for klass in ("flat", "gradient"):
        assert not is_photographic(cfg, klass)
    for klass in PHOTO_CLASSES:
        assert is_photographic(cfg, klass)


def test_the_declaration_beats_the_class_in_both_directions():
    """"The caller said no" and "the caller said nothing" must be different
    values — the sentinel trap `fill_technique = "tatami"` still carries."""
    assert is_photographic(PipelineConfig(is_photographic=True), "gradient")
    assert is_photographic(PipelineConfig(is_photographic=True), "flat")
    assert not is_photographic(PipelineConfig(is_photographic=False), "photo_subject")
    assert not is_photographic(PipelineConfig(is_photographic=False), "photo_scene")


def test_one_canonical_photo_class_tuple():
    """Three independent literals is how the gate drifted apart. They alias
    one tuple now, so a change cannot reach two of the three."""
    from digitizer_core import stage4_vectorize, stage6_satin, stage7_sequence

    assert stage7_sequence.PHOTO_CLASSES is PHOTO_CLASSES
    assert stage4_vectorize._PHOTO_CLASSES is PHOTO_CLASSES
    assert stage6_satin._PHOTO_CLASSES is PHOTO_CLASSES


def test_declaring_a_gradient_photograph_brings_it_inside_max_colors():
    """The defect this flag exists to close, end to end.

    `owl_kent` is a photograph that stage 0 routes to `gradient`, so the
    palette bind never applied and it sewed 14 distinct cones against
    max_colors=12. Declaring it photographic applies the bind and brings it
    to budget. Preflight moves with it: the grade was F/0 driven by 12
    THREAD_MATCH_POOR findings scored on the wrong yardstick.
    """
    plain = PipelineConfig()
    declared = PipelineConfig(is_photographic=True)

    res_a = run_stages(OWL, plain)
    plan_a = plan_stitches(res_a, plain)
    res_b = run_stages(OWL, declared)
    plan_b = plan_stitches(res_b, declared)

    # Stage 0 still says gradient — this flag does not touch tier routing.
    assert res_a.design_class == res_b.design_class == "gradient"

    spools = lambda p: len({b.thread_index for b in p.blocks})
    assert spools(plan_a) > plain.max_colors, "the defect should still be visible undeclared"
    assert spools(plan_b) <= declared.max_colors, "declaring it must bring it to budget"

    grade = lambda r, p, c: run_preflight(r, p, c, image=OWL)
    rep_a, rep_b = grade(res_a, plan_a, plain), grade(res_b, plan_b, declared)
    poor = lambda rep: sum(1 for f in rep.get("findings", [])
                           if f.get("code") == "THREAD_MATCH_POOR")
    assert poor(rep_a) > 0 and poor(rep_b) == 0, \
        "the thread-match findings were the wrong yardstick, not real mismatches"
    assert rep_b["score"] > rep_a["score"]
