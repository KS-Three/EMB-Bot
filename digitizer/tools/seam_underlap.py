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


def measure_image(image: Path, width_mm: float, garment: str | None) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result = run_stages(image, cfg)
    planned, _w = resolve_overlaps(result.regions, fabric_for(cfg), cfg, result.design_class)
    out = measure(result.regions, planned)
    out["regions"] = len(result.regions)
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
    hdr = f"{'fixture':34s} {'pairs':>5s} {'seam mm':>8s} {'depth':>6s} " + " ".join(f"<{r:g}" for r in RUNGS) + "   same-thread"
    print(hdr)
    for name in names:
        path = Path(name) if Path(name).is_absolute() else ROOT / "testdata" / name
        m = measure_image(path, args.width, args.garment)
        under = " ".join(f"{m['under'][r]:>5.1f}" for r in RUNGS)
        depth = "-" if m["mean_depth_mm"] is None else f"{m['mean_depth_mm']:.3f}"
        print(f"{Path(name).name:34s} {len(m['pairs']):5d} {m['shared_mm']:8.1f} {depth:>6s} {under}   {m['same_thread_mm']:.1f} mm / {m['same_thread_pairs']} pairs")
        if args.pairs:
            for p in m["pairs"]:
                print(f"    {p['earlier']} under {p['later']}: {p['shared_mm']} mm shared, {p['depth_mm']} mm deep")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
