"""`words.py` -- L1 of the lettering lane: one tagger, one word model.

Synthetic glyphs are block capitals built from bars (H, E, L, T, F, I, U),
so a word's members DIFFER the way real letters do -- the pattern test
(`_pattern_ids`) exists to tell that apart from a rope's identical twists,
and bare rectangles would read as a pattern. The real-logo accuracy lives
in `tools/word_tagger_eval.py`, scored against `testdata/lettering_truth
.json`; the end-to-end checks here use Becker, the one logo whose both old
taggers and the new one agree, to pin the WIRING rather than the score.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, threads
from digitizer_core.columns import is_lettering
from digitizer_core.pipeline import build_generation
from digitizer_core.regions import Region
from digitizer_core.textcluster import _lettering_groups
from digitizer_core.words import (PATTERN_MIN_TWINS, WORD_KEYS, _candidates, _pattern_ids,
                                  detect_words, is_text, tag_words, word_groups, word_key,
                                  word_ocr_text)
from tools.word_tagger_eval import ari, kappa
from tests.conftest import PRE_FLIP

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
H, W, S = 4.0, 3.0, 0.6        # cap height, glyph width, stroke (mm)


def _glyph(ch: str, x: float, y: float) -> Polygon:
    """Block capital `ch` with its box's top-left at (x, y), y down."""
    bars = {
        "H": [(0, 0, S, H), (W - S, 0, W, H), (0, H / 2 - S / 2, W, H / 2 + S / 2)],
        "E": [(0, 0, S, H), (0, 0, W, S), (0, H / 2 - S / 2, W * 0.8, H / 2 + S / 2), (0, H - S, W, H)],
        "L": [(0, 0, S, H), (0, H - S, W, H)],
        "T": [(0, 0, W, S), (W / 2 - S / 2, 0, W / 2 + S / 2, H)],
        "F": [(0, 0, S, H), (0, 0, W, S), (0, H / 2 - S / 2, W * 0.8, H / 2 + S / 2)],
        "I": [(W / 2 - S / 2, 0, W / 2 + S / 2, H)],
        "U": [(0, 0, S, H), (W - S, 0, W, H), (0, H - S, W, H)],
    }[ch]
    return unary_union([box(x + a, y + b, x + c, y + d) for a, b, c, d in bars])


def _region(sid: str, poly: Polygon, ink: int = 0) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=ink, thread_number="1",
                  area_mm2=poly.area, meta={})


def _text(prefix: str, word: str, x0: float = 0.0, y0: float = 0.0,
          pitch: float = 3.8, ink: int = 0) -> list[Region]:
    return [_region(f"{prefix}{i}", _glyph(ch, x0 + i * pitch, y0), ink)
            for i, ch in enumerate(word)]


def _twist(x: float, y: float) -> Polygon:
    """One rope twist: a leaning lozenge, the same shape every time."""
    p = Polygon([(0, 0), (1.2, 0), (2.2, H), (1.0, H)])
    return translate(p, x, y)


def _rope(prefix: str, n: int, x0: float, y0: float, ink: int = 0) -> list[Region]:
    return [_region(f"{prefix}{i:02d}", _twist(x0 + 1.6 * i, y0), ink) for i in range(n)]


def _ids(word) -> list[str]:
    return [r.shape_id for r in word.members]


# ------------------------------------------------------------------ the tagger

def test_one_line_is_one_word_in_reading_order():
    regions = _text("a", "HELTFU")
    random.Random(1).shuffle(regions)
    words = detect_words(regions)
    assert len(words) == 1
    w = words[0]
    assert _ids(w) == [f"a{i}" for i in range(6)]
    assert w.line_deg is not None and min(w.line_deg, 180 - w.line_deg) < 1.0
    assert w.cap_mm == pytest.approx(H, rel=0.05)   # line from centroids: T sits high, L low
    assert w.stroke_mm == pytest.approx(S, rel=0.35)
    (bx0, by0), (bx1, by1) = w.baseline
    assert by0 == pytest.approx(H, rel=0.05) and by1 == pytest.approx(H, rel=0.05)
    assert bx1 > bx0


