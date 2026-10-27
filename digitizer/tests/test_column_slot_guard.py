"""`cfg.lettering_columns_slot_guard` (2026-10-27, built OFF): a Column-lane
letter walked twice, kept the cheaper way (`digitizer_core/letter_walk.py`,
`docs/satin-split-cuts-2026-10-27.md`).

`columns._span_graph` joins two column ends into one walk node within 1.3 W +
0.3 + the pull. On Becker's bold letters that is 5 mm, wider than an E's slot
or an M's notch, so the walk joined ends the letter does not join and the hop
between them left the letter: a trim inside the letter, which the pro links
needle-down under later satin. ON, the letter is also walked with the corner
fold's `within` guard (the letter grown 0.1 mm must cover the line between
two ends) and keeps that walk only where it cuts no more and leaves no more
travel off later satin (`letter_walk.walk_cost`). On the guard alone four
letters crossed finished satin instead.

`testdata/slot_guard_letters.json`: every Column-lane letter with a cut inside
on the paired jobs whose art is in the repo, its polygon and lane keyword
arguments as stage 7 handed them over with the flag OFF (captured on main
98603fb4 with this flag in place). The pins are the lane's output on those
arguments: no `PipelineConfig` is built, so no flip of a default moves them.
The band fixtures (`becker80_lane_letters` .. `drone62_band_letters`) are the
other Column-lane letters of four of those jobs, read the same way.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, columns, letter_walk

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
LETTERS = {k: v for k, v in json.loads((TESTDATA / "slot_guard_letters.json").read_text(
    encoding="utf-8")).items() if not k.startswith("_")}
#: the letters whose cut inside ON removes (the guarded walk cuts less and
#: lays no more travel off later satin). The rest keep today's walk: Becker's
#: N and E and Gaulke's other E would lay more travel on finished satin; MFab's
#: N and I cut between two walk components, which the guard does not join.
DROPS = {"becker76_M", "becker102_E", "gaulke114_E1"}
BANDS = ("becker80_lane_letters", "fremont92_band_letters", "mfab105_band_letters",
         "drone62_band_letters")


def _kw(raw: dict) -> dict:
    kw = dict(raw)
    for k in ("start_near", "end_near"):
        if kw.get(k) is not None:
            kw[k] = tuple(kw[k])
    if kw.get("counter_holes"):
        kw["counter_holes"] = [Polygon(h["exterior"], h["holes"]) for h in kw["counter_holes"]]
    return kw


def _sew(v: dict, on: bool, sid: str | None = None):
    return columns.lettering_columns_shape(Polygon(v["exterior"], v["holes"]), sid or v["shape_id"],
                                           **_kw(v["kw"]), **({"slot_guard": True} if on else {}))


def _md5(runs) -> str:
    rows = [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)] for r in runs for x, y in r.points]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _band(name: str) -> dict:
    return json.loads((TESTDATA / f"{name}.json").read_text(encoding="utf-8"))


# --- the flag ------------------------------------------------------------------------

def test_flag_is_off_by_default():
    assert PipelineConfig().lettering_columns_slot_guard is False


def test_stage7_wires_the_flag_and_nothing_else():
    src = (Path(__file__).resolve().parent.parent / "digitizer_core" / "stage7_sequence.py").read_text(
        encoding="utf-8")
    assert '**({"slot_guard": True} if cfg.lettering_columns_slot_guard else {})' in src


def test_off_never_reaches_the_pick(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("letter_walk.pick reached with the flag off")
    monkeypatch.setattr(letter_walk, "pick", boom)
    for v in LETTERS.values():
        _sew(v, False)


# --- OFF: byte for byte -----------------------------------------------------------------

def test_the_fixture_holds_the_letters_the_finding_names():
    assert DROPS <= set(LETTERS)
    assert {"becker76_N", "becker76_E", "gaulke114_E2", "mfab105_I"} <= set(LETTERS)


@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_off_is_byte_for_byte(lab):
    """And each one cuts inside today: the class this flag is for."""
    runs, _rep = _sew(LETTERS[lab], False)
    assert _md5(runs) == LETTERS[lab]["off"]["md5"]
    assert letter_walk.walk_cost(runs)[0] == LETTERS[lab]["off"]["cuts"] >= 1


# --- ON -----------------------------------------------------------------------------------

@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_on_never_cuts_more_nor_lays_more_off_later_satin(lab):
    off, _ = _sew(LETTERS[lab], False)
    on, _ = _sew(LETTERS[lab], True)
    (co, to), (cn, tn) = letter_walk.walk_cost(off), letter_walk.walk_cost(on)
    assert cn <= co
    assert tn <= to + letter_walk.TIE_MM


@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_on_drops_the_cut_where_the_guarded_walk_is_cheaper(lab):
    on, rep = _sew(LETTERS[lab], True)
    assert _md5(on) == LETTERS[lab]["on"]["md5"]
    if lab in DROPS:
        assert rep.get("slot_guard") == 1
        assert letter_walk.walk_cost(on)[0] == 0
    else:
        assert _md5(on) == LETTERS[lab]["off"]["md5"]


def test_the_guard_alone_lays_travel_on_finished_satin(monkeypatch):
    """Why the pick: walked with the guard and nothing else, Becker's N at
    76.5 mm loses its cut but lays twice the travel off later satin -- the
    hop from its stem's rail end to the diagonal's centre crosses the stem
    just sewn (4.0 -> 7.9 mm). The pick keeps today's walk there."""
    def guarded(column_runs, cols, cpoly, sid, **kw):
        return column_runs(cols, cpoly, sid, slot_guard=True, **kw)
    off, _ = _sew(LETTERS["becker76_N"], False)
    monkeypatch.setattr(letter_walk, "pick", guarded)
    alone, _ = _sew(LETTERS["becker76_N"], True)
    (co, to), (ca, ta) = letter_walk.walk_cost(off), letter_walk.walk_cost(alone)
    assert ca < co
    assert ta > to + 3.0


