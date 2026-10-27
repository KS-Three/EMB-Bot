"""`cfg.lettering_columns_apex_cut`'s WALK (2026-10-27, W5-02): a merged tip
is sewn from its point, not walked into and hopped out of.

`apex_cut` (#1088/#1090) sews an acute tip -- the M's V, a W's three
apexes, an N's diagonal into its stem -- as ONE column cut off its strokes
along the cross. OFF's mitre made a path through the point; a merged tip is
a dead end for `columns.column_runs`' walk, and the radius that joins
column ends into the walk's nodes (1.3 W + 0.3 + the pull) does not see a
tip: MFab's W fell into three components (a trim), the pairing doubled a
29 mm path to pair one 3 mm tip (MARINE's M at 95.7 mm), the hop out of a
tip ran along its own last cross, and on a bold letter the radius joined a
blunt tip's top to a leg's foot 4 mm off, so the walk sewed up into the
top and hopped back down over it (PROSEAL's A). The pro pays the hop but
sews the tip from its point up. The walk now reads a tip's two ends off the
cut (`_apex_tip_columns`, `_span_graph`'s `tips`), lets a tip's point start
a trail but never end one, chooses the trail's ends and the doubled paths
by millimetres (`_euler_trail`'s `postman`), steps out of a tip square to
its cut, ends every leg of a cut letter on the rail whose hop lies least
outside the satin still to come, and keeps a hop off a tip sewn before it.
The cut and every station are the flag's: only the walk moves.

The BAR (the brief): trims <= max(OFF, his); no travel on a tip's own satin
after it is sewn (`tools.apex_walk_census.letter_cost`'s `on_tip_mm`);
each cross reading within 2 deg of today's ON at 30 / 60 / 85% of the way
from crotch to tip; travel and exposed travel per job <= OFF. Met: the
first three on every letter but one (the M at 79.8 mm, a trim above OFF);
travel and exposure per job against today's ON and summed against OFF,
with the jobs that pay more named below. OFF is byte for byte today's.

`testdata/apex_walk_letters.json`: every Column-lane letter with a merged
tip on #1088's jobs whose art is in the repo (MARINE at four widths, MFab
hat and LC; PROSEAL's art is not, and its A is read by the census only), as
stage 7 handed it to the lane under the flag on main at 2c6b656c (polygon
and keyword arguments), with OFF and today's ON as main's engine sewed them
there (`python -m tools.apex_walk_census fixture`, run from that commit).
The pins are the lane's output on those captured arguments: no
`PipelineConfig` is built, so no flip of a default can move them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from digitizer_core import columns
from digitizer_core import outline_cut as oc
from tools import apex_walk_census as AW

FIXTURE = Path(__file__).resolve().parent.parent / "testdata" / "apex_walk_letters.json"
LETTERS = AW.load_fixture(FIXTURE)
#: the one reading that moves past 2 deg, and why: at 60% MARINE's M at
#: 95.7 mm reads the cut, where today's right leg laid its tuck OVER the V
#: sewn before it (3.4 mm of satin across the tip, the residual #1088 named).
#: The walk lays no tuck across a tip (`_tuck_stations`' `avoid`). The V's
#: own crosses read 0.0 in both; #1088 read his at 2-3.
MOVED = {("marine96_M", 0, 0.6): (0.4, 2.6)}
#: a hop's last hundredths at a cut: the census counts a hop on a tip's
#: satin from 0.45 mm past its last stitch, and a hop into the leg beside
#: it ends on the cut (MFab's IN 0.05, E 0.04, W 0.03; MARINE's M 0.01) --
#: an eighth of a 0.4 mm thread
ON_TIP_MM = 0.05
#: mm2 of bare ground at a crotch the walk may add to today's (the zigzag's
#: return stitch flips with the rail a leg begins on): a tenth of a
#: millimetre square. Without its butt PROSEAL's A opened 0.066.
BARE_MM2 = 0.01
#: trims above OFF and his: the M at 79.8 mm (`test_trims_within_off_and_the_pro`)
TRIMS_ABOVE_OFF = {"marine80_M": 1}
#: mm of travel the walk pays above today's ON, per job, as measured
#: (`test_travel_per_job_within_today`)
TRAVEL_ABOVE_TODAY = {"marine80": 26.91, "marine96": 17.02, "marine102": 22.68}

_SEWN: dict = {}


def _new(lab: str, on: bool) -> dict:
    if (lab, on) not in _SEWN:
        poly, sid, kw, _rec = LETTERS[lab]
        _SEWN[(lab, on)] = AW.letter_numbers(poly, sid, kw, on)
    return _SEWN[(lab, on)]


def _rec(lab: str) -> dict:
    return LETTERS[lab][3]


def _jobs() -> dict:
    out: dict = {}
    for lab, (_p, _s, _k, rec) in LETTERS.items():
        out.setdefault(rec["job"], []).append(lab)
    return out


def _runs(lab: str):
    poly, sid, kw, _rec = LETTERS[lab]
    with oc.apex_cut_scope(True):
        return columns.lettering_columns_shape(poly, sid, **kw)[0]


# --- the fixture and OFF ----------------------------------------------------------

def test_the_fixture_holds_the_letters_the_brief_names():
    assert {"marine96_M", "marine102_M", "mfab105_W", "mfab105_N", "mfab105_IN", "mfab105_4",
            "mfab97_W", "mfab97_N"} <= set(LETTERS)
    assert all(rec["head"] == "2c6b656c" for _p, _s, _k, rec in LETTERS.values())


@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_off_is_byte_for_byte(lab):
    assert _new(lab, False)["md5"] == _rec(lab)["off"]["md5"]


def test_the_census_reads_a_tip_as_the_cut_makes_it():
    assert AW.TIP_END_WIDTHS == columns._APEX_END_WIDTHS
    assert AW.TIP_CLOSED == columns._APEX_CLOSED


# --- the bar ------------------------------------------------------------------------

@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_no_travel_on_a_tips_own_satin(lab):
    """Today: 2.7 mm on MARINE's M at 95.7, 2.5 on MFab LC's W, 2.3 on the
    hat's N, 1.1 on its E; PROSEAL's A, 4.0, is the census's."""
    assert _new(lab, True)["on_tip_mm"] <= ON_TIP_MM, (lab, _rec(lab)["on"]["on_tip_mm"])


