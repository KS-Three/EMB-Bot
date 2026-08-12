"""Stage 6 appliqué — the four-layer tier, and the `steps[]` container under it.

Source for every number asserted here: `docs/specialty-techniques-2026-08-01.md`
§0 (the steps[] prerequisite) and §2 (the appliqué parametric spec), with
source tiers carried: [V] vendor, [S] supplier, [P] production, [D] derived.

The tests are grouped by the defect each one catches:

1. **The stop that vanishes.** Appliqué layers are frequently one thread, and
   the whole feature rests on the machine halting between them anyway. §0 calls
   a merged same-color boundary "the number-one reported appliqué failure in
   software terms". Proven at the byte level, not asserted.
2. **The default that isn't free.** A tier nobody asked for must cost nothing.
3. **The offsets.** Measured off the emitted stitches against B, not read back
   out of the config that generated them.
4. **The resequencer crossing a boundary**, which silently converts an operator
   instruction into nothing.
"""
from __future__ import annotations

import io
import itertools
import math

import pystitch
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, digitize, export, machine
from digitizer_core.stage6_applique import (COLOR_CHANGE, COVER, CUTTING, END,
                                            PLACEMENT, PRE_CUT, TACKDOWN,
                                            TRIM_IN_PLACE, Step,
                                            applique_steps, assert_steps_valid,
                                            cover_rails, min_inscribed_diameter,
                                            nn_group_key, plan_steps, q,
                                            solve_cover_width, solve_geometry,
                                            visible_fabric_width)
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun
from tests.conftest import TESTDATA, cfg

# A shield: convex, big enough to clear every §2.12 gate, with one concave
# notch at the point so the cover's inner rail has a real corner to survive.
SHIELD = Polygon([(-20, -20), (20, -20), (20, 8), (0, 22), (-20, 8)])
BIG_SQUARE = Polygon([(-20, -20), (20, -20), (20, 20), (-20, 20)])
# 2.5 mm wide: under the 4.0 mm no-fabric floor (`2*|c_in| + 1.0` at the rails
# we sew, c_in -1.50), so the two inner cover rails meet and no fabric can show.
# §2.12 prints that floor as 5.9 mm, which is `2*1.95 + 1.0` — §2.4's rails, the
# ones `cover_rails` deliberately does not implement.
THIN_RIBBON = Polygon([(-20, -1.25), (20, -1.25), (20, 1.25), (-20, 1.25)])
# 3.5 mm and 4.5 mm: either side of that 4.0 mm floor, so the floor itself is
# pinned rather than inferred from one fixture.
UNDER_FLOOR = Polygon([(-20, -1.75), (20, -1.75), (20, 1.75), (-20, 1.75)])
OVER_FLOOR = Polygon([(-20, -2.25), (20, -2.25), (20, 2.25), (-20, 2.25)])
# 9 mm across: clears the 8 mm pre-cut floor, fails the 12 mm scissors floor.
SMALL_DISC = Point(0, 0).buffer(4.5, quad_segs=32)

RED = (200, 30, 30)


def _sq(cx, cy, r=5.0):
    return [(cx + r, cy + r), (cx - r, cy + r), (cx - r, cy - r),
            (cx + r, cy - r), (cx + r, cy + r)]


def _signed_offset(pt, poly: Polygon) -> float:
    """Signed normal distance from B: + outward onto the ground, - inward."""
    d = Point(pt).distance(poly.exterior)
    return -d if poly.contains(Point(pt)) else d


def _layer_offsets(steps, poly, kind) -> list[float]:
    return [_signed_offset(p, poly)
            for s in steps for r in s.runs if r.kind == kind for p in r.points]


# =========================================================================
# 1. The stop that vanishes  (§0.1, §0.2)
# =========================================================================

def _raw_records(data: bytes) -> list[str]:
    """Decode DST 3-byte records by the published Tajima table.

    Deliberately NOT pystitch's reader. Reading back with the library that
    wrote the file only proves self-consistency, and the claim under test is
    about what is in the bytes.
    """
    body = data[512:]
    out = []
    for i in range(0, len(body) - 2, 3):
        b3 = body[i + 2]
        if b3 == 0xF3:
            out.append("END")
            break
        out.append("CC" if b3 & 0x40 else ("JUMP" if b3 & 0x80 else "STITCH"))
    return out


def _dst_segments(data: bytes) -> list[list[str]]:
    """The file split at its colour-change records. -> one list per BLOCK.

    This is the operator's view of the file: the machine runs a segment, halts,
    the human does something, the machine runs the next. If the writer merged
    two same-thread blocks there would be one fewer segment and one fewer
    chance to lay the fabric — so the segment count IS the step count, read
    from the bytes rather than from the plan that produced them.
    """
    body = data[512:]
    segs: list[list[str]] = []
    cur: list[str] = []
    for i in range(0, len(body) - 2, 3):
        b3 = body[i + 2]
        if b3 == 0xF3:
            break
        if b3 & 0x40:
            assert body[i:i + 3] == b"\x00\x00\xc3", body[i:i + 3].hex()
            segs.append(cur)
            cur = []
        else:
            cur.append("JUMP" if b3 & 0x80 else "STITCH")
    segs.append(cur)
    return segs


def test_same_thread_stop_survives_dst():
    """DST has no STOP opcode — a stop IS a color change (0xC3), and appliqué
    layers are frequently all one thread. If the writer or pystitch's
    encoder merged adjacent same-color blocks, the machine would sew straight
    through "lay the twill" and the operator would never get the garment.

    §0.2 names this the number-one reported appliqué failure in software terms,
    so it is proven from the bytes rather than assumed.
    """
    plan = StitchPlan(palette=[], blocks=[
        StitchBlock(0, "1801", RED, [StitchRun(points=_sq(-10, 0), kind="run")]),
        StitchBlock(0, "1801", RED, [StitchRun(points=_sq(10, 0), kind="run")]),
    ])
    data = export.export_dst(plan)

    records = _raw_records(data)
    assert records.count("CC") == 1, records
    # The literal record, byte for byte: a zero-delta color change.
    body = data[512:]
    idx = records.index("CC")
    assert body[idx * 3:idx * 3 + 3] == b"\x00\x00\xc3"

    # And it survives a decode, so the machine's parser sees it too.
    pattern = pystitch.read_dst(io.BytesIO(data))
    assert sum(1 for s in pattern.stitches
               if s[2] == pystitch.COLOR_CHANGE) == 1


def test_empty_step_cannot_swallow_its_stop():
    """A block that produces ZERO stitches — a suppressed cover arc, an empty
    tackdown — must not collapse the color change beside it. Two adjacent 0xC3
    records is the correct encoding of "two stops, nothing sewn between", and
    §0.2 warns that an encoder normalizing the command list is exactly how the
    boundary goes missing.
    """
    plan = StitchPlan(palette=[], blocks=[
        StitchBlock(0, "1801", RED, [StitchRun(points=_sq(-10, 0), kind="run")]),
        StitchBlock(0, "1801", RED, []),
        StitchBlock(0, "1801", RED, [StitchRun(points=_sq(10, 0), kind="run")]),
    ])
    records = _raw_records(export.export_dst(plan))
    assert records.count("CC") == 2, records
    # Adjacent, not separated by stitching.
    first = records.index("CC")
    assert records[first + 1] == "CC"


def test_every_applique_step_boundary_is_one_operator_action():
    """§6.5: every step must carry a non-empty action or the emitter should
    refuse to build the file. A stop with no instruction is worse than no stop
    — the machine halts and the operator guesses.
    """
    steps, _ = applique_steps(SHIELD, "S1", solve_geometry())
    for s in steps:
        assert s.action.strip(), f"{s.code} has no operator action"
    assert_steps_valid(steps)

    with pytest.raises(ValueError, match="one color stop = one human action"):
        assert_steps_valid([Step(code="X", label="x", runs=[], action="  ",
                                 function=COLOR_CHANGE)])


# =========================================================================
# 2. The default that isn't free
# =========================================================================

def test_applique_is_off_by_default():
    assert PipelineConfig().applique is False


def test_applique_off_is_byte_identical():
    """The tier existing must not move a single stitch of a design that never
    asked for it. Pinned on the exported DST bytes, not on a stitch count: a
    count can stay equal while geometry moves.
    """
    a = digitize(TESTDATA / "logo_whitebg.png", cfg(garment_id="hat_front"))[1]
    b = digitize(TESTDATA / "logo_whitebg.png",
                 cfg(garment_id="hat_front", applique=False))[1]
    assert export.export_dst(a) == export.export_dst(b)
    assert not [r for _b, r in a.iter_runs()
                if r.kind in (PLACEMENT, CUTTING, TACKDOWN, COVER)]
    assert all(block.step is None for block in a.blocks)


def test_applique_off_leaves_the_resequencer_grouping_untouched():
    """The step-boundary guard replaces stage 7's `sorted({p.sew_index})` with a
    grouping by `(sew_index, step_key)`. With no step keys in play the two must
    produce identical groups in identical order, or the guard has silently
    reordered every design in the shop.
    """
    from digitizer_core.pipeline import fabric_for
    from digitizer_core.stage5_overlap import resolve_overlaps

    c = cfg(garment_id="hat_front")
    result = digitize(TESTDATA / "logo_whitebg.png", c)[0]
    planned, _ = resolve_overlaps(result.regions, fabric_for(c), c)

    keys = sorted({nn_group_key(p) for p in planned})
    # Same partition, same order: one group per sew_index (no group split, no
    # two merged — the key's step and thread elements are constant within a
    # layer on an unedited design), iterated in sew order.
    assert [k[0] for k in keys] == sorted({p.sew_index for p in planned})
    assert all(k[1] == "" for k in keys)


# =========================================================================
# 3. The tolerance solver  (§2.3, §2.13)
# =========================================================================

