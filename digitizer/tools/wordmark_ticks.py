"""Kent's four ticks on Fremont's HOTEL FREMONT wordmark (81 mm Hat): what sews there?

Kent's marked Studio screenshot of 2026-10-13 (15,129 stitches) ticks four small
spots on the bold wordmark: above HOTEL's E, the R's foot, a circle in the M's
middle V, and the foot of the N's diagonal beside the final T. The letters are
Column-lane SATIN, so the small-text switch (`small_text_true_size`) never
reaches them. This names, per tick, every dark-thread thing that sews within
`radius` of it, on the plan and in the file:

- `runs`: plan runs (block, run index, shape, kind, points, jump / trim, first
  and last stitch length) with a needle point inside the radius;
- `records`: the design records (what the machine file holds) of that block
  inside the radius, as contiguous index ranges, with the jumps and trims among
  them and the longest step;
- `max_out_mm`: the furthest dark needle point outside the dark artwork (the
  union of the dark regions' polygons). The Column lane's rails reach about
  0.29 mm out by design (pull compensation), so that is the floor;
- `excess_mm2`: dark thread (each laid segment `THREAD_MM` wide, the needle
  path including needle-down links between runs) further than `PULL_MM` plus
  half a thread outside the artwork, read on a `PX_PER_MM` raster;
  `bare_mm2`: dark artwork inside the window no dark thread covers.

Two arms: `main` (the Studio request as it is today) and `ends_off`
(`lettering_columns_square_ends` and `lettering_columns_inside_connectors`
False, the two flags #922 flipped ON on 2026-10-13, after Kent's render; the
closest reproducible stand-in for what he saw). Fremont is an UNREPRESENTATIVE
fixture: reproduce defects on it, never size a constant on it. Measurement only.

    # one arm (a digitize is ~5 minutes): writes DIR/<arm>.json and DIR/<arm>.pkl
    .venv/Scripts/python -m tools.wordmark_ticks --arm main --out DIR
    .venv/Scripts/python -m tools.wordmark_ticks --arm ends_off --out DIR
    # re-census a saved arm without digitizing (after a change to this tool)
    .venv/Scripts/python -m tools.wordmark_ticks --arm main --reuse --out DIR
    # the table, and the panels (artwork | each arm, 40 px/mm; then the excess map)
    .venv/Scripts/python -m tools.wordmark_ticks --table --out DIR
    .venv/Scripts/python -m tools.wordmark_ticks --panels --out DIR --renders DIR2
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Each tick as a FRACTION of the 2500 x 1345 source artwork (x, y), read off
# Kent's screenshot against the letters, and the radius (mm) read round it.
TICKS = {
    "e_top": ((0.3247, 0.4220), 1.3, "1. above HOTEL's E (top arm, right end)"),
    "r_foot": ((0.5642, 0.5551), 1.3, "2. the R's foot (leg end, foot serif)"),
    "m_v": ((0.6901, 0.5344), 1.3, "3. the M's middle V (vertex)"),
    "n_foot": ((0.8852, 0.5620), 1.3, "4. the N's diagonal foot, before the final T"),
}
ARMS = {
    "main": {},
    "ends_off": {"lettering_columns_square_ends": False,
                 "lettering_columns_inside_connectors": False},
}
DARK_MAX = 100        # a block whose darkest channel is under this is "dark thread"
THREAD_MM = 0.4       # stitchviz.THREAD_MM, the drawn filament
PULL_MM = 0.30        # the lane's rail reach is ~0.29 mm: thread inside it is by design
PX_PER_MM = 40.0


# --- pure helpers (the tests pin these) --------------------------------------

def frac_to_mm(shape_hw, art_bbox, px_per_mm, frac) -> tuple[float, float]:
    """Source-image fraction -> design mm (y down), `fremont_triage.roi_mm`'s
    transform for one point."""
    h, w = shape_hw
    x0, y0, x1, y1 = art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return (frac[0] * w - cx) / px_per_mm, (frac[1] * h - cy) / px_per_mm


def index_groups(idx: list[int]) -> list[list[int]]:
    """Sorted indices -> [first, last] of each contiguous run."""
    out: list[list[int]] = []
    for i in sorted(idx):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def dark_blocks(plan) -> list[int]:
    return [i for i, b in enumerate(plan.blocks) if min(b.rgb) < DARK_MAX]


def block_record_span(stitches: list[dict], block: int) -> tuple[int, int]:
    """[lo, hi) design-record indices of plan block `block`: the records between
    the colour changes either side of it (`adapter.plan_to_design` writes one
    colour record between consecutive blocks)."""
    cc = [i for i, s in enumerate(stitches) if s.get("type") == "color"]
    lo = 0 if block == 0 else cc[block - 1] + 1
    hi = cc[block] if block < len(cc) else len(stitches)
    return lo, hi


def laid_segments(plan, blocks) -> list[tuple[tuple, tuple]]:
    """Every segment dark thread lies along: each run's own steps plus the
    needle-down link from the previous run's end (not across a jump)."""
    segs = []
    for bi in blocks:
        prev = None
        for r in plan.blocks[bi].runs:
            if not r.points:
                continue
            if prev is not None and not r.jump:
                segs.append((prev, r.points[0]))
            segs.extend(zip(r.points[:-1], r.points[1:]))
            prev = r.points[-1]
    return segs