def test_two_stacked_lines_are_two_words_where_the_house_group_saw_one():
    """Gaulke and the screenshot: two rows at one size, closer than the
    link's reach, were ONE group in both old taggers."""
    top = _text("t", "HELTFU", y0=0.0)
    bottom = _text("b", "FUTHEL", y0=H * 1.4)
    regions = top + bottom
    assert len(_lettering_groups(regions)) == 1
    words = detect_words(regions)
    assert sorted(sorted(_ids(w)) for w in words) == [
        sorted(r.shape_id for r in bottom), sorted(r.shape_id for r in top)]


def test_an_arched_line_is_not_split():
    """A line laid on an arc spreads across its chord continuously; no gap,
    no split (Becker's BECKER, bridge's RESTAURANT)."""
    regions = []
    for i, ch in enumerate("HELTFUHE"):
        g = _glyph(ch, 0.0, 0.0)
        g = rotate(g, -35 + 10 * i, origin=(W / 2, 20.0))
        regions.append(_region(f"r{i}", g))
    words = detect_words(regions)
    assert len(words) == 1 and len(words[0].members) == 8


def test_a_rope_beside_the_text_is_a_pattern_not_a_word():
    """Fremont: rope twists in the letters' ink and size chained into the
    EAT STAY PLAY component and made three rope 'words' of their own."""
    text = _text("t", "HELTFU", y0=0.0)
    rope = _rope("r", 16, x0=-6.0, y0=H * 1.6)
    words = detect_words(text + rope)
    tagged = {s for w in words for s in _ids(w)}
    assert tagged == {r.shape_id for r in text}
    comp = _candidates(text + rope)
    assert _pattern_ids(comp) == {r.shape_id for r in rope}


def test_letters_spelled_up_to_four_times_are_not_a_pattern():
    """PLOWING DIVISION has four I's: three twins each, under the
    threshold; a word only becomes a 'pattern' past PATTERN_MIN_TWINS."""
    regions = _text("w", "HIEILTIFI")
    assert PATTERN_MIN_TWINS > 3
    assert _pattern_ids(_candidates(regions)) == set()
    assert {s for w in detect_words(regions) for s in _ids(w)} == {r.shape_id for r in regions}


def test_a_letter_repeated_across_a_lockup_is_not_a_pattern():
    """MILLION DOLLAR BILLS spells six L's. Counted over the whole linked
    component they are five twins each; within the pattern reach a letter
    only sees its own neighbourhood (review finding 2026-10-08)."""
    phrase = "HILLTEF ULLHEFT ILLUTEH"
    regions = [_region(f"p{i:02d}", _glyph(ch, i * 3.8, 0.0))
               for i, ch in enumerate(phrase) if ch != " "]
    assert sum(ch == "L" for ch in phrase) == 6
    assert _pattern_ids(_candidates(regions)) == set()
    assert {s for w in detect_words(regions) for s in _ids(w)} == {r.shape_id for r in regions}


def test_two_inks_are_two_words():
    chart = threads.CHART
    far = next(j for j in range(1, 50) if float(chart.delta_e(0, j)) > 20.0)
    regions = _text("a", "HELT", ink=0) + _text("b", "FUHE", x0=4 * 3.8, ink=far)
    words = detect_words(regions, chart=chart)
    assert sorted(sorted(_ids(w)) for w in words) == [
        [f"a{i}" for i in range(4)], [f"b{i}" for i in range(4)]]


def test_under_three_glyphs_is_not_a_word():
    assert detect_words(_text("a", "HE")) == []


def test_deterministic_under_input_order():
    regions = _text("t", "HELTFU") + _text("b", "FUTHEL", y0=H * 1.4) + _rope("r", 10, -4, 15)
    ref = [(w.word_id, _ids(w)) for w in detect_words(regions)]
    for seed in range(5):
        shuffled = regions[:]
        random.Random(seed).shuffle(shuffled)
        assert [(w.word_id, _ids(w)) for w in detect_words(shuffled)] == ref


# ------------------------------------------------------------------ meta + readers

