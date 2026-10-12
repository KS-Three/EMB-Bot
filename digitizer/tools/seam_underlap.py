#!/usr/bin/env python
"""Seams between colours: how far the earlier colour reaches under the later.

Kent's second sew-out finding, in another reader's words (2026-09-03): *"a
visible line of black fabric on the seams, not a butt joint — each region is
being sewn to its exact geometric boundary with no overlap."* The code
disagrees — stage 5 extends the colour that sews FIRST under the one that
sews after it by `pull + cfg.overlap_mm` and forbids the later colour from
growing back (`stage5_overlap.resolve_overlaps`) — and nothing had ever
measured what that rule actually leaves on a design, so neither side could
be checked. This is the instrument: it reads the planned geometry, pair by
pair, and reports the shared boundary in millimetres and the underlap depth
along it.

What it measures, per pair of ART-adjacent regions on different threads:

  * `shared_mm` — the length of the later colour's SEWN boundary that lies
    on the earlier colour's sewn polygon (the seam the cloth will show if
    pull opens it);
  * `depth_mm` — the sewn overlap of the two polygons over that length: the
    average underlap along the seam, as sewn. Artwork that abuts with no
    sewn overlap at all is a seam at depth 0.

Totals: shared seam length, its length-weighted mean depth, and how much of
it sits under each rung of `RUNGS` (0.25 / 0.5 / 1.0 mm — the card's block
6 sews exactly these). Same-thread neighbours are reported apart: stage 5
gives them no seam logic (they share a colour, the corridor keeps them
from fusing) and an underlap there would be a colour error.

It does NOT measure the blend tier's shade-band seams (bands are cut inside
stage 6 from one region) — since 2026-09-03 those underlap by
`cfg.overlap_mm` too, earlier under later, and `test_stage6_blend.py` pins
it. And it does not set a number: whether 0.25 mm survives pique pull is a
sew-out question, card block 6.

    .venv/bin/python tools/seam_underlap.py logo_whitebg.png photo/logo_bridge_bar.jpg
    .venv/bin/python tools/seam_underlap.py --all [--width 80] [--garment left_chest]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, run_stages  # noqa: E402
from digitizer_core.pipeline import fabric_for  # noqa: E402
from digitizer_core.regions import Region  # noqa: E402
from digitizer_core.stage5_overlap import PlannedRegion, resolve_overlaps  # noqa: E402

TOUCH_MM = 0.3           # artwork polygons closer than this abut (a pixel of anti-aliasing at 4 px/mm)
RUNGS = (0.25, 0.5, 1.0)  # the card's block 6 underlap rungs
# The forbid-gap rule's documented CANDIDATE (`cfg.forbid_gap_mm`, Law 26:
# "engineered gaps under 2 stitch rows (~0.8 mm) close up"). A reading
# threshold here, not a measured constant — ROADMAP gate 1, card block 6.
GAP_MM = 0.8
FIXTURES = [
    "logo_whitebg.png", "logo_alpha.png", "bg_uncertain.png", "becker_marine_logo.png",
    "photo/enthusiast_logo.png", "photo/logo_bridge_bar.jpg", "photo/logo_hotel_fremont.webp",
    "photo/drone_render.png", "photo/repro_gradient_white_icon.png", "photo/summit_badge.png",
]


def _art_shared_length(a: Polygon, b: Polygon) -> float:
    """Length of `a`'s artwork boundary within TOUCH_MM of `b`'s."""
    return float(a.boundary.intersection(b.boundary.buffer(TOUCH_MM)).length)


def measure(regions: list[Region], planned: list[PlannedRegion]) -> dict:
    """-> {'pairs': [...], 'shared_mm', 'mean_depth_mm', 'under': {rung: mm},
    'same_thread_mm', 'same_thread_pairs'}.

    A seam is where the LATER colour's sewn boundary lies on the earlier
    colour's sewn polygon; its depth is the sewn overlap of the two over that
    length — the tongue stage 5 hid under the later colour, as sewn. A pair
    whose artwork abuts but whose sewn polygons never overlap is a seam with
    no underlap at all, reported at depth 0 over its artwork contact.
    """
    by_id = {p.shape_id: p for p in planned}
    art = {r.shape_id: r for r in regions}
    ids = [r.shape_id for r in regions if r.shape_id in by_id]
    pairs = []
    same_mm = 0.0
    same_pairs = 0
    for i, a_id in enumerate(ids):
        for b_id in ids[i + 1:]:
            pa, pb = by_id[a_id], by_id[b_id]
            ra, rb = art[a_id], art[b_id]
            art_touch = ra.polygon.distance(rb.polygon) <= TOUCH_MM
            if pa.sew_index == pb.sew_index:
                if art_touch:
                    same_mm += _art_shared_length(ra.polygon, rb.polygon)
                    same_pairs += 1
                continue
            earlier, later = (pa, pb) if pa.sew_index < pb.sew_index else (pb, pa)
            seam = later.polygon.boundary.intersection(earlier.polygon.buffer(0.01))
            seam_len = float(seam.length)
            if seam_len > 0.0:
                tongue = earlier.polygon.intersection(later.polygon)
                depth = float(tongue.area) / seam_len
            elif art_touch:
                seam_len = _art_shared_length(ra.polygon, rb.polygon)
                depth = 0.0
            else:
                continue
            if seam_len <= 0.0:
                continue
            pairs.append({"earlier": earlier.shape_id, "later": later.shape_id,
                          "shared_mm": round(seam_len, 2), "depth_mm": round(depth, 3)})
    shared_total = sum(p["shared_mm"] for p in pairs)
    mean_depth = (sum(p["shared_mm"] * p["depth_mm"] for p in pairs) / shared_total) if shared_total else None
    under = {r: round(sum(p["shared_mm"] for p in pairs if p["depth_mm"] < r), 2) for r in RUNGS}
    return {"pairs": pairs, "shared_mm": round(shared_total, 2),
            "mean_depth_mm": None if mean_depth is None else round(mean_depth, 3),
            "under": under, "same_thread_mm": round(same_mm, 2), "same_thread_pairs": same_pairs}


def cloth_take_back(planned: list[PlannedRegion], cfg, fabric) -> dict[str, float]:
    """-> {shape_id: how far the fabric pulls that sewn polygon back in}.

    Stage 5 grows every shape by the fabric's pull so the CLOTH lands on the
    artwork; reading a sewn polygon as the cloth means taking that back.
    A satin-tier shape under `cfg.satin_rail_comp` takes its pull on the
    rails in stage 6, so its stage-5 polygon is already the cloth: 0.
    Isotropic, like the default compensation; `cfg.directional_comp` would
    want an axial take-back, which this does not model.
    """
    from digitizer_core.stage5_overlap import widened_lettering
    pull = max(0.0, float(fabric.pull_comp_mm))
    rails = bool(getattr(cfg, "satin_rail_comp", False))
    return {p.shape_id: (0.0 if rails and p.satin_tier and not widened_lettering(p.region)
                         else pull) for p in planned}


def narrow_gaps(regions: list[Region], planned: list[PlannedRegion],
                gap_mm: float = GAP_MM, take_back: dict[str, float] | None = None) -> list[dict]:
    """-> [{'earlier', 'later', 'gap_mm', 'gap_mm2', 'open_mm2'}] — every
    strip of bare fabric narrower than `gap_mm` between two STITCHED colours
    that no one colour covers on the cloth.

    The strip is read off the ARTWORK, as the morphological closing of the
    pair at `gap_mm / 2` (it fills exactly the fabric narrower than `gap_mm`
    between them, flush with their ends), kept where it lies within `gap_mm`
    of both, touches both, and no third stitched colour's artwork covers
    it; pieces under `gap_mm²` are corner fillets where two edges meet at an
    angle, not a channel, and are dropped.

    It is OPEN where nothing covers it on the cloth: the union of every
    stitched colour's SEWN polygon, each eroded by its `take_back`
    (`cloth_take_back`; None reads the plan as drawn) wherever it lies on
    bare fabric — pull takes back compensation, and compensation is the
    thread beyond the artwork; thread on some colour's artwork (a clipped
    seam edge, a tongue) stays. That is what stage 5
    leaves without `cfg.forbid_gap_mm`: its underlap reaches only into the
    later colour's ARTWORK, never across bare fabric, so across a strip the
    two pull bands meet in the middle (overlapping, under two pulls wide)
    and pull takes both back on the cloth. It is closed when one colour
    spans it and tucks under the other — an ordinary seam. `open_mm2` is
    the uncovered area; a gap reads open over 0.01 mm² (a hundredth of a
    square millimetre is buffer noise) and only if some of it is at least
    0.1 mm wide (the DST grid): where a closed strip meets a third colour,
    that seam's own tongue (`overlap_mm`) is shallower than the pull on
    pique by 0.05 mm, a seam shortfall defect 47's underlap half owns, not
    a gap.
    """
    cloth: dict[str, object] = {}

    def on_cloth(p: PlannedRegion):
        if p.shape_id not in cloth:
            k = (take_back or {}).get(p.shape_id, 0.0)
            cloth[p.shape_id] = p.polygon.buffer(-k) if k > 0 else p.polygon
        return cloth[p.shape_id]

    from shapely import STRtree
    from shapely.geometry import box as _box
    from shapely.ops import unary_union

    by_id = {p.shape_id: p for p in planned}
    sew = [r for r in regions if r.meta.get("stitched", True) and r.shape_id in by_id]
    if len(sew) < 2 or gap_mm <= 0:
        return []
    tree = STRtree([r.polygon for r in sew])
    half = gap_mm / 2.0
    floor = gap_mm * gap_mm
    out = []
    for i, a in enumerate(sew):
        x0, y0, x1, y1 = a.polygon.bounds
        for j in tree.query(_box(x0 - gap_mm, y0 - gap_mm, x1 + gap_mm, y1 + gap_mm)):
            j = int(j)
            if j <= i:
                continue
            b = sew[j]
            pa, pb = by_id[a.shape_id], by_id[b.shape_id]
            if pa.sew_index == pb.sew_index:
                continue
            d = a.polygon.distance(b.polygon)
            if d >= gap_mm:
                continue
            lens = a.polygon.buffer(gap_mm).intersection(b.polygon.buffer(gap_mm))
            if lens.is_empty:
                continue
            lx0, ly0, lx1, ly1 = lens.bounds
            win = _box(lx0 - 2 * gap_mm, ly0 - 2 * gap_mm, lx1 + 2 * gap_mm, ly1 + 2 * gap_mm)
            ca, cb = a.polygon.intersection(win), b.polygon.intersection(win)
            both = unary_union([ca, cb])
            strip = both.buffer(half).buffer(-half).difference(both).intersection(lens)
            others = [sew[int(k)].polygon for k in tree.query(win) if int(k) not in (i, j)]
            if others:
                strip = strip.difference(unary_union(others))
            parts = [g for g in getattr(strip, "geoms", [strip])
                     if g.geom_type == "Polygon" and g.area >= floor
                     and g.distance(ca) < 1e-6 and g.distance(cb) < 1e-6]
            if not parts:
                continue
            gap = unary_union(parts)
            near = [int(k) for k in tree.query(win)]
            art_win = unary_union([sew[k].polygon.intersection(win) for k in near])
            cover = unary_union([on_cloth(by_id[sew[k].shape_id]) for k in near]
                                + [by_id[sew[k].shape_id].polygon.intersection(art_win)
                                   for k in near])
            hole = gap.difference(cover)
            # A band thinner than the DST's 0.1 mm grid is not a gap the
            # machine can leave; it is what is left where a seam's own
            # underlap is shallower than the pull (defect 47's other half).
            if hole.area <= 0.01 or hole.buffer(-0.05).is_empty:
                continue
            open_mm2 = hole.area
            earlier, later = (pa, pb) if pa.sew_index < pb.sew_index else (pb, pa)
            out.append({"earlier": earlier.shape_id, "later": later.shape_id,
                        "gap_mm": round(float(d), 3), "gap_mm2": round(float(gap.area), 3),
                        "open_mm2": round(float(open_mm2), 3)})
    return out


def measure_image(image: Path, width_mm: float, garment: str | None) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result = run_stages(image, cfg)
    planned, _w = resolve_overlaps(result.regions, fabric_for(cfg), cfg, result.design_class)
    out = measure(result.regions, planned)
    out["regions"] = len(result.regions)
    out["narrow_gaps"] = narrow_gaps(result.regions, planned,
                                     take_back=cloth_take_back(planned, cfg, fabric_for(cfg)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("images", nargs="*", help="paths under testdata/, or absolute")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--pairs", action="store_true", help="print every pair")
    args = ap.parse_args(argv)
    names = FIXTURES if args.all else args.images
    if not names:
        ap.error("give fixture paths or --all")
    hdr = (f"{'fixture':34s} {'pairs':>5s} {'seam mm':>8s} {'depth':>6s} "
           + " ".join(f"<{r:g}" for r in RUNGS) + f"   same-thread   open gaps<{GAP_MM:g}")
    print(hdr)
    for name in names:
        path = Path(name) if Path(name).is_absolute() else ROOT / "testdata" / name
        m = measure_image(path, args.width, args.garment)
        under = " ".join(f"{m['under'][r]:>5.1f}" for r in RUNGS)
        depth = "-" if m["mean_depth_mm"] is None else f"{m['mean_depth_mm']:.3f}"
        print(f"{Path(name).name:34s} {len(m['pairs']):5d} {m['shared_mm']:8.1f} {depth:>6s} {under}   {m['same_thread_mm']:.1f} mm / {m['same_thread_pairs']} pairs"
              f"   {len(m['narrow_gaps'])}")
        if args.pairs:
            for p in m["pairs"]:
                print(f"    {p['earlier']} under {p['later']}: {p['shared_mm']} mm shared, {p['depth_mm']} mm deep")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
