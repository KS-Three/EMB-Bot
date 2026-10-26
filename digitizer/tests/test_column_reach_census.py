"""`tools/column_reach_census.py`: why a labelled letter never reaches the
Column lane.

Synthetic glyphs are block capitals built from bars, as in `test_words.py`,
so the text tagger (`textcluster.detect_text_clusters`) admits and links them
the way it does real letters. The census's numbers on the real pairs live in
the PR that built it; these pin the parts a number rests on: the reason
classifier, its parity with the tagger it replays, and the label carry's
exactness at the corpus width.
"""
from __future__ import annotations

import copy

from shapely.affinity import scale as shp_scale
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core import threads
from digitizer_core.regions import Region
from digitizer_core.textcluster import detect_text_clusters
from tools import column_reach_census as crc

H, W, S = 4.0, 3.0, 0.6        # cap height, glyph width, stroke (mm)


def _glyph(ch: str, x: float, y: float, k: float = 1.0) -> Polygon:
    """Block capital `ch`, its box's top-left at (x, y), y down, scaled `k`."""
    h, w, s = H * k, W * k, S * k
    bars = {
        "H": [(0, 0, s, h), (w - s, 0, w, h), (0, h / 2 - s / 2, w, h / 2 + s / 2)],
        "E": [(0, 0, s, h), (0, 0, w, s), (0, h / 2 - s / 2, w * 0.8, h / 2 + s / 2), (0, h - s, w, h)],
        "L": [(0, 0, s, h), (0, h - s, w, h)],
        "T": [(0, 0, w, s), (w / 2 - s / 2, 0, w / 2 + s / 2, h)],
        "U": [(0, 0, s, h), (w - s, 0, w, h), (0, h - s, w, h)],
    }[ch]
    return unary_union([box(x + a, y + b, x + c, y + d) for a, b, c, d in bars])


def _region(sid: str, poly: Polygon, ink: int = 0) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=ink, thread_number="1",
                  area_mm2=poly.area, meta={})


def _far_ink(chart) -> int:
    """A thread index whose CIEDE2000 from thread 0 is far past the tagger's
    one-ink tolerance (20)."""
    best = max(range(1, len(chart)), key=lambda i: chart.delta_e(0, i))
    assert chart.delta_e(0, best) > 40
    return best


def _scene(chart):
    """Four lines, each with ONE planted miss, and the labels naming them:
      L1  H E L T U + a too-WIDE glyph (two letters joined: aspect)
      L2  H E L T + an E drawn 0.7x the line's height (height ratio)
      L3  H E L T + a U in a far ink (other thread)
      L4  H E, alone (cluster of one: two letters cannot make a word)"""
    far = _far_ink(chart)
    regs, lines = [], {}

    def line(name, y, word, extra=()):
        ids = []
        for i, ch in enumerate(word):
            sid = f"{name}{i}"
            regs.append(_region(sid, _glyph(ch, i * 3.8, y)))
            ids.append(sid)
        for sid, poly, ink in extra:
            regs.append(_region(sid, poly, ink))
            ids.append(sid)
        lines[name] = ids
    wide = unary_union([_glyph("H", 5 * 3.8, 0), _glyph("E", 5 * 3.8 + W, 0)])
    line("L1", 0.0, "HELTU", [("L1wide", wide, 0)])
    line("L2", 20.0, "HELT", [("L2small", _glyph("E", 4 * 3.8, 20.0 + 0.6, k=0.7), 0)])
    line("L3", 40.0, "HELT", [("L3ink", _glyph("U", 4 * 3.8, 40.0), far)])
    line("L4", 70.0, "HE")
    return regs, lines


def _reasons(regs, lines, chart):
    rp = crc.replay_text_door(regs, chart)
    out = {}
    for name, ids in lines.items():
        for sid in ids:
            out[sid] = crc.door_reason(sid, [s for s in ids if s != sid], rp, chart)["reason"]
    return rp, out


# ------------------------------------------------------------------ the classifier

def test_each_planted_miss_gets_its_own_reason():
    chart = threads.CHART
    regs, lines = _scene(chart)
    _rp, why = _reasons(regs, lines, chart)
    assert why["L1wide"] == "aspect"
    assert why["L2small"] == "height_ratio"
    assert why["L3ink"] == "other_thread"
    assert why["L40"] == why["L41"] == "cluster_of_one"
    # and every ordinary letter of the three real lines is tagged
    for name in ("L1", "L2", "L3"):
        for sid in lines[name]:
            if sid not in ("L1wide", "L2small", "L3ink"):
                assert why[sid] == "tagged", sid


def test_replay_tags_exactly_what_the_tagger_tags():
    """Parity: the replay is a reading of `detect_text_clusters`, not a
    second tagger. The same regions, the tagger's default path."""
    chart = threads.CHART
    regs, _lines = _scene(chart)
    real = copy.deepcopy(regs)
    detect_text_clusters(real, None, chart=chart, rescued_ink_link=True, counters_as_drawn=True)
    tagged = {r.shape_id for r in real if r.meta.get("text_candidate")}
    rp = crc.replay_text_door(regs, chart)
    assert tagged and rp["tagged"] == tagged


