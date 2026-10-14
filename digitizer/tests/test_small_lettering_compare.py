"""`tools/small_lettering_compare.py`: small lettering, head to head, on one
render set (MASTER_SCOPE "Waiting on Kent" 56). The tool digitizes Hotel
Fremont (minutes per cell), so these pin what does not need a digitize: the
arm table (the values #911/#914/#913 name, valid config fields), the
counters-open derivation, the table the PR prints, the spy that restores
stage 7, and that a saved cell re-prints its table without a run.
"""
from __future__ import annotations

import json

import pytest

from digitizer_core import PipelineConfig
from tools import small_lettering_compare as slc


def _glyph(openable, spurious, counters, **kw):
    return {"src_counters_openable": openable, "sewn_counters_spurious": spurious,
            "counters": counters, **kw}


def _word(leg=0.5, space=0.2, ctr=(1, 2), ocr=(1, 2), st=100, tr=3, built=(0, 0, 3)):
    return {"glyphs": 3, "legibility": leg, "legibility_space": space, "worst_glyph": 0.1,
            "counters_open": list(ctr),
            "ocr": {"recovered": ocr[0], "read": ocr[1],
                    "ci95": [0.1, 0.9] if ocr[1] else None},
            "stitches": st, "trims": tr, "box_mm": [0, 0, 1, 1],
            "built": dict(zip(("skeleton", "bean", "outline"), built))}


def _cell(fx, arm, **kw):
    return {"fixture": fx, "arm": arm, "stitches": 15625, "trims": 47,
            "words": {w: _word(**kw) for w in slc.WORDS}}


def test_arms_are_valid_config_and_carry_the_values_the_scope_names():
    assert slc.ARM_ORDER == ["main", "sk073", "sk100", "true", "both073", "both100"]
    for name, (overrides, _label) in slc.ARMS.items():
        PipelineConfig(**overrides)                 # every key is a real field, every value accepted
    assert slc.ARMS["main"][0] == {}
    # #911 + #914, MASTER_SCOPE 56: restore 3.0, bean 0.4, pitch 0.45, serif 0.45
    assert slc.TRUE_SIZE == {"small_text_restore_mm": 3.0, "bean_letter_max_stroke_mm": 0.4,
                             "bean_letter_stitch_mm": 0.45, "bean_letter_serif_mm": 0.45}
    assert slc.ARMS["sk073"][0] == {"small_lettering_skeleton": True,
                                    "small_lettering_skeleton_floor_mm": 0.73}
    assert slc.ARMS["sk100"][0] == {"small_lettering_skeleton": True}      # the default floor
    assert slc.ARMS["true"][0] == slc.TRUE_SIZE
    assert slc.ARMS["both073"][0] == {**slc.TRUE_SIZE, **slc.ARMS["sk073"][0]}
    assert slc.ARMS["both100"][0] == {**slc.TRUE_SIZE, **slc.ARMS["sk100"][0]}
    assert slc.FIXTURES == {"hat81": 81.0, "hat925": 92.5}


def test_the_arms_change_only_the_two_options_and_nothing_else():
    base = PipelineConfig()
    keys = {"small_lettering_skeleton", "small_lettering_skeleton_floor_mm", *slc.TRUE_SIZE}
    for name, (overrides, _l) in slc.ARMS.items():
        assert set(overrides) <= keys, name
    # the options themselves are OFF in the config the arms start from
    assert not base.small_lettering_skeleton and base.small_text_restore_mm is None
    assert base.bean_letter_max_stroke_mm is None


def test_counters_open_is_matched_over_what_a_reader_can_see():
    # an A whose counter is shut: 1 openable, 0 matched, 0 spurious
    assert slc.counters_open([_glyph(1, 0, 0.0)]) == (0, 1)
    # an 8 keeping one of two: score = 1 / (2 + 0)
    assert slc.counters_open([_glyph(2, 0, 0.5)]) == (1, 2)
    # a spurious hole in the thread lowers the score but not the count of source counters
    assert slc.counters_open([_glyph(1, 1, 0.5)]) == (1, 1)
    # a letter with no counters adds nothing; sums across the word
    assert slc.counters_open([_glyph(0, 0, 1.0), _glyph(1, 0, 1.0), _glyph(1, 0, 0.0)]) == (1, 2)
    assert slc.counters_open([]) == (0, 0)


def test_word_row_reads_ocr_or_says_it_is_unavailable():
    s = {"glyphs": 3, "legibility": 0.614, "legibility_space": 0.1, "worst_glyph": 0.0,
         "ocr": {"read_on_source": 3, "recovered": 1, "rate": 0.333, "ci95": [0.061, 0.792]}}
    r = slc.word_row(s, [_glyph(1, 0, 0.0)])
    assert r["ocr"] == {"recovered": 1, "read": 3, "ci95": [0.061, 0.792]}
    assert r["counters_open"] == [0, 1]
    assert slc.fmt_ocr(r["ocr"]) == "1/3 [0.06-0.79]"
    r = slc.word_row({**s, "ocr": "OCR UNAVAILABLE"}, [])
    assert r["ocr"]["recovered"] is None and slc.fmt_ocr(r["ocr"]) == "n/a"


