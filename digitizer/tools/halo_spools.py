#!/usr/bin/env python
"""Compression-halo spools: cones a design spends on JPEG ringing, not on art.

The instrument behind the Bridge Bar finding in
`docs/kent-review-2026-09-03.md` -- "13 thread colours on a four-colour logo
... blocks 6-12 together: 3,131 stitches (29%), 53 trims (50%), 7 of the 13
colour changes on artefacts". That number was read off one hand-inspected
plan; this is the re-runnable version, so a fix can be measured instead of
eyeballed, and so the same test can be pointed at flat art to show it finds
nothing there.

A JPEG saved at a hard colour boundary rings: the encoder cannot hold the
step, so it lays a band of intermediate pixels either side of it. That band
is a genuinely distinct colour population, so stage 2 keeps it, the palette
buys it a cone, and stage 4 shatters it into hairline slivers that each sew
as a run with a trim. Three properties separate such a band from a thin
feature the designer drew:

  1. **Thin.** Mean band width -- `2 * area / perimeter` -- is a fraction of
     a millimetre, well under the satin floor and the detail floor.
  2. **Between two things.** It borders at least two regions that are each
     much larger than it, across a boundary of real colour contrast. Ringing
     only forms at a step; there is no halo in the middle of a flat field.
  3. **An interpolation of them.** Its colour sits ON the Lab segment
     between those two neighbours -- that is what "the encoder could not
     hold the step" produces. A designer's keyline is a CHOSEN colour and
     lands off that segment (gold on black-and-white is not grey).

Property 3 is the one doing the discriminating. Dropping it flags every thin
feature in the corpus; keeping it is what makes the test safe to act on.

    .venv/bin/python tools/halo_spools.py [fixture ...] [--mm 80] [--colors 6]
    .venv/bin/python tools/halo_spools.py bridge --detail

Fixtures are paths under `testdata/` or the short names below. `--detail`
lists every candidate region. Nothing here changes stitches: it reads a plan.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.threads import chart_for  # noqa: E402

try:
    from skimage.color import deltaE_ciede2000
except ImportError:  # pragma: no cover - the digitizer already depends on it
    raise

# --- the test's four numbers, all geometric or colorimetric ------------------
# None of these is a physical constant (ROADMAP gate 1): they describe the
# artwork's own raster, not how thread behaves on cloth.

# A band this thin cannot be a sewable feature: `machine.SATIN_MIN_WIDTH_MM`
# is 0.5 and `cfg.min_detail_mm` is 1.5. Set at 0.5 so the test can never
# claim something the satin tier would have been willing to sew as a column.
HALO_MAX_WIDTH_MM = 0.5
# "Much larger than it": a neighbour has to outweigh the candidate this many
# times before it counts as one of the two sides of the step. Keeps two
# adjacent halo slivers from vouching for each other.
NEIGHBOUR_AREA_RATIO = 4.0
# A step worth ringing. dE00 20 is roughly mid-grey against white.
HALO_MIN_CONTRAST_DE = 20.0
# How far off the n1->n2 Lab segment a colour may sit and still read as an
# interpolation of the two rather than a colour of its own.
HALO_MAX_OFFSET_DE = 10.0
# Where on that segment it has to land. A halo is a blend of both sides; a
# value at either end is just one of the neighbours' own colour.
HALO_T_RANGE = (0.10, 0.90)
# Regions closer than this share a boundary. Stage 5 pulls neighbours apart
# by the compensation tongue, so touching polygons do not stay touching.
NEIGHBOUR_GAP_MM = 0.6
# How much of a region's outline has to face nothing at all before the
# removed background counts as one side of its step. The commonest halo in
# the corpus is the one around black artwork on a white page, and the white
# is not a region -- stage 1 took it out -- so without this the test can
# only see the minority of halos that happen to lie between two sewn shapes.
FREE_BOUNDARY_FRAC = 0.25

SHORT = {
    "bridge": "photo/logo_bridge_bar.jpg",
    "fremont": "photo/logo_hotel_fremont.webp",
    "becker": "becker_marine_logo.png",
    "goldentee": "photo/logo_golden_tee.jpg",
    "enthusiast": "photo/enthusiast_logo.png",
    "drone": "photo/drone_render.png",
    "whitebg": "logo_whitebg.png",
    "gaulke": "photo/logo_gaulke_roofing.png",
    "golke": "photo/screenshot_phone_ui_golke.jpg",
    "summit": "photo/summit_badge.png",
    "tires": "logo_script_tires.png",
}


@dataclass
class Candidate:
    """One region the halo test flagged, with the reading that flagged it."""

    shape_id: str
    thread_number: str
    area_mm2: float
    width_mm: float
    n1: str
    n2: str
    contrast_de: float
    t: float
    offset_de: float


@dataclass
class Reading:
    """What one design spends on halos."""

    regions: int = 0
    halo_regions: int = 0
    halo_area_mm2: float = 0.0
    art_area_mm2: float = 0.0
    stitches: int = 0
    trims: int = 0
    blocks: int = 0
    halo_stitches: int = 0
    halo_trims: int = 0
    halo_blocks: int = 0
    halo_threads: list[str] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)


def _width_mm(poly) -> float:
    """Mean band width: twice the area over the perimeter.

    For a long thin band of width w and length L this is 2wL / (2L + 2w) ~= w,
    which is what we want to read; for a disc of radius r it is r. It needs no
    raster and no distance transform, so it works on any Region.
    """
    per = poly.length
    return (2.0 * poly.area / per) if per > 0 else 0.0


def _neighbours(regions, gap_mm: float = NEIGHBOUR_GAP_MM) -> dict[int, list[int]]:
    """-> index -> indices of regions within `gap_mm`, via an STRtree."""
    from shapely.strtree import STRtree

    polys = [r.polygon for r in regions]
    tree = STRtree(polys)
    out: dict[int, list[int]] = {}
    for i, poly in enumerate(polys):
        near = tree.query(poly.buffer(gap_mm))
        out[i] = [int(j) for j in near
                  if int(j) != i and polys[int(j)].distance(poly) <= gap_mm]
    return out


def _lab(chart, idx: int) -> np.ndarray:
    return np.asarray(chart.lab[idx], dtype=np.float64)


def _de(a: np.ndarray, b: np.ndarray) -> float:
    return float(deltaE_ciede2000(a.reshape(1, 3), b.reshape(1, 3))[0])


def background_lab(image_path) -> np.ndarray:
    """The page colour, from the source raster's own border ring.

    The same pixels stage 1's flood fill starts from, read the same way it
    would: a median, so a logo touching one edge of its canvas cannot move
    the answer. Returned in Lab, to compare against thread colours.
    """
    import cv2

    from digitizer_core.threads import rgb_to_lab

    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise SystemExit(f"cannot read {image_path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    ring = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]], axis=0)
    med = np.median(ring.reshape(-1, 3), axis=0).astype(np.uint8)
    return rgb_to_lab(med.reshape(1, 3)).reshape(3).astype(np.float64)


def _free_boundary_frac(poly, neighbours, gap_mm: float = NEIGHBOUR_GAP_MM) -> float:
    """How much of `poly`'s outline faces no other region -- i.e. bare page."""
    ext = poly.exterior
    total = ext.length
    if total <= 0:
        return 0.0
    covered = 0.0
    for n in neighbours:
        part = ext.intersection(n.buffer(gap_mm))
        if not part.is_empty:
            covered += part.length
    return max(0.0, 1.0 - covered / total)