def test_tag_words_stamps_members_and_clears_stale_keys():
    regions = _text("a", "HELT") + [_region("x", box(40, 40, 41, 41))]
    regions[-1].meta["word_id"] = "WDstale"
    words = tag_words(regions)
    assert len(words) == 1
    for i, r in enumerate(regions[:4]):
        assert r.meta["word_id"] == words[0].word_id and r.meta["word_index"] == i
        assert r.meta["word_size"] == 4 and r.meta["word_cap_mm"] == pytest.approx(H, rel=0.05)
    assert not any(k in regions[-1].meta for k in WORD_KEYS)
    assert word_groups(regions) == [regions[:4]]


def test_word_ocr_text_joins_in_reading_order():
    regions = _text("a", "HELT")
    tag_words(regions)
    for r, ch in zip(regions, "HE?T"):
        if ch != "?":
            r.meta["ocr_char"] = ch
    word_ocr_text(regions)
    assert {r.meta["word_ocr_text"] for r in regions} == {"HE?T"}


def test_readers_follow_the_flag():
    # A stroke-shaped box (1 x 6), not a 1 x 1 square: a solid blob is refused
    # by `lettering_columns_skip_blobs` (ON since 2026-10-13), tagged or not.
    r = _region("a", box(0, 0, 1, 6))
    r.meta.update({"text_candidate": True, "text_cluster_id": "TCx", "lettering_group": True})
    off, on = PipelineConfig(), PipelineConfig(lettering_words=True)
    assert is_text(r, off) and word_key(r, off) == "TCx" and is_lettering(r, off)
    assert not is_text(r, on) and word_key(r, on) is None and not is_lettering(r, on)
    r.meta["word_id"] = "WDy"
    assert is_text(r, on) and word_key(r, on) == "WDy" and is_lettering(r, on)
    assert is_lettering(r) and is_lettering(r, None)     # no cfg: the old reading


def test_stitch_width_groups_by_word_under_the_flag():
    from digitizer_core.stitchwidth import GROUP_KEY, measure_stitch_widths
    regions = _text("a", "HELT")
    tag_words(regions)
    regions[0].meta["text_cluster_id"] = "TCother"
    measure_stitch_widths(regions, satin_max=6.5, words=True)
    assert {r.meta.get(GROUP_KEY) for r in regions} == {regions[0].meta["word_id"]}
    measure_stitch_widths(regions, satin_max=6.5)
    assert regions[0].meta.get(GROUP_KEY) == "TCother"
    assert all(GROUP_KEY not in r.meta for r in regions[1:])


def test_satin_split_ceiling_reads_the_word_under_the_flag():
    import math
    from digitizer_core.stage7_sequence import _satin_ceiling_for
    r = _region("a", box(0, 0, 1, 4))
    r.meta["word_id"] = "WDx"
    off, on = PipelineConfig(satin_lettering_split=True), PipelineConfig(
        satin_lettering_split=True, lettering_words=True)
    assert _satin_ceiling_for(r, on, 5.0)[0] == math.inf
    assert _satin_ceiling_for(r, off, 5.0)[0] == 5.0
    r.meta.update({"text_candidate": True})
    del r.meta["word_id"]
    assert _satin_ceiling_for(r, off, 5.0)[0] == math.inf
    assert _satin_ceiling_for(r, on, 5.0)[0] == 5.0


# ------------------------------------------------------------------ end to end

@pytest.fixture(scope="module")
def becker():
    out = {}
    for on in (False, True):
        cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest", max_colors=6,
                             lettering_words=on)
        out[on] = build_generation(str(TESTDATA / "becker_marine_logo.png"), cfg).regions
    return out


def test_off_writes_no_word_and_on_finds_becker_two_lines(becker):
    assert not any("word_id" in r.meta for r in becker[False])
    groups = word_groups(becker[True])
    assert sorted(len(g) for g in groups) == [5, 6]       # BECKER (E+C one region), MARINE
    tagged = {r.shape_id for g in groups for r in g}
    assert tagged == {r.shape_id for r in becker[False] if r.meta.get("text_candidate")}


