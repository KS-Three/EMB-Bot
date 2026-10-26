"""`tools/flag_ledger.py`: every flag built OFF, its kind, PR, flip-sheet row and
memory note, read off config.py (never written).

Pinned on the real config: `pull_comp_by_stroke` (FABRIC, a physical
constant), `sew_enclosed_white` and `cut_every_jump` (HELD, by their memory
notes), `monoline_script_satin` (LAYOUT; `border_by_size`, the brief's
layout pick, is ON since #1057), and `lettering_columns_small_bold`, which is
ON and so is neither a row nor a stale comment. Then each rule on a small
synthetic config and memory folder.
"""
from __future__ import annotations

import textwrap

import pytest

from tools import flag_ledger as L


@pytest.fixture(scope="module")
def real():
    return L.ledger(use_git=False)


def _row(led, name):
    return next((r for r in led["rows"] if r["name"] == name), None)


@pytest.mark.parametrize("name, kind", [
    ("pull_comp_by_stroke", "FABRIC"),
    ("sew_enclosed_white", "HELD"),
    ("cut_every_jump", "HELD"),
    ("monoline_script_satin", "LAYOUT"),
])
def test_known_flags_read_their_kind(real, name, kind):
    r = _row(real, name)
    assert r is not None and r["default"] is False
    assert r["kind"] == kind, (name, r["why"])


def test_known_flags_link_their_memory_and_flip_sheet(real):
    assert _row(real, "pull_comp_by_stroke")["memory"] == "pull-comp-by-stroke-2026-10-22.md"
    assert _row(real, "monoline_script_satin")["memory"] == "monoline-script-satin-2026-10-24.md"
    assert _row(real, "cut_every_jump")["flip_sheet"] is True
    assert _row(real, "pull_comp_by_stroke")["flip_sheet"] is False


def test_a_flag_that_is_on_is_neither_a_row_nor_stale(real):
    assert _row(real, "lettering_columns_small_bold") is None
    assert "lettering_columns_small_bold" not in {s["name"] for s in real["stale"]}
    assert _row(real, "border_by_size") is None


def test_counts_add_up(real):
    assert sum(real["counts"].values()) == len(real["rows"])
    assert set(real["counts"]) <= {"LAYOUT", "FABRIC", "HELD"}


SYNTH = textwrap.dedent('''
    from dataclasses import dataclass

    @dataclass
    class PipelineConfig:
        # A layout flag (built OFF 2026-10-25, #1234). Layout (ruling
        # 2026-10-22: judged in the preview). Off, byte-identical.
        alpha_layout: bool = False
        # A cloth flag, built OFF: a physical constant (ROADMAP gate 1),
        # Kent flips after a sew-out.
        beta_fabric: bool = False
        # Another, built OFF; nothing about cloth or holds here.
        gamma_held: bool = False
        # Built OFF 2026-10-01; flipped ON 2026-10-20 by Kent.
        delta_flipped: bool = True
        # Built OFF 2026-10-01 (the comment was never updated).
        epsilon_stale: bool = True
        # An old opt-in; False is the shipped behaviour.
        zeta_quiet: bool = False
        # A knob, OFF unless set.
        eta_knob: float | None = None
        # A count, OFF at 0 -- not a flag.
        theta_count: int = 0
''')

NOTE = textwrap.dedent('''\
    ---
    name: gamma
    description: the gamma_held study
    ---
    **Held OFF, and why:** `gamma_held` costs trims.
    The keyline-held bodies of `alpha_layout` are no hold.
''')


@pytest.fixture
def synth(tmp_path):
    cfg = tmp_path / "config.py"
    cfg.write_text(SYNTH, encoding="utf-8")
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "gamma-2026-10-01.md").write_text(NOTE, encoding="utf-8")
    return L.ledger(use_git=False, config=cfg, memory=mem)


def test_each_rule_on_a_synthetic_config(synth):
    rows = {r["name"]: r for r in synth["rows"]}
    assert set(rows) == {"alpha_layout", "beta_fabric", "gamma_held", "eta_knob"}
    assert rows["alpha_layout"]["kind"] == "LAYOUT" and rows["alpha_layout"]["pr"] == "1234"
    assert rows["beta_fabric"]["kind"] == "FABRIC"
    assert rows["gamma_held"]["kind"] == "HELD"
    assert rows["gamma_held"]["memory"] == "gamma-2026-10-01.md"
    assert rows["eta_knob"]["default"] is None


def test_stale_and_quiet_are_listed_not_ledgered(synth):
    assert [s["name"] for s in synth["stale"]] == ["epsilon_stale"]
    assert [q["name"] for q in synth["quiet"]] == ["zeta_quiet"]


def test_markdown_carries_every_section(synth):
    md = L.markdown(synth)
    for head in ("### LAYOUT (2)", "### FABRIC (1)", "### HELD (1)", "### Stale comments",
                 "`epsilon_stale`", "`zeta_quiet`"):
        assert head in md, head
