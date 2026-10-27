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
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon
from skimage.color import lab2rgb

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import (BOUNDARY_CONTRAST_MERGE_FACTOR,
                                                 MERGE_DELTAE00_THRESH, segment)
from digitizer_core.stage4_vectorize import enforce_color_cap
from digitizer_core.thin_ink import (DARK_INK_GROUND_DE00, DARK_INK_MIN_CONTRAST_DE00,
                                     THIN_INK_GROUND_SHARE, find_dark_thin_ink)
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