@pytest.mark.parametrize("discipline, t_hi, w_req", [
    ("tight", 1.5, 2.5),     # [P] duckbill scissors, "absolute minimum (risky)"
    ("normal", 2.0, 3.0),    # [P] beginner safe zone 3.0-3.8; Hatch baseline
    ("loose", 3.0, 4.0),     # [P] Melco DS11 practice: cover 40 pt = 4.0 mm
])
def test_solver_reproduces_the_spec_validation_table(discipline, t_hi, w_req):
    """§2.3's whole argument is that cover width is a tolerance budget, not an
    aesthetic. The equation is [D] — ours — and it earns its keep by landing on
    four independently published numbers. If the solver drifts off this table
    the derivation has stopped being the reason for the number.
    """
    s = solve_cover_width(trim_discipline=discipline)
    assert s["t_hi_mm"] == t_hi
    assert s["w_req_mm"] == pytest.approx(w_req)


@pytest.mark.parametrize("placement, w_req", [
    ("hand", 2.5),          # [V] e 0.75 -> 2*(0.75+0.5)
    ("heat_tacked", 1.8),   # [S] e 0.40 -> Stahls' Poly-Twill 2 mm row
])
def test_pre_cut_width_comes_from_placement_error_not_trim(placement, w_req):
    """Pre-cut has no trim step, so `t_hi` is zero and the placement error is
    the entire budget — §2.3: `W_req = 2*(e + m_edge)`. The heat-tacked row is
    the strongest confirmation in the spec, because Stahls' publishes stitch
    width by letter size for exactly this workflow and it is dramatically
    narrower than every embroidery-appliqué recommendation.
    """
    s = solve_cover_width(mode=PRE_CUT, o_tack=0.0, placement=placement)
    assert s["placement_error_mm"] == machine.APPLIQUE_PLACEMENT_ERROR_MM[placement]
    assert s["w_req_mm"] == pytest.approx(w_req)


def test_cover_rails_never_drift_off_the_solved_width():
    """§2.2: quantize to 0.1 mm BEFORE rail generation "so the two cover rails
    don't accumulate a half-unit drift".

    The defect this catches is real and was hit while building: §2.4's rails
    are -1.95 and +1.05, both exactly on a half-quantum and neither
    representable in DST's 0.1 mm units. Rounding them independently gives
    -2.0 and +1.1 — a 3.1 mm column where the tolerance stack solved for 3.00.
    """
    for share in (0.5, 0.65, 0.7):
        for width in (2.5, 3.0, 3.5, 4.0, 4.5, 5.0):
            solved = dict(solve_cover_width(), width_mm=width)
            c_in, c_out = cover_rails(solved, share)
            assert c_out - c_in == pytest.approx(width, abs=1e-9), (width, share)


@pytest.mark.parametrize("discipline, width, headroom, bury", [
    ("tight", 3.0, 0.7, 0.8),
    ("normal", 3.0, 0.5, 0.5),
    ("loose", 4.0, 0.5, 0.5),
])
def test_the_cover_always_reaches_past_the_raw_edge(discipline, width,
                                                    headroom, bury):
    """The governing constraint §2.3 spends the whole section deriving::

        c_out >= o_tack + t_hi + m_edge      # reach past the raw edge
        c_in  <= o_tack - m_bury             # bury the tackdown thread

    **This test is why §2.4's printed worked default is not implemented.**
    Splitting the whole width 65/35 about B — §2.4's `c_in = -1.95,
    c_out = +1.05` — satisfies neither inequality in general. Measured across
    the three disciplines it gives headroom of +0.50 / **+0.00** / **-0.60** mm,
    so at loose discipline the raw edge lands 0.6 mm OUTSIDE the cover and
    §2.15's first failure mode is guaranteed rather than risked.

    §2.13's solver — rails at the required positions, only the SURPLUS split by
    `inside_share` — holds both inequalities at every discipline, which is what
    the tolerance stack is for.
    """
    g = solve_geometry(trim_discipline=discipline)
    assert g.width_mm == width
    assert g.edge_headroom_mm == pytest.approx(headroom, abs=0.051)
    assert g.bury_mm == pytest.approx(bury, abs=0.051)
    # Both inequalities, stated the way §2.3 states them.
    assert g.c_out >= g.raw_edge_outer + machine.APPLIQUE_MARGIN_EDGE_MM - 0.051
    assert g.c_in <= g.s_tack - machine.APPLIQUE_MARGIN_BURY_MM + 0.051


def test_surplus_width_goes_inward_not_outward():
    """§2.3's 65/35 rule [P], and the only place it is observable: at tight
    discipline the material floor (3.0 mm woven) exceeds `W_req` (2.5 mm), so
    there is 0.5 mm of surplus to place. 65% of it goes inward.

    Inward because the error is asymmetric — an operator can under-trim and
    leave fabric hanging out, but the tackdown thread hard-stops over-trimming.
    """
    g = solve_geometry(trim_discipline="tight")
    surplus = g.width_mm - g.solved["w_req_mm"]
    assert surplus == pytest.approx(0.5)
    # c_in moved 0.65*0.5 = 0.325 inward of its required position (quantized).
    assert g.c_in == pytest.approx(g.solved["c_in_req_mm"] - 0.325, abs=0.051)
    assert abs(g.c_in - g.solved["c_in_req_mm"]) > abs(g.c_out - g.solved["c_out_req_mm"])


def test_quantizer_rounds_half_away_from_zero_on_both_signs():
    """Python's `round` is banker's: `round(-19.5)` is -20 but `round(10.5)` is
    10. Applied to §2.4's two rails that rounds them in OPPOSITE directions and
    narrows the column by a full quantum.
    """
    assert q(-1.95) == -2.0
    assert q(1.05) == 1.1
    assert q(1.5) == 1.5 and q(-1.5) == -1.5


def test_the_worked_default_offsets_and_raw_edge_band():
    """§2.4's worked default, trim-in-place / normal / woven. Everything except
    the cover rails is taken from it verbatim; the rails are §2.13's — see
    `test_the_cover_always_reaches_past_the_raw_edge` for why.

    The raw-edge band is the load-bearing part and it matches §2.4 exactly:
    with the tackdown at -1.00 and a normal trim band of [0.30, 2.00], the raw
    edge lands somewhere in **[-0.70, +1.00]**, which is the interval §2.4
    prints and checks its rails against.
    """
    g = solve_geometry()
    assert (g.s_placement, g.s_cutting, g.s_tack) == (0.0, 0.0, -1.0)
    assert g.width_mm == 3.0
    assert (g.raw_edge_inner, g.raw_edge_outer) == (-0.7, 1.0)
    assert (g.c_in, g.c_out) == (-1.5, 1.5)


def test_a_forced_narrow_cover_is_warned_not_absorbed():
    """`APPLIQUE_COVER_MARGINAL` exists for the cases the solver cannot fix: a
    caller overriding the width downward, or the 5.0 mm ceiling biting on a
    thick material at loose discipline. §2.15's first failure mode is the
    headroom going negative, so it is measured and reported rather than
    silently sewn.
    """
    from digitizer_core.warnings_codes import APPLIQUE_COVER_MARGINAL

    # The solver's own output is never marginal.
    assert not [x for x in check_gates_of(solve_geometry())
                if x["code"] == APPLIQUE_COVER_MARGINAL]

    # Forced to the 2.5 mm floor at loose discipline, it cannot reach.
    tight_cover = solve_geometry(trim_discipline="loose", width_mm=2.5)
    assert tight_cover.edge_headroom_mm < machine.APPLIQUE_MARGIN_EDGE_MM
    assert [x for x in check_gates_of(tight_cover)
            if x["code"] == APPLIQUE_COVER_MARGINAL]


def check_gates_of(geom):
    from digitizer_core.stage6_applique import check_gates
    return check_gates(BIG_SQUARE, geom)


def test_solve_cover_width_can_clamp_from_the_tolerance_stack_itself():
    """`solve_cover_width`'s own `"clamped"` field is not just a hypothetical
    that only an out-of-range override can trip — the solver's own W_req can
    exceed the 5.0 mm ceiling on its own, e.g. an aggressive `m_edge` margin
    (still a public keyword, just not one any published trim discipline uses
    at the default). This pins the field itself is correct before the next
    test pins that a caller finally reads it.
    """
    normal = solve_cover_width()
    assert not normal["clamped"]

    wide_margin = solve_cover_width(m_edge=3.0)
    assert wide_margin["w_req_mm"] > machine.APPLIQUE_COVER_WIDTH_MAX_MM
    assert wide_margin["clamped"]
    assert wide_margin["width_mm"] == machine.APPLIQUE_COVER_WIDTH_MAX_MM


def test_a_clamped_cover_width_is_warned_not_silent():
    """`max_cover_width`'s 5.0 mm clamp used to be silent: `solve_cover_
    width`'s own `"clamped"` field was computed and read by no caller, so a
    design that hit §2.12's named snag-risk ceiling — or §2.13's own 2.5 mm
    "absolute minimum (risky)" floor — sewed with no record the requirement
    and the stitched width disagreed. `check_gates` now reads it and reports
    which bound fired.

    The override escape hatch (`solve_geometry`'s `width_mm`, `PipelineConfig.
    applique_cover_width_mm`) is the practically reachable path — config.py's
    own comment calls it "still clamped to [2.5, 5.0]" — since the solver's
    own W_req never reaches either bound at a published trim discipline.
    Landing exactly ON a bound (not past it) is a legitimate width, not a
    clamp, and must not fire.
    """
    from digitizer_core.warnings_codes import APPLIQUE_COVER_WIDTH_CLAMPED

    # The solver's own in-range output is never clamped.
    assert not [x for x in check_gates_of(solve_geometry())
                if x["code"] == APPLIQUE_COVER_WIDTH_CLAMPED]

    over = solve_geometry(width_mm=8.0)
    assert over.width_mm == machine.APPLIQUE_COVER_WIDTH_MAX_MM
    hits = [x for x in check_gates_of(over)
            if x["code"] == APPLIQUE_COVER_WIDTH_CLAMPED]
    assert hits and hits[0]["bound"] == "ceiling" and hits[0]["width_mm"] == 5.0

    under = solve_geometry(width_mm=1.0)
    assert under.width_mm == machine.APPLIQUE_COVER_WIDTH_FLOOR_MM
    hits = [x for x in check_gates_of(under)
            if x["code"] == APPLIQUE_COVER_WIDTH_CLAMPED]
    assert hits and hits[0]["bound"] == "floor" and hits[0]["width_mm"] == 2.5

    # Exactly on a bound is not past it.
    at_floor = solve_geometry(width_mm=machine.APPLIQUE_COVER_WIDTH_FLOOR_MM)
    assert not [x for x in check_gates_of(at_floor)
                if x["code"] == APPLIQUE_COVER_WIDTH_CLAMPED]