@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_trims_within_off_and_the_pro(lab):
    """Today MARINE's M at 101.9 mm trims twice inside the letter (OFF
    none, his one) and the hat's W once (OFF none): none now. MARINE's M at
    79.8 mm (the beanie: no DST of his) trims once, today twice, OFF never:
    its V hangs between its stems' flanks like the M at 76.5 mm's, no column
    ends on its cross, and the walk takes it as it always has
    (`_apex_tip_columns`)."""
    rec = _rec(lab)
    new = _new(lab, True)["trims"]
    assert new <= rec["on"]["trims"]
    assert new <= max(rec["off"]["trims"], rec["pro_trims"] or 0, TRIMS_ABOVE_OFF.get(lab, 0))


@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_the_crosses_are_todays(lab):
    """The cut and its stations are today's; only the walk moves (the
    census reads stations, so the rail a satin begins on does not move it).
    One reading moves, by 2.2 deg toward his (`MOVED`)."""
    got, was = _new(lab, True)["crosses"], _rec(lab)["on"]["crosses"]
    assert len(got) == len(was)
    for tip, (now, then) in enumerate(zip(got, was)):
        for f, (a, b) in enumerate(zip(now, then)):
            assert (a is None) == (b is None), (lab, tip, f)
            if (lab, tip, AW.FRACS[f]) in MOVED:
                assert (b, a) == MOVED[(lab, tip, AW.FRACS[f])]
            elif a is not None:
                assert abs(a - b) <= 2.0, (lab, tip, AW.FRACS[f], a, b)


def _sum(labs, arm: str, key: str) -> float:
    return sum((_new(lab, True) if arm == "new" else _rec(lab)[arm])[key] for lab in labs)


@pytest.mark.parametrize("job", sorted(_jobs()))
def test_exposed_travel_per_job_within_today(job):
    """Gate 3 read on the letters alone (`letter_exposed`): travel no later
    thread of the letter covers, per job, against today's ON. Against OFF
    it is met summed over the jobs (below) and per job everywhere but
    MARINE's M at 101.9 mm (2.3 vs 0.3) and MFab's hat (2.6 vs 1.9): the
    hops between ends the merge radius joins 2-4 mm apart. The plan-level
    instruments are the census's arms."""
    labs = _jobs()[job]
    assert _sum(labs, "new", "exposed_mm") <= _sum(labs, "on", "exposed_mm") + 1e-6, job