def test_retag_with_nothing_set_is_the_tagger_byte_for_byte_and_never_leaks():
    """The held-out grid reads a rescue by re-running the tagger on the
    pair's pre-tag snapshot. With no keyword that IS `detect_text_clusters`
    (every meta key, every region, in order); an `@NAME` constant is set
    for that call only and the module is left exactly as it was."""
    from digitizer_core import PipelineConfig
    from digitizer_core import textcluster as T
    chart = threads.CHART
    regs, _lines = _scene(chart)
    kw = {"rescued_ink_link": True, "counters_as_drawn": True, "wide_letters": True}
    data = {"pre_tag": regs, "tag_kwargs": kw, "cfg": PipelineConfig(), "regions": regs}
    real = copy.deepcopy(regs)
    detect_text_clusters(real, None, chart=threads.chart_for(PipelineConfig()), **kw)
    got = crc.retag(data)
    assert [(r.shape_id, r.meta) for r in got] == [(r.shape_id, r.meta) for r in real]
    before = T.LETTER_HEIGHT_RATIO
    small = next(r for r in crc.retag(data, {"@LETTER_HEIGHT_RATIO": 0.6}) if r.shape_id == "L2small")
    assert small.meta.get("text_candidate")          # the 0.7x E links at 0.6 ...
    assert T.LETTER_HEIGHT_RATIO == before           # ... and the module never saw it


def test_buckets_are_the_briefs_five():
    assert crc.bucket("aspect") == "aspect"
    assert crc.bucket("height_ratio") == "height_ratio"
    assert crc.bucket("other_thread") == "other_thread"
    assert crc.bucket("cluster_of_one") == "cluster_of_one"
    for r in ("guard:solid_blob", "guard:icon", "rung:run_outline", "lane_declined", "unsewn"):
        assert crc.bucket(r) == "stage7_route"
    assert crc.bucket("stroke_cv") == "stroke_cv"        # anything else keeps its own name


def test_route_reason_reads_the_recorded_rungs():
    r = _region("A", _glyph("H", 0, 0))
    assert crc.route_reason(r, None, {"A": [("run_outline", False)]}) == "rung:run_outline"
    assert crc.route_reason(r, None, {"A": [(crc.LANE, True), ("satin_shape", False)]}) == "lane_declined"
    assert crc.route_reason(r, None, {}) == "unsewn"
    assert crc.lane_built({"A": [(crc.LANE, False)], "B": [(crc.LANE, True)]}) == {"A"}


# ------------------------------------------------------------------ the label carry

def test_carry_is_exact_on_its_own_regions_and_under_a_resize():
    """`word_tagger_eval.transfer_labels`: onto the labelled regions
    themselves it gives the labels back; onto the same scene at 1.3x the
    width (scaled about the design centre, as a resize is) every letter
    lands on its own region and nothing else does."""
    from tools.word_tagger_eval import _same_labels, transfer_labels
    chart = threads.CHART
    regs, lines = _scene(chart)
    regs.append(_region("frame", box(-2, -2, 30, 80).difference(box(-1.5, -1.5, 29.5, 79.5))))
    truth = {"lines": lines, "ignore": []}
    assert _same_labels(transfer_labels(regs, truth, regs, 1.0), truth)
    big = [_region("B" + r.shape_id, shp_scale(r.polygon, 1.3, 1.3, origin=(0, 0)), r.thread_index)
           for r in regs]
    got = transfer_labels(regs, truth, big, 1.3)
    want = {"lines": {k: ["B" + s for s in v] for k, v in lines.items()}, "ignore": []}
    assert _same_labels(got, want)


def test_carry_keeps_a_filled_counter_out_of_its_letter():
    """Stage 4 fills a small counter into its letter and the counter
    survives as a speck of the ground's ink inside it. Carried by geometry
    the speck lies wholly in the labelled letter, but it is the counter:
    `carry_labels` leaves it unlabelled, at a new width and in the same frame."""
    o = box(0, 0, 3, 4)                                   # an O with its counter filled in
    speck = box(1, 1, 2, 3)                               # the counter, in the ground's ink
    src = [_region("O", o), _region("c", speck, ink=1),
           _region("L", _glyph("L", 4, 0)), _region("E", _glyph("E", 8, 0))]
    truth = {"lines": {"OLE": ["O", "L", "E"]}, "ignore": []}
    big = [_region("B" + r.shape_id, shp_scale(r.polygon, 1.25, 1.25, origin=(0, 0)), r.thread_index)
           for r in src]
    got = crc.carry_labels(src, truth, big, 1.25)
    assert sorted(got["lines"]["OLE"]) == ["BE", "BL", "BO"]
    assert got["source"]["BO"] == "O"
    same = crc.carry_labels(src, truth, src, 1.0)
    assert sorted(same["lines"]["OLE"]) == ["E", "L", "O"]


def test_held_out_scores_each_job_at_the_value_the_others_chose():
    """A value that helps ONE job only is in-sample tuning: left out, that
    job is scored at the value the other jobs prefer (today's), so the
    held-out kappa is today's."""
    def row(job, t, d):
        return {"job": job, "_t": t, "_d": d}
    t = [True, True, False, False]
    base = [row("a", t, [True, True, False, False]), row("b", t, [True, False, False, False])]
    tuned = [row("a", t, [True, True, False, False]), row("b", t, [True, True, False, False])]
    res = crc.held_out({"off": base, "tuned": tuned}, "off")
    assert res["in_sample"]["tuned"] > res["in_sample"]["off"]
    # b's gain is b's own: left out, b is scored at what a prefers (a tie: today's)
    assert res["picks"]["b"] == "off"
    assert res["held_out"] == res["base"]


def test_carry_reproduces_the_hand_labels_at_the_corpus_width():
    """The real thing, on the smallest labelled logo (Tires, 6 regions at
    80 mm): carried onto its own generation at the corpus width, the hand
    labels come back exactly -- the check the census refuses a fixture on."""
    res = crc.carry_check("tires", None)
    assert res["stale"] == 0 and res["ok"], res