def test_the_guard_joins_no_end_across_a_slot(monkeypatch):
    """Becker's E at 76.5 mm: OFF its top arm's root and its middle arm's
    root are one walk node, 4.0 mm apart across the slot; the guarded walk
    (the final sew's second graph) keeps them apart."""
    calls = []
    real = columns._span_graph

    def spy(ready, merge_r, within=None, **k):
        out = real(ready, merge_r, within, **k)
        calls.append((within is not None, len(out[0])))
        return out
    monkeypatch.setattr(columns, "_span_graph", spy)
    _sew(LETTERS["becker76_E"], False)
    off = calls[-1]
    calls.clear()
    _sew(LETTERS["becker76_E"], True)
    today, guarded = calls[-2], calls[-1]
    assert off == today and off[0] is False      # no folded column: no guard today
    assert guarded[0] is True and guarded[1] > off[1]


# --- the other letters of four jobs -----------------------------------------------------

@pytest.mark.parametrize("name", BANDS)
def test_on_the_band_letters_never_cost_more(name):
    """Per letter, ON against OFF on the letters around them (house cross 0,
    as `test_column_italic_lean` reads them). Becker at 80 mm: two letters take
    the guarded walk and the travel off later satin falls 31.0 -> 17.0 mm; the
    Drone: one cut fewer (2 -> 1), 12.3 -> 10.5 mm; MFab hat 22.0 -> 20.6;
    Fremont is unchanged."""
    tot = [0, 0, 0.0, 0.0]
    for sid, v in sorted(_band(name).items()):
        kw = _kw(v["kw"])
        poly = Polygon(v["exterior"], v["holes"])
        off, _ = columns.lettering_columns_shape(poly, v.get("shape_id", sid), **kw)
        on, _ = columns.lettering_columns_shape(poly, v.get("shape_id", sid), **kw, slot_guard=True)
        (co, to), (cn, tn) = letter_walk.walk_cost(off), letter_walk.walk_cost(on)
        assert cn <= co and tn <= to + letter_walk.TIE_MM, (name, sid)
        tot = [tot[0] + co, tot[1] + cn, tot[2] + to, tot[3] + tn]
    assert tot[1] <= tot[0] and tot[3] <= tot[2]