def _thin_bands(regions, near, max_width_mm: float) -> list[list[int]]:
    """Group touching thin regions into the bands they were shattered from.

    Ringing at one edge is not one band but a STACK of them -- on Bridge Bar
    the black spokes go black -> Whale -> Cobblestone -> Skylight -> page,
    four concentric bands, each then broken into shards by stage 4's
    `make_valid` explode. Tested shard by shard, every inner shard's only
    neighbours are other shards, so nothing is ever "much larger than it" and
    nothing faces the page: the test sees the outermost band and misses the
    rest. Grouping first puts the question back where it belongs -- what is
    this whole thin structure sitting between?
    """
    thin = [i for i, r in enumerate(regions)
            if not r.meta.get("enclosed_background")
            and _width_mm(r.polygon) < max_width_mm]
    parent = {i: i for i in thin}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    thin_set = set(thin)
    for i in thin:
        for j in near[i]:
            if j in thin_set:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
    groups: dict[int, list[int]] = {}
    for i in thin:
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def find_halo_regions(result, cfg, bg_lab: np.ndarray | None = None) -> list[Candidate]:
    """Every region that reads as an edge-transition band rather than artwork.

    Colours are the regions' THREADS, not their raw pixels: a halo's cost is
    a cone on the machine, and the thread is what the operator loads. The
    thread is also the colour a fix has to stop the palette from buying.

    `bg_lab` (the page colour) lets the removed background stand as one side
    of a step. Without it the test sees only halos between two sewn shapes,
    which on this corpus is the minority of them.
    """
    chart = chart_for(cfg)
    regions = result.regions
    if not regions:
        return []
    near = _neighbours(regions)
    from shapely.ops import unary_union

    out: list[Candidate] = []
    for group in _thin_bands(regions, near, HALO_MAX_WIDTH_MM):
        members = set(group)
        group_area = sum(regions[i].area_mm2 for i in group)
        group_threads = {regions[i].thread_index for i in group}
        # The sides of the step this whole structure sits in: the regions
        # around it that outweigh the structure itself, largest first, plus
        # the page when a real share of the structure's outline faces
        # nothing. Measured against the GROUP so a stack of bands is judged
        # by what the stack lies between, not by what each shard touches.
        outside = {j for i in group for j in near[i] if j not in members}
        sides: list[tuple[str, np.ndarray]] = [
            (regions[j].thread_number, _lab(chart, regions[j].thread_index))
            for j in sorted(
                (j for j in outside
                 if regions[j].area_mm2 >= NEIGHBOUR_AREA_RATIO * group_area
                 and regions[j].thread_index not in group_threads),
                key=lambda j: -regions[j].area_mm2,
            )
        ]
        if bg_lab is not None:
            hull = unary_union([regions[i].polygon for i in group])
            free = max(
                (_free_boundary_frac(p, [regions[j].polygon for j in outside])
                 for p in (hull.geoms if hull.geom_type == "MultiPolygon" else [hull])),
                default=0.0,
            )
            if free >= FREE_BOUNDARY_FRAC:
                sides.append(("page", np.asarray(bg_lab, dtype=np.float64)))
        if len(sides) < 2:
            continue
        for i in group:
            r = regions[i]
            cand = _between(r, _width_mm(r.polygon), _lab(chart, r.thread_index), sides)
            if cand is not None:
                out.append(cand)
    return out