def test_pre_cut_is_fifty_fifty_and_centred_on_b():
    """§2.9's side-by-side: pre-cut cover is "50/50, offset 0", and its tackdown
    is a column straddling B rather than a run inside it. Those are the same
    statement once the chain is right — "cover offset 0 relative to the
    tackdown" and "cover centred on B" only agree when `o_tack` is 0.
    """
    g = solve_geometry(mode=PRE_CUT)
    assert g.inside_share == 0.5
    assert g.s_tack == 0.0
    assert (g.c_in, g.c_out) == (-1.5, 1.5)
    assert g.cover_offset_from_tack == 0.0


def test_the_offset_chain_is_reported_the_way_vendors_state_it():
    """§2.2: vendors CHAIN offsets — tack relative to the guide run, cover
    relative to the tackdown — and warns the published numbers will not
    transfer unless we match that. The chain is reported, not just the
    absolute rails, so a number from a vendor panel can be checked against it.

    The cover link is +1.00 mm because §2.13's rails are symmetric about B:
    centre `(-1.5 + 1.5)/2 = 0.0` against a tackdown at -1.00. §2.4's rails
    would put the centre at -0.5 and the link at +0.5 — that is the number this
    test used to assert, and it went stale when `cover_rails` chose §2.13 over
    §2.4. Nothing else in the file noticed, because every other test reads the
    rails off the geometry instead of hard-coding them.
    """
    g = solve_geometry()
    assert g.tack_offset_from_placement == machine.APPLIQUE_TACK_OFFSET_MM
    assert (g.c_in, g.c_out) == (-1.5, 1.5)
    assert g.cover_offset_from_tack == pytest.approx(1.0)
    # Stated as the chain, not as three absolutes: each link off the last.
    assert g.cover_offset_from_tack == pytest.approx((g.c_in + g.c_out) / 2 - g.s_tack)
    assert g.s_tack == pytest.approx(g.s_placement + g.tack_offset_from_placement)


# =========================================================================
# 4. Emitted geometry — measured off the stitches
# =========================================================================

def test_trim_in_place_emits_four_layers_and_two_stops():
    """§2.1's canonical sequence::

        guide run -> [CC, lay fabric] -> cutting line -> tackdown
                  -> [CC, trim] -> cover

    The trim stop comes AFTER the tackdown, not between the cutting line and
    the tackdown: the tack is what holds the fabric flat while the operator
    cuts, so cutting line and tackdown share one block. Wilcom is explicit and
    §2.1 notes most hobby writeups get this wrong — this test is the guard on
    getting it wrong again.
    """
    steps, report = applique_steps(SHIELD, "S1", solve_geometry())

    assert [s.code for s in steps] == ["PLACE", "CUT+TACK", "COVER"]
    assert report["layers"] == 4
    # Two blocks end in a stop the operator acts on; the third ends the piece.
    assert [s.function for s in steps[:2]] == [COLOR_CHANGE, COLOR_CHANGE]

    # The cutting line and the tackdown are in ONE block, sewn back to back.
    middle_kinds = [r.kind for r in steps[1].runs]
    assert CUTTING in middle_kinds and TACKDOWN in middle_kinds
    assert middle_kinds.index(CUTTING) < middle_kinds.index(TACKDOWN)

    # And the stop after them is the trim, not the lay.
    assert "trim" in steps[1].action.lower()
    assert "lay" in steps[0].action.lower()


def test_pre_cut_collapses_to_one_stop():
    """§2.1: pre-cut is `guide run -> [CC, lay pre-cut piece] -> tackdown ->
    cover`. Melco makes it an explicit checkbox — "Enable Color Change After
    Tackdown" — which you leave OFF for pre-cut [V]. So the tackdown runs
    straight into the cover with no stop, and the piece costs one intervention
    instead of two.
    """
    steps, report = applique_steps(SHIELD, "S1", solve_geometry(mode=PRE_CUT))

    assert [s.code for s in steps] == ["PLACE", "TACK+COVER"]
    assert report["layers"] == 3
    assert steps[0].function == COLOR_CHANGE
    # One block holds both the tackdown and the cover: no stop between them.
    kinds = [r.kind for r in steps[1].runs]
    assert TACKDOWN in kinds and COVER in kinds


def test_cutting_line_only_exists_for_trim_in_place():
    """§2.6: the cutting line exists *because* the placement run disappears
    under the fabric, and only trim-in-place has anything to cut. Wilcom's
    Pre-cut / Trim-in-place switch is §2.1's "single biggest branch in the
    feature", and emitting a cutting line on a pre-cut piece perforates a
    finished edge for nothing.
    """
    trim, _ = applique_steps(SHIELD, "S1", solve_geometry(mode=TRIM_IN_PLACE))
    pre, _ = applique_steps(SHIELD, "S1", solve_geometry(mode=PRE_CUT))

    assert _layer_offsets(trim, SHIELD, CUTTING)
    assert not _layer_offsets(pre, SHIELD, CUTTING)


def test_the_placement_run_is_never_suppressed():
    """§2.15's "misaligned appliqué" failure mode is the placement line being
    skipped, and the response column reads "never suppress layer 1, even for
    pre-cut". It is the only thing telling the operator where the fabric goes.
    """
    for mode in (TRIM_IN_PLACE, PRE_CUT):
        steps, _ = applique_steps(SHIELD, "S1", solve_geometry(mode=mode))
        assert _layer_offsets(steps, SHIELD, PLACEMENT), mode


