"""Sew-out card v8 (`tools/sewout_card_v8.py`, 2026-11-01): `cut_every_jump`
(Python) and `cutEveryJump` (browser) OFF beside ON, the small-text bold
factor and the 0.8 mm halo, on Fremont's lower crest at 92.5 mm Hat,
ENTHUSIAST's tagline at 93 mm, a typed name at 44 mm and Drone's AND DRONE at
62.6 mm Hat. Regenerates the card from the COMMITTED cuts and checks the file
pystitch reads back. Gate 1: the cloth is Kent's.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig, machine  # noqa: E402
from tools import jump_walk_oracle as oracle  # noqa: E402
from tools import sewout_card_v8 as c8  # noqa: E402

COMMITTED = c8.DEFAULT_OUT
FIELDS = {f.name for f in dataclasses.fields(PipelineConfig)}


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("card8")
    return out, c8.generate(out, COMMITTED / "cuts", quiet=True)


def test_every_arm_pins_every_flag_an_arm_touches_and_the_halo():
    """An unpinned OFF would follow a later default flip (`bean-holds-on`)."""
    touched = {k for _label, flags, _clear in c8.ARMS.values() for k in flags}
    assert touched <= set(c8.PIN), touched - set(c8.PIN)
    assert c8.PIN["cut_every_jump"] is False and c8.PIN["small_text_cap_bold_scale"] == 1.45
    for arm, (_label, flags, clear) in c8.ARMS.items():
        ov = c8.overrides(arm)
        assert set(ov) == set(c8.PIN), arm
        assert set(ov) <= FIELDS, set(ov) - FIELDS
        PipelineConfig(**ov)
        assert c8.clear_mm(arm) == clear and clear in (c8.CLEAR_PIN, 0.3), arm
    assert c8.overrides("a") == c8.PIN and c8.clear_mm("a") == c8.CLEAR_PIN
    assert c8.overrides("b")["cut_every_jump"] is True
    assert c8.overrides("c")["small_text_cap_bold_scale"] == 2.0 and c8.clear_mm("c") == c8.CLEAR_PIN
    assert c8.overrides("d") == c8.PIN and c8.clear_mm("d") == 0.3
    assert c8.overrides("e")["small_text_cap_bold_scale"] == 2.0 and c8.clear_mm("e") == 0.3
    assert [c8.TEETH[a] for a in c8.ARMS] == [1, 2, 3, 4, 5]


def test_the_committed_cuts_carry_each_arms_flag_set_and_halo():
    for job, j in c8.JOBS.items():
        cut = c8.load(COMMITTED / "cuts", job)
        assert cut["pin"] == c8.PIN and cut["clear_pin"] == c8.CLEAR_PIN, job
        assert list(cut["arms"]) == list(j["arms"]), job
        for arm, a in cut["arms"].items():
            assert a["overrides"] == c8.overrides(arm), (job, arm)
            assert a["clear_mm"] == c8.clear_mm(arm), (job, arm)
            assert all(r["jump"] or not r["trim"] for r in a["runs"]), (job, arm)
    let = c8.load(COMMITTED / "cuts", "lettering")
    assert let["font"] == "medium_font" and let["width_mm"] == 44
    assert let["arms"]["a"]["cutEveryJump"] is False and let["arms"]["b"]["cutEveryJump"] is True


def test_the_python_flag_walks_fremonts_floats_and_cuts_enthusiasts(card):
    """Today's engine: every Fremont float lies on the white field (walked,
    no cut); ENTHUSIAST's lie between letters on bare cloth (cut)."""
    _out, rb = card
    got = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    fa, fb = got["F", "a"]["hops"], got["F", "b"]["hops"]
    assert fa["floats"] >= 40 and fb["floats"] == 0, (fa, fb)
    assert fb["cuts"] == fa["cuts"], (fa, fb)
    assert fb["sewn_hops"] >= fa["sewn_hops"] + fa["floats"] - 2, (fa, fb)
    fre = c8.load(COMMITTED / "cuts", "fremont")["arms"]
    assert fre["a"]["floats_whole"] > 100 and fre["b"]["floats_whole"] == 0
    assert fre["b"]["trims_whole"] == fre["a"]["trims_whole"]
    ea, eb = got["E", "a"]["hops"], got["E", "b"]["hops"]
    assert ea["floats"] >= 10 and eb["floats"] == 0, (ea, eb)
    assert eb["cuts"] - ea["cuts"] >= 10, (ea, eb)
    ent = c8.load(COMMITTED / "cuts", "enthusiast")["arms"]
    assert ent["b"]["floats_whole"] == 0 and ent["b"]["trims_whole"] > ent["a"]["trims_whole"]


def test_the_browser_flag_cuts_every_float_of_the_typed_name(card):
    _out, rb = card
    got = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    ja, jb = got["J", "a"], got["J", "b"]
    assert ja["hops"]["floats"] == ja["floats_whole"] >= 10 and jb["hops"]["floats"] == 0
    assert jb["hops"]["cuts"] == ja["hops"]["cuts"] + ja["hops"]["floats"]
    assert jb["cut_every_jump"]["cut"] == ja["hops"]["floats"]
    assert rb["lettering"]["floats_off"] == ja["hops"]["floats"] and rb["lettering"]["floats_on"] == 0
    assert rb["lettering"]["oracle"]["bare_segments"] == 0


