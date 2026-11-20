"""Orphan keyline fragments: a dark sliver left on one edge of a lighter shape.

Kent, 2026-11-17, on the Drone render: "The P,R & C should not have the dark
stitch lines on them". The chrome letters of PRECISION carry a hairline dark
edge in the art. Stage 2 keeps most of it inside the letter, but a few
millimetres survive as their own dark regions hugging the bottom of the P
(twice), the R's leg and the C's foot, and each sews as a short dark satin
bar on a light letter. A keyline that goes all the way round is drawn art; a
piece of one on a tenth of the outline is a tracing remnant.

`drop_keyline_fragments` removes a region (it becomes page) when ALL hold:

* it is a band: mean width 2A/P at most `bevel_fold.BAND_MAX_MM` (two laid
  threads, the same definition the bevel fold uses; no new width);
* it lies along ONE host: at least `HUG_FRAC` of its outline is on a shape
  that is not itself a band and has at least `HOST_AREA_RATIO` times its
  area, and under `OTHER_FRAC` of its outline is on any other shape (a line
  BETWEEN two shapes is drawn art and stays);
* it is darker than its host (CIELAB L of the two threads): a light sliver
  on a dark shape is a highlight or a gap, and is not this rule's business;
* it lies on the host's OUTER outline, not in a hole of it (2026-11-17: a thin
  dark band inside a white fill is a drawn line, To a T's speed lines, and
  its whole outline hugs the host's hole rings);
* it is not the design's darkest ink in its own art ink (`bevel_fold`'s
  rule: Golden Tee's tee shadow and outline are drawn; a rescued or
  cap-merged piece is not protected, as there), and it is darker than its
  host by more than `bevel_fold.DARKEST_L_TOL` L* (two near-equal inks the
  palette kept apart are one colour, not a keyline);
* it is a HAIRLINE in the art: no more than `HAIRLINE_SRC_PX` source pixels
  wide (measured on the art: the Drone's remnants are 1.3 to 1.9 source
  pixels, Golden Tee's black bar under the F's arm is 15; a keyline thicker
  than that is a drawn band). Skipped when the caller gives no scale;
* all such slivers of its thread on that host together cover under
  `FRAGMENT_WRAP` of the host's outline: an outline or a drop shadow that
  follows a real share of the letter stays.

Every constant is a ratio or a snapping tolerance in the plan's own mm; no
fabric constant, so ROADMAP gate 1 does not apply. Off (`cfg.
keyline_fragment_drop` False) the module never loads.
"""
from __future__ import annotations

from shapely.geometry import LinearRing

from .bevel_fold import (BAND_MAX_MM, DARK_L_MAX, DARKEST_L_TOL, HUG_FRAC, _poly, _width)

TOUCH_MM = 0.1            # outlines traced from one raster agree to well under this
OTHER_FRAC = 0.15         # bevel_fold.EDGE_HUG_FRAC's figure: more than this on a second shape = a line between two
HOST_AREA_RATIO = 10.0
HAIRLINE_SRC_PX = 3.0     # between the Drone's remnants (<= 1.9 px) and a drawn band (Golden Tee's, 15 px)
FRAGMENT_WRAP = 0.25      # under a quarter of the host's outline, all slivers together
SKIP_KEYS = ("counter", "enclosed_background")


def _hug(band, other_buffered) -> float:
    return float(band.exterior.intersection(other_buffered).length)


