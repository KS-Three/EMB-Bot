"""Hairline tier: OFF vs ON at 40 and 60 wt, rendered and measured (2026-10-12).

    python -m tools.hairline_renders [--out ../docs/renders/hairline-ground-2026-10-12]

For each synthetic fixture (`tools/draw_hair_fixtures.py`) and each arm —
`off40` (today), `on40` (`cfg.hairline` at 40 wt), `on60` (at 60 wt),
`on60g` (at 60 wt with `cfg.hairline_over_ground`, step 2) — this
digitizes once (stages 0-4 are shared; only stage 5-7 differ by arm), renders
the plan as THREAD with `stitchviz` at the arm's laid width
(`machine.thread_profile(wt).width_mm`), and prints one table row:

- bare fabric (step 2): artwork the design claims that no thread covers,
  read with preflight's own uncovered-artwork instrument
  (`preflight._coverage_map` at `_UNCOVERED_CELL_MM`, covered at
  `_COVERAGE_FLOOR_UNITS`, wanted = sewn regions' artwork on the source's
  ink — `_uncovered_findings`' ground truth) but summed over EVERY bare
  cell, not only the compact patches that finding reports, since a strip
  of cloth beside a strand is exactly the thin patch it filters out. Also
  the part of it the `off40` arm did not have (`bare_new_mm2`).
- the largest hairline shape's width: traced median, source read, and its
  margin under the arm's gate (step 2's finding-1 fix).

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
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, preflight, stitchviz  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from digitizer_core.stage6_hairline import hairline_candidates  # noqa: E402
from tools import draw_hair_fixtures as fx  # noqa: E402
from tools.fill_pitch import _summarise  # noqa: E402

SYN = ROOT / "testdata" / "synthetic"
FIXTURES = {
    "hair_strands": dict(file="hair_strands.png", width_mm=80.0,
                         drawn=len(fx.hair_strands()), zoom=(14, 34, 34, 52)),
    "thin_script": dict(file="thin_script.png", width_mm=60.0,
                        drawn=len(fx.script_strokes()), zoom=(8, 10, 32, 24)),
}
# arm -> (cfg.hairline, cfg.thread_wt, cfg.hairline_over_ground)
ARMS = {"off40": (False, 40, False), "on40": (True, 40, False),
        "on60": (True, 60, False), "on60g": (True, 60, True)}
RENDER_PX_PER_MM = 12.0
ZOOM_PX_PER_MM = 30.0


def bare_cells(plan, result, p):
    """-> (bool grid of bare artwork cells, (x0, y0) mm origin, cell mm).

    Preflight's uncovered-artwork instrument (`_uncovered_findings`): thread
    is `_coverage_map`'s ribbons, covered at `_COVERAGE_FLOOR_UNITS`; wanted
    is every sewn-or-not STITCHED region's artwork (exterior minus its own
    interiors, OR-ed) on the source's ink (`~bg_mask`). Every region the
    design claims is wanted in every arm, so the arms compare like for like."""
    cell = preflight._UNCOVERED_CELL_MM
    grid, (gx0, gy0) = preflight._coverage_map(plan, cell_mm=cell)
    covered = grid >= preflight._COVERAGE_FLOOR_UNITS
    ny, nx = grid.shape
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h, w = p.bg_mask.shape

    def to_px(coords):
        a = np.asarray(coords, np.float64)
        return np.column_stack([a[:, 0] * p.px_per_mm + cx,
                                a[:, 1] * p.px_per_mm + cy]).astype(np.int32)

    claimed = np.zeros((h, w), np.uint8)
    one = np.zeros((h, w), np.uint8)
    for r in result.regions:
        if not r.meta.get("stitched", True):
            continue
        for part in (r.polygon.geoms if hasattr(r.polygon, "geoms") else [r.polygon]):
            one[:] = 0
            cv2.fillPoly(one, [to_px(part.exterior.coords)], 1)
            for ring in part.interiors:
                cv2.fillPoly(one, [to_px(ring.coords)], 0)
            claimed |= one
    wanted_px = (claimed > 0) & (~p.bg_mask)
    gy, gx = np.mgrid[0:ny, 0:nx]
    sx = np.clip((((gx + 0.5) * cell + gx0) * p.px_per_mm + cx).astype(np.int64), 0, w - 1)
    sy = np.clip((((gy + 0.5) * cell + gy0) * p.px_per_mm + cy).astype(np.int64), 0, h - 1)
    return wanted_px[sy, sx] & ~covered, (gx0, gy0), cell


def bare_new_mm2(bare, origin, base) -> float:
    """Bare cells of this arm that sit on a cell the `off40` arm covered."""
    grid, (gx0, gy0), cell = bare
    bgrid, (bx0, by0), _ = base
    ys, xs = np.nonzero(grid)
    if not len(xs):
        return 0.0
    mx = (xs + 0.5) * cell + gx0
    my = (ys + 0.5) * cell + gy0
    bi = np.floor((mx - bx0) / cell).astype(int)
    bj = np.floor((my - by0) / cell).astype(int)
    inside = (bi >= 0) & (bj >= 0) & (bi < bgrid.shape[1]) & (bj < bgrid.shape[0])
    was_bare = np.zeros(len(xs), bool)
    was_bare[inside] = bgrid[bj[inside], bi[inside]]
    return float((~was_bare).sum()) * cell * cell


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
    ap.add_argument("--out", default=str(ROOT.parent / "docs" / "renders"
                                         / "hairline-ground-2026-10-12"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table = {}
    for key, f in FIXTURES.items():
        base_cfg = dict(target_width_mm=f["width_mm"], forced_class="flat")
        result = run_stages(SYN / f["file"], PipelineConfig(**base_cfg))
        p = preflight.prep(SYN / f["file"], PipelineConfig(**base_cfg),
                           design_class=result.design_class)
        stitched = [r for r in result.regions if r.meta.get("stitched", True)]
        base_md5 = None
        base_bare = None
        for arm, (on, wt, ground) in ARMS.items():
            cfg = PipelineConfig(**base_cfg, hairline=on, thread_wt=wt,
                                 hairline_over_ground=ground)
            plan = plan_stitches(result, cfg)
            row = measure(plan, f["drawn"], base_md5)
            table[f"{key}/{arm}"] = row
            bare = bare_cells(plan, result, p)
            cell2 = bare[2] ** 2
            row["bare_mm2"] = round(float(bare[0].sum()) * cell2, 2)
            if base_bare is None:
                base_bare = bare
                row["bare_new_mm2"] = 0.0
            else:
                row["bare_new_mm2"] = round(bare_new_mm2(bare, None, base_bare), 2)
            if on:
                cands = hairline_candidates(stitched, cfg, ink=result.ink_source)
                area = {r.shape_id: r.polygon.area for r in stitched}
                row["hairline_candidates"] = len(cands)
                if cands:
                    big = max(cands, key=lambda s: area[s])
                    m = cands[big]
                    lim = machine.thread_profile(wt).hairline_max_width_mm
                    row["largest_hairline"] = {
                        "area_mm2": round(area[big], 1),
                        "traced_mm": round(m["width_traced_mm"], 3),
                        "source_mm": (None if m["width_source_mm"] is None
                                      else round(m["width_source_mm"], 3)),
                        "gate_mm": lim,
                        "margin_mm": round(lim - m["width_mm"], 3)}
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