def excess_bare(ink, segs, centre, radius, px_per_mm=PX_PER_MM,
                thread_mm=THREAD_MM, pull_mm=PULL_MM, image=False) -> tuple:
    """(thread area further than pull + half a thread outside `ink`, ink area no
    thread covers), mm², inside the square window of half-size `radius`.
    `image=True` appends the map (BGR): grey ink, dark thread, red excess, blue
    bare ink, green the ink's outline."""
    import cv2
    import numpy as np
    cx, cy = centre
    n = int(round(2 * radius * px_per_mm))
    sub = 4

    def tp(p):
        return (int(round((p[0] - cx + radius) * px_per_mm * (1 << sub))),
                int(round((p[1] - cy + radius) * px_per_mm * (1 << sub))))
    inkr = np.zeros((n, n), np.uint8)
    thr = np.zeros((n, n), np.uint8)
    for poly in getattr(ink, "geoms", [ink]):
        if poly.is_empty:
            continue
        cv2.fillPoly(inkr, [np.array([tp(q) for q in poly.exterior.coords], np.int32)], 255,
                     cv2.LINE_8, sub)
        for hole in poly.interiors:
            cv2.fillPoly(inkr, [np.array([tp(q) for q in hole.coords], np.int32)], 0,
                         cv2.LINE_8, sub)
    tw = max(1, int(round(thread_mm * px_per_mm)))
    reach = radius + 3.0
    for a, b in segs:
        if min(abs(a[0] - cx), abs(b[0] - cx)) > reach or min(abs(a[1] - cy), abs(b[1] - cy)) > reach:
            continue
        cv2.line(thr, tp(a), tp(b), 255, tw, cv2.LINE_8, sub)
    k = 2 * int(round((pull_mm + thread_mm / 2.0) * px_per_mm)) + 1
    grown = cv2.dilate(inkr, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    excess = (thr > 0) & (grown == 0)
    bare = (inkr > 0) & (thr == 0)
    ex, br = float(excess.sum()) / px_per_mm ** 2, float(bare.sum()) / px_per_mm ** 2
    if not image:
        return ex, br
    img = np.full((n, n, 3), 255, np.uint8)
    img[inkr > 0] = (200, 200, 200)
    img[thr > 0] = (40, 40, 40)
    img[excess] = (0, 0, 230)
    img[bare] = (230, 120, 0)
    cnt, _ = cv2.findContours(inkr, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(img, cnt, -1, (0, 190, 0), 1)
    return ex, br, img


def tick_census(plan, regions, design, centre, radius) -> dict:
    """Everything dark that sews within `radius` of `centre` (mm, y down)."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    blocks = dark_blocks(plan)
    ids = {r.shape_id for bi in blocks for r in plan.blocks[bi].runs}
    ink = unary_union([g.polygon for g in regions if g.shape_id in ids]).buffer(0)
    runs = []
    max_out = 0.0
    for bi in blocks:
        for ri, r in enumerate(plan.blocks[bi].runs):
            pts = r.points
            if not pts or not any(math.dist(q, centre) <= radius for q in pts):
                continue
            steps = [math.dist(pts[i - 1], pts[i]) for i in range(1, len(pts))]
            for q in pts:
                if math.dist(q, centre) <= radius:
                    max_out = max(max_out, ink.distance(Point(q)))
            runs.append({"block": bi, "run": ri, "shape": r.shape_id, "kind": r.kind,
                         "points": len(pts), "jump": bool(r.jump), "trim": bool(r.trim),
                         "first_mm": round(steps[0], 2) if steps else 0.0,
                         "last_mm": round(steps[-1], 2) if steps else 0.0,
                         "start": [round(v, 2) for v in pts[0]],
                         "end": [round(v, 2) for v in pts[-1]]})
    st = design["stitches"]
    recs, jumps, trims, longest = [], [], [], 0.0
    for bi in blocks:
        lo, hi = block_record_span(st, bi)
        for i in range(lo, hi):
            s = st[i]
            q = (s["x"] / 10.0, -s["y"] / 10.0)
            if math.dist(q, centre) > radius:
                continue
            recs.append(i)
            t = s.get("type")
            if t == "jump":
                jumps.append(i)
            elif t == "trim":
                trims.append(i)
            elif t == "stitch" and i > lo and st[i - 1].get("type") == "stitch":
                p0 = (st[i - 1]["x"] / 10.0, -st[i - 1]["y"] / 10.0)
                longest = max(longest, math.dist(p0, q))
    ex, bare = excess_bare(ink, laid_segments(plan, blocks), centre, radius)
    return {"centre_mm": [round(v, 2) for v in centre], "radius_mm": radius,
            "runs": runs, "records": index_groups(recs), "n_records": len(recs),
            "jumps": jumps, "trims": trims, "longest_step_mm": round(longest, 2),
            "max_out_mm": round(max_out, 2), "excess_mm2": round(ex, 2),
            "bare_mm2": round(bare, 2)}


# --- digitize / table / panels -----------------------------------------------

def run_arm(arm: str, run: dict | None = None) -> tuple[dict, dict]:
    """Digitize `arm` (or census an already-digitized `run`)."""
    if run is None:
        from tools import fremont_triage as ft
        run = ft.run_arm("main", overrides=ARMS[arm], preflight=True)
    p = run["gen"].p
    s = run["plan"].stats
    out = {"arm": arm, "overrides": ARMS[arm], "stitches": s.stitch_count,
           "trims": s.trims, "jumps": s.jumps, "ticks": {}}
    for name, (frac, radius, _title) in TICKS.items():
        c = frac_to_mm(p.bg_mask.shape, p.art_bbox, p.px_per_mm, frac)
        out["ticks"][name] = tick_census(run["plan"], run["result"].regions, run["design"],
                                         c, radius)
    return out, run


def table(rows: dict) -> str:
    lines = ["| tick | arm | dark runs there (kind) | records | jumps / trims | longest step mm "
             "| max out mm | excess mm2 | bare mm2 |", "|---|---|---|---|---|---|---|---|---|"]
    for name, (_f, _r, title) in TICKS.items():
        for arm, row in rows.items():
            t = row["ticks"][name]
            kinds = ", ".join(f"r{r['run']} {r['kind']}" for r in t["runs"])
            recs = ", ".join(f"{a}-{b}" for a, b in t["records"])
            lines.append(f"| {title} | {arm} | {kinds} | {recs} | {len(t['jumps'])} / "
                         f"{len(t['trims'])} | {t['longest_step_mm']} | {t['max_out_mm']} | "
                         f"{t['excess_mm2']} | {t['bare_mm2']} |")
    return "\n".join(lines) + "\n"


def _artwork_crop(p, frac, radius, size_px):
    """The prep raster over the same mm window the thread crops show, sampled
    through the prep's own transform (so artwork and thread line up)."""
    import numpy as np
    h, w = p.bg_mask.shape
    x0, y0, x1, y1 = p.art_bbox
    acx, acy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    cx, cy = frac_to_mm(p.bg_mask.shape, p.art_bbox, p.px_per_mm, frac)
    t = (np.arange(size_px) + 0.5) / size_px * 2 * radius - radius
    xi = np.clip(((cx + t) * p.px_per_mm + acx).astype(int), 0, w - 1)
    yi = np.clip(((cy + t) * p.px_per_mm + acy).astype(int), 0, h - 1)
    return np.ascontiguousarray(p.rgb[yi[:, None], xi[None, :]][..., ::-1])


def panels(out: Path, renders: Path) -> list[Path]:
    """Per tick: artwork | each arm (stitchviz, 40 px/mm, shown 2x), and below
    each arm the excess map (grey ink, dark thread, red = past pull + half a
    thread, blue = bare ink)."""
    import pickle
    import cv2
    import numpy as np
    from tools import fremont_triage as ft
    renders.mkdir(parents=True, exist_ok=True)
    runs = {}
    for arm in ARMS:
        pk = out / f"{arm}.pkl"
        if pk.exists():
            runs[arm] = pickle.loads(pk.read_bytes())       # our own scratch file
    from shapely.ops import unary_union
    rendered = {arm: ft._render(run["design"], PX_PER_MM) for arm, run in runs.items()}
    written = []
    for name, (frac, radius, title) in TICKS.items():
        cols, maps = [], []
        for arm, run in runs.items():
            p, plan = run["gen"].p, run["plan"]
            cx, cy = frac_to_mm(p.bg_mask.shape, p.art_bbox, p.px_per_mm, frac)
            img, to_px = rendered[arm]
            crop = ft._crop(img, to_px, (cx - radius, cy - radius, cx + radius, cy + radius), 0.0)
            crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            t = json.loads((out / f"{arm}.json").read_text())["ticks"][name]
            cols.append(ft._label(crop, f"{arm}: {t['n_records']} records, max out "
                                        f"{t['max_out_mm']} mm"))
            blocks = dark_blocks(plan)
            ids = {r.shape_id for bi in blocks for r in plan.blocks[bi].runs}
            ink = unary_union([g.polygon for g in run["result"].regions
                               if g.shape_id in ids]).buffer(0)
            _e, _b, m = excess_bare(ink, laid_segments(plan, blocks), (cx, cy), radius, image=True)
            m = cv2.resize(m, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_NEAREST)
            maps.append(ft._label(m, f"{arm}: excess {t['excess_mm2']} / bare {t['bare_mm2']} mm2"))
        run = next(iter(runs.values()))
        src = _artwork_crop(run["gen"].p, frac, radius, cols[0].shape[0] - 22)
        top = ft._hstack([ft._label(src, "artwork")] + cols)
        bottom = ft._hstack([np.full((maps[0].shape[0], src.shape[1], 3), 255, np.uint8)] + maps)
        w = max(top.shape[1], bottom.shape[1])
        both = np.vstack([np.pad(top, ((0, 6), (0, w - top.shape[1]), (0, 0)), constant_values=255),
                          np.pad(bottom, ((0, 0), (0, w - bottom.shape[1]), (0, 0)), constant_values=255)])
        panel = ft._label(both, title + " (thread 40 px/mm shown 2x; red past pull, blue bare)")
        path = renders / f"tick_{name}.png"
        cv2.imwrite(str(path), panel)
        written.append(path)
    return written


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", choices=list(ARMS))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reuse", action="store_true",
                    help="census DIR/<arm>.pkl instead of digitizing again")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--panels", action="store_true")
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.arm:
        import pickle
        pk = a.out / f"{a.arm}.pkl"
        prior = pickle.loads(pk.read_bytes()) if (a.reuse and pk.exists()) else None
        row, run = run_arm(a.arm, prior)       # `prior` is our own scratch file
        (a.out / f"{a.arm}.json").write_text(json.dumps(row, indent=1))
        (a.out / f"{a.arm}.pkl").write_bytes(pickle.dumps(run))
        print(json.dumps({k: v for k, v in row.items() if k != "ticks"}))
    if a.table:
        rows = {arm: json.loads((a.out / f"{arm}.json").read_text())
                for arm in ARMS if (a.out / f"{arm}.json").exists()}
        print(table(rows))
    if a.panels:
        for p in panels(a.out, a.renders or a.out / "renders"):
            print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
