"""The reference digitizer's rule for WHAT gets a bean (triple run), measured.

`cfg.bean_only_lines` (built OFF, 2026-10-27; `tools/bean_census.py`,
docs/bean-census-reference-2026-10-27.md). Ours has no bean classifier: a
bean comes out of five size-gated fallbacks (the run tier under the area
floor, bean letters under the ink line, the silhouette edge cap, the satin
tier's hairline fallback, the detail layer), each picked by SIZE and none by
what the element IS. The census read every retraced run in 17 reference files
(one detector for both sides, ties and underlay walks excluded) and placed
each on our segmentation of the same art:

  * The reference digitizer beans almost nothing: 17 uncovered retraced runs
    in 17 files (780 mm; 8 of 1,101 regions), 16 of them TWO passes at a
    median 1.31 mm pitch, one three-pass. They lie along a LINE the art
    draws as a stroke of another colour than its surround, too thin to
    satin: a drone's panel and edge lines (627 mm of the 780), a line-drawn
    gun grip, a TM mark, short stubs.
  * He beans the edge of a filled body on 4 of 231 bodies, every one along
    a drawn outline stroke (his open fill edges are satin-bordered by size,
    or bare); small lettering on 1 of 251 letters under 1.2 mm (he raises
    it to satin); a small solid on 0 of 81 bodies under 2 mm (one satin
    blob, or dropped).
  * Ours beans 137 of the same regions: 111 letters, 24 thin regions and 2
    bodies (bean letters, the run tier, the edge cap). Region kappa with
    the reference, "carries a bean": -0.014 OFF, 0.129 ON (ours 137 -> 21).

So the rule has one positive clause and three refusals, and this module is
that decision. ON, the three sources that disagree most consult it: the run
tier (`stage7_sequence.routes_to_run` and the reactive rescue), bean letters
(`beanletters.tag_bean_letters`) and the bean-style edge cap. A LINE keeps its
bean; a LETTER and a SOLID go down the ordinary ladder (satin where
`compact_solids_satin` / `small_solids_satin` / the Column lane sew one: all
58 of Fremont's bean letters sew satin ON) and are otherwise left unsewn, as
the reference file leaves them. The edge cap's
bean style sews nothing; its satin style is untouched. Layout (ruling
2026-10-22: judged in the preview). No width, pull, density or stitch length
moves: the pass count (`machine.BEAN_PASSES`) is not touched here.
"""
from __future__ import annotations

from shapely.geometry import Polygon
from shapely.ops import polylabel

#: A stroke whose smallest dimension (twice its largest inscribed circle) is
#: no wider than this is a LINE: the reference digitizer's retraced runs lie
#: on drawn strokes of 0.47-1.7 mm (median 1.4 over the 17 segments), and his
#: satin floor for a free bar is 0.86 mm (`fine_bars_satin`). Anything wider
#: is a body he fills or satins. Geometry, not cloth: no gate 1.
LINE_MAX_MM = 1.2

LETTER = "letter"
LINE = "line"
SOLID = "solid"
EDGE = "edge"


def min_dim_mm(poly) -> float:
    """Twice the largest inscribed circle (`stage7_sequence._min_dim_mm`'s
    measure, repeated here so this module imports nothing from stage 7)."""
    if poly is None or poly.is_empty or not isinstance(poly, Polygon):
        return 0.0
    try:
        c = polylabel(poly, tolerance=0.05)
    except Exception:  # noqa: BLE001 - a degenerate ring: no circle, no line
        return 0.0
    return 2.0 * float(poly.boundary.distance(c))


def element_of(poly, *, letter: bool = False) -> str:
    """What a shape IS to the bean decision: LETTER (lettering-tagged, whatever
    its width), LINE (a stroke no wider than `LINE_MAX_MM`), else SOLID."""
    if letter:
        return LETTER
    return LINE if min_dim_mm(poly) <= LINE_MAX_MM else SOLID


def wants_bean(element: str) -> bool:
    """The measured rule: a bean only on a LINE. A letter, a solid and a
    body's bare edge never (1 of 251, 0 of 81, 0 of 231 bare edges in the
    reference files: his 4 edge runs ride drawn outline strokes)."""
    return element == LINE


def allows_bean(poly, *, letter: bool = False) -> bool:
    """`wants_bean(element_of(poly, letter))`: the one call the sources make."""
    return wants_bean(element_of(poly, letter=letter))
