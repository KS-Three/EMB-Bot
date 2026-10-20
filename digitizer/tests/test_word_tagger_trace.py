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
from digitizer_core import words as W
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


# --- the census -------------------------------------------------------------

def test_a_fused_pair_is_named_merged_with_the_rule_that_refused_the_host():
    ref = _text("a", "HELT")
    # at half the size the first three letters stand alone and the fourth is
    # fused with a neighbour into one box wider than the glyph limit
    k = 0.5
    small = [_region(f"n{i}", shp_scale(r.polygon, k, k, origin=(0, 0))) for i, r in enumerate(ref[:3])]
    x0, y0, x1, y1 = ref[3].polygon.bounds
    fused = _region("f0", box(x0 * k, y0 * k, x1 * k + 3.0 * H * k, y1 * k))
    regions = small + [fused]
    t = T.trace(regions, threads.CHART)
    assert t.rejected["f0"].rule == "aspect"
    m = T.carry(ref, 100.0, regions, 50.0)
    ab = T.absorbers(ref, 100.0, regions, 50.0, m)
    (row,) = T.report_size({"WORD": ["a0", "a1", "a2", "a3"]}, m, t, threads.CHART, ab)
    if m["a3"] is None:                       # the carry gave the fused box to nobody
        assert ab == {"a3": "f0"}
        assert [x["rule"] for x in row["missing"]] == ["merged>aspect"]
    else:                                     # or to the fourth glyph, refused at admission
        assert [x["rule"] for x in row["missing"]] == ["aspect"]


def _far_ink(chart):
    return next(j for j in range(1, 50) if float(chart.delta_e(0, j)) > 20.0)


def test_pair_rescue_completes_a_strict_pair_with_a_relaxed_third_and_only_that():
    chart = threads.CHART
    far = _far_ink(chart)
    base = T.base_rules()
    relaxed = T.replace(base, ink_de=200.0)
    pair_plus_far = _text("a", "HE", ink=0) + [_region("z0", _glyph("L", 2 * 3.8, 0.0), far)]
    assert T.trace(pair_plus_far, chart).words == []                       # shipped: no word
    t = T.trace(pair_plus_far, chart, rescue=relaxed)
    assert t.words == [["a0", "a1", "z0"]]
    # three glyphs that each fail the shipped ink test against everything have no strict
    # pair to hang from: the relaxed rule alone seeds nothing
    inks = [0]
    for j in range(1, 50):
        if all(float(chart.delta_e(i, j)) > 20.0 for i in inks):
            inks.append(j)
        if len(inks) == 3:
            break
    assert len(inks) == 3
    scattered = [_region(f"s{i}", _glyph("HEL"[i], i * 3.8, 0.0), inks[i]) for i in range(3)]
    far_pairwise = T.trace(scattered, chart, rescue=relaxed)
    assert far_pairwise.words == []
    # and a component that already holds three is not extended by a relaxed glyph
    full = _text("a", "HEL", ink=0) + [_region("z0", _glyph("T", 3 * 3.8, 0.0), far)]
    assert T.trace(full, chart, rescue=relaxed).words == [["a0", "a1", "a2"]]


def test_default_rules_are_the_shipped_constants():
    r = T.base_rules()
    assert (r.aspect_max, r.height_ratio, r.prox_mult, r.min_members) == (
        WORD_ASPECT_MAX, LETTER_HEIGHT_RATIO, PROXIMITY_HEIGHT_MULT, 3)


def test_a_relaxed_reach_joins_the_far_glyph_and_the_shipped_rules_do_not():
    regions = _text("a", "HELT") + _text("z", "F", x0=60.0)
    base = T.trace(regions, threads.CHART)
    wide = T.trace(regions, threads.CHART, rules=T.replace(T.base_rules(), prox_mult=30.0))
    assert base.words == [["a0", "a1", "a2", "a3"]]
    assert wide.words == [["a0", "a1", "a2", "a3", "z0"]]


def test_variant_parity_when_nothing_is_overridden():
    regions = _text("t", "HELTFU") + _rope("r", 12, -4, 15) + _text("x", "HE", x0=40.0)
    a = T.trace(regions, threads.CHART)
    b = T.trace(regions, threads.CHART, rules=T.base_rules(), memo={})
    assert a.words == b.words and a.rejected.keys() == b.rejected.keys()


def test_score_words_counts_gained_letters_and_new_strays_and_crossline_words():
    line_of = {"a": "ONE", "b": "ONE", "c": "ONE", "d": "TWO", "e": "TWO", "f": "TWO"}
    base = [["a", "b", "c"]]
    # the variant adds the second line as its own word, and a stray joined to the first
    var = [["a", "b", "c", "x"], ["d", "e", "f"]]
    s = T.score_words(var, base, line_of, set(), {"ONE": 3, "TWO": 3})
    assert s["gained"] == ["d", "e", "f"] and s["lost"] == []
    assert s["stray"] == ["x"] and s["crossline"] == 0 and s["complete"] == 2
    # a word spanning two expected lines is a cross-line join
    s = T.score_words([["a", "b", "c", "d", "e", "f"]], base, line_of, set(), {"ONE": 3, "TWO": 3})
    assert s["crossline"] == 1
    # an ignored region is neither a stray nor a letter
    s = T.score_words([["a", "b", "c", "ig"]], base, line_of, {"ig"}, {"ONE": 3})
    assert s["stray"] == []


