#!/usr/bin/env python
"""Defect 5 re-measured: satin-vs-fill routing against the pro, on today's main.

MEASUREMENT ONLY. Every paired job in `tools.pro_baseline.JOBS` is digitized
ONCE per arm with the Studio's request at the pro's width and garment
(`pro_pair.digitize`, `--set KEY=JSON` laid over it), and the one plan feeds
three readings, so they cannot disagree about what was sewn:

  job kappa     `pro_parity.scorecard`'s stitch-type kappa (satin / fill / run,
                2 mm cells over the shared solid area) -- `pro_baseline.kappas`,
                byte for byte. CHANCE-CORRECTED ONLY (ROADMAP gate 4); the
                chance floor rides beside it.
  oracle        the same cells, with every cell inside one of OUR regions
                relabelled to the pro's majority type in that region: the
                ceiling a perfect per-region classifier reaches on our
                segmentation (`satin-gate-attribution-2026-08-16.md` §4's
                76.6%, now as a kappa). Its gap above `job kappa` is what
                routing can still buy; the gap below 1 is segmentation.
  straddle      cells in regions under 75% one pro type, split by
                `splitprobe.classify_straddle` (ring / split / speckle), and
                the minority cells' connected-component sizes -- the test of
                `segmentation-alignment-2026-08-17.md`'s "speckle is grid
                noise" reading, beside the pro's own map read against itself
                half a cell off (`pro_self_kappa`: what 2 mm cells cost a
                PERFECT engine; also at a quarter cell).
  shape kappa   `tier_census`'s reader on the pro's file per OUR shape
                (FILL / SATIN / SPLIT / RUN; BAR left out as undecidable)
                against our tier from the PLAN, where it is known; grounds
                (a shape with another sewn shape inside) left out, since the
                pro's pieces sewn on them read as their tier. Read it by AREA:
                the same reader scores our own plan ~0.2 by count
                (`reader_on_ours`), which is its noise on small shapes.

    python -m tools.satin_fill_census digitize --runs DIR [--set KEY=JSON ...] [--only SLUG ...]
                                     # --set extra.KEY=JSON: a cfg.extra flag (pro_pair.config)
    python -m tools.satin_fill_census measure --runs DIR [--only SLUG ...]
    python -m tools.satin_fill_census table --runs DIR [--vs DIR2]
    python -m tools.satin_fill_census flip --runs OFF --vs ON              # a flag's two arms
    python -m tools.satin_fill_census render --runs OFF --vs ON --out docs/renders/NAME
    python -m tools.satin_fill_census oracle-split --runs DIR              # after `measure`; C3's bound
    python -m tools.satin_fill_census attribute --runs DIR                 # after `measure`; where C3's gain sits
    python -m tools.satin_fill_census edge-bands --runs DIR                # after `measure`; the cut blobs' widths

`oracle-split` (2026-11-06, lagging-areas C3) is the per-region oracle one level
finer: each of OUR regions is cut along the pro's minority-type blobs of >= 10
connected cells, each part takes the pro's type there, and the cells are re-scored
with the same `_kappa_of`. It READS the pro's blobs, so it is a maximum, not
something inference from flat art could reach. It writes `DIR/oracle_split.json`.

`attribute` (2026-11-07) splits that gain per job into the per-region relabel and
the blob cut, scores the blobs alone on today's routing, attributes the cut to
regions and to each blob's layering pattern (keyline / halo / band / contained / edge,
and the pro's thread colour against the ground's), with region-cluster bootstrap
95% intervals on every kappa. It writes `DIR/attribution.json`.

`edge-bands` (2026-11-07) takes the regions that carry the cut term and records, per
blob and per region, the band width in mm, whether it is a rim, and the region's
`border_by_size` tier; then scores a width-band predictor (satin up to the engine's
5 mm satin ceiling, fill over; fixed before any width was read) against the pro's
type on the blobs' cells: chance-corrected kappa, its floor, and a region-cluster
bootstrap 95% interval. It writes `DIR/edge_bands.json`.

`digitize` writes `DIR/<slug>/{ours.dst, design.json, ours.json}`; `measure`
writes `DIR/census.json`; `render` writes OFF | ON crops round every shape whose
tier moved to `--out` and the pro's crop to gitignored `pro_renders/` (Kent
2026-10-27, `tools.pro_renders`). The pro files are gitignored third-party files
(`EMB_SCRATCH_KENT`, `EMB_BRIDGE_PRO`; `tools/pro_baseline.py`). Nothing here
writes a pro render under docs/; the doc it feeds carries numbers only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")   # the test env's IPP path (tests/conftest.py)

DIGITIZER = Path(__file__).resolve().parent.parent
for p in (str(DIGITIZER), str(DIGITIZER / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

PURITY = 0.75           # splitprobe / gateprobe's straddle threshold
HALF_CELL_MM = 1.0      # the pro read against itself this far off: 2 mm cells' own noise
SATIN_TIERS = {"SATIN": "satin", "SPLIT": "satin", "FILL": "fill", "RUN": "run"}


# ------------------------------------------------------------------ digitize
def digitize(runs: Path, slugs: list[str], extra: dict) -> None:
    from digitizer_core.export import write_dst
    from digitizer_core.preflight import run_preflight
    from tools import border_census as bc
    from tools import pro_pair
    from tools.pro_baseline import JOBS, resolve
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "arm.json").write_text(json.dumps({"set": extra}), encoding="utf-8")
    for s in slugs:
        out = runs / s
        if (out / "plan.json").exists():           # written last: a killed run leaves none
            print(s, "cached", flush=True)
            continue
        garment, width, art, pro_dst, *_ = JOBS[s]
        d = pro_pair.digitize(resolve(art), width, garment, extra or None)
        out.mkdir(parents=True, exist_ok=True)
        write_dst(d.plan, out / "ours.dst")
        (out / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
        # tier_census's cache, from the SAME plan (its own digitize would be a second run)
        bc.write_ours(out, s, garment, width, resolve(pro_dst), resolve(art), d.result, d.plan, d.secs)
        # bare cloth the way the flag's own guard test reads it (preflight's uncovered)
        m = run_preflight(d.result, d.plan, d.cfg, image=str(resolve(art)))["metrics"]
        (out / "plan.json").write_text(json.dumps({
            "stitches": d.plan.stats.stitch_count, "trims": d.plan.stats.trims, "secs": round(d.secs, 1),
            "uncovered_total_mm2": m.get("uncovered_total_mm2"),
            "uncovered_worst_mm2": m.get("uncovered_worst_mm2")}), encoding="utf-8")
        print(s, d.plan.stats.stitch_count, d.plan.stats.trims, f"{d.secs:.0f}s",
              "bare", m.get("uncovered_total_mm2"), flush=True)


# ------------------------------------------------------------------- kappas
def _kappa_of(pt, ot) -> tuple[float, float]:
    """scorecard's own corrected sttype: (kappa, chance) over two equal-length type arrays."""
    from tools.pro_parity import scorecard
    if pt.size == 0:
        return 0.0, 0.0
    raw = float((pt == ot).mean())
    ch = scorecard.type_chance(pt, ot)
    return scorecard.chance_correct(raw, ch), ch


def _components(mask) -> list[int]:
    import cv2
    import numpy as np
    n, lab = cv2.connectedComponents(mask.astype(np.uint8), connectivity=4)
    return [int((lab == k).sum()) for k in range(1, n)]


def _cell_grids(slug: str, runs: Path) -> dict:
    """The cell grid `cell_census` and `oracle_split_job` share: the pro's and our
    type maps (`pt`, `ot`), the graded population (`tboth`), and `owner` (the
    SMALLEST sewn region over each cell, -1 where none), all on one grid."""
    import numpy as np
    import shapely.wkt
    from shapely.affinity import translate
    from tools.pro_parity import scorecard
    from tools.pro_parity.splitprobe import _cells_of

    work = runs / slug / "score" / slug                 # written by pro_baseline.kappas
    _r, pro, _s, _t = scorecard.load_side(work, "pro", slug)
    _r, our, _s, _t = scorecard.load_side(work, "ours", slug)
    dx, dy, _iou = scorecard.register(pro, our, scorecard.bounds(pro, our))
    our_r = scorecard.shifted(our, dx, dy)
    bb = scorecard.bounds(pro, our_r)
    pa, pt, _ = scorecard.cell_stats(pro, bb)
    oa, ot, _ = scorecard.cell_stats(our_r, bb)
    _cov, sp, so, _d = scorecard.coverage_component(pro, our_r, bb, scorecard.load_blocks(work, "pro"),
                                                    scorecard.load_blocks(work, "ours"))
    shared = scorecard.solid_cells(sp & so, bb)
    h = min(pa.shape[0], shared.shape[0]); w = min(pa.shape[1], shared.shape[1])
    both = np.zeros(pa.shape, bool)
    both[:h, :w] = shared[:h, :w]
    both &= ~np.isnan(pa) & ~np.isnan(oa)
    tboth = both & (pt >= 0) & (ot >= 0)

    info = json.loads((runs / slug / "ours.json").read_text(encoding="utf-8"))
    # A cell belongs to the SMALLEST sewn region over it. Regions overlap on
    # purpose (an under-fill silhouette, a patch ground, Fremont's 2,137 mm2
    # field under its letters): taken in list order the ground claimed every
    # cell and the "oracle" fell below the engine it is the ceiling of. The
    # smallest is the one sewn on top, which is the thread the cell shows.
    polys = []
    for k, r in enumerate(info["regions"]):
        if not any(key.split(":")[0] in ("fill", "satin", "run", "bean", "border")
                   for key in (r.get("kinds") or {})):
            continue                                    # never becomes thread
        poly = shapely.wkt.loads(r["wkt"])
        if poly.is_empty:
            continue
        if not poly.is_valid:
            poly = poly.buffer(0)
        polys.append((poly.area, k, poly))
    owner = np.full(pt.shape, -1, int)
    for _a, k, poly in sorted(polys, key=lambda t: t[0], reverse=True):
        for c in _cells_of(translate(poly, dx, dy), bb, pt.shape):
            owner[c] = k                                # smaller ones overwrite
    return {"scorecard": scorecard, "pro": pro, "bb": bb, "dx": dx, "dy": dy, "pt": pt, "ot": ot,
            "tboth": tboth, "owner": owner, "info": info, "polys": polys}


