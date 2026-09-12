"""The design-silhouette edge cap (`cfg.edge_cap`, default "none").

The second edge finding of Kent's first physical sew-out (Instagram icon,
80 mm on pique polo, 2026-08-31/09-01). `borders_last` fixed the ORDER the
design's borders sew in; this is the edge that had no border at all. Every
tatami row in the icon's background ended in open air — 100% of the 293.2 mm
outer silhouette uncovered at 1.0 mm, against 0.0% on the glyph edge Kent
rated flawless — because the silhouette is the union of several shapes'
outer edges and each shape's own border rides its own ring.

Two styles, both the engine's own emitters on new geometry (no new geometry
code, and no new physical constant — gate 1 untouched):

- "bean"  -> `run_outline`, three passes at `BEAN_STITCH_MM` stations,
             tracing the silhouette exactly.
- "satin" -> `border_runs(style="auto")`, a `BORDER_WIDTH_MM` column just
             inside the edge, lightening to bean wherever it will not fit.

Measured on the icon at 9,596 stitches: bean +1,207 (+12.6%), satin +1,465
(+15.3%). Kent asked for both, toggleable (2026-09-01) — the two read very
differently on cloth and the choice is per design.

Default "none" is gate 3: a blanket border was measured spending +60% of
stitches to worsen a silhouette. That ruling was about bordering every
shape and this is one ring, which is why the option exists — but nothing
sewn yet says a cap helps, so it stays opt-in. The off-path byte-identity
test below is what pins that claim.
"""
from __future__ import annotations

import math
import time
from types import SimpleNamespace

from shapely import affinity
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, get_fabric, machine
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_border import EDGE_CAP_STYLES, silhouette_cap
from digitizer_core.stage7_sequence import (_cap_thread, _sewn_linear_cover,
                                            sequence)
from digitizer_core.threads import CHART
from digitizer_core.warnings_codes import EDGE_CAP_APPLIED, EDGE_CAP_EMPTY

FAB = get_fabric("pique_knit")


# --- helpers -----------------------------------------------------------------

def bar(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, cy - h / 2)


def region(poly: Polygon, sid: str, thread: int, layer: int,
           meta: dict | None = None) -> Region:
    m = {"layer": layer}
    m.update(meta or {})
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta=m)


# Two abutting fields in different threads. Their shared seam is INTERIOR to
# the design, so the silhouette is the 30x30 outline around both — exactly
# the geometry no per-shape border can cover on its own, and the reason this
# pass exists rather than another rung on stitch_one's ladder.
LEFT = bar(15, 30, cx=-7.5)
RIGHT = bar(15, 30, cx=7.5)
BOTH = [region(LEFT, "L", 3, 0), region(RIGHT, "R", 5, 1)]


def plan_for(regions: list[Region], fabric=FAB, **cfg_kw):
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, fabric, c)
    blocks, warnings = sequence(planned, fabric, c)
    return SimpleNamespace(blocks=blocks, warnings=warnings, cfg=c)


def stitch_count(plan) -> int:
    return sum(b.stitch_count for b in plan.blocks)


def cap_block(plan):
    """The cap's block, found by the shape_id the pass stamps on its runs."""
    for b in plan.blocks:
        if any(r.shape_id == "__edge_cap__" for r in b.runs):
            return b
    return None


# --- the default: nothing happens -------------------------------------------

def test_the_default_is_bean():
    """Kent's flip, 2026-09-11 — "gate it, then flip", after item 14 measured
    5.9-100.0% of the sewn silhouette carrying no linear stitching at all
    (median 76.7%) and the gate brought the bill down to +5.9-26.3%.

    Bean rather than satin because it is cheaper in stitches on five of six
    fixtures and closes the two worst-open designs at least as well; the STYLE
    is still a sew-out's call (gate 1), and this line is where to change it.
    `config.py`'s own comment carries the table.
    """
    assert PipelineConfig().edge_cap == "bean"
    assert "none" in EDGE_CAP_STYLES, "turning it off must stay reachable"


def test_turning_it_off_is_byte_identical_to_the_flag_not_existing():
    """The off-path pin. It used to be the DEFAULT path and is now the
    explicit one (Kent's flip 2026-09-11), which changes which config the
    test has to build and nothing about what it proves: `edge_cap="none"`
    must leave a plan exactly as it was before this pass existed — same
    blocks, same stitches, same coordinates.

    This is what keeps every pre-flip golden meaningful, and what
    `conftest.PRE_FLIP` relies on.
    """
    off = plan_for(BOTH, edge_cap="none")
    assert cap_block(off) is None
    capped = plan_for(BOTH)
    assert cap_block(capped) is not None, "the default should now cap"
    art = [b for b in capped.blocks if b is not cap_block(capped)]
    assert len(art) == len(off.blocks)
    for a, b in zip(art, off.blocks):
        assert a.thread_index == b.thread_index
        assert [r.points for r in a.runs] == [r.points for r in b.runs]


