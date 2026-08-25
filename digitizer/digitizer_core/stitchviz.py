"""Render a finished design as THREAD, for the eyeball loop.

The acceptance sheet used to show `pystitch.write_svg`'s vector proof:
hairline polylines tracing where the needle went. That is the right
instrument for "did the geometry come out" and the wrong one for "will this
read as a face". Kent said so directly on 2026-08-24, looking at a sheet of
them — *"it's hard to picture how these would be turned into a digitized or
embroidered product"* — and he was right: thread has width, it overlaps, and
it catches light, so a photo reduced to twelve spools looks like a scribble
until those are drawn. The first render of that same design showed the
subject occupying a quarter of the frame with the rest given over to deck
boards, which no sheet of vector proofs had made visible in two days of
looking at them.

What this is: each stitch drawn as a round-capped stroke at real thread
width, in sew order, so later stitches cover earlier ones the way they
physically do, with a lighter core over a darker body standing in for the
sheen of a round filament.

What this is NOT, and the distance matters before anyone quotes a render as
evidence about a sew-out: no thread tension, no fabric distortion or pull,
no nap, no needle-penetration dimple, no bobbin show-through, and no push
compensation made visible. It is a picture of where the thread lands and how
much cloth it covers, which is exactly the question the vector proof could
not answer — and nothing more. Anything about how it will actually SEW still
needs the machine (ROADMAP gate 1).
"""
from __future__ import annotations

import cv2
import numpy as np

# Design coordinates are 0.1 mm with y up; `adapter.plan_to_design` is the
# one place that flip happens, and this undoes it.
UNITS_PER_MM = 10.0

# 40wt polyester, the house default weight, measured as filament diameter.
# Coverage numbers move with this, so it is a named constant rather than a
# literal: change it and every coverage figure changes meaning.
THREAD_MM = 0.4

# Enough that a 0.4 mm filament lands on 3 px and reads as thread rather than
# as a hairline. Below about 5 the sheen core rounds away to nothing.
DEFAULT_PX_PER_MM = 8.0

# A light garment. Deliberately not white: bare cloth has to be
# distinguishable from white thread, or a highlight and a hole look alike.
FABRIC_BGR = (232, 236, 238)

# Coverage is measured at a FIXED scale, never at the caller's display
# scale. Thread width rounds to whole pixels (`max(2, round(...))`), so the
# effective filament diameter — and therefore the fraction of cloth it
# covers — drifts with zoom: the same design measured 0.75 at 8 px/mm and
# 0.67 at 14 px/mm before this was pinned. At 20 px/mm a 0.4 mm filament
# lands on 8 px, where a half-pixel rounding error is under 1% of the width,
# so two runs are comparable to each other and to the figures recorded in
# the acceptance notes.
COVERAGE_PX_PER_MM = 20.0

# `coverage` renders the SAME design twice, on black and on white, and reads
# the difference. A pixel the thread fully covers comes out identical both
# times; one the thread misses entirely differs by the full 255; an
# anti-aliased edge differs in proportion to how much thread is actually on
# it. So coverage falls out as `1 - mean(difference) / 255` with no
# threshold to tune and no sentinel colour to collide with a real spool.
#
# The alternative — a sentinel background and a "is this pixel still the
# sentinel" test — was tried first and is wrong in both directions. A tight
# tolerance scored anti-aliased fringe as bare and read 99.9% on a design
# that is visibly two-thirds cloth; a loose one counts fringe as fully
# covered, and fringe is wide: a nominal 4 px filament occupies about 7 px
# once anti-aliased, so every sparse design would read roughly a third
# denser than it sews.
_COVER_LO_BGR = (0, 0, 0)
_COVER_HI_BGR = (255, 255, 255)


