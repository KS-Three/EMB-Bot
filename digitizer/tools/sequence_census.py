#!/usr/bin/env python
"""Block/patch census of a plan's sew order — the fragmentation instrument.

Built for the 2026-09-01 sew-out follow-up: Kent watched the machine sew a
gradient icon as scattered per-shade patches, criss-crossing sewn work and
re-entering enclosed interiors late. This dumps the numbers that verdict is
made of, per design:

- per BLOCK (= cone/colour change): stitches, patches, sew-position %, and
  whether the block re-enters territory earlier blocks already sewed;
- per block, the needle-up travel BETWEEN its patches (the intra-block
  criss-cross), plus how much of that travel crosses thread already laid;
- design totals: cones, trims, jumps, needle-up mm, tail travel.

A "patch" is a maximal needle-down streak: a run opened by jump/trim plus
everything after it up to the next lifted run. Patch travel is the straight
gap between one patch's last stitch and the next patch's first — what the
machine actually flies (or walks as a split jump-chain).

Usage (from digitizer/):
    .venv/Scripts/python tools/sequence_census.py testdata/photo/repro_gradient_white_icon.png
    ... [--width 80] [--photo] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shapely.geometry import LineString, Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402


def _block_geom(block):
    parts = []
    for r in block.runs:
        if len(r.points) >= 2:
            parts.append(LineString(r.points))
        elif r.points:
            parts.append(Point(r.points[0]))
    return unary_union(parts) if parts else None


def census(image: Path, width: float, photo: bool) -> dict:
    cfg = PipelineConfig(target_width_mm=width, is_photographic=photo or None)
    result, plan = digitize(image, cfg)

    total_st = sum(len(r.points) for _, r in plan.iter_runs())
    out_blocks = []
    sewn_so_far = 0
    laid_geoms = []          # per finished block, its thread geometry
    laid_union = None
    for bi, b in enumerate(plan.blocks):
        st = sum(len(r.points) for r in b.runs)
        # Patches: maximal needle-down streaks.
        patches = []         # (first_pt, last_pt, stitches)
        gaps = []            # needle-up gap before each patch after the first
        cross_mm = 0.0       # gap length that crosses earlier blocks' thread
        cross_n = 0
        trims = jumps = 0
        cur_first = cur_last = None
        cur_n = 0
        for r in b.runs:
            if not r.points:
                continue
            if r.trim:
                trims += 1
            elif r.jump:
                jumps += 1
            if (r.jump or r.trim) and cur_first is not None:
                patches.append((cur_first, cur_last, cur_n))
                gap = math.dist(cur_last, r.points[0])
                gaps.append(gap)
                if laid_union is not None and gap > 0:
                    seg = LineString([cur_last, r.points[0]])
                    if seg.intersects(laid_union):
                        cross_mm += gap
                        cross_n += 1
                cur_first, cur_n = r.points[0], 0
            elif cur_first is None:
                cur_first = r.points[0]
            cur_last = r.points[-1]
            cur_n += len(r.points)
        if cur_first is not None:
            patches.append((cur_first, cur_last, cur_n))

        geom = _block_geom(b)
        # Re-entry: this block's thread lies inside the convex hull of what
        # was already sewn (the machine returns INTO finished territory).
        reentry = bool(
            laid_union is not None and geom is not None
            and laid_union.convex_hull.contains(geom)
        )
        out_blocks.append({
            "block": bi,
            "thread": b.thread_index,
            "number": b.thread_number,
            "stitches": st,
            "start_pct": round(100.0 * sewn_so_far / total_st, 1) if total_st else 0.0,
            "patches": len(patches),
            "patch_sizes": sorted((n for _f, _l, n in patches), reverse=True),
            "trims": trims,
            "jumps": jumps,
            "travel_mm": round(sum(gaps), 1),
            "travel_max_mm": round(max(gaps), 1) if gaps else 0.0,
            "cross_mm": round(cross_mm, 1),
            "cross_n": cross_n,
            "reentry_into_sewn": reentry,
        })
        sewn_so_far += st
        if geom is not None:
            laid_geoms.append(geom)
            laid_union = unary_union(laid_geoms)

    # Inter-block gaps (the colour-change hauls) and the tail: needle-up
    # travel spent in the last 10% of penetrations.
    inter = []
    prev_end = None
    for b in plan.blocks:
        pts = [p for r in b.runs for p in r.points]
        if not pts:
            continue
        if prev_end is not None:
            inter.append(math.dist(prev_end, pts[0]))
        prev_end = pts[-1]
    tail_cut = 0.9 * total_st
    seen = 0
    tail_travel = 0.0
    last_pt = None
    for _b, r in plan.iter_runs():
        if not r.points:
            continue
        if (r.jump or r.trim) and last_pt is not None and seen >= tail_cut:
            tail_travel += math.dist(last_pt, r.points[0])
        seen += len(r.points)
        last_pt = r.points[-1]

    st = plan.stats
    return {
        "image": str(image),
        "width": width,
        "photo": photo,
        "blocks": len(plan.blocks),
        "color_changes": max(0, len(plan.blocks) - 1),
        "stitches": total_st,
        "trims": st.trims,
        "jumps": st.jumps,
        "intra_travel_mm": round(sum(b["travel_mm"] for b in out_blocks), 1),
        "cross_mm": round(sum(b["cross_mm"] for b in out_blocks), 1),
        "cross_n": sum(b["cross_n"] for b in out_blocks),
        "inter_block_mm": round(sum(inter), 1),
        "tail_travel_mm": round(tail_travel, 1),
        "reentries": sum(1 for b in out_blocks if b["reentry_into_sewn"]),
        "per_block": out_blocks,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--photo", action="store_true")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    c = census(args.image, args.width, args.photo)
    if args.json:
        args.json.write_text(json.dumps(c, indent=2), encoding="utf-8")

    print(f"{c['image']}  {c['width']}mm  photo={c['photo']}")
    print(f"blocks={c['blocks']} changes={c['color_changes']} stitches={c['stitches']} "
          f"trims={c['trims']} jumps={c['jumps']}")
    print(f"intra-block travel={c['intra_travel_mm']}mm  "
          f"crossing sewn work={c['cross_mm']}mm in {c['cross_n']} moves  "
          f"inter-block={c['inter_block_mm']}mm  tail(last 10%)={c['tail_travel_mm']}mm  "
          f"re-entries={c['reentries']}")
    for b in c["per_block"]:
        sizes = b["patch_sizes"]
        shown = ",".join(str(s) for s in sizes[:6]) + ("+" if len(sizes) > 6 else "")
        print(f"  b{b['block']} t{b['thread']} ({b['number']}) @{b['start_pct']}%  "
              f"{b['stitches']}st {b['patches']}patches[{shown}] "
              f"trims={b['trims']} jumps={b['jumps']} travel={b['travel_mm']}mm "
              f"max={b['travel_max_mm']} cross={b['cross_mm']}mm"
              f"{'  REENTRY' if b['reentry_into_sewn'] else ''}")


if __name__ == "__main__":
    main()