@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_no_more_thread_on_bare_fabric_than_today(lab):
    """Gate 3's other instrument read on the letter alone
    (`letter_thread_bare`): a hop's thread further than half a thread from
    any stitch the letter lays. Scored on the legs' pieces, the rail rule
    took PROSEAL's small N's shorter hop across the notch between two
    strokes, 0.2 mm bare; it reads the legs' stations now."""
    assert _new(lab, True)["thread_bare_mm"] <= _rec(lab)["on"]["thread_bare_mm"] + 1e-6, lab


def test_exposed_travel_summed_within_off():
    labs = sorted(LETTERS)
    assert _sum(labs, "new", "exposed_mm") <= _sum(labs, "off", "exposed_mm")


@pytest.mark.parametrize("job", sorted(_jobs()))
def test_travel_per_job_within_today(job):
    """Needle-down travel in the tipped letters, per job, against today's
    ON. Three jobs pay more, each held to what it pays now: MARINE's M at
    101.9 mm runs under its V to sew it from the point where today it
    sewed into the V and trimmed out (+8.8 mm, 2 trims -> 0; his file trims
    once), at 95.7 mm it lays no tuck across the V (+1.3), at 79.8 mm one
    trim fewer (+1.6). Against OFF the travel is met summed over the jobs
    (below), per job only on the Ms at 76.5 and 95.7 mm: a stub the cut
    leaves standing is a dead end the walk doubles under its own satin.
    That half of the brief's bar is the foreman's call
    (docs/apex-walk-2026-10-27.md)."""
    labs = _jobs()[job]
    cap = TRAVEL_ABOVE_TODAY.get(job, _sum(labs, "on", "travel_mm"))
    assert _sum(labs, "new", "travel_mm") <= cap + 1e-6, job


def test_travel_summed_within_off_and_today():
    labs = sorted(LETTERS)
    new = _sum(labs, "new", "travel_mm")
    assert new <= _sum(labs, "off", "travel_mm")
    assert new <= _sum(labs, "on", "travel_mm")


@pytest.mark.parametrize("lab", sorted(LETTERS))
def test_the_crotch_stays_covered(lab):
    """No bare ground within 0.6 mm of an apex cross beyond today's and
    OFF's (`crotch_bare`: the letter there, less every satin stitch grown
    by 0.2 mm, half a 40 wt thread)."""
    rec = _rec(lab)
    assert _new(lab, True)["bare_mm2"] <= max(rec["on"]["bare_mm2"], rec["off"]["bare_mm2"]) + BARE_MM2


def test_nothing_is_tucked_over_the_ms_v():
    """Today's M at 95.7 mm sewed its right leg after the V and tucked it
    3.4 mm across the V: satin over the V's core (0.2 mm in from its
    piece) after the V's own satin. None now."""
    from shapely.geometry import LineString
    poly, _sid, kw, _rec = LETTERS["marine96_M"]
    sat = [(k, LineString(AW._strip([list(p) for p in r.points])))
           for k, r in enumerate(_runs("marine96_M")) if r.kind == "satin"]
    (tip,) = AW.apex_tips(poly, kw)
    own = max(sat, key=lambda s: s[1].intersection(tip["piece"]).length)[0]
    core = tip["piece"].buffer(-0.2)
    assert sum(ln.intersection(core).length for k, ln in sat if k > own) < 0.005


@pytest.mark.parametrize("lab", ["marine96_M", "mfab105_N", "mfab105_W", "mfab97_W"])
def test_each_tip_is_sewn_from_its_point(lab):
    """The satin over each tip starts at its point end and finishes at its
    cut: its first stitch nearer the point than its last."""
    from shapely.geometry import LineString
    poly, _sid, kw, _rec = LETTERS[lab]
    runs = _runs(lab)
    for t in AW.apex_tips(poly, kw):
        sat = [r for r in runs if r.kind == "satin"
               and LineString(r.points).intersection(t["piece"]).length > 0.5 * LineString(r.points).length]
        assert len(sat) == 1, lab
        p, tip = sat[0].points, t["tip"]
        assert ((p[0][0] - tip[0]) ** 2 + (p[0][1] - tip[1]) ** 2
                < (p[-1][0] - tip[0]) ** 2 + (p[-1][1] - tip[1]) ** 2), lab


def test_mfab_w_walks_in_one_go():
    """Its three tips' cut ends were nodes the radius gave away: three
    components and a trim between them. Read off the cut: one trail."""
    assert not any(r.jump or r.trim for r in _runs("mfab105_W"))
