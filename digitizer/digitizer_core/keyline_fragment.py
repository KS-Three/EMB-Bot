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
* all such slivers of its thread on that host together cover under
  `FRAGMENT_WRAP` of the host's outline: an outline or a drop shadow that
  follows a real share of the letter stays.

Every constant is a ratio or a snapping tolerance in the plan's own mm; no
fabric constant, so ROADMAP gate 1 does not apply. Off (`cfg.
keyline_fragment_drop` False) the module never loads.
"""
from __future__ import annotations

from .bevel_fold import BAND_MAX_MM, HUG_FRAC, _poly, _width

TOUCH_MM = 0.1            # outlines traced from one raster agree to well under this
OTHER_FRAC = 0.15         # bevel_fold.EDGE_HUG_FRAC's figure: more than this on a second shape = a line between two
HOST_AREA_RATIO = 10.0
FRAGMENT_WRAP = 0.25      # under a quarter of the host's outline, all slivers together
SKIP_KEYS = ("counter", "enclosed_background")


def _hug(band, other_buffered) -> float:
    return float(band.exterior.intersection(other_buffered).length)


def drop_keyline_fragments(regions, chart) -> list[str]:
    """Remove orphan keyline fragments from `regions` in place. -> their shape ids."""
    ok = [i for i, r in enumerate(regions) if _poly(r)]
    bands = [i for i in ok if _width(regions[i].polygon) <= BAND_MAX_MM
             and not any(regions[i].meta.get(k) for k in SKIP_KEYS)]
    if not bands:
        return []
    bodies = [i for i in ok if _width(regions[i].polygon) > BAND_MAX_MM]
    grown = {i: regions[i].polygon.buffer(TOUCH_MM) for i in bodies}
    found: dict[tuple[int, int], list[tuple[int, float]]] = {}      # (host, thread) -> [(band, hug length)]
    for b in bands:
        g = regions[b].polygon
        if g.length <= 0:
            continue
        hugs = [(h, _hug(g, grown[h])) for h in bodies
                if h != b and grown[h].intersects(g)]
        others = [(o, _hug(g, regions[o].polygon.buffer(TOUCH_MM))) for o in bands
                  if o != b and regions[o].polygon.distance(g) <= TOUCH_MM]
        if not hugs:
            continue
        host, on_host = max(hugs, key=lambda t: (t[1], -t[0]))
        elsewhere = sum(v for h, v in hugs if h != host) + sum(v for _o, v in others)
        if on_host / g.length < HUG_FRAC or elsewhere / g.length >= OTHER_FRAC:
            continue
        if regions[host].polygon.area < HOST_AREA_RATIO * g.area:
            continue
        if chart.lab[regions[b].thread_index][0] >= chart.lab[regions[host].thread_index][0]:
            continue
        found.setdefault((host, regions[b].thread_index), []).append((b, on_host))
    drop: list[int] = []
    for (host, _thread), rows in found.items():
        outline = regions[host].polygon.exterior.length
        if outline > 0 and sum(v for _b, v in rows) / outline < FRAGMENT_WRAP:
            drop.extend(b for b, _v in rows)
    ids = [regions[i].shape_id for i in sorted(drop)]
    for i in sorted(drop, reverse=True):
        del regions[i]
    return ids