def drop_keyline_fragments(regions, chart, mm_per_src_px: float | None = None,
                           subpixel_darkest: bool = False) -> list[str]:
    """Remove orphan keyline fragments from `regions` in place. -> their shape ids."""
    ok = [i for i, r in enumerate(regions) if _poly(r)]
    bands = [i for i in ok if _width(regions[i].polygon) <= BAND_MAX_MM
             and not any(regions[i].meta.get(k) for k in SKIP_KEYS)]
    if not bands:
        return []
    bodies = [i for i in ok if _width(regions[i].polygon) > BAND_MAX_MM]
    darkest = min(float(chart.lab[regions[i].thread_index][0]) for i in ok)
    dark_cut = min(darkest + DARKEST_L_TOL, DARK_L_MAX)
    grown = {i: regions[i].polygon.buffer(TOUCH_MM) for i in bodies}

    fringe: list[int] = []

    def subpx(g) -> bool:
        """`cfg.extra["keyline_fragment_subpixel"]`: thinner than the art can draw."""
        from .sliver_prune import SLIVER_WIDTH_SRC_PX
        return bool(subpixel_darkest and mm_per_src_px
                    and _width(g) <= SLIVER_WIDTH_SRC_PX * mm_per_src_px)

    found: dict[tuple[int, int], list[tuple[int, float]]] = {}      # (host, thread) -> [(band, hug length)]
    for b in bands:
        g = regions[b].polygon
        if g.length <= 0:
            continue
        hugs = [(h, _hug(g, grown[h])) for h in bodies
                if h != b and grown[h].intersects(g)]
        others = [(o, _hug(g, regions[o].polygon.buffer(TOUCH_MM))) for o in bands
                  if o != b and regions[o].polygon.distance(g) <= TOUCH_MM]
        if subpx(g):
            # `keyline_fragment_subpixel`: the fringe of a line may lie on
            # another, wider BAND (the National Guard's white rim is 0.29 mm
            # in the art): any wider shape of another thread can host it
            wider = [(o, v) for o, v in others
                     if regions[o].thread_index != regions[b].thread_index
                     and _width(regions[o].polygon) > _width(g)]
            hugs = hugs + wider
            others = [t for t in others if t not in wider]
        if not hugs:
            continue
        host, on_host = max(hugs, key=lambda t: (t[1], -t[0]))
        elsewhere = sum(v for h, v in hugs if h != host) + sum(v for _o, v in others)
        if on_host / g.length < HUG_FRAC or elsewhere / g.length >= OTHER_FRAC:
            continue
        if regions[host].polygon.area < HOST_AREA_RATIO * g.area:
            continue
        if mm_per_src_px and _width(g) > HAIRLINE_SRC_PX * mm_per_src_px:
            continue                       # wider than a hairline in the art: a drawn band
        lb = float(chart.lab[regions[b].thread_index][0])
        if lb > chart.lab[regions[host].thread_index][0] - DARKEST_L_TOL:
            continue
        m = regions[b].meta
        if lb <= dark_cut and not m.get("color_cap_merged_from") and not m.get("rescued_small_shape"):
            # the design's own darkest ink: drawn. Unless
            # `cfg.extra["keyline_fragment_subpixel"]` (built OFF 2026-11-19)
            # and the band is thinner than the art can DRAW
            # (`sliver_prune.SLIVER_WIDTH_SRC_PX`, 1.5 source pixels, the line
            # the hairline-outline mark already holds): that is the raster's
            # fringe of a keyline, whatever its ink. The National Guard seal
            # at 90 mm: a hairline black keyline round the white rim traced as
            # seven fragments 0.05-0.09 mm wide (0.5-1.0 source px); the two
            # rescued ones went, the other five, in the design's black, each
            # sewed a 1.5 mm satin dash on the rim.
            if not subpx(g):
                continue
        hole_rings = [LinearRing(h.coords).buffer(TOUCH_MM) for h in regions[host].polygon.interiors]
        in_holes = sum(float(g.exterior.intersection(r).length) for r in hole_rings)
        if in_holes > on_host - in_holes:
            continue                       # a band in a hole of the host: drawn
        if subpx(g):
            # no wrap test: a line thinner than the art can draw is fringe
            # however much of the outline its pieces follow (the National
            # Guard's seven cover about half the rim)
            fringe.append(b)
            continue
        found.setdefault((host, regions[b].thread_index), []).append((b, on_host))
    drop: list[int] = list(fringe)
    for (host, _thread), rows in found.items():
        outline = regions[host].polygon.exterior.length
        if outline > 0 and sum(v for _b, v in rows) / outline < FRAGMENT_WRAP:
            drop.extend(b for b, _v in rows)
    ids = [regions[i].shape_id for i in sorted(drop)]
    for i in sorted(drop, reverse=True):
        del regions[i]
    return ids