def test_census_table_flags_a_variant_with_a_false_join():
    res = [{"fixture": "f", "sizes": {"50.0": {
        "base_score": {"complete": 0},
        "variants": {"good": {"gained": ["a"], "lost": [], "stray": [], "crossline": 0, "complete": 1},
                     "bad": {"gained": ["a"], "lost": [], "stray": ["x"], "crossline": 0, "complete": 1}}}}}]
    rows = T.census_table(res).splitlines()
    assert rows[2].endswith("| yes |") and rows[3].endswith("| NO |")


# --- the nesting drop, named ------------------------------------------------

def _ring(sid, cx, cy, r, stroke=0.8):
    from shapely.geometry import Point
    c = Point(cx, cy)
    return _region(sid, c.buffer(r, 64).difference(c.buffer(r - stroke, 64)))


def test_a_nested_glyph_names_its_host_and_the_containment_values():
    regions = _text("a", "HELTFU", x0=-11.0, y0=-2.0) + [_ring("ring", 0.0, 0.0, 15.0)]
    # the rule before 2026-10-20 ("box") swallows the whole line; the shipped
    # one frees it (`test_words.py`), so the naming is read under "box"
    assert T.trace(regions, threads.CHART).words == [[f"a{i}" for i in range(6)]]
    t = T.trace(regions, threads.CHART, rules=T.replace(T.base_rules(), nested="box"))
    assert t.words == []
    info = t.nested["a0"]
    assert info["host"] == "ring" and info["hosts"] == 1
    assert info["host_h"] == pytest.approx(30.0, rel=0.01)
    assert info["h_ratio"] == pytest.approx(H / 30.0, rel=0.02)
    assert info["ink_overlap"] == pytest.approx(0.0)       # not on the ring's ink
    assert info["shell_frac"] == pytest.approx(1.0)        # it sits in the ring's hole
    assert t.rejected["a0"].rule == "nested" and "host ring" in t.rejected["a0"].detail


def test_the_ring_policy_frees_the_word_in_the_hole_and_nothing_else():
    crumb = _region("crumb", box(-1.0, 7.0, -0.2, 8.5))
    regions = (_text("a", "HELTFU", x0=-11.0, y0=-2.0) + [_ring("ring", 0.0, 0.0, 15.0), crumb])
    ring = T.replace(T.base_rules(), nested="ring")
    t = T.trace(regions, threads.CHART, rules=ring)
    assert t.words == [[f"a{i}" for i in range(6)]]
    assert "ring" in t.cands and t.rejected["crumb"].rule == "nested"
    # two glyphs are not a word: the host keeps them
    pair = _text("a", "HE", x0=-3.5, y0=-2.0) + [_ring("ring", 0.0, 0.0, 15.0)]
    assert set(T.trace(pair, threads.CHART, rules=ring).cands) == {"ring"}


def test_the_ring_policy_also_frees_a_two_by_two_icon_grid():
    """Why it is not shipped: four panes in a 2x2 grid inside a shape's hole
    (the drone's and the screenshot's icons at 100 mm, gaulke's window)
    link like a word of four and are freed with it."""
    panes = [_region(f"p{i}", box(x, y, x + 1.5, y + 1.5))
             for i, (x, y) in enumerate([(-1.7, -1.7), (0.2, -1.7), (-1.7, 0.2), (0.2, 0.2)])]
    regions = panes + [_ring("ring", 0.0, 0.0, 6.0)]
    assert T.trace(regions, threads.CHART).words == []          # shipped: ring+line keeps it out
    t = T.trace(regions, threads.CHART, rules=T.replace(T.base_rules(), nested="ring"))
    assert t.words == [["p0", "p1", "p2", "p3"]]
    # ... and the line test is what refuses it: a 2x2 block doubles back
    assert W._max_turn_deg([t.cands[f"p{i}"] for i in range(4)]) >= 90.0


def test_the_shipped_nesting_policy_is_the_taggers_own_and_the_trace_mirrors_it():
    """`base_rules().nested` names the tagger's rule, and on a word in a hole,
    a grid in a hole and a word beside a host's ink the trace reads the same
    words `detect_words` does (parity under the new drop)."""
    assert T.base_rules().nested == T.SHIPPED_NEST == "ring+line"
    assert T.Rules.__dataclass_fields__["nested"].default == T.SHIPPED_NEST
    from shapely.geometry import Polygon as P
    panes = [_region(f"p{i}", box(30 + x, y, 31.5 + x, y + 1.5))
             for i, (x, y) in enumerate([(-1.7, -1.7), (0.2, -1.7), (-1.7, 0.2), (0.2, 0.2)])]
    host = _region("host", P([(60, 0), (61, 0), (61, 29), (100, 29), (100, 30), (60, 30)]))
    regions = (_text("a", "HELTFU", x0=-11.0, y0=-2.0) + [_ring("ring", 0.0, 0.0, 15.0)]
               + panes + [_ring("ring2", 30.0, 0.0, 6.0)]
               + _text("b", "HELT", x0=70.0, y0=5.0) + [host])
    t = T.trace(regions, threads.CHART)
    assert sorted(t.words) == _ids_of(detect_words(regions, chart=threads.CHART))
    assert t.words == [[f"a{i}" for i in range(6)]]
    assert t.rejected["p0"].rule == "nested" and t.rejected["b0"].rule == "nested"


