"""Dark thin strokes on a shaded ground -- `cfg.keep_dark_thin_strokes`,
`thin_ink.find_dark_thin_ink`, built OFF 2026-10-27.

The case: hand lettering drawn in a dark pen on a shaded body, where the ink
sits under `MERGE_DELTAE00_THRESH` of the ground and the strokes are a
fraction of a superpixel wide. The flat quantiser (`find_thin_ink`) never
gives such ink a colour of its own, the superpixels straddle it, and the merge
on their means absorbs it. On Kent's cartoon of 2026-10-27 that was four of
"HUNNY"'s five letters (Disney artwork, never committed; the pot and its
pen are redrawn here as an olive blob with a left-to-right shade).

Five contracts:
  * the five letters are the dark population, one ink, on a spool darker
    than the ground;
  * a posterised ramp is NOT dark ink (the band between two levels is not
    on one ground), so the photo goldens' invariant holds: with nothing
    found, stage 2 is byte-identical ON;
  * the constants derive from the lane's own (`DARK_INK_GROUND_DE00` is the
    boundary-contrast rule's absolute local threshold);
  * end to end on the gradient lane, OFF sews at most one of the letters
    as its own dark region and ON sews all five, each in a thread darker
    than the blob's;
  * the colour cap's dark-ink rule: a dark-ink region whose spool the cap
    drops lands on the nearest kept thread not lighter than it, never on
    its ground's.

Two more from PR #1162's sheet on `testdata/photo/summit_badge.png`
(2026-10-28), each on the fixture itself rather than a drawing:
  * a glyph's COUNTER is refused: the dark ground inside the lower bowl of
    the S of SUMMIT passes every stroke test, but its one ground is the
    thin population's S, and `find_dark_thin_ink(..., glyphs=thin.mask)`
    leaves it alone (`is_counter`);
  * a ground the carve re-shaped reads its blend shade count from the
    tails of its sample (`stage6_blend.tail_extremes`, the design path's
    read), gated by `carved_ground` on `SourcePixels.dark_ink`, so the count
    no longer hinges on which single pixel the seeded sample lands on at
    t = 0 -- OFF's read of the badge was one near-black pixel inside that
    counter.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon
from skimage.color import deltaE_ciede2000, lab2rgb

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import build_generation, finish_generation, run_stages
from digitizer_core.stage6_blend import (SHADE_COUNT_MIN, SourcePixels, _choose_shade_count,
                                         _sample_pixels, blend_fill, carved_ground,
                                         detect_ramp_detail, tail_extremes)
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import (BOUNDARY_CONTRAST_MERGE_FACTOR,
                                                 MERGE_DELTAE00_THRESH, segment)
from digitizer_core.stage4_vectorize import enforce_color_cap
from digitizer_core.thin_ink import (DARK_INK_GROUND_DE00, DARK_INK_MIN_CONTRAST_DE00,
                                     THIN_INK_GROUND_SHARE, find_dark_thin_ink, find_thin_ink,
                                     is_counter)
from digitizer_core.threads import CHART, rgb_to_lab

from .test_thin_population import _foreground, _steep_ramp

# The blob's ground and the pen, in Lab: the cartoon's pot read (66.1, -4.1,
# 18.6) and its ink (43.7, -1.0, 20.5), 21.5 dE00 apart -- under the merge
# threshold, which is the whole point. The pen applies INK - GROUND to the
# shaded ground under it (`_lettered_blob`).
GROUND_LAB = (66.0, -4.0, 19.0)
INK_LAB = (44.0, -1.0, 20.0)
BLOB_BOX_MM = (-18.0, -12.0, 24.0, 12.0)   # x0, y0, x1, y1 round the blob, design mm


def _lettered_blob(path: Path) -> np.ndarray:
    """A 41 x 26 mm olive ellipse shaded left to right (L* +12 to -12 round
    the ground), carrying "HUNNY" in a 0.8 mm pen whose ink TRACKS the
    shading: every pen pixel is the ground under it minus the cartoon's own
    ink offset (-22.4 L*, +3.1 a*, +1.9 b*, the pot's Lab to its ink's). Five
    letters ~5.5 mm tall, each touching nothing but the blob, every stroke
    under the detail floor (Hershey thickness 1: any thicker draws 11-12 px
    strokes, AT the floor, and three letters fail the width test).

    Five flat panels of other colours sit round the blob -- the cartoon's
    yellow, red, white, dark brown and blue -- so the six-colour budget is
    spent the way it is there. Both are needed to show the loss: with a pen
    of one colour the flat quantiser gives the ink a cluster of its own and
    the thin population reads it, panels or not; with the tracking pen and
    the panels, main sews none of the five (measured 2026-10-27). The panels
    set the art box, so a 60 mm target is 9.7 px/mm. -> the pen's mask."""
    h, w = 400, 600
    img = np.full((h, w, 3), 255, np.uint8)
    for (x0, y0, x1, y1), rgb in (((10, 10, 590, 60), (235, 170, 40)),        # yellow
                                  ((10, 340, 590, 390), (210, 30, 30)),       # red
                                  ((10, 70, 60, 330), (250, 250, 248)),       # near-white
                                  ((540, 70, 590, 330), (60, 48, 46)),        # dark brown
                                  ((70, 70, 120, 330), (40, 80, 200))):       # blue
        img[y0:y1, x0:x1] = rgb
    lab = np.empty((h, w, 3), float)
    lab[..., 0] = np.linspace(GROUND_LAB[0] + 12, GROUND_LAB[0] - 12, w)[None, :]
    lab[..., 1] = GROUND_LAB[1]
    lab[..., 2] = GROUND_LAB[2]
    pen = np.zeros((h, w), np.uint8)
    cv2.putText(pen, "HUNNY", (195, 225), cv2.FONT_HERSHEY_SIMPLEX, 2.2, 255, 1, cv2.LINE_AA)
    cover = pen.astype(float) / 255.0
    for ch, delta in enumerate(np.subtract(INK_LAB, GROUND_LAB)):
        lab[..., ch] += delta * cover
    shaded = (lab2rgb(lab) * 255).round().astype(np.uint8)
    blob = np.zeros((h, w), np.uint8)
    cv2.ellipse(blob, (330, 200), (200, 125), 0, 0, 360, 255, -1)
    img[blob > 0] = shaded[blob > 0]
    cv2.imwrite(str(path), img[..., ::-1])
    return pen > 127