def test_an_unknown_style_is_inert_rather_than_an_error():
    """A stale project file or a typo must not fail the job — it caps
    nothing, exactly as "none" does."""
    typo = plan_for(BOTH, edge_cap="stain")
    assert cap_block(typo) is None
    # Against the OFF plan, not the default one: the default caps now.
    assert stitch_count(typo) == stitch_count(plan_for(BOTH, edge_cap="none"))


# --- both styles emit --------------------------------------------------------

def test_bean_caps_the_silhouette():
    plan = plan_for(BOTH, edge_cap="bean")
    cap = cap_block(plan)
    assert cap is not None, "bean cap emitted no block"
    assert cap.stitch_count > 0


def test_satin_caps_the_silhouette():
    plan = plan_for(BOTH, edge_cap="satin")
    cap = cap_block(plan)
    assert cap is not None, "satin cap emitted no block"
    assert cap.stitch_count > 0


def test_satin_costs_more_thread_than_bean():
    """The artifact's own measured ordering (bean +12.6%, satin +15.3% on
    the icon): a column is heavier than three traced passes. Pins the two
    styles as genuinely different tiers, not one emitter behind two names."""
    bean = cap_block(plan_for(BOTH, edge_cap="bean")).stitch_count
    satin = cap_block(plan_for(BOTH, edge_cap="satin")).stitch_count
    assert satin > bean


def test_a_cap_only_adds_stitches():
    """Whatever the cap costs, it must not disturb the artwork underneath —
    the design's own stitches are unchanged and the cap is purely additive."""
    base = plan_for(BOTH, edge_cap="none")
    for style in ("bean", "satin"):
        plan = plan_for(BOTH, edge_cap=style)
        cap = cap_block(plan)
        assert stitch_count(plan) == stitch_count(base) + cap.stitch_count
        art = [b for b in plan.blocks if b is not cap]
        assert len(art) == len(base.blocks)
        for a, b in zip(art, base.blocks):
            assert [r.points for r in a.runs] == [r.points for r in b.runs]


# --- where it sews, and in what -----------------------------------------------

def test_the_cap_sews_after_every_artwork_block():
    """Craft layering read at design scale: the cap covers row ends, so it
    goes on top of the rows it covers. Anything else and it is buried.

    "After the artwork", not "last in the file" — the detail layer still
    rides above everything (plan row 14's "details last"), so a cap that
    asserted `blocks[-1]` would be pinning the wrong claim and would only
    pass because these fixtures leave `detail_layer` off."""
    for style in ("bean", "satin"):
        plan = plan_for(BOTH, edge_cap=style)
        cap = cap_block(plan)
        cap_at = plan.blocks.index(cap)
        art_at = [i for i, b in enumerate(plan.blocks) if b is not cap]
        assert cap_at > max(art_at)


def test_the_cap_reuses_a_thread_the_design_already_loads():
    """It costs the operator no extra cone. The result palette is
    regions-derived; a cap inventing a colour would grow the cone list for
    a decoration nobody asked to be a new colour."""
    for style in ("bean", "satin"):
        plan = plan_for(BOTH, edge_cap=style)
        cap = cap_block(plan)
        design_threads = {r.thread_index for r in BOTH}
        assert cap.thread_index in design_threads


def test_the_cap_thread_is_the_one_owning_the_most_silhouette():
    """`_cap_thread` driven directly: the cap continues the edge it caps, so
    the colour facing the most bare fabric wins. A region buried inside the
    design contributes nothing."""
    planned, _ = resolve_overlaps(
        [region(bar(30, 30), "OUT", 3, 0), region(bar(4, 4), "IN", 5, 1)],
        FAB, PipelineConfig())
    # Built exactly as `sequence` builds it — from the PLANNED (pull-
    # compensated) polygons, not the artwork ones. Measuring a grown
    # boundary against an ungrown silhouette misses by the compensation
    # itself, which is an order of magnitude wider than the 0.02 mm band.
    silhouette = unary_union([p.polygon for p in planned])
    assert _cap_thread(silhouette, planned, default_thread=99) == 3


def test_the_cap_thread_falls_back_when_nothing_touches_the_edge():
    planned, _ = resolve_overlaps([region(bar(4, 4), "IN", 5, 0)],
                                  FAB, PipelineConfig())
    far = bar(2, 2, cx=500, cy=500)
    assert _cap_thread(far, planned, default_thread=7) == 7


# --- honest on empty ----------------------------------------------------------

