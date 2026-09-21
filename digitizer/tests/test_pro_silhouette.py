"""The edge-cap readings — and the two versions of them that were wrong.

Quality review 2026-09-08 item 14. `cfg.edge_cap` closes the design/fabric
boundary where every tatami row ends in open air (MASTER_SCOPE defect 19), and
the question was whether the trade does the same and how much of our own edge
is genuinely open.

**The two sides are not one measurement and these tests exist because two
earlier versions pretended they were.** Ours is exact: we own the plan, so
every run carries the kind that made it, and `_sewn_linear_cover` — the edge
cap's own gate — is what the instrument reads. His is a lower bound through
`border_pro`'s validated fill-edge test, because a stitch file has no kinds and
separating a border from a big tatami's row-turn phases is exactly the
ambiguity that module's B1 and B4 warnings are about.

Version 1 built cover from whole runs and skipped fill runs, reading the pro
76.7-100% uncovered. Version 2 added every column phase back, including a
tatami's own row turns, and read him 0.5-2.2% — and on OUR side called Hotel
Fremont 0.0% uncovered when the engine says its outer edge carries no linear
stitch at all. The tell was the edge-cap gate, which reads real run kinds,
saving Fremont nothing while the tool said it needed nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pro_silhouette                                          # noqa: E402

REFERENCE = Path(__file__).resolve().parent.parent / "testdata" / "reference"
CHEST = REFERENCE / "becker_chest_small_beckers_logo_lc_2_a.dst"


@pytest.mark.skipif(not CHEST.exists(),
                    reason="the commissioned reference files are not in this checkout")
def test_the_pro_borders_a_real_share_of_his_fill_edge():
    """The finding, stated as what it is: a floor, not a coverage figure.

    Only columns `border_pro` certifies as fill-edge borders are counted, each
    credited with the length it actually tracks, so real border satin the test
    misses reads as absent. A number in the tens of percent is the claim; a
    number near zero would mean the credit lookup broke (it did once — the
    tracking fraction is stored as `near_fill`, and reading `near` gave 0.0%
    across every file).
    """
    r = pro_silhouette.pro(CHEST)
    assert r["fills"] > 0 and r["columns"] > 0
    assert r["edge_borders"] > 0, "border_pro found no fill-edge border at all"
    assert r["fill_edge_mm"] > 100.0
    assert 5.0 < r["bordered_pct"] < 95.0, (
        f"{r['bordered_pct']:.1f}% — near 0 means the tracked length is not "
        "being credited; near 100 means a fill's own rows are being counted")


def test_our_reading_uses_the_engines_own_gate():
    """Instrument and engine must be ONE definition of 'covered'.

    This is item 12's lesson applied here: a scorer and an emitter that
    disagree produce a guard that passes while the result gets worse. The
    silhouette cap's gate and this reading share `_sewn_linear_cover`, so a
    change to what counts as linear cover cannot move one without the other.
    """
    from digitizer_core.stage7_sequence import _sewn_linear_cover
    src = Path(pro_silhouette.__file__).read_text(encoding="utf-8")
    assert "_sewn_linear_cover" in src
    assert callable(_sewn_linear_cover)


def test_a_fill_only_design_reads_as_wide_open():
    """Hotel Fremont: a badge whose satin is all interior lettering.

    The engine says 0.0 mm of its outer silhouette carries linear stitching.
    Version 2 of this tool said the opposite, which is what exposed it. Pinned
    at a coarse threshold — the point is the direction, not the decimal.
    """
    r = pro_silhouette.ours("fremont", 80.0, "none")
    assert r["silhouette_mm"] > 50.0
    assert r["uncovered_pct"] > 90.0, (
        f"fremont reads {r['uncovered_pct']:.1f}% uncovered — if this has "
        "genuinely improved, the cap's own gate should show it too")


def test_the_cap_closes_what_the_gate_leaves_open():
    """Cap ON must cover materially more of the edge than cap OFF.

    Not pinned to 0.0%: the gate now leaves alone whatever is already covered,
    and both emitters skip arcs shorter than a column is wide, so a design can
    legitimately finish with a few millimetres open.
    """
    off = pro_silhouette.ours("fremont", 80.0, "none")
    on = pro_silhouette.ours("fremont", 80.0, "bean")
    assert on["uncovered_pct"] < off["uncovered_pct"] - 50.0
    assert on["stitches"] > off["stitches"], "a cap that costs nothing sewed nothing"
