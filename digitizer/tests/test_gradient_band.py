"""A gradient band is not a ribbon (`digitizer_core/gradient_band.py`).

Kent, 2026-09-09: the Instagram icon's Tangerine sliver — a ~2 mm colour slice
the quantizer cut out of a gradient — sewed as a satin column in a field of
tatami. The rule: a ribbon-shaped region whose boundary is mostly SOFT in the
source image (a cut through a gradient, not an edge) sews as FILL. Its shape
is exactly a stroke's shape, so every test pairs the band with a control that
differs only in the pixels at its edge.
"""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, Region, digitize, fabric_for_garment
from digitizer_core.gradient_band import (is_gradient_band, mark_gradient_bands,
                                          soft_share)
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_satin import classify_ribbon
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import chart_for
from digitizer_core.warnings_codes import GRADIENT_BANDS_AS_FILL

BRAND = "brothread-40"
CFG = PipelineConfig(thread_brand=BRAND)
CHART = chart_for(CFG)
FABRIC = fabric_for_garment("left_chest")

PPM = 10.0          # px per mm of the synthetic images
RED, MID, YELLOW = (220, 40, 40), (220, 120, 40), (220, 200, 40)


def _idx(number: str) -> int:
    return next(i for i, t in enumerate(CHART) if t.number == number)


VERMILION, TANGERINE, ORANGE = (_idx(n) for n in ("030", "209", "208"))


def _rect(x0, x1, y0, y1, thread: int, name: str, layer: int, **meta) -> Region:
    poly = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    return Region(shape_id=name, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer, **meta})


def _three_bands(**middle_meta) -> list[Region]:
    """Left 30 mm, a 4 mm band, right 30 mm — 20 mm tall, origin at (0, 0) mm.
    4 mm keeps the band under the classifier's 5 mm satin cap (p90 medial
    width) so it really is satin by shape; 6 mm was `dt_p90_cap`. The left
    parent is WIDE (30 x 20) so its own auto fill angle is 0 deg while the
    band's would be 90 — the angle inheritance has something to prove."""
    return [_rect(0, 30, 0, 20, VERMILION, "Sleft", 0),
            _rect(30, 34, 0, 20, TANGERINE, "Sband", 1, **middle_meta),
            _rect(34, 64, 0, 20, ORANGE, "Sright", 2)]


BLUE = (40, 40, 220)


def _image(gradient: bool) -> np.ndarray:
    """64 x 20 mm at 10 px/mm. `gradient`: red fades to yellow from 14 mm to
    the band's right edge at 34 mm — a gentle 20 mm ramp, so the band's LEFT
    edge is a cut through it (soft at the near AND the far probe; parent
    Sleft) — then a hard step to blue (the right edge is an edge). Else three
    flat panels with hard steps on both sides (a stripe between two fills)."""
    img = np.zeros((200, 640, 3), np.uint8)
    xs = np.arange(640)
    if gradient:
        t = np.clip((xs - 140) / 200.0, 0.0, 1.0)          # 14 mm .. 34 mm
        col = (np.array(RED)[None, :] * (1 - t)[:, None]
               + np.array(YELLOW)[None, :] * t[:, None])
        img[:, :, :] = col[None, :, :].astype(np.uint8)
        img[:, 340:] = BLUE
    else:
        img[:, :300] = RED
        img[:, 300:340] = MID
        img[:, 340:] = YELLOW
    return img