def test_on_the_house_angle_groups_by_word(becker):
    """Under the flag the house pass's groups are the words: every word
    member is marked `lettering_group` and nothing else is."""
    on = becker[True]
    assert {r.shape_id for r in on if r.meta.get("lettering_group")} == {
        r.shape_id for r in on if r.meta.get("word_id")}


# ------------------------------------------------------------------ the instrument

def test_kappa_and_ari_reference_values():
    assert kappa([True, False] * 5, [True, False] * 5) == pytest.approx(1.0)
    assert kappa([True, False] * 5, [False, True] * 5) == pytest.approx(-1.0)
    assert kappa([True] * 3 + [False] * 7, [False] * 10) == pytest.approx(0.0)
    assert ari([0, 0, 1, 1], ["a", "a", "b", "b"]) == pytest.approx(1.0)
    # Hubert & Arabie's own small example: ARI of {0,0,0,1,1,1} vs {0,0,1,1,2,2}
    assert ari([0, 0, 0, 1, 1, 1], [0, 0, 1, 1, 2, 2]) == pytest.approx(0.242424, abs=1e-5)


def test_truth_file_is_well_formed():
    from tools.thin_strokes import REAL_ART
    truth = json.loads((TESTDATA / "lettering_truth.json").read_text())
    assert truth["commit"] and truth["about"]
    for name, fx in truth["fixtures"].items():
        assert name in REAL_ART
        ids = [s for line in fx["lines"].values() for s in line]
        assert ids and len(ids) == len(set(ids))
        assert not set(ids) & set(fx.get("ignore", []))


# ------------------------------------------------------------------ the nesting drop
#
# `_drop_nested_words` (2026-10-20): a host's box swallows a glyph UNLESS the
# glyph is one of a LINE of lettering lying in the host's hole, and a line
# is a chain that never doubles back (`_is_line`, `LINE_TURN_MAX_DEG`). The
# measured case is bridge's BAR & RESTAURANT inside its badge at 50 mm (PRs
# #889, #900); the measured refusals are 2x2 icon grids in a shape's hole.

from shapely.geometry import Point  # noqa: E402

from digitizer_core.words import (LINE_TURN_MAX_DEG, _drop_nested_words, _is_line,  # noqa: E402
                                  _max_turn_deg)


def _ring(sid: str, cx: float, cy: float, r: float, stroke: float = 0.8) -> Region:
    c = Point(cx, cy)
    return _region(sid, c.buffer(r, 64).difference(c.buffer(r - stroke, 64)))


def _panes(prefix: str, x0: float, y0: float, side: float = 1.5, pitch: float = 1.9) -> list[Region]:
    """A 2x2 block of identical squares (an icon's window panes)."""
    return [_region(f"{prefix}{i}", box(x0 + x, y0 + y, x0 + x + side, y0 + y + side))
            for i, (x, y) in enumerate([(0, 0), (pitch, 0), (0, pitch), (pitch, pitch)])]


def test_a_line_in_a_rings_hole_is_a_word():
    """The badge case: a ring under the height ceiling passes every glyph
    screen and its box holds the whole line in its hole. Before 2026-10-20
    the line was swallowed."""
    text = _text("a", "HELTFU", x0=-11.0, y0=-2.0)
    regions = text + [_ring("ring", 0.0, 0.0, 15.0)]
    words = detect_words(regions)
    assert len(words) == 1 and _ids(words[0]) == [f"a{i}" for i in range(6)]
    assert {c.region.shape_id for c in _candidates(regions)} == {r.shape_id for r in regions}


def test_an_arched_line_in_a_rings_hole_is_a_word():
    """BAR & RESTAURANT runs round its badge (24-34 deg between steps at
    every size): the chain test tolerates an arc."""
    regions = []
    for i, ch in enumerate("HELTFUHE"):
        g = rotate(_glyph(ch, 0.0, 0.0), -42 + 12 * i, origin=(W / 2, 14.0))
        regions.append(_region(f"r{i}", g))
    regions.append(_ring("ring", W / 2, 14.0, 19.0))
    words = detect_words(regions)
    assert len(words) == 1 and len(words[0].members) == 8
    cands = [c for c in _candidates(regions) if c.region.shape_id != "ring"]
    assert 5.0 < _max_turn_deg(cands) < LINE_TURN_MAX_DEG


