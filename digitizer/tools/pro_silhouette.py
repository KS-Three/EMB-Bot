#!/usr/bin/env python
"""How much of a design's FILL EDGE has thread laid ALONG it — his, and ours.

Quality review 2026-09-08 item 14, third derivation. `cfg.edge_cap` is built in
two styles and default OFF, and MASTER_SCOPE defect 19's reason is that on
Kent's icon every tatami row ends in open air. The question is whether the
trade does something about that, and how much of our own edge is genuinely
open.

## Read this before trusting a number out of here

**The two sides are NOT measured the same way, and the first two versions of
this tool were wrong for pretending they could be.**

  * **Ours is exact.** We own the plan, so every run carries the KIND that
    made it. `stage7_sequence._sewn_linear_cover` — the same function the
    edge cap's own gate uses — unions every satin, border, bean and run-tier
    polyline at one thread width, and a fill's rows are never in it. The
    silhouette is the outer boundary of the union of the regions that sewed.
    Nothing is inferred.

  * **His is a LOWER BOUND, through a validated test.** A stitch file carries
    no kinds, and separating a cap from a big tatami's row-turn phases is
    exactly the ambiguity `border_pro`'s own B1 and B4 warnings are about. So
    this does not guess: it counts only the columns `border_pro` already flags
    as FILL-EDGE BORDERS (a spine tracking a fill's boundary for at least
    `EDGE_FRAC` of its samples within `EDGE_NEAR_MM`), and credits each with
    the length it actually tracks. Real border satin that the test misses is
    counted as absent, so the figure can only understate him.

**Version 1 read the pro 76.7-100% uncovered** by building cover from whole
runs and skipping any run that was an area fill — in this corpus a run is
routinely both a fill and the host of the columns bordering it.
**Version 2 read him 0.5-2.2% uncovered** by adding every column phase back,
including a tatami's own row turns; on OUR side that same rule called Hotel
Fremont 0.0% uncovered when the engine says its outer edge has no linear
stitch on it at all — 0.0 mm of 203.7. The tell was that the edge-cap gate,
which reads real run kinds, saved Fremont nothing while the tool claimed it
needed nothing. **Two instruments disagreeing is the finding; publish neither
until they are one measurement or two clearly labelled ones.**

    .venv/bin/python tools/pro_silhouette.py                 # the pro's files
    .venv/bin/python tools/pro_silhouette.py --ours becker fremont [--edge-cap satin]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from shapely.geometry import LineString                        # noqa: E402
from shapely.ops import unary_union                            # noqa: E402

from digitizer_core import machine                             # noqa: E402

REFERENCE = ROOT / "testdata" / "reference"

# `border_runs`' own host margin: how far from the edge a stitch still counts
# as standing on it. The edge cap's gate uses the same number, so "covered"
# means the same thing to the instrument and to the engine.
DEFAULT_TOL_MM = machine.BORDER_HOST_MARGIN_MM


# --------------------------------------------------------------------- ours --

def ours(name: str, width_mm: float = 80.0, edge_cap: str = "none",
         tol_mm: float = DEFAULT_TOL_MM) -> dict:
    """Exact: the plan's own run kinds against the plan's own silhouette."""
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core.stage7_sequence import _sewn_linear_cover
    from fill_exposure import SHORT

    rel, kw = SHORT.get(name, (name, {}))
    result, plan = digitize(ROOT / "testdata" / rel,
                            PipelineConfig(target_width_mm=width_mm,
                                           edge_cap=edge_cap, **kw))
    polys = [r.polygon for r in result.regions if r.meta.get("stitched", True)]
    if not polys:
        return {"name": name, "silhouette_mm": 0.0}
    union = unary_union(polys)
    parts = [g for g in getattr(union, "geoms", [union]) if g.geom_type == "Polygon"]
    outer = unary_union([LineString(p.exterior.coords) for p in parts])
    cover = _sewn_linear_cover(plan.blocks)
    total = float(outer.length)
    covered = 0.0 if cover is None else float(
        outer.intersection(cover.buffer(tol_mm)).length)
    return {
        "name": name,
        "parts": len(parts),
        "silhouette_mm": total,
        "covered_mm": covered,
        "uncovered_pct": 100.0 * (1.0 - covered / total) if total else 0.0,
        "stitches": plan.stats.stitch_count,
        "trims": plan.stats.trims,
    }


# ---------------------------------------------------------------------- his --

def pro(path: Path) -> dict:
    """A LOWER bound: only columns `border_pro` certifies as fill-edge borders."""
    from border_pro import area_fills, study

    recs, fills, _n_trim, _dst = study(path)
    if not fills:
        return {"name": path.name, "fills": 0}
    # `area_fills` hands back whatever `_polys` recovered, which for a badge
    # with counters is a MultiPolygon — walk the parts rather than assuming.
    edge_len = 0.0
    for f in fills:
        for poly in f["polys"]:
            for part in getattr(poly, "geoms", [poly]):
                if part.geom_type != "Polygon":
                    continue
                edge_len += float(LineString(part.exterior.coords).length)
                edge_len += sum(float(LineString(r.coords).length)
                                for r in part.interiors)
    borders = [r for r in recs if r.get("fill_edge")]
    # Each flagged column is credited with the length it actually TRACKS: its
    # own spine length times `near`, the fraction of samples on the boundary.
    tracked = 0.0
    for r in borders:
        spine = r.get("_spine") or []
        if len(spine) > 1:
            # `near_fill`, not `near` — `border_pro` stores the tracking
            # fraction under that name on the record it keeps.
            tracked += float(LineString(spine).length) * float(r.get("near_fill", 0.0))
    return {
        "name": path.name,
        "fills": len(fills),
        "columns": len(recs),
        "edge_borders": len(borders),
        "fill_edge_mm": edge_len,
        "tracked_mm": tracked,
        "bordered_pct": 100.0 * tracked / edge_len if edge_len else 0.0,
        "_unused": area_fills,
    }


def main(argv: list[str]) -> int:
    tol = DEFAULT_TOL_MM
    if "--tol" in argv:
        tol = float(argv[argv.index("--tol") + 1])
    width = 80.0
    if "--width" in argv:
        width = float(argv[argv.index("--width") + 1])
    cap = "none"
    if "--edge-cap" in argv:
        cap = argv[argv.index("--edge-cap") + 1]
    consumed = {argv.index(o) + 1 for o in ("--tol", "--width", "--edge-cap")
                if o in argv}

    if "--ours" in argv:
        picks = [a for i, a in enumerate(argv)
                 if i > argv.index("--ours") and not a.startswith("--")
                 and i not in consumed]
        if not picks:
            print("--ours needs at least one fixture name")
            return 1
        print(f"OURS (exact, from the plan's run kinds) edge_cap={cap} "
              f"width={width:.0f} mm tol={tol} mm")
        print(f"{'fixture':14s} {'parts':>5s} {'silhouette':>11s} {'covered':>10s} "
              f"{'UNCOVERED':>9s} {'stitches':>9s} {'trims':>6s}")
        rows = [ours(n, width, cap, tol) for n in picks]
        for r in rows:
            if not r.get("silhouette_mm"):
                print(f"{r['name'][:14]:14s}  nothing sewed")
                continue
            print(f"{r['name'][:14]:14s} {r['parts']:5d} {r['silhouette_mm']:10.1f}mm "
                  f"{r['covered_mm']:9.1f}mm {r['uncovered_pct']:8.1f}% "
                  f"{r['stitches']:9d} {r['trims']:6d}")
        good = [r for r in rows if r.get("silhouette_mm")]
        if good:
            share = sorted(r["uncovered_pct"] for r in good)
            print(f"\npooled: {len(good)} fixtures, "
                  f"{sum(r['silhouette_mm'] for r in good):.0f} mm of silhouette, "
                  f"uncovered {share[0]:.1f}-{share[-1]:.1f}% "
                  f"(median {share[len(share) // 2]:.1f}%)")
        return 0

    names = [a for a in argv if not a.startswith("--") and a.endswith(".dst")]
    paths = [Path(n) for n in names] or sorted(REFERENCE.glob("*.dst"))
    if not paths:
        print(f"no .dst files (looked in {REFERENCE})")
        return 1
    print("PRO (a LOWER bound — only columns border_pro certifies as fill-edge "
          "borders; see the module docstring)")
    print(f"{'file':52s} {'fills':>5s} {'cols':>5s} {'edge':>5s} {'fill edge':>10s} "
          f"{'tracked':>9s} {'BORDERED':>9s}")
    rows = [pro(p) for p in paths]
    for r in rows:
        if not r.get("fills"):
            print(f"{r['name'][:52]:52s}  no area fill recovered")
            continue
        print(f"{r['name'][:52]:52s} {r['fills']:5d} {r['columns']:5d} "
              f"{r['edge_borders']:5d} {r['fill_edge_mm']:9.1f}mm "
              f"{r['tracked_mm']:8.1f}mm {r['bordered_pct']:8.1f}%")
    good = [r for r in rows if r.get("fills")]
    if good:
        share = sorted(r["bordered_pct"] for r in good)
        print(f"\npooled: {len(good)} files, "
              f"{sum(r['fill_edge_mm'] for r in good):.0f} mm of fill edge, "
              f"at least {share[0]:.1f}-{share[-1]:.1f}% bordered "
              f"(median {share[len(share) // 2]:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