def cell_census(slug: str, runs: Path) -> dict:
    """job kappa, oracle kappa, straddle anatomy and the pro's half-cell self kappa."""
    import numpy as np
    from tools.pro_parity.splitprobe import classify_straddle

    g = _cell_grids(slug, runs)
    scorecard, pro, bb, dx, dy = g["scorecard"], g["pro"], g["bb"], g["dx"], g["dy"]
    pt, ot, tboth, owner, info, polys = g["pt"], g["ot"], g["tboth"], g["owner"], g["info"], g["polys"]
    oracle = ot.copy()
    shapes = []
    for _a, k, _poly in sorted(polys, key=lambda t: t[1]):
        r = info["regions"][k]
        cells = [tuple(c) for c in np.argwhere(owner == k)]
        graded = [c for c in cells if tboth[c]]
        if not graded:
            continue
        hist = Counter(int(pt[c]) for c in graded)
        dom, n_dom = hist.most_common(1)[0]
        for c in cells:
            if pt[c] >= 0:
                oracle[c] = dom
        # straddle anatomy on the graded cells of this region
        i0 = min(i for i, _ in graded); i1 = max(i for i, _ in graded)
        j0 = min(j for _, j in graded); j1 = max(j for _, j in graded)
        grid = np.full((i1 - i0 + 1, j1 - j0 + 1), -1, int)
        for i, j in graded:
            grid[i - i0, j - j0] = pt[i, j]
        minority = (grid >= 0) & (grid != dom)
        sizes = _components(minority)
        meta = r.get("meta") or {}
        shapes.append({"id": r["id"], "cells": len(graded), "purity": round(n_dom / len(graded), 3),
                       "pattern": classify_straddle(grid), "pro_dom": dom,
                       "ours_dom": Counter(int(ot[c]) for c in graded).most_common(1)[0][0],
                       "minority_sizes": sizes,
                       "lettering": any(k2 in meta for k2 in
                                        ("text_cluster_id", "lettering_group", "bean_letter", "small_text_stray"))})

    jk, jc = _kappa_of(pt[tboth], ot[tboth])
    ok, oc = _kappa_of(pt[tboth], oracle[tboth])
    in_shape = tboth & (owner >= 0)

    # the pro against himself a little off: what 2 mm cells and a registration
    # error that size cost a PERFECT engine (the same population rule as tboth)
    def self_kappa(off):
        _pa2, pt2, _ = scorecard.cell_stats(scorecard.shifted(pro, off, off), bb)
        hh = min(pt.shape[0], pt2.shape[0]); ww = min(pt.shape[1], pt2.shape[1])
        a, b = pt[:hh, :ww], pt2[:hh, :ww]
        m = (a >= 0) & (b >= 0)
        return _kappa_of(a[m], b[m])
    sk, sc = self_kappa(HALF_CELL_MM)
    qk, _qc = self_kappa(HALF_CELL_MM / 2)

    return {"job_kappa": round(jk, 3), "job_chance": round(jc, 3), "type_cells": int(tboth.sum()),
            "oracle_kappa": round(ok, 3), "oracle_chance": round(oc, 3),
            "cells_in_regions": int(in_shape.sum()),
            "pro_self_kappa": round(sk, 3), "pro_self_chance": round(sc, 3), "pro_self_kappa_half": round(qk, 3),
            "registration_mm": [round(dx, 2), round(dy, 2)], "shapes": shapes}


#: the pro's minority-type blob must reach this many connected cells (2 mm cells,
#: 4-connectivity) before the oracle cuts a region along it: the 10+ band of
#: `minority_cells_by_component`, where the straddle stops being grid noise.
SPLIT_FLOOR = 10
SPLIT_FLOORS_SWEPT = (5, 10, 20)        # the floor's own sensitivity, printed beside the headline
#: decision rule, docs/lagging-areas-2026-11-06/2-satin-fill.md section C3
SPLIT_WORTH_DESIGNING = 0.55
SPLIT_CLOSES_DIRECTION = 0.45


def oracle_split(pt, ot, tboth, owner, floor: int = SPLIT_FLOOR) -> dict:
    """The per-region oracle one level finer: cut each of OUR regions along the
    pro's minority-type blobs and give every part the pro's type there.

    For region k, `dom` is the pro's majority type over its graded cells (the
    `cell_census` oracle's label). For each other pro type t, the graded cells
    of k the pro sews as t form 4-connected blobs; a blob of >= `floor` cells
    becomes a part of its own, labelled t; every other cell of k keeps `dom`.
    A region with no such blob is labelled exactly as the per-region oracle
    labels it. Cells outside any region keep our own type.

    THE PRO'S BLOBS ARE READ, so this is a maximum, not something inference from
    flat art could reach. Returns the relabelled map, the plain per-region oracle
    map (for the same call's own cross-check) and what was cut.
    """
    import cv2
    import numpy as np
    plain = ot.copy()
    split = ot.copy()
    parts = []                          # (region, pro type, blob mask): what `attribute` reads
    grounds, blobs, cut_cells, ground_cells = 0, 0, 0, 0
    for k in np.unique(owner[owner >= 0]):
        in_k = owner == k
        graded = in_k & tboth
        if not graded.any():
            continue
        vals, counts = np.unique(pt[graded], return_counts=True)
        # a tie goes to the type met first in row-major order: `cell_census`'s
        # Counter.most_common, so the plain oracle here IS that oracle, tie for tie
        first = {int(t): int(np.flatnonzero(graded.ravel() & (pt.ravel() == t))[0]) for t in vals}
        dom = min((int(t) for t, c in zip(vals, counts) if c == counts.max()), key=first.get)
        plain[in_k & (pt >= 0)] = dom
        split[in_k & (pt >= 0)] = dom
        n_here = 0
        for t in vals:
            if int(t) == dom:
                continue
            n, lab = cv2.connectedComponents((graded & (pt == t)).astype(np.uint8), connectivity=4)
            for c in range(1, n):
                blob = lab == c
                size = int(blob.sum())
                if size < floor:
                    continue
                split[blob] = int(t)
                parts.append({"region": int(k), "type": int(t), "dom": dom, "mask": blob})
                blobs += 1; cut_cells += size; n_here += 1
        if n_here:
            grounds += 1
            ground_cells += int(graded.sum())
    return {"split": split, "plain": plain, "grounds_cut": grounds, "blobs": blobs, "cells_cut": cut_cells,
            "cut_region_cells": ground_cells, "parts": parts}


def oracle_split_job(slug: str, runs: Path, floors=SPLIT_FLOORS_SWEPT) -> dict:
    """`oracle_split` on one job's cell grid, scored beside today's routing, the
    per-region oracle and the pro against himself (all three from `cell_census`'s
    own grid and `_kappa_of`, so the columns read against the 10-29 table)."""
    g = _cell_grids(slug, runs)
    scorecard, pt, ot, tboth, owner = g["scorecard"], g["pt"], g["ot"], g["tboth"], g["owner"]
    jk, jc = _kappa_of(pt[tboth], ot[tboth])
    row = {"job_kappa": round(jk, 3), "job_chance": round(jc, 3), "type_cells": int(tboth.sum())}
    cell_mm2 = scorecard.CELL ** 2
    for f in floors:
        o = oracle_split(pt, ot, tboth, owner, f)
        sk, sc = _kappa_of(pt[tboth], o["split"][tboth])
        pk, _pc = _kappa_of(pt[tboth], o["plain"][tboth])
        row[f"floor_{f}"] = {
            "split_kappa": round(sk, 3), "split_chance": round(sc, 3), "plain_kappa": round(pk, 3),
            "grounds_cut": o["grounds_cut"], "blobs": o["blobs"], "cells_cut": o["cells_cut"],
            "cut_mm2": round(o["cells_cut"] * cell_mm2, 1),
            # the graded area of the regions that were cut (the whole ground, not just the blobs)
            "cut_region_mm2": round(o["cut_region_cells"] * cell_mm2, 1)}
    return row


