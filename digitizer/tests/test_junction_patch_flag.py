"""`cfg.satin_patch_junctions` — sew what the satin tier missed. DEFAULT OFF.

Crosses are placed along a spine, perpendicular to one arm, sized by a ray
that measures THAT arm's width. Where several arms meet, each ray reads its
own arm's ~2 mm rather than the junction's 5+ mm, so the interior is covered
only by whatever overlap the arms happen to have — and on a five-arm junction
it does not close. Measured 2026-09-06: the K's crotch in
`becker_marine_logo` is bare, 37.2 mm2 at 80 mm, and it is the whole reason
that fixture grades B 76 instead of A 100.

Four cross-LENGTH knobs were measured against that hole and none reached it,
because none of them changes where a cross is PLACED (DOCTRINE 2026-09-06).
So this flag does not adjust a cross: it rasterizes the thread actually
emitted, finds the artwork that thread missed, and sews the patches as
tatami.

What these tests exist to guarantee: OFF changes nothing at all, ON actually
clears the grader's finding, and a patch never sews outside the artwork.
"""
from __future__ import annotations

from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.pipeline import digitize
from digitizer_core.preflight import run_preflight
from digitizer_core.stage6_satin import _uncovered_patches, satin_shape
from tests.conftest import TESTDATA

BECKER = TESTDATA / "becker_marine_logo.png"


def _points(plan) -> list:
    return [tuple(map(tuple, r.points)) for _b, r in plan.iter_runs()]


def _cfg(**kw) -> PipelineConfig:
    # `subpixel_edges_upscaled` held OFF: the 37.2 mm2 bare crotch and every
    # patch measured here are becker's on its staircase polygons; Kent's
    # 2026-09-18 flip reads that source from its own pixels, and on the
    # accurate outline band the SATIN cover mode lays a tatami run inside
    # the satin shape (`test_the_satin_cover_*` failed on it). That is an
    # open observation about the satin cover on the new polygon, recorded
    # in scope-history's flip addendum; this file pins the patch mechanism
    # on the polygons it was measured on.
    kw.setdefault("subpixel_edges_upscaled", False)
    # `satin_rails_follow_edge` held at the symmetric model since the envelope
    # went ON (2026-09-30, Kent's ruling on its labelled sitting): the far
    # rail's reach into the crotch takes three stitches off the satin cover's
    # count (4,810 -> 4,807 against the arms alone) where the assertion below
    # wants the cover to cost thread; the finding is still cleared either
    # way. The cover is priced on the rails it was measured on.
    kw.setdefault("satin_rails_follow_edge", False)
    # `satin_corner_twigs` held OFF for the same reason (Kent's 2026-09-19
    # flip): the corner rule re-decomposes the arms the cover patches, and on
    # Becker at 80 mm the satin cover then clears the finding at a net -1
    # stitch (6,528 -> 6,527) instead of adding thread -- the mechanism is
    # measured on the decomposition it was built on.
    kw.setdefault("satin_corner_twigs", False)
    # `satin_junction_stack` held OFF too (Kent's 2026-09-19 flip, the same
    # day): its part C composes this very cover under the arms by default,
    # so OFF and ON would sew the same cover and this file's contrast -- the
    # cover alone against no cover -- would read nothing.
    kw.setdefault("satin_junction_stack", False)
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


def test_the_flag_is_off_by_default():
    """It puts tatami sheen inside a satin letter, which is a look question a
    render answers and a number does not. The default lives here so a change
    to it is a visible diff rather than a quiet one."""
    assert PipelineConfig().satin_patch_junctions is False


def test_off_is_byte_identical_on_the_fixture_the_flag_moves():
    """On the ONE fixture where the flag is known to change the sewn result —
    a byte test on a fixture it cannot move would prove nothing."""
    _r1, p1 = digitize(BECKER, _cfg())
    _r2, p2 = digitize(BECKER, _cfg(satin_patch_junctions=False))
    assert _points(p1) == _points(p2), \
        "the default and an explicit False must be the same plan"


