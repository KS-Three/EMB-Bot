"""The bay-hold / edge-cap-pitch card (`tools/sewout_card_bayhold_edgecap.py`, 2026-10-15).

Block B: Fremont's 1895 (81 mm), THE and STAY (92.5 mm) on a Hat in three arms of
`bean_letter_bay_hold` (#967): OFF / 0.2 / 0.25, `small_text_true_size` ON by override.
Block P: a synthetic tatami plate (straight edges, R3 mm curve) and a 4 mm disc in four
arms of `edge_cap_bean_pitch_mm` (#969): OFF / 1.0 / 1.2 / 1.5. These tests pin the
arms (the overrides, the arm count, an md5 of each block's stitch output), regenerate
the card in a temp dir from the COMMITTED cuts, check the file pystitch reads back, and
check the committed machine file is the one the committed read-back describes. The
replays themselves are not re-run (a Fremont digitize is minutes: `--cut` makes the
cuts). ROADMAP gate 1: the cloth is Kent's.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig  # noqa: E402
from tools import sewout_card_bayhold_edgecap as ce  # noqa: E402

COMMITTED = ce.DEFAULT_OUT

#: md5 of each block's stitch output, points rounded to 0.001 mm
BLOCK_MD5 = {
    "B": "af4ef574f783e1ceb1507757ca4a63a8",
    "P": "63971725ed53095b950a16d3520aadc2",
}
ARM_COUNT = 13          # 3 words x 3 hold arms + 4 pitch arms


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("cardbayedge")
    rb = ce.generate(out, COMMITTED / "cuts", None, quiet=True)
    return out, rb


def test_the_arms_differ_only_in_the_knob_under_test_and_are_valid_config():
    # B: the switch is ON in every arm by override; the holds are #967's two candidates
    assert ce.SWITCH == {"small_text_true_size": True}
    assert [lbl for lbl, _o in ce.B_ARMS] == ["off", "hold0.2", "hold0.25"]
    assert ce.B_ARMS[0][1] == {}
    assert ce.B_ARMS[1][1] == {"bean_letter_bay_hold": 0.2}
    assert ce.B_ARMS[2][1] == {"bean_letter_bay_hold": 0.25}
    for _lbl, ov in ce.B_ARMS:
        PipelineConfig(**{**ce.SWITCH, **ov})
    # P: OFF plus #969's three proposed pitches, nothing else varies
    assert ce.P_ARMS == (("off", None), ("p1.0", 1.0), ("p1.2", 1.2), ("p1.5", 1.5))
    for _lbl, pitch in ce.P_ARMS:
        cfg = ce.p_config(pitch)
        assert cfg.edge_cap_bean_pitch_mm == pitch and cfg.thread_wt == 40
        assert cfg.garment_id == ce.GARMENT and cfg.forced_class == "flat"
    # neither knob is on by default: the card does not touch the default config
    d = PipelineConfig()
    assert d.bean_letter_bay_hold is None and d.edge_cap_bean_pitch_mm is None
    # the rows: the 1895 row is 81 mm, THE and STAY are 92.5 mm
    assert ce.B_ROWS == (("1895", "b81"), ("THE", "b925"), ("STAY", "b925"))
    assert ce.CUTS["b81"][0] == 81.0 and ce.CUTS["b925"][0] == 92.5


def test_the_fremont_cuts_reproduce_967s_cells():
    # the OFF arm is main's defaults; each arm's whole-design stream md5 is #967's corpus cell
    for (cut, arm), md5 in ce.POST_967_MD5.items():
        d = ce.load(COMMITTED / "cuts", cut)
        assert d["arms"][arm]["md5"].startswith(md5), (cut, arm)
        assert d["arms"][arm]["overrides"]["small_text_true_size"] is True
    d = ce.load(COMMITTED / "cuts", "b81")
    assert d["arms"]["hold0.2"]["md5"].startswith("fa685e6a") and d["arms"]["hold0.25"]["md5"].startswith("3fc447bd")


def test_the_card_reads_back_whole_and_fits_the_4x4_hoop(card):
    out, rb = card
    assert (out / f"{ce.NAME}.dst").exists() and (out / "README.md").exists()
    assert (out / "scoring-sheet.md").exists()
    assert rb["stitches_file"] == rb["stitches_plan"]
    assert rb["within_hoop"] and rb["colours"] == 1
    assert max(rb["extent_mm"]) <= 100.0
    assert rb["max_record_axis_mm"] <= ce.v2.MAX_RECORD_MM


def test_the_arms_are_all_there_and_the_blocks_are_pinned(card):
    _out, rb = card
    assert len(rb["arm_md5"]) == ARM_COUNT, sorted(rb["arm_md5"])
    assert rb["block_md5"] == BLOCK_MD5
    for word, _cut in ce.B_ROWS:
        for lbl, _o in ce.B_ARMS:
            assert f"B:{word}-{lbl}" in rb["arm_md5"]
    for lbl, _p in ce.P_ARMS:
        assert f"P:{lbl}" in rb["arm_md5"]


def test_each_knob_changes_its_own_arms(card):
    _out, rb = card
    md5, n = rb["arm_md5"], rb["stitches_by_piece"]
    # B: the hold moves station positions: each word differs from OFF in both hold arms
    for word, _cut in ce.B_ROWS:
        assert md5[f"B:{word}-off"] != md5[f"B:{word}-hold0.2"], word
        assert md5[f"B:{word}-off"] != md5[f"B:{word}-hold0.25"], word
    # P: every pitch is a different stitch stream, and a coarser cap sews fewer stitches
    assert len({md5[f"P:{lbl}"] for lbl, _p in ce.P_ARMS}) == 4
    counts = [n[f"P:{lbl}"] for lbl, _p in ce.P_ARMS]
    assert counts == sorted(counts, reverse=True) and counts[0] > counts[-1]


def test_the_p_cuts_carry_the_pitch_they_name():
    d = ce.load(COMMITTED / "cuts", "p")
    for lbl, pitch in ce.P_ARMS:
        a = d["arms"][lbl]
        assert a["edge_cap_bean_pitch_mm"] == pitch
        want = pitch or 0.73
        assert abs(a["cap_median_step_mm"] - want) < 0.06, (lbl, a["cap_median_step_mm"])


def test_the_committed_readback_matches(card):
    _out, rb = card
    committed = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    for key in ("colours", "colour_changes_file", "within_hoop", "blocks", "stitches_file", "block_md5", "arm_md5"):
        assert rb[key] == committed[key], key
    dst = (COMMITTED / f"{ce.NAME}.dst").read_bytes()
    assert hashlib.md5(dst).hexdigest() == committed["dst_md5"]
    readme = (COMMITTED / "README.md").read_text(encoding="utf-8")
    assert committed["dst_md5"] in readme
    for md5 in committed["arm_md5"].values():
        assert md5 in readme