def _thread_l(index: int) -> float:
    return float(rgb_to_lab(np.array([CHART[index].rgb], float))[0, 0])


def _dark_regions_in_blob(regions) -> list:
    """Regions inside the blob box sewn in a thread at least
    `DARK_INK_MIN_CONTRAST_DE00` L* darker than the ground."""
    x0, y0, x1, y1 = BLOB_BOX_MM
    out = []
    for r in regions:
        c = r.polygon.centroid
        if x0 <= c.x <= x1 and y0 <= c.y <= y1 and _thread_l(r.thread_index) < GROUND_LAB[0] - DARK_INK_MIN_CONTRAST_DE00:
            out.append(r)
    return out


def test_ground_tolerance_is_the_boundary_contrast_rules_local_threshold():
    # 13.0 dE00: `BOUNDARY_CONTRAST_MERGE_FACTOR`'s numerator, the one
    # absolute "same region" number the merge already holds. Pinned so the
    # two cannot drift apart silently.
    assert DARK_INK_GROUND_DE00 == pytest.approx(MERGE_DELTAE00_THRESH * BOUNDARY_CONTRAST_MERGE_FACTOR)
    assert 0.5 < THIN_INK_GROUND_SHARE < 1.0


def test_five_letters_on_a_shaded_blob_are_the_dark_population_as_one_ink(tmp_path):
    art = tmp_path / "lettered_blob.png"
    pen = _lettered_blob(art)
    cfg = PipelineConfig(target_width_mm=60.0, max_colors=6)
    p = prep(str(art), cfg, design_class="gradient")
    assert p.rgb.shape[:2] == pen.shape, "the prep raster is the source raster here"
    dark = find_dark_thin_ink(p, cfg, _foreground(p))
    assert dark is not None
    assert dark.components == 5, dark.components
    assert len(dark.spools) == 1 and dark.dark == 1, dark.spools
    assert _thread_l(dark.spools[0]) < GROUND_LAB[0] - DARK_INK_MIN_CONTRAST_DE00
    assert set(np.unique(dark.labels[dark.mask]).tolist()) == {0}
    assert (dark.labels[~dark.mask] == -1).all()
    # the kept pixels are the pen's, not the blob's, and most of the pen is kept
    assert (pen & dark.mask).sum() / dark.mask.sum() > 0.9
    assert (pen & dark.mask).sum() / pen.sum() > 0.8


