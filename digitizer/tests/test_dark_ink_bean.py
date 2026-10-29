"""Dark-read strokes sewn as a bean ON their ground -- `cfg.dark_ink_bean`,
`thin_ink.bean_dark_ink` / `ink_after_ground`, built OFF 2026-10-28 (Kent on
the Pooh pot: "No holes + bean (Recommended)").

On main the pot cut a hole for each HUNNY letter and sewed its satin edge
round every hole (the starbursts), and the letters sewed as 0.5-0.75 mm
satin. ON, each `dark_ink` region sews as a bean along its skeleton (the
bean-letter path), after its ground, and stage 5's `ground_under` sews the
ground through underneath.

Contracts:
  * only a pen line goes: ink within `BEAN_MAX_GROUND_DE00` of its ground's
    thread; the Fremont wordmark (Black on White, 100 dE00) sewed as
    hairline skeletons and keeps its satin;
  * a dark stroke gets bean spines; its ground keeps its hole (closing it
    first makes the ground "a colour already down" that clips the stroke to
    nothing, measured on the cartoon) and stops being lettering (the
    house-angle group took the pot into the Column lane: one 37 mm satin);
  * a stroke the review pinned to a tier, and a region that is not dark
    ink, are left alone;
  * a stroke whose ground sews in the same or a later layer moves to a
    layer of its own right after the ground's; already after: untouched;
  * end to end on the lettered blob: every letter sews bean only, the blob
    sews fill under each letter (no hole), and no letter is lost.
"""
from __future__ import annotations

import json

from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig
from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.regions import Region
from digitizer_core.thin_ink import BEAN_MAX_GROUND_DE00, bean_dark_ink, ink_after_ground
from digitizer_core.threads import CHART

from .test_keep_dark_thin_strokes import _lettered_blob


_IDX = {c.number: i for i, c in enumerate(CHART)}
POT, PEN = _IDX["0763"], _IDX["1233"]          # the Pooh pot and its pen, 17.8 dE00
WHITE, BLACK = _IDX["0015"], _IDX["0020"]      # the Fremont wordmark, 100 dE00


def _r(sid: str, poly: Polygon, thread_index: int, layer: int, **meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread_index,
                  thread_number=CHART[thread_index].number, area_mm2=float(poly.area),
                  meta={"layer": layer, **meta})


# A 20 x 20 mm ground with an "L"-ish stroke hole, and the stroke in it.
STROKE = Polygon([(4, 4), (4.6, 4), (4.6, 12), (10, 12), (10, 12.6), (4, 12.6)])
GROUND = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)], [list(STROKE.exterior.coords)])


def test_flag_is_on_by_default_since_the_flip():
    # Kent 2026-10-29, after #1181: "Flip ON (Recommended)".
    assert PipelineConfig().dark_ink_bean is True


def test_the_gate_sits_between_the_pen_lines_and_the_wordmark():
    # thread to thread, as measured on the sheet (`BEAN_MAX_GROUND_DE00`'s note)
    from digitizer_core.thin_ink import _thread_de00
    pens = [("0454", "0763"), ("0873", "0015"), ("0862", "0015"), ("0454", "6071")]
    assert all(_thread_de00(_IDX[a], _IDX[b]) <= BEAN_MAX_GROUND_DE00 for a, b in pens)
    assert _thread_de00(BLACK, WHITE) > BEAN_MAX_GROUND_DE00


def test_a_dark_stroke_gets_spines_and_its_ground_keeps_the_hole_and_is_no_letter():
    ground = _r("G", GROUND, POT, 0, lettering_group=True)
    stroke = _r("K", STROKE, PEN, 1, dark_ink=True)
    other = _r("O", Polygon([(30, 0), (31, 0), (31, 8), (30, 8)]), PEN, 1)
    assert bean_dark_ink([ground, stroke, other]) == 1
    spines = stroke.meta[BEAN_LETTER_KEY]
    assert spines and all(len(s) >= 2 for s in spines)
    # the spines run inside the stroke
    assert all(STROKE.buffer(0.2).contains(Point(p)) for s in spines for p in s)
    assert ground.polygon.equals(GROUND) and len(ground.polygon.interiors) == 1
    assert ground.meta["lettering_group"] is False
    assert BEAN_LETTER_KEY not in other.meta


