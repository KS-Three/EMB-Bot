"""`tools/stage0_photo_gate.py` — the photo-gate readings and margins.

The instrument restates the SHIPPED answer beside its own (DOCTRINE
2026-09-11: an instrument that reconstructs its input must print the engine's
verdict next to it), so these tests pin that restatement, the margin
arithmetic on a hand-built row list, and the width ladder's shape. Every
number is a reading (ROADMAP gate 4).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.stage0_classify import classify
from tools import stage0_photo_gate as pg

HERE = Path(__file__).resolve().parent
TESTDATA = HERE.parent / "testdata"
PHOTO_DIR = TESTDATA / "photo"


def test_rows_restate_the_engines_class_on_both_arms():
    paths = [PHOTO_DIR / "owl_kent.jpg", TESTDATA / "logo_script_tires.png",
             PHOTO_DIR / "drone_render.png"]
    rows = pg.rows(paths, PipelineConfig(target_width_mm=80.0))
    assert [r["slug"] for r in rows] == ["photo/owl_kent.jpg", "logo_script_tires.png",
                                         "photo/drone_render.png"]
    for r, p in zip(rows, paths):
        on = classify(p, PipelineConfig(target_width_mm=80.0))
        off = classify(p, PipelineConfig(target_width_mm=80.0, stage0_texture_gate=False))
        assert r["class_on"] == on.class_ and r["class_off"] == off.class_
        assert r["route"] == on.signals["photo_route"]
        assert r["texture_frac"] == on.signals["texture_frac"]
        assert r["kind"] == "fixture"
    assert rows[0]["cutout"] is False and rows[2]["cutout"] is True


def test_margins_on_a_hand_built_row_list():
    rows = [
        {"slug": "a", "kind": "photo", "cutout": False, "texture_frac": 0.30, "two_tone_mass": 0.40},
        {"slug": "b", "kind": "photo", "cutout": False, "texture_frac": 0.25, "two_tone_mass": 0.76},
        {"slug": "c", "kind": "logo", "cutout": False, "texture_frac": 0.09, "two_tone_mass": 0.97},
        {"slug": "d", "kind": "logo", "cutout": False, "texture_frac": 0.05, "two_tone_mass": 0.70},
        {"slug": "e", "kind": "logo", "cutout": True, "texture_frac": 0.80, "two_tone_mass": 0.30},
        {"slug": "f", "kind": "photo-of-logo", "cutout": False, "texture_frac": 0.90, "two_tone_mass": 0.40},
    ]
    m = pg.margins(rows)
    assert m["photo_texture_min"] == (0.25, "b")
    assert m["graphic_texture_max"] == (0.09, "c")     # the cut-out row is not in the margin
    assert m["photo_two_tone_max"] == (0.76, "b")
    assert m["texture_gap"] == pytest.approx(0.25 - 0.09)
    assert m["n_photo"] == 2 and m["n_graphic"] == 2
    assert m["n_photo_of_logo"] == 1      # printed, in neither margin


def test_the_photographed_graphics_are_labelled_from_the_corpus_kind():
    kinds = pg.corpus_kinds([{"slug": "halftone_dots", "kind": "logo"}, {"slug": "low_poly", "kind": "logo"},
                             {"slug": "bw_street", "kind": "photo"}])
    assert kinds == {"halftone_dots": "photo-of-logo", "low_poly": "logo", "bw_street": "photo"}


def test_ladder_reads_below_the_native_width_only():
    out = pg.ladder(TESTDATA / "logo_whitebg.png", (250, 400, 640, 2000))
    assert out["native_w"] == 800
    assert set(out["widths"]) == {250, 400, 640, 2000}
    assert out["widths"][2000] is None
    for w in (250, 400, 640):
        assert 0.0 <= out["widths"][w]["texture_frac"] <= 1.0
        assert 0.0 <= out["widths"][w]["two_tone_mass"] <= 1.0


def test_cli_runs_on_the_fixtures(capsys):
    assert pg.main(["--fixtures-only"]) == 0
    text = capsys.readouterr().out
    assert "photo/owl_kent.jpg" in text and "TEXTURE_PHOTO_MIN" in text
    assert "photo texture min" in text


def test_the_repo_art_logos_sit_in_the_fixture_margin():
    """The graphic-side margin the spec quotes (0.066, `logo_toat_beanie`) was
    read on the repo's small real art under `testdata/art/`, which the
    corpus (nothing under 500 px) cannot show. The instrument has to carry
    those files, as `logo`, under an `art/` slug, or it cannot re-read the
    number that sites the gate (review 2026-10-28, Important 1)."""
    art = sorted(p for p in (TESTDATA / "art").glob("logo_*.png"))
    assert len(art) == 6
    for p in art:
        assert pg._slug(p) == f"art/{p.name}"
        assert pg.FIXTURES.get(f"art/{p.name}") == "logo"
    paths = [TESTDATA / rel for rel in pg.FIXTURES if (TESTDATA / rel).exists()]
    rows = pg.rows(paths, PipelineConfig(target_width_mm=80.0), dict(pg.FIXTURES))
    m = pg.margins(rows)
    value, slug = m["graphic_texture_max"]
    assert slug == "art/logo_toat_beanie.png"
    assert value == pytest.approx(0.066, abs=0.005)