def _between(r, width: float, me: np.ndarray,
             sides: list[tuple[str, np.ndarray]]) -> Candidate | None:
    """Is `me` an interpolation of two of `sides`? -> the closest reading."""
    best: Candidate | None = None
    for a in range(len(sides)):
        for b in range(a + 1, len(sides)):
            (na, la), (nb, lb) = sides[a], sides[b]
            contrast = _de(la, lb)
            if contrast < HALO_MIN_CONTRAST_DE:
                continue
            seg = lb - la
            denom = float(seg @ seg)
            if denom <= 0:
                continue
            t = float((me - la) @ seg / denom)
            if not (HALO_T_RANGE[0] <= t <= HALO_T_RANGE[1]):
                continue
            foot = la + t * seg
            offset = _de(me, foot)
            if offset > HALO_MAX_OFFSET_DE:
                continue
            if best is None or offset < best.offset_de:
                best = Candidate(
                    shape_id=r.shape_id, thread_number=r.thread_number,
                    area_mm2=round(r.area_mm2, 2), width_mm=round(width, 3),
                    n1=na, n2=nb,
                    contrast_de=round(contrast, 1), t=round(t, 2),
                    offset_de=round(offset, 1),
                )
    return best


def read(result, plan, cfg, bg_lab=None) -> Reading:
    """Size what this design spends on halos, in the units the machine bills."""
    cands = find_halo_regions(result, cfg, bg_lab)
    halo_ids = {c.shape_id for c in cands}
    halo_threads = {c.thread_number for c in cands}

    rd = Reading(
        regions=len(result.regions),
        halo_regions=len(cands),
        halo_area_mm2=round(sum(c.area_mm2 for c in cands), 1),
        art_area_mm2=round(sum(r.area_mm2 for r in result.regions), 1),
        blocks=len(plan.blocks),
        candidates=sorted(cands, key=lambda c: (c.thread_number, -c.area_mm2)),
    )
    # A block is a halo block when EVERY shape it sews is a halo candidate:
    # that is a colour change, a cone and a rethread the design would not
    # have needed. A block that also carries artwork is not counted, even
    # though part of it is ringing -- this reads low on purpose.
    for i, b in enumerate(plan.blocks):
        n = sum(len(r.points) for r in b.runs)
        trims = sum(1 for r in b.runs if r.trim)
        rd.stitches += n
        rd.trims += trims
        shapes = {r.shape_id.split("-blend")[0] for r in b.runs if r.shape_id}
        if shapes and shapes <= halo_ids:
            rd.halo_blocks += 1
            rd.halo_stitches += n
            rd.halo_trims += trims
            num = plan.palette[i].get("number", "?") if i < len(plan.palette) else "?"
            rd.halo_threads.append(num)
    rd.halo_threads = sorted(set(rd.halo_threads))
    return rd


