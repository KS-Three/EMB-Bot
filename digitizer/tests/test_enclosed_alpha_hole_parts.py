"""`cfg.enclosed_alpha_hole_parts` (2026-10-23): a TRANSPARENT counter cut
into several colour regions is still a counter.

The 5-10 mm lettering band against the pro (`docs/lettering-5-10mm-2026-10-23.md`):
Precision Drone's PRECISION at the pro's 62.6 mm (6.3 mm cap) sews its O as a
solid blob. The O's polygon carries its 4.1 x 3.4 mm counter; two regions of
7.1 and 4.9 mm² sit inside it, in the letter's own thread, both stitched.
Mechanism: the hole is transparent (alpha 0, stage 1's `bg_from_alpha` path),
`alpha_edge_extend` paints it with the nearest opaque colour — light from the
letter's top edge, dark from its bottom — so it vectorizes as two regions,
and `tag_enclosed_background`'s second ratio (the component mostly THIS
region) fails for each: 0.51 and 0.36 against 0.6. Fail-open sews both.

The fixture here is that letter reduced to its essentials: a ring whose top
half is light and bottom half dark, with a fully transparent middle. OFF
reproduces the defect (a region in the hole sews); ON tags every region
lying mostly inside the transparent component, with
`enclosed_colour_unknown` beside it, so they stay unstitched. The colour
path is untouched (`logo_whitebg.png`).
"""
from __future__ import annotations

import cv2
import numpy as np
from shapely.geometry import Point

from digitizer_core.pipeline import run_stages

from .conftest import SEW_WHITE_OFF, TESTDATA, cfg

N = 240
HOLE_R = 55


def two_tone_ring_with_transparent_middle() -> bytes:
    """A ring, light on top and dark below, transparent inside and out. The
    RGB UNDER the transparent middle is two-tone as well, light above and
    dark below — what `alpha_edge_extend` leaves there on the Drone file
    (nearest opaque colour), and what any exporter may flatten there."""
    rgba = np.zeros((N, N, 4), np.uint8)
    cv2.circle(rgba, (N // 2, N // 2), 100, (235, 235, 235, 255), -1)
    rgba[N // 2:, :, :3] = (40, 40, 40)
    rgba[N // 2:, :, 3] = np.where(rgba[N // 2:, :, 3] > 0, 255, 0)
    cv2.circle(rgba, (N // 2, N // 2), HOLE_R, (205, 205, 205, 0), -1)
    hole = np.zeros((N, N), np.uint8)
    cv2.circle(hole, (N // 2, N // 2), HOLE_R, 255, -1)
    low = (hole > 0) & (np.arange(N)[:, None] >= N // 2)
    rgba[low, :3] = (70, 70, 70)
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    assert ok
    return bytes(buf)


def _hole_regions(result):
    """Regions whose centroid lies inside the transparent middle (the design's
    centre, in mm): the hole's parts, whatever colour they were painted."""
    hole_mm = HOLE_R / result.px_per_mm
    return [r for r in result.regions
            if Point(0.0, 0.0).buffer(hole_mm * 0.95).contains(r.polygon.representative_point())
            and r.polygon.area < np.pi * hole_mm ** 2 * 1.2]


def test_off_reproduces_the_blob():
    """OFF is the engine as it was: the transparent middle vectorizes as more
    than one region and at least one of them is left stitched — the Drone O."""
    result = run_stages(two_tone_ring_with_transparent_middle(), cfg(target_width_mm=20.0))
    parts = _hole_regions(result)
    assert len(parts) >= 2, [r.polygon.bounds for r in parts]
    untagged = [r for r in parts if not r.meta.get("enclosed_background")]
    assert untagged, "the fixture no longer reproduces the split-hole defect"
    assert any(r.meta.get("stitched", True) for r in untagged)


def test_on_tags_every_part_of_the_transparent_hole():
    """ON: each part of the hole is enclosed background with no colour of its
    own, and none of them sews."""
    # `sew_enclosed_white` OFF (ON by default since 2026-10-24): the tags
    # are this flag's; whether a tagged hole then sews is that option's
    result = run_stages(two_tone_ring_with_transparent_middle(),
                        cfg(target_width_mm=20.0, enclosed_alpha_hole_parts=True, **SEW_WHITE_OFF))
    parts = _hole_regions(result)
    assert len(parts) >= 2, [r.polygon.bounds for r in parts]
    for r in parts:
        assert r.meta.get("enclosed_background") is True, r.polygon.bounds
        assert r.meta.get("enclosed_colour_unknown") is True
        assert r.meta.get("stitched") is False


def test_on_leaves_the_ring_itself_sewn():
    """The rule reaches only regions mostly INSIDE a transparent component:
    the ring, which merely borders the hole, keeps sewing."""
    result = run_stages(two_tone_ring_with_transparent_middle(),
                        cfg(target_width_mm=20.0, enclosed_alpha_hole_parts=True))
    hole = {r.shape_id for r in _hole_regions(result)}
    ring = [r for r in result.regions if r.shape_id not in hole]
    assert ring
    assert all(not r.meta.get("enclosed_background") for r in ring)
    assert all(r.meta.get("stitched", True) for r in ring)


def test_colour_path_is_untouched():
    """`logo_whitebg.png`'s hole is found by COLOUR: ON changes nothing there
    (the second ratio stays), and nothing reads colour-unknown."""
    off = run_stages(TESTDATA / "logo_whitebg.png", cfg())
    on = run_stages(TESTDATA / "logo_whitebg.png", cfg(enclosed_alpha_hole_parts=True))
    key = lambda res: sorted((r.shape_id, bool(r.meta.get("enclosed_background")),
                              bool(r.meta.get("enclosed_colour_unknown"))) for r in res.regions)
    assert key(on) == key(off)
    assert not any(r.meta.get("enclosed_colour_unknown") for r in on.regions)
