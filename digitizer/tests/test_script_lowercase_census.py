"""`tools/script_lowercase_census.py` -- which tagger refuses each glyph, and why.

Synthetic block capitals (`tests/test_words.py`'s helpers) plus one wide
"script word" region, so each refusal is built on purpose and the tool must
name the rule with the measured value beside the threshold OF THAT TAGGER
(the three taggers' constants differ: aspect 1.4 / 1.4 / 2.0, ink, height
bounds). The parity tests matter most: the mirror must read the same members
the shipped passes wrote, or its reasons describe a tagger that is not the
shipped one. One real fixture (becker, ~12 s) pins the wiring end to end.
"""
from __future__ import annotations

import json

import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig, threads
from digitizer_core.columns import is_lettering
from digitizer_core.textcluster import (ASPECT_RATIO_MAX, _lettering_groups,
                                        detect_text_clusters)
from digitizer_core.words import WORD_ASPECT_MAX
from tests.test_words import H, _glyph, _region, _text
from tools import script_lowercase_census as C


def _tagged(regions):
    """Run the two OLD taggers the way the pipeline does, so the regions carry
    `text_candidate` and `lettering_group` for the census to read."""
    detect_text_clusters(regions, None, chart=threads.CHART)
    for g in _lettering_groups(regions):
        for r in g:
            r.meta["lettering_group"] = True
    return regions


def _census(regions, truth=None, name="synthetic"):
    return C.census_regions(name, regions, threads.CHART, PipelineConfig(), truth)


def test_the_mirror_reads_the_same_members_as_each_shipped_tagger():
    regions = _tagged(_text("a", "HELTFU") + _text("b", "FUTHEL", y0=H * 1.4)
                      + _text("x", "HE", x0=60.0))
    res = _census(regions)
    assert res["parity"] == {"text_cluster": True, "house_group": True, "words": True}
    assert {g["shape"] for g in res["glyphs"]} >= {f"a{i}" for i in range(6)}


def test_a_wide_script_word_is_refused_by_aspect_at_each_taggers_own_ceiling():
    wide = _region("w0", box(0.0, 0.0, 3.0 * H, H))
    regions = _tagged(_text("a", "HELT") + [wide])
    traces = {"text_cluster": C.text_cluster_trace(regions, threads.CHART),
              "house_group": C.house_group_trace(regions),
              "words": C.words_trace(regions, threads.CHART)}
    ceiling = {"text_cluster": ASPECT_RATIO_MAX, "house_group": ASPECT_RATIO_MAX,
               "words": WORD_ASPECT_MAX}
    for k, t in traces.items():
        why = t.rejected["w0"]
        assert why.rule == "aspect" and why.threshold == ceiling[k], k
        assert why.value == pytest.approx(3.0)


def test_a_lone_glyph_is_refused_by_the_link_not_by_admission():
    regions = _tagged(_text("a", "HELT") + _text("z", "F", x0=60.0))
    res = _census(regions, {"lines": {"W": ["a0", "a1", "a2", "a3", "z0"]}})
    z = next(g for g in res["glyphs"] if g["shape"] == "z0")
    assert not any(z["tagged"].values()) and z["lane"] is False
    assert {k: v["rule"] for k, v in z["refused"].items()} == {
        "text_cluster": "distance", "house_group": "distance", "words": "distance"}


def test_a_rescued_glyph_goes_through_the_rescued_door_and_says_so():
    """The text cluster's first door has its own calibration (cv 0.32, ratio
    0.5); a rescued region it refuses never reaches the letter door."""
    plain = _text("a", "HELT")
    rescued = _text("r", "HELT", y0=H * 3.0)
    for r in rescued:
        r.meta["rescued_small_shape"] = True
    odd = _region("o0", box(40.0, 0.0, 50.0, 1.0))          # aspect 10: refused at admission
    odd.meta["rescued_small_shape"] = True
    regions = _tagged(plain + rescued + [odd])
    t = C.text_cluster_trace(regions, threads.CHART)
    assert sorted(s for w in t.words for s in w) == sorted(
        r.shape_id for r in regions if r.meta.get("text_candidate"))
    assert t.rejected["o0"].rule == "aspect" and "(rescued door)" in t.rejected["o0"].detail


