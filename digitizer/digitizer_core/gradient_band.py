"""A gradient band is not a ribbon.

Kent, 2026-09-09, on the Instagram icon: *"any idea what the yellow/golden
stitching looks different than everything else?"* It was one shape — a
37 mm², ~2 mm wide crescent the quantizer had cut out of the gradient's
orange→yellow run (Brother 209 Tangerine, the last slice before the white
ring cuts the gradient off). The satin classifier read it as a ribbon
(`promoted_ribbon`) and sewed it as one satin column: 41 crosses across its
width in a field of diagonal tatami, both tapered tips unsewn. His ruling:
**a gradient band is not a ribbon** — refuse the satin verdict and sew it as
fill like the fills around it.

What makes a band a band is not its shape — a thin band and a thin stroke are
the same polygon — and it is not its neighbours' colours either (the first
version of this rule asked whether the band's thread lay between its two
neighbours' threads, and the icon's own band failed it: its second neighbour
is the WHITE ring, not the next gradient colour). It is what the ARTWORK does
at its edge: a stroke's outline is an edge in the picture, a colour step; a
band's outline is a line the quantizer drew through a smooth gradient, and the
pixels either side of it are almost the same colour. So the test reads the
prepared source image along each ribbon-shaped region's boundary — a probe a
few tenths of a millimetre inside and one the same distance outside — and
calls the region a band when most of that boundary is SOFT.

The gradient lane already has this idea — `stage6_blend.region_rides_design_ramp`
("a shape that RIDES the design's ramp is part of the sweep") — but it needs
`source_pixels`, which a design forced flat does not carry. This is the flat
lane's version, run in `pipeline.finish_generation` where the prepared image
is still in hand.

The verdict sites (`stage5_overlap._comp_axis`, `stage7_sequence._sews_satin`
and `stitch_one`) all read a shape's `tier` first; a tagged shape on `auto`
reads as fill there, and an explicit review-screen `satin` still wins — the
user has answered the question. Every ribbon-shaped candidate keeps its
measured soft share in `meta["gradient_band_soft"]`, tagged or not, so
`tools/gradient_bands.py` can show the whole population against the line.

Constants below are a starting position off ONE design (the icon) plus the
fixtures in `tests/test_gradient_band.py`; the survey says what they catch.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Point
from shapely.strtree import STRtree

from .stage6_satin import ribbon_width_mm
from .threads import rgb_to_lab

# Fraction of a region's boundary that must be soft for it to be a band.
# ONE gradient side is enough — the icon's Tangerine crescent has the gradient
# on one long side and the white ring on the other — and one long side of a
# ribbon is L / (2L + 2w) of its boundary: 0.375 at the aspect floor of 3,
# 0.47 on that crescent (measured, 118 samples), tending to 0.5. A stroke
# reads near zero. So the line sits under the one-sided band and well above
# the stroke, not at the 0.5 a two-sided band would suggest — that missed
# the very shape the rule was written for.
BAND_SOFT_MIN = 0.35
# A boundary sample is soft when the source colours a probe's distance
# either side of it differ by less than this (CIELAB Euclidean). Measured on
# the icon at 62.5 px/mm: a quantizer's cut through the gradient reads
# 1.2–5.3 (p10–p90 across four shapes), an edge against the white ring reads
# 73–84. The gap is thirteen-fold; 12 sits in it with room for a lower-
# resolution source whose probe lands inside the anti-aliasing ramp.
BAND_SOFT_DE = 12.0
# How far either side of the boundary the probes sit, in mm — past any
# anti-aliasing ramp at web resolutions, well inside a 1.3 mm band — but
# never under `_PROBE_MIN_PX` SOURCE pixels (`Prep.input_px_per_mm`, the
# resolution the input delivered, not the one stage 1's Lanczos upscale
# manufactured): below that both probes sit in one source pixel's ramp and
# every edge is "soft". Measured before the floor existed: Gaulke's 0.06 mm
# hairlines (probe 0.02 mm) read 0.7–1.0. A region whose third-width cannot
# hold the floored probe is unjudgeable at that resolution and is left
# alone — Becker (1.5 px/mm) is entirely so at 80 mm, which is right: at
# that resolution nothing can tell a cut from an edge.
BAND_PROBE_MM = 0.4
# The patch is one pixel either side of the probe and the anti-aliasing ramp
# is about a source pixel wide, so the probe centre sits 2.5 px out to keep
# the patch clear of the ramp.
_PROBE_MIN_PX = 2.5
# A second, FAR probe this much further out into the neighbour. A bevel is a
# narrow transition between two flat colours — soft at 0.4 mm, hard once the
# probe is past it — where a gradient keeps drifting and is soft at both.
# Found on the drone badge: the P, R and N faces of its extruded lettering
# each have a bevelled shadow along one edge and read soft 0.41–0.47 at the
# near probe alone, exactly a one-sided band's share, and were demoted.
BAND_FAR_MM = 1.2
# The far probe's tolerance is looser than the near one's because a gradient
# genuinely drifts over 1.6 mm (the icon's runs ~2.4 Lab units per mm); a
# bevel's step is the face-to-shadow contrast, tens of units.
BAND_SOFT_DE_FAR = 20.0
# Boundary sampling pitch.
BAND_SAMPLE_MM = 0.5
# Same first two gates the classifier applies (`classify_ribbon`): only a
# ribbon-shaped region can be sewn as satin, so only one can be a band.
_ASPECT_MIN = 3.0
_MIN_SAMPLES = 8
# Each probe averages a small patch so one JPEG artefact cannot vote.
_PATCH_PX = 1


def is_gradient_band(region) -> bool:
    """The predicate the verdict sites read: tagged, and not overridden."""
    return bool(region.meta.get("gradient_band"))


def _patch_lab(rgb: np.ndarray, x: float, y: float) -> np.ndarray | None:
    h, w = rgb.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    if xi < _PATCH_PX or yi < _PATCH_PX or xi >= w - _PATCH_PX or yi >= h - _PATCH_PX:
        return None
    patch = rgb[yi - _PATCH_PX:yi + _PATCH_PX + 1, xi - _PATCH_PX:xi + _PATCH_PX + 1]
    return rgb_to_lab(patch.reshape(-1, 3).mean(axis=0, keepdims=True))[0]


def _in_background(bg_mask: np.ndarray | None, x: float, y: float) -> bool:
    if bg_mask is None:
        return False
    h, w = bg_mask.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    return 0 <= xi < w and 0 <= yi < h and bool(bg_mask[yi, xi])


def soft_share(poly, rgb: np.ndarray, cx: float, cy: float, px_per_mm: float,
               *, probe_mm: float, bg_mask: np.ndarray | None = None,
               across=None) -> tuple[float, int, dict]:
    """-> (fraction of the boundary that is soft, samples judged, and — when
    `across` is a `(STRtree, [region])` pair over the other shapes — how many
    soft samples face each neighbour, keyed by shape id).

    Walks every ring of `poly` at `BAND_SAMPLE_MM`; at each sample takes the
    tangent over the neighbouring samples, probes `probe_mm` inside and
    outside along the normal (inside decided by asking the polygon, never by
    trusting ring winding), and compares the two source colours in Lab — and
    again against a FAR probe `BAND_FAR_MM` further out, so a bevel (soft
    near, flat beyond) is not mistaken for a gradient (soft at both).
    Samples whose probes leave the image are not judged.

    A probe that lands in `bg_mask` is HARD whatever the colours say: the
    artwork ends there, which is an edge by definition. This is not a
    nicety — an alpha-cutout PNG carries whatever RGB the exporter left
    under its transparency, and on Becker that is the letters' own dark, so
    by colour alone every letter edge read soft 1.00 and five letters would
    have been demoted to fill.
    """
    rings = [poly.exterior, *poly.interiors]
    soft = judged = 0
    owners: dict[str, int] = {}
    tree, others = across if across is not None else (None, None)
    for ring in rings:
        n = max(_MIN_SAMPLES, int(ring.length / BAND_SAMPLE_MM))
        pts = [ring.interpolate(ring.length * k / n) for k in range(n)]
        for k in range(n):
            a, b = pts[(k - 1) % n], pts[(k + 1) % n]
            tx, ty = b.x - a.x, b.y - a.y
            d = math.hypot(tx, ty)
            if d < 1e-9:
                continue
            nx, ny = -ty / d, tx / d
            s = pts[k]
            if not poly.contains(Point(s.x + nx * 1e-3, s.y + ny * 1e-3)):
                nx, ny = -nx, -ny          # make (nx, ny) point INTO the shape
            far_mm = probe_mm + BAND_FAR_MM
            ins = (s.x + nx * probe_mm, s.y + ny * probe_mm)
            out = (s.x - nx * probe_mm, s.y - ny * probe_mm)
            far = (s.x - nx * far_mm, s.y - ny * far_mm)
            ipx = (ins[0] * px_per_mm + cx, ins[1] * px_per_mm + cy)
            opx = (out[0] * px_per_mm + cx, out[1] * px_per_mm + cy)
            fpx = (far[0] * px_per_mm + cx, far[1] * px_per_mm + cy)
            li = _patch_lab(rgb, *ipx)
            lo = _patch_lab(rgb, *opx)
            lf = _patch_lab(rgb, *fpx)
            if li is None or lo is None or lf is None:
                continue
            judged += 1
            if (_in_background(bg_mask, *opx) or _in_background(bg_mask, *ipx)
                    or _in_background(bg_mask, *fpx)):
                continue               # the artwork ends here: hard
            if (float(np.linalg.norm(li - lo)) < BAND_SOFT_DE
                    and float(np.linalg.norm(li - lf)) < BAND_SOFT_DE_FAR):
                soft += 1
                if tree is not None:
                    op = Point(out)
                    for j in tree.query(op):
                        if others[int(j)].polygon.covers(op):
                            sid = others[int(j)].shape_id
                            owners[sid] = owners.get(sid, 0) + 1
                            break
    return (soft / judged if judged else 0.0), judged, owners


def mark_gradient_bands(regions, rgb: np.ndarray, bg_mask: np.ndarray | None,
                        cx: float, cy: float, px_per_mm: float, *,
                        satin_max_mm: float,
                        source_px_per_mm: float | None = None) -> list[str]:
    """Tag `meta["gradient_band"] = True` on every stitched region that is a
    ribbon by shape and a band by its edges; record `meta["gradient_band_soft"]`
    on every ribbon-shaped candidate. Clears both on every region first, so a
    re-run on an edited region list never leaves a stale tag behind.
    -> the ids tagged, in region order.

    `rgb` and `bg_mask` are stage 1's prepared image and background;
    `cx, cy, px_per_mm` are stage 4's pixel↔mm transform
    (`px = mm * px_per_mm + c`). `source_px_per_mm` is the resolution the
    INPUT delivered (`Prep.input_px_per_mm`) — the probe floor is counted in
    those pixels, because stage 1's Lanczos upscale manufactures pixels
    without narrowing the anti-aliasing ramp they carry.
    """
    for r in regions:
        r.meta.pop("gradient_band", None)
        r.meta.pop("gradient_band_of", None)
        r.meta.pop("gradient_band_soft", None)
    stitched = [r for r in regions if r.meta.get("stitched", True)]
    by_id = {r.shape_id: r for r in stitched}
    tree = STRtree([r.polygon for r in stitched]) if stitched else None
    src_ppm = source_px_per_mm if source_px_per_mm else px_per_mm
    probe = max(BAND_PROBE_MM, _PROBE_MIN_PX / src_ppm)
    tagged: list[str] = []
    for r in stitched:
        poly = r.polygon
        w = ribbon_width_mm(poly)
        if w <= 0 or w > satin_max_mm:
            continue
        if poly.length / 2.0 - w < _ASPECT_MIN * w:
            continue
        if probe > w / 3.0:
            continue           # too narrow to judge at this resolution
        share, judged, owners = soft_share(poly, rgb, cx, cy, px_per_mm,
                                           probe_mm=probe, bg_mask=bg_mask,
                                           across=(tree, stitched))
        if judged < _MIN_SAMPLES:
            continue
        r.meta["gradient_band_soft"] = round(share, 3)
        if share < BAND_SOFT_MIN:
            continue
        owners.pop(r.shape_id, None)
        if not owners:
            continue           # soft against nothing sewn: no sweep to belong to
        # The neighbour across the most soft edge is the region this band was
        # cut from. It has to be a FILL — a slice of a sweep sits beside the
        # sweep — so a ribbon by the classifier's own two shape gates does
        # not qualify: a bevelled letter face beside its own extruded shadow
        # is soft at both probes (the drone badge's R and N, 0.39–0.40) and
        # that shadow is another ribbon, not a field. Stage 7 sews the band's
        # rows at the parent's angle (`stage7_sequence._fill_angle_deg`), so
        # the band disappears into the field instead of reading as its own
        # texture.
        parent_id = max(owners, key=lambda k: (owners[k], k))
        parent = by_id.get(parent_id)
        if parent is None:
            continue
        pw = ribbon_width_mm(parent.polygon)
        if 0 < pw <= satin_max_mm and parent.polygon.length / 2.0 - pw >= _ASPECT_MIN * pw:
            continue           # the neighbour is a stroke too: a bevel, not a sweep
        r.meta["gradient_band"] = True
        r.meta["gradient_band_of"] = parent_id
        tagged.append(r.shape_id)
    return tagged
