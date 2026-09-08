"""`cfg.keep_thin_strokes` — absorb by colour, not by adjacency (flat lane).

The contract, in four parts. OFF is byte-identical: the flat goldens pin the
pipeline, and the unit tests here pin `resolve_small_regions`'s own
behaviour with and without the flag on the same masks. ON, a sub-floor
region touching a neighbour of ANOTHER colour that clears the run tier's
floors is kept for the run tier; a same-colour sliver is absorbed as before;
a contrasting speck under the floors is absorbed as before; and without
layer colours (how the photo segmenters call it) the flag is inert. On the
primary golden the plan PREDICTED no change — the teal patch "fails the loop
proxy (2 mm against 2.2)" — and the measurement says otherwise: the patch is
10 px = 1.19 mm at 80 mm, its proxy 2.38 mm clears the 2.2 mm floor, and ON
it is kept as its own teal run (one more cone, +3 stitches, +1 trim). OFF the
golden holds; that pair is pinned here as measured. And on a fixture built
for it, the strokes the flag keeps are SEWN in their own colour, read by
`tools/thin_strokes.py` on the stitches.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

from digitizer_core import PipelineConfig, digitize, machine
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions
from digitizer_core.threads import rgb_to_lab
from digitizer_core.warnings_codes import ABSORBED_SMALL_SHAPES, DROPPED_SMALL_SHAPES

from .conftest import TESTDATA, codes

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

PX_PER_MM = 10.0
FRAME = (200, 200)
# Layer colours: a red panel, a black stroke, a near-red sliver (2 dE76 from
# the panel, inside `merge_delta_e` 6.0), a black speck.
RGB = np.array([(200, 30, 30), (0, 0, 0), (205, 32, 34), (0, 0, 0)], float)


def _mask(rows: slice, cols: slice, layer: int, carve=()) -> RegionMask:
    m = np.zeros(FRAME, bool)
    m[rows, cols] = True
    for r, c in carve:
        m[r, c] = False
    return RegionMask.from_full(m, layer)


def _scene() -> list[RegionMask]:
    """A 16 x 16 mm red panel with, cut into it, a 0.3 x 6 mm black stroke
    (180 px: under the 225 px detail floor, over the 16 px noise floor, loop
    proxy 120 px against 22) and a 3 x 3 px black speck (9 px: under the
    noise floor); along its top edge a 2 x 60 px near-red sliver."""
    stroke = (slice(100, 103), slice(40, 100))
    speck = (slice(150, 153), slice(150, 153))
    panel = _mask(slice(20, 180), slice(20, 180), 0, carve=[stroke, speck])
    return [panel, _mask(*stroke, 1), _mask(slice(18, 20), slice(60, 120), 2), _mask(*speck, 3)]


def _floors_hold():
    cfg = PipelineConfig()
    assert (cfg.min_detail_mm * PX_PER_MM) ** 2 == 225.0
    assert machine.RUN_MIN_AREA_MM2 * PX_PER_MM ** 2 <= 16.0
    assert machine.RUN_MIN_LOOP_MM * PX_PER_MM <= 120.0
    assert cfg.merge_delta_e >= 3.0


def test_the_scene_is_what_its_docstring_says():
    _floors_hold()
    panel, stroke, sliver, speck = _scene()
    assert stroke.area == 180 and sliver.area == 120 and speck.area == 9
    assert panel.area == 160 * 160 - 180 - 9
    lab = rgb_to_lab(RGB)
    assert np.linalg.norm(lab[2] - lab[0]) < PipelineConfig().merge_delta_e
    assert np.linalg.norm(lab[1] - lab[0]) > PipelineConfig().merge_delta_e


def test_flag_off_every_small_region_is_absorbed_into_the_panel():
    kept, warnings = resolve_small_regions(_scene(), PipelineConfig(), PX_PER_MM,
                                           layer_lab=rgb_to_lab(RGB))
    assert len(kept) == 1
    assert kept[0].layer == 0 and kept[0].area == 160 * 160 + 120
    assert ABSORBED_SMALL_SHAPES in {w["code"] for w in warnings}


def test_flag_on_keeps_the_contrasting_stroke_and_still_absorbs_the_sliver_and_the_speck():
    cfg = PipelineConfig(keep_thin_strokes=True)
    kept, _warnings = resolve_small_regions(_scene(), cfg, PX_PER_MM, layer_lab=rgb_to_lab(RGB))
    by_layer = {k.layer: k for k in kept}
    assert set(by_layer) == {0, 1}, [k.layer for k in kept]
    assert by_layer[1].area == 180, "the stroke is kept as itself, not grown"
    # The panel took the near-red sliver (a sliver OF it) and the speck (which
    # clears no floor, so colour never came into it).
    assert by_layer[0].area == 160 * 160 - 180 + 120


def test_without_layer_colours_the_flag_is_inert_which_is_the_photo_lanes_contract():
    cfg = PipelineConfig(keep_thin_strokes=True)
    on, w_on = resolve_small_regions(_scene(), cfg, PX_PER_MM, layer_lab=None)
    off, w_off = resolve_small_regions(_scene(), PipelineConfig(), PX_PER_MM, layer_lab=None)
    assert [(k.layer, k.area, k.origin) for k in on] == [(k.layer, k.area, k.origin) for k in off]
    assert w_on == w_off


def test_the_user_facing_rescue_opt_out_still_wins():
    cfg = PipelineConfig(keep_thin_strokes=True, small_shape_rescue=False)
    kept, _ = resolve_small_regions(_scene(), cfg, PX_PER_MM, layer_lab=rgb_to_lab(RGB))
    assert [k.layer for k in kept] == [0], "strict floor behaviour absorbs the stroke too"


def test_a_contrasting_stroke_that_fails_the_loop_proxy_is_absorbed_as_before():
    """1 x 1.5 mm: 150 px clears the noise floor, but 2 * max(10, 15) = 30 px
    against a 22 px loop floor... clears it too — so shorten it: 1 x 1 mm is
    100 px with a 20 px proxy, under the floor, and colour never decides."""
    stub = (slice(60, 70), slice(60, 70))
    panel = _mask(slice(20, 180), slice(20, 180), 0, carve=[stub])
    kept, _ = resolve_small_regions([panel, _mask(*stub, 1)], PipelineConfig(keep_thin_strokes=True),
                                    PX_PER_MM, layer_lab=rgb_to_lab(RGB))
    assert [k.layer for k in kept] == [0]
    assert kept[0].area == 160 * 160


def test_on_the_primary_golden_off_absorbs_the_teal_patch_and_on_keeps_it_as_a_run():
    """The plan predicted the flag would change nothing here: the teal patch
    "differs in colour but fails the loop proxy (2 mm against 2.2)". Measured
    2026-09-08, it does not fail it — the patch is 10 px = 1.19 mm at 80 mm,
    2 * max(w, h) = 2.38 mm — so ON it is what the rule says a contrasting
    small element that clears the floors is: kept, tagged rescued, sewn as a
    run in its own thread. OFF is today's answer (the flat golden pins it).
    The orange dot is isolated and drops either way."""
    off, off_plan = digitize(TESTDATA / "logo_whitebg.png", PipelineConfig(target_width_mm=80.0))
    on, on_plan = digitize(TESTDATA / "logo_whitebg.png",
                           PipelineConfig(target_width_mm=80.0, keep_thin_strokes=True))
    assert ABSORBED_SMALL_SHAPES in codes(off) and DROPPED_SMALL_SHAPES in codes(off)
    assert [r for r in off.regions if r.thread_number == "4531"] == [], "OFF: teal survived"
    teal = [r for r in on.regions if r.thread_number == "4531"]
    assert len(teal) == 1 and teal[0].meta.get("rescued_small_shape"), "ON: the teal patch is kept"
    assert 1.0 < teal[0].area_mm2 < 1.6, teal[0].area_mm2
    assert ABSORBED_SMALL_SHAPES not in codes(on) and DROPPED_SMALL_SHAPES in codes(on)
    # Everything else is the same design: one more region, one more colour
    # block, a run's worth of stitches.
    assert len(on.regions) == len(off.regions) + 1
    assert len(on_plan.blocks) == len(off_plan.blocks) + 1
    assert 0 < on_plan.stats.stitch_count - off_plan.stats.stitch_count < 60
    kinds = {run.kind for _b, run in on_plan.iter_runs() if run.shape_id == teal[0].shape_id}
    assert kinds == {"run"}, kinds


def _strokes_on_a_panel(path: Path) -> None:
    """A 50 x 20 mm yellow panel carrying a row of six 0.6 x 3 mm dark
    bars — glyph-sized strokes: each 1.8 mm², under the 2.25 mm² floor, each
    touching nothing but the panel, and each a thin stroke to the instrument
    (0.6 mm wide, a 2.4 mm skeleton). The panel's 500 px ARE the art bbox
    (the white margin is background), so a 50 mm target is 10 px/mm."""
    img = np.full((300, 600, 3), 255, np.uint8)
    cv2.rectangle(img, (50, 50), (549, 249), (40, 200, 230), -1)       # yellow panel (BGR)
    for k in range(6):
        x = 120 + 60 * k
        cv2.rectangle(img, (x, 135), (x + 5, 164), (30, 30, 30), -1)    # 6 x 30 px = 0.6 x 3 mm
    cv2.imwrite(str(path), img)


def test_on_a_fixture_built_for_it_the_kept_marks_are_sewn_in_their_own_colour(tmp_path):
    import thin_strokes as ts

    art = tmp_path / "strokes_on_panel.png"
    _strokes_on_a_panel(art)
    off = ts.run(art, 50.0, "left_chest", forced_class="flat")
    on = ts.run(art, 50.0, "left_chest", forced_class="flat", flag="keep_thin_strokes")
    # The instrument sees six thin strokes either way (it reads the artwork);
    # OFF they are panel-coloured thread, so every one is lost.
    assert off["thin_strokes"] == 6 and on["thin_strokes"] == 6, (off["thin_strokes"], on["thin_strokes"])
    assert off["recall"] == 0.0, off["recall"]
    assert on["recall"] >= 0.8, on["recall"]
    assert on["regions"] >= off["regions"] + 6