def test_a_silhouette_too_small_to_cap_warns_rather_than_going_silent():
    """Silence on an opt-in the user switched on is how a knob comes to look
    broken. Under the loop floors both emitters keep, the cap produces
    nothing — and says so."""
    tiny = [region(bar(0.4, 0.4), "T", 3, 0)]
    plan = plan_for(tiny, edge_cap="bean")
    if cap_block(plan) is None:
        codes = [w["code"] for w in plan.warnings]
        assert EDGE_CAP_EMPTY in codes


# --- what it cost --------------------------------------------------------------

def _cap_warning(plan):
    for w in plan.warnings:
        if w["code"] == EDGE_CAP_APPLIED:
            return w
    return None


def test_the_cap_always_reports_what_it_cost():
    """Reported every time the cap runs, not above some threshold. The cap is
    opt-in, so a message when you opt in is the answer to "what did that buy
    me" — and the cost is NOT predictable from the design's size, so the only
    honest thing is to measure it on this design and say so."""
    for style in ("bean", "satin"):
        plan = plan_for(BOTH, edge_cap=style)
        w = _cap_warning(plan)
        assert w is not None, f"{style} cap reported no cost"
        assert w["style"] == style
        assert w["stitches"] == cap_block(plan).stitch_count
        assert w["edges"] >= 1
        assert w["percent"] > 0
        assert w["cracks_filled"] == 0      # two clean bars: nothing to fill


def test_no_cost_report_when_the_cap_is_off():
    assert _cap_warning(plan_for(BOTH, edge_cap="none")) is None
    assert _cap_warning(plan_for(BOTH, edge_cap="stain")) is None
    # ...and one WITH the cap, so the assertions above cannot pass vacuously
    # on a plan that stopped capping for some unrelated reason.
    assert _cap_warning(plan_for(BOTH)) is not None


def test_the_reported_percent_is_against_the_artwork_not_the_total():
    """+13.2% must mean "the design grew by an eighth", not "the cap is an
    eighth of what you now have" — the two differ by enough to matter at the
    sizes this feature costs."""
    base = stitch_count(plan_for(BOTH, edge_cap="none"))
    plan = plan_for(BOTH, edge_cap="satin")
    w = _cap_warning(plan)
    assert w["percent"] == round(100.0 * w["stitches"] / base, 1)


# --- the emitter, driven directly ---------------------------------------------

def test_silhouette_cap_reports_the_style_that_ran():
    poly = bar(30, 30)
    for style in ("bean", "satin"):
        runs, report = silhouette_cap(poly, "S", style=style, entry=None,
                                      trim_at_mm=6.0)
        assert runs, f"{style} emitted nothing on a 30 mm square"
        assert report["style"] == style
        assert report["empty"] is False
        assert report["loops"] >= 1


def test_silhouette_cap_is_inert_on_none_and_on_no_geometry():
    poly = bar(30, 30)
    for bad_style in ("none", "", "satinish"):
        runs, report = silhouette_cap(poly, "S", style=bad_style, entry=None,
                                      trim_at_mm=6.0)
        assert runs == []
        assert report["empty"] is True
        assert report["style"] == "none"
    runs, report = silhouette_cap(None, "S", style="bean", entry=None,
                                  trim_at_mm=6.0)
    assert runs == [] and report["empty"] is True


def test_the_cap_walks_holes_as_well_as_the_outer_edge():
    """A hole's edge is bare fabric on the same terms as the outer boundary.
    Both emitters walk exterior and interiors, so a ring caps twice."""
    ring = bar(30, 30).difference(bar(12, 12))
    solid_runs, _ = silhouette_cap(bar(30, 30), "S", style="bean", entry=None,
                                   trim_at_mm=6.0)
    ring_runs, ring_report = silhouette_cap(ring, "S", style="bean",
                                            entry=None, trim_at_mm=6.0)
    assert ring_report["loops"] > 1
    assert sum(len(r.points) for r in ring_runs) > \
        sum(len(r.points) for r in solid_runs)
    assert ring_report["holes_skipped"] == 0


def test_a_hairline_crack_in_the_silhouette_is_not_an_edge():
    """Kent, 2026-09-08, Instagram icon with Design edge = Satin: a 3.4 mm
    satin bar sewn down the MIDDLE of the design. The silhouette is a union
    of adjacent fills' polygons, and that union carries hairline cracks where
    neighbours' edges nearly coincide — measured 20 on the icon, 0.0-0.1 mm
    wide, up to 7.7 mm long, none owned by any region. The loop gate is a
    PERIMETER floor (`BORDER_MIN_LOOP_MM`, 8.8 mm), so a 7.7 mm crack clears
    it with room to spare, and the crosses cast outward from a hole into the
    host always fit — nothing asked whether the hole was wide enough to be
    an edge. A hole narrower than the column is a crack, not an edge: it is
    filled before either emitter sees the ring, and the cap reads exactly as
    it does on the same shape without the crack."""
    solid = bar(30, 30)
    cracked = solid.difference(bar(0.05, 10))        # perimeter 20.1 mm > 8.8
    assert len(cracked.interiors) == 1
    for style in ("satin", "bean"):
        s_runs, s_rep = silhouette_cap(solid, "S", style=style, entry=None,
                                       trim_at_mm=6.0)
        c_runs, c_rep = silhouette_cap(cracked, "S", style=style, entry=None,
                                       trim_at_mm=6.0)
        assert c_rep["holes_skipped"] == 1, style
        assert c_rep["loops"] == s_rep["loops"], style
        assert c_rep["bean_loops"] == s_rep["bean_loops"], style
        assert sum(len(r.points) for r in c_runs) == \
            sum(len(r.points) for r in s_runs), style


