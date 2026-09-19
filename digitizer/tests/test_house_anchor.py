"""`cfg.satin_house_anchor` — the house angle ANCHORED to the line of text
(`textcluster._cluster_house_angle_deg`, lettering construction plan step 1,
2026-09-19).

Both house-angle votes decide from every stroke of a group, and on lettering
with diagonals the diagonals pull the answer off the stems' perpendicular
the stitch-angle rule names (2026-09-03): on the nine real logos the
doubled-angle vote puts six of the twelve groups it accepts 12-50 deg off
their own line of text, all upright words. ON, a group that makes a line of
text takes house = the line + its STEMS' slant -- the strokes within the
lean cap of the line's normal, length-weighted median offset, on chains
resampled at the four-fold reading's chord -- and the votes are not asked.
A group with no line, or no stems in that family, is voted on as before.

Fixtures are words built at test time from committed `src/fonts/*.json`
(see `test_house_from_line._word_raster`). "HOTEL" in `manga_impact` at
80 mm is the word the doubled-angle vote accepts and answers 27 deg off its
line (27.2 against 180.0 -- the T's bar and the L's foot against five
stems); the same word turned 20 deg, where the vote lands 45 deg off,
pins that the anchor follows the art rather than the raster's axes.
(Diagonal-heavy words were the first choice: "NAVY" fuses at the font's own
advances and never groups; "VANE" reads 0.2 deg upright and 6.7 deg turned,
"ZANY" 12 deg -- the honest middle of a family with hardly a stem, recorded
in the plan, not pinned here.) "Marine" in
`mam_script` is a leaned script: its stems lean about 15 deg, and the
anchor keeps that lean instead of squaring the word to its line.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import pytest
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig
from digitizer_core import textcluster as tc
from digitizer_core.regions import Region

from tests.test_house_from_line import _angle_gap, _run, _word_raster

SCRIPT_FONT = Path(__file__).resolve().parents[2] / "src" / "fonts" / "mam_script.json"


def _group(result):
    groups = tc._lettering_groups(result.regions)
    assert len(groups) == 1, [len(g) for g in groups]
    return groups[0]


def _house(group) -> float | None:
    angles = {r.meta.get("satin_angle_deg") for r in group}
    assert len(angles) == 1, angles
    return angles.pop()


@pytest.fixture(scope="module")
def hotel(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("word") / "hotel80.png"
    cv2.imwrite(str(p), _word_raster("HOTEL", 80.2))
    return p


@pytest.fixture(scope="module")
def hotel_turned(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("word") / "hotel80_r20.png"
    cv2.imwrite(str(p), _word_raster("HOTEL", 80.2, rotate_deg=20.0))
    return p


@pytest.fixture(scope="module")
def script_word(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("word") / "marine_script80.png"
    cv2.imwrite(str(p), _word_raster("Marine", 80.2, font_path=SCRIPT_FONT))
    return p


def test_the_flag_is_off_by_default():
    """Built OFF; the flip is Kent's."""
    assert PipelineConfig().satin_house_anchor is False


# --- the slant reading on its own -------------------------------------------

def _chain(x0, y0, x1, y1, n=12):
    return [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n + 1)]


def _leaning(offset_deg: float, length: float = 6.0, at: float = 0.0):
    """A stroke `offset_deg` off the vertical (the normal to a horizontal
    line), `length` mm, so a positive offset leans the same way a
    forward-slanted stem does in the pipeline's y-down frame."""
    a = math.radians(90.0 + offset_deg)
    return _chain(at, 0.0, at + length * math.cos(a), length * math.sin(a))


def test_stems_square_to_the_line_read_no_slant():
    chains = [(_leaning(0.0, at=x), 10.0) for x in (0.0, 4.0, 8.0)] + [(_chain(0.0, 0.0, 8.0, 0.0), 10.0)]
    assert tc._stem_slant_deg(chains, 0.0) == pytest.approx(0.0, abs=1e-9)


def test_leaned_stems_read_their_lean_and_a_bar_does_not_vote():
    chains = [(_leaning(15.0, at=x), 10.0) for x in (0.0, 4.0, 8.0)] + [(_chain(0.0, 0.0, 30.0, 0.0), 10.0)]
    assert tc._stem_slant_deg(chains, 0.0) == pytest.approx(15.0, abs=1e-6)


