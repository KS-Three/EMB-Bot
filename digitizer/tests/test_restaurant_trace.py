"""`tools/restaurant_trace.py` -- which reader refuses each glyph of bridge's
BAR & RESTAURANT. The bridge digitize itself is minutes, so these build the
refusals on synthetic block capitals (`tests/test_words.py`'s helpers) and
check that the replay names the same rule the shipped tagger applies, that
the census-only `adopt_line` arm adopts by ink and nothing else, and that the
tier gates read the true-size switch's own values.
"""
from __future__ import annotations

import json

from shapely.affinity import rotate
from shapely.geometry import box

from digitizer_core import PipelineConfig, threads
from digitizer_core.textcluster import detect_text_clusters
from tests.test_words import H, _glyph, _region, _text
from tools import restaurant_trace as RT


def _far_ink(i: int = 0) -> int:
    """A thread index further than the text cluster's ink link from `i`."""
    chart = threads.CHART
    return next(j for j in range(len(chart)) if chart.delta_e(i, j) > 30.0)


def test_a_straight_word_is_tagged_and_the_replay_agrees_with_the_tagger():
    regs = _text("t", "HELTF")
    ids = [r.shape_id for r in regs]
    out = RT.text_cluster_trace(regs, threads.CHART, ids)
    detect_text_clusters(regs, None, chart=threads.CHART)
    assert all(v["tagged"] for v in out.values())
    assert all(r.meta.get("text_candidate") for r in regs)


def test_a_glyph_turned_on_an_arc_is_refused_by_its_axis_aligned_box():
    regs = _text("t", "HELT")
    turned = _region("turned", rotate(_glyph("I", 16.0, 0.0), 90, origin="centroid"))
    out = RT.text_cluster_trace(regs + [turned], threads.CHART, ["turned"])
    assert not out["turned"]["tagged"]
    assert out["turned"]["why"].startswith("aspect")
    detect_text_clusters(regs + [turned], None, chart=threads.CHART)
    assert not turned.meta.get("text_candidate")


def test_a_glyph_inside_a_larger_shapes_box_is_refused_as_nested():
    ring = _region("ring", box(-10, -10, 30, 20).difference(box(-9, -9, 29, 19)))
    regs = _text("t", "HELT")
    out = RT.text_cluster_trace([ring] + regs, threads.CHART, ["t0"])
    assert not out["t0"]["tagged"]
    assert out["t0"]["why"].startswith("nested in ring")


def test_a_lone_glyph_names_its_component_and_the_link_it_fails():
    regs = _text("t", "HELT") + [_region("far", _glyph("H", 80.0, 0.0))]
    out = RT.text_cluster_trace(regs, threads.CHART, ["far"])
    assert out["far"]["why"].startswith("component of 1")
    assert "distance" in out["far"]["why"]


def test_adopt_line_adopts_the_line_ink_and_leaves_a_far_ink_out():
    far = _far_ink(0)
    regs = _text("t", "HELT")
    turned = _region("turned", rotate(_glyph("I", 16.0, 0.0), 90, origin="centroid"))
    amp = _region("amp", rotate(_glyph("I", 20.0, 0.0), 90, origin="centroid"), ink=far)
    allr = regs + [turned, amp]
    detect_text_clusters(allr, None, chart=threads.CHART)
    adopted = RT.adopt_line(allr, [r.shape_id for r in allr], threads.CHART)
    assert adopted == ["turned"]
    assert turned.meta["text_cluster_id"] == regs[0].meta["text_cluster_id"]
    assert not amp.meta.get("text_candidate")


def test_adopt_line_does_nothing_without_a_tagged_neighbour():
    lone = [_region("a", _glyph("H", 0.0, 0.0)), _region("b", _glyph("E", 40.0, 0.0))]
    assert RT.adopt_line(lone, ["a", "b"], threads.CHART) == []


def _rows(regs, ink, area):
    return [{"sid": r.shape_id, "ink_stroke_mm": ink, "area_mm2": area} for r in regs]


def test_tier_gates_read_the_true_size_values_unless_the_config_sets_its_own():
    regs = _text("t", "HELT")
    detect_text_clusters(regs, None, chart=threads.CHART)
    rows = _rows(regs, 0.8, 9.0)
    RT.tier_gates(rows, regs, PipelineConfig())
    t = rows[0]["tiers"]
    assert t["restore"] == f"line cap {H:.2f} >= 3"          # SMALL_TEXT_TRUE_SIZE's 3.0
    assert t["bean"] == "ink 0.80 >= 0.5"
    assert t["skeleton"].startswith("area 9.0 >=")
    rows = _rows(regs, 0.3, 1.0)
    RT.tier_gates(rows, regs, PipelineConfig(small_text_restore_mm=6.0))
    assert rows[0]["tiers"] == {"restore": "reached", "bean": "reached", "skeleton": "reached"}


def test_tier_gates_with_no_cluster_and_no_ink():
    regs = _text("t", "HE")                         # two glyphs: never a cluster
    rows = _rows(regs, None, 9.0)
    RT.tier_gates(rows, regs, PipelineConfig())
    assert rows[0]["tiers"]["restore"] == "no text cluster on the line"
    assert rows[0]["tiers"]["bean"] == "no ink read"


def test_letters_cover_exactly_the_labelled_line():
    truth = json.loads(RT.TRUTH.read_text())["fixtures"][RT.CASE]["lines"][RT.LINE]
    assert sorted(RT.LETTERS) == sorted(truth)
    assert "".join(RT.LETTERS[s] for s in RT.LETTERS).replace("&", "") == "BARRESTAURANT"


def test_parse_set():
    assert RT._parse_set(["a=true", "b=none", "c=3", "d=1.3"]) == {"a": True, "b": None, "c": 3, "d": 1.3}


def test_band_render_writes_one_row_per_design(tmp_path):
    design = {"stitches": [{"x": -50, "y": -50, "type": "stitch"}, {"x": 50, "y": -150, "type": "stitch"},
                           {"x": 100, "y": -100, "type": "stitch"}],
              "colors": [{"r": 0, "g": 0, "b": 255}]}
    out = tmp_path / "band.png"
    RT.band_render([("one", design), ("two", design)], out, px_per_mm=4.0, scale=1.0)
    import cv2
    img = cv2.imread(str(out))
    assert img is not None and img.shape[0] > 0
