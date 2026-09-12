"""The catalogue: one set of readers, pointed at two files.

Spec §5. Tier is read by the same scale-free rule on both sides
(`satin_columns` share, then `union_pitch` rows); `study_pro.classify` is
never pointed at ours (its 0.7 mm floor).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE.parent / "tools" / "pro_parity"))

import proloop_synth as synth                        # noqa: E402
import pairframe                                     # noqa: E402
import overlay                                       # noqa: E402
import diff as pdiff                                 # noqa: E402
from test_pro_overlay import becker_pair             # noqa: E402,F401  (session fixture)


def _two_regions(ours_tier_b="satin", pro_tier_b="fill", width_b=2.0):
    """Region A: satin on both sides. Region B: satin ours, `pro_tier_b` pro.

    R1 (controller ruling): the fill arm uses `fill_passes(0, 8, 20, 4.0,
    row=0.4, stitch=2.5)` rather than the brief's `fill_passes(0, 9, 20,
    2.0)`, which yields ~48 segments -- under `row_pitch_union.union_pitch`'s
    50-segment floor, so `tier_of` would misread the fill arm as "run"
    instead of "fill". This arm measures 88 segments (11 rows), well clear
    of the floor. Region B's box is widened to (-0.5, 7.5, 20.5, 12.5) to
    contain both the widened fill arm (y in [8, 12]) and the unchanged
    satin arm (`satin_pass(0, 10, 20, ...)`, y in [9, 11]).
    """
    a_ours = synth.satin_pass(0, 0, 20, 2.0)
    a_pro = synth.satin_pass(0, 0, 20, 2.0)
    b_ours = ([synth.satin_pass(0, 10, 20, 2.0)] if ours_tier_b == "satin"
              else synth.fill_passes(0, 8, 20, 4.0, row=0.4, stitch=2.5))
    b_pro = ([synth.satin_pass(0, 10, 20, width_b)] if pro_tier_b == "satin"
             else synth.fill_passes(0, 8, 20, 4.0, row=0.4, stitch=2.5))
    ours = [((0, 0, 0), [a_ours, *b_ours])]
    pro = [((0, 0, 0), [a_pro, *b_pro])]
    regions = [("A", "satin", box(-0.5, -1.5, 20.5, 1.5)), ("B", "satin", box(-0.5, 7.5, 20.5, 12.5))]
    return pro, ours, regions


def test_tier_disagreement_shows_on_one_row(tmp_path):
    pro, ours, regions = _two_regions(pro_tier_b="fill")
    d = synth.make_prep_dir(tmp_path, "tier", pro, ours, regions, [(0, -1, 20, 1), (0, 8, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    rows, residual = pdiff.region_rows(pair, reg)
    by = {r["shape_id"]: r for r in rows}
    assert by["A"]["ours"]["tier"] == "satin" and by["A"]["pro"]["tier"] == "satin"
    assert by["B"]["ours"]["tier"] == "satin" and by["B"]["pro"]["tier"] == "fill"
    assert by["B"]["tier_planned"] == "satin"
    assert residual["pro_passes"] == 0 and residual["ours_passes"] == 0


def test_width_difference_is_a_width_row_not_a_tier_row(tmp_path):
    pro, ours, regions = _two_regions(pro_tier_b="satin", width_b=2.6)
    d = synth.make_prep_dir(tmp_path, "width", pro, ours, regions, [(0, -1, 20, 1), (0, 8, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    rows, _ = pdiff.region_rows(pair, reg)
    b = next(r for r in rows if r["shape_id"] == "B")
    assert b["ours"]["tier"] == b["pro"]["tier"] == "satin"
    assert abs(b["ours"]["width_p50"] - 2.0) < 0.15 and abs(b["pro"]["width_p50"] - 2.6) < 0.15


def test_readers_agree_between_plan_and_file(becker_pair):
    """`passes_from_file` on ours.dst measures what `passes_from_plan` would:
    the DST round trip does not move a column width (spec §7 test 6)."""
    from satin_columns import measure, passes_from_file
    from digitizer_core import PipelineConfig, digitize
    import prep_all
    cfg = prep_all.parity_config(becker_pair.width_mm, "left_chest")
    _res, plan = digitize(becker_pair.art, cfg)
    from satin_columns import passes_from_plan
    a = measure(passes_from_plan(plan))
    b = measure(passes_from_file(becker_pair.ours_path))
    assert abs(a["median_mm"] - b["median_mm"]) < 0.05
    assert abs(a["share"] - b["share"]) < 0.02


def test_a_pass_that_crosses_two_regions_is_split_between_them(tmp_path):
    """A professional file travels with the needle down, so one pass can cross
    several of our regions. Each region must get the thread that lies in it."""
    from shapely.geometry import box
    long_satin = synth.satin_pass(0, 0, 40, 2.0)          # spans both boxes below
    blocks = [((0, 0, 0), [long_satin])]
    regions = [("L", "satin", box(-0.5, -1.5, 18.0, 1.5)),
               ("R", "satin", box(22.0, -1.5, 40.5, 1.5))]
    d = synth.make_prep_dir(tmp_path, "cross", blocks, blocks, regions, [(0, -1, 40, 1)], 40.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    rows, residual = pdiff.region_rows(pair, reg)
    by = {r["shape_id"]: r for r in rows}
    assert by["L"]["pro"]["tier"] == "satin" and by["R"]["pro"]["tier"] == "satin"
    assert by["L"]["pro"]["stitches"] > 20 and by["R"]["pro"]["stitches"] > 20
    assert by["L"]["pro"]["trims"] == 1 and by["R"]["pro"]["trims"] == 1   # one lift, two regions


def test_every_assigned_chunk_lies_in_its_own_region(becker_pair):
    """Chunked assignment credits a region only with thread that is really in
    it. Whole-pass assignment credited a region with a pass's whole length
    once 60% of its points fell inside, which on this pro file meant 54% of
    33.3 m "assigned" with much of it lying elsewhere.

    R16: assignment labels a SEGMENT by its midpoint, not its endpoints, so a
    chunk's own endpoint can sit a little outside the buffer (the next
    segment past it belongs to a different label). Check the MIDPOINTS —
    what `assign_passes` actually tested — not every endpoint."""
    import shapely
    reg = pairframe.register_pair(becker_pair.pro_path, becker_pair.ours_path)
    polys = dict(pdiff.region_polys(becker_pair, reg))
    passes = pdiff.passes_of(becker_pair.pro_path)
    per, _residual, _lifts = pdiff.assign_passes(passes, list(polys.items()))
    for sid, chunks in per.items():
        buffered = polys[sid].buffer(pdiff.ASSIGN_BUFFER_MM + 1e-6)
        for pts in chunks:
            mx = [(pts[i][0] + pts[i + 1][0]) / 2.0 for i in range(len(pts) - 1)]
            my = [(pts[i][1] + pts[i + 1][1]) / 2.0 for i in range(len(pts) - 1)]
            assert shapely.contains_xy(buffered, mx, my).all(), sid


def test_assignment_accounts_for_every_millimetre(becker_pair):
    """Nothing may vanish between a region and the residual. Labelling points
    instead of segments lost the thread that crosses a region boundary: 18.6 m
    of the pro's 33.3 m and 12.1 m of our 33.6 m went uncounted."""
    reg = pairframe.register_pair(becker_pair.pro_path, becker_pair.ours_path)
    polys = pdiff.region_polys(becker_pair, reg)
    for path, transform in ((becker_pair.pro_path, None),
                            (becker_pair.ours_path, reg.apply_xy)):
        passes = pdiff.passes_of(path, transform)
        per, residual, _lifts = pdiff.assign_passes(passes, polys)
        assigned = sum(pdiff.length_mm(v) for v in per.values())
        assert abs(assigned + pdiff.length_mm(residual) - pdiff.length_mm(passes)) < 1.0


def test_the_planned_tier_reaches_the_regions_file(becker_pair):
    tiers = {r.get("tier") for r in becker_pair.regions}
    assert tiers - {None}, becker_pair.regions[:2]


def test_fragments_do_not_dilute_the_tier_ratio():
    """A chunk under 3 points has no crossing information, so it may not vote
    on the satin share. On the Becker pro file 1,136 of 2,541 chunks are that
    short, and they pulled the largest region from 0.520 to 0.444."""
    column = synth.satin_pass(0, 0, 20, 2.0)
    fragments = [[(float(i), 0.0), (float(i) + 0.4, 0.0)] for i in range(60)]
    assert pdiff.tier_of([column] + fragments) == "satin"
    assert pdiff.tier_of([column]) == "satin"


def test_the_pros_largest_region_reads_satin(becker_pair):
    """The pro sews BECKER's outline as a satin keyline. Read with every
    fragment voting, it read fill."""
    reg = pairframe.register_pair(becker_pair.pro_path, becker_pair.ours_path)
    rows, _residual = pdiff.region_rows(becker_pair, reg)
    biggest = max(rows, key=lambda r: r["area_mm2"])
    assert biggest["pro"]["tier"] == "satin", biggest["pro"]


def test_shape_tags_split_by_ink(tmp_path):
    """A pro-only bar over ink -> dropped; a pro-only bar over bare art ->
    redesign (`sewn_by` "pro"); an ours-only bar over bare art -> background;
    an ours-only bar over ink -> redesign too (`sewn_by` "ours", R18) --
    the untested branch (fix round 1, finding 3).

    `anchor_hi`/`anchor_lo`, identical in both files at distant y, are NOT
    part of the brief's fixture -- added because the brief's bare pro/ours
    geometry (measured) sends `pairframe.register_pair` to `dy=-4.0,
    iou=0.0`: pro's own extra bars and ours' extra bar(s) pull the two
    files' bbox centroids apart (originally 4mm with one ours-only bar; 8mm
    once the fix-round-1 ours-only-over-ink bar below is added, since that
    bar pulls ours' MIN down while the original single high anchor only
    ever equalised the MAX), `register_pair`'s crude
    centroid-then-local-hillclimb search only explores a small neighbourhood
    of that centroid guess (`scorecard.register`, step 1.0mm down to 0.25mm,
    no restart), and the true zero-shift optimum is far enough outside that
    neighbourhood (probed: IOU is a flat 0 within a few mm of a bad seed)
    that the search never finds it -- so the shared `common` pass itself
    never lands where it should and every tag comes out on the wrong side.
    Two anchors, present verbatim in both files on the high and low side,
    each pin one extreme of both bounding boxes to the SAME value regardless
    of whatever asymmetric content sits between them, which is what lets the
    real `register_pair` converge on the true `dy=0.0` here (measured:
    `iou=0.43`) without touching pairframe.py's own, separately-tested,
    registration search."""
    common = synth.satin_pass(0, 0, 20, 2.0)
    anchor_hi = synth.satin_pass(0, 60, 5, 2.0)            # registration ballast -- see docstring
    anchor_lo = synth.satin_pass(0, -40, 5, 2.0)           # registration ballast -- see docstring
    pro = [((0, 0, 0), [common,
                        synth.satin_pass(0, 8, 10, 2.0),      # over ink: we dropped it
                        synth.satin_pass(0, 16, 10, 2.0),     # no ink: the pro added it
                        anchor_hi, anchor_lo])]
    ours = [((0, 0, 0), [common,
                         synth.satin_pass(0, 24, 10, 2.0),    # no ink: we sewed ground
                         synth.satin_pass(0, -16, 10, 2.0),   # over ink: the pro left it unsewn
                         anchor_hi, anchor_lo])]
    regions = [("A", "satin", box(-0.5, -1.5, 20.5, 1.5))]
    ink = [(0, -1, 20, 1), (0, 7, 10, 9), (0, -17, 10, -15)]
    d = synth.make_prep_dir(tmp_path, "tags", pro, ours, regions, ink, 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg)
    rows = pdiff.shape_rows(pair, reg, r)
    tags = sorted((x["tag"], round(x["centre_mm"][1]), x["sewn_by"]) for x in rows if not x.get("dust"))
    assert tags == [("background", 24, "ours"), ("dropped", 8, "pro"),
                    ("redesign", -16, "ours"), ("redesign", 16, "pro")]
    for x in rows:
        if not x.get("dust"):
            assert 15 < x["area_mm2"] < 30 and x["nearest_region"] == "A" and x["crop"].startswith("--crop ")
    dust_tags = [x["tag"] for x in rows if x.get("dust")]
    assert len(dust_tags) == len(set(dust_tags)), rows          # one dust row per tag (finding 1)
    for x in rows:
        if x.get("dust"):
            assert x["sewn_by"] in ("pro", "ours", "mixed")


def test_shape_rows_finds_a_real_redesign_on_becker(becker_pair):
    """Real-data check (no synthetic geometry): the pro fills BECKER's
    letter bodies solid where we sew them as a hollow satin outline, so
    `shape_rows` must surface at least one substantial `redesign` row --
    not just dust -- on the actual Becker pair. R2's branch 2 (no
    `art_meta.json` sidecar on a real prep dir) is what maps the art here;
    see the report for the measured ink-bbox-vs-regions-bbox residual and
    the full tag totals."""
    reg = pairframe.register_pair(becker_pair.pro_path, becker_pair.ours_path)
    r = overlay.render_pair(becker_pair, reg)
    rows = pdiff.shape_rows(becker_pair, reg, r)
    totals: dict = {}
    for x in rows:
        t = totals.setdefault(x["tag"], {"count": 0, "area_mm2": 0.0})
        t["count"] += x.get("count", 1)
        t["area_mm2"] += x["area_mm2"]
    print("Becker shape_rows tag totals:", totals)
    redesign = [x for x in rows if x["tag"] == "redesign" and not x.get("dust")]
    assert redesign, rows
    biggest = max(redesign, key=lambda x: x["area_mm2"])
    print("Becker largest redesign row:", biggest)
    assert biggest["area_mm2"] > 20.0, biggest
    # R18 / fix round 1, finding 2: `redesign` covers both directions on real
    # data -- the pro adding thread (sewn_by "pro") and the pro leaving art
    # unsewn or merged (sewn_by "ours") -- and a row must say which.
    assert {x["sewn_by"] for x in redesign} == {"pro", "ours"}
    # fix round 1, finding 1: one dust row per tag, never two for the same tag.
    dust_tags = [x["tag"] for x in rows if x.get("dust")]
    assert len(dust_tags) == len(set(dust_tags)), rows


def test_flag_row_rules():
    row = {"shape_id": "X", "pro": {"tier": "satin", "width_p50": 2.6, "direction_deg": 20.0, "direction_R": 0.9,
                                    "pitch_mm": None, "layers_p50": 1.1},
           "ours": {"tier": "satin", "width_p50": 2.0, "direction_deg": 22.0, "direction_R": 0.9,
                    "pitch_mm": None, "layers_p50": 1.0}}
    assert pdiff.flag_row(row) == ["width"]
    row["ours"]["tier"] = "fill"
    row["ours"]["direction_deg"] = 80.0
    assert pdiff.flag_row(row) == ["tier", "width", "direction"]
    row["pro"]["tier"] = "none"
    assert "tier" not in pdiff.flag_row(row)


def test_catalogue_and_json_written(tmp_path):
    pro, ours, regions = _two_regions(pro_tier_b="fill")
    d = synth.make_prep_dir(tmp_path, "cat", pro, ours, regions, [(0, -1, 20, 1), (0, 9, 20, 11)], 20.0)
    assert pdiff.main(["--dir", str(d)]) == 0
    md = (d / "catalogue.md").read_text(encoding="utf-8")
    js = json.loads((d / "diff.json").read_text())
    assert "## Flagged" in md and "| B |" in md and "Kent's call" in md
    # Measured, not assumed (digitizer/.venv, this exact fixture): B's pro
    # side is a tatami fill (rows run at 180 deg, pitch 0.4mm) and its ours
    # side a satin column (crosses at 90 deg, pitch 0.78mm) on the SAME
    # polygon -- a real tier disagreement, so the whole-file registration
    # (driven by A's identical geometry plus B's mismatched footprint) lands
    # at iou 0.4886, and B's OTHER craft readers (direction, pitch) disagree
    # too, for the same underlying reason tier does. Pinned to what actually
    # runs rather than the higher/narrower numbers a quick guess would pick.
    assert js["registration"]["iou"] == pytest.approx(0.4886, abs=0.005)
    assert [r["shape_id"] for r in js["flagged"]] == ["B"]
    assert js["flagged"][0]["flags"] == ["tier", "direction", "pitch"]

    # R12 (controller ruling): the Design table carries both sides' own
    # extent_mm (width, height, aspect) -- an aspect mismatch is a finding
    # the per-region craft rows can't show on their own.
    assert "width mm" in md and "height mm" in md and "aspect" in md
    assert js["design"]["ours"]["extent_mm"][0] > 0.0
    assert js["design"]["pro"]["extent_mm"][0] > 0.0

    # R19 (controller ruling): a shape tag with more than 15 big rows is
    # capped at the 15 largest in catalogue.md, with a trailing summary line
    # for the rest -- but diff.json still keeps every row. This tiny fixture
    # has nowhere near 15 real shape components, so exercise write_catalogue
    # directly with a hand-built `shapes` list, reusing the pair/rows/design
    # main() already computed above.
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    rows, residual = pdiff.region_rows(pair, reg)
    design = pdiff.design_rows(pair, reg)
    many = [{"tag": "redesign", "sewn_by": "pro", "area_mm2": float(20 - i),
             "centre_mm": [0.0, float(i)], "nearest_region": "A", "crop": "--crop 0 0 1 1"}
            for i in range(20)]
    out2 = d / "many"
    out2.mkdir(parents=True, exist_ok=True)
    md2, js2 = pdiff.write_catalogue(pair, reg, rows, residual, design, many, out2)
    text2 = md2.read_text(encoding="utf-8")
    assert "and 5 more" in text2 and "mm² total" in text2
    assert len(json.loads(js2.read_text())["shapes"]) == 20


def test_smoke_becker_diff(becker_pair):
    reg = pairframe.register_pair(becker_pair.pro_path, becker_pair.ours_path)
    rows, residual = pdiff.region_rows(becker_pair, reg)
    assert len(rows) == len(becker_pair.regions) > 5
    r = overlay.render_pair(becker_pair, reg)
    shapes = pdiff.shape_rows(becker_pair, reg, r)
    md, js = pdiff.write_catalogue(becker_pair, reg, rows, residual,
                                   pdiff.design_rows(becker_pair, reg), shapes, becker_pair.dir)
    assert md.exists() and js.exists()
    tags = {s["tag"] for s in shapes}
    assert "redesign" in tags        # BECKER's filled bodies (spec §8)
