"""Hairline tier: OFF vs ON at 40 and 60 wt, rendered and measured (2026-10-12).

    python -m tools.hairline_renders [--out ../docs/renders/hairline-2026-10-12]

For each synthetic fixture (`tools/draw_hair_fixtures.py`) and each arm —
`off40` (today), `on40` (`cfg.hairline` at 40 wt), `on60` (at 60 wt) — this
digitizes once (stages 0-4 are shared; only stage 5-7 differ by arm), renders
the plan as THREAD with `stitchviz` at the arm's laid width
(`machine.thread_profile(wt).width_mm`), and prints one table row:

- strands drawn (the fixture's own count) vs hairline strands sewn
- stitches, trims, jumps, total needle-down thread (m)
- stitches under 1.0 mm in the dark (hair / ink) thread — the needle floor
- longest jump (mm)
- the skin fill (its fill + underlay runs): stitch count, an md5 against
  `off40` (byte-identical or not — the hairline shapes' new end points move
  the fill's entries, so expect "not" with an unchanged count and pitch),
  and `fill_pitch`'s median row pitch; whole-design `stitchviz.coverage`

The fixtures are forced flat: they are flat art (one colour per strand), and
stage 0 reads the hair fixture's dense thin strokes as `gradient` — recorded
in the doc as a finding, not hidden by the force.

Every number this prints is a property of the FILE, not of a sew-out (ROADMAP
gate 1). The render is thread drawn at a width; it is not cloth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitchviz  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools import draw_hair_fixtures as fx  # noqa: E402
from tools.fill_pitch import _summarise  # noqa: E402

SYN = ROOT / "testdata" / "synthetic"
FIXTURES = {
    "hair_strands": dict(file="hair_strands.png", width_mm=80.0,
                         drawn=len(fx.hair_strands()), zoom=(14, 34, 34, 52)),
    "thin_script": dict(file="thin_script.png", width_mm=60.0,
                        drawn=len(fx.script_strokes()), zoom=(8, 10, 32, 24)),
}
ARMS = {"off40": (False, 40), "on40": (True, 40), "on60": (True, 60)}
RENDER_PX_PER_MM = 12.0
ZOOM_PX_PER_MM = 30.0


def _lum(rgb) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def measure(plan, drawn: int, base_skin_md5: str | None) -> dict:
    blocks = list(plan.blocks)
    dark = min(blocks, key=lambda b: _lum(b.rgb)).thread_number
    light = max(blocks, key=lambda b: sum(len(r.points) for r in b.runs if r.kind == "fill")
                if any(r.kind == "fill" for r in b.runs) else -1)
    stitches = trims = jumps = 0
    thread_mm = 0.0
    short_dark = short_all = lock_legs = dark_stitches = 0
    dark_mm = 0.0
    skin_fill = 0
    longest_jump = 0.0
    strands = 0
    prev = None
    skin = hashlib.md5()
    skin_passes, cur = [], []
    for b in blocks:
        for r in b.runs:
            pts = r.points
            stitches += len(pts)
            if r.trim:
                trims += 1
            elif r.jump:
                jumps += 1
            if r.jump and prev is not None and pts:
                longest_jump = max(longest_jump, math.dist(prev, pts[0]))
            for a, c in zip(pts, pts[1:]):
                d = math.dist(a, c)
                thread_mm += d
                if b.thread_number == dark:
                    dark_mm += d
                if 0.01 < d < machine.MIN_STITCH_MM:   # SAME_POINT_MM: not a penetration
                    short_all += 1
                    if b.thread_number == dark:
                        if abs(d - machine.TIE_STITCH_MM) < 1e-6:
                            lock_legs += 1     # the existing lock rule's 0.8 mm legs
                        else:
                            short_dark += 1
            if b.thread_number == dark:
                dark_stitches += len(pts)
                if r.jump or r.trim or not strands:
                    strands += 1      # needle-down passes in the dark thread
            if b is light and r.kind in ("fill", "underlay"):
                # The skin's own fill rows and their underlay — what the
                # hairline tier must not touch. (Thin skin SLIVERS between
                # strands are run-tier shapes and may legitimately move.)
                skin.update(json.dumps([[round(x, 4), round(y, 4), r.kind]
                                        for x, y in pts]).encode())
                skin_fill += len(pts)
                if r.kind == "fill":
                    if r.jump and cur:
                        skin_passes.append(cur)
                        cur = []
                    cur.extend(pts)
            if pts:
                prev = pts[-1]
    if cur:
        skin_passes.append(cur)
    pitch = _summarise(skin_passes, "skin")
    skin_md5 = skin.hexdigest()
    return {
        "drawn": drawn,
        "dark_passes": strands,
        "stitches": stitches,
        "trims": trims,
        "jumps": jumps,
        "thread_m": round(thread_mm / 1000.0, 2),
        "dark_stitches": dark_stitches,
        "dark_thread_m": round(dark_mm / 1000.0, 2),
        "under_1mm_dark": short_dark,
        "lock_legs_dark": lock_legs,
        "under_1mm_all": short_all,
        "longest_jump_mm": round(longest_jump, 1),
        "skin_md5": skin_md5[:10],
        "_skin_full": skin_md5,
        "skin_unchanged": True if base_skin_md5 is None else skin_md5 == base_skin_md5,
        "skin_fill_stitches": skin_fill,
        "skin_pitch_mm": pitch["pitch_mm_median"],
        "hairline_warning": next(({k: w.get(k) for k in ("shapes", "strands", "dropped")}
                                  for w in plan.warnings if w["code"] == "HAIRLINE_TIER_SEWN"), None),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(ROOT.parent / "docs" / "renders" / "hairline-2026-10-12"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table = {}
    for key, f in FIXTURES.items():
        base_cfg = dict(target_width_mm=f["width_mm"], forced_class="flat")
        result = run_stages(SYN / f["file"], PipelineConfig(**base_cfg))
        base_md5 = None
        for arm, (on, wt) in ARMS.items():
            cfg = PipelineConfig(**base_cfg, hairline=on, thread_wt=wt)
            plan = plan_stitches(result, cfg)
            row = measure(plan, f["drawn"], base_md5)
            table[f"{key}/{arm}"] = row
            design = plan_to_design(plan, name=f"{key} {arm}")
            row["coverage"] = round(stitchviz.coverage(design), 4)
            tw = machine.thread_profile(wt).width_mm
            img = stitchviz.render_design(design, px_per_mm=RENDER_PX_PER_MM, thread_mm=tw)
            cv2.imwrite(str(out / f"{key}_{arm}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
            # A zoom on a curl / loop region, mm box (x0, y0, x1, y1) in the
            # fixture's own frame, read off the render's frame (pad 2 mm).
            big = stitchviz.render_design(design, px_per_mm=ZOOM_PX_PER_MM, thread_mm=tw)
            x0, y0, x1, y1 = f["zoom"]
            s = ZOOM_PX_PER_MM
            crop = big[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)]
            if crop.size:
                cv2.imwrite(str(out / f"{key}_{arm}_zoom.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
            if arm == "off40":
                base_md5 = row.pop("_skin_full")
            else:
                row.pop("_skin_full")
            print(f"{key}/{arm}: " + json.dumps(row))
    (out / "table.json").write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
