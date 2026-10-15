"""`cfg.small_letter_ties` (2026-10-14, default OFF, a gate-1 CANDIDATE): the
lock stitches of bean-letter and skeleton runs laid along the letter's own
centreline (`stitches.spread_tie_in` / `spread_tie_off`), or not laid where a
three-pass bean already sews over its own opening stitch. `TIE_STITCH_MM`,
`TIE_STITCHES` and every other tie are untouched; OFF is byte-identical (the
flat goldens' md5, as `test_bean_ink_shape_gate.py` pins them).
`tools/small_letter_ties.py` is the instrument; its helpers are pinned here.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, digitize, machine, stitches
from digitizer_core.stitches import (RUN, StitchRun, apply_ties, opened_by_retrace,
                                     spread_tie_in, spread_tie_off, tie_run)
from tools import small_letter_ties as slt

from .conftest import TESTDATA

BRIDGE = Path(__file__).resolve().parent.parent / "testdata" / "photo" / "logo_bridge_bar.jpg"

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _line(n: int, pitch: float = 0.45) -> list[tuple[float, float]]:
    return [(i * pitch, 0.0) for i in range(n)]


def _bean(n: int, pitch: float = 0.45, passes: int = 3) -> list[tuple[float, float]]:
    lap = _line(n, pitch)
    out = list(lap)
    for p in range(1, passes):
        leg = list(reversed(lap)) if p % 2 == 1 else list(lap)
        out.extend(leg[1:])
    return out


def _thread(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


# --- the construction ---------------------------------------------------------------

def test_the_constants_are_untouched():
    assert machine.TIE_STITCH_MM == 0.8 and machine.TIE_STITCHES == 3
    assert PipelineConfig().small_letter_ties is False
    assert "small_letter_ties" not in __import__("digitizer_core.config", fromlist=["x"]).SMALL_TEXT_TRUE_SIZE


def test_a_three_pass_bean_opens_itself_and_gets_no_tie_in():
    bean = _bean(6)
    assert opened_by_retrace(bean)
    assert spread_tie_in(bean) == bean
    assert not opened_by_retrace(_line(6))
    assert not opened_by_retrace(_bean(6, passes=2))       # one retrace is not three passes


def test_a_single_run_is_entered_three_stations_in_and_walks_back():
    pts = _line(6)
    out = spread_tie_in(pts)
    assert out == [pts[3], pts[2], pts[1]] + pts
    assert _thread(out) - _thread(pts) == pytest.approx(3 * 0.45)


def test_the_tie_off_walks_back_over_the_last_stations():
    pts = _bean(6)
    out = spread_tie_off(pts)
    assert out[:len(pts)] == pts
    assert out[len(pts):] == [(1.8, 0.0), (1.35, 0.0), (0.9, 0.0)]


def test_the_walk_never_lays_more_thread_than_the_bounce_could():
    long = _line(5, pitch=1.5)                             # 3 legs would be 4.5 mm > 3 x 0.8
    assert spread_tie_off(long)[len(long):] == [long[-2]]  # one leg: always one
    short = _line(3)                                       # only two stations to walk
    assert spread_tie_off(short)[len(short):] == [short[1], short[0]]


def test_only_small_letter_runs_change_and_none_is_the_old_rule():
    def runs():
        a = StitchRun(points=_bean(5), kind=RUN, shape_id="L1")
        b = StitchRun(points=_line(5), kind=stitches.FILL, shape_id="F", trim=True, jump=True)
        c = StitchRun(points=_bean(5), kind=RUN, shape_id="L2", trim=True, jump=True)
        return [a, b, c]
    old, new, none = runs(), runs(), runs()
    apply_ties(old)
    apply_ties(none, small_letters=None)
    apply_ties(new, small_letters={"L1", "L2"})
    assert [r.points for r in none] == [r.points for r in old]
    lead = tie_run(_line(5)[0], _line(5)[1]).points
    assert old[1].points[:4] == lead[:-1] and new[1].points == old[1].points     # the fill keeps its bounce
    assert new[0].points[:len(_bean(5))] == _bean(5)                             # no tie-in on the bean
    assert new[2].points[:len(_bean(5))] == _bean(5)
    # at the 0.45 mm pitch the bounce lays four 0.45 mm legs at each end; the
    # spread lays none at the start and three at the end
    assert _thread(old[0].points) - _thread(_bean(5)) == pytest.approx(8 * 0.45)
    assert _thread(new[0].points) - _thread(_bean(5)) == pytest.approx(3 * 0.45)
    assert {(r.jump, r.trim) for r in new} == {(r.jump, r.trim) for r in old}


def test_a_real_bean_letter_piles_at_least_half_less_lock_thread():
    from digitizer_core.stage6_beanletter import bean_letter
    spines = [[(0.0, 0.0), (0.0, 2.0)], [(1.2, 0.0), (1.2, 2.0)], [(3.0, 0.0), (3.0, 2.0)]]
    out = {}
    for name, small in (("off", None), ("on", {"G"})):
        runs, rep = bean_letter(spines, "G", entry=None, trim_at_mm=1.5, stitch_mm=0.45)
        assert not rep["empty"] and any(r.trim for r in runs)
        bare = sum(_thread(r.points) for r in runs)
        apply_ties(runs, small_letters=small)
        out[name] = sum(_thread(r.points) for r in runs) - bare
    assert out["on"] <= 0.5 * out["off"]


# --- the instrument ---------------------------------------------------------------------

def test_the_tool_reads_both_constructions_at_their_source():
    log: list = []

    def runs():
        return [StitchRun(points=_bean(5), kind=RUN, shape_id="L"),
                StitchRun(points=_line(4), kind=RUN, shape_id="M", trim=True, jump=True)]
    with slt.spy_ties(log):
        stitches.apply_ties(runs())
    s = slt.summarize(log)
    assert s["slots"] == 4 and s["laid"] == 4 and s["legs"] == 16
    assert s["thread_mm"] == pytest.approx(16 * 0.45)
    assert s["pile_mm2"] == pytest.approx(16 * 0.45 * slt.THREAD_MM)
    log.clear()
    with slt.spy_ties(log):
        stitches.apply_ties(runs(), small_letters={"L", "M"})
    s = slt.summarize(log)
    assert s["slots"] == 4 and s["laid"] == 3 and s["untied"] == 1 and s["legs"] == 9
    assert {(t["shape_id"], t["end"]) for t in log if not t["laid"]} == {("L", "in")}


def test_the_tool_helpers():
    assert slt.parse_sets(["small_text_true_size=true", "a=0.5", "b=3", "c=none"]) == {
        "small_text_true_size": True, "a": 0.5, "b": 3, "c": None}
    r = [StitchRun(points=_line(3)), StitchRun(points=_line(3), trim=True), StitchRun(points=[(0, 0)], trim=True)]
    assert slt.tie_slots(r) == [(0, "in"), (1, "in"), (0, "out"), (1, "out")]
    pre = _line(3)
    assert slt.split_added(pre, [(9, 9)] + pre + [(8, 8)], True, True) == ([(9, 9)], [(8, 8)])
    assert slt.change(2.0, 0.5) == "-75%" and slt.change(0, 1) == "-"


def test_word_ties_reads_box_glyph_box_and_ink_apart():
    from shapely.geometry import box
    glyph = box(0, 0, 0.2, 2.0).union(box(0, 0, 1.0, 0.2))        # an L of 0.2 mm strokes
    t = lambda x, y, laid=True: {"anchor": [x, y], "laid": laid, "kind": "run", "tier": "bean",
                                 "legs": [[x, y], [x, y + 0.45]] if laid else []}
    row = {"glyphs_wkt": [glyph.wkt],
           "ties_detail": [t(0.1, 0.5), t(0.8, 1.5), t(1.5, 1.0), t(0.1, 1.5, laid=False)]}
    w = slt.word_ties(row)
    assert (w["ties"]["slots"], w["ties_glyph_box"]["slots"], w["ties_ink"]["slots"]) == (4, 3, 2)
    assert w["ties_ink"]["laid"] == 1 and w["ties_ink"]["pile_mm2"] == pytest.approx(0.45 * 0.4)
    assert w["by_tier"] == {"bean": 3, "bean (untied)": 1}


def test_help_is_cheap():
    import subprocess
    import sys
    out = subprocess.run([sys.executable, "-c", "import sys; import tools.small_letter_ties; "
                          "print('digitizer_core.pipeline' in sys.modules, 'cv2' in sys.modules)"],
                         capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent.parent))
    assert out.stdout.split() == ["False", "False"]


# --- the pipeline ---------------------------------------------------------------------------

def _md5(fixture: str, **kw) -> str:
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none", **kw))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_off_is_byte_identical(fixture):
    assert _md5(fixture) == GOLDEN_MD5[fixture]


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_on_without_small_letters_moves_nothing(fixture):
    """The goldens carry no bean letter or skeleton run: ON is OFF."""
    assert _md5(fixture, small_letter_ties=True) == GOLDEN_MD5[fixture]


@pytest.fixture(scope="module")
def bridge():
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from tools.hairline_logo_bill import shape_digests

    def cfg(**kw):
        return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", max_colors=6,
                              bean_letter_max_stroke_mm=1.0, bean_letter_stitch_mm=0.45, **kw)
    gen = build_generation(str(BRIDGE), cfg())
    out = {}
    for name, kw in (("off", {}), ("on", {"small_letter_ties": True})):
        log: list = []
        sk: dict = {}
        bean: dict = {}
        from tools.small_lettering_compare import spy_tiers
        with spy_tiers(sk, bean), slt.spy_ties(log):
            c = cfg(**kw)
            result = finish_generation(gen.fork(), c)
            plan = plan_stitches(result, c)
        small = {s for s, rep in bean.items() if not rep.get("empty")}
        out[name] = {"plan": plan, "digests": shape_digests(plan), "small": small,
                     "ties": slt.summarize([t for t in log if t["shape_id"] in small])}
    return out


def test_bridge_only_its_bean_letters_change_and_their_lock_thread_halves(bridge):
    off, on = bridge["off"], bridge["on"]
    assert off["small"] and off["small"] == on["small"]
    changed = {k for k in set(off["digests"]) | set(on["digests"])
               if off["digests"].get(k) != on["digests"].get(k)}
    assert changed and changed <= off["small"]
    assert on["plan"].stats.trims == off["plan"].stats.trims
    assert on["ties"]["pile_mm2"] <= 0.5 * off["ties"]["pile_mm2"]


def test_the_flag_reaches_every_tie_call_and_off_passes_nothing(monkeypatch):
    from digitizer_core import stage7_sequence as s7
    import threading
    me = threading.get_ident()
    seen: dict[str, list] = {"off": [], "on": []}
    real = s7._apply_ties
    arm = {"name": "off"}

    def spy(runs, **kw):
        if threading.get_ident() == me:
            seen[arm["name"]].append(kw)
        return real(runs, **kw)
    monkeypatch.setattr(s7, "_apply_ties", spy)
    for name in ("off", "on"):
        arm["name"] = name
        digitize(TESTDATA / "logo_whitebg.png",
                 PipelineConfig(target_width_mm=80.0, edge_cap="none", small_letter_ties=(name == "on")))
    assert seen["off"] and all(kw == {} for kw in seen["off"])
    assert seen["on"] and all(set(kw) == {"small_letters"} for kw in seen["on"])