def test_wilson_is_the_instruments_own():
    lo, hi = slc.wilson(1, 2)
    assert (round(lo, 3), round(hi, 3)) == (0.095, 0.905)      # the pro's EST row in the PR body
    assert slc.wilson(0, 0) is None


def test_built_as_ranks_skeleton_over_bean_over_outline():
    sk = {"a": {"empty": False}, "b": {"empty": True}}
    bean = {"c": {"empty": False}, "b": {"empty": False}}
    assert slc.built_as(["a"], sk, bean) == "skeleton"
    assert slc.built_as(["b"], sk, bean) == "bean"          # skeleton declined it, bean sewed it
    assert slc.built_as(["c"], sk, bean) == "bean"
    assert slc.built_as(["z"], sk, bean) == "outline"
    assert slc.built_as([], sk, bean) == "outline"


def test_table_prints_every_arm_every_word_and_the_pro_beside_925():
    cells = {f"{fx}__{a}": _cell(fx, a) for fx in slc.FIXTURES for a in slc.ARM_ORDER}
    pro = {"words": {w: _word(st=None, tr=None) for w in slc.WORDS}}
    cells["pro_hat"], cells["pro_patch"] = pro, pro
    md = slc.table(cells)
    for fx, width in slc.FIXTURES.items():
        assert f"Hotel Fremont, Hat, {width:g} mm" in md
    for w in slc.WORDS:
        assert f"**{slc.WORD_TITLE[w]}**" in md
    assert md.count("| both073 |") == 2 * (1 + len(slc.WORDS))      # summary row + a row per word, two fixtures
    assert "pro_hat (reference)" in md and "pro_patch (reference)" in md
    assert md.index("pro_hat (reference)") > md.index("Hat, 92.5 mm")   # only at the pro's size
    assert "| 0.500 | 0.200 | 1 of 2 | 1/2 [0.10-0.90] | 100 | 3 |" in md
    assert "| 0.500 | 0.200 | 1 of 2 | 1/2 [0.10-0.90] | - | - |" in md   # the pro has no split


def test_table_skips_a_fixture_with_no_cells_and_a_word_with_no_glyphs():
    cells = {"hat81__main": _cell("hat81", "main")}
    cells["hat81__main"]["words"]["est"] = {"legibility": None, "legibility_space": None,
                                            "counters_open": [0, 0], "ocr": {"recovered": None},
                                            "built": {"skeleton": 0, "bean": 0, "outline": 0}}
    md = slc.table(cells)
    assert "92.5 mm" not in md
    assert "no glyphs read" in md


def test_pick_table_sums_the_ocr_over_all_four_words_with_one_interval():
    cells = {"hat81__main": _cell("hat81", "main", ocr=(1, 2)), "hat81__true": _cell("hat81", "true", ocr=(2, 2))}
    md = slc.pick_table(cells)
    assert "| 81 mm | main | 15,625 | 47 | 0.50 / 0.50 / 0.50 / 0.50 | 4/8 [0.22-0.78] |" in md
    assert "| 81 mm | true | 15,625 | 47 | 0.50 / 0.50 / 0.50 / 0.50 | 8/8 [0.68-1.00] |" in md


def test_spy_tiers_records_and_restores_stage_7():
    from digitizer_core import stage7_sequence as s7
    real = (s7.skeleton_letter_runs, s7.bean_letter)
    sk, bean = {}, {}
    with slc.spy_tiers(sk, bean):
        assert (s7.skeleton_letter_runs, s7.bean_letter) != real
    assert (s7.skeleton_letter_runs, s7.bean_letter) == real
    with pytest.raises(RuntimeError):
        with slc.spy_tiers(sk, bean):
            raise RuntimeError
    assert (s7.skeleton_letter_runs, s7.bean_letter) == real      # restored on an error too


def test_saved_cells_reprint_without_digitizing(tmp_path):
    (tmp_path / "hat81__main.json").write_text(json.dumps(_cell("hat81", "main")))
    (tmp_path / "hat81__main_design.json").write_text(json.dumps({"stitches": [], "colors": []}))
    (tmp_path / "unrelated.json").write_text(json.dumps({"x": 1}))
    cells = slc.load_cells(tmp_path)
    assert list(cells) == ["hat81__main"]
    assert "Hotel Fremont, Hat, 81 mm" in slc.table(cells)
    assert slc.main(["--table", "--out", str(tmp_path)]) == 0
