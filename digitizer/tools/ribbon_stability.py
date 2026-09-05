#!/usr/bin/env python
"""How stable the satin/fill classifier is under boundary detail, and what the
candidate cures do to it.

The instrument behind the classifier-robustness item (2026-09-03,
`docs/classifier-stability-2026-09-03.md`). For every fixture it digitizes
twice -- the shipped polygons, and the same art with the curve refinement
ungated (`stage4_vectorize._CURVE_MIN_PX_PER_MM` = 0, `curve_turn_deg` = 15),
which is the strongest boundary-detail change the engine can make without
touching the artwork -- pairs the shapes by id then centroid, and reports,
over the population the DT gates actually judge (past the width cap and the
aspect gate):

- **flips**: shapes whose verdict differs between the two polygons under
  the shipped classifier and under each `--variant`;
- **changes a shipped verdict**: shapes whose verdict on the SHIPPED
  polygon the variant would move -- the cost of adopting it;
- the letterform archetypes and the serrated disc from `tests/test_satin`,
  which every variant has to keep.

Variants (all measured 2026-09-03, none adopted; every one changed shipped
verdicts while the flips stayed at 3-12 against 5 today):

    spur:K   prune skeleton edges with one free end shorter than K x the DT
             radius at their junction, then measure everything on what is left
    sew      the same, with `extract_strokes`' own spur rule (1.6 half-widths)
    hybrid   regularity and p90 on the full skeleton, spine length on the
             sewing-pruned one
    smooth:R morphological open+close of the classifier's raster by R px
             before thinning (measurement only, the art is untouched)
    band     within cv 0.45-0.55 the promotion rule decides both ways
    strokes  the per-stroke rung (2026-09-05): keep the shipped verdict, and
             ADDITIONALLY take a refused region whose stroke-partitioned area
             passes both per-stroke gates by at least
             `stage6_satin._STROKE_AREA_FRAC_MIN`. Promotion-only by
             construction -- DOCTRINE measured that a replacement demotes 15
             regions incl. one of 638.8 mm2 -- so its `changes a shipped
             verdict` count can only ever be fill->satin. This is the variant
             the plan's §7 asks for BEFORE its threshold is adopted.

    .venv/bin/python tools/ribbon_stability.py [case ...] [--variant NAME ...]

Cases: whitebg, alpha, ribbon, becker, fremont, drone, enthusiast, gaulke,
sunset, meadow (the `tools/curve_tiers.py` set).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from skimage.morphology import medial_axis  # noqa: E402

from digitizer_core import PipelineConfig, digitize, machine  # noqa: E402
from digitizer_core import stage4_vectorize as s4  # noqa: E402
from digitizer_core import stage6_satin as s6  # noqa: E402
from digitizer_core.shapefield import build_shape_field  # noqa: E402
from digitizer_core.stage6_satin import (RibbonVerdict, _DtStats, _floor_or,  # noqa: E402
                                         _skeleton_edges, classify_ribbon,
                                         ribbon_width_mm)
import curve_tiers  # noqa: E402


def _stats_from(r: np.ndarray, area: float, scale: float,
                r_full: np.ndarray | None = None) -> _DtStats | None:
    """DT stats from the radii `r` at the (possibly pruned) skeleton; the
    regularity/p90 radii come from `r_full` when given (the hybrid)."""
    rr = r if r_full is None else r_full
    if r.size == 0 or rr.size == 0 or rr.mean() <= 0:
        return None
    spine_len_mm = float(r.size) / scale
    width_mm = 2.0 * float(rr.mean()) / scale
    swept = spine_len_mm * width_mm
    return _DtStats(mean=float(rr.mean()), std=float(rr.std()),
                    p90_mm=2.0 * float(np.percentile(rr, s6._DT_TIGHTEN_PERCENTILE)) / scale,
                    spine_len_mm=spine_len_mm,
                    explained=(area / swept) if swept > 0 else 0.0,
                    elongation=(spine_len_mm / width_mm) if width_mm > 0 else 0.0)


def variant_stats(poly, variant: str) -> _DtStats | None:
    field = build_shape_field(poly)
    if field is None or not field.skel.any():
        return None
    skel, dist, scale = field.skel, field.dist, field.scale
    full = dist[skel]
    if variant.startswith("spur:"):
        k = float(variant.split(":")[1])
        keep: set = set()
        for e in _skeleton_edges(skel):
            pts = e["pts"]
            if e["closed"] or e["free_start"] == e["free_end"]:
                keep.update(pts)
                continue
            node = pts[-1] if e["free_start"] else pts[0]
            if len(pts) < k * float(dist[node[1], node[0]]):
                keep.add(node)
            else:
                keep.update(pts)
        if not keep:
            return None
        ys = np.array([p[1] for p in keep])
        xs = np.array([p[0] for p in keep])
        return _stats_from(dist[ys, xs], float(poly.area), scale)
    if variant in ("sew", "hybrid"):
        m = skel.astype(np.uint8)
        s6._prune_spurs(m, max(3.0, float(full.mean()) * 1.6))
        ys, xs = np.nonzero(m)
        return _stats_from(dist[ys, xs], float(poly.area), scale,
                           r_full=full if variant == "hybrid" else None)
    if variant.startswith("smooth:"):
        rad = int(variant.split(":")[1])
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rad + 1, 2 * rad + 1))
        m8 = field.mask.astype(np.uint8) * 255
        m8 = cv2.morphologyEx(cv2.morphologyEx(m8, cv2.MORPH_OPEN, ker), cv2.MORPH_CLOSE, ker)
        if not m8.any():
            return None
        sk, d2 = medial_axis(m8 > 0, return_distance=True, rng=0)
        return _stats_from(d2[sk], float(poly.area), scale)
    return s6._dt_stats(poly)


def classify_variant(poly, variant: str, design_class: str) -> RibbonVerdict:
    """`classify_ribbon` with the variant's stats in place of `_dt_stats`."""
    max_w = machine.SATIN_MAX_WIDTH_MM
    w = ribbon_width_mm(poly)
    perim = poly.exterior.length + sum(r.length for r in poly.interiors)
    m: dict = {"ribbon_w": w}
    if w <= 0 or w > max_w:
        return RibbonVerdict(False, "width_cap", m)
    if perim / 2.0 - w < 3.0 * w:
        return RibbonVerdict(False, "aspect", m)
    if variant == "strokes":
        # Promotion-only: the shipped call still decides, and the rung may
        # only ADD. Placed after the width and aspect gates on purpose --
        # those are properties of the region the machine sews, not of a
        # stroke, and `classify_strokes` deliberately does not re-apply them.
        shipped = classify_ribbon(poly, max_w, design_class=design_class,
                                  full_metrics=True)
        if shipped.satin:
            return shipped
        sv = s6.classify_strokes(poly, max_w, design_class=design_class)
        # Carry the REGION's own dt metrics through, not just the fraction:
        # the report prints dt_cv/explained/elongation per verdict, and a
        # variant that leaves them unset prints `cv 0.51->0.00`, which reads
        # as the rung having driven cv to zero rather than as a missing key.
        m.update({k: shipped.metrics.get(k, 0.0)
                  for k in ("dt_cv", "explained", "elongation")},
                 p90=shipped.metrics.get("dt_p90_mm", 0.0),
                 stroke_frac=sv.passing_frac, strokes=len(sv.strokes))
        if sv.passing_frac >= s6._STROKE_AREA_FRAC_MIN:
            return RibbonVerdict(True, "stroke_ribbon", m)
        return shipped
    stats = variant_stats(poly, variant)
    if stats is None:
        return RibbonVerdict(True, "dt_degenerate", m)
    cv = stats.std / stats.mean
    m.update(dt_cv=cv, explained=stats.explained, elongation=stats.elongation, p90=stats.p90_mm)
    ribbon_like = (stats.p90_mm <= max_w
                   and s6._PROMOTE_EXPLAINED_MIN <= stats.explained <= s6._PROMOTE_EXPLAINED_MAX
                   and stats.elongation >= s6._PROMOTE_ELONGATION_MIN)
    if variant == "band" and 0.45 <= cv <= 0.55:
        return (_floor_or(RibbonVerdict(True, "band_ribbon", m), stats, design_class, m)
                if ribbon_like else RibbonVerdict(False, "band_blob", m))
    if 2.0 * stats.std >= stats.mean:
        if ribbon_like:
            return _floor_or(RibbonVerdict(True, "promoted_ribbon", m), stats, design_class, m)
        return RibbonVerdict(False, "dt_irregular", m)
    if stats.p90_mm > max_w:
        return RibbonVerdict(False, "dt_p90_cap", m)
    return _floor_or(RibbonVerdict(True, "satin", m), stats, design_class, m)