def test_on_clears_the_graders_finding_rather_than_merely_moving_a_number():
    """Proven on the emitted stitches through the grader that reported the
    defect, not on the patch geometry this module computed for itself.

    Measured 2026-09-06 at 80 mm: `ARTWORK_UNCOVERED` 23.8 -> 0.0 mm2,
    B 76 -> B 88, for +383 stitches (~7%). At 90 mm, 44.5 -> 0.0.

    RE-EXPRESSED 2026-09-30. "0.0 and no finding at all" was never a claim
    about this patch — it was a claim about a check that could not resolve a
    hole. Measured on the 0.25 mm grid with no erosion, on this file's own
    `_cfg()` arms:

        off      44.1 mm2, 11 holes, worst 17.0    5,094 stitches
        tatami   23.8 mm2,  9 holes, worst  4.9    5,341 stitches

    The patch does exactly its job — the K's crotch, `Sead76620`, goes
    **30.1 -> 13.1 mm2** and `Sf795e8d1` 4.9 -> 1.6 — and the design's other
    holes were always there. NO shape leaves the list, because the check now
    resolves the residue inside each one, and the score does not move (76
    both ways) because the finding still fires for the rest.

    So the claim is pinned where it belongs: on the SHAPE the patch targets,
    on the design total, and on the thread it costs. Not on a zero.
    """
    r_off, p_off = digitize(BECKER, _cfg())
    rep_off = run_preflight(r_off, p_off, _cfg(), image=BECKER)
    on = _cfg(satin_patch_junctions=True)
    r_on, p_on = digitize(BECKER, on)
    rep_on = run_preflight(r_on, p_on, on, image=BECKER)

    def named(rep):
        f = [x for x in rep["findings"] if x["code"] == "ARTWORK_UNCOVERED"]
        return ({s["shape_id"]: s["missing_mm2"] for s in f[0]["extra"]["shapes"]}
                if f else {})

    off_shapes, on_shapes = named(rep_off), named(rep_on)
    assert off_shapes, \
        "the fixture stopped exhibiting the defect these tests are about"
    assert not (set(on_shapes) - set(off_shapes)), \
        f"the patch OPENED a hole: {sorted(set(on_shapes) - set(off_shapes))}"
    target = max(off_shapes, key=off_shapes.get)          # the K's crotch
    assert on_shapes.get(target, 0.0) <= off_shapes[target] * 0.6, \
        (target, off_shapes[target], on_shapes.get(target))
    assert (rep_on["metrics"]["uncovered_total_mm2"]
            <= rep_off["metrics"]["uncovered_total_mm2"] * 0.7)
    # It must cost SOMETHING — a patch that adds no thread covered nothing.
    assert p_on.stats.stitch_count > p_off.stats.stitch_count


def test_the_patch_sews_under_the_shapes_own_id():
    """Or preflight attributes the fix somewhere other than where it reported
    the defect, and `_owning_region_id` never links the two. The patch is FILL
    inside a shape whose other runs are SATIN, which is how it is recognised.
    """
    _r, plan = digitize(BECKER, _cfg(satin_patch_junctions=True))
    kinds: dict[str, set] = {}
    for _b, run in plan.iter_runs():
        if run.shape_id:
            kinds.setdefault(run.shape_id, set()).add(run.kind)
    patched = [s for s, k in kinds.items()
               if stitches.SATIN in k and stitches.FILL in k]
    assert patched, "no shape carries both satin and a patch fill"


def test_a_patch_never_sews_outside_the_artwork():
    """The patch is GROWN before sewing so its rows overlap the columns around
    it rather than butting against them; that growth is clipped to the
    polygon, and this is what pins the clip.
    """
    result, plan = digitize(BECKER, _cfg(satin_patch_junctions=True))
    by_id = {r.shape_id: r.polygon for r in result.regions}
    checked = 0
    for _b, run in plan.iter_runs():
        if run.kind != stitches.FILL or run.shape_id not in by_id:
            continue
        # A thread's own width of slack, and no more: the patch is clipped to
        # the polygon, but a stitch lands ON that boundary by construction.
        allowed = by_id[run.shape_id].buffer(machine.COVERAGE_THREAD_W_MM)
        outside = [p for p in run.points if not allowed.covers(Point(p))]
        assert not outside, \
            f"{run.shape_id} sews {len(outside)} patch stitches outside its artwork"
        checked += len(run.points)
    assert checked, "no patch runs to check — the flag stopped reaching them"


def test_a_fully_covered_shape_gets_no_patch():
    """The finder must answer "nothing" rather than "a sliver everywhere" on a
    shape the columns already cover — otherwise every satin shape in every
    design pays for a patch pass.
    """
    bar = Polygon([(0, 0), (24, 0), (24, 3), (0, 3)])
    runs, _report = satin_shape(bar, "Sbar", underlay_style="none",
                                trim_at_mm=machine.TRIM_AT_MM)
    assert runs, "the fixture stopped sewing as satin"
    assert _uncovered_patches(bar, runs) == []


