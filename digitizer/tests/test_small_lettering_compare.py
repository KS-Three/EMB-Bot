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
    assert slc.ARM_ORDER == ["main", "sk073", "sk100", "true", "both073", "both100", "switch", "ring"]
    for name, (overrides, _label) in slc.ARMS.items():
        PipelineConfig(**overrides)                 # every key is a real field, every value accepted
    # the switch is ON by default since 2026-10-14: main is the pre-flip engine
    assert slc.OFF == {"small_text_true_size": False}
    assert slc.ARMS["main"][0] == slc.OFF
    # #911 + #914, MASTER_SCOPE 56: restore 3.0, bean 0.4, pitch 0.45, serif 0.45
    assert slc.TRUE_SIZE == {"small_text_restore_mm": 3.0, "bean_letter_max_stroke_mm": 0.4,
                             "bean_letter_stitch_mm": 0.45, "bean_letter_serif_mm": 0.45}
    assert slc.ARMS["sk073"][0] == {**slc.OFF, "small_lettering_skeleton": True,
                                    "small_lettering_skeleton_floor_mm": 0.73}
    assert slc.ARMS["sk100"][0] == {**slc.OFF, "small_lettering_skeleton": True}   # the default floor
    # the small-glyph second try (#936) is the config's own default, not an arm setting
    assert "small_lettering_skeleton_small_floor_mm" not in slc.ARMS["sk073"][0]
    assert slc.ARMS["true"][0] == {**slc.OFF, **slc.TRUE_SIZE}
    assert slc.ARMS["both073"][0] == {**slc.TRUE_SIZE, **slc.ARMS["sk073"][0]}
    assert slc.ARMS["both100"][0] == {**slc.TRUE_SIZE, **slc.ARMS["sk100"][0]}
    # the switch arm is the shipped default
    assert PipelineConfig(**slc.ARMS["switch"][0]) == PipelineConfig()
    assert slc.FIXTURES == {"hat81": 81.0, "hat925": 92.5}
    # the one switch fills the true-size values, bean stroke raised to 0.5
    sw = PipelineConfig(**slc.ARMS["switch"][0])
    assert {k: getattr(sw, k) for k in slc.TRUE_SIZE} == {**slc.TRUE_SIZE,
                                                          "bean_letter_max_stroke_mm": 0.5}


def test_the_arms_change_only_the_two_options_and_nothing_else():
    base = PipelineConfig(**slc.ARMS["main"][0])
    keys = {"small_lettering_skeleton", "small_lettering_skeleton_floor_mm", *slc.TRUE_SIZE,
            "small_text_true_size", "ink_ground_ring_mm"}
    for name, (overrides, _l) in slc.ARMS.items():
        assert set(overrides) <= keys, name
    # the options themselves are OFF in the main arm every other arm is priced against
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


# --- the corpus mode (what the true-size arm costs outside Fremont) ------------------

def _ccell(design, arm, st=1000, tr=10, md5="a", digests=None, au=0.0, bare=1.0, leg=None, ocr=(2, 4)):
    words = {} if leg is None else {"w": {"legibility": leg, "ocr": {"recovered": ocr[0], "read": ocr[1],
                                                                       "ci95": [0.1, 0.9]}}}
    return {"design": design, "arm": arm, "stitches": st, "trims": tr, "md5": md5,
            "shape_digests": digests or {"s1": "x", "s2": "y"}, "uncovered_total_mm2": au,
            "bare_mm2": bare, "words": words}


def test_corpus_designs_are_the_nine_logos_the_hat_renders_and_the_small_print_set():
    specs = slc.corpus_designs()
    names = list(specs)
    logos = [n for n, s in specs.items() if s["kind"] == "logo"]
    assert len(logos) == 9 and "thermal" not in logos           # the byte-duplicate runs once
    assert {"becker", "tires", "enthusiast", "fremont", "bridge", "golden_tee", "gaulke", "drone",
            "screenshot"} == set(logos)
    assert names[9:11] == ["fremont_hat81", "fremont_hat925"]
    assert [n for n in names if n.startswith("sp_")] == [
        f"sp_{fx}_{c:g}" for fx in slc.SMALL_PRINT_CORPUS for c in slc.SMALL_PRINT_CAPS]
    assert specs["fremont_hat925"]["width_mm"] == 92.5
    assert specs["becker"]["cfg"]["max_colors"] == 6            # the Studio's six
    from tools import glyph_legibility as gl
    for case in slc.LEGIBILITY_CASE.values():
        assert case in gl.CASES
    assert slc.CORPUS_ARMS == ["main", "true", "sk073", "switch"]
    assert all(a in slc.ARMS for a in slc.CORPUS_ARMS)


def test_changed_shapes_counts_differing_added_and_retired_ids():
    base = {"a": "1", "b": "2", "c": "3"}
    assert slc.changed_shapes(base, dict(base)) == 0
    assert slc.changed_shapes(base, {**base, "b": "9"}) == 1
    assert slc.changed_shapes(base, {"a": "1", "b": "2", "d": "4"}) == 2       # c retired, d added