def test_lane_verdict_matches_is_lettering_and_names_the_guard():
    cfg = PipelineConfig()
    letter = _region("l0", _glyph("H", 0.0, 0.0))
    blob = _region("b0", box(0.0, 0.0, 4.0, 4.0))
    stray = _region("s0", _glyph("H", 0.0, 0.0))
    for r in (letter, blob, stray):
        r.meta["text_candidate"] = True
    stray.meta["lettering_ink_stray"] = True
    plain = _region("p0", _glyph("H", 0.0, 0.0))
    for r in (letter, blob, stray, plain):
        assert C.lane_verdict(r, cfg)[0] == is_lettering(r, cfg)
        w = PipelineConfig(lettering_words=True)
        assert C.lane_verdict(r, w)[0] == is_lettering(r, w)
    assert C.lane_verdict(letter, cfg) == (True, None)
    assert C.lane_verdict(blob, cfg) == (False, "skip_blobs")
    assert C.lane_verdict(stray, cfg) == (False, "ink_stray")
    assert C.lane_verdict(plain, cfg) == (False, None)


def test_labels_define_the_glyphs_and_a_stale_label_set_is_read_as_unlabelled():
    regions = _tagged(_text("a", "HELT") + _text("z", "F", x0=60.0))
    truth = {"lines": {"WORD": ["a0", "a1", "a2", "a3", "z0"]}}
    res = _census(regions, truth)
    assert res["source"] == "labels" and not res["stale"]
    assert [g["line"] for g in res["glyphs"]] == ["WORD"] * 5
    assert res["truth"].count(True) == 5
    stale = _census(regions, {"lines": {"WORD": ["a0", "gone"]}})
    assert stale["stale"] and stale["source"] == "reference" and stale["truth"] is None


def test_a_tagged_region_that_is_not_a_labelled_letter_is_listed():
    regions = _tagged(_text("a", "HELT"))
    res = _census(regions, {"lines": {"WORD": ["a0", "a1", "a2"]}})
    assert [g["shape"] for g in res["tagged_not_letter"]] == ["a3"]


def test_kappa_with_a_ci_is_chance_corrected_and_seeded():
    truth = [True] * 10 + [False] * 30
    perfect, ci = C.kappa_ci(truth, list(truth), draws=200)
    assert perfect == pytest.approx(1.0) and ci[0] <= 1.0 <= ci[1] + 1e-9
    never, _ = C.kappa_ci(truth, [False] * 40, draws=200)
    assert never == pytest.approx(0.0)          # calling nothing a letter is chance, not 75%
    assert C.kappa_ci(truth, [not x for x in truth], draws=200, seed=3) == \
        C.kappa_ci(truth, [not x for x in truth], draws=200, seed=3)


def test_pooled_kappa_reads_only_labelled_fixtures():
    regions = _tagged(_text("a", "HELTFU"))
    labelled = _census(regions, {"lines": {"W": [f"a{i}" for i in range(6)]}})
    unlabelled = _census(_tagged(_text("a", "HELTFU")))
    pooled = C.pooled_kappa([labelled, unlabelled])
    assert set(pooled) == set(C.PREDICTORS)
    assert pooled["words"]["fixtures"] == ["synthetic"] and pooled["words"]["letters"] == 6
    assert C.pooled_kappa([unlabelled]) == {}


def test_the_table_and_summary_print_ascii_only():
    regions = _tagged(_text("a", "HELT") + [_region("w0", box(30.0, 0.0, 30.0 + 3.0 * H, H))])
    res = _census(regions, {"lines": {"W": ["a0", "a1", "a2", "a3", "w0"]}})
    res["width_mm"] = 80.0
    text = "\n".join(C.format_table(res) + C.format_summary([res], C.pooled_kappa([res])))
    text.encode("ascii")
    assert "aspect" in text and "w0" in text and "kappa" in text


def test_an_unknown_fixture_is_a_usage_error():
    with pytest.raises(SystemExit):
        C.main(["no_such_logo"])


def test_becker_end_to_end_the_lane_takes_every_labelled_letter():
    """The control: block caps, the one logo every tagger agrees on."""
    res = C.run(["becker"], log=lambda *_: None)[0]
    assert res["source"] == "labels" and not res["stale"]
    assert res["parity"] == {"text_cluster": True, "house_group": True, "words": True}
    assert len(res["glyphs"]) == 11
    assert all(g["lane"] and all(g["tagged"].values()) for g in res["glyphs"])
    assert res["tagged_not_letter"] == []
    json.dumps({k: v for k, v in res.items() if k not in ("scored", "truth", "pred")})