def test_a_grid_in_a_rings_hole_is_not_a_word():
    """Why freeing whatever LINKS in a hole was a measured negative (#900):
    four panes link like a word of four. A block has to double back
    between its rows, so it fails the line test and stays swallowed."""
    regions = _panes("p", -1.7, -1.7) + [_ring("ring", 0.0, 0.0, 6.0)]
    assert detect_words(regions) == []
    assert [c.region.shape_id for c in _candidates(regions)] == ["ring"]
    raw = [c for c in _candidates(regions[:4])]          # the panes alone, no host
    assert len(raw) == 4
    assert _max_turn_deg(raw) >= 90.0 and not _is_line(raw)
    # the plateau the limit sits in: every measured line under 37 deg, every
    # measured block over 99 (the module's constant comment has the table)
    assert 37.0 < LINE_TURN_MAX_DEG < 99.0


def test_a_pair_a_crumb_and_a_line_beside_a_hosts_ink_are_swallowed_as_before():
    # two glyphs are not a word, so the ring keeps them, and the crumb too
    pair = _text("a", "HE", x0=-3.5, y0=-2.0) + [_region("crumb", box(-1.0, 7.0, -0.2, 8.5)),
                                                 _ring("ring", 0.0, 0.0, 15.0)]
    assert detect_words(pair) == []
    assert [c.region.shape_id for c in _candidates(pair)] == ["ring"]
    # a line in the host's BOX beside its ink (an L-shaped host): the
    # exception is for the hole, not the box, so it is swallowed as before
    host = _region("host", Polygon([(0, 0), (1, 0), (1, 29), (40, 29), (40, 30), (0, 30)]))
    beside = _text("b", "HELT", x0=10.0, y0=5.0) + [host]
    kept = {c.region.shape_id for c in _candidates(beside)}
    if "host" in kept:                      # the host passed the glyph screens, as the badge does
        assert kept == {"host"} and detect_words(beside) == []


def test_the_row_test_values_and_the_plain_drop_without_a_host():
    row = _candidates(_text("a", "HELTFU"))
    assert _max_turn_deg(row) < 5.0 and _is_line(row)
    assert _max_turn_deg(row[:2]) == 0.0 and not _is_line(row[:2])
    # with no host holding three, the drop IS `textcluster._drop_nested`
    from digitizer_core.textcluster import _drop_nested
    regions = _text("a", "HELT") + [_region("frag", box(0.1, 0.5, 0.4, 2.0))]
    raw = _candidates(regions)
    assert [c.region.shape_id for c in raw] == [c.region.shape_id for c in _drop_nested(raw)]
    assert "frag" not in {c.region.shape_id for c in raw}


# --- the corpus cases the rule was measured on ------------------------------

@pytest.fixture(scope="module")
def bridge():
    from digitizer_core.threads import chart_for
    from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS
    fname, corpus_w, garment = REAL_ART["bridge"]
    out = {}
    for w in (corpus_w, 50.0):
        # `dissolve_phantom_blends` held OFF (ON since Kent's 2026-10-20 flip,
        # item 46): the hand labels are shape ids read without it, and on this
        # JPEG it re-cuts the halo regions they name.
        cfg = PipelineConfig(target_width_mm=w, garment_id=garment, max_colors=STUDIO_MAX_COLORS,
                             dissolve_phantom_blends=False)
        out[w] = (build_generation(str(TESTDATA / fname), cfg).regions, chart_for(cfg))
    return corpus_w, out


