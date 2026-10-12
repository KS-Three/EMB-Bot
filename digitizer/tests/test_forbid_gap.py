"""`cfg.forbid_gap_mm` — Law 26's forbid-gap half (defect 47).

Two fills of different threads with a strip of bare fabric between them
narrower than the threshold: the planner must not leave it. With the flag
the colour sewn FIRST closes it — it extends across the strip and tucks the
ordinary `pull + overlap_mm` tongue under the later colour, whose edge stays
on its artwork (the colour on top owns the seam, Kent's 2026-09-09 ruling).
A gap at or over the threshold, a gap a third colour fills, and a gap
between two shapes of one thread are left exactly as they were. OFF (None)
is the engine before it: nothing is built.

What OFF leaves is not always a gap on paper: the underlap reaches only
into the later colour's artwork, never across bare fabric, so across a
strip narrower than two pulls the two pull bands meet and overlap in the
middle with neither colour spanning it. On the CLOTH, where pull takes both
bands back, that is the strip again. The instrument
(`seam_underlap.narrow_gaps`) reads it on the cloth, which is why every
reading here hands it the fabric's pull.

The value is ROADMAP gate 1's: 0.8 mm is the documented candidate (two
stitch rows), not a measured constant — card block 6 owns it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig, run_stages
from digitizer_core.fabrics import get_fabric
from digitizer_core.pipeline import fabric_for
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import gap_bridges, resolve_overlaps

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from seam_underlap import cloth_take_back, measure, narrow_gaps  # noqa: E402

FABRIC = get_fabric("pique_knit")
ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = 0.8


def _region(sid, poly, layer, thread, tier="fill"):
    return Region(shape_id=sid, polygon=poly, thread_index=layer,
                  thread_number=thread, area_mm2=float(poly.area),
                  meta={"layer": layer, "tier": tier, "fill_angle_deg": 0.0})


def _pair(gap, first="A"):
    """A on the left, B on the right, `gap` mm of bare fabric between them.
    `first` names the shape that sews first (layer 0)."""
    la, lb = (0, 1) if first == "A" else (1, 0)
    a = _region("A", box(-20, 0, 0, 20), la, "1000")
    b = _region("B", box(gap, 0, 20 + gap, 20), lb, "2000")
    return [a, b]


def _plan(regions, gap_mm=None, **kw):
    planned, _ = resolve_overlaps(regions, FABRIC, PipelineConfig(forbid_gap_mm=gap_mm, **kw))
    return {p.shape_id: p for p in planned}


def _gaps(regions, plan):
    planned = list(plan.values())
    return narrow_gaps(regions, planned, CANDIDATE,
                       take_back=cloth_take_back(planned, PipelineConfig(), FABRIC))


def _mid(planned):
    """The sewn polygon along the middle of the seam, clear of the corners
    where compensation rounds round the ends."""
    return planned.polygon.intersection(box(-30, 2, 30, 18))


def _wkb(regions, gap_mm=None):
    return {k: p.polygon.wkb for k, p in _plan(regions, gap_mm).items()}


def test_default_is_off():
    assert PipelineConfig().forbid_gap_mm is None


def test_off_leaves_a_gap_on_the_cloth_and_the_instrument_sees_it():
    regs = _pair(0.6)
    plan = _plan(regs)
    pull = FABRIC.pull_comp_mm
    # The underlap reaches only into the later colour's ARTWORK, never
    # across bare fabric: A stops at its own pull band.
    assert _mid(plan["A"]).bounds[2] == pytest.approx(pull, abs=0.02)
    gaps = _gaps(regs, plan)
    assert len(gaps) == 1 and gaps[0]["gap_mm"] == pytest.approx(0.6, abs=1e-6)
    assert gaps[0]["earlier"] == "A"


def test_off_a_04_strip_is_covered_on_paper_and_open_on_the_cloth():
    regs = _pair(0.4)
    plan = _plan(regs)
    # The two pull bands overlap in the middle of the strip on paper (the
    # tongue A's reach found in B's artwork is cut off from A and dropped)...
    assert plan["A"].polygon.intersection(plan["B"].polygon).area > 0.0
    assert _mid(plan["A"]).bounds[2] == pytest.approx(FABRIC.pull_comp_mm, abs=0.02)
    # ...so the plan as drawn reads covered, and the cloth, where pull takes
    # both bands back, reads the strip open: neither colour spans it.
    assert narrow_gaps(regs, list(plan.values()), CANDIDATE) == []
    assert len(_gaps(regs, plan)) == 1


def test_on_closes_a_04_gap_to_an_ordinary_seam():
    regs = _pair(0.4)
    plan = _plan(regs, CANDIDATE)
    pull = FABRIC.pull_comp_mm
    # The earlier colour spans the gap and reaches under the later one by
    # the same `pull + overlap_mm` an abutting seam gets.
    assert _mid(plan["A"]).bounds[2] == pytest.approx(0.4 + pull + 0.25, abs=0.02)
    # The later colour's seam edge stays on its artwork: it does not grow
    # back over the strip the earlier colour now owns.
    assert _mid(plan["B"]).bounds[0] == pytest.approx(0.4, abs=1e-6)
    assert _gaps(regs, plan) == []
    # Read through the seam instrument, it is the seam two abutting fills get.
    pairs = measure(regs, list(plan.values()))["pairs"]
    abut = measure(_pair(0.0), list(_plan(_pair(0.0)).values()))["pairs"]
    assert len(pairs) == 1 and pairs[0]["earlier"] == "A"
    assert pairs[0]["depth_mm"] == pytest.approx(abut[0]["depth_mm"], abs=0.01)


def test_the_colour_sewn_first_is_the_one_that_extends():
    regs = _pair(0.4, first="B")
    plan = _plan(regs, CANDIDATE)
    pull = FABRIC.pull_comp_mm
    assert _mid(plan["B"]).bounds[0] == pytest.approx(-(pull + 0.25), abs=0.02)
    assert _mid(plan["A"]).bounds[2] == pytest.approx(0.0, abs=1e-6)
    assert _gaps(regs, plan) == []


def test_a_12_gap_is_untouched():
    regs = _pair(1.2)
    assert _wkb(regs, CANDIDATE) == _wkb(regs)
    assert gap_bridges(regs, CANDIDATE)[1] == []


def test_a_gap_just_over_the_threshold_is_untouched():
    regs = _pair(0.85)
    assert _wkb(regs, CANDIDATE) == _wkb(regs)


def test_a_gap_just_under_the_threshold_closes():
    regs = _pair(0.75)
    assert len(_gaps(regs, _plan(regs))) == 1
    plan = _plan(regs, CANDIDATE)
    assert plan["A"].polygon.intersection(plan["B"].polygon).area > 0.0
    assert _gaps(regs, plan) == []


def test_a_gap_another_colour_fills_is_not_bridged():
    # C, a third thread, fills the strip between A and B: there is no bare
    # fabric there, so nothing is built.
    regs = _pair(0.4) + [_region("C", box(0.0, 0, 0.4, 20), 2, "3000")]
    assert gap_bridges(regs, CANDIDATE)[1] == []


def test_same_thread_neighbours_are_held_apart_not_bridged():
    a = _region("A", box(-20, 0, 0, 20), 0, "1000")
    b = _region("B", box(0.4, 0, 20.4, 20), 0, "1000")
    regs = [a, b]
    assert gap_bridges(regs, CANDIDATE)[1] == []
    assert _wkb(regs, CANDIDATE) == _wkb(regs)


def test_an_unstitched_shape_never_takes_part():
    regs = _pair(0.4)
    regs[1].meta["stitched"] = False
    assert gap_bridges(regs, CANDIDATE)[1] == []


def test_a_ring_gap_round_an_inset_shape_closes():
    # A later colour sitting in the earlier colour's hole with 0.6 mm of
    # bare fabric all round it: the ring is a gap like any other.
    ground = box(-10, -10, 10, 10).difference(box(-3.6, -3.6, 3.6, 3.6))
    a = _region("A", ground, 0, "1000")
    b = _region("B", box(-3, -3, 3, 3), 1, "2000")
    regs = [a, b]
    assert len(_gaps(regs, _plan(regs))) == 1
    on = _plan(regs, CANDIDATE)
    assert _gaps(regs, on) == []
    assert on["A"].polygon.intersection(on["B"].polygon).area > 0.0


# The real fixtures: ON, `seam_underlap.narrow_gaps` reads no gap under the
# candidate anywhere. Drone must read some OFF, or it proves nothing; Fremont
# reads none either way (measured 2026-10-11: `gap_bridges` finds no strip
# there, so ON plans it byte for byte as OFF) -- it stays as the "touches
# nothing it should not" side.
@pytest.mark.parametrize("rel,width,garment,gaps_off", [
    ("photo/logo_hotel_fremont.webp", 92.5, "patch", False),
    ("photo/drone_render.png", 80.0, "left_chest", True),
])
def test_fixture_reads_no_gap_under_the_candidate(rel, width, garment, gaps_off):
    base = PipelineConfig(target_width_mm=width, garment_id=garment)
    result = run_stages(ROOT / "testdata" / rel, base)
    regions = [r for r in result.regions if r.meta.get("stitched", True)]
    fabric = fabric_for(base)
    on_cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                            forbid_gap_mm=CANDIDATE)
    wkb = []
    for cfg, want_any in ((base, gaps_off), (on_cfg, False)):
        planned, _ = resolve_overlaps(regions, fabric, cfg, result.design_class)
        gaps = narrow_gaps(regions, planned, CANDIDATE,
                           take_back=cloth_take_back(planned, cfg, fabric))
        assert bool(gaps) is want_any, gaps[:5]
        wkb.append([p.polygon.wkb for p in planned])
    if not gaps_off:
        assert wkb[0] == wkb[1]