def test_a_posterised_ramp_is_not_dark_ink_and_on_is_byte_identical(tmp_path):
    art = tmp_path / "ramp.png"
    _steep_ramp(art)
    cfg = PipelineConfig(target_width_mm=60.0, max_colors=6)
    p = prep(str(art), cfg, design_class="gradient")
    assert find_dark_thin_ink(p, cfg, _foreground(p)) is None
    off = segment(p, cfg, thin_population=True)
    on = segment(p, cfg, thin_population=True, dark_population=True)
    assert np.array_equal(off.labels, on.labels)
    assert off.thread_indices == on.thread_indices
    assert on.dark_ink_labels is None


def test_on_the_gradient_lane_off_loses_the_letters_and_on_sews_all_five(tmp_path):
    art = tmp_path / "lettered_blob.png"
    _lettered_blob(art)

    def run(flag: bool):
        cfg = PipelineConfig(target_width_mm=60.0, max_colors=6, forced_class="gradient",
                             edge_cap="none", keep_dark_thin_strokes=flag)
        return run_stages(str(art), cfg)

    off = run(False)
    on = run(True)
    assert off.design_class == "gradient" and on.design_class == "gradient"
    lost = _dark_regions_in_blob(off.regions)
    found = _dark_regions_in_blob(on.regions)
    assert len(lost) <= 1, [(r.thread_number, round(r.area_mm2, 2)) for r in lost]
    assert len(found) >= 5, [(r.thread_number, round(r.area_mm2, 2)) for r in found]
    letters = [r for r in found if r.meta.get("dark_ink")]
    assert len(letters) >= 5
    assert len({r.thread_index for r in letters}) == 1, "one ink, one thread"
    # each letter is its own region, 3-8 mm tall, not a blob-sized piece
    for r in letters:
        _x0, y0, _x1, y1 = r.polygon.bounds
        assert 3.0 < y1 - y0 < 8.0, (r.shape_id, y1 - y0)
    # the blob itself is still one region in a thread the letters do not wear
    blob = max((r for r in on.regions), key=lambda r: r.area_mm2)
    assert blob.thread_index not in {r.thread_index for r in letters}


def _region(thread_index: int, area: float, **meta) -> Region:
    s = area ** 0.5
    return Region(shape_id=f"S{thread_index}", polygon=Polygon([(0, 0), (s, 0), (s, s), (0, s)]),
                  thread_index=thread_index, thread_number=CHART[thread_index].number,
                  area_mm2=area, meta=meta)


def test_color_cap_sends_dark_ink_to_a_dark_kept_thread_not_its_ground():
    # The cartoon's threads: the pot (Dark Rattan), the pen (Olive Drab, the
    # nearest chart colour to the ink and only 7 dE00 from the pot's thread),
    # the outline (Very Dark Brown), and three more big areas. max_colors=5
    # drops the pen, the smallest sewn area.
    by_number = {t.number: i for i, t in enumerate(CHART)}
    pot, pen, outline = by_number["0763"], by_number["0454"], by_number["0576"]
    others = [by_number[n] for n in ("0015", "0702", "1902")]
    regions = [_region(pot, 1000.0), _region(outline, 300.0)] + [_region(t, 200.0) for t in others]
    regions += [_region(pen, 7.0, dark_ink=True) for _ in range(5)]
    regions.append(_region(pen, 7.0))     # the same spool on an ordinary region
    warnings = enforce_color_cap(regions, CHART, 5)
    assert warnings and warnings[0]["dropped"] == 1
    letters = [r for r in regions if r.meta.get("dark_ink")]
    assert {r.thread_index for r in letters} == {outline}, [r.thread_number for r in letters]
    assert all(r.meta["color_cap_merged_from"] == "0454" for r in letters)
    plain = [r for r in regions if r.thread_number != CHART[outline].number and r.meta.get("color_cap_merged_from")]
    assert len(plain) == 1 and plain[0].thread_index == pot, "an ordinary region keeps the plain nearest"
    # no dark-ink regions: the cap it always was, including on the same spool
    again = [_region(pot, 1000.0), _region(outline, 300.0)] + [_region(t, 200.0) for t in others]
    again += [_region(pen, 7.0) for _ in range(6)]
    enforce_color_cap(again, CHART, 5)
    assert {r.thread_index for r in again if r.meta.get("color_cap_merged_from")} == {pot}


