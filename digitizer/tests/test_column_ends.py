"""Column END shapes: `cfg.lettering_columns_square_ends` (built OFF).

Kent's Fremont 81 mm hat job (PR #898's replay) traced three of his circles to
how the Column lane ENDS a column: HOTEL's E upper serif stood 0.29 mm past
the arm's end face, the N's diagonal foot sewed a 142-deg ear under the
baseline, and the M's V two fans pushed under the vertex with a tuck run out
below it. The flag holds every cross end that starts on an end face on that
face (`columns._hold_end_faces`); `tools/column_ends.py` measures it.

These pin:
- the flag is OFF by default, OFF never reaches the new code, and OFF is
  byte-identical: the lane's runs on the stored aileron glyphs and the three
  circled Fremont letters hash to the same md5 on this branch and on main at
  8240f86c (computed with both trees, 2026-10-13);
- the rule itself, on a bar whose end is a slant: ON, every end-face
  penetration lies on the face's line;
- on the three circled letters (`testdata/fremont81_end_letters.json`, the
  polygons and arguments the lane received in the 81 mm replay): OFF each has
  an end past its face by more than the 0.10 mm candidate, ON none does (the
  M keeps one, at 0.17 mm), no penetration ends past the rails' side reach,
  and neither stitches nor bare outline move by more than a hair.
Fremont is UNREPRESENTATIVE: these reproduce its defects, they size nothing.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, columns, outline_cut
from tools import column_ends as ce
from tools import lowercase_angle as la

LETTERS = Path(__file__).resolve().parent.parent / "testdata" / "fremont81_end_letters.json"
#: the lane's OFF runs on the aileron glyphs (120 and 80 mm) and the three
#: Fremont letters, at the hat's 0.4 mm pull -- identical on this branch and
#: on main at 8240f86c (2026-10-13)
OFF_LANE_MD5 = "fb45063036a8dc1aead7ce4482f48251"


def _fremont() -> dict[str, tuple[Polygon, dict]]:
    data = json.loads(LETTERS.read_text(encoding="utf-8"))
    out = {}
    for key, v in data.items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        out[key] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def _aileron() -> dict[str, tuple[Polygon, dict]]:
    kw = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.4, pull_floor_mm=1.5,
              underlay_style="center_run")
    out = {}
    for tag, path in (("120", la.LETTERS), ("80", la.LETTERS_80)):
        data = json.loads(path.read_text(encoding="utf-8"))["letters"]
        for ch, v in data.items():
            out[f"{tag}:{ch}"] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def lane_md5(letters: dict) -> str:
    rows = []
    for name in sorted(letters):
        poly, kw = letters[name]
        runs, _rep = columns.lettering_columns_shape(poly, "pin", **kw)
        rows.append([name, [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
                            for r in runs for x, y in r.points]])
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


@pytest.fixture(scope="module")
def fremont():
    return _fremont()


@pytest.fixture(scope="module")
def ends(fremont):
    return {key: {arm: ce.letter_ends(poly, kw, square_ends=(arm == "on"))
                  for arm in ("off", "on")}
            for key, (poly, kw) in fremont.items()}


# --- OFF ------------------------------------------------------------------------

def test_the_flag_is_off_by_default():
    assert PipelineConfig().lettering_columns_square_ends is False


def test_off_never_reaches_the_new_code(fremont, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("square_ends code reached with the flag off")
    for name in ("_hold_end_faces", "end_face_hold", "end_faces", "_ring_edges"):
        monkeypatch.setattr(columns, name, boom)
    monkeypatch.setattr(outline_cut, "_mitre_ends", boom)
    for poly, kw in list(fremont.values()) + list(_aileron().values())[:12]:
        columns.lettering_columns_shape(poly, "off", **kw)


def test_off_is_byte_identical_to_main(fremont):
    assert lane_md5({**_aileron(), **{f"fremont:{k}": v for k, v in fremont.items()}}) == OFF_LANE_MD5


# --- the rule ---------------------------------------------------------------------

def test_a_slanted_end_stays_on_its_face():
    """A 0.8 mm bar whose right end is cut at 60 deg: OFF the pull carries
    the end crosses past the slant; ON every cross end that starts on it
    stays on its line."""
    bar = Polygon([(0, 0), (6, 0), (6.46, 0.8), (0, 0.8)])
    cut = outline_cut.letter_columns(bar, pitch_mm=0.4)
    edges = columns._ring_edges(cut.poly)
    slant = next(e for e in edges if abs(e[2][0]) < 0.9 and abs(e[2][1]) > 0.1)
    hold = columns.end_face_hold(cut.columns, cut.poly)

    def past(p):
        return ce._past_line(p, slant, cut.poly)

    worst = {}
    for arm, h in (("off", None), ("on", hold)):
        w = 0.0
        for col in cut.columns:
            a1, b1 = columns.sewn_rails(col, cut.poly, 0.4, 1.5, h)
            for (a0, b0), pa, pb in zip(col.stations, a1, b1):
                for p0, p1 in ((a0, pa), (b0, pb)):
                    if columns._seg_dist(p0, slant) <= columns._FACE_EPS_MM:
                        w = max(w, past(p1))
        worst[arm] = w
    assert worst["off"] > ce.TOL_MM
    assert worst["on"] < 1e-6


def test_end_faces_reads_a_square_cap_as_a_face():
    """A plain upright stem: its top and foot are the letter's terminal
    faces, its sides are not."""
    stem = Polygon([(0, 0), (0.7, 0), (0.7, 5), (0, 5)])
    cut = outline_cut.letter_columns(stem, pitch_mm=0.4)
    edges = columns._ring_edges(cut.poly)
    faces = [edges[k] for k in columns.end_faces(cut.columns, cut.poly)]
    assert faces and all(abs(e[2][1]) < 0.1 for e in faces)        # horizontal only


# --- Kent's circles ----------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(ce.FREMONT_ENDS))
def test_off_reproduces_the_circled_end(ends, key):
    assert ends[key]["off"]["overshoots"] >= 1
    assert ends[key]["off"]["worst_stub_mm"] > 0.24


@pytest.mark.parametrize("key", sorted(ce.FREMONT_ENDS))
def test_on_ends_on_the_outline(ends, key):
    """#907 left the M's vertex one end at 0.17 mm (its last cross slid
    along the right diagonal's edge, off the V's flat foot); a corner held
    on both faces leaves none."""
    on = ends[key]["on"]
    assert on["overshoots"] == 0
    assert on["worst_stub_mm"] <= ce.TOL_MM
    assert on["beyond_pull"] == 0


@pytest.mark.parametrize("key", sorted(ce.FREMONT_ENDS))
def test_on_costs_no_thread_and_no_cover(ends, key):
    off, on = ends[key]["off"], ends[key]["on"]
    assert abs(on["stitches"] - off["stitches"]) <= 0.03 * off["stitches"]
    assert on["bare_mm2"] - off["bare_mm2"] <= 0.05


def test_the_m_travel_no_longer_crosses_its_counter(ends):
    """OFF the M's walk hopped from its right foot to its vertex over the
    counter (1.65 mm of travel outside the satin's reach); ON it does not."""
    assert ends["m_o_junction"]["off"]["travel_off_mm"] > 1.0
    assert ends["m_o_junction"]["on"]["travel_off_mm"] < 0.05


def _end_at(row, xy):
    return min(row["ends"], key=lambda e: math.dist(e["at_mm"], xy))


def test_the_n_foot_is_mitred_to_the_baseline(ends):
    """#907 left the N's diagonal ending in crosses square to the diagonal,
    a chamfer 40 deg off the baseline it stands on; `outline_cut._mitre_ends`
    turns its last crosses onto the baseline."""
    foot = (31.13, 2.9)
    off, on = _end_at(ends["final_t"]["off"], foot), _end_at(ends["final_t"]["on"], foot)
    assert math.dist(off["at_mm"], foot) < 0.3 and math.dist(on["at_mm"], foot) < 0.3
    assert off["cap_deg"] > 30
    assert on["cap_deg"] < 5
    assert on["stub_mm"] <= ce.TOL_MM


def test_a_thin_bar_keeps_its_side_push():
    """A 0.12 mm bar: every cross is inset by a quarter of itself, so its
    side push reaches past `pull - RAIL_REACH_INSET_MM`. #907 cut it back to
    that and the crosses fell under the cross floor (golden_tee 50 mm: 31
    crosses unsewn on one letter, +0.56 mm2 bare); ON keeps them all."""
    bar = Polygon([(0, 0), (6, 0), (6, 0.12), (0, 0.12)])
    kw = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.3, pull_floor_mm=1.5)
    _r, off = columns.lettering_columns_shape(bar, "bar", **kw)
    _r, on = columns.lettering_columns_shape(bar, "bar", **kw, square_ends=True)
    assert off["stations"] > 0 and off["thin_crosses"] == 0
    assert on["thin_crosses"] == 0 and on["stations"] >= off["stations"] - 2


