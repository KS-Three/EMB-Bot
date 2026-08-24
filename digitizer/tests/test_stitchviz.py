"""Stage-agnostic — `digitizer_core.stitchviz`, the thread render.

Why it exists: the acceptance sheet showed `pystitch.write_svg`'s vector
proof, and Kent, looking at a sheet of them on 2026-08-24, said it was hard
to picture how any of it became an embroidered product. He was right. A
hairline polyline cannot show whether twelve spools read as a face, because
thread has width, overlaps, and covers cloth. These pin the geometry of the
render and the one number it produces.
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core.stitchviz import (
    COVERAGE_PX_PER_MM,
    FABRIC_BGR,
    THREAD_MM,
    UNITS_PER_MM,
    coverage,
    render_design,
    render_png_bytes,
)


def _design(stitches, colors=None):
    return {"stitches": stitches, "colors": colors or [{"r": 10, "g": 20, "b": 200}]}


def _run(x0, y0, x1, y1, n=40):
    """A straight run of `n` stitches, in 0.1 mm design units (y up)."""
    return [{"x": int(x0 + (x1 - x0) * i / (n - 1)),
             "y": int(y0 + (y1 - y0) * i / (n - 1)),
             "type": "stitch"} for i in range(n)]


def test_an_empty_design_renders_bare_cloth_rather_than_raising():
    """A plan that emitted nothing is a real outcome (stage 7's never-drop
    ladder can still hand back an empty design), and the sheet has to draw
    a cell for it."""
    img = render_design(_design([]))
    assert img.ndim == 3 and img.shape[2] == 3
    assert np.all(img.reshape(-1, 3) == np.array(FABRIC_BGR))


def test_the_render_is_scaled_and_oriented_like_the_design():
    """Design units are 0.1 mm with y UP; the image is pixels with y DOWN.
    A run that climbs in design space must descend in the image, or every
    render is vertically mirrored and nobody notices until a sew-out."""
    d = _design(_run(0, 0, 0, 200))          # 20 mm straight up
    px_per_mm, pad = 10.0, 2.0
    img = render_design(d, px_per_mm=px_per_mm, pad_mm=pad)

    # 20 mm of travel plus 2 mm padding each side, at 10 px/mm.
    assert img.shape[0] == int((200 / UNITS_PER_MM + 2 * pad) * px_per_mm)
    ys = np.where(np.any(np.any(img != np.array(FABRIC_BGR), axis=2), axis=1))[0]
    # Thread occupies the middle band, not the padding — allowing for the
    # round cap, which deliberately extends half a filament past the last
    # stitch because that is what the end of a stitch looks like.
    cap = THREAD_MM * px_per_mm / 2.0 + 1.0
    assert ys.min() >= pad * px_per_mm - cap
    assert ys.max() <= img.shape[0] - pad * px_per_mm + cap


def test_thread_is_drawn_at_its_real_width():
    """The whole point of the render: a filament, not a hairline.

    The measured footprint is WIDER than the nominal filament and that is
    not a bug — anti-aliasing puts a partial fringe either side, so a
    nominal 4 px thread touches about 7 px. The fringe is why `coverage`
    reads the difference between two backgrounds instead of counting
    non-fabric pixels: counted flat, that fringe would inflate every sparse
    design by roughly a third.
    """
    d = _design(_run(0, 0, 0, 200))
    img = render_design(d, px_per_mm=10.0)
    mid = img[img.shape[0] // 2]
    nominal = THREAD_MM * 10.0
    touched = np.where(np.any(mid != np.array(FABRIC_BGR), axis=1))[0]
    assert nominal <= len(touched) <= nominal + 4, "fringe should be a fringe"

    # The SOLID part — pixels more thread than cloth — stays near nominal.
    dist = np.linalg.norm(mid.astype(int) - np.array(FABRIC_BGR), axis=1)
    solid = np.where(dist > dist.max() / 2.0)[0]
    assert len(solid) == pytest.approx(nominal, abs=2.0)


def test_jumps_and_trims_lay_no_thread():
    """Travel moves the needle without stitching. Drawing through a jump
    would paint travel as coverage — the exact error that would make a
    sparse design look solid."""
    walk = (_run(0, 0, 0, 100, n=20)
            + [{"x": 0, "y": 100, "type": "trim"},
               {"x": 900, "y": 100, "type": "jump"}]
            + _run(900, 100, 900, 200, n=20))
    img = render_design(_design(walk), px_per_mm=10.0)
    # The horizontal gap the jump crossed must be bare.
    row = img[img.shape[0] // 2]
    bare = np.all(row == np.array(FABRIC_BGR), axis=1)
    assert bare.sum() > 0.5 * len(row), "the jump was drawn as thread"


def test_a_colour_change_advances_through_the_block_colour_list():
    """`adapter.plan_to_design` writes one colour PER BLOCK, so a design
    that returns to an earlier spool has that spool listed again. Rendering
    must walk the list rather than dedupe it, or a thread return paints in
    the wrong colour."""
    red, blue = {"r": 220, "g": 0, "b": 0}, {"r": 0, "g": 0, "b": 220}
    stitches = (_run(0, 0, 200, 0, n=20)
                + [{"x": 200, "y": 0, "type": "color"}]
                + _run(200, 0, 400, 0, n=20))
    img = render_design(_design(stitches, [red, blue]), px_per_mm=10.0)
    h, w = img.shape[:2]
    left, right = img[h // 2, : w // 3], img[h // 2, 2 * w // 3:]
    # BGR: the first half leans red, the second blue.
    assert left[:, 2].max() > left[:, 0].max()
    assert right[:, 0].max() > right[:, 2].max()


def test_coverage_is_zero_for_an_empty_design_and_high_for_a_solid_block():
    """The number's two ends. A filled square is nearly all thread; nothing
    sewn is none."""
    assert coverage(_design([])) == 0.0
    rows = []
    for i in range(60):                      # 6 mm of rows, 0.1 mm apart
        y = i * 1
        rows += _run(0, y, 600, y, n=30)
        rows += [{"x": 600, "y": y, "type": "jump"}]
    assert coverage(_design(rows)) > 0.9


def test_coverage_does_not_move_with_the_display_scale():
    """It is a MEASUREMENT, so it cannot depend on zoom. Thread width rounds
    to whole pixels, and before this was pinned the same design read 0.75 at
    8 px/mm and 0.67 at 14 — a number that drifts with how you look at it is
    not evidence. `coverage` takes no scale argument for exactly this
    reason; this test pins that it stays that way."""
    import inspect
    assert "px_per_mm" not in inspect.signature(coverage).parameters
    assert COVERAGE_PX_PER_MM >= 20.0, (
        "below ~20 px/mm the half-pixel rounding on a 0.4 mm filament is a "
        "few percent of its width, which lands straight in the number")


def test_png_bytes_are_a_real_png():
    """The sheet embeds these base64; a silent encode failure would render
    every cell as a broken image."""
    b = render_png_bytes(_design(_run(0, 0, 200, 200)))
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