def _bounds(stitches: list[dict]) -> tuple[int, int, int, int] | None:
    xs = [s["x"] for s in stitches if s.get("type") in ("stitch", "jump")]
    ys = [s["y"] for s in stitches if s.get("type") in ("stitch", "jump")]
    if not xs:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def render_design(design: dict, px_per_mm: float = DEFAULT_PX_PER_MM,
                  fabric_bgr: tuple[int, int, int] = FABRIC_BGR,
                  pad_mm: float = 2.0) -> np.ndarray:
    """-> BGR image of `design` sewn on `fabric_bgr`.

    Colour changes advance through `design["colors"]` in order, which is the
    same per-block list `adapter.plan_to_design` writes, so a block that
    returns to an earlier spool renders in that spool's colour rather than
    the next one along. Jumps and trims break the thread path: they move the
    needle without laying thread, and drawing through them would paint
    travel as stitching.
    """
    stitches = design.get("stitches") or []
    colors = design.get("colors") or [{"r": 0, "g": 0, "b": 0}]
    box = _bounds(stitches)
    if box is None:
        return np.full((8, 8, 3), fabric_bgr, np.uint8)
    x0, x1, y0, y1 = box

    w = max(8, int(((x1 - x0) / UNITS_PER_MM + 2 * pad_mm) * px_per_mm))
    h = max(8, int(((y1 - y0) / UNITS_PER_MM + 2 * pad_mm) * px_per_mm))
    img = np.full((h, w, 3), fabric_bgr, np.uint8)
    tw = max(2, int(round(THREAD_MM * px_per_mm)))

    def to_px(s: dict) -> tuple[int, int]:
        px = ((s["x"] - x0) / UNITS_PER_MM + pad_mm) * px_per_mm
        py = ((y1 - s["y"]) / UNITS_PER_MM + pad_mm) * px_per_mm
        return int(round(px)), int(round(py))

    ci, prev = 0, None
    rgb = colors[0]
    for s in stitches:
        kind = s.get("type")
        if kind == "color":
            ci += 1
            if ci < len(colors):
                rgb = colors[ci]
            prev = None
            continue
        if kind in ("jump", "trim", "end"):
            prev = None
            continue
        if kind != "stitch":
            continue
        p = to_px(s)
        if prev is not None and prev != p:
            base = (int(rgb["b"]), int(rgb["g"]), int(rgb["r"]))
            body = tuple(int(c * 0.78) for c in base)
            core = tuple(min(255, int(c * 1.16 + 14)) for c in base)
            cv2.line(img, prev, p, body, tw, cv2.LINE_AA)
            cv2.line(img, prev, p, base, max(1, tw - 1), cv2.LINE_AA)
            cv2.line(img, prev, p, core, max(1, tw // 3), cv2.LINE_AA)
        prev = p
    return img


def coverage(design: dict) -> float:
    """Fraction of the design's own footprint that carries thread, 0..1.

    The number that separates the two photo routes at a glance: measured
    2026-08-24 on the acceptance portraits, the streamline thread-paint route
    covers **0.55-0.59** of its footprint while the gradient blend route
    covers **0.99**. Neither is wrong; they are different products, and the
    sheet never said so because a vector proof cannot.

    (This docstring said "0.61-0.67 of its bounding box" until 2026-08-25,
    which contradicted the very next paragraph — this function measures the
    FOOTPRINT, not a bounding box, and the two are not the same denominator.
    The footprint figure is the one every other doc quotes.)

    Why 0.55-0.59 and not something adjustable: `STREAMLINE_D_SEP_DARK_MM`
    is 0.8 mm — exactly TWO thread widths — so at full black the tightest
    line spacing that tier can draw leaves half the cloth bare BY
    CONSTRUCTION, and 0.50 is its hard analytic ceiling. The blend tier
    reaches 0.99 because `machine.FILL_ROW_MM` is 0.40 mm, exactly ONE
    thread width: rows sit edge to edge. That is the whole difference.

    Measured inside the footprint, not the padded canvas, so padding cannot
    dilute it, and always at `COVERAGE_PX_PER_MM` rather than at whatever
    scale the caller is displaying — see that constant for why. Partial
    (anti-aliased) coverage counts partially, which is the physically honest
    reading: half a filament's width over a pixel hides half its cloth.
    """
    lo = render_design(design, px_per_mm=COVERAGE_PX_PER_MM,
                       fabric_bgr=_COVER_LO_BGR).astype(np.int16)
    hi = render_design(design, px_per_mm=COVERAGE_PX_PER_MM,
                       fabric_bgr=_COVER_HI_BGR).astype(np.int16)
    show_through = np.abs(hi - lo).max(axis=2) / 255.0     # 1.0 = bare cloth
    covered = 1.0 - show_through
    ys, xs = np.where(covered > 0.01)
    if len(xs) == 0:
        return 0.0
    inner = covered[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return float(inner.mean())


def render_png_bytes(design: dict, px_per_mm: float = DEFAULT_PX_PER_MM) -> bytes:
    """`render_design` as lossless PNG. For anything that will be measured
    or diffed; the contact sheet wants `render_jpeg_bytes` instead."""
    ok, buf = cv2.imencode(".png", render_design(design, px_per_mm=px_per_mm))
    if not ok:
        raise RuntimeError("PNG encode failed")
    return buf.tobytes()


# A thread render is photo-like — thousands of small shaded strokes — which
# is the content PNG is worst at. Measured on one acceptance design at
# 8 px/mm: PNG 1,960 KB against JPEG q82's 327 KB, and a 36-cell sheet is
# the difference between 69 MB and 12 MB. The sheet is looked at, not
# measured, so the loss costs nothing that matters there.
SHEET_JPEG_QUALITY = 85


def render_jpeg_bytes(design: dict, px_per_mm: float = DEFAULT_PX_PER_MM,
                      quality: int = SHEET_JPEG_QUALITY) -> bytes:
    """`render_design` as JPEG, for embedding many cells in one page."""
    ok, buf = cv2.imencode(".jpg", render_design(design, px_per_mm=px_per_mm),
                           [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("JPEG encode failed")
    return buf.tobytes()