def _row_angle_deg(blocks, shape_id: str) -> float:
    """Dominant direction of the shape's fill rows, from the stitches."""
    import math
    hist = np.zeros(36)
    for b in blocks:
        for r in b.runs:
            if r.kind != "fill" or r.shape_id != shape_id:
                continue
            for (x0, y0), (x1, y1) in zip(r.points, r.points[1:]):
                d = math.hypot(x1 - x0, y1 - y0)
                if d > 1.0:
                    hist[int(math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180) // 5] += d
    return float(hist.argmax() * 5 + 2.5)


def _mark(regions, img, bg_mask=None):
    # mm (0,0) is pixel (0,0): cx = cy = 0; the synthetic page has no background
    return mark_gradient_bands(regions, img, bg_mask, 0.0, 0.0, PPM,
                               satin_max_mm=5.0, source_px_per_mm=PPM)


def _kinds(blocks, shape_id: str) -> set[str]:
    return {r.kind for b in blocks for r in b.runs if r.shape_id == shape_id}


def _sew(regions):
    planned, _ = resolve_overlaps(regions, FABRIC, CFG)
    return sequence(planned, FABRIC, CFG)


def test_fixture_sanity_the_band_is_a_ribbon_by_shape():
    """The 4 x 20 mm band earns satin on shape alone — that is the point."""
    band = _three_bands()[1]
    assert classify_ribbon(band.polygon, 5.0).satin


def test_soft_share_separates_a_gradient_cut_from_a_colour_step():
    band = _three_bands()[1].polygon
    soft_g, n_g, _ = soft_share(band, _image(True), 0.0, 0.0, PPM, probe_mm=0.4)
    soft_s, n_s, _ = soft_share(band, _image(False), 0.0, 0.0, PPM, probe_mm=0.4)
    assert n_g >= 8 and n_s >= 8
    # The short ends hit the image border and are not judged. Gradient: the
    # left long side is a cut through the ramp (soft), the right one a step
    # to blue (hard) — one soft side, about half. Panels: both sides hard.
    assert 0.4 < soft_g < 0.6, soft_g
    assert soft_s < 0.1, soft_s


def test_a_cut_through_a_gradient_sews_as_fill_at_its_parents_angle():
    regions = _three_bands()
    assert _mark(regions, _image(True)) == ["Sband"]
    assert is_gradient_band(regions[1])
    assert 0.35 <= regions[1].meta["gradient_band_soft"] < 0.6
    assert regions[1].meta["gradient_band_of"] == "Sleft", "the soft side is the parent"
    assert not is_gradient_band(regions[0]) and not is_gradient_band(regions[2])
    blocks, _ = _sew(regions)
    kinds = _kinds(blocks, "Sband")
    assert "fill" in kinds and "satin" not in kinds, kinds
    # ...and its rows run WITH the parent's, not across the band: the 30 x 20
    # parent's auto angle is 0 deg, the 4 x 20 band's own would be 90.
    parent_deg = _row_angle_deg(blocks, "Sleft")
    band_deg = _row_angle_deg(blocks, "Sband")
    assert abs(band_deg - parent_deg) <= 5.0, (band_deg, parent_deg)
    assert abs(band_deg - 90.0) > 30.0, band_deg


def test_a_stripe_between_two_flat_panels_keeps_its_satin():
    """Same regions, same colours, same shape — hard edges in the picture.
    A stroke that happens to sit between two fills is still a stroke."""
    regions = _three_bands()
    assert _mark(regions, _image(False)) == []
    assert regions[1].meta["gradient_band_soft"] < 0.1
    blocks, _ = _sew(regions)
    kinds = _kinds(blocks, "Sband")
    assert "satin" in kinds and "fill" not in kinds, kinds


def test_a_probe_in_the_background_is_hard_whatever_the_colours_say():
    """The alpha-cutout case (Becker): the RGB under transparency happens to
    be the stroke's own colour, so by colour the stroke's edge reads soft.
    The background mask says the artwork ends there — an edge."""
    regions = _three_bands()
    img = _image(True)
    # Paint everything right of the band's left edge the band's own colour
    # so both long sides read soft by colour...
    img[:, 300:] = img[:, 300][:, None, :]
    bg = np.zeros(img.shape[:2], bool)
    assert _mark(regions, img, bg) == ["Sband"], "sanity: soft by colour alone"
    # ...then declare everything from 34 mm on to be transparent background.
    bg[:, 340:] = True
    assert _mark(regions, img, bg) == ["Sband"], "one gradient side still makes a band"
    bg[:, :300] = True
    assert _mark(regions, img, bg) == [], "background on both sides: a stroke on bare fabric"
    assert regions[1].meta["gradient_band_soft"] == 0.0


def test_the_probe_floor_is_counted_in_source_pixels():
    """A 1.5 px/mm source upscaled to 10 px/mm has a 4 mm band whose third
    (1.33 mm) cannot hold 2.5 SOURCE pixels (1.67 mm): unjudgeable, untagged,
    not even measured — where the same band at 10 px/mm native is a band."""
    regions = _three_bands()
    img = _image(True)
    assert mark_gradient_bands(regions, img, None, 0.0, 0.0, PPM, satin_max_mm=5.0,
                               source_px_per_mm=1.5) == []
    assert "gradient_band_soft" not in regions[1].meta
    assert mark_gradient_bands(regions, img, None, 0.0, 0.0, PPM, satin_max_mm=5.0,
                               source_px_per_mm=PPM) == ["Sband"]


def test_a_band_whose_soft_neighbour_is_itself_a_ribbon_is_a_bevel_not_a_band():
    """The drone badge's extruded lettering: a letter face beside its own
    shaded shadow is soft at both probes, but the shadow is a ribbon, not a
    field. Same 4 mm band and gradient as the tagged case; the parent on the
    soft side is now a 4 mm ribbon instead of a 30 mm fill."""
    regions = [_rect(26, 30, 0, 20, VERMILION, "Sleft", 0),     # a ribbon, not a fill
               _rect(30, 34, 0, 20, TANGERINE, "Sband", 1),
               _rect(34, 64, 0, 20, ORANGE, "Sright", 2)]
    assert _mark(regions, _image(True)) == []
    assert regions[1].meta["gradient_band_soft"] >= 0.35, "still soft — refused on its parent"
    assert not is_gradient_band(regions[1])


def test_the_wide_fills_either_side_are_never_candidates():
    regions = _three_bands()
    _mark(regions, _image(True))
    assert "gradient_band_soft" not in regions[0].meta
    assert "gradient_band_soft" not in regions[2].meta


def test_an_explicit_satin_beats_the_band_and_a_rerun_clears_a_stale_tag():
    regions = _three_bands(tier="satin")
    _mark(regions, _image(True))
    assert is_gradient_band(regions[1]), "the tag is set; the user's tier outranks it"
    blocks, _ = _sew(regions)
    assert "satin" in _kinds(blocks, "Sband")

    regions = _three_bands()
    regions[1].meta["gradient_band"] = True
    assert _mark(regions, _image(False)) == []
    assert not is_gradient_band(regions[1])


# --- end to end: pixels in, the band sews as fill, and the plan says so ------

def _disc_png(path, blur_mm: float):
    """A yellow 40 mm rounded page with a red 20 mm disc; the disc's edge is
    blurred over `blur_mm` (0 = a sharp disc). Quantized to three colours the
    blurred edge becomes a thin orange RING — a gradient band; the sharp one
    has no thin region at all."""
    from PIL import ImageDraw, ImageFilter
    ppm = 12
    size = 60 * ppm
    page = Image.new("RGB", (size, size), (255, 255, 255))
    d = ImageDraw.Draw(page)
    c = size // 2
    d.rounded_rectangle([c - 20 * ppm, c - 20 * ppm, c + 20 * ppm, c + 20 * ppm],
                        radius=6 * ppm, fill=YELLOW)
    disc = Image.new("RGB", (size, size), YELLOW)
    ImageDraw.Draw(disc).ellipse([c - 10 * ppm, c - 10 * ppm, c + 10 * ppm, c + 10 * ppm], fill=RED)
    if blur_mm > 0:
        disc = disc.filter(ImageFilter.GaussianBlur(radius=blur_mm * ppm / 2.0))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [c - 20 * ppm, c - 20 * ppm, c + 20 * ppm, c + 20 * ppm], radius=6 * ppm, fill=255)
    page.paste(disc, (0, 0), mask)
    page.save(path)


