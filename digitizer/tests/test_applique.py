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
import math

import pyembroidery
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

    Deliberately NOT pyembroidery's reader. Reading back with the library that
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
    layers are frequently all one thread. If the writer or pyembroidery's
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
    pattern = pyembroidery.read_dst(io.BytesIO(data))
    assert sum(1 for s in pattern.stitches
               if s[2] == pyembroidery.COLOR_CHANGE) == 1


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

    old = [(i, "") for i in sorted({p.sew_index for p in planned})]
    assert sorted({nn_group_key(p) for p in planned}) == old


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

    Measured on the shield at the trim-in-place default: rails land at -1.50
    and +1.50 against a tackdown at -1.00, i.e. the cover reaches **0.50 mm**
    inboard of the tackdown — exactly the bury margin §2.3 asks for.
    """
    g = solve_geometry()
    steps, _ = applique_steps(SHIELD, "S1", g)
    cover = _layer_offsets(steps, SHIELD, COVER)
    assert cover

    # The column spans the solved rails, with a hair of tolerance for the
    # corner fillet the inner rail needs on the shield's point.
    assert min(cover) == pytest.approx(g.c_in, abs=0.05)
    assert max(cover) == pytest.approx(g.c_out, abs=0.05)

    # It actually CROSSES B rather than running beside it.
    assert min(cover) < 0.0 < max(cover)

    # And it buries the tackdown: the inner rail is inboard of the tack line.
    assert g.c_in < g.s_tack
    assert g.bury_mm >= machine.APPLIQUE_MARGIN_BURY_MM
    assert [d for d in cover if d < g.s_tack], "no cover inboard of the tackdown"


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


# =========================================================================
# 6. The resequencer guard  (§0.3, §6.5)
# =========================================================================

class _FakeRegion:
    def __init__(self, meta):
        self.meta = meta


class _FakePlanned:
    def __init__(self, sew_index, step_key=None):
        self.sew_index = sew_index
        self.region = _FakeRegion({} if step_key is None else {"step_key": step_key})


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
    """The guard is a strict refinement: with no step keys every region keys on
    `(sew_index, "")`, so the group set and its sort order are what
    `sorted({p.sew_index})` always produced. Anything else silently reorders
    every design in the shop.
    """
    planned = [_FakePlanned(i) for i in (2, 0, 1, 0, 2)]
    assert sorted({nn_group_key(p) for p in planned}) == [(0, ""), (1, ""), (2, "")]


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

    # And the stops survive into the file.
    from digitizer_core.stage6_applique import plan_steps as read_steps
    assert len(read_steps(plan)) == len(plan.blocks)


def test_pre_cut_costs_one_fewer_stop_per_piece():
    """§2.9's table: pre-cut is 3 layers and **1** machine stop per piece,
    trim-in-place is 4 layers and **2**. On a single head that is the whole
    economics of the mode switch.

    Counted per piece, not as `3 * pieces` across the design — which is what
    this test used to assert, and it is not the law. Two gates legitimately
    shorten a trim-in-place piece to two blocks, and the benchmark logo trips
    both: one region has a 14.02 mm hole (under the 15 mm scissors floor) so
    §2.12 forces it pre-cut, and one is 1.0 mm² with a 1.07 mm inscribed
    diameter, so its tackdown ring at -1.00 mm is annihilated by its own offset
    and the step is refused. Neither is a lost stop — both are warned, and the
    assertions below are that they are warned.
    """
    from digitizer_core.warnings_codes import (APPLIQUE_FORCED_PRE_CUT,
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
    for piece, codes in pre_pieces.items():
        assert codes == ["PLACE", "TACK+COVER"], (piece, codes)

    full = {}
    for piece, codes in trim_pieces.items():
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
    assert len(pre_steps) == 2 * len(pre_pieces)
    assert len(pre_steps) < len(trim_steps)
    # The economics, exactly: one extra stop per piece that really trims.
    assert len(trim_steps) - len(pre_steps) == len(full)


@pytest.mark.parametrize("mode", [TRIM_IN_PLACE, PRE_CUT])
def test_applique_blocks_survive_export_with_their_stops(mode):
    """The invariant end to end: N appliqué blocks must produce N-1 color
    changes in the DST, or the operator loses an instruction between the plan
    and the machine.

    The load-bearing half is the boundaries where BOTH sides are the same
    thread — the ones a writer that merges adjacent same-colour blocks deletes
    without a word, which §0.2 calls the number-one reported appliqué failure.
    Measured on the benchmark logo: trim-in-place emits 16 blocks and 15 stops,
    **11 of which are same-thread**; pre-cut emits 12 blocks, 11 stops, 7 of
    them same-thread. All of them are in the file.

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

    # The stops that a same-colour merge would have swallowed.
    same_thread = [i for i in range(1, len(plan.blocks))
                   if plan.blocks[i].thread_number == plan.blocks[i - 1].thread_number]
    assert len(same_thread) >= len({b.step["piece"] for b in plan.blocks if b.step})

    # And an independent reader agrees with the raw byte walk.
    pattern = pyembroidery.read_dst(io.BytesIO(data))
    assert sum(1 for s in pattern.stitches
               if s[2] == pyembroidery.COLOR_CHANGE) == len(plan.blocks) - 1
