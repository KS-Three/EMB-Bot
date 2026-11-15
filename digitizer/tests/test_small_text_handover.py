"""`cfg.extra["small_text_handover"]` (built OFF 2026-11-14): a line just over
the small-text re-set's cutoff gets the true-size retrace too, so no size of a
line gets neither repair.

ProSeal's tagline at the Studio's hat auto-fit (109.6 mm) measures 4.01 mm --
past the re-set's 0.9 x cap (3.6) and the first restore's 3.0 -- and sewed its
raw trace: FOAM's A without its crossbar, COATINGS' T broken, a 0.13 mm
anti-aliased edge of the P kept and snapped to teal. ProSeal's art is not in
the repo, so the whole-design proof is the PR's sheets; here, the rule and
the wiring."""
from __future__ import annotations

from pathlib import Path

from shapely.geometry import box

from digitizer_core import small_text as st
from digitizer_core.regions import Region


def test_a_thin_other_thread_edge_inside_the_line_goes_a_neighbour_stays():
    letter = Region("L", box(0, 0, 3, 4), 1, "1375", 12.0, meta={})
    edge = Region("E", box(-0.1, 0.2, 0.03, 3.8), 7, "4101", 0.5, meta={})       # 0.13 mm, along the stem
    bar = Region("B", box(-2, 5, 10, 6), 7, "4101", 12.0, meta={})               # the underline, a real shape
    wide = Region("W", box(0.5, 0.5, 2.5, 3.5), 9, "0015", 6.0, meta={})         # a counter-sized piece, not thin
    gone = st._handover_slivers([letter, edge, bar, wide], [letter])
    assert gone == {id(edge)}


def test_the_pipeline_calls_the_handover_only_on(monkeypatch):
    """Off, `restore_small_text` runs once (the first, true-size restore); on,
    once more after the re-set, for the band from 0.9 to `HANDOVER_RATIO` caps
    and with the hand-over gate set."""
    from digitizer_core import small_text
    from digitizer_core.config import PipelineConfig
    from digitizer_core.pipeline import build_generation
    calls = []
    real = small_text.restore_small_text

    def spy(*a, **k):
        calls.append({x: k.get(x) for x in ("cap_mm", "min_cap_mm", "handover")})
        return real(*a, **k)
    monkeypatch.setattr(small_text, "restore_small_text", spy)
    art = Path(__file__).resolve().parents[1] / "testdata" / "logo_whitebg.png"
    build_generation(str(art), PipelineConfig(target_width_mm=40.0))
    assert not any(c["handover"] for c in calls)
    off_calls = len(calls)
    calls.clear()
    build_generation(str(art), PipelineConfig(target_width_mm=40.0,
                                              extra={"small_text_handover": True}))
    hand = [c for c in calls if c["handover"]]
    assert len(calls) == off_calls + 1 and len(hand) == 1
    cfg = PipelineConfig()
    assert hand[0]["cap_mm"] == st.HANDOVER_RATIO * cfg.small_text_cap_mm
    assert hand[0]["min_cap_mm"] == 0.9 * cfg.small_text_cap_mm