def test_a_crack_is_judged_by_width_not_perimeter():
    """The ruler is the column: `BORDER_WIDTH_MM` (or `width_mm`). A hole the
    column can stand in is an edge; one it cannot is a crack — whatever its
    perimeter says."""
    solid = bar(30, 30)
    wide = solid.difference(bar(2.0, 10))           # 2.0 mm > 1.70: an edge
    thin = solid.difference(bar(1.5, 10))           # 1.5 mm < 1.70: a crack
    _, wide_rep = silhouette_cap(wide, "S", style="bean", entry=None,
                                 trim_at_mm=6.0)
    _, thin_rep = silhouette_cap(thin, "S", style="bean", entry=None,
                                 trim_at_mm=6.0)
    assert wide_rep["holes_skipped"] == 0 and wide_rep["loops"] == 2
    assert thin_rep["holes_skipped"] == 1 and thin_rep["loops"] == 1
    # A narrower column lowers the bar the same way.
    _, thin_narrow = silhouette_cap(thin, "S", style="bean", entry=None,
                                    trim_at_mm=6.0, width_mm=1.0)
    assert thin_narrow["holes_skipped"] == 0 and thin_narrow["loops"] == 2


# --- the gate's own cost ------------------------------------------------------

def _fan_column(cx, n):
    """A satin column turning a corner, as slab-serif lettering makes one.

    The outer rail travels further than the inner one, so consecutive crosses
    overlap and the polyline crosses ITSELF. That is not a pathological
    invention: 106 of Hotel Fremont's 138 linear runs are non-simple for
    exactly this reason, and its satin alone nodes 9,404 points into 49,425
    segments.
    """
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = -0.5 + 2.9 * t
        ai = -0.5 + 2.9 * min(1.0, t * 1.35)            # the inner rail lags
        pts.append((cx + 2.6 * math.cos(a), 2.6 * math.sin(a)) if i % 2
                   else (cx + 0.8 * math.cos(ai), 0.8 * math.sin(ai)))
    return pts


def _satin_blocks(cols: int, n: int):
    """`_sewn_linear_cover` reads only `b.runs`, `r.kind` and `r.points`."""
    runs = [SimpleNamespace(kind="satin", points=_fan_column(c * 3.0, n))
            for c in range(cols)]
    return [SimpleNamespace(runs=runs)]


def test_the_cover_is_the_union_of_each_runs_own_ribbon():
    """The identity the gate is allowed to lean on.

    `buffer(A u B, r) == buffer(A, r) u buffer(B, r)` for positive r — a
    Minkowski sum distributes over a union — so the cover may be assembled
    either way. It must NOT be assembled by noding the raw polylines first:
    see the cost test below for what that costs on real lettering.
    """
    blocks = _satin_blocks(6, 28)
    cover = _sewn_linear_cover(blocks)
    ribbons = unary_union([LineString(r.points).buffer(
        machine.COVERAGE_THREAD_W_MM / 2.0)
        for b in blocks for r in b.runs])
    assert cover.symmetric_difference(ribbons).area < 1e-9


def test_the_cover_does_not_pay_for_noding_the_stitch_path():
    """Hotel Fremont's 86.7-minute prep, 2026-09-12.

    The gate used to hand `unary_union(lines)` — every satin zigzag noded at
    every self- and mutual-crossing — to a single `buffer()`. On Fremont that
    is a 49,535-part MultiLineString, and buffering it ran 86 minutes and
    tens of GB of commit for a cover the design's own 138 ribbons give in
    1.5 seconds.

    This is a budget, not a stopwatch race: on this fixture the shipped
    spelling measures 0.26 s and the noded one 32.2 s, so 4.0 s sits 15x
    above the first and 8x below the second. A box slow enough to fail this
    green could not run the suite at all.
    """
    blocks = _satin_blocks(18, 52)
    t0 = time.time()
    cover = _sewn_linear_cover(blocks)
    elapsed = time.time() - t0
    assert cover is not None and cover.area > 0.0
    assert elapsed < 4.0, f"_sewn_linear_cover took {elapsed:.1f}s"