def _fixture(name: str) -> Path:
    p = ROOT / "testdata" / SHORT.get(name, name)
    if not p.exists():
        p = Path(name)
    if not p.exists():
        raise SystemExit(f"no such fixture: {name}")
    return p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fixtures", nargs="*", default=["bridge"])
    ap.add_argument("--mm", type=float, default=80.0)
    ap.add_argument("--colors", type=int, default=6)
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args(argv)

    print(f"{'fixture':<28} {'reg':>4} {'halo':>4} {'blocks':>7} "
          f"{'st':>7} {'halo st':>9} {'trims':>6} {'halo tr':>9}")
    for name in args.fixtures:
        path = _fixture(name)
        cfg = PipelineConfig(target_width_mm=args.mm, max_colors=args.colors,
                             satin=True, garment_id="left_chest")
        result, plan = digitize(path, cfg)
        rd = read(result, plan, cfg, background_lab(path))
        print(f"{name:<28} {rd.regions:>4} {rd.halo_regions:>4} "
              f"{rd.halo_blocks:>3}/{rd.blocks:<3} {rd.stitches:>7} "
              f"{rd.halo_stitches:>5} ({100*rd.halo_stitches/max(1,rd.stitches):4.1f}%) "
              f"{rd.trims:>6} {rd.halo_trims:>5} "
              f"({100*rd.halo_trims/max(1,rd.trims):4.1f}%)")
        if rd.halo_threads:
            print(f"    halo cones: {', '.join(rd.halo_threads)}  "
                  f"area {rd.halo_area_mm2} of {rd.art_area_mm2} mm²")
        if args.detail:
            for c in rd.candidates:
                print(f"    {c.shape_id} {c.thread_number} "
                      f"{c.area_mm2:7.2f}mm² w={c.width_mm:.3f} "
                      f"between {c.n1}/{c.n2} dE={c.contrast_de} "
                      f"t={c.t} off={c.offset_de}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
