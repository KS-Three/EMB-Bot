#!/usr/bin/env python
"""Price and PICTURE `cfg.cap_center_out` on a cap garment, OFF vs ON.

Two things a reviewer needs before flipping a sequencing flag, and a static
before/after render gives neither:

  1. **What it costs.** Cap order ignores travel, so the needle flies further.
     Stitches, trims, needle-up millimetres and blocks, both arms.
  2. **What it actually did.** A finished design looks nearly identical
     whichever order it sewed in — the thread ends up in the same places. So
     this draws a SEW-PROGRESSION map instead: every needle-down run coloured
     by its position in the sew order, dark first to bright last, with the
     first and last runs ringed. Two of those side by side show an ordering
     change the way a before/after of the finished stitches cannot.

**The picture does NOT show the cost.** Only needle-DOWN runs are drawn, so
the travel between them — the thing that more than doubles on `gaulke` — is
invisible in it. The table is where the cost lives; the map only answers what
moved. Drawing the jumps was considered and left out: on a 42-shape group the
flight lines cover the artwork and the ordering becomes unreadable, which is
the one thing this view exists to show.

The progression map doubles as the orientation check DOCTRINE asks for
("when a claim is about ORIENTATION, render it"). `cap_center_out`'s second
key claims that the LARGER y is the bill end of the cap, because stage 4's
frame runs y-DOWN. If that is right, the flag ON must start at the BOTTOM of
a picture drawn y-down — which is what this draws, the same direction
`export.py` established by rendering a professional file upright.

  .venv/Scripts/python tools/cap_order_ab.py
  .venv/Scripts/python tools/cap_order_ab.py --out docs/renders/cap-order-2026-09-19
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.pipeline import fabric_for  # noqa: E402
from digitizer_core.stage5_overlap import resolve_overlaps  # noqa: E402
from digitizer_core.stage6_applique import nn_group_key  # noqa: E402

# Committed fixtures only, so this runs in a fresh checkout. The real client
# hat artwork lives in the gitignored Drive corpus (`tools/pro_parity`), and a
# reviewer without it must still be able to reproduce the picture.
# PICK THESE DELIBERATELY, and see `group_sizes` below for why. The obvious
# fixtures are the wrong ones: `logo_whitebg` and `logo_alpha` put ONE shape in
# every colour group, so the flag is inert on them by construction and the
# first run of this tool showed a flat zero on both arms — a result that says
# nothing about the rule. Real client artwork is the opposite: measured
# 2026-09-19, `becker_marine_logo` holds 17 shapes in one cone,
# `logo_gaulke_roofing` 42/9/2, `logo_bridge_bar` 16/15/12/8/6/5/5/3/3/2.
# Becker is also the artwork the pro digitized as an actual Richardson 112 cap
# front, so it is the case this flag exists for.
CASES = [
    ("becker_marine", ROOT / "testdata/becker_marine_logo.png", "hat_front", 80.0),
    ("script_tires", ROOT / "testdata/logo_script_tires.png", "hat_front", 80.0),
    ("gaulke_roofing", ROOT / "testdata/photo/logo_gaulke_roofing.png", "hat_front", 80.0),
]
PX_PER_MM = 8.0


def arm(path: Path, garment: str, width: float, on: bool):
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                         cap_center_out=on)
    _result, plan = digitize(path, cfg)
    runs = [r for _b, r in plan.iter_runs()]

    needle_up = 0.0
    prev = None
    for r in runs:
        pts = list(r.points)
        if not pts:
            continue
        if prev is not None:
            needle_up += float(np.hypot(pts[0][0] - prev[0], pts[0][1] - prev[1]))
        prev = pts[-1]

    return {
        "plan": plan,
        "runs": runs,
        "stitches": plan.stats.stitch_count,
        "trims": plan.stats.trims,
        "blocks": len(plan.blocks),
        "needle_up_mm": needle_up,
    }


def group_sizes(path: Path, garment: str, width: float) -> list[int]:
    """Shapes per colour group, largest first — the flag's REACHABLE POPULATION.

    `cap_center_out` reorders shapes WITHIN a colour block, so a block holding
    one shape has no order to change and the flag is inert on it by
    construction. A design whose groups are all size 1 will show a zero delta
    no matter how right the rule is, and printing this beside the delta is what
    stops that zero being read as "the rule does nothing".
    """
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment)
    result, _plan = digitize(path, cfg)
    planned, _ = resolve_overlaps(result.regions, fabric_for(cfg), cfg)
    counts: dict[tuple, int] = {}
    for p in planned:
        k = nn_group_key(p)
        counts[k] = counts.get(k, 0) + 1
    return sorted(counts.values(), reverse=True)


def first_shapes(runs, n: int = 6) -> list[tuple[str, float, float]]:
    """The first `n` DISTINCT shape ids to receive thread, with centroids."""
    seen: dict[str, tuple[float, float]] = {}
    for r in runs:
        if not r.shape_id or r.shape_id in seen:
            continue
        pts = np.array(list(r.points), float)
        if not len(pts):
            continue
        seen[r.shape_id] = (float(pts[:, 0].mean()), float(pts[:, 1].mean()))
        if len(seen) >= n:
            break
    return [(k, v[0], v[1]) for k, v in seen.items()]


def render(runs, out: Path, title: str) -> None:
    pts_all = np.array([p for r in runs for p in r.points], float)
    if not len(pts_all):
        return
    x0, y0 = pts_all[:, 0].min(), pts_all[:, 1].min()
    x1, y1 = pts_all[:, 0].max(), pts_all[:, 1].max()
    pad = 4.0
    w = int((x1 - x0 + 2 * pad) * PX_PER_MM)
    h = int((y1 - y0 + 2 * pad) * PX_PER_MM) + 34
    img = np.full((h, w, 3), 250, np.uint8)

    def to_px(p):
        # y is NOT flipped: the frame is y-down and the picture is drawn
        # y-down, so "lower in this image" IS "lower on the garment".
        return (int((p[0] - x0 + pad) * PX_PER_MM),
                int((p[1] - y0 + pad) * PX_PER_MM) + 34)

    n = max(1, len(runs) - 1)
    for i, r in enumerate(runs):
        pts = list(r.points)
        if len(pts) < 2:
            continue
        # dark (first) -> bright (last), so the eye reads the sweep direction
        c = cv2.applyColorMap(np.uint8([[int(255 * i / n)]]), cv2.COLORMAP_VIRIDIS)
        colour = tuple(int(v) for v in c[0, 0])
        cv2.polylines(img, [np.array([to_px(p) for p in pts], np.int32)],
                      False, colour, 1, cv2.LINE_AA)

    for r, ring, label in ((runs[0], (0, 0, 220), "1st"),
                           (runs[-1], (220, 0, 0), "last")):
        pts = list(r.points)
        if pts:
            cv2.circle(img, to_px(pts[0]), 9, ring, 2, cv2.LINE_AA)
            cv2.putText(img, label, (to_px(pts[0])[0] + 12, to_px(pts[0])[1] + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, ring, 1, cv2.LINE_AA)

    cv2.putText(img, title, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (30, 30, 30), 1, cv2.LINE_AA)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=ROOT.parent / "docs/renders/cap-order-2026-09-19")
    args = ap.parse_args()

    print(f"{'case':<14} {'arm':<4} {'stitches':>9} {'trims':>6} "
          f"{'blocks':>7} {'needle-up mm':>13}")
    print("-" * 60)
    for name, path, garment, width in CASES:
        if not path.exists():
            print(f"  MISSING {path}")
            continue
        off = arm(path, garment, width, False)
        on = arm(path, garment, width, True)
        for tag, a in (("off", off), ("on", on)):
            print(f"{name:<14} {tag:<4} {a['stitches']:>9} {a['trims']:>6} "
                  f"{a['blocks']:>7} {a['needle_up_mm']:>13.1f}")
        d_st = on["stitches"] - off["stitches"]
        d_up = on["needle_up_mm"] - off["needle_up_mm"]
        pct = (100.0 * d_up / off["needle_up_mm"]) if off["needle_up_mm"] else 0.0
        print(f"{'':<14} {'d':<4} {d_st:>+9} {on['trims'] - off['trims']:>+6} "
              f"{on['blocks'] - off['blocks']:>+7} {d_up:>+12.1f} ({pct:+.1f}%)")

        sizes = group_sizes(path, garment, width)
        multi = [s for s in sizes if s > 1]
        print(f"    groups: {len(sizes)}, holding {sizes[:12]}"
              f"{' ...' if len(sizes) > 12 else ''}")
        if not multi:
            print("    >> EVERY GROUP HOLDS ONE SHAPE — the flag has nothing to "
                  "reorder here, so the zero delta above is structural, not a "
                  "verdict on the rule.")
        else:
            print(f"    >> {len(multi)} group(s) hold more than one shape "
                  f"(max {max(multi)}) — those are the ones the flag can move.")

        print(f"    first shapes OFF: "
              + ", ".join(f"{s}@({x:+.1f},{y:+.1f})"
                          for s, x, y in first_shapes(off["runs"])))
        print(f"    first shapes ON : "
              + ", ".join(f"{s}@({x:+.1f},{y:+.1f})"
                          for s, x, y in first_shapes(on["runs"])))
        print()

        render(off["runs"], args.out / f"{name}-off.png",
               f"{name} - cap_center_out OFF (dark=first, bright=last)")
        render(on["runs"], args.out / f"{name}-on.png",
               f"{name} - cap_center_out ON (dark=first, bright=last)")

    print(f"renders -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