def oracle_split_run(runs: Path, slugs: list[str]) -> dict:
    """Every digitized job in `slugs`; writes `runs/oracle_split.json`. The per-job
    ceiling columns come from `census.json` (`measure`), the same numbers the
    10-29 table printed."""
    from tools.pro_baseline import JOBS
    cen = json.loads((runs / "census.json").read_text(encoding="utf-8"))["jobs"]
    out = {"jobs": {}}
    for s in slugs:
        if s not in JOBS or not (runs / s / "ours.json").exists() or s not in cen:
            print(s, "not measured", flush=True)
            continue
        row = oracle_split_job(s, runs)
        c = cen[s]["cells"]
        row["oracle_kappa"] = c["oracle_kappa"]
        row["pro_self_kappa_half"] = c.get("pro_self_kappa_half")
        row["pro_self_kappa"] = c["pro_self_kappa"]
        row["degenerate"] = c.get("pro_self_chance", 0) >= _degenerate()
        out["jobs"][s] = row
        h = row[f"floor_{SPLIT_FLOOR}"]
        print(s, "job", row["job_kappa"], "oracle", row["oracle_kappa"], "split", h["split_kappa"],
              "cut", h["grounds_cut"], "grounds", h["cut_mm2"], "mm2", flush=True)
    (runs / "oracle_split.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def _degenerate() -> float:
    from tools.pro_parity import scorecard
    return scorecard.CHANCE_DEGENERATE


def split_summary(res: dict, floor: int = SPLIT_FLOOR) -> dict:
    """Means over the defined jobs, the share of the remaining gap closed, and the verdict."""
    ks = {s: j for s, j in res["jobs"].items() if not j["degenerate"]}
    n = len(ks)
    if not n:
        return {"n_jobs": 0}
    mean = lambda f: round(sum(f(j) for j in ks.values()) / n, 3)   # noqa: E731
    fl = f"floor_{floor}"
    m_job = mean(lambda j: j["job_kappa"])
    m_plain = mean(lambda j: j["oracle_kappa"])
    m_split = mean(lambda j: j[fl]["split_kappa"])
    m_ceil = mean(lambda j: j["pro_self_kappa_half"])
    out = {"n_jobs": n, "floor": floor, "mean_job_kappa": m_job, "mean_oracle_kappa": m_plain,
           "mean_split_kappa": m_split, "mean_ceiling_kappa": m_ceil,
           # chance-corrected shares of a gap, never a raw agreement
           "share_of_gap_to_1": round((m_split - m_job) / (1 - m_job), 3) if m_job < 1 else None,
           "share_of_gap_to_ceiling": round((m_split - m_job) / (m_ceil - m_job), 3) if m_ceil > m_job else None,
           "split_wins_over_job": sum(j[fl]["split_kappa"] > j["job_kappa"] for j in ks.values()),
           "grounds_cut": sum(j[fl]["grounds_cut"] for j in ks.values()),
           "blobs": sum(j[fl]["blobs"] for j in ks.values()),
           "cut_mm2": round(sum(j[fl]["cut_mm2"] for j in ks.values()), 1),
           "cut_region_mm2": round(sum(j[fl]["cut_region_mm2"] for j in ks.values()), 1),
           "verdict": split_verdict(m_split)}
    return out


def split_verdict(k: float) -> str:
    if k >= SPLIT_WORTH_DESIGNING:
        return (f"{k:.3f} >= {SPLIT_WORTH_DESIGNING}: a layering-inference stage is worth designing "
                "(an extension of silhouette_underfill, not a splitter)")
    if k <= SPLIT_CLOSES_DIRECTION:
        return (f"{k:.3f} <= {SPLIT_CLOSES_DIRECTION}: the rest of the gap is edge caps and border tiers; "
                "the layering direction closes")
    return f"{k:.3f} is between {SPLIT_CLOSES_DIRECTION} and {SPLIT_WORTH_DESIGNING}: no verdict"


def split_table(res: dict) -> str:
    fl = f"floor_{SPLIT_FLOOR}"
    L = [f"| job | sttype kappa (chance) | per-region oracle | oracle-split ({SPLIT_FLOOR}+ cells) | "
         "grounds cut / blobs | cut mm2 | pro vs pro 0.5 mm |", "|---|---|---|---|---|---|---|"]
    for s, j in res["jobs"].items():
        h = j[fl]
        if j["degenerate"]:
            L.append(f"| {s} | {j['job_kappa']:.2f} ({j['job_chance']:.2f}), undefined | - | - | "
                     f"{h['grounds_cut']} / {h['blobs']} | {h['cut_mm2']} | - |")
            continue
        L.append(f"| {s} | {j['job_kappa']:.2f} ({j['job_chance']:.2f}) | {j['oracle_kappa']:.2f} | "
                 f"{h['split_kappa']:.2f} | {h['grounds_cut']} / {h['blobs']} | {h['cut_mm2']} | "
                 f"{j['pro_self_kappa_half']:.2f} |")
    sm = split_summary(res)
    if not sm["n_jobs"]:
        return "\n".join(L)
    L += ["", f"mean of {sm['n_jobs']}: routing {sm['mean_job_kappa']}, per-region oracle {sm['mean_oracle_kappa']}, "
          f"ORACLE-SPLIT {sm['mean_split_kappa']}, ceiling (pro vs pro 0.5 mm) {sm['mean_ceiling_kappa']}",
          f"oracle-split beats routing on {sm['split_wins_over_job']} of {sm['n_jobs']} jobs",
          f"closes {sm['share_of_gap_to_1']} of the gap from routing to kappa 1, "
          f"{sm['share_of_gap_to_ceiling']} of the gap from routing to the ceiling (kappa-based)",
          f"cut: {sm['grounds_cut']} grounds, {sm['blobs']} blobs, {sm['cut_mm2']} mm2 of blob "
          f"({sm['cut_region_mm2']} mm2 of ground regions touched)"]
    L.append("floor sensitivity (mean oracle-split kappa): " + ", ".join(
        f"{f} cells {split_summary(res, f)['mean_split_kappa']}" for f in SPLIT_FLOORS_SWEPT))
    L += ["", f"DECISION RULE (C3): {sm['verdict']}",
          "This oracle READS THE PRO'S BLOBS. It is optimistic by construction: the number is a maximum, "
          "not what inference from flat art could reach."]
    return "\n".join(L)


# ------------------------------------------------- C3 gain attribution (2026-11-07)
#: bootstrap replicates and seed. The resampling unit is a REGION (each of our
#: sewn regions is one cluster; cells no region owns go in TILE x TILE-cell
#: tiles): neighbouring 2 mm cells are not independent, and a cell bootstrap
#: would print intervals several times too narrow.
BOOT = 1000
BOOT_SEED = 1107
TILE = 8                                # 16 mm tiles for the unowned cells
#: a cut blob's layering pattern, read off OUR owner map (geometry only)
RIM_SHARE = 0.8                         # a rim: this share of the blob within 2 cells of an edge
DARKER = 25.0                           # Rec. 601 luma step (0-255) for darker / lighter than the ground's thread
MAPS = ("routing", "plain", "split", "routing_blobs")


def _wkappa(pt, ot, w=None) -> tuple[float, float]:
    """`_kappa_of` with integer cell weights (one bootstrap replicate). With no
    weights it IS `_kappa_of`."""
    from tools.pro_parity import scorecard
    if w is None:
        return _kappa_of(pt, ot)
    n = float(w.sum())
    if n == 0:
        return 0.0, 0.0
    raw = float(w[pt == ot].sum()) / n
    ch = sum((float(w[pt == c].sum()) / n) * (float(w[ot == c].sum()) / n) for c in (0, 1, 2))
    return scorecard.chance_correct(raw, ch), ch


def _boot_weights(clusters, B: int, rng):
    """B x N integer cell weights: each replicate draws the clusters with replacement."""
    import numpy as np
    _u, cid = np.unique(clusters, return_inverse=True)
    C = int(cid.max()) + 1
    draws = rng.integers(0, C, size=(B, C))
    counts = np.stack([np.bincount(r, minlength=C) for r in draws])
    return counts[:, cid]


def _boot_kappa(pt, m, w):
    """`_wkappa` for every row of `w` at once, with scorecard's clamp. A replicate
    whose chance floor is degenerate (it drew regions of one type only) is NaN:
    its kappa is undefined, as a degenerate job's is, and scorecard's raw
    pass-through would print it as agreement."""
    import numpy as np
    from tools.pro_parity import scorecard
    n = w.sum(1).astype(float)
    raw = (w * (pt == m)).sum(1) / n
    ch = sum(((w * (pt == c)).sum(1) / n) * ((w * (m == c)).sum(1) / n) for c in (0, 1, 2))
    deg = ch >= scorecard.CHANCE_DEGENERATE
    k = np.maximum(0.0, (raw - ch) / np.where(deg, 1.0, 1.0 - ch))
    return np.where(deg, np.nan, k)


def _ci(a) -> list[float]:
    import numpy as np
    a = np.asarray(a, float)
    if not np.isfinite(a).any():
        return [None, None]
    lo, hi = np.nanpercentile(a, [2.5, 97.5])
    return [round(float(lo), 3), round(float(hi), 3)]


def blob_pattern(blob, owner, k: int) -> dict:
    """Where a cut blob sits in its region k, from our owner map alone. Two
    edges: k's OUTLINE (next to a cell no region owns, or the grid edge) and OUR
    PIECES (next to a cell another of our regions owns: a piece sewn on k).

      keyline    a rim: >= RIM_SHARE of it within 2 cells of the outline, and
                 not of our pieces.
      halo       a rim round our pieces: the same, with the two edges swapped.
      band       a rim within 2 cells of BOTH (or only of their union): the strip
                 of ground between the outline and our pieces.
      contained  not a rim and not touching the outline: a piece of another type lying
                 inside the ground, which our segmentation merged into it.
      edge       the rest: a lobe or part of k that reaches the outline.
    """
    import cv2
    import numpy as np
    in_k = owner == k
    pad = np.pad(owner, 1, constant_values=-1)
    nb = [pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]]
    outer = in_k & np.any([b == -1 for b in nb], axis=0)
    inner = in_k & np.any([(b >= 0) & (b != k) for b in nb], axis=0)
    ker = np.ones((5, 5), np.uint8)
    near_o = cv2.dilate(outer.astype(np.uint8), ker).astype(bool)
    near_i = cv2.dilate(inner.astype(np.uint8), ker).astype(bool)
    size = int(blob.sum())
    share_o = float((blob & near_o).sum()) / size
    share_i = float((blob & near_i).sum()) / size
    share_u = float((blob & (near_o | near_i)).sum()) / size
    t_o = bool((blob & outer).any())
    if share_u >= RIM_SHARE:
        pat = ("keyline" if share_o >= RIM_SHARE > share_i else
               "halo" if share_i >= RIM_SHARE > share_o else "band")
    elif not t_o:
        pat = "contained"
    else:
        pat = "edge"
    dt = cv2.distanceTransform(np.pad(blob, 1).astype(np.uint8), cv2.DIST_L2, 3)
    return {"pattern": pat, "share_outline": round(share_o, 3), "share_our_pieces": round(share_i, 3),
            "share_either": round(share_u, 3),
            "half_width_cells": round(float(dt.max()), 2)}


