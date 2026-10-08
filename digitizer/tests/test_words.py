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
    r = _region("a", box(0, 0, 1, 1))
    r.meta.update({"text_candidate": True, "text_cluster_id": "TCx", "lettering_group": True})
    off, on = PipelineConfig(), PipelineConfig(lettering_words=True)
    assert is_text(r, off) and word_key(r, off) == "TCx" and is_lettering(r, off)
    assert not is_text(r, on) and word_key(r, on) is None and not is_lettering(r, on)
    r.meta["word_id"] = "WDy"
    assert is_text(r, on) and word_key(r, on) == "WDy" and is_lettering(r, on)
    assert is_lettering(r) and is_lettering(r, None)     # no cfg: the old reading


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