def test_box_line_frees_a_line_beside_a_hosts_ink_and_the_shipped_rule_does_not():
    """The census-only `box+line` containment (measured 2026-10-20: 16
    gained, 3 strays on golden_tee) against the shipped `ring+line`."""
    from shapely.geometry import Polygon as P
    host = _region("host", P([(0, 0), (1, 0), (1, 29), (40, 29), (40, 30), (0, 30)]))
    # the word sits in the L's box AND inside its convex hull (the hull's
    # diagonal runs from (1, 0) to (40, 29); at x 10-25 it passes y 7-18),
    # beside the L's ink, outside its outline
    regions = _text("a", "HELT", x0=10.0, y0=19.0) + [host]
    if "host" not in T.trace(regions, threads.CHART, rules=T.replace(T.base_rules(), nested="box")).cands:
        pytest.fail("fixture: the L host must pass the glyph screens")
    assert T.trace(regions, threads.CHART).words == []
    boxline = T.trace(regions, threads.CHART, rules=T.replace(T.base_rules(), nested="box+line"))
    hullline = T.trace(regions, threads.CHART, rules=T.replace(T.base_rules(), nested="hull+line"))
    assert boxline.words == [["a0", "a1", "a2", "a3"]]
    assert hullline.words == [["a0", "a1", "a2", "a3"]]
    # a word in the box but outside the hull: box+line frees it, hull+line not
    corner = _text("c", "HELT", x0=10.0, y0=1.0) + [host]
    assert T.trace(corner, threads.CHART, rules=T.replace(T.base_rules(), nested="box+line")).words == [
        ["c0", "c1", "c2", "c3"]]
    assert T.trace(corner, threads.CHART, rules=T.replace(T.base_rules(), nested="hull+line")).words == []
    # and neither frees a block
    panes = [_region(f"p{i}", box(10 + x, 19 + y, 11.5 + x, 20.5 + y))
             for i, (x, y) in enumerate([(0, 0), (1.9, 0), (0, 1.9), (1.9, 1.9)])]
    grid = panes + [host]
    for pol in ("box+line", "hull+line"):
        assert T.trace(grid, threads.CHART, rules=T.replace(T.base_rules(), nested=pol)).words == []


def test_the_frame_policy_frees_a_word_beside_a_hosts_ink_and_the_ring_does_not():
    from shapely.geometry import Polygon as P
    host = _region("host", P([(0, 0), (1, 0), (1, 29), (40, 29), (40, 30), (0, 30)]))
    regions = _text("a", "HELT", x0=10.0, y0=5.0) + [host]
    if "host" not in T.trace(regions, threads.CHART).cands:
        pytest.fail("fixture: the L host must pass the glyph screens")
    frame = T.trace(regions, threads.CHART, rules=T.replace(T.base_rules(), nested="frame"))
    ring = T.trace(regions, threads.CHART, rules=T.replace(T.base_rules(), nested="ring"))
    assert frame.words == [["a0", "a1", "a2", "a3"]] and ring.words == []


def test_the_outline_policy_frees_a_glyph_beside_a_hosts_ink_not_in_its_hole():
    from shapely.geometry import Polygon as P
    # an L-shaped host whose box holds a word that sits beside its ink
    host = _region("host", P([(0, 0), (1, 0), (1, 29), (40, 29), (40, 30), (0, 30)]))
    regions = _text("a", "HELT", x0=10.0, y0=5.0) + [host]
    outline = T.replace(T.base_rules(), nested="outline")
    base = T.trace(regions, threads.CHART)
    if "host" in base.cands:                  # the host passed the glyph screens
        assert base.words == [] and base.nested["a0"]["shell_frac"] == pytest.approx(0.0)
    assert T.trace(regions, threads.CHART, rules=outline).words == [["a0", "a1", "a2", "a3"]]
    ring = _text("a", "HELT", x0=-7.0, y0=-2.0) + [_ring("ring", 0.0, 0.0, 15.0)]
    assert T.trace(ring, threads.CHART, rules=outline).words == []   # in the hole: swallowed


def test_parse_variant_reads_a_nested_policy():
    assert T.parse_variant("nested=frame") == ("nested=frame", {"nested": "frame"})
    assert T.parse_variant("nest_max_h=5") == ("nest_max_h=5", {"nest_max_h": 5.0})
    assert set(T.NEST_VARIANTS) >= {"nested=box", "nested=ring", "nested=frame", "nested=outline",
                                    "nested=box+line", "nested=hull+line"}