# --- summit_badge: the counter and the carved ground (2026-10-28) -----------
SUMMIT = Path(__file__).resolve().parent.parent / "testdata" / "photo" / "summit_badge.png"
# The Studio request at 80 mm spans the badge's 894 px art box: 11.175 px/mm.
SUMMIT_PX_PER_MM = 11.175


def _summit_word_crop(path: Path) -> None:
    """Rows 700-800, columns 150-750 of the 900 px badge: the word SUMMIT on
    the vignette, 53.7 x 8.9 mm at the Studio's scale."""
    img = cv2.imread(str(SUMMIT), cv2.IMREAD_UNCHANGED)
    assert img is not None and img.shape[:2] == (900, 900)
    cv2.imwrite(str(path), img[700:800, 150:750])


def test_the_counter_of_the_s_is_refused_on_the_summit_word(tmp_path):
    art = tmp_path / "summit_word.png"
    _summit_word_crop(art)
    cfg = PipelineConfig(target_width_mm=600 / SUMMIT_PX_PER_MM, max_colors=6)
    p = prep(str(art), cfg, design_class="gradient")
    assert abs(p.px_per_mm - SUMMIT_PX_PER_MM) < 0.01
    valid = _foreground(p)
    thin = find_thin_ink(p, cfg, valid)
    assert thin is not None, "the letters are the thin population"
    # The reader as #1160 shipped it (no glyphs): one component, the dark
    # ground inside the lower bowl of the S -- badge px (287..316, 739..760),
    # crop px (137, 39), 29 x 21, 2.9 mm2 -- ringed by the S.
    bare = find_dark_thin_ink(p, cfg, valid)
    assert bare is not None and bare.components == 1
    n, cc, st, _ = cv2.connectedComponentsWithStats(bare.mask.astype(np.uint8), connectivity=8)
    x, y, w, h, area = (int(v) for v in st[1, :5])
    assert abs(x - 137) <= 2 and abs(y - 39) <= 2 and abs(w - 29) <= 2 and abs(h - 21) <= 2, (x, y, w, h)
    assert 2.5 < area / p.px_per_mm ** 2 < 3.5
    comp = (cc == 1).astype(np.uint8)
    ring = ((cv2.dilate(comp, np.ones((9, 9), np.uint8)) > 0)
            & ~(cv2.dilate(comp, np.ones((5, 5), np.uint8)) > 0))
    held = np.count_nonzero(ring & thin.mask) / np.count_nonzero(ring & valid)
    assert held > 0.5, f"the thin population holds {held:.2f} of the ring"
    # With the thin population's mask as `glyphs`, the counter is refused.
    assert find_dark_thin_ink(p, cfg, valid, glyphs=thin.mask) is None
    # The rule on its own terms: the one-ground share, applied to glyph pixels.
    same = np.ones(4, bool)
    assert is_counter(same, np.array([True, True, True, False]))
    assert not is_counter(same, np.array([True, True, False, False]))
    # End to end on the crop, the flag ON carves nothing: no dark-ink region,
    # the same regions as OFF.
    off = run_stages(str(art), PipelineConfig(target_width_mm=600 / SUMMIT_PX_PER_MM, max_colors=6,
                                              forced_class="gradient"))
    on = run_stages(str(art), PipelineConfig(target_width_mm=600 / SUMMIT_PX_PER_MM, max_colors=6,
                                             forced_class="gradient", keep_dark_thin_strokes=True))
    assert not any(r.meta.get("dark_ink") for r in on.regions)
    assert len(on.regions) == len(off.regions)
    assert sorted(round(r.area_mm2, 3) for r in on.regions) == sorted(round(r.area_mm2, 3) for r in off.regions)