def main(argv: list[str]) -> None:
    variants: list[str] = []
    names: list[str] = []
    it = iter(argv)
    for a in it:
        if a == "--variant":
            variants.append(next(it))
        else:
            names.append(a)
    total_flips = {"current": 0, **{v: 0 for v in variants}}
    total_changed = {v: 0 for v in variants}
    for name in names or list(curve_tiers.CASES):
        rel, kw = curve_tiers.CASES[name]
        runs = {}
        for tag, gate, turn in (("off", 20.0, 0.0), ("refined", 0.0, 15.0)):
            s4._CURVE_MIN_PX_PER_MM = gate
            cfg = dict(target_width_mm=80.0)
            cfg.update(kw)
            cfg["curve_turn_deg"] = turn
            result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**cfg))
            runs[tag] = (result, curve_tiers.shapes(result, plan))
        s4._CURVE_MIN_PX_PER_MM = 20.0
        (res_off, sh_off), (res_ref, sh_ref) = runs["off"], runs["refined"]
        dc = res_off.design_class
        polys_off = {r.shape_id: r.polygon for r in res_off.regions}
        polys_ref = {r.shape_id: r.polygon for r in res_ref.regions}
        pairs = [(a, b) for a, b in curve_tiers.pair(sh_off, sh_ref) if a and b]
        flips = {k: [] for k in total_flips}
        changed = {v: [] for v in variants}
        n_dt = 0
        t0 = time.perf_counter()
        for a, b in pairs:
            pa, pb = polys_off[a], polys_ref[b]
            va = classify_ribbon(pa, machine.SATIN_MAX_WIDTH_MM, design_class=dc)
            vb = classify_ribbon(pb, machine.SATIN_MAX_WIDTH_MM, design_class=dc)
            if va.reason in ("width_cap", "aspect") and vb.reason in ("width_cap", "aspect"):
                continue
            n_dt += 1
            if va.satin != vb.satin:
                flips["current"].append(f"{a} {va.reason} -> {vb.reason} w={va.metrics.get('ribbon_w', 0):.2f}")
            for v in variants:
                qa, qb = classify_variant(pa, v, dc), classify_variant(pb, v, dc)
                if qa.satin != qb.satin:
                    flips[v].append(f"{a} {qa.reason} -> {qb.reason}")
                if qa.satin != va.satin:
                    changed[v].append(f"{a} {va.reason} -> {qa.reason} w={w_(va):.2f} "
                                      f"expl {va.metrics.get('explained', 0):.2f}->{qa.metrics.get('explained', 0):.2f} "
                                      f"cv {va.metrics.get('dt_cv', 0):.2f}->{qa.metrics.get('dt_cv', 0):.2f} "
                                      f"elong {va.metrics.get('elongation', 0):.1f}->{qa.metrics.get('elongation', 0):.1f}")
        print(f"## {name} ({dc}) dt-population={n_dt} of {len(pairs)} shapes  "
              f"classify time {time.perf_counter() - t0:.2f}s")
        print("   verdict flips shipped->refined: " + "  ".join(f"{k}={len(x)}" for k, x in flips.items()))
        for k, x in flips.items():
            for line in x:
                print(f"      {k} flip: {line}")
        for v in variants:
            for line in changed[v]:
                print(f"      {v} changes a shipped verdict: {line}")
        for k in total_flips:
            total_flips[k] += len(flips[k])
        for v in variants:
            total_changed[v] += len(changed[v])
    print("TOTAL flips:", total_flips, " shipped verdicts changed:", total_changed)
    from tests.test_satin import BAR, C_STROKE, O_RING, T_SHAPE, _serrated_disc
    for nm, poly in (("BAR", BAR), ("O_RING", O_RING), ("C_STROKE", C_STROKE), ("T_SHAPE", T_SHAPE),
                     ("serrated0.3", _serrated_disc(10.0, 0.3)), ("serrated0.6", _serrated_disc(10.0, 0.6)),
                     ("serrated1.2", _serrated_disc(10.0, 1.2))):
        cur = classify_ribbon(poly, machine.SATIN_MAX_WIDTH_MM)
        print(f"archetype {nm:12s} current={cur.satin}/{cur.reason} "
              + " ".join(f"{v}={classify_variant(poly, v, 'flat').satin}/{classify_variant(poly, v, 'flat').reason}"
                         for v in variants))


def w_(v: RibbonVerdict) -> float:
    return float(v.metrics.get("ribbon_w", 0.0))


if __name__ == "__main__":
    main(sys.argv[1:])