def test_both_call_sites_forward_the_flag():
    """`satin_shape` has two callers and a flag wired to one of them is a flag
    that silently does nothing on the other route. Read off the source: a
    keyword this specific cannot appear by accident, and asserting on the
    behaviour of the applique route would need an applique fixture.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "digitizer_core"
    for name in ("stage7_sequence.py", "stage6_applique.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert "patch_junctions=cfg.satin_patch_junctions" in src, \
            f"{name} does not forward cfg.satin_patch_junctions"


def test_a_design_with_no_hole_pays_nothing_for_the_flag():
    """The claim the corpus sweep licenses, pinned rather than asserted in
    prose: 2 of 255 satin shapes leave any bare cloth, so on the other 253
    the pass must find nothing and add nothing.

    `logo_alpha` is one of them — A 100 with 0.0 uncovered at 80/85/90/95/100
    mm. Byte-identity here is the real test of the 5.0 mm2 floor: this pass
    uses a STRICTER coverage test than preflight (no erosion, a finer cell),
    so a floor set too low would find slivers in every clean design and
    charge every one of them for a patch nobody grades.
    """
    art = TESTDATA / "logo_alpha.png"
    _r1, p1 = digitize(art, _cfg())
    _r2, p2 = digitize(art, _cfg(satin_patch_junctions=True))
    assert _points(p1) == _points(p2), \
        "the patch pass changed a design that has no hole to patch"


# --- `satin_patch_junctions = "satin"` (2026-09-09, item 5 PR 2) -------------
#
# The same holes, each sewn as a satin COLUMN along its own long axis and
# placed FIRST in the shape, under the arms (`_junction_cover_runs`). It
# exists to answer the two reasons the tatami patch is OFF: the surface
# inside a satin letter stays satin, and the needle never comes back for
# the hole once the letter is done. `True` is untouched by it.


def _first_run_of(plan, shape_id: str):
    for _b, run in plan.iter_runs():
        if run.shape_id == shape_id:
            return run
    return None


def test_the_satin_cover_clears_the_graders_finding_with_no_tatami():
    """Same proof as the tatami patch — through `ARTWORK_UNCOVERED` on the
    emitted stitches — plus the property that makes it a different answer:
    the shape it patches carries no fill run at all afterwards.

    RE-EXPRESSED 2026-09-30 off "zero", for the same reason as the tatami
    test above. `_cfg()` already holds `satin_junction_stack=False` and says
    why — part C composes this very cover by default, so on the shipped
    engine this flag is a no-op. Re-measured that day, on a bare config, it
    is a no-op down to the stitch: stack ON reads 6,101 stitches and 29.3 mm2
    whether the flag is set or not, while stack OFF reads 5,695 / 47.2
    without the cover and 5,874 / 22.2 with it. The note was right.

    On this file's own arms, the cover shrinks the K's crotch and the total:

        off     44.1 mm2, 11 holes, worst 17.0    5,094 stitches
        satin   27.5 mm2, 11 holes, worst  4.9    5,136 stitches
                `Sead76620` 30.1 -> 16.8, `Sf795e8d1` 4.9 -> 1.6

    It clears no shape outright, because the check now resolves the residue
    inside each one. Pinned on the target shape and the total.

    (One observation for its own look: the stack leaves MORE uncovered on
    this fixture than the cover alone — 29.3 against 22.2 on a bare config —
    while costing 227 more stitches. It buys other things, self-crossings
    311 -> 0 among them, so that is a trade to price, not a verdict.)
    """
    off = _cfg()
    r_off, p_off = digitize(BECKER, off)
    rep_off = run_preflight(r_off, p_off, off, image=BECKER)
    f_off = [x for x in rep_off["findings"] if x["code"] == "ARTWORK_UNCOVERED"]
    assert f_off, "the fixture stopped exhibiting the defect these tests are about"
    shapes_off = {s["shape_id"]: s["missing_mm2"] for s in f_off[0]["extra"]["shapes"]}
    on = _cfg(satin_patch_junctions="satin")
    r_on, p_on = digitize(BECKER, on)
    rep_on = run_preflight(r_on, p_on, on, image=BECKER)
    f_on = [x for x in rep_on["findings"] if x["code"] == "ARTWORK_UNCOVERED"]
    shapes_on = {s["shape_id"]: s["missing_mm2"] for s in f_on[0]["extra"]["shapes"]} if f_on else {}
    target = max(shapes_off, key=shapes_off.get)
    assert shapes_on.get(target, 0.0) <= shapes_off[target] * 0.7, \
        (target, shapes_off[target], shapes_on.get(target))
    assert (rep_on["metrics"]["uncovered_total_mm2"]
            <= rep_off["metrics"]["uncovered_total_mm2"] * 0.75), (
        rep_off["metrics"]["uncovered_total_mm2"],
        rep_on["metrics"]["uncovered_total_mm2"])
    assert p_on.stats.stitch_count > p_off.stats.stitch_count
    kinds: dict[str, set] = {}
    for _b, run in p_on.iter_runs():
        if run.shape_id:
            kinds.setdefault(run.shape_id, set()).add(run.kind)
    assert not [s for s, k in kinds.items() if stitches.SATIN in k and stitches.FILL in k], \
        "the satin cover put tatami inside a satin shape"


def test_the_satin_cover_sews_first_under_the_arms():
    """The cover is the shape's FIRST run — satin, where the tatami patch was
    the shape's last run and a fill — so the arms' crosses land on its margin
    and the needle is never sent back to the hole after the letter."""
    _r_t, p_tatami = digitize(BECKER, _cfg(satin_patch_junctions=True))
    _r_s, p_satin = digitize(BECKER, _cfg(satin_patch_junctions="satin"))
    patched = set()
    last_kind: dict[str, str] = {}
    for _b, run in p_tatami.iter_runs():
        if run.shape_id:
            last_kind[run.shape_id] = run.kind
            if run.kind == stitches.FILL:
                patched.add(run.shape_id)
    satin_shapes = {run.shape_id for _b, run in p_tatami.iter_runs() if run.kind == stitches.SATIN}
    patched &= satin_shapes
    assert patched, "the tatami patch stopped firing on this fixture"
    for sid in patched:
        assert last_kind[sid] == stitches.FILL, "the tatami patch is no longer the shape's last run"
        first = _first_run_of(p_satin, sid)
        assert first is not None and first.kind == stitches.SATIN, \
            f"{sid}: the satin cover is not the shape's first run ({first and first.kind})"


def test_the_satin_cover_never_sews_outside_the_artwork():
    result, plan = digitize(BECKER, _cfg(satin_patch_junctions="satin"))
    by_id = {r.shape_id: r.polygon for r in result.regions}
    checked = 0
    for _b, run in plan.iter_runs():
        if run.kind != stitches.SATIN or run.shape_id not in by_id:
            continue
        allowed = by_id[run.shape_id].buffer(machine.COVERAGE_THREAD_W_MM)
        outside = [p for p in run.points if not allowed.covers(Point(p))]
        assert not outside, \
            f"{run.shape_id} sews {len(outside)} satin stitches outside its artwork"
        checked += len(run.points)
    assert checked


def test_the_tatami_patch_is_untouched_by_the_satin_mode():
    """`True` and `"satin"` are two answers to the same hole; the first one
    must not have moved when the second arrived."""
    _r, plan = digitize(BECKER, _cfg(satin_patch_junctions=True))
    kinds: dict[str, set] = {}
    for _b, run in plan.iter_runs():
        if run.shape_id:
            kinds.setdefault(run.shape_id, set()).add(run.kind)
    assert [s for s, k in kinds.items() if stitches.SATIN in k and stitches.FILL in k], \
        "True no longer sews its tatami patch"


def test_a_design_with_no_hole_pays_nothing_for_the_satin_mode():
    art = TESTDATA / "logo_alpha.png"
    _r1, p1 = digitize(art, _cfg())
    _r2, p2 = digitize(art, _cfg(satin_patch_junctions="satin"))
    assert _points(p1) == _points(p2), \
        "the satin cover changed a design that has no hole to patch"


def test_a_wedge_patch_gets_a_column_along_its_long_axis():
    """`_principal_spine` on a plain wedge: the spine runs along the long
    side, inside the patch, and the half-width is half the short side."""
    from digitizer_core.stage6_satin import _principal_spine
    wedge = Polygon([(0, 0), (8, 0), (8, 2.5), (0, 0.5)])
    got = _principal_spine(wedge)
    assert got is not None
    spine, half = got
    assert len(spine) >= 3
    assert all(wedge.buffer(1e-6).covers(Point(p)) for p in spine)
    dx = spine[-1][0] - spine[0][0]
    dy = spine[-1][1] - spine[0][1]
    assert abs(dx) > 6.0 and abs(dy) < abs(dx) * 0.4, "the spine does not run along the wedge"
    assert 0.5 < half < 2.0
