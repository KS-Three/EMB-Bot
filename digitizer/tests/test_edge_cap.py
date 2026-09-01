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

from types import SimpleNamespace

from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, get_fabric
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_border import EDGE_CAP_STYLES, silhouette_cap
from digitizer_core.stage7_sequence import _cap_thread, sequence
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

def test_the_default_is_none():
    assert PipelineConfig().edge_cap == "none"
    assert "none" in EDGE_CAP_STYLES


def test_off_by_default_is_byte_identical_to_the_flag_not_existing():
    """Gate 3's pin. `edge_cap` defaulting to "none" must leave every
    existing plan exactly as it was — same blocks, same stitches, same
    coordinates — or the option is a silent default change wearing an
    opt-in's clothes."""
    base = plan_for(BOTH)
    explicit_off = plan_for(BOTH, edge_cap="none")
    assert cap_block(base) is None
    assert len(base.blocks) == len(explicit_off.blocks)
    for a, b in zip(base.blocks, explicit_off.blocks):
        assert a.thread_index == b.thread_index
        assert [r.points for r in a.runs] == [r.points for r in b.runs]


def test_an_unknown_style_is_inert_rather_than_an_error():
    """A stale project file or a typo must not fail the job — it caps
    nothing, exactly as "none" does."""
    typo = plan_for(BOTH, edge_cap="stain")
    assert cap_block(typo) is None
    assert stitch_count(typo) == stitch_count(plan_for(BOTH))


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
    base = plan_for(BOTH)
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


def test_no_cost_report_when_the_cap_is_off():
    assert _cap_warning(plan_for(BOTH)) is None
    assert _cap_warning(plan_for(BOTH, edge_cap="none")) is None


def test_the_reported_percent_is_against_the_artwork_not_the_total():
    """+13.2% must mean "the design grew by an eighth", not "the cap is an
    eighth of what you now have" — the two differ by enough to matter at the
    sizes this feature costs."""
    base = stitch_count(plan_for(BOTH))
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