def _block_map(segs, bb, shape):
    """Per cell, the pro's colour block carrying the most thread (-1 where none),
    on `scorecard.cell_stats`'s grid and with its segment filter."""
    import numpy as np
    from tools.pro_parity import scorecard
    x0, y0, _x1, _y1 = bb
    H, W = shape
    tally: dict = {}
    for (ax, ay, bx, by, d, blk, tr) in segs:
        if tr or d > scorecard.LONG_MM or d < 0.05:
            continue
        ci = int(((ay + by) / 2 - y0) / scorecard.CELL)
        cj = int(((ax + bx) / 2 - x0) / scorecard.CELL)
        if 0 <= ci < H and 0 <= cj < W:
            cell = tally.setdefault((ci, cj), {})
            cell[blk] = cell.get(blk, 0.0) + d
    out = np.full(shape, -1, int)
    for (i, j), c in tally.items():
        out[i, j] = max(c, key=c.get)
    return out


def _pro_thread_rgbs(slug: str, n_blocks: int):
    """The pro's thread colour per DST block, from his PES when the job has one and
    its colour count matches the DST's blocks; else None (a DST carries no colour)."""
    from tools.pro_baseline import JOBS, resolve
    pes = JOBS[slug][4]
    if not pes:
        return None
    try:
        import pystitch
        threads = [(t.get_red(), t.get_green(), t.get_blue()) for t in pystitch.read(str(resolve(pes))).threadlist]
    except Exception:                                           # noqa: BLE001 -- no colour, not a crash
        return None
    return threads if len(threads) == n_blocks else None


def _luma(rgb) -> float:
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _mode(a) -> int:
    import numpy as np
    a = a[a >= 0]
    if not a.size:
        return -1
    v, c = np.unique(a, return_counts=True)
    return int(v[np.argmax(c)])


