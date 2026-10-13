"""`tools/word_tagger_trace.py` -- the tagger's refusals, named.

Synthetic block capitals (`tests/test_words.py`'s helpers) so every rule that
can turn a glyph away is built on purpose and the tool must name that rule
with the measured value beside its threshold. The parity test is the one
that matters most: the trace must read the same words `detect_words` does,
or its reasons describe a tagger that is not the shipped one.
"""
from __future__ import annotations

import json

import pytest
from shapely.affinity import scale as shp_scale
from shapely.geometry import box

from digitizer_core import threads
from digitizer_core.textcluster import LETTER_HEIGHT_RATIO, PROXIMITY_HEIGHT_MULT
from digitizer_core.words import WORD_ASPECT_MAX, detect_words
from tests.test_words import H, _glyph, _region, _rope, _text
from tools import word_tagger_trace as T


def _ids_of(words):
    return sorted(sorted(r.shape_id for r in w.members) for w in words)


def test_parity_with_detect_words():
    regions = (_text("t", "HELTFU") + _text("b", "FUTHEL", y0=H * 1.4)
               + _rope("r", 12, -4, 15) + _text("x", "HE", x0=40.0))
    t = T.trace(regions, threads.CHART)
    assert sorted(t.words) == _ids_of(detect_words(regions, chart=threads.CHART))


def test_a_far_glyph_is_refused_by_distance_with_the_measured_reach():
    regions = _text("a", "HELT") + _text("z", "F", x0=60.0)
    t = T.trace(regions, threads.CHART)
    assert t.words == [["a0", "a1", "a2", "a3"]]
    w = T.explain_missing("z0", ["a0", "a1", "a2", "a3"], t, threads.CHART)
    assert w.rule == "distance"
    assert w.threshold == pytest.approx(PROXIMITY_HEIGHT_MULT * H, rel=0.05)
    assert w.value > w.threshold


def test_a_small_glyph_is_refused_by_height_ratio():
    small = _region("s0", shp_scale(_glyph("F", 15.2, 0.0), 0.6, 0.6, origin=(15.2, 0.0)))
    regions = _text("a", "HELT") + [small]
    t = T.trace(regions, threads.CHART)
    w = T.explain_missing("s0", ["a0", "a1", "a2", "a3"], t, threads.CHART)
    assert w.rule == "height_ratio"
    assert w.threshold == LETTER_HEIGHT_RATIO
    assert w.value < LETTER_HEIGHT_RATIO


def test_a_far_ink_is_refused_by_ink():
    chart = threads.CHART
    far = next(j for j in range(1, 50) if float(chart.delta_e(0, j)) > 20.0)
    regions = _text("a", "HELT", ink=0) + [_region("z0", _glyph("F", 4 * 3.8, 0.0), far)]
    t = T.trace(regions, chart)
    w = T.explain_missing("z0", ["a0", "a1", "a2", "a3"], t, chart)
    assert w.rule == "ink" and w.threshold == 20.0 and w.value > 20.0


def test_a_wide_region_is_refused_at_admission_by_aspect():
    wide = _region("w0", box(0.0, 0.0, 3.0 * H, H))
    t = T.trace(_text("a", "HELT") + [wide], threads.CHART)
    why = t.rejected["w0"]
    assert why.rule == "aspect" and why.threshold == WORD_ASPECT_MAX and why.value == pytest.approx(3.0)


def test_a_sub_millimetre_region_is_refused_by_height_min():
    tiny = _region("t0", box(0.0, 0.0, 0.3, 0.6))
    t = T.trace([tiny], threads.CHART)
    assert t.rejected["t0"].rule == "height_min"
    assert t.rejected["t0"].value == pytest.approx(0.6)


def test_a_pair_is_a_small_component_and_names_its_size():
    t = T.trace(_text("a", "HE"), threads.CHART)
    assert t.words == []
    assert t.fate["a0"].rule == "small_component" and t.fate["a0"].value == 2


def test_a_rope_member_is_lost_to_the_pattern_test():
    regions = _text("a", "HELTFU") + _rope("r", 14, 0.0, 6.0)
    t = T.trace(regions, threads.CHART)
    assert [t.fate[f"r{i:02d}"].rule for i in (3, 4)] == ["pattern", "pattern"]


def test_carry_maps_by_scaled_position_one_to_one_and_none_when_absent():
    ref = _text("a", "HELT")
    at50 = [_region(f"n{i}", shp_scale(r.polygon, 0.5, 0.5, origin=(0, 0)))
            for i, r in enumerate(ref[:3])]          # the fourth is gone at this size
    m = T.carry(ref, 100.0, at50, 50.0)
    assert m == {"a0": "n0", "a1": "n1", "a2": "n2", "a3": None}


def test_report_rows_count_expected_found_and_name_each_missing_glyph():
    regions = _text("a", "HELT") + _text("z", "F", x0=60.0)
    t = T.trace(regions, threads.CHART)
    lines = {"WORD": ["a0", "a1", "a2", "a3", "z0", "gone"]}
    mapping = {s: s for s in ("a0", "a1", "a2", "a3", "z0")} | {"gone": None}
    (row,) = T.report_size(lines, mapping, t, threads.CHART)
    assert (row["expected"], row["found"], row["members"]) == (6, 4, 4)
    assert {m["ref"]: m["rule"] for m in row["missing"]} == {"z0": "distance", "gone": "no_region"}
    assert T.tally([row]) == {"distance": 1, "no_region": 1}


def test_expected_lines_reads_labels_when_present_and_words_otherwise():
    truth = json.loads(T.TRUTH.read_text())["fixtures"]["becker"]["lines"]
    ids = [s for v in truth.values() for s in v]
    regs = [_region(s, box(i * 5.0, 0.0, i * 5.0 + 3.0, 4.0)) for i, s in enumerate(ids)]
    lines, source = T.expected_lines("becker", regs, threads.CHART)
    assert source == "labels" and lines == truth
    lines, source = T.expected_lines("golden_tee", _text("a", "HELT"), threads.CHART)
    assert source == "reference" and list(lines.values()) == [["a0", "a1", "a2", "a3"]]