def test_bridge_50mm_bar_and_restaurant_is_freed_from_the_badge(bridge):
    """At 50 mm the badge disc (49.4 mm, under the 60 mm ceiling) held every
    letter of BAR & RESTAURANT in its box and the tagger found no word
    (#889: 12 of the 58 misses). Now the eight that link are one word and
    nothing else is tagged: the labelled letters, carried to 50 mm by
    position, are the only members."""
    from tools.word_tagger_trace import carry
    corpus_w, out = bridge
    ref_regions, _ = out[corpus_w]
    regions, chart = out[50.0]
    truth = json.loads((TESTDATA / "lettering_truth.json").read_text())["fixtures"]["bridge"]
    letters = {carry(ref_regions, corpus_w, regions, 50.0).get(s)
               for s in truth["lines"]["BAR & RESTAURANT"]} - {None}
    assert len(letters) == 12, "the carry lost a letter: re-read the fixture"
    words = detect_words(regions, chart=chart)
    assert len(words) == 1
    members = set(_ids(words[0]))
    assert members <= letters and len(members) == 8
    # the host is still a candidate (it passes the screens) and in no word
    badge = max(regions, key=lambda r: r.polygon.bounds[3] - r.polygon.bounds[1])
    assert badge.shape_id not in members
    assert 45.0 < badge.polygon.bounds[3] - badge.polygon.bounds[1] < 60.0


@pytest.mark.parametrize("name", ["drone", "screenshot"])
def test_the_icon_grids_in_a_hole_stay_out_at_100mm(name):
    """#900's two strays under the `ring` policy: a 2x2 grid of panes in an
    icon's hole (drone's body, the phone's app icon) linked like a word of
    four. With the line test the tagger at 100 mm reads exactly what it read
    under the rule before 2026-10-20."""
    from dataclasses import replace
    from digitizer_core.threads import chart_for
    from tools import word_tagger_trace as T
    from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS
    fname, _w, garment = REAL_ART[name]
    # The census #900 read was taken before `subpixel_corner_runs` (ON since
    # 2026-10-20, Kent's ruling); ON, drone's grid reads as three panes, not
    # four. Held on the engine it was measured on (`PRE_FLIP`).
    cfg = PipelineConfig(target_width_mm=100.0, garment_id=garment, max_colors=STUDIO_MAX_COLORS,
                         subpixel_corner_runs=PRE_FLIP["subpixel_corner_runs"])
    regions = build_generation(str(TESTDATA / fname), cfg).regions
    chart = chart_for(cfg)
    memo: dict = {}
    now = sorted(sorted(_ids(w)) for w in detect_words(regions, chart=chart))
    before = sorted(T.trace(regions, chart, rules=replace(T.base_rules(), nested="box"), memo=memo).words)
    ring = sorted(T.trace(regions, chart, rules=replace(T.base_rules(), nested="ring"), memo=memo).words)
    assert now == before
    extra = [w for w in ring if w not in before]
    assert len(extra) == 1 and len(extra[0]) == 4, "the grid #900 measured is gone: re-read the census"
    cands = T.trace(regions, chart, rules=replace(T.base_rules(), nested="ring"), memo=memo).cands
    assert _max_turn_deg([cands[s] for s in extra[0]]) >= 90.0


def test_the_hole_exception_is_deterministic_under_input_order():
    """A word in a ring's hole, a grid in another's, a line beside an L
    host and a plain row: the same words and ids from any input order."""
    host = _region("host", Polygon([(60, 0), (61, 0), (61, 29), (100, 29), (100, 30), (60, 30)]))
    regions = (_text("a", "HELTFU", x0=-11.0, y0=-2.0) + [_ring("ring", 0.0, 0.0, 15.0)]
               + _panes("p", 28.3, -1.7) + [_ring("ring2", 30.0, 0.0, 6.0)]
               + _text("b", "HELT", x0=70.0, y0=5.0) + [host] + _text("c", "FUTHEL", y0=40.0))
    ref = [(w.word_id, _ids(w)) for w in detect_words(regions)]
    assert sorted(ids for _wid, ids in ref) == [[f"a{i}" for i in range(6)], [f"c{i}" for i in range(6)]]
    for seed in range(5):
        shuffled = regions[:]
        random.Random(seed).shuffle(shuffled)
        assert [(w.word_id, _ids(w)) for w in detect_words(shuffled)] == ref
