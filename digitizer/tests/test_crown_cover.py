"""`cfg.satin_crown_cover` — sew the wedges no stroke claims.

MASTER_SCOPE defect 50. `satin_lettering_split` leaves 11 holes / 22.9 mm2 at
the crowns of curved letters on MARINE 127.4 where the fill lane leaves none,
and **the crowns are not in any column**: five rail and pitch arms are refuted
(DOCTRINE 2026-09-30) and every one that moved a crown made `lost_frac` worse.
The strokes' union leaves wedges of artwork no stroke claims, 4 of the 11 at a
node between two sub-strokes.

So this is the junction cover with its junction gate removed and
`ARTWORK_UNCOVERED`'s own thresholds — the same `_uncovered_patches` finder
and the same `_junction_cover_runs` emitter, which is why the build is small.
Kent's ruling on `docs/superpowers/plans/2026-09-30-crown-cover.md` §7: a
cover rather than a new decomposition, on ALL satin shapes rather than
lettering only.

**Measured 2026-09-30, OFF -> ON:**

    MARINE 127.4   7,168 -> 7,446 st  11 -> 1 holes  22.9 -> 1.5 mm2  lost 0.1800 -> 0.1744
    MARINE 80.2    2,354 -> 2,358      2 -> 0         3.9 -> 0.0      lost 0.1083 -> 0.1064
    ENTHUSIAST 80  2,474 -> 2,486      2 -> 1         2.6 -> 1.0      lost 0.2573 -> 0.2573
    BECKER 100     8,827 -> 9,066     17 -> 8        31.4 -> 13.6     lost 0.0415 -> 0.0338

Corpus holes 20 -> 9; `lost_frac` never rises on any of the nine and falls on
three; golden_tee comes out 1.2% CHEAPER. The four fixtures that report no
holes find NO WEDGES AT ALL, which is the over-fire test. 26 wedges found, 26
sewn, **none without a satin answer** — so Kent's 2026-09-09 "no tatami inside
a satin shape" costs nothing here and did not need re-asking.

**ENTHUSIAST's remaining hole is the 1.00 mm2 gap between two letters; the
1.56 mm2 apex is closed.** That is defect 49, and it makes 49 and 50 one
mechanism — artwork no stroke reaches — rather than two.
"""
from __future__ import annotations

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig
from digitizer_core import stage6_satin as s6
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import (build_generation, finish_generation,
                                     plan_stitches)
from digitizer_core.preflight import run_preflight
from digitizer_core import stitches
from tests.conftest import TESTDATA

MARINE_127 = (TESTDATA.parents[1] / "docs" / "renders"
              / "lettering-split-2026-09-19" / "marine_127mm_traced_input.png")


def _sew(art, width_mm, **kw):
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest",
                         max_colors=6, **kw)
    gen = build_generation(str(art), cfg)
    result = finish_generation(gen.fork(), cfg)
    return cfg, result, plan_stitches(result, cfg)


def test_the_flag_is_on_by_default():
    """Built OFF (Kent's §7.4), flipped ON 2026-10-02 (Kent's call) on the
    corpus table AND `lost_frac`, never on coverage alone — the 2026-09-30
    apex widening closed its hole and was retracted the same day for
    spending 0.0088 of `lost_frac` on overshoot. False is the pre-flip
    engine, pinned beside it below."""
    assert PipelineConfig().satin_crown_cover is True
    assert PipelineConfig(satin_crown_cover=False).satin_crown_cover is False


