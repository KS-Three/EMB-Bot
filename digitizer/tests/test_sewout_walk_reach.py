"""`tools/sewout_walk_reach.py` — the sew-out arm for
`satin_walk_cursor_reach_mm` (Kent's ruling 2026-09-20: OFF until cloth
settles it).

The measurement is done; what cloth has to settle is whether a short run of
thread between letters reads better than the trim it replaces. Pinned here:
the arms are the flag's measured settings including OFF, the cases are ones
whose trade differs, and the README the tool writes carries the question and
what each answer flips — the parts that survive without the files, which live
on Kent's machine.
"""
from __future__ import annotations

from digitizer_core import PipelineConfig
from tools import sewout_walk_reach as sw


def test_the_arms_are_off_and_the_two_measured_radii():
    assert [a for a, _ in sw.ARMS] == ["off", "reach4", "reach5"]
    assert [r for _, r in sw.ARMS] == [0.0, 4.0, 5.0]
    # OFF is the shipped default, so one arm is always the engine as it ships.
    assert PipelineConfig().satin_walk_cursor_reach_mm == sw.ARMS[0][1] == 0.0
    assert set(sw.FORMATS) == {"dst", "pes"}


def test_every_case_exists_in_this_checkout_and_says_why_it_is_on_the_sheet():
    assert len(sw.CASES) == 3
    for name, path, width_mm, garment, why in sw.CASES:
        assert path.exists(), f"{name}: {path}"
        assert width_mm > 0 and garment
        assert len(why) > 20, name       # a reason, not a label


def test_the_readme_carries_the_question_and_what_each_answer_flips():
    rows = [{"case": "becker100", "why": "best ratio: 3.0 mm of exposed thread for three trims",
             "arm": "off", "reach_mm": 0.0, "stitches": 8440, "trims": 54,
             "exposed_mm": 0.4, "worst_leg_mm": 0.4, "files": {}}]
    text = sw.readme(rows)
    assert "question D" in text.lower() or "Question D" in text
    assert "stays OFF until cloth" in text
    # The three outcomes a sew-out can have, each with its consequence.
    assert "flip ON at" in text and "stays OFF for good" in text and "needs a gate" in text
    assert "| becker100 | off | 8,440 | 54 | 0.4 | 0.4 |" in text
