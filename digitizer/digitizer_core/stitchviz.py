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

import math

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

# ---- The lit filament ---------------------------------------------------
# A stitch is a cylinder lying on cloth, not a coloured line. Two things
# follow, and this render had neither until 2026-08-25 -- Kent, looking at a
# fill sheet: *"It feels like i'm looking at an image made up of vectors and
# not stitches."* He was right, and scale was not the cause: the same design
# reads as flat hatching at 6, 8, 16 and 28 px/mm alike, because every stitch
# was shaded identically no matter which way it ran.
#
# 1. HOW MUCH light a filament catches depends on its angle to the source. A
#    row running across the light is bright; one running along it is dim.
#    Without this term a tatami field of parallel rows is one flat tone --
#    which is precisely what hatching looks like.
# 2. WHERE the highlight sits is off-centre, pushed toward the light, with the
#    far side falling into shadow. That shadow is what separates one row from
#    the next and makes the surface read as raised rather than printed.
#
# `preview.js` in the Studio implements this same model against a canvas; the
# two are kept in step deliberately, so what Kent rules on and what a customer
# sees agree. Change one, change both.
# Measured in IMAGE coordinates, where y increases DOWNWARD -- so 225 deg is
# up and to the LEFT. That is the direction thread catalogues shoot to, and
# the direction `preview.js` already lit from (shadow +1/+1.5, highlight
# -0.6/-0.9); matching it is why this is 225 and not 135. Getting this
# backwards is easy and costs nothing visually except that every render is
# lit from the opposite corner to the Studio's.
LIGHT_DEG = 225.0
_LIGHT = (math.cos(math.radians(LIGHT_DEG)), math.sin(math.radians(LIGHT_DEG)))
AMBIENT, DIFFUSE = 0.80, 0.42     # tone = AMBIENT + DIFFUSE * |axis x light|

# The three bands, as fractions of the nominal filament width: (width, offset
# toward the light). EVERY band is clamped inside the nominal width by
# `_band` below, and the widest is exactly `tw` -- so the drawn FOOTPRINT is
# unchanged by shading. That is not cosmetic: `coverage` is measured by
# rendering, so a band spilling half a pixel past the filament would inflate
# every coverage figure ever recorded, silently.
_BANDS = ((1.00, 0.00, 0.62),     # shadowed body -- defines the footprint
          (0.66, 0.14, 1.00),     # lit body
          (0.28, 0.26, 1.22))     # specular

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
                  pad_mm: float = 2.0, lit: bool = True) -> np.ndarray:
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
            _draw_filament(img, prev, p, rgb, tw, lit)
        prev = p
    return img


def _band(tw: int, w_frac: float, off_frac: float) -> tuple[int, float]:
    """One shading band's pixel width and its offset toward the light.

    The offset is CLAMPED so the band never reaches past the nominal
    filament: at small `tw` the fractions round to whole pixels that would
    otherwise poke out the side, which would widen the footprint and move
    `coverage`. Clamping costs a little contrast on tiny thread and keeps
    the measurement honest, which is the right trade.
    """
    w = max(1, int(round(w_frac * tw)))
    return w, max(0.0, min(off_frac * tw, (tw - w) / 2.0))


def _draw_filament(img: np.ndarray, a: tuple[int, int], b: tuple[int, int],
                   rgb: dict, tw: int, lit: bool = True) -> None:
    """One stitch, as a lit cylinder. Bands are painted widest first, so the
    specular lands on top of the body lands on top of the shadow.

    `lit=False` draws ONE opaque band at the full nominal width and nothing
    else. That is the filament's footprint with no shading in it, and it is
    what `coverage` measures: coverage asks how much cloth the thread hides,
    which is a question about width, not about light. Keeping the two apart
    is what lets the render be restyled without moving a recorded number --
    the first cut of this shading moved coverage by 8e-4 across the board,
    because off-centre bands push their anti-aliased fringe a fraction wider
    than centred ones do.
    """
    base = (int(rgb["b"]), int(rgb["g"]), int(rgb["r"]))
    if not lit:
        # The pre-2026-08-25 draw, kept EXACTLY: three centred bands, in this
        # order, at these widths. Not "something equivalent" -- each
        # anti-aliased pass re-blends the fringe pixels of the one before, so
        # the footprint's soft edge depends on the NUMBER of passes as well as
        # their width. Collapsing these three into one opaque band at `tw` was
        # tried and moved coverage by 1.2e-3; three bands reproduce it to the
        # last bit. Do not tidy this.
        body = tuple(int(c * 0.78) for c in base)
        core = tuple(min(255, int(c * 1.16 + 14)) for c in base)
        cv2.line(img, a, b, body, tw, cv2.LINE_AA)
        cv2.line(img, a, b, base, max(1, tw - 1), cv2.LINE_AA)
        cv2.line(img, a, b, core, max(1, tw // 3), cv2.LINE_AA)
        return

    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1.0
    ux, uy = dx / ln, dy / ln
    lx, ly = _LIGHT

    # Lambert on a cylinder: the axis-to-light cross product. |x| because a
    # filament is symmetric -- running north-east and south-west catch the
    # same light, and signing this would make sew DIRECTION visible as tone.
    tone = AMBIENT + DIFFUSE * abs(ux * ly - uy * lx)

    # Perpendicular, resolved to point AT the light.
    nx, ny = -uy, ux
    if nx * lx + ny * ly < 0:
        nx, ny = -nx, -ny

    for w_frac, off_frac, shade in _BANDS:
        w, off = _band(tw, w_frac, off_frac)
        colour = tuple(int(max(0, min(255, c * tone * shade))) for c in base)
        pa = (int(round(a[0] + nx * off)), int(round(a[1] + ny * off)))
        pb = (int(round(b[0] + nx * off)), int(round(b[1] + ny * off)))
        cv2.line(img, pa, pb, colour, w, cv2.LINE_AA)


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
                       fabric_bgr=_COVER_LO_BGR, lit=False).astype(np.int16)
    hi = render_design(design, px_per_mm=COVERAGE_PX_PER_MM,
                       fabric_bgr=_COVER_HI_BGR, lit=False).astype(np.int16)
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