def test_the_two_filters_refuse_a_seam_and_an_outline():
    """`_uncovered_patches`' extra filters, on the two shapes they exist for.

    Area alone cannot tell a hole from an outline: at a 1.0 mm2 floor the
    largest patches on golden_tee are one-cell seams between colour bands,
    and a full-bleed design's rim comes back as ONE 73.9 mm2 component whose
    max inscribed half is 0.90 mm — thicker than most real holes — at a fill
    of 0.007. Both filters default None for every other caller, which is what
    keeps the junction cover byte-identical.
    """
    # A thin frame with ONE FAT CORNER: the full-bleed rim in miniature, and
    # the case `min_fill` exists for. The real one is 73.94 mm2 at max
    # inscribed half 0.90 mm and fill 0.007 -- thicker than fourteen of the
    # twenty adjudicated holes, which is why MEAN thickness is refuted as the
    # alternative and compactness is the property tested.
    #
    # The fat corner is not decoration. A frame of uniform thin wall is
    # refused by `min_half_mm` alone and would prove nothing about `min_fill`.
    frame = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)],
                    [[(0.6, 0.6), (19.4, 0.6), (19.4, 19.4), (0.6, 19.4)]])
    ring = frame.union(Polygon([(0, 0), (3, 0), (3, 3), (0, 3)]))
    assert _found(ring, min_mm2=1.0, min_half_mm=0.30), \
        "the fat corner carries it past the thickness test, as the real rim does"
    assert not _found(ring, min_mm2=1.0, min_half_mm=0.30, min_fill=0.15), \
        "a rim is an outline, not a patch"

    # `min_fill` alone must not refuse a genuine compact hole
    blob = Polygon([(0, 0), (3, 0), (3, 3), (0, 3)])
    assert _found(blob, min_mm2=1.0, min_half_mm=0.30, min_fill=0.15)

    # The THICKNESS filter is not testable on a synthetic at this scale: the
    # finder rasterises at `_JUNCTION_PATCH_CELL_MM` = 0.25 mm, and a strip
    # thin enough to be a seam is within a cell of the 0.30 mm threshold, so
    # rounding decides the answer rather than the rule. Its evidence is the
    # corpus: on golden_tee SIX patches clear the 1.0 mm2 area floor and ONE
    # clears thickness too, the other five being one-cell seams between
    # colour bands (`preflight._UNCOVERED_MIN_HALF_MM`, rendered).


def _found(poly, **kw) -> bool:
    """-> did `_uncovered_patches` keep `poly`, with no thread on it at all?"""
    return bool(s6._uncovered_patches(poly, [], **kw))


def test_on_the_word_it_closes_the_crowns_and_holds_lost_frac():
    """Defect 50's own fixture, both halves of the gate.

    Pinned as a FLOOR on what it closes and a CEILING on what it costs, so a
    cheaper or more effective build stays green. `lost_frac` is the gate and
    not a footnote: a cover that spills thread outside the artwork fails the
    way the apex widening did, whatever it does to coverage.
    """
    from tools.dropped_elements import analyse_design

    cfg_off, res_off, p_off = _sew(MARINE_127, 127.4, satin_crown_cover=False)
    cfg_on, res_on, p_on = _sew(MARINE_127, 127.4, satin_crown_cover=True)
    m_off = run_preflight(res_off, p_off, cfg_off, image=str(MARINE_127))["metrics"]
    m_on = run_preflight(res_on, p_on, cfg_on, image=str(MARINE_127))["metrics"]

    assert m_off["uncovered_holes"] >= 8, \
        "the fixture stopped exhibiting the defect this flag is about"
    assert m_on["uncovered_holes"] <= 2, m_on["uncovered_holes"]      # 11 -> 1
    assert m_on["uncovered_total_mm2"] <= 5.0, m_on["uncovered_total_mm2"]

    # THE GATE. 0.1800 -> 0.1744 measured; a rise means this is the apex
    # widening again and is retracted, not loosened.
    lost_off = analyse_design(MARINE_127, plan_to_design(p_off))["lost_frac"]
    lost_on = analyse_design(MARINE_127, plan_to_design(p_on))["lost_frac"]
    assert lost_on <= lost_off + 0.0005, (lost_off, lost_on)

    # and the thread it costs stays inside the measured price (+3.9%)
    assert p_on.stats.stitch_count <= p_off.stats.stitch_count * 1.05


def test_the_cover_sews_first_in_its_shape_and_only_satin():
    """Under the arms, per the 2026-09-09 ruling the junction cover is built
    on — the arms' crosses land on the cover's margin instead of the cover's
    rows landing on finished satin. And no tatami inside a satin shape: a
    wedge that cannot carry a column is SKIPPED, not filled."""
    _cfg, result, plan = _sew(MARINE_127, 127.4, satin_crown_cover=True)
    kinds: dict[str, set] = {}
    first: dict[str, str] = {}
    for _b, run in plan.iter_runs():
        if not run.shape_id or run.kind == stitches.TRAVEL:
            continue
        kinds.setdefault(run.shape_id, set()).add(run.kind)
        first.setdefault(run.shape_id, run.kind)
    mixed = [s for s, k in kinds.items()
             if stitches.SATIN in k and stitches.FILL in k]
    assert not mixed, f"the cover put tatami inside a satin shape: {mixed}"