def test_the_bold_factor_widens_and_the_halo_raises_drones_line(card):
    """Bold alone trades height for width in the same room; the halo buys
    height; together they land on the pro's x1.57 / 1.26."""
    _out, rb = card
    got = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    scale = {arm: next(r["scale"] for r in got["D", arm]["reset"] if r.get("scale")) for arm in "acde"}
    width = {arm: got["D", arm]["reset_satin"]["width_mm"] for arm in "acde"}
    assert width["c"] > width["a"] and scale["c"] < scale["a"], (width, scale)
    assert scale["d"] > scale["a"] + 0.2, scale
    assert width["e"] > width["c"] and scale["e"] > scale["a"], (width, scale)
    assert got["D", "a"]["clear_mm"] == 0.8 and got["D", "d"]["clear_mm"] == 0.3


def test_the_oracle_rode_each_python_cut_and_reads_the_walk(card):
    """The 0.01 mm oracle (`tools/jump_walk_oracle.py`) on each job's
    whole-design OFF and ON files: every float is gone ON, and the README
    says what it found off the thread."""
    _out, rb = card
    assert set(rb["oracle"]) == set(c8.JOBS)
    assert rb["oracle"]["fremont"]["sewn"] and rb["oracle"]["enthusiast"]["sewn"] and not rb["oracle"]["drone"]["sewn"]
    for job, o in rb["oracle"].items():
        assert o["on_uncut_moves"] == 0 and o["off_uncut_moves"] > 0, job
        assert o["sample_step_mm"] == oracle.CELL_MM == 0.01
        assert o["bare_walked_segments"] == len([d for d in o["bare_detail"] if not d["lock"]])
    readme = (COMMITTED / "README.md").read_text(encoding="utf-8")
    assert "**Verdict" in readme


def test_the_oracle_fails_a_stitch_across_cloth_and_passes_one_on_thread():
    """Hand-written files: the oracle shares no code with the walk, so it
    must fail a sewn hop on bare fabric and pass one along a stitch."""
    from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

    def plan(runs):
        return StitchPlan(blocks=[StitchBlock(thread_index=0, thread_number="1", rgb=(0, 0, 0), runs=runs)],
                          palette=[], warnings=[])
    a = StitchRun(points=[(0.0, 0.0), (3.0, 0.0), (6.0, 0.0)], kind="run", jump=True, trim=True)
    b_float = StitchRun(points=[(6.0, 2.0), (9.0, 2.0), (12.0, 2.0)], kind="run", jump=True, trim=False)
    b_sewn = StitchRun(points=[(6.0, 2.0), (9.0, 2.0), (12.0, 2.0)], kind="run", jump=False, trim=False)
    v = oracle.judge(plan([a, b_float]), plan([a, b_sewn]))
    assert v["off_uncut_moves"] == 1 and v["on_uncut_moves"] == 0
    # the hop's two ends sit on thread (a's last stitch, b's first); its middle
    # is a millimetre from either, less half a thread
    assert v["bare_walked_segments"] == 1 and 0.6 < v["worst_off_thread_mm"] < 1.0, v
    c = StitchRun(points=[(0.0, 0.0), (3.0, 0.0), (6.0, 0.0), (9.0, 0.0)], kind="run", jump=True, trim=True)
    d_float = StitchRun(points=[(3.0, 0.0), (0.0, 0.0)], kind="run", jump=True, trim=False)   # back along c
    d_sewn = StitchRun(points=[(3.0, 0.0), (0.0, 0.0)], kind="run", jump=False, trim=False)
    v = oracle.judge(plan([c, d_float]), plan([c, d_sewn]))
    assert v["off_uncut_moves"] == 1 and v["on_uncut_moves"] == 0 and v["bare_walked_segments"] == 0, v


def test_the_crop_keeps_each_pieces_own_cuts_and_floats():
    """A kept run whose predecessor is on the card sews with its own
    jump/cut; a hop the crop made is never a float."""
    base = {"b": 0, "kind": "run", "shape_id": "s", "rgb": [0, 0, 0], "clipped": False}
    runs = [{**base, "seq": 0, "jump": True, "trim": True, "points": [[0, 0], [2, 0]]},
            {**base, "seq": 1, "jump": True, "trim": False, "points": [[3, 0], [5, 0]]},      # a float, kept
            {**base, "seq": 3, "jump": True, "trim": False, "points": [[7, 0], [9, 0]]},      # seq 2 fell outside
            {**base, "seq": 4, "jump": False, "trim": False, "points": [[9.3, 0], [11, 0]]}]  # a walked hop, kept
    items = c8.piece_items({"arms": {"x": {"runs": runs}}}, "x")
    flags = [(r.jump, r.trim) for _s, r in items]
    assert flags == [(True, True), (True, False), (True, True), (False, False)]
    assert c8.hop_counts(items) == {"floats": 1, "cuts": 1, "sewn_hops": 0, "travel_stitches": 0}


def test_the_card_fits_the_hoop_beside_the_patch_two_cones_and_reads_back(card):
    out, rb = card
    assert (out / f"{c8.NAME}.dst").exists() and (out / f"{c8.NAME}.png").exists()
    assert (out / "README.md").exists() and (out / "scoring-sheet.md").exists()
    assert all((out / f"block_{b}.jpg").exists() for b in "FEJD")
    assert rb["stitches_file"] == rb["stitches_plan"]
    assert rb["within_hoop"] and rb["colours"] == 2
    assert rb["extent_mm"][0] <= 92.5 and rb["extent_mm"][1] <= 100.0, rb["extent_mm"]
    assert [s["thread"] for s in rb["stops"]] == ["white", "dark"]
    assert rb["max_record_axis_mm"] <= 12.1 and rb["max_needle_stitch_mm"] <= machine.MAX_STITCH_MM + 0.5


def test_the_committed_readback_matches(card):
    _out, rb = card
    committed = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    for key in ("colours", "within_hoop", "stitches_file", "trims", "arm_md5", "extent_mm", "lettering"):
        assert rb[key] == committed[key], key
