#!/usr/bin/env python
"""Does the professional CAP his design's outer silhouette? Measured on his files.

Quality review 2026-09-08 item 14. `cfg.edge_cap` is built in two styles and
default OFF, held by ROADMAP gate 1 with the note *"a sew-out settles which
cap, if either"*. The review proposes a cheaper source first: the pro's own
stitch files, the evidence class that settled fill row spacing. Reading a
decision a digitizer with a machine already made is not inventing a physical
constant — see the gate's own test in ROADMAP ("ask which kind it is").

THE STATISTIC IS THE ONE ALREADY QUOTED ABOUT OUR OWN WORK. MASTER_SCOPE
defect 19 says Kent's icon leaves **100% of its 293.2 mm outer silhouette
uncovered at 1.0 mm**, against 0.0% on the glyph edge he rated flawless. So
this measures exactly that, on `testdata/reference/*.dst`:

  * the design's area fills, recovered from penetration geometry
    (`border_pro.area_fills` — `classify()` is never consulted, see that
    module's B1), plus every satin COLUMN and every non-fill run;
  * the OUTER boundary of all of that together — the design/fabric boundary,
    which is what defect 19 is about and what no per-shape border reaches;
  * as COVER, only the LINEAR elements: satin columns and non-fill runs, each
    at its own thread footprint. A fill's own rows are deliberately NOT cover
    — a row ENDING on the boundary is the defect, not a cap;
  * the share of silhouette length with no cover within `--tol` mm.

So where the outermost thing is a column or a traced run, the edge reads
capped; where it is a fill row's end, it reads open. That is the distinction
`edge_cap` exists for, and it is measured the same way on both sides:
`--ours FIXTURE` digitizes one of our own fixtures, exports it to DST and
reads it back through this same function, so the pro's number and ours are
never two different instruments.

A LOW number means the pro caps his silhouette and `edge_cap` has a precedent.
A HIGH number means he leaves it open exactly as we do, and the flag is a
preference rather than a correction — which is the more useful answer, because
it is the one that would stop us spending 12-57% more stitches on a habit
nobody in the trade has.

    .venv/bin/python tools/pro_silhouette.py [file.dst ...] [--tol MM]
    .venv/bin/python tools/pro_silhouette.py --ours becker fremont [--width MM]

Defaults to every `.dst` under `testdata/reference/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np                                             # noqa: E402
from shapely.geometry import LineString, MultiLineString        # noqa: E402
from shapely.ops import unary_union                             # noqa: E402

from border_pro import (area_fills, columns, med, rail_metrics,  # noqa: E402
                        spine_of)
from study_pro import load_runs                                 # noqa: E402

REFERENCE = ROOT / "testdata" / "reference"

# Half a 40-weight thread, the same half-width `stage6_border`'s coverage
# reading uses. Not a fabric constant: it is how wide the thread draws.
THREAD_HALF_MM = 0.20
# How far from the silhouette a cover may sit and still count as covering it.
# 1.0 mm is MASTER_SCOPE defect 19's own tolerance, kept so the pro's number
# and ours are the same measurement.
DEFAULT_TOL_MM = 1.0
# Segments longer than this inside a run are travel, not stitching, and must
# not be painted as cover (`border_pro._mask` drops them for the same reason).
TRAVEL_MM = 6.0


def _cover(runs, fill_idx: set[int]):
    """Everything that could CAP an edge: a line of stitching ALONG it.

    Two sources, and the second is the one a first version got wrong. A fill
    run's own rows cross its boundary and end there — that is the defect, not
    a cap — so a fill run is not painted as cover wholesale. But a satin
    column frequently lives in the SAME RUN as a large fill (`border_pro`'s
    own report shows run#6 of the Becker chest file being both a 542.7 mm2
    area fill and the host of eleven columns, three of them tracking a fill
    edge), and skipping the whole run would hide exactly the cap being looked
    for. So:

      * every satin COLUMN recovered from every run, spine buffered by its
        own half width — a satin cap, wherever it lives;
      * every segment of runs that are NOT area fills — a bean or run cap.
    """
    segs = []
    for i, r in enumerate(runs):
        pts = r["pts"]
        cols, _toks, _cnts = columns(pts)     # -> (spans, tokens, counts)
        for s0, s1 in cols:
            seg = pts[s0:s1 + 1]
            if len(seg) < 6:
                continue
            spine = spine_of(seg)
            if len(spine) < 2:
                continue
            # `rail_metrics` returns the per-pair spans; a column's width is
            # their median (its own docstring: every consecutive pair spans
            # the column).
            w = med(rail_metrics(seg)[0]) or 0.0
            half = max(THREAD_HALF_MM, w / 2.0)
            segs.append(LineString(spine).buffer(half))
        if i in fill_idx:
            continue
        for a, b in zip(pts, pts[1:]):
            d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
            if 1e-9 < d <= TRAVEL_MM:
                segs.append(LineString([a, b]).buffer(THREAD_HALF_MM))
    if not segs:
        return None
    return unary_union(segs)


def silhouette(path: Path, tol_mm: float = DEFAULT_TOL_MM) -> dict:
    runs, _n_trim, _n_jump = load_runs(path)
    fills = area_fills(runs)
    if not fills:
        return {"file": path.name, "fills": 0}

    cover = _cover(runs, {f["idx"] for f in fills})

    # The design's outline: fills AND linear elements together, outer boundary
    # only. Interior holes are counters and enclosed background — a different
    # question; defect 19 is about the design/fabric boundary.
    pieces = [p for f in fills for p in f["polys"]]
    if cover is not None:
        pieces.append(cover)
    union = unary_union(pieces)
    parts = [g for g in getattr(union, "geoms", [union]) if g.geom_type == "Polygon"]
    if not parts:
        return {"file": path.name, "fills": len(fills)}
    outer = unary_union([LineString(p.exterior.coords) for p in parts])

    total = float(outer.length)
    if cover is None or total <= 0:
        return {"file": path.name, "fills": len(fills), "silhouette_mm": total,
                "uncovered_pct": 100.0 if total else 0.0, "parts": len(parts)}

    # Covered = within `tol` of a cover. Measured on the boundary itself by
    # intersecting it with the cover grown by the tolerance, so the answer is
    # a LENGTH share and not a point-sample estimate.
    covered = float(outer.intersection(cover.buffer(tol_mm)).length)
    return {
        "file": path.name,
        "fills": len(fills),
        "parts": len(parts),
        "silhouette_mm": total,
        "covered_mm": covered,
        "uncovered_pct": 100.0 * (1.0 - covered / total),
    }


def ours(name: str, width_mm: float = 80.0, edge_cap: str = "none") -> Path:
    """Digitize one of our fixtures and write it out as DST.

    The point is that the answer then comes from the SAME reader as the pro's
    — the comparison this whole tool exists for is worthless if our number and
    his come from two instruments. `fill_exposure.SHORT` supplies the Studio
    config each fixture is normally read at.
    """
    import tempfile
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core.export import write_dst
    from fill_exposure import SHORT

    rel, kw = SHORT.get(name, (name, {}))
    _result, plan = digitize(ROOT / "testdata" / rel,
                             PipelineConfig(target_width_mm=width_mm,
                                            edge_cap=edge_cap, **kw))
    stem = Path(rel).stem + ("" if edge_cap == "none" else f"__{edge_cap}")
    out = Path(tempfile.mkdtemp(prefix="pro_silhouette_")) / f"{stem}.dst"
    path = write_dst(plan, out, label="EMBBOT")
    print(f"    ({name} {edge_cap}: {plan.stats.stitch_count} st, "
          f"{plan.stats.trims} trims)")
    return path


def main(argv: list[str]) -> int:
    tol = DEFAULT_TOL_MM
    if "--tol" in argv:
        tol = float(argv[argv.index("--tol") + 1])
    width = 80.0
    if "--width" in argv:
        width = float(argv[argv.index("--width") + 1])
    cap = "none"
    consumed = set()
    for opt in ("--tol", "--width", "--edge-cap"):
        if opt in argv:
            consumed.add(argv.index(opt) + 1)
    if "--edge-cap" in argv:
        cap = argv[argv.index("--edge-cap") + 1]
    if "--ours" in argv:
        # `consumed` matters: an option's VALUE is not a fixture name, and
        # without this `--edge-cap bean` digitizes a fixture called "bean".
        picks = [a for i, a in enumerate(argv)
                 if i > argv.index("--ours") and not a.startswith("--")
                 and i not in consumed]
        paths = [ours(n, width, cap) for n in picks]
        if not paths:
            print("--ours needs at least one fixture name")
            return 1
    else:
        names = [a for a in argv if not a.startswith("--") and a.endswith(".dst")]
        paths = [Path(n) for n in names] or sorted(REFERENCE.glob("*.dst"))
    if not paths:
        print(f"no .dst files (looked in {REFERENCE})")
        return 1

    print(f"{'file':52s} {'fills':>5s} {'parts':>5s} {'silhouette':>10s} "
          f"{'covered':>9s} {'UNCOVERED':>9s}")
    rows = []
    for p in paths:
        r = silhouette(p, tol)
        rows.append(r)
        if not r.get("fills"):
            print(f"{p.name[:52]:52s} {'-':>5s}  no area fill recovered")
            continue
        print(f"{p.name[:52]:52s} {r['fills']:5d} {r['parts']:5d} "
              f"{r['silhouette_mm']:9.1f}mm {r['covered_mm']:8.1f}mm "
              f"{r['uncovered_pct']:8.1f}%")
    good = [r for r in rows if r.get("fills")]
    if good:
        share = [r["uncovered_pct"] for r in good]
        print(f"\npooled: {len(good)} files, silhouette "
              f"{sum(r['silhouette_mm'] for r in good):.0f} mm, "
              f"uncovered {min(share):.1f}-{max(share):.1f}% "
              f"(median {sorted(share)[len(share) // 2]:.1f}%), tol {tol} mm")
        print("compare: Kent's icon reads 100% uncovered at 1.0 mm "
              "(MASTER_SCOPE defect 19), the glyph edge he rated flawless 0.0%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