def test_the_median_holds_the_stems_against_a_one_sided_diagonal():
    """Three stems and one longer diagonal inside the window: the median
    stays on the stems where a mean would drift toward the diagonal."""
    chains = [(_leaning(0.0, at=x), 10.0) for x in (0.0, 4.0, 8.0)] + [(_leaning(25.0, length=12.0, at=12.0), 10.0)]
    assert tc._stem_slant_deg(chains, 0.0) == pytest.approx(0.0, abs=1e-9)


def test_a_stroke_past_the_window_is_not_a_stem():
    chains = [(_leaning(45.0, at=x), 10.0) for x in (0.0, 4.0, 8.0)]
    assert tc._stem_slant_deg(chains, 0.0) is None


def test_a_family_under_the_floor_is_silent():
    bars = [(_chain(0.0, y, 40.0, y), 10.0) for y in (0.0, 3.0, 6.0)]        # 120 mm along the line
    stem = [(_leaning(0.0, length=4.0), 10.0)]                                 # 4 mm square to it: 3%
    assert tc._stem_slant_deg(bars + stem, 0.0) is None
    assert tc._stem_slant_deg(bars + [(_leaning(0.0, length=20.0), 10.0)], 0.0) == pytest.approx(0.0, abs=1e-9)


def test_the_window_is_the_lean_cap():
    from digitizer_core.stage6_satin import SATIN_HOUSE_MIN_SPAN_DEG
    assert tc.SATIN_HOUSE_STEM_WINDOW_DEG == pytest.approx(90.0 - SATIN_HOUSE_MIN_SPAN_DEG)


# --- through the pipeline ---------------------------------------------------

def test_off_the_word_keeps_the_votes_pulled_house(hotel):
    group = _group(_run(hotel, 80.2))
    line = tc._line_of_text_deg(group)
    house = _house(group)
    assert house is not None and line is not None
    assert _angle_gap(house, line) > 15.0, (house, line)                        # 27.2 against 180.0


def test_on_the_word_sews_square_to_its_line(hotel):
    group = _group(_run(hotel, 80.2, satin_house_anchor=True))
    line = tc._line_of_text_deg(group)
    assert _angle_gap(_house(group), line) < 1.5, (_house(group), line)
    assert _angle_gap(line, 0.0) < 2.0                                          # an upright word on the axis


def test_off_the_word_turned_20_deg_is_further_off_still(hotel_turned):
    group = _group(_run(hotel_turned, 80.2))
    line = tc._line_of_text_deg(group)
    assert 15.0 < _angle_gap(line, 0.0) < 25.0, line                            # the turn happened
    assert _angle_gap(_house(group), line) > 15.0, (_house(group), line)        # 25.5 against 160.4


def test_on_the_word_turned_20_deg_follows_the_art(hotel_turned):
    group = _group(_run(hotel_turned, 80.2, satin_house_anchor=True))
    line = tc._line_of_text_deg(group)
    assert 15.0 < _angle_gap(line, 0.0) < 25.0, line
    assert _angle_gap(_house(group), line) < 5.0, (_house(group), line)         # 163.6 against 160.4


def test_on_a_leaned_script_keeps_its_lean(script_word):
    group = _group(_run(script_word, 80.2, satin_house_anchor=True))
    line = tc._line_of_text_deg(group)
    house = _house(group)
    lean = (house - line + 90.0) % 180.0 - 90.0
    assert 10.0 < lean < 25.0, (house, line)


def test_a_group_with_no_stems_falls_through_to_the_votes():
    """Three bars laid end to end along a diagonal -- the bridge logo's
    wheel spokes: every stroke runs along the line, the near-normal family
    is silent, and the anchor defers to the votes, unchanged."""
    bar = Polygon([(-4.0, -0.5), (4.0, -0.5), (4.0, 0.5), (-4.0, 0.5)])
    members = []
    for i, s in enumerate((-10.0, 0.0, 10.0)):
        poly = translate(rotate(bar, 135.0, origin=(0, 0)), xoff=s * math.cos(math.radians(135.0)), yoff=s * math.sin(math.radians(135.0)))
        members.append(Region(shape_id=f"spoke{i}", polygon=poly, thread_index=0, thread_number="1000", area_mm2=poly.area))
    assert tc._line_of_text_deg(members) is not None
    voted = tc._cluster_house_angle_deg(members, fourfold=True, from_line=True)
    assert voted is not None
    assert tc._cluster_house_angle_deg(members, fourfold=True, from_line=True, anchor=True) == voted