def test_ocr_total_and_mean_legibility_skip_what_was_not_read():
    words = {"a": {"legibility": 0.6, "ocr": {"recovered": 1, "read": 2}},
             "b": {"legibility": 0.2, "ocr": {"recovered": None, "read": None}},
             "c": {"legibility": None, "ocr": {"note": "OCR UNAVAILABLE"}}}
    assert slc.ocr_total(words) == (1, 2)
    assert slc.mean_legibility(words) == pytest.approx(0.4)
    assert slc.mean_legibility({}) is None


def test_corpus_tables_and_the_worst_line_per_arm():
    cells = {"becker": {"main": _ccell("becker", "main", leg=0.6),
                        "true": _ccell("becker", "true", st=1300, tr=12, md5="b", au=2.5, bare=3.0, leg=0.4,
                                       digests={"s1": "x", "s2": "z"}),
                        "sk073": _ccell("becker", "sk073", leg=0.6)},
             "drone": {"main": _ccell("drone", "main"), "true": _ccell("drone", "true"),
                       "sk073": _ccell("drone", "sk073", st=900, tr=8, md5="c")}}
    rows = {(r["design"], r["arm"]): r for r in slc.corpus_deltas(cells)}
    assert rows[("becker", "true")]["identical"] is False and rows[("becker", "true")]["changed"] == 1
    assert rows[("becker", "true")]["d_au"] == 2.5 and rows[("becker", "true")]["d_trims"] == 2
    assert rows[("becker", "true")]["d_leg"] == {"w": -0.2}
    assert rows[("becker", "sk073")]["identical"] and rows[("drone", "true")]["identical"]
    md = slc.corpus_table(cells)
    assert "| becker | 1,000 / 10 | 1,300 / 12 | NO | 1 | +2.50 | +2.00 | 1,000 / 10 | yes | 0 | +0.00 | +0.00 |" in md
    assert "| drone | 1,000 / 10 | 1,000 / 10 | yes | 0 |" in md
    leg = slc.corpus_legibility_table(cells)
    assert "| becker | true | 1 | 0.400 | w 0.400 | 2/4 [0.15-0.85] |" in leg
    assert "drone" not in leg                                   # no case reads it
    lines = slc.worst_regressions(cells)
    assert lines[0].startswith("true size changed 1 of 2 designs")
    assert "new uncovered artwork: worst +2.50 mm2 (becker)" in lines[0]
    assert "legibility: worst -0.200 (becker w)" in lines[0]
    assert lines[1].startswith("skeleton @ 0.73 changed 1 of 2 designs")
    assert "new uncovered artwork: no increase anywhere" in lines[1]
    assert "stitches: no increase anywhere" in lines[1]


def test_corpus_sheet_stacks_the_arms_over_the_changed_box(tmp_path):
    cells, side = tmp_path / "cells", tmp_path / "side"
    cells.mkdir()
    side.mkdir()
    run = [{"x": int(i * 3), "y": 100, "type": "stitch"} for i in range(60)]
    for arm in ("main", "true"):
        (cells / f"corpus_demo__{arm}.json").write_text(json.dumps(_ccell("demo", arm)))
        (side / f"corpus_demo__{arm}_design.json").write_text(json.dumps(
            {"stitches": run, "colors": [{"r": 10, "g": 20, "b": 200}]}))
    (side / "corpus_demo__true_changed.json").write_text(json.dumps(
        {"design": "demo", "arm": "true", "box_mm": [0.0, -15.0, 10.0, -5.0], "changed_shapes": []}))
    path = slc.corpus_sheet("demo", cells, side)
    assert path == side / "corpus_demo.png" and path.exists()
    import cv2
    two = cv2.imread(str(path)).shape[0]
    (side / "corpus_demo__true_design.json").unlink()
    one = cv2.imread(str(slc.corpus_sheet("demo", cells, side))).shape[0]
    assert two > one                                            # a second arm adds a row
    assert slc.corpus_sheet("nothing", cells, side) is None


def test_small_print_table_reads_the_censuses_counters():
    c = _ccell("sp_synthetic_3", "true")
    c["sp"] = {"counters": 6, "counters_shut": 2, "counter_open": 0.5, "covered": 0.93, "spill": None}
    md = slc.corpus_small_print_table({"sp_synthetic_3": {"true": c, "main": _ccell("sp_synthetic_3", "main")}})
    assert "| sp_synthetic_3 | true | 2 / 6 | 0.50 | 0.93 | - |" in md
    assert "main" not in md                                     # a cell with no `sp` read has no row


def test_saved_corpus_cells_reprint_without_digitizing(tmp_path, capsys):
    for arm in slc.CORPUS_ARMS:
        (tmp_path / f"corpus_becker__{arm}.json").write_text(json.dumps(_ccell("becker", arm)))
    assert list(slc.load_cells(tmp_path)) == []                 # the Fremont loader leaves them alone
    assert set(slc.load_corpus(tmp_path)["becker"]) == set(slc.CORPUS_ARMS)
    assert slc.main(["--corpus-table", "--out", str(tmp_path)]) == 0
    assert "| becker | 1,000 / 10 |" in capsys.readouterr().out