def attribute_job(slug: str, runs: Path, B: int = BOOT, seed: int = BOOT_SEED,
                  floor: int = SPLIT_FLOOR) -> dict:
    """Where one job's oracle-split gain sits.

    Four maps on `cell_census`'s grid: `routing` (ours), `plain` (the per-region
    oracle), `split` (oracle-split at `floor`) and `routing_blobs` (ours, with ONLY
    the cut blobs given the pro's type: the layering term on today's engine, with
    no per-region relabel riding along). Each kappa carries its chance floor and a
    region-cluster bootstrap 95% interval; each difference a PAIRED interval (one
    set of replicate weights for all four maps).

    Regions: add-one gains from routing (region k alone relabelled as `plain`,
    then as `split`). Blobs: add-one gains on top of `plain` (the cut term) and on
    top of `routing` (the layering term today's engine could buy), with the blob's
    layering pattern and the pro's thread colour against the ground's. A blob our
    routing already sews as the pro's type adds to the cut term ONLY by undoing
    the per-region relabel's damage there; `ours_right` says how much of it.
    """
    import zlib
    import numpy as np
    from tools.tier_census import plan_tier
    g = _cell_grids(slug, runs)
    scorecard, pt, ot, tboth, owner, info = (g["scorecard"], g["pt"], g["ot"], g["tboth"],
                                             g["owner"], g["info"])
    o = oracle_split(pt, ot, tboth, owner, floor)
    rb = ot.copy()
    for p in o["parts"]:
        rb[p["mask"]] = p["type"]
    full = {"routing": ot, "plain": o["plain"], "split": o["split"], "routing_blobs": rb}
    P = pt[tboth]
    flat = {n: m[tboth] for n, m in full.items()}
    point = {n: _kappa_of(P, m) for n, m in flat.items()}

    ii, jj = np.nonzero(tboth)
    own = owner[tboth]
    clusters = np.where(own >= 0, own, -1 - ((ii // TILE) * 100_000 + jj // TILE))
    rng = np.random.default_rng([seed, zlib.crc32(slug.encode())])
    w = _boot_weights(clusters, B, rng)
    reps = {n: _boot_kappa(P, m, w) for n, m in flat.items()}

    undefined = np.zeros(B, bool)
    for r in reps.values():
        undefined |= np.isnan(r)
    row = {"type_cells": int(tboth.sum()), "boot": B, "clusters": int(len(np.unique(clusters))),
           "undefined_replicates": int(undefined.sum())}
    for n in MAPS:
        row[n] = {"kappa": round(point[n][0], 3), "chance": round(point[n][1], 3), "ci": _ci(reps[n])}
    for name, a, b in (("gain", "split", "routing"), ("relabel", "plain", "routing"),
                       ("cut", "split", "plain"), ("blobs_on_routing", "routing_blobs", "routing")):
        row[name] = {"delta": round(point[a][0] - point[b][0], 3), "ci": _ci(reps[a] - reps[b])}

    # ---- regions: add-one from routing
    k_route = point["routing"][0]
    sewn = {k: poly for _a, k, poly in g["polys"]}
    cut_regions = {p["region"] for p in o["parts"]}
    regions = []
    for k in np.unique(own[own >= 0]):
        k = int(k)
        in_k = owner == k
        m = ot.copy(); m[in_k] = o["plain"][in_k]
        kp = _kappa_of(P, m[tboth])[0]
        m[in_k] = o["split"][in_k]
        ks = _kappa_of(P, m[tboth])[0]
        r = info["regions"][k]
        poly = sewn[k]
        ground = any(j != k and q.area < poly.area and poly.contains(q.representative_point())
                     for j, q in sewn.items())
        lettering = any(key in (r.get("meta") or {}) for key in
                        ("text_cluster_id", "lettering_group", "bean_letter", "small_text_stray"))
        regions.append({"id": r["id"], "k": k, "tier": plan_tier(r.get("kinds") or {}),
                        "lettering": lettering, "ground": ground, "cut": k in cut_regions,
                        "graded_mm2": round(float((in_k & tboth).sum()) * scorecard.CELL ** 2, 1),
                        "add_relabel": round(kp - k_route, 4), "add_split": round(ks - k_route, 4)})

    # ---- blobs: add-one on top of the per-region oracle, with pattern and colour
    blocks = _block_map(g["pro"], g["bb"], pt.shape)
    n_blocks = len(scorecard.load_blocks(runs / slug / "score" / slug, "pro"))
    rgbs = _pro_thread_rgbs(slug, n_blocks)
    k_plain = point["plain"][0]
    blob_rows = []
    in_any_blob = np.zeros(pt.shape, bool)
    for p in o["parts"]:
        in_any_blob |= p["mask"]
    for p in o["parts"]:
        m = o["plain"].copy(); m[p["mask"]] = p["type"]
        gain = _kappa_of(P, m[tboth])[0] - k_plain
        m = ot.copy(); m[p["mask"]] = p["type"]
        on_routing = _kappa_of(P, m[tboth])[0] - k_route
        geo = blob_pattern(p["mask"], owner, p["region"])
        b_blk = _mode(blocks[p["mask"]])
        g_blk = _mode(blocks[(owner == p["region"]) & tboth & ~in_any_blob])
        colour = "unknown"
        if b_blk >= 0 and g_blk >= 0:
            if b_blk == g_blk:
                colour = "same block"
            elif rgbs is None:
                colour = "other block"
            else:
                d = _luma(rgbs[b_blk]) - _luma(rgbs[g_blk])
                colour = "darker" if d <= -DARKER else "lighter" if d >= DARKER else "other block, same luma"
        blob_rows.append({"region": info["regions"][p["region"]]["id"], "k": p["region"],
                          "pro_type": p["type"], "ground_type": p["dom"],
                          "cells": int(p["mask"].sum()), "add_cut": round(gain, 4),
                          "add_on_routing": round(on_routing, 4),
                          # the share of the blob our routing already sews as the pro's type
                          "ours_right": round(float((ot[p["mask"]] == p["type"]).mean()), 3),
                          "colour": colour, **geo})
    row["regions"] = regions
    row["blobs"] = blob_rows
    row["_reps"] = {n: reps[n] for n in MAPS}          # for the pooled interval; not written
    return row


def attribute_run(runs: Path, slugs: list[str], B: int = BOOT) -> dict:
    """`attribute_job` on every measured, non-degenerate job, plus the pooled
    means with a two-stage bootstrap (jobs, or whole artworks, resampled; each
    pick takes one of that job's own replicates). Writes `runs/attribution.json`."""
    import numpy as np
    from tools.pro_baseline import ARTWORK, JOBS
    cen = json.loads((runs / "census.json").read_text(encoding="utf-8"))["jobs"]
    jobs, reps = {}, {}
    for s in slugs:
        if s not in JOBS or s not in cen or not (runs / s / "ours.json").exists():
            continue
        if cen[s]["cells"].get("pro_self_chance", 0) >= _degenerate():
            print(s, "degenerate (the pro sews one type): left out", flush=True)
            continue
        row = attribute_job(s, runs, B)
        reps[s] = row.pop("_reps")
        jobs[s] = row
        print(s, "gain", row["gain"]["delta"], row["gain"]["ci"], "relabel", row["relabel"]["delta"],
              "cut", row["cut"]["delta"], "blobs on routing", row["blobs_on_routing"]["delta"], flush=True)
    out = {"jobs": jobs, "pooled": {}}
    names = list(jobs)
    if names:
        rng = np.random.default_rng(BOOT_SEED)
        art_of = {s: a for a, ss in ARTWORK.items() for s in ss}
        arts = sorted({art_of[s] for s in names})
        for unit in ("job", "artwork"):
            groups = [[s] for s in names] if unit == "job" else [[s for s in names if art_of[s] == a] for a in arts]
            pooled = {n: [] for n in MAPS}
            # each pick takes one of its job's DEFINED replicates (all four maps finite)
            ok = {s: np.flatnonzero(np.all([np.isfinite(reps[s][n]) for n in MAPS], axis=0)) for s in names}
            for _b in range(B):
                pick = [s for gi in rng.integers(0, len(groups), len(groups)) for s in groups[gi]]
                r = [ok[s][rng.integers(0, len(ok[s]))] for s in pick]
                for n in MAPS:
                    pooled[n].append(float(np.mean([reps[s][n][ri] for s, ri in zip(pick, r)])))
            pooled = {n: np.array(v) for n, v in pooled.items()}
            out["pooled"][unit] = {
                **{n: _ci(pooled[n]) for n in MAPS},
                "gain": _ci(pooled["split"] - pooled["routing"]),
                "relabel": _ci(pooled["plain"] - pooled["routing"]),
                "cut": _ci(pooled["split"] - pooled["plain"]),
                "blobs_on_routing": _ci(pooled["routing_blobs"] - pooled["routing"]),
                "units": len(groups)}
    (runs / "attribution.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def _region_class(r: dict) -> str:
    return "lettering" if r["lettering"] else "ground" if r["ground"] else "piece"


def attribution_summary(res: dict) -> dict:
    """Per job the gain and its two terms; the share the top 3 jobs carry; how
    many regions carry the cut term; the cut term by region class and by blob
    pattern / colour. All shares are of a mean CHANCE-CORRECTED kappa."""
    jobs = res["jobs"]
    n = len(jobs)
    if not n:
        return {"n_jobs": 0}
    mean = lambda key, sub="delta": round(sum(j[key][sub] for j in jobs.values()) / n, 4)   # noqa: E731
    out = {"n_jobs": n,
           "mean": {m: round(sum(j[m]["kappa"] for j in jobs.values()) / n, 3) for m in MAPS},
           "mean_gain": mean("gain"), "mean_relabel": mean("relabel"), "mean_cut": mean("cut"),
           "mean_blobs_on_routing": mean("blobs_on_routing")}
    for term in ("gain", "cut", "blobs_on_routing"):
        ranked = sorted(jobs, key=lambda s: jobs[s][term]["delta"], reverse=True)
        tot = sum(j[term]["delta"] for j in jobs.values())
        top = ranked[:3]
        out[f"top3_{term}"] = {"jobs": top,
                               "share": round(sum(jobs[s][term]["delta"] for s in top) / tot, 3) if tot else None}
    # the cut term, region by region (add-one on top of plain, summed over its blobs)
    reg_gain = []
    for s, j in jobs.items():
        per = Counter()
        for b in j["blobs"]:
            per[b["k"]] += b["add_cut"]
        by_k = {r["k"]: r for r in j["regions"]}
        for k, v in per.items():
            reg_gain.append((v / n, s, by_k[k]))
    reg_gain.sort(key=lambda t: t[0], reverse=True)
    tot_cut = sum(v for v, *_ in reg_gain)
    acc, need = 0.0, {}
    for i, (v, *_r) in enumerate(reg_gain, 1):
        acc += v
        for share in (0.5, 0.8):
            if share not in need and tot_cut > 0 and acc >= share * tot_cut:
                need[share] = i
    out["cut_regions"] = {"n": len(reg_gain), "sum_add_one": round(tot_cut, 4),
                          "for_50pct": need.get(0.5), "for_80pct": need.get(0.8),
                          "top": [{"job": s, "id": r["id"], "class": _region_class(r), "tier": r["tier"],
                                   "graded_mm2": r["graded_mm2"], "share": round(v / tot_cut, 3) if tot_cut else None}
                                  for v, s, r in reg_gain[:8]]}
    cls, pat, col, pat_col, dirn = Counter(), Counter(), Counter(), Counter(), Counter()
    n_pat = Counter()
    tname = {0: "run", 1: "satin", 2: "fill"}
    widths = []
    for v, s, r in reg_gain:
        cls[f"{_region_class(r)} {r['tier'].lower()}"] += v
    for j in jobs.values():
        for b in j["blobs"]:
            v = b["add_cut"] / n
            pat[b["pattern"]] += v; n_pat[b["pattern"]] += 1
            col[b["colour"]] += v
            pat_col[f"{b['pattern']} / {b['colour']}"] += v
            dirn[f"pro {tname[b['pro_type']]} in a pro-{tname[b['ground_type']]} ground"] += v
            widths.append(b["half_width_cells"])
    tot_blob = sum(pat.values())
    share = lambda c: {k: round(x / tot_blob, 3) for k, x in c.most_common()} if tot_blob else {}   # noqa: E731
    out["cut_by_region_class"] = {k: round(x / tot_cut, 3) for k, x in cls.most_common()} if tot_cut else {}
    out["cut_by_pattern"] = share(pat)
    out["blobs_by_pattern"] = dict(n_pat)
    out["cut_by_colour"] = share(col)
    out["cut_by_pattern_colour"] = share(pat_col)
    out["cut_by_direction"] = share(dirn)
    # the same split for the blobs alone on today's routing
    pr, cr = Counter(), Counter()
    for j in jobs.values():
        for b in j["blobs"]:
            pr[b["pattern"]] += b["add_on_routing"] / n
            cr[b["colour"]] += b["add_on_routing"] / n
    tr = sum(pr.values())
    out["on_routing_by_pattern"] = {k: round(x / tr, 3) for k, x in pr.most_common()} if tr else {}
    out["on_routing_by_colour"] = {k: round(x / tr, 3) for k, x in cr.most_common()} if tr else {}
    out["sum_blob_on_routing"] = round(tr, 4)
    cells = sum(b["cells"] for j in jobs.values() for b in j["blobs"])
    out["blob_cells_ours_right"] = round(sum(b["cells"] * b["ours_right"] for j in jobs.values()
                                             for b in j["blobs"]) / cells, 3) if cells else None
    out["blob_half_width_cells_max"] = max(widths) if widths else None
    out["sum_blob_add_one"] = round(tot_blob, 4)
    out["verdict"] = split_verdict(out["mean"]["split"])
    return out


def attribution_table(res: dict) -> str:
    sm = attribution_summary(res)
    if not sm["n_jobs"]:
        return "no jobs"
    iv = lambda ci, fmt: "[undefined]" if ci[0] is None else f"[{ci[0]:{fmt}}, {ci[1]:{fmt}}]"   # noqa: E731
    f = lambda d: f"{d['kappa']:.3f} ({d['chance']:.2f}) {iv(d['ci'], '.2f')}"                     # noqa: E731
    g = lambda d: f"{d['delta']:+.3f} {iv(d['ci'], '+.2f')}"                                       # noqa: E731
    L = ["| job (undefined replicates) | routing kappa (chance) [95%] | per-region oracle | oracle-split | routing + blobs only "
         "| gain split - routing | of which relabel | of which cut | blobs on routing | blobs |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for s, j in sorted(res["jobs"].items(), key=lambda t: t[1]["gain"]["delta"], reverse=True):
        L.append(f"| {s} ({j['undefined_replicates']}) | {f(j['routing'])} | {f(j['plain'])} | {f(j['split'])} | {f(j['routing_blobs'])} | "
                 f"{g(j['gain'])} | {g(j['relabel'])} | {g(j['cut'])} | {g(j['blobs_on_routing'])} | "
                 f"{len(j['blobs'])} |")
    m = sm["mean"]
    L += ["", f"mean of {sm['n_jobs']}: routing {m['routing']}, per-region oracle {m['plain']}, "
          f"oracle-split {m['split']}, routing + blobs only {m['routing_blobs']}",
          f"mean gain {sm['mean_gain']} = relabel {sm['mean_relabel']} + cut {sm['mean_cut']}; "
          f"blobs alone on routing {sm['mean_blobs_on_routing']}"]
    for unit, p in res.get("pooled", {}).items():
        L.append(f"95% intervals, {p['units']} {unit}s resampled (two-stage): " + ", ".join(
            f"{k} {p[k]}" for k in (*MAPS, "gain", "relabel", "cut", "blobs_on_routing")))
    for term in ("gain", "cut", "blobs_on_routing"):
        t = sm[f"top3_{term}"]
        L.append(f"top 3 jobs carry {t['share']} of the mean {term}: {', '.join(t['jobs'])}")
    c = sm["cut_regions"]
    L.append(f"cut term over {c['n']} regions (add-one sum {c['sum_add_one']} vs cut {sm['mean_cut']}): "
             f"{c['for_50pct']} carry 50%, {c['for_80pct']} carry 80%")
    for r in c["top"]:
        L.append(f"  {r['job']} {r['id']} {r['class']} {r['tier']} {r['graded_mm2']} mm2: {r['share']}")
    L.append(f"cut by region class {sm['cut_by_region_class']}")
    L.append(f"cut by blob pattern {sm['cut_by_pattern']} (blobs {sm['blobs_by_pattern']})")
    L.append(f"cut by pro thread colour vs the ground's {sm['cut_by_colour']}")
    L.append(f"cut by pattern / colour {sm['cut_by_pattern_colour']}")
    L.append(f"cut by type direction {sm['cut_by_direction']}; widest blob half-width "
             f"{sm['blob_half_width_cells_max']} cells")
    L.append(f"blobs alone on routing (add-one sum {sm['sum_blob_on_routing']}): by pattern "
             f"{sm['on_routing_by_pattern']}, by colour {sm['on_routing_by_colour']}; "
             f"our routing already sews {sm['blob_cells_ours_right']} of the blob cells as the pro's type")
    L.append(f"DECISION RULE (C3): {sm['verdict']}")
    return "\n".join(L)


# ------------------------------------------------- C3 edge-band census (2026-11-07)
#: PRE-REGISTERED before any band width was read: the predictor is the engine's own
#: satin ceiling (`machine.SATIN_MAX_WIDTH_MM`, 5.0; the pro's satin letters read
#: 4.2-5.4 mm, per `config.border_by_size`'s comment). A band at or under it is
#: predicted SATIN, a wider one FILL. No threshold is fitted to these blobs.
BAND_SATIN_MAX_MM = 5.0
BAND_SWEPT_MM = (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)     # shown beside it, never picked from
BAND_MIN_CLUSTERS = 5                                   # fewer clusters than this: no interval is printed
BAND_UPSAMPLE = 4                                      # sub-cell resolution of a blob's width
RIM_PATTERNS = ("keyline", "halo", "band")
TYPE_NAME = {0: "run", 1: "satin", 2: "fill"}


def band_width_mm(blob, cell: float = 2.0) -> dict:
    """A cut blob's width in mm from its cell mask. `max_mm` is twice its largest
    inscribed circle (the measure `border_by_size` reads a shape by), taken at
    1/BAND_UPSAMPLE-cell resolution; `strip_mm` is 2 x area / perimeter, the mean
    width of a long strip. A grid of 2 mm cells cannot place either closer than
    about 1 mm, and a one-cell strip reads 2 mm."""
    import cv2
    import numpy as np
    m = np.pad(np.asarray(blob, bool), 1).astype(np.uint8)
    up = cv2.resize(m, None, fx=BAND_UPSAMPLE, fy=BAND_UPSAMPLE, interpolation=cv2.INTER_NEAREST)
    dt = cv2.distanceTransform(up, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    max_cells = (2.0 * float(dt.max()) - 1.0) / BAND_UPSAMPLE
    pad = np.pad(m, 1)
    edges = sum(int(((pad == 1) & (np.roll(pad, sh, (0, 1)) == 0)).sum())
                for sh in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    strip_cells = 2.0 * float(m.sum()) / edges if edges else 0.0
    return {"max_mm": round(max_cells * cell, 2), "strip_mm": round(strip_cells * cell, 2)}


def border_tier(min_dim_mm: float) -> str:
    """`border_by_size`'s band for a shape of this smallest dimension, by the engine's own table."""
    from digitizer_core import machine
    for floor, width in machine.BORDER_BY_SIZE_WIDTH_MM:
        if min_dim_mm >= floor:
            return f"{floor:g}+ ({width} mm ring)"
    return f"under {machine.BORDER_BY_SIZE_WIDTH_MM[-1][0]:g} (none)"


def band_predict(width_mm: float, satin_max: float = BAND_SATIN_MAX_MM) -> int:
    """The simple width-band predictor: satin (1) up to the ceiling, fill (2) over it."""
    return 1 if width_mm <= satin_max else 2


def edge_band_job(slug: str, runs: Path, floor: int = SPLIT_FLOOR) -> list[dict]:
    """One row per cut blob of the job (the blobs `attribute` attributes the cut
    term to), with its width, rim pattern, and its region's size, class and border tier."""
    from shapely import maximum_inscribed_circle
    from tools.tier_census import plan_tier
    g = _cell_grids(slug, runs)
    scorecard, pt, ot, tboth, owner, info = (g["scorecard"], g["pt"], g["ot"], g["tboth"],
                                             g["owner"], g["info"])
    o = oracle_split(pt, ot, tboth, owner, floor)
    sewn = {k: poly for _a, k, poly in g["polys"]}
    rows = []
    for p in o["parts"]:
        k = p["region"]
        r = info["regions"][k]
        poly = sewn[k]
        ground = any(j != k and q.area < poly.area and poly.contains(q.representative_point())
                     for j, q in sewn.items())
        lettering = any(key in (r.get("meta") or {}) for key in
                        ("text_cluster_id", "lettering_group", "bean_letter", "small_text_stray"))
        min_dim = 2.0 * maximum_inscribed_circle(poly, tolerance=0.05).length
        geo = blob_pattern(p["mask"], owner, k)
        wd = band_width_mm(p["mask"], scorecard.CELL)
        rows.append({
            "job": slug, "region": r["id"], "k": k,
            "class": "lettering" if lettering else "ground" if ground else "piece",
            "tier": plan_tier(r.get("kinds") or {}),
            "ours_border": any(key.split(":")[0] == "border" for key in (r.get("kinds") or {})),
            "region_mm2": round(float(poly.area), 1), "min_dim_mm": round(min_dim, 1),
            "border_tier": border_tier(min_dim),
            "cells": int(p["mask"].sum()), "pro_type": int(p["type"]), "ground_type": int(p["dom"]),
            "pattern": geo["pattern"], "rim": geo["pattern"] in RIM_PATTERNS,
            "width_mm": wd["max_mm"], "strip_mm": wd["strip_mm"],
            "ours_right": round(float((ot[p["mask"]] == p["type"]).mean()), 3)})
    return rows


def _band_arrays(rows: list[dict], satin_max: float, cluster: str = "region"):
    """Unit-level arrays over the blobs (one unit per cell, or per blob when a row
    carries `units`): the pro's type, the predictor's, a cluster id."""
    import numpy as np
    from tools.pro_baseline import ARTWORK
    art_of = {s: a for a, ss in ARTWORK.items() for s in ss}
    pt, pr, cl = [], [], []
    ids: dict = {}
    for r in rows:
        key = (r["job"], r["region"]) if cluster == "region" else art_of[r["job"]]
        c = ids.setdefault(key, len(ids))
        n = r.get("units", r["cells"])
        pt += [r["pro_type"]] * n
        pr += [band_predict(r["width_mm"], satin_max)] * n
        cl += [c] * n
    return np.array(pt, int), np.array(pr, int), np.array(cl, int)


def edge_band_kappa(rows: list[dict], satin_max: float = BAND_SATIN_MAX_MM, B: int = BOOT,
                    seed: int = BOOT_SEED, cluster: str = "region") -> dict:
    """The predictor against the pro's type over the blobs' cells: chance-corrected
    kappa, its chance floor and a cluster-bootstrap 95% interval (the cluster is
    the region, or the artwork). `clears_zero`: the interval's low end is over 0.
    Kappa is clamped at 0, so a low end of exactly 0 does NOT clear it."""
    import numpy as np
    pt, pr, cl = _band_arrays(rows, satin_max, cluster)
    if not pt.size:
        return {"cells": 0, "kappa": 0.0, "chance": 0.0, "ci": [None, None], "clears_zero": False,
                "clusters": 0, "undefined_replicates": 0, "agree": 0.0}
    k, ch = _kappa_of(pt, pr)
    n_cl = int(len(np.unique(cl)))
    rep = _boot_kappa(pt, pr, _boot_weights(cl, B, np.random.default_rng([seed, 7])))
    # a degenerate floor leaves kappa undefined (scorecard would pass raw agreement
    # through as 1.0), and under BAND_MIN_CLUSTERS clusters a bootstrap is not an interval
    ci = _ci(rep) if n_cl >= BAND_MIN_CLUSTERS and ch < _degenerate() else [None, None]
    return {"cells": int(pt.size), "kappa": None if ch >= _degenerate() else round(k, 3),
            "chance": round(ch, 3), "ci": ci,
            "clears_zero": bool(ci[0] is not None and ci[0] > 0.0), "clusters": n_cl,
            "undefined_replicates": int(np.isnan(rep).sum()), "agree": round(float((pt == pr).mean()), 3)}


def edge_band_regions(rows: list[dict]) -> list[dict]:
    """One row per region that carries a cut blob (the 13), cell-weighted."""
    by: dict = {}
    for r in rows:
        by.setdefault((r["job"], r["region"]), []).append(r)
    out = []
    for (job, rid), bl in by.items():
        cells = sum(b["cells"] for b in bl)
        pt, pr, _c = _band_arrays(bl, BAND_SATIN_MAX_MM)
        k, ch = _kappa_of(pt, pr)
        b0 = bl[0]
        out.append({"job": job, "region": rid, "class": b0["class"], "tier": b0["tier"],
                    "ours_border": b0["ours_border"], "region_mm2": b0["region_mm2"],
                    "min_dim_mm": b0["min_dim_mm"], "border_tier": b0["border_tier"],
                    "blobs": len(bl), "cells": cells,
                    "width_mm": round(sum(b["width_mm"] * b["cells"] for b in bl) / cells, 1),
                    "width_range": [min(b["width_mm"] for b in bl), max(b["width_mm"] for b in bl)],
                    "rims": sum(b["rim"] for b in bl),
                    "patterns": dict(Counter(b["pattern"] for b in bl)),
                    "pro_types": dict(Counter(TYPE_NAME[b["pro_type"]] for b in bl)),
                    "agree_cells": int((pt == pr).sum()),
                    "kappa": None if ch >= _degenerate() else round(k, 3), "chance": round(ch, 3)})
    out.sort(key=lambda r: r["cells"], reverse=True)
    return out


def edge_band_widths(rows: list[dict]) -> dict:
    import numpy as np
    w = np.array([r["width_mm"] for r in rows], float)
    c = np.array([r["cells"] for r in rows], float)
    return {"blobs": len(rows), "rims": sum(r["rim"] for r in rows),
            "width_mm_min": float(w.min()) if w.size else None,
            "width_mm_max": float(w.max()) if w.size else None,
            "width_mm_cell_weighted_mean": round(float((w * c).sum() / c.sum()), 2) if c.sum() else None,
            "width_hist": {f"{v:g}": int((w == v).sum()) for v in sorted(set(w.tolist()))},
            "cells_by_pro_type": {TYPE_NAME[t]: int(sum(r["cells"] for r in rows if r["pro_type"] == t))
                                  for t in (0, 1, 2)}}


def edge_band_run(runs: Path, slugs: list[str], B: int = BOOT) -> dict:
    """Every cut blob on every measured, non-degenerate job; the regions that carry
    them; the predictor's kappa. Writes `runs/edge_bands.json`."""
    cen = json.loads((runs / "census.json").read_text(encoding="utf-8"))["jobs"]
    rows = []
    for s in slugs:
        if s not in cen or not (runs / s / "ours.json").exists():
            continue
        if cen[s]["cells"].get("pro_self_chance", 0) >= _degenerate():
            continue
        rows += edge_band_job(s, runs)
        print(s, "blobs", sum(r["job"] == s for r in rows), flush=True)
    out = {"blobs": rows, "regions": edge_band_regions(rows), "widths": edge_band_widths(rows),
           "predictor": {"satin_max_mm": BAND_SATIN_MAX_MM,
                         "by_region": edge_band_kappa(rows, B=B),
                         "by_artwork": edge_band_kappa(rows, B=B, cluster="artwork"),
                         "per_blob": edge_band_kappa([{**r, "units": 1} for r in rows], B=B),
                         "swept": {f"{t:g}": edge_band_kappa(rows, t, B=B) for t in BAND_SWEPT_MM}}}
    (runs / "edge_bands.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def edge_band_table(res: dict) -> str:
    iv = lambda ci: "[undefined]" if ci[0] is None else f"[{ci[0]:.2f}, {ci[1]:.2f}]"    # noqa: E731
    L = ["| job | region | class | ours | region mm2 | min dim mm | border tier | band width mm (range) "
         "| blobs (rims) | pattern | pro type | predictor agrees (cells) | kappa (chance) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["regions"]:
        pats = ", ".join(f"{n} {k}" for k, n in r["patterns"].items())
        pro = ", ".join(f"{n} {k}" for k, n in r["pro_types"].items())
        kap = "undefined" if r["kappa"] is None else f"{r['kappa']:.2f}"
        L.append(f"| {r['job']} | {r['region']} | {r['class']} | {r['tier'].lower()}{' + border' if r['ours_border'] else ''} "
                 f"| {r['region_mm2']:.0f} | {r['min_dim_mm']} | {r['border_tier']} | {r['width_mm']} "
                 f"({r['width_range'][0]:g}-{r['width_range'][1]:g}) | {r['blobs']} ({r['rims']}) | {pats} | {pro} "
                 f"| {r['agree_cells']}/{r['cells']} | {kap} ({r['chance']:.2f}) |")
    p = res["predictor"]
    L += ["", f"{len(res['regions'])} regions, {res['widths']['blobs']} blobs ({res['widths']['rims']} rims); "
          f"predictor: satin up to {p['satin_max_mm']} mm, fill over (the engine's satin ceiling, fixed beforehand)"]
    for name in ("by_region", "by_artwork", "per_blob"):
        q = p[name]
        L.append(f"  {name}: kappa {'undefined' if q['kappa'] is None else format(q['kappa'], '.3f')} (chance {q['chance']:.2f}) 95% {iv(q['ci'])}, "
                 f"{q['clusters']} clusters, {q['cells']} units, raw agreement {q['agree']}, "
                 f"undefined replicates {q['undefined_replicates']}, clears 0: {q['clears_zero']}")
    L.append("  threshold sweep (region clusters; not a pick): " + "; ".join(
        f"{t} mm {'undef' if q['kappa'] is None else format(q['kappa'], '.2f')} ({q['chance']:.2f}) {iv(q['ci'])}" for t, q in p["swept"].items()))
    L.append(f"  widths: {res['widths']}")
    return "\n".join(L)


def region_census(slug: str, runs: Path) -> dict:
    """tier_census's per-shape reading of both files. `ground`: another sewn region
    sits inside this one, so the pro's pieces sewn ON it read as its tier."""
    import shapely.wkt
    from tools import tier_census as tc
    res = tc.analyse(slug, runs)
    info = json.loads((runs / slug / "ours.json").read_text(encoding="utf-8"))
    sewn = {}
    for r in info["regions"]:
        if any(k.split(":")[0] in ("fill", "satin", "run", "bean", "border") for k in r["kinds"]):
            p = shapely.wkt.loads(r["wkt"])
            sewn[r["id"]] = p if p.is_valid else p.buffer(0)
    ground = {i for i, p in sewn.items()
              if any(j != i and q.area < p.area and p.contains(q.representative_point())
                     for j, q in sewn.items())}
    rows = []
    for row in res["rows"]:
        rows.append({"id": row["id"], "lettering": row["lettering"], "area": row["geom"]["area"],
                     "stroke": row["geom"]["stroke"], "plan": row["plan"], "ground": row["id"] in ground,
                     "ours": row["ours"]["tier"], "pro": row["pro"]["tier"]})
    return {"rows": rows}


def measure(runs: Path, slugs: list[str]) -> dict:
    from tools.pro_baseline import JOBS, kappas, resolve
    path = runs / "census.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"jobs": {}}
    for s in slugs:
        if not (runs / s / "ours.json").exists():
            print(s, "not digitized", flush=True)
            continue
        pro = resolve(JOBS[s][3])
        row = {"baseline": kappas(runs / s / "ours.dst", pro, runs / s / "score" / s)}
        row["cells"] = cell_census(s, runs)
        try:
            row["regions"] = region_census(s, runs)
        except Exception as e:                                   # noqa: BLE001 -- a row, not a crash
            row["regions"] = {"error": f"{type(e).__name__}: {e}"[:300]}
        res["jobs"][s] = row
        c = row["cells"]
        print(s, "job", c["job_kappa"], "oracle", c["oracle_kappa"], "self", c["pro_self_kappa"], flush=True)
        path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# -------------------------------------------------------------------- table
def _shape_kappa(rows, weight=False):
    """Cohen's kappa over shapes both files read as satin / fill / run; `weight` by area."""
    pairs = [(SATIN_TIERS[r["ours"]], SATIN_TIERS[r["pro"]], r["area"] if weight else 1.0)
             for r in rows if r["ours"] in SATIN_TIERS and r["pro"] in SATIN_TIERS]
    n = sum(w for *_, w in pairs)
    if not n:
        return None, 0
    po = sum(w for a, b, w in pairs if a == b) / n
    labs = {a for a, *_ in pairs} | {b for _, b, _ in pairs}
    pe = sum((sum(w for a, _, w in pairs if a == lab) / n) * (sum(w for _, b, w in pairs if b == lab) / n)
             for lab in labs)
    return (round((po - pe) / (1 - pe), 3) if pe < 1 else None), len(pairs)


def summary(res: dict) -> dict:
    """Cell figures per job; shape figures as `plan` (our tier, known) against the
    pro's READ tier, grounds out, by AREA. By count the reader is the noise: it
    scores our own known plan ~0.2 (`reader_on_ours`), so count columns ride
    along only to show that."""
    from tools.pro_parity import scorecard
    out = {"jobs": {}}
    pat = Counter(); pat_cells = Counter(); minority = Counter()
    shapes, reader = [], []
    for s, row in res["jobs"].items():
        c = row["cells"]
        regs = row["regions"].get("rows", []) if isinstance(row.get("regions"), dict) else []
        for r in regs:
            plan = r["plan"] if r["plan"] in SATIN_TIERS else "NONE"
            reader.append({**r, "pro": plan})                      # the reader against the truth
            if not r["ground"]:
                shapes.append({**r, "ours": plan, "slug": s})
        straddled = [sh for sh in c["shapes"] if sh["purity"] <= PURITY]
        for sh in c["shapes"]:
            key = "pure" if sh["purity"] > PURITY else sh["pattern"]
            pat[key] += 1
            pat_cells[key] += sh["cells"]
        for sh in straddled:
            for sz in sh["minority_sizes"]:
                minority["1" if sz == 1 else "2-3" if sz <= 3 else "4-9" if sz <= 9 else "10+"] += sz
        out["jobs"][s] = {
            "job_kappa": c["job_kappa"], "job_chance": c["job_chance"],
            "oracle_kappa": c["oracle_kappa"], "pro_self_kappa": c["pro_self_kappa"],
            "pro_self_kappa_half": c.get("pro_self_kappa_half"),
            # the pro sews ONE type: his side of the floor is degenerate, the kappa undefined
            "degenerate": c.get("pro_self_chance", 0) >= scorecard.CHANCE_DEGENERATE,
            "straddled_share": round(sum(sh["cells"] for sh in straddled)
                                     / max(1, sum(sh["cells"] for sh in c["shapes"])), 3),
        }
    out["patterns"] = {k: {"shapes": pat[k], "cells": pat_cells[k]} for k in pat}
    out["minority_cells_by_component"] = dict(minority)
    let = [r for r in shapes if r["lettering"]]
    rest = [r for r in shapes if not r["lettering"]]
    out["shape_kappa"] = {name: {"area": _shape_kappa(rs, True), "count": _shape_kappa(rs)}
                          for name, rs in (("all", shapes), ("lettering", let), ("rest", rest),
                                           ("reader_on_ours", reader))}
    conf = Counter()
    for r in shapes:
        if r["ours"] in SATIN_TIERS and r["pro"] in SATIN_TIERS:
            conf[(SATIN_TIERS[r["ours"]], SATIN_TIERS[r["pro"]])] += r["area"]
    out["confusion_mm2"] = {f"{a}->{b}": round(n) for (a, b), n in sorted(conf.items())}
    ks = [j for j in out["jobs"].values() if not j["degenerate"]]
    out["n_jobs"] = len(ks)
    for k in ("job_kappa", "oracle_kappa", "pro_self_kappa", "pro_self_kappa_half"):
        out[f"mean_{k}"] = round(sum(j[k] for j in ks) / len(ks), 3) if ks else None
    out["oracle_wins"] = sum(j["oracle_kappa"] > j["job_kappa"] for j in ks)
    return out


def _fmt(k):
    v, n = k
    return "-" if v is None else f"{v:.2f} (n {n})"


def table(runs: Path, vs: Path | None) -> str:
    res = json.loads((runs / "census.json").read_text(encoding="utf-8"))
    sm = summary(res)
    other = summary(json.loads((vs / "census.json").read_text(encoding="utf-8"))) if vs else None
    L = ["| job | sttype kappa (chance) | oracle | pro vs pro 0.5 / 1.0 mm | straddled |"
         + (" kappa ON |" if other else ""), "|---|---|---|---|---|" + ("---|" if other else "")]
    for s, j in sm["jobs"].items():
        if j["degenerate"]:
            L.append(f"| {s} | {j['job_kappa']:.2f} ({j['job_chance']:.2f}), undefined | - | - | "
                     f"{100 * j['straddled_share']:.0f}% |" + (" - |" if other else ""))
            continue
        line = (f"| {s} | {j['job_kappa']:.2f} ({j['job_chance']:.2f}) | {j['oracle_kappa']:.2f} | "
                f"{j['pro_self_kappa_half']:.2f} / {j['pro_self_kappa']:.2f} | {100 * j['straddled_share']:.0f}% |")
        if other:
            o = other["jobs"].get(s)
            line += f" {o['job_kappa']:.2f} |" if o else " - |"
        L.append(line)
    L += ["", f"mean of {sm['n_jobs']}: job kappa {sm['mean_job_kappa']}, oracle {sm['mean_oracle_kappa']} "
          f"(wins {sm['oracle_wins']}), pro self 0.5 / 1.0 mm {sm['mean_pro_self_kappa_half']} / "
          f"{sm['mean_pro_self_kappa']}" + (f"; ON {other['mean_job_kappa']}" if other else "")]
    for name, k in sm["shape_kappa"].items():
        L.append(f"shape kappa {name}: area {_fmt(k['area'])}, count {_fmt(k['count'])}"
                 + (f"; ON area {_fmt(other['shape_kappa'][name]['area'])}" if other else ""))
    L.append(f"confusion ours->pro (mm2, grounds out) {sm['confusion_mm2']}")
    L.append(f"patterns {sm['patterns']}")
    L.append(f"straddled minority cells by blob size {sm['minority_cells_by_component']}")
    return "\n".join(L)


# ---------------------------------------------------------- a flag's two arms
def _md5(path: Path) -> str:
    import hashlib
    return hashlib.md5(path.read_bytes()).hexdigest()


def moved_shapes(off: Path, on: Path, slug: str) -> list[dict]:
    """Shapes whose plan tier (the kind carrying most of their thread) differs."""
    from tools.tier_census import plan_tier
    a = {r["id"]: r for r in json.loads((off / slug / "ours.json").read_text(encoding="utf-8"))["regions"]}
    b = {r["id"]: r for r in json.loads((on / slug / "ours.json").read_text(encoding="utf-8"))["regions"]}
    out = []
    import shapely.wkt
    for sid in sorted(set(a) | set(b)):
        ta = plan_tier(a[sid]["kinds"]) if sid in a else "ABSENT"
        tb = plan_tier(b[sid]["kinds"]) if sid in b else "ABSENT"
        if ta != tb:
            poly = shapely.wkt.loads((a.get(sid) or b[sid])["wkt"])
            out.append({"id": sid, "off": ta, "on": tb, "area": round(poly.area, 1),
                        "bounds": [round(v, 2) for v in poly.bounds]})
    return out


def flip_table(off: Path, on: Path) -> str:
    co = json.loads((off / "census.json").read_text(encoding="utf-8"))["jobs"]
    cn = json.loads((on / "census.json").read_text(encoding="utf-8"))["jobs"]
    L = ["| job | identical | shapes moved (mm²) | sttype kappa OFF / ON | stitches OFF / ON | trims OFF / ON "
         "| bare mm² OFF / ON (worst) |", "|---|---|---|---|---|---|---|"]
    for s in co:
        if s not in cn:
            continue
        po = json.loads((off / s / "plan.json").read_text(encoding="utf-8"))
        pn = json.loads((on / s / "plan.json").read_text(encoding="utf-8"))
        same = _md5(off / s / "ours.dst") == _md5(on / s / "ours.dst")
        mv = [] if same else moved_shapes(off, on, s)
        mvs = ", ".join(f"{m['off'].lower()}->{m['on'].lower()} {m['area']}" for m in mv) or ("-" if same else "none")
        ko, kn = co[s]["cells"]["job_kappa"], cn[s]["cells"]["job_kappa"]
        L.append(f"| {s} | {'yes' if same else 'NO'} | {mvs} | {ko:.2f} / {kn:.2f} | "
                 f"{po['stitches']:,} / {pn['stitches']:,} | {po['trims']} / {pn['trims']} | "
                 f"{po['uncovered_total_mm2']} / {pn['uncovered_total_mm2']} "
                 f"({po['uncovered_worst_mm2']} / {pn['uncovered_worst_mm2']}) |")
    return "\n".join(L)


def render(off: Path, on: Path, out: Path, pro_out: Path, slugs: list[str], ppm: float = 20.0) -> None:
    """OFF | ON crops around every moved shape (committed) and the pro's crop (local only)."""
    import cv2
    from tools import flip_sheet_renders as fsr
    from tools import pro_pair
    from tools.pro_baseline import JOBS, resolve
    from tools.pro_parity import pairframe
    out.mkdir(parents=True, exist_ok=True)
    pro_out.mkdir(parents=True, exist_ok=True)
    for s in slugs:
        if not (on / s / "ours.dst").exists() or _md5(off / s / "ours.dst") == _md5(on / s / "ours.dst"):
            continue
        mv = moved_shapes(off, on, s)
        if not mv:
            continue
        x0 = min(m["bounds"][0] for m in mv) - 3; y0 = min(m["bounds"][1] for m in mv) - 3
        x1 = max(m["bounds"][2] for m in mv) + 3; y1 = max(m["bounds"][3] for m in mv) + 3
        box = (x0, y0, x1, y1)
        do = json.loads((off / s / "design.json").read_text(encoding="utf-8"))
        dn = json.loads((on / s / "design.json").read_text(encoding="utf-8"))
        tiles = [pro_pair._label(fsr.render_crop(do, box, ppm), "OFF"),
                 pro_pair._label(fsr.render_crop(dn, box, ppm), "ON")]
        cv2.imwrite(str(out / f"{s}.jpg"), pro_pair._hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 88])
        _g, _w, _a, pro_dst, pro_pes, _wl = JOBS[s]
        dp = pairframe.design_for(resolve(pro_pes or pro_dst), None, None, s)
        pb = fsr.pro_box(dp, fsr._design_frame(do), box)
        cv2.imwrite(str(pro_out / f"{s}_pro.jpg"),
                    pro_pair._label(fsr.render_crop(dp, pb, ppm), "pro"), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(s, len(mv), "shapes", out / f"{s}.jpg", flush=True)


def main(argv=None) -> int:
    from tools.pro_baseline import JOBS
    from tools.pro_pair import parse_sets
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("digitize", "measure", "table", "flip", "render", "oracle-split",
                                       "attribute", "edge-bands"))
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
    ap.add_argument("--vs", type=Path, help="the ON arm's runs (table, flip, render)")
    ap.add_argument("--out", type=Path, help="render: where OUR crops go (committable)")
    a = ap.parse_args(argv)
    slugs = [s for s in JOBS if not a.only or s in a.only]
    if a.cmd == "digitize":
        digitize(a.runs, slugs, parse_sets(a.set))
    elif a.cmd == "measure":
        measure(a.runs, slugs)
    elif a.cmd == "oracle-split":
        print(split_table(oracle_split_run(a.runs, slugs)))
    elif a.cmd == "attribute":
        print(attribution_table(attribute_run(a.runs, slugs)))
    elif a.cmd == "edge-bands":
        print(edge_band_table(edge_band_run(a.runs, slugs)))
    elif a.cmd == "flip":
        print(flip_table(a.runs, a.vs))
    elif a.cmd == "render":
        from tools import pro_renders
        render(a.runs, a.vs, a.out, pro_renders.out_dir(a.out.name), slugs)
    else:
        print(table(a.runs, a.vs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
