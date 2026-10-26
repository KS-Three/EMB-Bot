"""`cfg.lettering_columns_italic_lean` (2026-10-25, built OFF): the bars of an
italic word cross along the word's stems (`column_lean.italic_bar`).

Read per cross on ProSeal's italic PROSEAL (`tools/italic_cross.py`, the
pro's hat 85.9 mm and beanie 75.0 mm, stems leaning ~11 deg): he crosses a
bar 71-78 deg off the line of text on the slant's side -- parallel to the
stems, an upright digitizing sheared -- where the Column lane crosses it
square to itself. ON, a tagged word whose letters' stems lean 5-30 deg is
italic, and its straight columns within 25 deg of the line of text are
re-stationed along the stems; everything else is the text lean's.

The OFF pins are the lane's runs over four captured letter sets with the
house cross at 0 (text lean on), digested on `origin/main` at 82b0bf28,
before this flag existed. ON is identical on all four: none is italic.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
from shapely.affinity import affine_transform, rotate, translate
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, column_lean, columns, machine
from tests.conftest import FLIP_2026_10_23
from digitizer_core.column_lean import (ITALIC_BAR_DEG, ITALIC_MIN_DEG, italic_lean, italic_words,
                                        lean_columns, with_italic_lean)
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.outline_cut import letter_columns
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
PITCH = machine.SATIN_SPACING_MM
SLANT = 11.0
#: lane md5 per fixture, house 0, var unset -- `origin/main` 82b0bf28
OFF_MD5 = {
    "becker80_lane_letters": "86caf377cfbbc59ae107008f72cff89e",
    "fremont92_band_letters": "537d4ffbbe7f0d7cea6e29e98240a3b1",
    "mfab105_band_letters": "d0ff65715ae16ed75286c9a396691a98",
    "drone62_band_letters": "054c1d023dbaf2a8484d13f2607b8c27",
}


# --- synthetic italic lettering (y down: the top of a letter is its smaller y) ------

def _e() -> Polygon:
    return (box(0, 0, 3, 16).union(box(0, 0, 11, 3)).union(box(0, 6.5, 9, 9.5))
            .union(box(0, 13, 11, 16)))


def _h() -> Polygon:
    return box(0, 0, 3, 16).union(box(8, 0, 11, 16)).union(box(0, 6.5, 11, 9.5))


def _shear(poly: Polygon, slant_deg: float, base_y: float = 16.0) -> Polygon:
    """Italic: x shifted right by (base_y - y) tan(slant), the top furthest."""
    t = math.tan(math.radians(slant_deg))
    return affine_transform(poly, [1.0, -t, 0.0, 1.0, t * base_y, 0.0])


def _word(slant_deg: float = SLANT) -> list[Region]:
    """E H E: letters whose centroids sit mid-cap, so the line of text reads
    level (two letters of unequal mass, an E and an L, read it at 8 deg)."""
    out = []
    for i, p in enumerate((_e(), _h(), _e())):
        poly = translate(_shear(p, slant_deg), xoff=16.0 * i)
        out.append(Region(shape_id=f"S{i}", polygon=poly, thread_index=0, thread_number="4101",
                          area_mm2=poly.area, source="test",
                          meta={"layer": 0, "text_candidate": True, "lettering_group": True,
                                "text_cluster_id": "TC1", "satin_angle_deg": slant_deg}))
    return out


def _deg(v) -> float:
    return math.degrees(math.atan2(v[1], v[0])) % 180.0


def _off(a: float, b: float) -> float:
    return abs((a - b + 90.0) % 180.0 - 90.0)


def _is_bar(col) -> bool:
    return col.kind == "straight" and col.axis is not None and _off(_deg(col.axis), 0.0) <= ITALIC_BAR_DEG


def _cross_of(station) -> float:
    (ax, ay), (bx, by) = station
    return _deg((bx - ax, by - ay))


# --- the flag and the variable --------------------------------------------------------

def test_flag_default_is_off():
    assert PipelineConfig().lettering_columns_italic_lean is False


def test_the_word_reads_italic_and_upright_reads_nothing():
    words = italic_words(_word())
    assert len(words) == 1
    assert abs(words[0].slant_deg - SLANT) < 1.0
    assert italic_words(_word(0.0)) == []
    assert italic_words(_word(ITALIC_MIN_DEG - 2.0)) == []


def test_the_variable_is_set_only_inside_and_reset_on_exit():
    assert column_lean._ITALIC.get() is None
    with italic_lean(_word()):
        assert len(column_lean._ITALIC.get()) == 1
        with italic_lean(_word(0.0)):
            assert column_lean._ITALIC.get() == ()
        assert len(column_lean._ITALIC.get()) == 1
    assert column_lean._ITALIC.get() is None
    with pytest.raises(RuntimeError):
        with italic_lean(_word()):
            raise RuntimeError
    assert column_lean._ITALIC.get() is None


def test_with_italic_lean_wraps_and_returns():
    seen = []
    run = with_italic_lean(lambda x: seen.append(column_lean._ITALIC.get()) or x * 2, _word())
    assert run(21) == 42
    assert len(seen[0]) == 1 and column_lean._ITALIC.get() is None


# --- the rule ---------------------------------------------------------------------------

def test_bars_cross_along_the_stems_and_nothing_else_moves():
    regions = _word()
    stem_deg = (90.0 + SLANT) % 180.0
    for reg in regions:
        cols = letter_columns(reg.polygon, pitch_mm=PITCH, rail_axis=True).columns
        off = lean_columns(cols, SLANT, PITCH)
        with italic_lean(regions):
            on = lean_columns(cols, SLANT, PITCH)
        bars = 0
        for c, a, b in zip(cols, off, on):
            if _is_bar(c):
                bars += 1
                crosses = [_cross_of(s) for s in b.stations]
                assert max(_off(x, stem_deg) for x in crosses) < 1.0
                assert min(_off(x, stem_deg) for x in (_cross_of(s) for s in a.stations)) > 3.0
                # the spacing between crosses stays the satin spacing
                assert len(b.stations) >= 3
            else:
                assert b.stations == a.stations
        assert bars >= 1


def test_a_bar_past_the_lean_cap_is_left_to_the_text_lean():
    # a bar tilted 25 deg against a 30 deg slant would lean 55 deg off its own normal
    word = column_lean.ItalicWord(line_deg=0.0, slant_deg=30.0, area=None)
    bar = rotate(box(0, 0, 12, 3), -25.0, origin=(6, 1.5))
    cols = [c for c in letter_columns(bar, pitch_mm=PITCH, rail_axis=True).columns if _is_bar(c)]
    assert cols and all(column_lean.italic_bar(c, word, PITCH) is None for c in cols)


def test_an_upright_word_is_the_text_lean_pass():
    regions = _word(0.0)
    for reg in regions:
        cols = letter_columns(reg.polygon, pitch_mm=PITCH, rail_axis=True).columns
        with italic_lean(regions):
            on = lean_columns(cols, 0.0, PITCH)
        assert [c.stations for c in on] == [c.stations for c in lean_columns(cols, 0.0, PITCH)]


def test_a_letter_outside_every_italic_word_is_untouched():
    regions = _word()
    far = translate(_e(), xoff=200.0)
    cols = letter_columns(far, pitch_mm=PITCH, rail_axis=True).columns
    with italic_lean(regions):
        on = lean_columns(cols, 0.0, PITCH)
    assert [c.stations for c in on] == [c.stations for c in lean_columns(cols, 0.0, PITCH)]


def _sew(regions, italic: bool):
    planned = [PlannedRegion(region=r, polygon=r.polygon, sew_index=i) for i, r in enumerate(regions)]
    # the synthetic E was measured before the 2026-10-23 flips (corner fold re-cuts its bars)
    cfg = PipelineConfig(underlay=False, lettering_columns_skip_blobs=False, **FLIP_2026_10_23)
    run = with_italic_lean(sequence, regions) if italic else sequence
    blocks, _w = run(planned, fabric_for_garment("hat_front"), cfg)
    return [r for b in blocks for r in b.runs]


def _bar_crosses(runs, bars) -> list[float]:
    out = []
    for r in runs:
        if r.kind != "satin":
            continue
        for a, b in zip(r.points, r.points[1:]):
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if 2.0 <= math.dist(a, b) <= 4.5 and any(bar.contains_point(m) for bar in bars):
                out.append(_deg((b[0] - a[0], b[1] - a[1])))
    return out


class _Zone:
    def __init__(self, poly):
        from shapely.prepared import prep
        self.p = prep(poly)

    def contains_point(self, m):
        from shapely.geometry import Point
        return self.p.contains(Point(m))


def test_stage7_sews_the_bars_along_the_slant():
    regions = _word()
    # the E's three bars, past the stem, sheared like the letter
    bars = [_Zone(_shear(box(5, y0, 9, y1), SLANT)) for y0, y1 in ((0, 3), (6.5, 9.5), (13, 16))]
    stem_deg = (90.0 + SLANT) % 180.0
    off = _bar_crosses(_sew(regions, False), bars)
    on = _bar_crosses(_sew(regions, True), bars)
    assert len(on) >= 20 and len(off) >= 20
    assert np.median([_off(x, stem_deg) for x in on]) < 1.0
    assert np.median([_off(x, stem_deg) for x in off]) > 3.0


# --- real letters: OFF pinned, upright words identical ON -------------------------------

def _fixture(name: str):
    out = {}
    for sid, v in json.loads((TESTDATA / f"{name}.json").read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        out[sid] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def _lane_md5(letters: dict) -> str:
    rows = []
    for sid, (poly, kw) in sorted(letters.items()):
        runs, _rep = columns.lettering_columns_shape(poly, "pin", **kw, text_lean_deg=0.0)
        rows.append([sid, [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
                           for r in runs for x, y in r.points]])
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _as_word(letters: dict) -> list[Region]:
    return [Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="4101",
                   area_mm2=poly.area, source="test",
                   meta={"layer": 0, "text_candidate": True, "lettering_group": True,
                         "text_cluster_id": "TC1"})
            for sid, (poly, _kw) in letters.items()]


@pytest.mark.parametrize("name", sorted(OFF_MD5))
def test_off_is_the_lane_before_the_flag(name):
    assert _lane_md5(_fixture(name)) == OFF_MD5[name]


@pytest.mark.parametrize("name", ["becker80_lane_letters", "fremont92_band_letters"])
def test_on_an_upright_word_is_byte_identical(name):
    letters = _fixture(name)
    regions = _as_word(letters)
    assert italic_words(regions) == []
    with italic_lean(regions):
        assert _lane_md5(letters) == OFF_MD5[name]


# --- the wiring ---------------------------------------------------------------------------

def test_plan_stitches_sets_the_words_only_when_on(whitebg, monkeypatch):
    from digitizer_core import pipeline
    real = pipeline.sequence
    seen = []

    def spy(*a, **k):
        seen.append(column_lean._ITALIC.get())
        return real(*a, **k)
    monkeypatch.setattr(pipeline, "sequence", spy)
    pipeline.plan_stitches(whitebg, PipelineConfig(target_width_mm=80.0))
    pipeline.plan_stitches(whitebg, PipelineConfig(target_width_mm=80.0, lettering_columns_italic_lean=True))
    assert seen[0] is None and isinstance(seen[1], tuple)
    assert column_lean._ITALIC.get() is None


def test_off_never_reads_the_words(whitebg, monkeypatch):
    from digitizer_core import pipeline

    def boom(*_a, **_k):
        raise AssertionError("italic words read with the flag off")
    monkeypatch.setattr(column_lean, "italic_words", boom)
    pipeline.plan_stitches(whitebg, PipelineConfig(target_width_mm=80.0))


# --- the reader (tools/italic_cross.py) ---------------------------------------------------

def _zigzag(axis_deg: float, cross_deg: float, length: float = 10.0, width: float = 3.0,
            pitch: float = 0.4) -> np.ndarray:
    """A satin column along `axis_deg` whose stitches lie along `cross_deg` (y down)."""
    u = np.array([math.cos(math.radians(axis_deg)), math.sin(math.radians(axis_deg))])
    c = np.array([math.cos(math.radians(cross_deg)), math.sin(math.radians(cross_deg))])
    n = np.array([-u[1], u[0]])
    half = 0.5 * width / abs(float(c @ n))
    pts, t, side = [], 0.0, 1
    while t <= length:
        pts.append(u * t + side * half * c)
        t += pitch / 2
        side = -side
    return np.array(pts)


def _read_one(monkeypatch, pts):
    from tools import italic_cross as ic
    from tools import letter_pieces as LP
    monkeypatch.setattr(LP, "runs_of", lambda _p: [{"block": 0, "pts": pts}])
    return ic.read("synthetic", hmin=2.0)


def test_reader_an_italic_stem_crossed_along_the_line(monkeypatch):
    r = _read_one(monkeypatch, _zigzag(90.0 + SLANT, 0.0))
    s = r["all"]["stem"]
    assert abs(r["slant"] - SLANT) < 0.5
    assert abs(s["cross"]) < 0.5 and abs(s["square"] + SLANT) < 0.5 and s["on_text_5"] == 1.0


def test_reader_a_bar_crossed_along_the_slant(monkeypatch):
    r = _read_one(monkeypatch, np.vstack([_zigzag(90.0 + SLANT, 0.0),
                                          _zigzag(0.0, 90.0 + SLANT) + (20.0, 0.0)]))
    b = r["all"]["bar"]
    assert b["along_slant"] == 1.0 and abs(b["off_slant"]) < 0.5
