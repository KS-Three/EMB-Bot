"""Stray dark reads refused -- `cfg.dark_ink_refuse_strays`, built OFF
2026-10-28 on Kent's "Keep ON, queue refusal (worker's pick)" on PR #1172.

#1172 flipped `keep_dark_thin_strokes` ON and judged its 30 dark reads (the
owl's 16, the Fremont patch's 14, 80 mm left_chest) against the artwork: 10
"not ink", 8 of them on the owl's plain ground and 6 of those at the design's
edge, 2 black blobs in the patch's white chevron gap. The refusal it queued:
a kept component whose own pixels are no darker than its ring, or one that
touches the design's edge.

Measured here on the engine's own raster (Lab, the space the tails read,
`tests/test_keep_dark_thin_strokes.py`), the 30 components are all 11-98 L*
darker than their ring's median with 0.75-1.0 of their pixels 8 L* under it;
the 10 "not ink" rows are the 10 components within 1 px of the frame, and the
sheet's artwork window had been clipped at the frame and stretched (fixed in
`tools.dark_ink_flip_sheet._art_crop`). So:

  * `stray_clause` refuses a component within `DARK_INK_EDGE_PX` (guard +
    ring = 4 px) of `p.art_bbox` ("edge": its one-ground test ran on part of
    a ring) or with fewer than `DARK_INK_STRAY_SHARE` (0.5, the majority
    `absorbed_dark_ink` asks for) of its pixels `DARK_INK_DEPTH_L` under the
    ring ("ground"); the 16 ink reads sit 6-170 px in;
  * OFF is byte-identical to the read as flipped (the gate is the one line);
  * on a drawn ground, ON keeps every stroke inside the frame and refuses
    the ones at it;
  * on the fixtures themselves, ON refuses the owl's edge strays and keeps
    the Fremont patch's letters (FREMONT's N, O, F) and keylines -- the count
    pins below are the engine's at 80 mm left_chest, the Studio's request.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from skimage.color import lab2rgb

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.stage1_prep import prep
from digitizer_core.thin_ink import (_DARK_INK_GUARD_PX, _RING_PX, DARK_INK_DEPTH_L, DARK_INK_EDGE_PX,
                                     DARK_INK_STRAY_SHARE, find_dark_thin_ink, stray_clause)

from .conftest import ENGINE_2026_10_27, PRE_FLIP, frozen_cfg

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
OWL = TESTDATA / "photo" / "owl_kent.jpg"
PATCH = TESTDATA / "art" / "logo_hotel_fremont_patch.png"
GROUND_LAB = (66.1, -4.1, 18.6)      # the pot of Kent's cartoon, as test_keep_dark_thin_strokes draws it
INK_LAB = (43.7, -1.0, 20.5)


def test_flag_defaults_off_and_is_frozen():
    assert PipelineConfig().dark_ink_refuse_strays is False
    assert PRE_FLIP["dark_ink_refuse_strays"] is False
    assert ENGINE_2026_10_27["dark_ink_refuse_strays"] is False
    assert frozen_cfg().dark_ink_refuse_strays is False


def test_the_clauses_on_their_own_terms():
    assert DARK_INK_EDGE_PX == _DARK_INK_GUARD_PX + _RING_PX == 4
    assert DARK_INK_STRAY_SHARE == 0.5
    art = (0, 0, 640, 640)
    dark = np.full(50, 30.0)                      # every pixel 30 L* under a ground of 60
    assert stray_clause((3, 100, 10, 10), art, dark, 60.0) == "edge"       # 3 px from the left
    assert stray_clause((100, 100, 10, 537), art, dark, 60.0) == "edge"    # 3 px from the bottom
    assert stray_clause((4, 100, 10, 10), art, dark, 60.0) is None         # 4 px in: a whole ring fits
    assert stray_clause((100, 100, 10, 536), art, dark, 60.0) is None
    half = np.r_[np.full(20, 30.0), np.full(30, 58.0)]   # 0.4 of the pixels under the ring by 8 L*
    assert stray_clause((100, 100, 10, 10), art, half, 60.0) == "ground"
    most = np.r_[np.full(30, 30.0), np.full(20, 58.0)]   # 0.6: a majority
    assert stray_clause((100, 100, 10, 10), art, most, 60.0) is None
    # exactly DARK_INK_DEPTH_L under is not "under": the black-hat's own strict test
    assert stray_clause((100, 100, 10, 10), art, np.full(50, 60.0 - DARK_INK_DEPTH_L), 60.0) == "ground"


def _barred_ground(path: Path) -> tuple[list[tuple[int, int, int, int]], list[tuple[int, int, int, int]]]:
    """A 60 x 30 mm olive ground shaded left to right (the cartoon's pot), filling
    the frame, with seven 0.6 x 5 mm dark bars in the cartoon's ink: five well
    inside, one on the left frame edge, one on the top. Returns (inside, edge)
    bars as (x, y, w, h) px at 8 px/mm."""
    w, h = 480, 240
    lab = np.empty((h, w, 3), float)
    lab[..., 0] = np.linspace(GROUND_LAB[0] + 12, GROUND_LAB[0] - 12, w)[None, :]
    lab[..., 1] = GROUND_LAB[1]
    lab[..., 2] = GROUND_LAB[2]
    inside = [(x, 100, 5, 40) for x in (100, 160, 220, 280, 340)]
    edge = [(0, 100, 5, 40), (400, 0, 5, 40)]
    for x, y, bw, bh in inside + edge:
        for ch, delta in enumerate(np.subtract(INK_LAB, GROUND_LAB)):
            lab[y:y + bh, x:x + bw, ch] += delta
    img = (lab2rgb(lab) * 255).round().astype(np.uint8)
    cv2.imwrite(str(path), img[..., ::-1])
    return inside, edge


def _components(ink) -> list[tuple[int, int, int, int]]:
    n, _cc, st, _ = cv2.connectedComponentsWithStats(ink.mask.astype(np.uint8), connectivity=8)
    return sorted(tuple(int(v) for v in st[c, :4]) for c in range(1, n))


def test_on_a_drawn_ground_on_keeps_the_strokes_inside_and_refuses_the_ones_at_the_frame(tmp_path):
    art = tmp_path / "barred_ground.png"
    inside, edge = _barred_ground(art)
    cfg = PipelineConfig(target_width_mm=60.0, max_colors=6, forced_class="gradient")
    p = prep(str(art), cfg, design_class="gradient")
    assert abs(p.px_per_mm - 8.0) < 0.01 and p.art_bbox == (0, 0, 480, 240)
    valid = ~p.bg_mask
    off = find_dark_thin_ink(p, cfg, valid)
    assert off is not None and off.components == 7, "OFF reads all seven bars"
    on = find_dark_thin_ink(p, frozen_cfg(dark_ink_refuse_strays=True), valid)
    assert on is not None and on.components == 5
    got = _components(on)
    assert len(got) == 5
    for (x, y, bw, bh), (gx, gy, gw, gh) in zip(sorted(inside), got):
        assert abs(x - gx) <= 1 and abs(y - gy) <= 1 and abs(bw - gw) <= 2 and abs(bh - gh) <= 2
    # the refused two are the ones whose ring reaches the frame
    for b in edge:
        assert stray_clause(b, p.art_bbox, np.full(10, 0.0), 60.0) == "edge"
    for b in inside:
        assert stray_clause(b, p.art_bbox, np.full(10, 0.0), 60.0) is None
    # OFF is the flag never having existed: the same seven, pixel for pixel
    again = find_dark_thin_ink(p, frozen_cfg(dark_ink_refuse_strays=False), valid)
    assert again is not None and np.array_equal(again.mask, off.mask) and again.spools == off.spools


def _studio_cfg(**kw) -> PipelineConfig:
    from digitizer_service.app import _parse_config
    from tools.fremont_triage import studio_request
    return PipelineConfig(**_parse_config(json.dumps({**studio_request(80.0), "garment_id": "left_chest"})), **kw)


def _dark(regions) -> list:
    return [r for r in regions if r.meta.get("dark_ink")]


def _edge_mm(r, half_w: float, half_h: float) -> float:
    x0, y0, x1, y1 = r.polygon.bounds
    return min(x0 + half_w, y0 + half_h, half_w - x1, half_h - y1)


def test_on_refuses_the_owls_edge_strays_and_keeps_the_patchs_letters():
    """The two heroes of #1172's sheet at the Studio's request (80 mm left_chest),
    `keep_dark_thin_strokes` riding its ON default. Counts are the engine's on
    2026-10-28 (sheet `docs/renders/dark-read-refusal-2026-10-28/`); re-pin from
    CI with `tools.ci_repin` when the engine under them moves."""
    on = run_stages(str(OWL), _studio_cfg(dark_ink_refuse_strays=True))
    assert on.design_class == "gradient"
    owl = _dark(on.regions)
    # ON (flipped, no refusal) carved 16: 10 within 1 px of the frame (the 8
    # "not ink" rows and the 2 "mixed" at the frame), 6 inside -- the feather
    # streaks and edges the sheet read as ink (rows 1, 4, 5, 6, 9, 15).
    assert len(owl) == 6, [(r.shape_id, round(r.area_mm2, 2), r.polygon.bounds) for r in owl]
    w, h = on.design_size_mm
    for r in owl:
        assert _edge_mm(r, w / 2, h / 2) >= DARK_INK_EDGE_PX / 8.0 - 0.1, (r.shape_id, r.polygon.bounds)

    on = run_stages(str(PATCH), _studio_cfg(dark_ink_refuse_strays=True))
    assert on.design_class == "gradient"
    patch = _dark(on.regions)
    # ON carved 14: the two at the bottom vertex (the chevron's lower band
    # cut by the frame, 2.2 mm2 each) are refused; the keylines, FREMONT's
    # letters, the rope and EAT | STAY | PLAY stay.
    assert len(patch) == 12, [(r.shape_id, round(r.area_mm2, 2), r.polygon.bounds) for r in patch]
    w, h = on.design_size_mm
    assert all(_edge_mm(r, w / 2, h / 2) >= DARK_INK_EDGE_PX / 8.0 - 0.1 for r in patch)

    def holds(cx: float, cy: float) -> bool:
        return any(r.polygon.bounds[0] <= cx <= r.polygon.bounds[2]
                   and r.polygon.bounds[1] <= cy <= r.polygon.bounds[3] for r in patch)

    assert holds(27.5, 0.0), "the N of FREMONT"
    assert holds(21.0, 0.0), "the O of FREMONT"
    assert holds(-2.9, 0.0), "the F of FREMONT"
    assert holds(0.0, -13.6) and holds(0.0, 13.5), "the two keyline bands"
    # the two refused blobs sat at x -4.5..-0.4 and 0.1..4.1, y 19.3..20.7; the
    # keyline band itself spans the width and reaches y 19.9
    assert not any(-6.0 < r.polygon.bounds[0] and r.polygon.bounds[2] < 6.0 and r.polygon.bounds[3] > 19.0
                   for r in patch), "nothing at the bottom vertex"


def test_the_sheets_art_window_is_padded_at_the_frame_not_stretched(tmp_path, monkeypatch):
    """`tools.dark_ink_flip_sheet._art_crop` once clipped a window past the
    artwork's edge and stretched what was left to the whole window, which is
    how 10 edge reads came to be judged against ground that was not under
    them. Now the part past the edge is mid grey and the rest is unmoved."""
    from tools import dark_ink_flip_sheet as sheet
    raw = np.zeros((100, 100, 3), np.uint8)
    raw[:, :, 2] = np.arange(100, dtype=np.uint8)[None, :] * 2     # a horizontal ramp in red
    cv2.imwrite(str(tmp_path / "ramp.png"), raw)
    monkeypatch.setattr(sheet, "TESTDATA", tmp_path)
    stats = {"art_box_frac": [0.0, 0.0, 1.0, 1.0], "design_size_mm": [10.0, 10.0]}
    tile = sheet._art_crop("ramp.png", stats, (-7.0, -5.0, 3.0, 5.0), 10.0)   # 2 mm past the left edge
    assert tile.shape == (100, 100, 3)
    assert (tile[:, :20] == 128).all(), "the part past the edge is grey"
    assert np.array_equal(tile[:, 20:], raw[:, :80]), "the part inside is the artwork, unmoved"
    assert sheet._art_crop("ramp.png", stats, (6.0, -5.0, 16.0, 5.0), 10.0) is None