def test_end_to_end_a_blurred_edge_becomes_a_band_that_sews_as_fill(tmp_path):
    png = tmp_path / "disc.png"
    _disc_png(png, blur_mm=6.0)          # wider than the far probe's reach
    cfg = PipelineConfig(target_width_mm=60.0, max_colors=3, forced_class="flat",
                         thread_brand=BRAND)
    result, plan = digitize(png, cfg)
    hits = [w for w in plan.warnings if w["code"] == GRADIENT_BANDS_AS_FILL]
    assert len(hits) == 1, [w["code"] for w in plan.warnings]
    ring_ids = hits[0]["ids"]
    assert ring_ids
    for sid in ring_ids:
        r = next(r for r in result.regions if r.shape_id == sid)
        assert r.meta["gradient_band_soft"] >= 0.35
        assert r.meta["gradient_band_of"]
        kinds = {run.kind for b in plan.blocks for run in b.runs if run.shape_id == sid}
        assert "satin" not in kinds and "fill" in kinds, (sid, kinds)


def test_end_to_end_a_sharp_disc_has_no_band_and_the_flag_off_marks_nothing(tmp_path):
    sharp = tmp_path / "sharp.png"
    _disc_png(sharp, blur_mm=0.0)
    cfg = PipelineConfig(target_width_mm=60.0, max_colors=3, forced_class="flat",
                         thread_brand=BRAND)
    result, plan = digitize(sharp, cfg)
    assert not [w for w in plan.warnings if w["code"] == GRADIENT_BANDS_AS_FILL]
    assert not any(is_gradient_band(r) for r in result.regions)

    blurred = tmp_path / "blur.png"
    _disc_png(blurred, blur_mm=6.0)
    off = PipelineConfig(target_width_mm=60.0, max_colors=3, forced_class="flat",
                         thread_brand=BRAND, gradient_band_fill=False)
    r_off, p_off = digitize(blurred, off)
    assert not [w for w in p_off.warnings if w["code"] == GRADIENT_BANDS_AS_FILL]
    assert not any(is_gradient_band(r) for r in r_off.regions)
    on = PipelineConfig(target_width_mm=60.0, max_colors=3, forced_class="flat",
                        thread_brand=BRAND)
    _r_on, p_on = digitize(blurred, on)
    on_pts = [r.points for b in p_on.blocks for r in b.runs]
    off_pts = [r.points for b in p_off.blocks for r in b.runs]
    assert on_pts != off_pts, "the flag must change the band's stitches"