def test_a_pinned_stroke_is_left_alone():
    ground = _r("G", GROUND, POT, 0, lettering_group=True)
    stroke = _r("K", STROKE, PEN, 1, dark_ink=True, tier="satin")
    assert bean_dark_ink([ground, stroke]) == 0
    assert BEAN_LETTER_KEY not in stroke.meta
    assert ground.meta["lettering_group"] is True


def test_designed_lettering_far_from_its_ground_keeps_its_satin():
    ground = _r("G", GROUND, WHITE, 0, lettering_group=True)
    stroke = _r("K", STROKE, BLACK, 1, dark_ink=True)
    assert bean_dark_ink([ground, stroke]) == 0
    assert BEAN_LETTER_KEY not in stroke.meta
    assert ground.meta["lettering_group"] is True


def test_a_stroke_on_no_ground_is_left_alone():
    stroke = _r("K", STROKE, PEN, 1, dark_ink=True)
    assert bean_dark_ink([stroke]) == 0
    assert BEAN_LETTER_KEY not in stroke.meta


def test_a_stroke_under_its_ground_moves_to_a_layer_right_after_it():
    stroke = _r("K", STROKE, PEN, 0, dark_ink=True, **{BEAN_LETTER_KEY: [[(4.3, 4), (4.3, 12)]]})
    ground = _r("G", GROUND, POT, 1)
    later = _r("Z", Polygon([(30, 0), (35, 0), (35, 5), (30, 5)]), 30, 2)
    out = ink_after_ground([stroke, ground, later])
    layer = {r.shape_id: r.meta["layer"] for r in out}
    assert layer["G"] < layer["K"] < layer["Z"], layer
    assert [r.shape_id for r in out] == ["G", "K", "Z"]
    # already after its ground: the list itself, untouched
    again = ink_after_ground(out)
    assert again is out


def test_on_the_lettered_blob_letters_sew_bean_on_a_whole_ground(tmp_path):
    art = tmp_path / "lettered_blob.png"
    _lettered_blob(art)
    cfg = PipelineConfig(target_width_mm=60.0, max_colors=6, forced_class="gradient",
                         edge_cap="none", keep_dark_thin_strokes=True, dark_ink_bean=True)
    result = run_stages(str(art), cfg)
    letters = [r for r in result.regions if r.meta.get("dark_ink")]
    assert len(letters) >= 5
    plan = plan_stitches(result, cfg)
    lost = [w for w in plan.warnings if w.get("code") == "SHAPE_NOT_STITCHED"]
    lost_ids = {i for w in lost for i in w.get("ids", ())}
    assert not lost_ids & {r.shape_id for r in letters}, json.dumps(lost, default=str)
    kinds: dict[str, set] = {}
    ground_pts: list[tuple[float, float]] = []
    ids = {r.shape_id for r in letters}
    blob = max(result.regions, key=lambda r: r.area_mm2)
    for _b, run in plan.iter_runs():
        if run.shape_id in ids:
            kinds.setdefault(run.shape_id, set()).add(run.kind)
        elif run.shape_id == blob.shape_id and run.kind == "fill":
            ground_pts.extend(run.points)
    for r in letters:
        assert kinds.get(r.shape_id), f"{r.shape_id} sewed nothing"
        assert kinds[r.shape_id] <= {"run", "travel"}, (r.shape_id, kinds[r.shape_id])
    # the ground fills through under every letter: fill needles inside each one
    for r in letters:
        inside = sum(1 for p in ground_pts if r.polygon.buffer(0.3).contains(Point(p)))
        assert inside > 0, r.shape_id