@pytest.mark.parametrize("kind, want", [
    (PLACEMENT, 0.0),    # [V] relative to the outline B
    (CUTTING, 0.0),      # [V] coincident with B
    (TACKDOWN, -1.0),    # [V][P] 1 mm inward, chained off the guide run
])
def test_measured_layer_offsets(kind, want):
    """The offsets read back off the emitted stitches, not out of the config
    that produced them. A sign error in the normal direction would put the
    tackdown on the ground fabric instead of the appliqué — §2.7's stated
    mechanism for peeling, since outside stitches compress the background.
    """
    steps, _ = applique_steps(SHIELD, "S1", solve_geometry())
    offsets = _layer_offsets(steps, SHIELD, kind)
    assert offsets
    offsets.sort()
    median = offsets[len(offsets) // 2]
    assert median == pytest.approx(want, abs=0.05), f"{kind} median {median}"


def test_cover_straddles_the_edge_and_buries_the_tackdown():
    """§2.8's whole job: the cover buries the raw edge. Two things must be true
    and both are measured here — the column crosses B (professionals verify
    this at 400-600% zoom [P], §2.15's renderable assertion), and its inner
    rail reaches past the tackdown line so the tack thread does not show.

    Measured on the shield at the trim-in-place default: the SOLVED rails land
    at -1.50 and +1.50 against a tackdown at -1.00, i.e. the cover reaches
    **0.50 mm** inboard of the tackdown — exactly the bury margin §2.3 asks
    for. The STITCHED rails sit `APPLIQUE_COVER_PULL_COMP_MM` (0.20 mm)
    further out on each side — -1.70 / +1.70 — because `_cover_layer` pull-
    compensates the column it actually sews; `g.c_in`/`g.c_out` stay the
    solved, uncompensated values (see `_cover_layer`'s docstring for why).
    """
    g = solve_geometry()
    steps, _ = applique_steps(SHIELD, "S1", g)
    cover = _layer_offsets(steps, SHIELD, COVER)
    assert cover

    # The column spans the solved rails WIDENED by pull comp, with a hair of
    # tolerance for the corner fillet the inner rail needs on the shield's
    # point.
    pull = machine.APPLIQUE_COVER_PULL_COMP_MM
    assert min(cover) == pytest.approx(g.c_in - pull, abs=0.05)
    assert max(cover) == pytest.approx(g.c_out + pull, abs=0.05)

    # It actually CROSSES B rather than running beside it.
    assert min(cover) < 0.0 < max(cover)

    # And it buries the tackdown: the inner rail is inboard of the tack line.
    assert g.c_in < g.s_tack
    assert g.bury_mm >= machine.APPLIQUE_MARGIN_BURY_MM
    assert [d for d in cover if d < g.s_tack], "no cover inboard of the tackdown"


def test_cover_pull_comp_leaves_the_solved_geometry_and_the_tackdown_alone():
    """`APPLIQUE_COVER_PULL_COMP_MM` (0.20 mm, §2.8) is applied only to the
    column `_cover_layer` actually stitches, not to `AppliqueGeometry` itself
    — `g.c_in`/`g.c_out`/`g.width_mm` stay exactly the tolerance-stack's own
    solved numbers (3.00 mm at the default, matching §2.3's validation table),
    because every gate (`edge_headroom_mm`, `bury_mm`, §2.12's checks) and
    every other test in this file measures against those. And it is COVER-
    only, §2.8's own row — pre-cut's zigzag tackdown shares `_rail_column`
    with the cover but must not pick up a width it was never given: measured
    directly, its spread stays `min(APPLIQUE_TACK_WIDTH_MM, W_cover -
    2*m_bury)` with no pull-comp term added.
    """
    g = solve_geometry()
    assert (g.c_in, g.c_out, g.width_mm) == (-1.5, 1.5, 3.0)

    gp = solve_geometry(mode=PRE_CUT)
    steps, _ = applique_steps(BIG_SQUARE, "S1", gp)
    tack = _layer_offsets(steps, BIG_SQUARE, TACKDOWN)
    expected_width = min(machine.APPLIQUE_TACK_WIDTH_MM,
                         gp.width_mm - 2 * machine.APPLIQUE_MARGIN_BURY_MM)
    assert max(tack) - min(tack) == pytest.approx(expected_width, abs=0.05)


def test_cover_closure_overlap_reads_the_appliqué_specific_stitch_count(monkeypatch):
    """`APPLIQUE_CLOSURE_OVERLAP_STITCHES` (6, §2.8's own row) existed and was
    read by no code path — `_cover_layer` inherited `BORDER_CLOSURE_OVERLAP_MM`
    (1.40 mm, the border module's generic distance) through `_satin_loop`'s
    hardcoded default instead. At the 0.40 mm cover spacing the two land close
    (1.40 mm / 0.20 mm-per-station rounds to 7 stitches, one more than the
    appliqué constant) and both sit inside Stahls' published 4-8 stitch
    window, so the substitution was never a visible defect — but it was a
    coincidence resting on `APPLIQUE_COVER_SPACING_MM` staying 0.40 mm, not a
    read of the appliqué tier's own number.

    Proven by moving the constant and watching the emitted cover move with
    it: before this fix, changing `APPLIQUE_CLOSURE_OVERLAP_STITCHES` could
    not change a single stitch, because nothing read it. Now the closing
    circuit continues past its own start for exactly the constant's station
    count, so raising it by N raises the measured cross count by exactly N.
    """
    g = solve_geometry()
    _steps, before = applique_steps(BIG_SQUARE, "S1", g)

    monkeypatch.setattr(machine, "APPLIQUE_CLOSURE_OVERLAP_STITCHES",
                        machine.APPLIQUE_CLOSURE_OVERLAP_STITCHES + 4)
    _steps, after = applique_steps(BIG_SQUARE, "S1", g)

    assert after["crosses"] - before["crosses"] == 4


def test_tackdown_is_a_double_run_for_trim_in_place():
    """§2.7: trim-in-place wants run or double run, because a zigzag tackdown
    gets clipped by the scissors and leaves fabric "whiskers" [P] — §2.15's
    "whiskers at the trim" row. Two passes, so the ring is walked and walked
    back.
    """
    steps, _ = applique_steps(SHIELD, "S1", solve_geometry())
    tack = [r for s in steps for r in s.runs if r.kind == TACKDOWN]
    place = [r for s in steps for r in s.runs if r.kind == PLACEMENT]
    assert tack and place
    # Same ring, twice the path: the double run is ~2x the single placement.
    ratio = sum(len(r.points) for r in tack) / sum(len(r.points) for r in place)
    assert ratio > 1.6, ratio


def test_pre_cut_tackdown_is_a_real_column_not_a_zero_width_run():
    """§2.7: pre-cut's default tackdown is zigzag, and a zigzag/E tackdown is
    a COLUMN with real width, straddling B and centered on the tack line
    ("positioned by column width, centered on the line", §2.2) — not a run
    stitch.

    Before `_zigzag_tack_layer` existed, `applique_steps` called `_run_layer`
    unconditionally for every tackdown type; the only branch was the pass
    count (`2` for `"double_run"`, `1` otherwise). So a zigzag tack — the
    pre-cut DEFAULT — sewed as a zero-width, single-pass running stitch
    exactly on `s_tack`, geometrically identical to `tackdown="run"`.
    `machine.APPLIQUE_TACK_WIDTH_MM` was defined and read by no code path.
    Measured here off the emitted points, not off the config that produced
    them, same convention as `test_measured_layer_offsets`.

    Width is §2.7's hard vendor constraint verbatim: `W_tack <= W_cover -
    2*m_bury`, which at the default 3.0 mm cover clamps to the published
    2.00 mm exactly.
    """
    g = solve_geometry(mode=PRE_CUT)
    steps, _ = applique_steps(BIG_SQUARE, "S1", g)
    offsets = _layer_offsets(steps, BIG_SQUARE, TACKDOWN)
    assert offsets

    expected_width = min(machine.APPLIQUE_TACK_WIDTH_MM,
                         g.width_mm - 2 * machine.APPLIQUE_MARGIN_BURY_MM)
    assert expected_width == pytest.approx(2.0)

    spread = max(offsets) - min(offsets)
    assert spread == pytest.approx(expected_width, abs=0.05), spread
    # Centered on the tackdown line, which is B itself for pre-cut (o_tack=0).
    assert (max(offsets) + min(offsets)) / 2 == pytest.approx(g.s_tack, abs=0.05)


def test_run_and_double_run_tackdowns_stay_a_single_line():
    """Regression guard on the dispatch `_zigzag_tack_layer` was added
    beside: `"run"` and `"double_run"` are explicitly run-stitch-only (§2.2)
    and must keep sewing on the line with zero column width, not gain one.
    """
    g = solve_geometry()  # trim-in-place default -> double_run
    steps, _ = applique_steps(BIG_SQUARE, "S1", g)
    offsets = _layer_offsets(steps, BIG_SQUARE, TACKDOWN)
    assert offsets
    assert max(offsets) - min(offsets) == pytest.approx(0.0, abs=1e-6)


# =========================================================================
# 5. Gates  (§2.12)
# =========================================================================

def test_a_shape_too_narrow_to_show_fabric_says_so():
    """§2.12: below `2*|c_in| + 1.0 mm` the two inner cover rails meet and no
    appliqué fabric shows at all. The spec is emphatic that the engine must SAY
    it, rather than silently emitting an appliqué that reads as plain satin —
    the customer paid for twill they cannot see.

    The floor is 4.0 mm, not §2.12's printed 5.9 mm: 5.9 is `2*1.95 + 1.0`, and
    1.95 is §2.4's inner rail, which `cover_rails` does not implement (see
    `test_the_cover_always_reaches_past_the_raw_edge` for why). Measured by
    ribbon sweep at the shipped rails, the gate fires at 3.5 mm and clears at
    4.0 mm — so both sides of it are pinned here. This is the assertion that
    went stale when the rails moved, and nothing else caught it.
    """
    from digitizer_core.warnings_codes import APPLIQUE_NO_FABRIC_VISIBLE
    g = solve_geometry()
    floor = 2 * abs(g.c_in) + machine.APPLIQUE_MIN_FEATURE_MARGIN_MM
    assert floor == pytest.approx(4.0)

    assert visible_fabric_width(THIN_RIBBON, g.c_in) == 0.0
    _steps, report = applique_steps(THIN_RIBBON, "S1", g)
    assert APPLIQUE_NO_FABRIC_VISIBLE in {x["code"] for x in report["gates"]}

    # The floor itself, from both sides. 3.5 mm leaves 0.50 mm of fabric — some,
    # but under the 1.0 mm margin — and must still be called out.
    assert visible_fabric_width(UNDER_FLOOR, g.c_in) == pytest.approx(0.5, abs=0.05)
    assert APPLIQUE_NO_FABRIC_VISIBLE in {
        x["code"] for x in applique_steps(UNDER_FLOOR, "S1", g)[1]["gates"]}
    assert visible_fabric_width(OVER_FLOOR, g.c_in) == pytest.approx(1.5, abs=0.05)
    assert not [x for x in applique_steps(OVER_FLOOR, "S1", g)[1]["gates"]
                if x["code"] == APPLIQUE_NO_FABRIC_VISIBLE]

    # Real artwork has plenty: 40 mm wide keeps 40 - 2*1.5 = 37 mm showing.
    assert visible_fabric_width(BIG_SQUARE, g.c_in) == pytest.approx(37.0, abs=0.2)
    assert not [x for x in applique_steps(BIG_SQUARE, "S1", g)[1]["gates"]
                if x["code"] == APPLIQUE_NO_FABRIC_VISIBLE]


def test_a_shape_scissors_do_not_fit_into_loses_its_cutting_line():
    """§2.6/§2.12: the cutting line is emitted only where the min inscribed
    diameter clears 12 mm, because below that scissors physically do not fit
    and the operator cannot trim what the line marks. A 9 mm disc clears the
    8 mm pre-cut floor and fails the trim-in-place one.
    """
    from digitizer_core.warnings_codes import APPLIQUE_CUTTING_LINE_SUPPRESSED
    assert min_inscribed_diameter(SMALL_DISC) == pytest.approx(9.0, abs=0.2)

    steps, report = applique_steps(SMALL_DISC, "S1", solve_geometry())
    assert APPLIQUE_CUTTING_LINE_SUPPRESSED in {x["code"] for x in report["gates"]}
    assert not report["cutting_line"]
    assert not _layer_offsets(steps, SMALL_DISC, CUTTING)
    # The step is renamed, because the operator's instruction changed with it.
    assert [s.code for s in steps] == ["PLACE", "TACK", "COVER"]


def test_a_hole_too_small_to_trim_forces_pre_cut():
    """§2.12: `min_hole_diameter >= 15 mm trim-in-place; otherwise force
    pre-cut`. You cannot get scissors into a 10 mm hole in a hooped garment, so
    the piece has to arrive already cut whatever the config asked for.
    """
    from digitizer_core.warnings_codes import APPLIQUE_FORCED_PRE_CUT
    donut = Point(0, 0).buffer(20, quad_segs=48).difference(
        Point(0, 0).buffer(5, quad_segs=48))

    _steps, report = applique_steps(donut, "S1", solve_geometry())
    assert APPLIQUE_FORCED_PRE_CUT in {x["code"] for x in report["gates"]}
    assert report["mode"] == PRE_CUT


def test_a_neck_too_narrow_for_scissors_is_caught_even_with_big_lobes():
    """`min_inscribed_diameter` finds the ONE best spot in a shape — the
    largest circle that fits ANYWHERE. That is the wrong measure for "can
    scissors get all the way around this piece": a two-lobe "dog bone" (two
    20 mm circles joined by a 3 mm neck) has an enormous best spot in either
    lobe, so `min_inscribed_diameter` reports ~19.9 mm and the scissors gate
    never fires — even though nothing wider than 3 mm can pass through the
    neck. `narrowest_passage_diameter` is a strict refinement built for
    exactly this: it finds the erosion radius at which the shape first
    splits, which for a dog bone is the neck itself.
    """
    from shapely.ops import unary_union

    from digitizer_core.stage6_applique import narrowest_passage_diameter
    from digitizer_core.warnings_codes import APPLIQUE_CUTTING_LINE_SUPPRESSED

    lobe_a = Point(-20, 0).buffer(10, quad_segs=64)
    lobe_b = Point(20, 0).buffer(10, quad_segs=64)
    neck = Polygon([(-20, -1.5), (20, -1.5), (20, 1.5), (-20, 1.5)])
    bone = unary_union([lobe_a, lobe_b, neck])

    # The defect, pinned directly: the old measure is blind to the neck.
    assert min_inscribed_diameter(bone) == pytest.approx(19.9, abs=0.2)
    # The fix: the narrowest passage IS the neck, not either lobe.
    assert narrowest_passage_diameter(bone) == pytest.approx(3.0, abs=0.1)

    _steps, report = applique_steps(bone, "S1", solve_geometry())
    codes = {x["code"] for x in report["gates"]}
    assert APPLIQUE_CUTTING_LINE_SUPPRESSED in codes, (
        "a 3 mm neck between two 20 mm lobes must suppress the cutting line "
        "-- scissors cannot navigate a 3 mm passage")
    assert not report["cutting_line"]


def test_an_off_centre_hole_is_measured_by_its_thin_side_not_its_fat_side():
    """Same failure mode as the dog bone, on a ring: `min_inscribed_diameter`
    of a ring whose hole is NOT centred lands on the ring's fat side (the
    single largest inscribed circle), overstating how much clearance the
    ring's own thin side actually has. `narrowest_passage_diameter` finds the
    thin side instead, because that is where the ring first pinches shut
    under erosion.
    """
    from digitizer_core.stage6_applique import narrowest_passage_diameter

    outer = Point(0, 0).buffer(20, quad_segs=48)
    hole = Point(10, 0).buffer(5, quad_segs=48)  # off-centre: thin side ~5 mm
    ring = outer.difference(hole)

    assert min_inscribed_diameter(ring) == pytest.approx(25.0, abs=0.3)
    assert narrowest_passage_diameter(ring) == pytest.approx(5.0, abs=0.1)


def test_narrowest_passage_matches_min_inscribed_diameter_on_ordinary_shapes():
    """The refinement must not move a number that was already right: on a
    shape with no neck (nothing to sever, nothing to pinch), the two measures
    have to agree exactly, or `narrowest_passage_diameter` would be widening
    its own bisection bracket incorrectly rather than converging to the same
    answer by a different route.
    """
    from digitizer_core.stage6_applique import narrowest_passage_diameter

    for shape in (BIG_SQUARE, SMALL_DISC):
        assert narrowest_passage_diameter(shape) == pytest.approx(
            min_inscribed_diameter(shape), abs=0.01)


def test_a_precut_piece_clears_the_scissors_floor_by_default():
    """§2.12's pre-cut scissors/placement floor, `APPLIQUE_MIN_INSCRIBED_
    PRECUT_MM` (8 mm) — lower than trim-in-place's 12 mm because pre-cut has
    no in-hoop trim step to fall back to; the piece just has to be cuttable
    by hand before it is placed. Real artwork and `SMALL_DISC` (9 mm across —
    see its own comment: "clears the 8 mm pre-cut floor, fails the 12 mm
    scissors floor") both clear it, and clearing must not depend on mode:
    the same disc that trips the trim-in-place gate must NOT trip this one.
    """
    from digitizer_core.warnings_codes import APPLIQUE_PRECUT_TOO_NARROW

    g = solve_geometry(mode=PRE_CUT)
    for shape in (BIG_SQUARE, SMALL_DISC):
        _steps, report = applique_steps(shape, "S1", g)
        assert not [x for x in report["gates"]
                    if x["code"] == APPLIQUE_PRECUT_TOO_NARROW], shape


def test_a_narrow_precut_piece_is_warned_not_silent():
    """A pre-cut piece with a bottleneck under 8 mm is physically impractical
    to cut cleanly with scissors before placing it, and §2.12 is explicit
    every gate here "must be enforced" — silently emitting the piece anyway
    is the exact failure mode the other four gates already refuse to allow.

    Same dog-bone construction as `test_a_neck_too_narrow_for_scissors_is_
    caught_even_with_big_lobes`, widened to a 6 mm neck (under the 8 mm
    pre-cut floor, clear of the 12 mm trim-in-place one) so this pins the
    pre-cut gate specifically rather than reusing the trim-in-place fixture.
    `narrowest_passage_diameter`, not `min_inscribed_diameter`, has to be
    what feeds it: the two 20 mm lobes give `min_inscribed_diameter` ~19.9 mm
    and the naive measure would never fire.
    """
    from shapely.ops import unary_union

    from digitizer_core.stage6_applique import narrowest_passage_diameter
    from digitizer_core.warnings_codes import APPLIQUE_PRECUT_TOO_NARROW

    lobe_a = Point(-20, 0).buffer(10, quad_segs=64)
    lobe_b = Point(20, 0).buffer(10, quad_segs=64)
    neck = Polygon([(-20, -3.0), (20, -3.0), (20, 3.0), (-20, 3.0)])
    bone = unary_union([lobe_a, lobe_b, neck])

    assert min_inscribed_diameter(bone) == pytest.approx(19.9, abs=0.2)
    assert narrowest_passage_diameter(bone) == pytest.approx(6.0, abs=0.1)

    _steps, report = applique_steps(bone, "S1", solve_geometry(mode=PRE_CUT))
    hits = [x for x in report["gates"] if x["code"] == APPLIQUE_PRECUT_TOO_NARROW]
    assert hits, "a 6 mm neck on a pre-cut piece must warn -- scissors cannot cut it cleanly"
    assert hits[0]["measured_mm"] == pytest.approx(6.0, abs=0.1)
    assert hits[0]["floor_mm"] == machine.APPLIQUE_MIN_INSCRIBED_PRECUT_MM


def test_precut_and_trim_in_place_scissors_floors_never_both_fire():
    """The two floors are scoped to their own mode and must stay mutually
    exclusive, not merely both-correct-in-isolation: the same 6 mm-neck piece
    fails pre-cut's 8 mm floor and trim-in-place's 12 mm floor at once, so a
    caller that gated on `geom.mode` incorrectly (or not at all) would fire
    both codes on one piece and the operator would get a contradictory
    instruction (a cutting line AND a "cannot be pre-cut" warning).
    """
    from shapely.ops import unary_union

    from digitizer_core.warnings_codes import (APPLIQUE_CUTTING_LINE_SUPPRESSED,
                                                APPLIQUE_PRECUT_TOO_NARROW)

    lobe_a = Point(-20, 0).buffer(10, quad_segs=64)
    lobe_b = Point(20, 0).buffer(10, quad_segs=64)
    neck = Polygon([(-20, -3.0), (20, -3.0), (20, 3.0), (-20, 3.0)])
    bone = unary_union([lobe_a, lobe_b, neck])

    _steps, pre_report = applique_steps(bone, "S1", solve_geometry(mode=PRE_CUT))
    pre_codes = {x["code"] for x in pre_report["gates"]}
    assert APPLIQUE_PRECUT_TOO_NARROW in pre_codes
    assert APPLIQUE_CUTTING_LINE_SUPPRESSED not in pre_codes

    _steps, trim_report = applique_steps(bone, "S1", solve_geometry())
    trim_codes = {x["code"] for x in trim_report["gates"]}
    assert APPLIQUE_CUTTING_LINE_SUPPRESSED in trim_codes
    assert APPLIQUE_PRECUT_TOO_NARROW not in trim_codes


# =========================================================================
# 6. The resequencer guard  (§0.3, §6.5)
# =========================================================================

class _FakeRegion:
    def __init__(self, meta, thread_index=0):
        self.meta = meta
        self.thread_index = thread_index


class _FakePlanned:
    def __init__(self, sew_index, step_key=None, thread_index=0):
        self.sew_index = sew_index
        self.region = _FakeRegion({} if step_key is None else {"step_key": step_key},
                                  thread_index)


def test_resequencer_cannot_merge_two_steps_into_one_block():
    """§0.3: "Merging two objects to save a stop destroys an operator
    instruction." Stage 7 groups shapes and sews a whole group as ONE block, so
    two regions that land in the same group can never be separated by a color
    change — and on a single head a color change is the only stop there is.

    Two regions on the same thread but in different steps must therefore key
    differently, or the file stops carrying "lay the twill here" and the
    operator sews the cover onto bare garment.
    """
    a = _FakePlanned(0, "piece1/placement")
    b = _FakePlanned(0, "piece1/cover")
    assert nn_group_key(a) != nn_group_key(b)
    assert len({nn_group_key(a), nn_group_key(b)}) == 2


def test_regions_without_steps_group_exactly_as_before():
    """The guard is a strict refinement: with no step keys (and one thread per
    layer, which is every unedited design) every region keys on
    `(sew_index, "", thread)`, so the group set and its sort order are what
    `sorted({p.sew_index})` always produced. Anything else silently reorders
    every design in the shop.
    """
    planned = [_FakePlanned(i) for i in (2, 0, 1, 0, 2)]
    assert sorted({nn_group_key(p) for p in planned}) == \
        [(0, "", 0), (1, "", 0), (2, "", 0)]


def test_a_layer_override_shares_the_sew_position_but_never_the_block():
    """The shape-layers contract's `layer` override can put two THREADS in one
    layer. A block is sewn in one thread and stage 7 takes the block's thread
    from its first region, so a mixed layer must split into per-thread groups
    — deterministically, thread order breaking the tie."""
    red = _FakePlanned(2, thread_index=148)
    green = _FakePlanned(2, thread_index=364)
    assert nn_group_key(red) != nn_group_key(green)
    assert sorted([nn_group_key(red), nn_group_key(green)]) == \
        [nn_group_key(red), nn_group_key(green)]


# =========================================================================
# 7. The steps[] read interface
# =========================================================================

def test_plan_steps_is_uniform_across_tiers():
    """The worksheet renders ONE list whether or not a specialty tier produced
    the design. §6.1's complaint is that a thread list "actively misleads": on
    an all-one-colour appliqué it implies nothing is happening at all. So an
    ordinary block still yields a step — its action is just "change thread".
    """
    plan = StitchPlan(palette=[], blocks=[
        StitchBlock(0, "1801", RED, [StitchRun(points=_sq(-10, 0), kind="run")]),
        StitchBlock(1, "0015", (250, 250, 250),
                    [StitchRun(points=_sq(10, 0), kind="run")]),
    ])
    steps = plan_steps(plan)
    assert [s["index"] for s in steps] == [1, 2]
    assert all(s["action"].strip() for s in steps)
    assert steps[0]["code"] == "COLOR"
    assert "1801" in steps[0]["action"]
    # Every step reports what it costs, so the operator knows how long it runs.
    assert steps[0]["stitches"] == plan.blocks[0].stitch_count


def test_the_last_step_ends_rather_than_stopping():
    """The machine halts on the last block because the file is over, not
    because anyone has to do anything. Printing a change the operator would
    stand and wait for is exactly the wrong-thing-at-the-right-time §6.5 warns
    about.
    """
    plan = StitchPlan(palette=[], blocks=[
        StitchBlock(0, "1801", RED, [StitchRun(points=_sq(-10, 0), kind="run")]),
        StitchBlock(0, "1801", RED, [StitchRun(points=_sq(10, 0), kind="run")]),
    ])
    steps = plan_steps(plan)
    assert steps[0]["function"] == COLOR_CHANGE
    assert steps[-1]["function"] == END
    assert steps[-1]["action"] == "Design complete"


def test_step_metadata_reaches_the_block_the_worksheet_reads():
    """§6.5: "The step boundary in the IR and the color-change record in the
    DST must be the same object." The worksheet reads blocks; if the action
    string lives anywhere else the sheet and the file can disagree.
    """
    steps, _ = applique_steps(SHIELD, "S1", solve_geometry())
    meta = steps[0].as_meta(1, "1801")
    for key in ("index", "code", "label", "action", "function", "flags",
                "material", "piece", "layers", "stitches", "thread"):
        assert key in meta, key
    assert meta["action"]
    assert meta["function"] == COLOR_CHANGE
    # The stop is a frame-out on the same needle — §6.2's `flags`, which warn
    # that the machine will stop with no colour to change.
    assert "SAME NEEDLE" in meta["flags"]


# =========================================================================
# 8. End to end through stage 7
# =========================================================================

def _applique_plan(**kw):
    from digitizer_core import plan_stitches
    c = cfg(garment_id="hat_front", applique=True, **kw)
    result = digitize(TESTDATA / "logo_whitebg.png", c)[0]
    return plan_stitches(result, c), c


def test_applique_pieces_sew_as_consecutive_same_thread_blocks():
    """The end-to-end shape of the feature: every piece becomes several blocks
    on ONE thread, and the boundaries between them are the operator's stops.
    That is the arrangement §0 says four other techniques are waiting on.
    """
    plan, _c = _applique_plan()
    steps = [b.step for b in plan.blocks if b.step]
    assert steps, "appliqué produced no steps"

    # At least one piece's steps are consecutive blocks on one thread number.
    codes = [s["code"] for s in steps]
    assert "PLACE" in codes
    assert any(c in codes for c in ("CUT+TACK", "TACK", "TACK+COVER"))

    # Every appliqué step carries a real instruction.
    for s in steps:
        assert s["action"].strip(), s

    # Thread-run contiguity over the whole plan — the assertion
    # hardening-closeout-2026-08-02 §6 found missing ("No test asserts
    # thread-run contiguity, so this is invisible to the 234"): every thread
    # sews as ONE contiguous stretch of blocks. A fall-through implementation
    # that hands a no-fabric piece back to the normal color loop fails this —
    # the piece's thread is sewn among the appliqué blocks, abandoned, then
    # picked up again at the end (5 contiguous same-thread runs become 6).
    threads = [b.thread_number for b in plan.blocks]
    thread_runs = [k for k, _g in itertools.groupby(threads)]
    assert len(thread_runs) == len(set(threads)), thread_runs

    # And the stops survive into the file.
    from digitizer_core.stage6_applique import plan_steps as read_steps
    assert len(read_steps(plan)) == len(plan.blocks)


def test_a_forced_cover_width_override_warns_end_to_end():
    """The gate-level clamp warning (`test_a_clamped_cover_width_is_warned_
    not_silent`) reaches a real plan through `applique_pass`'s own warning
    aggregation, the same path every other appliqué gate warning takes.
    `applique_cover_width_mm` is config.py's documented "escape hatch for a
    sew-out comparison, still clamped to [2.5, 5.0]" — the practically
    reachable way to hit §2.12's snag-risk ceiling on the benchmark logo.
    """
    from digitizer_core.warnings_codes import APPLIQUE_COVER_WIDTH_CLAMPED

    plan, _c = _applique_plan(applique_cover_width_mm=8.0)
    hits = [w for w in plan.warnings if w["code"] == APPLIQUE_COVER_WIDTH_CLAMPED]
    assert hits, "no clamp warning on a width override 3.2 mm past the ceiling"
    assert hits[0]["bounds"] == ["ceiling"]
    assert hits[0]["count"] > 0

    # A normal, unforced design never hits either bound.
    plan_normal, _c = _applique_plan()
    assert not [w for w in plan_normal.warnings
               if w["code"] == APPLIQUE_COVER_WIDTH_CLAMPED]


def test_pre_cut_costs_one_fewer_stop_per_piece():
    """§2.9's table: pre-cut is 3 layers and **1** machine stop per piece,
    trim-in-place is 4 layers and **2**. On a single head that is the whole
    economics of the mode switch.

    Counted per piece, not as `3 * pieces` across the design — which is what
    this test used to assert, and it is not the law. Two gates legitimately
    change a piece's shape, and the benchmark logo trips both: one region has
    a 14.02 mm hole (under the 15 mm scissors floor) so §2.12 forces it
    pre-cut, and two are too narrow for the cover to leave any fabric showing
    (a 1.0 mm² dot and a 48 mm² thin letterform), so §2.12's fall-through
    degrades each to ONE block of plain stitching — identical in both modes,
    no stops, no fabric. Neither is a lost stop — both are warned, and the
    assertions below are that they are warned.
    """
    from digitizer_core.warnings_codes import (APPLIQUE_FORCED_PRE_CUT,
                                               APPLIQUE_NO_FABRIC_VISIBLE,
                                               APPLIQUE_STEP_EMPTY)
    trim, _ = _applique_plan(applique_mode="trim_in_place")
    pre, _ = _applique_plan(applique_mode="pre_cut")

    def by_piece(plan):
        out: dict[str, list[str]] = {}
        for b in plan.blocks:
            if b.step:
                out.setdefault(b.step["piece"], []).append(b.step["code"])
        return out

    trim_pieces, pre_pieces = by_piece(trim), by_piece(pre)
    assert trim_pieces and set(trim_pieces) == set(pre_pieces)
    trim_codes = {w["code"] for w in trim.warnings}

    # Pre-cut is flat: PLACE, then everything else. One stop, one instruction.
    # A piece the no-fabric gate degraded is flatter still: one block of
    # plain stitching, and it must be warned, never silent.
    fell = {}
    for piece, codes in pre_pieces.items():
        if codes in (["SATIN"], ["RUN"]):
            fell[piece] = codes
            continue
        assert codes == ["PLACE", "TACK+COVER"], (piece, codes)
    if fell:
        assert APPLIQUE_NO_FABRIC_VISIBLE in {w["code"] for w in pre.warnings}
    assert fell, "the benchmark's two no-fabric pieces should fall through"

    full = {}
    for piece, codes in trim_pieces.items():
        if codes in (["SATIN"], ["RUN"]):
            # §2.12's fall-through is mode-independent: no fabric can show
            # either way, so the piece sews identically in both modes.
            assert codes == pre_pieces[piece], (piece, codes)
            assert APPLIQUE_NO_FABRIC_VISIBLE in trim_codes
            continue
        assert codes[0] == "PLACE", (piece, codes)
        if codes == ["PLACE", "TACK+COVER"]:
            # §2.12 decided for us: no scissors fit, so the piece is pre-cut.
            assert APPLIQUE_FORCED_PRE_CUT in trim_codes
        elif len(codes) == 2:
            # A step produced nothing. It must be reported, never silent.
            assert APPLIQUE_STEP_EMPTY in trim_codes, (piece, codes)
        else:
            assert codes[1] in ("CUT+TACK", "TACK") and codes[2] == "COVER"
            assert len(codes) == 3, (piece, codes)
            full[piece] = codes
    assert full, "no piece actually sewed as trim-in-place"

    trim_steps = [b.step for b in trim.blocks if b.step]
    pre_steps = [b.step for b in pre.blocks if b.step]
    assert len(pre_steps) == 2 * (len(pre_pieces) - len(fell)) + len(fell)
    assert len(pre_steps) < len(trim_steps)
    # The economics, exactly: one extra stop per piece that really trims.
    assert len(trim_steps) - len(pre_steps) == len(full)


def test_a_precut_design_warns_when_a_piece_is_too_narrow_to_hand_cut():
    """The gate-level warning (`test_a_narrow_precut_piece_is_warned_not_
    silent`) reaches a real plan through `applique_pass`'s own warning
    aggregation, the same path every other appliqué gate warning takes — same
    shape as `test_a_forced_cover_width_override_warns_end_to_end` for
    `APPLIQUE_COVER_WIDTH_CLAMPED`.

    No synthetic fixture needed: the benchmark logo already has a piece under
    the 8 mm pre-cut floor (`test_pre_cut_costs_one_fewer_stop_per_piece`'s
    own 1.0 mm² / 1.07 mm-inscribed region), so `applique_mode="pre_cut"` on
    real artwork fires this without construction.
    """
    from digitizer_core.warnings_codes import APPLIQUE_PRECUT_TOO_NARROW

    pre, _c = _applique_plan(applique_mode="pre_cut")
    hits = [w for w in pre.warnings if w["code"] == APPLIQUE_PRECUT_TOO_NARROW]
    assert hits, "no warning for a pre-cut piece under the 8 mm scissors floor"
    assert hits[0]["count"] > 0

    # Mode-scoped end to end too: trim-in-place on the same artwork never
    # fires the pre-cut-only code, even though it has its own gates tripping.
    trim, _c = _applique_plan(applique_mode="trim_in_place")
    assert not [w for w in trim.warnings if w["code"] == APPLIQUE_PRECUT_TOO_NARROW]


@pytest.mark.parametrize("mode", [TRIM_IN_PLACE, PRE_CUT])
def test_applique_blocks_survive_export_with_their_stops(mode):
    """The invariant end to end: N appliqué blocks must produce N-1 color
    changes in the DST, or the operator loses an instruction between the plan
    and the machine.

    The load-bearing half is the boundaries where BOTH sides are the same
    thread — the ones a writer that merges adjacent same-colour blocks deletes
    without a word, which §0.2 calls the number-one reported appliqué failure.
    Measured on the benchmark logo: trim-in-place emits 13 blocks and 12 stops,
    **8 of which are same-thread**; pre-cut emits 10 blocks, 9 stops, 5 of
    them same-thread. All of them are in the file. (16/15/11 and 12/11/7
    before §2.12's no-fabric fall-through landed: the two pieces that cannot
    show fabric now sew as one plain-stitching block each instead of 2-3
    appliqué blocks.)

    Read from the bytes, not from the plan: the file is split at its 0x0000C3
    records and the segments are counted and measured against the plan.
    """
    plan, _c = _applique_plan(applique_mode=mode)
    data = export.export_dst(plan)

    assert _raw_records(data).count("CC") == len(plan.blocks) - 1

    # One segment per block. Fewer means two steps were welded together.
    segments = _dst_segments(data)
    assert len(segments) == len(plan.blocks)
    assert all(seg for seg in segments), "a segment sews nothing"
    assert sum(s.count("STITCH") for s in segments) == plan.stats.stitch_count

    # The stops that a same-colour merge would have swallowed. A piece the
    # no-fabric gate degraded to plain stitching is ONE block with no internal
    # stop, so the floor is the pieces that sew as two or more blocks.
    same_thread = [i for i in range(1, len(plan.blocks))
                   if plan.blocks[i].thread_number == plan.blocks[i - 1].thread_number]
    pieces = [b.step["piece"] for b in plan.blocks if b.step]
    multi_block = {pid for pid in pieces if pieces.count(pid) >= 2}
    assert multi_block, "every piece fell through -- nothing pins the stops"
    assert len(same_thread) >= len(multi_block)

    # And an independent reader agrees with the raw byte walk.
    pattern = pystitch.read_dst(io.BytesIO(data))
    assert sum(1 for s in pattern.stitches
               if s[2] == pystitch.COLOR_CHANGE) == len(plan.blocks) - 1


def test_a_jump_does_not_eat_the_penetration_it_lands_on():
    """A jump moves the needle WITHOUT penetrating, so the stitch that follows
    it is the first penetration of the new path, not a repeat of the last one.

    `plan_to_pattern` used to carry `last` across the jump and delete that
    stitch whenever the new block entered within 0.01 mm of where the previous
    one ended — which for appliqué is not a rare coincidence but the normal
    case, because a layer change at the same offset re-enters the ring at the
    point nearest the needle, i.e. exactly where it already is. Measured on the
    benchmark logo: 1 penetration lost in trim-in-place and 5 in pre-cut, every
    one of them run 0 point 0, and every one the FIRST of the five penetrations
    in `stitches.tie_run`'s 0.8 mm lock (at, in, at, in, at) — the anchor that
    holds a thread the trim just cut, landing 4 of 5.

    Both directions are pinned here, because the dedup is right when the needle
    never left: without the jump flag the coincident point IS the same needle
    position and skipping it is correct. "Never left" is scoped WITHIN one
    block: a block boundary is a machine stop (`stitches.iter_machine_
    commands`' own rule — sewing restarts fresh after it, whatever flags the
    next run carries), so the needle-never-left control lives inside a single
    block, and the two-block case keeps every penetration on BOTH sides of
    the stop.

    The counts are taken from the decoded file and from `plan.stats` — since
    the exporter and `stats` consume the same `iter_machine_commands` stream,
    the file/worksheet agreement is by construction, and asserting both here
    guards the stream itself.
    """
    square = _sq(0, 0)

    lifted = StitchPlan(palette=[], blocks=[
        StitchBlock(0, "1801", RED, [StitchRun(points=list(square), kind="run")]),
        StitchBlock(0, "1801", RED, [StitchRun(points=list(square), kind="run",
                                               jump=True, trim=True)]),
    ])
    stayed = StitchPlan(palette=[], blocks=[
        StitchBlock(0, "1801", RED, [StitchRun(points=list(square), kind="run"),
                                     StitchRun(points=list(square), kind="run")]),
    ])
    # The two plans hold the identical points; only the needle-up flag and
    # the stop between the paths differ.
    assert (lifted.blocks[1].runs[0].points == stayed.blocks[0].runs[1].points
            == list(square))

    assert [s.count("STITCH") for s in _dst_segments(export.export_dst(lifted))] \
        == [5, 5]
    # One block, needle never lifted: the coincident re-entry point IS the
    # same needle position, and exactly one stitch is deduped.
    assert [s.count("STITCH") for s in _dst_segments(export.export_dst(stayed))] \
        == [9]

    # And the plan's own count agrees with the file in both cases, or the
    # worksheet and the machine tell the operator different numbers.
    assert lifted.stats.stitch_count == 10
    assert stayed.stats.stitch_count == 9


# =========================================================================
# 9. Cover style (§2.8) — satin vs zigzag vs e_stitch
# =========================================================================
#
# `applique_steps(..., cover=...)` threaded `cover` all the way down to
# `_cover_layer`'s call site and no further — `_cover_layer` itself never
# took a `cover` argument, so every appliqué cover sewed byte-identical
# satin rail geometry regardless of the config value. `cover` only ever
# reached a worksheet label string. Confirmed here the same way the rest of
# this file confirms an offset: measured off the emitted stitch points, not
# read back out of the config that generated them.

def test_cover_satin_is_untouched_by_the_cover_parameter():
    """The load-bearing regression: `cover="satin"` (and the unspecified
    default, which is the same string) must keep sewing exactly what it sewed
    before `_cover_layer` learned about `cover` at all. Pinned against the
    shield fixture other tests in this file already measure the cover layer
    on (`test_cover_straddles_the_edge_and_buries_the_tackdown`).

    Two kinds of proof: point-for-point equality between the implicit default
    and an explicit `cover="satin"` call (so the two code paths that reach
    `_cover_layer` cannot silently diverge), and a pinned count/checksum of
    the actual emitted column, so a change to `_rail_column`'s satin branch
    that happened to keep the point COUNT the same could not slip past this
    test unnoticed.
    """
    g = solve_geometry()
    steps_default, _ = applique_steps(SHIELD, "S1", g)
    steps_satin, _ = applique_steps(SHIELD, "S1", g, cover="satin")

    cover_default = [p for s in steps_default for r in s.runs
                     if r.kind == COVER for p in r.points]
    cover_satin = [p for s in steps_satin for r in s.runs
                   if r.kind == COVER for p in r.points]
    assert cover_default == cover_satin
    assert len(cover_default) == 783

    # A checksum over every emitted point, not just the count — two different
    # 783-point columns could tie on length alone.
    sum_x = sum(p[0] for p in cover_default)
    sum_y = sum(p[1] for p in cover_default)
    assert sum_x == pytest.approx(-121.651153, abs=1e-3)
    assert sum_y == pytest.approx(-2271.726091, abs=1e-3)

    # The satin spacing constant, unchanged — `APPLIQUE_COVER_SPACING_MM`,
    # not the new zigzag one.
    label = [s.label for s in steps_default if s.code == "COVER"][0]
    assert f"{machine.APPLIQUE_COVER_SPACING_MM:.2f} mm spacing" in label
    assert "satin cover" in label


def test_cover_zigzag_produces_genuinely_different_geometry():
    """`cover="zigzag"` must sew a real, differently-spaced column — not the
    satin rail geometry with a different label. `_rail_column` (the same
    column emitter `_zigzag_tack_layer` already reuses for the pre-cut
    tackdown at ITS own spacing) is driven by `APPLIQUE_ZIGZAG_COVER_SPACING_MM`
    (3.0 mm) instead of `geom.spacing_mm` (0.40 mm) — roughly 7.5x fewer
    crosses for the same boundary.

    Measured on the shield: satin sews 783 crosses at 0.40 mm, zigzag sews
    109 at 3.00 mm. What must NOT change is where the rails themselves sit —
    only the pitch — so the min/max cover offsets against B are checked to
    stay the same pull-compensated rails (`geom.c_in - pull`, `geom.c_out +
    pull`) either way.
    """
    g = solve_geometry()
    steps_satin, report_satin = applique_steps(SHIELD, "S1", g, cover="satin")
    steps_zigzag, report_zigzag = applique_steps(SHIELD, "S1", g, cover="zigzag")

    assert report_satin["crosses"] == 783
    assert report_zigzag["crosses"] == 109
    assert report_zigzag["crosses"] < report_satin["crosses"] / 5

    cover_satin = _layer_offsets(steps_satin, SHIELD, COVER)
    cover_zigzag = _layer_offsets(steps_zigzag, SHIELD, COVER)
    pull = machine.APPLIQUE_COVER_PULL_COMP_MM
    for offsets in (cover_satin, cover_zigzag):
        assert min(offsets) == pytest.approx(g.c_in - pull, abs=0.05)
        assert max(offsets) == pytest.approx(g.c_out + pull, abs=0.05)

    label = [s.label for s in steps_zigzag if s.code == "COVER"][0]
    assert f"{machine.APPLIQUE_ZIGZAG_COVER_SPACING_MM:.2f} mm spacing" in label
    assert "zigzag cover" in label


def test_cover_zigzag_reads_its_own_spacing_constant(monkeypatch):
    """`APPLIQUE_ZIGZAG_COVER_SPACING_MM` must be an actual read, not a second
    unread constant like `APPLIQUE_TACK_WIDTH_MM` was before `_zigzag_tack_
    layer` existed. Proven the same way `test_cover_closure_overlap_reads_
    the_appliqué_specific_stitch_count` proves `APPLIQUE_CLOSURE_OVERLAP_
    STITCHES` is read: move the constant and watch the emitted column move
    with it. `cover="satin"` is re-checked in the same breath to confirm the
    move does not leak into the unrelated branch.
    """
    g = solve_geometry()
    _steps, satin_before = applique_steps(SHIELD, "S1", g, cover="satin")
    _steps, zigzag_before = applique_steps(SHIELD, "S1", g, cover="zigzag")

    monkeypatch.setattr(machine, "APPLIQUE_ZIGZAG_COVER_SPACING_MM", 6.0)

    _steps, satin_after = applique_steps(SHIELD, "S1", g, cover="satin")
    _steps, zigzag_after = applique_steps(SHIELD, "S1", g, cover="zigzag")

    assert satin_after["crosses"] == satin_before["crosses"]
    assert zigzag_after["crosses"] < zigzag_before["crosses"]


def test_e_stitch_cover_falls_through_to_satin_geometry():
    """`e_stitch` has no cover algorithm anywhere in this codebase and no
    spec to implement it against (§2.8 describes a comb stitch ORDER, not
    just a spacing) — it is explicitly out of scope here and must keep
    falling through to plain satin rail geometry, not raise and not silently
    grow a spacing branch of its own. Documented as a real, deliberate
    non-implementation rather than an untested gap.
    """
    g = solve_geometry()
    steps_satin, report_satin = applique_steps(SHIELD, "S1", g, cover="satin")
    steps_e, report_e = applique_steps(SHIELD, "S1", g, cover="e_stitch")

    cover_satin = [p for s in steps_satin for r in s.runs
                  if r.kind == COVER for p in r.points]
    cover_e = [p for s in steps_e for r in s.runs
              if r.kind == COVER for p in r.points]
    assert cover_e == cover_satin
    assert report_e["crosses"] == report_satin["crosses"] == 783


def test_applique_cover_config_reaches_the_cover_layer_end_to_end():
    """The config value (`cfg.applique_cover`) has to actually reach
    `_cover_layer` through `applique_pass` -> `applique_steps`, not just be
    accepted and ignored — the exact defect this section exists to close.
    Run through the real stage-7 entry point, not `applique_steps` directly,
    so the whole wire is exercised end to end.
    """
    plan_satin, _ = _applique_plan(applique_cover="satin")
    plan_zigzag, _ = _applique_plan(applique_cover="zigzag")

    cover_steps_satin = [b.step for b in plan_satin.blocks
                         if b.step and COVER in b.step.get("layers", [])]
    cover_steps_zigzag = [b.step for b in plan_zigzag.blocks
                          if b.step and COVER in b.step.get("layers", [])]
    assert cover_steps_satin and cover_steps_zigzag

    satin_stitches = sum(s["stitches"] for s in cover_steps_satin)
    zigzag_stitches = sum(s["stitches"] for s in cover_steps_zigzag)
    # Same real-world claim as the shield-level test above, just reached
    # through config instead of a direct `applique_steps` call: a 3.0 mm
    # zigzag pitch crosses far fewer times than a 0.40 mm satin pitch over
    # the same boundaries.
    assert zigzag_stitches < satin_stitches / 3


# =========================================================================
# 10. §2.12's no-fabric fall-through — and the two integrity properties a
#     prior implementation of it measurably broke
#     (docs/hardening-closeout-2026-08-02.md §6 and §7)
# =========================================================================
#
# `check_gates`' docstring has always promised that a piece failing the
# min-feature-width gate "falls through to plain satin", quoting §2.12 —
# and until this section's fixes, nothing performed it: the piece sewed a
# placement run, a tackdown and a cover over fabric the cover then buried
# completely, three operator actions spent on nothing visible. The
# fall-through now happens in `applique_pass`, per piece and IN PLACE,
# because the one previous implementation of it (a different lineage,
# audited in the hardening-closeout dossier) got both integrity properties
# wrong: handing the piece back to the normal color loop fragmented thread
# contiguity (§6: "thread 1305 is sewn, abandoned for 2905, then picked up
# again — 5 contiguous thread runs become 6"), and filtering it out of
# `picked` before the overlap count silenced APPLIQUE_PIECES_OVERLAP on
# exactly the fallen-over-live case (§7: "Before: 1. After: 0.").

class _Region2:
    def __init__(self, poly, thread_index, meta):
        self.polygon = poly
        self.thread_index = thread_index
        self.meta = meta


class _Planned2:
    """The minimal `PlannedRegion` surface `applique_pass` reads."""

    def __init__(self, poly, thread_index, sew_index, shape_id, layer=0):
        self.region = _Region2(poly, thread_index, {"layer": layer})
        self.polygon = poly
        self.sew_index = sew_index
        self.shape_id = shape_id


def _run_applique_pass(planned, **cfg_kw):
    from digitizer_core.stage6_applique import applique_pass
    from digitizer_core.threads import chart_for
    c = cfg(applique=True, **cfg_kw)
    return applique_pass(planned, c, chart_for(c))


# A 2.5 mm ribbon away from every other fixture used in this section: under
# the 4.0 mm no-fabric floor, overlapping nothing.
APART_RIBBON = Polygon([(-20, 30), (20, 30), (20, 32.5), (-20, 32.5)])


def test_a_no_fabric_piece_falls_through_to_plain_satin():
    """DEFECT 3 (the promise itself): a piece whose two inner cover rails
    meet sews as ordinary flat stitching — §2.12: "falls through to plain
    satin, and the engine must say so rather than silently emitting an
    appliqué with no visible fabric". Before the fix this piece sewed the
    full appliqué program (placement + tackdown + cover) around fabric that
    could never show, and the machine stopped twice to ask the operator to
    lay and trim it.
    """
    from digitizer_core.warnings_codes import APPLIQUE_NO_FABRIC_VISIBLE

    blocks, warnings, remaining, _cursor = _run_applique_pass(
        [_Planned2(THIN_RIBBON, 20, 0, "RB")])

    # In the appliqué block sequence, not handed back to the normal loop.
    assert remaining == []
    assert len(blocks) == 1
    step = blocks[0].step
    assert step["code"] == "SATIN"

    # Plain stitching, no appliqué layer of any kind.
    kinds = {r.kind for r in blocks[0].runs}
    assert not kinds & {PLACEMENT, CUTTING, TACKDOWN, COVER}, kinds
    assert "satin" in kinds

    # No stop asks the operator to lay fabric that can never show.
    assert "lay" not in step["action"].lower()

    # The stitching is a real plain satin on the ribbon itself, not the
    # appliqué cover in disguise: the cover's pull-compensated outer rail
    # reaches 1.7 mm OUTSIDE B, a plain satin never leaves the artwork by
    # more than a hair.
    slack = THIN_RIBBON.buffer(0.5)
    assert all(slack.covers(Point(p)) for b in blocks
               for r in b.runs for p in r.points)

    # And the engine says so, in the honest tense.
    hits = [w for w in warnings if w["code"] == APPLIQUE_NO_FABRIC_VISIBLE]
    assert hits and hits[0]["count"] == 1
    assert hits[0]["as_satin"] == 1 and hits[0]["as_run"] == 0
    assert "fell through" in hits[0]["message"]


def test_a_fallen_piece_keeps_its_threads_blocks_contiguous():
    """DEFECT 1 (dossier §6): the fall-through must not fragment thread
    order. The fallen piece's block sews at the piece's own slot in the
    appliqué sequence — right beside its thread's other pieces — so the
    contiguous same-thread run count through the plan equals the distinct
    thread count. The known-bad implementation handed the piece back to the
    normal color loop, which sews after EVERY appliqué block: its thread was
    sewn, abandoned for the next thread, then picked up again at the end.
    """
    live_a = _Planned2(BIG_SQUARE, 10, 0, "A1", layer=0)
    fallen_a = _Planned2(APART_RIBBON, 10, 0, "A2", layer=0)
    live_b = _Planned2(Polygon([(60, 60), (100, 60), (100, 100), (60, 100)]),
                       20, 1, "B1", layer=1)
    # Input order deliberately interleaved; the pass sorts by layer/sew/id.
    blocks, _warnings, remaining, _cursor = _run_applique_pass(
        [live_a, live_b, fallen_a])

    assert remaining == []

    # One contiguous stretch per thread, fallen piece included.
    seq = [b.thread_index for b in blocks]
    assert [k for k, _g in itertools.groupby(seq)] == [10, 20], seq

    # The fallen piece degraded to ONE plain-stitching block, and it sits
    # immediately after its own thread's live piece, not appended after B.
    a2 = [i for i, b in enumerate(blocks) if b.step["piece"] == "A2"]
    a1 = [i for i, b in enumerate(blocks) if b.step["piece"] == "A1"]
    assert len(a2) == 1 and blocks[a2[0]].step["code"] == "SATIN"
    assert a2[0] == max(a1) + 1


def test_overlap_warning_survives_a_fall_through_over_a_live_piece():
    """DEFECT 2 (dossier §7): `APPLIQUE_PIECES_OVERLAP` must keep firing
    when one of the two overlapping pieces falls through — the one case
    where the warning matters MOST, because the fallen piece's plain satin
    sews straight across the live piece's cover. The known-bad
    implementation filtered fallen pieces out of `picked` before the
    overlap count and went silent on exactly this case while the
    two-live-pieces control still warned.
    """
    from digitizer_core.warnings_codes import APPLIQUE_PIECES_OVERLAP

    live = _Planned2(BIG_SQUARE, 10, 0, "SQ", layer=0)
    fallen = _Planned2(THIN_RIBBON, 20, 1, "RB", layer=1)  # crosses the square
    blocks, warnings, _remaining, _cursor = _run_applique_pass([live, fallen])

    # The ribbon really fell through (this is what makes the case THE case).
    rb = [b for b in blocks if b.step["piece"] == "RB"]
    assert len(rb) == 1 and rb[0].step["code"] == "SATIN"

    hits = [w for w in warnings if w["code"] == APPLIQUE_PIECES_OVERLAP]
    assert hits and hits[0]["count"] == 1, warnings

    # Control: the same two pieces moved apart warn about nothing.
    _b, w2, _r, _c = _run_applique_pass(
        [_Planned2(BIG_SQUARE, 10, 0, "SQ", layer=0),
         _Planned2(APART_RIBBON, 20, 1, "RB", layer=1)])
    assert not [w for w in w2 if w["code"] == APPLIQUE_PIECES_OVERLAP]