# --- inside connectors --------------------------------------------------------------

def test_inside_connectors_is_off_by_default():
    assert PipelineConfig().lettering_columns_inside_connectors is False


@pytest.mark.parametrize("square", [False, True])
def test_the_m_connector_stays_on_the_letter(fremont, square):
    """Kent's M->O "loop": OFF a 2.5 mm needle-down connector from the M's
    right foot to its vertex, 1.65 mm of it over the bare notch, passed the
    link rule's letter + 0.1 + pull. With `inside_connectors`, alone or with
    `square_ends`, no connector leaves the letter or its satin."""
    poly, kw = fremont["m_o_junction"]
    r = ce.letter_ends(poly, kw, square_ends=square, inside_connectors=True)
    assert r["connector_bare_mm"] < 0.05
    assert r["trims"] == 0


def test_stage7_passes_the_flags(monkeypatch):
    """The stage 7 call carries `square_ends` and `inside_connectors`
    exactly when their flags are on."""
    from digitizer_core import digitize
    from digitizer_core import stage7_sequence as s7
    seen = []
    real = s7.lettering_columns_shape

    def spy(poly, shape_id, **kw):
        seen.append((kw.get("square_ends"), kw.get("inside_connectors")))
        return real(poly, shape_id, **kw)

    monkeypatch.setattr(s7, "lettering_columns_shape", spy)
    digitize(la.FIXTURE.with_suffix(".png"),
             PipelineConfig(target_width_mm=80.0, forced_class="flat",
                            lettering_columns_square_ends=True,
                            lettering_columns_inside_connectors=True))
    assert seen and all(v == (True, True) for v in seen)