def test_a_carved_ground_reads_its_shade_count_from_the_tails_on_summit():
    """The Studio's own request on the whole badge (a crop breaks the vignette's
    radial fit: the bottom half reads r2 0.03, a quadrant is refused as speckled)."""
    from digitizer_service.app import _decode, _parse_config
    from tools.fremont_triage import studio_request
    data = SUMMIT.read_bytes()
    cfg = PipelineConfig(**_parse_config(json.dumps({**studio_request(80.0), "garment_id": "left_chest"})))
    assert not cfg.keep_dark_thin_strokes
    gen = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    p = gen.p
    x0, y0, x1, y1 = p.art_bbox
    sp = SourcePixels(rgb=p.rgb, px_per_mm=p.px_per_mm, origin_px=((x0 + x1) / 2.0, (y0 + y1) / 2.0),
                      gradient_class=True)
    ground = max(result.regions, key=lambda r: r.area_mm2)      # the vignette, ~2,776 mm2
    assert ground.area_mm2 > 2000
    # The counter as #1160's reader found it (no glyphs), in stage 6's frame.
    dark = find_dark_thin_ink(p, cfg, _foreground(p))
    assert dark is not None and dark.components == 1
    contours, _ = cv2.findContours(dark.mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pts = max(contours, key=cv2.contourArea).reshape(-1, 2)
    counter = Polygon([sp.to_mm(x + 0.5, y + 0.5) for x, y in pts]).buffer(0)
    assert 2.0 < counter.area < 3.5
    assert counter.intersection(ground.polygon).area > 0.9 * counter.area, "the counter lies in the ground"
    diff = ground.polygon.difference(counter)
    carved = max(getattr(diff, "geoms", [diff]), key=lambda g: g.area)
    with_ink = dataclasses.replace(sp, dark_ink=counter)

    # The gate: only a ground the ink was carved from, and only when there is ink.
    assert not carved_ground(ground.polygon, sp)
    assert carved_ground(ground.polygon, with_ink) and carved_ground(carved, with_ink)
    near = min((r for r in result.regions if r.area_mm2 > 5 and not r.polygon.intersects(counter)),
               key=lambda r: r.polygon.distance(counter))
    assert near.polygon.distance(counter) > 1.0 and not carved_ground(near.polygon, with_ink), near.shape_id

    def read(poly, source):
        _runs, report = blend_fill(dataclasses.replace(ground, polygon=poly), source, cfg)
        return report

    # OFF (no ink): the two-pixel read, exactly as shipped.
    off = read(ground.polygon, sp)
    assert off["blend_shades"] >= SHADE_COUNT_MIN, off.get("blend_reject")
    model, _reject, _r2 = detect_ramp_detail(ground.polygon, sp, speckle_r2_override=cfg.blend_speckle_r2_override,
                                             speckle_residual=cfg.blend_speckle_residual)
    assert model is not None
    mm_x, mm_y, rgb, _m, _c = _sample_pixels(ground.polygon, sp)
    lab = rgb_to_lab(rgb)
    ts = np.array([model.t(x, y) for x, y in zip(mm_x, mm_y)])
    two_pixel = float(deltaE_ciede2000(lab[np.argmin(ts)][None, :], lab[np.argmax(ts)][None, :])[0])
    assert off["blend_shades"] == _choose_shade_count(two_pixel)
    # The sample holds near-black pixels (the badge's outlines inside the
    # ground's raster) 30 L* and more below the dark tail's mean: whichever
    # of them the seeded draw puts at t = 0 is the two-pixel read's extreme.
    lo, hi = tail_extremes(ts, lab)
    assert lab[:, 0].min() < lo[0] - 30.0, (lab[:, 0].min(), lo[0])
    # ON (ink carved): the tail read, the same count with the counter in the
    # ground and out of it, and within a dE00 of itself.
    whole = read(ground.polygon, with_ink)
    after = read(carved, with_ink)
    assert whole["blend_shades"] == after["blend_shades"] >= SHADE_COUNT_MIN
    tails = float(deltaE_ciede2000(lo[None, :], hi[None, :])[0])
    assert whole["blend_shades"] == _choose_shade_count(tails)
    model_c, _rj, _r = detect_ramp_detail(carved, sp, speckle_r2_override=cfg.blend_speckle_r2_override,
                                          speckle_residual=cfg.blend_speckle_residual)
    cx, cy, crgb, _m, _c = _sample_pixels(carved, sp)
    clab = rgb_to_lab(crgb)
    cts = np.array([model_c.t(x, y) for x, y in zip(cx, cy)])
    clo, chi = tail_extremes(cts, clab)
    assert abs(float(deltaE_ciede2000(clo[None, :], chi[None, :])[0]) - tails) < 1.0
