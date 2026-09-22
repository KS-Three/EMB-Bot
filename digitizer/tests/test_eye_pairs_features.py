import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import analysis as an  # noqa: E402
from tools.eye_pairs import features as ft  # noqa: E402


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    img = np.full((160, 240, 3), 255, np.uint8)
    cv2.rectangle(img, (30, 40), (110, 120), (0, 0, 0), -1)
    cv2.circle(img, (170, 80), 35, (0, 0, 200), -1)
    path = tmp_path_factory.mktemp("feat") / "tiny.png"
    cv2.imwrite(str(path), img)
    return path


@pytest.fixture(scope="module")
def held(tiny):
    cfg = ft.base_cfg(40.0, "left_chest")
    return (cfg, *ft.digitize_once(tiny, cfg))


def test_base_cfg_is_the_studio_config():
    cfg = ft.base_cfg(92.5, "patch", satin_per_stroke=True)
    assert (cfg.target_width_mm, cfg.garment_id, cfg.max_colors) == (92.5, "patch", 6)
    assert cfg.satin_per_stroke is True


def test_every_analysis_metric_is_produced_and_json_safe(tiny, held):
    cfg, gen, result, plan, design = held
    row = ft.features_full(tiny, cfg, gen, result, plan, design)
    assert set(an.METRICS) <= set(row)
    json.dumps(row)                       # numpy scalars would raise here
    assert row["stitches"] == plan.stats.stitch_count
    assert isinstance(row["refusals"], dict) and isinstance(row["notes"], dict)


def test_design_only_is_a_subset_that_never_touches_the_engine(tiny, held, monkeypatch):
    _cfg, _gen, _result, _plan, design = held

    def boom(*_a, **_k):
        raise AssertionError("the design-only path must not digitize")

    monkeypatch.setattr(ft, "build_generation", boom)
    row = ft.features_design_only(tiny, design)
    assert set(ft.DESIGN_ONLY_METRICS) <= set(row)
    assert "artfid" not in row and "preflight_raw_score" not in row
    json.dumps(row)


def test_the_two_paths_agree_on_what_they_share(tiny, held):
    cfg, gen, result, plan, design = held
    full = ft.features_full(tiny, cfg, gen, result, plan, design)
    only = ft.features_design_only(tiny, design)
    for m in ft.DESIGN_ONLY_METRICS:
        assert full[m] == only[m], m


def test_a_missing_tesseract_reads_null_not_a_crash(tiny, held, monkeypatch):
    cfg, gen, result, plan, design = held

    def no_ocr(*_a, **_k):
        raise RuntimeError("tesseract is not installed")

    # A box without the binary is BOTH of these at once. Patching `measure`
    # alone is not that box: where tesseract IS installed (CI), preflight's
    # own legibility check calls the same module-level `measure`, and the
    # raise escapes `run_preflight` instead of reaching the guard under test.
    # That is how this test went red on PR #506's digitizer job (2026-09-18)
    # while passing on Kent's machine, which has no tesseract.
    monkeypatch.setattr(ft.core_legibility, "tesseract_available", lambda: False)
    monkeypatch.setattr(ft.core_legibility, "measure", no_ocr)
    row = ft.features_full(tiny, cfg, gen, result, plan, design)
    assert row["legibility"] is None
    assert "RuntimeError" in row["notes"]["legibility"]


def test_the_registration_search_runs_once_per_arm(tiny, held, monkeypatch):
    """Review finding 9 (2026-09-17): features_design_only registered the
    fields, then each split instrument registered the same fields again —
    three 441-point grid searches per arm, 0.4-3.9 s each at real sizes."""
    import tools.artfidelity_self as afs
    import tools.dropped_elements as de
    import tools.edge_smoothness as es
    cfg, gen, result, plan, design = held
    calls = []
    real = afs.register

    def counting(*a, **k):
        calls.append(1)
        return real(*a, **k)

    for mod in (afs, de, es):
        monkeypatch.setattr(mod, "register", counting)
    ft.features_full(tiny, cfg, gen, result, plan, design)
    assert len(calls) == 1


def test_artfid_is_the_instruments_own_number(tiny, held):
    """Review finding 8 (2026-09-17): artfid was recomposed by hand from
    4-dp components and rounded to 2 dp, where score_image rounds once to
    1 dp from raw values; and --verify never checked it."""
    from tools.artfidelity_self import score_image
    cfg, gen, result, plan, design = held
    row = ft.features_full(tiny, cfg, gen, result, plan, design)
    theirs = score_image(tiny, cfg)
    assert row["artfid"] == theirs["artfid"]
    assert row["artfid"] == round(row["artfid"], 1)
    assert row["refusals"].get("artfid") == theirs["refusal"]


def test_an_ink_refusal_marks_every_ink_based_metric(tiny, held, monkeypatch):
    import tools.artfidelity_self as afs
    _cfg, _gen, _result, _plan, design = held
    # The ladder lives in ONE place now; patch it there.
    monkeypatch.setattr(afs, "ink_is_ambiguous", lambda _p: True)
    row = ft.features_design_only(tiny, design)
    assert row["ragged_mm"] is not None            # the value is KEPT
    for m in ft.INK_METRICS:
        if m in row:
            assert "ambiguous" in row["refusals"][m]
