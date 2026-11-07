"""Trace a THREAD_MATCH_POOR offender back through the stages that coloured it.

Written 2026-11-07 for Fremont's surviving thread block: `0020 Black` at dE00
100 on art the grader reads as pure white, with `0015 White` loaded. That
block survived the excess yardstick (`thread_match_excess_gradient`), and the
dark-ink flags had been ruled out, so the cause was open.

For every offender row of every THREAD_MATCH_POOR finding, the probe reports
the region's colour at each stage:

  1. quantize / segment -- the artwork under the region's polygon as stage 3/4
     traced it, BEFORE `small_text.enlarge_small_text` touched it (a spy
     records every polygon going into that call), with the nearest loaded
     spool by the grader's own estimator (median per-pixel CIEDE2000);
  2. palette -- the spool the region carries and that spool's chart RGB;
  3. thread match -- the dE00 of that pre-enlargement artwork to the spool;
  4. enlarge -- whether `enlarge_small_text` changed the polygon, its scale,
     area before/after, and how much of the sewn polygon still lies on the
     traced letter;
  5. block -- the dE00 the preflight grader actually scores, on the polygon
     as SEWN, with the white/dark share of the pixels under it.

A row whose stage-3 dE is inside DELTA_E_VISIBLE and whose stage-5 dE is past
DELTA_E_CLEARLY_DIFFERENT is mislabelled by the GRADER, not by the palette:
the thread is right for the ink, and the grader is reading the ground the
enlargement grew over.

`--matrix` digitizes every `corpus_scorecard` FIXTURES x MATRIX entry once and
runs preflight twice over the same plan, default and with
`cfg.extra["thread_match_skip_enlarged_text"]`, counting the F entries that
carry a THREAD_MATCH_POOR block in each arm. The plan is not regraded, so its
md5 is printed once per entry; it cannot depend on a preflight-only key.

Both modes grade on the PRE-FLIP grader: `thread_match_grade_traced_letter`
(ON since 2026-11-07, Kent's flip) is pinned False, because the block this
probe traces is the one that flag cures, and the skip is priced against the
grader it was built beside (`_PRE_TRACED_GRADE`).

Usage (from digitizer/):
    .venv/bin/python -m tools.thread_match_fremont_probe
    .venv/bin/python -m tools.thread_match_fremont_probe photo/logo_hotel_fremont.webp --json out.json
    .venv/bin/python -m tools.thread_match_fremont_probe --matrix --json matrix.json
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core import small_text as _small_text  # noqa: E402
from digitizer_core.preflight import (DELTA_E_CLEARLY_DIFFERENT,  # noqa: E402
                                      DELTA_E_VISIBLE, THREAD_MATCH_POOR,
                                      _two_tone_view, run_preflight)
from digitizer_core.stage1_prep import prep  # noqa: E402
from digitizer_core.threads import chart_for, rgb_to_lab  # noqa: E402

TESTDATA = ROOT / "testdata"
FLAG = "thread_match_skip_enlarged_text"
DEFAULT_FIXTURES = ("photo/logo_hotel_fremont.webp", "art/logo_hotel_fremont_patch.png")
GARMENTS = ("left_chest", "hat_front")


def plan_md5(plan) -> str:
    """The house plan digest (`tools/held_hole_tongue.plan_md5`)."""
    h = hashlib.md5()
    for b, r in plan.iter_runs():
        h.update(f"{b.thread_number}|{r.shape_id}|{r.kind}|{r.trim}".encode())
        for x, y in r.points:
            h.update(f"{x:.6f},{y:.6f};".encode())
    return h.hexdigest()


class EnlargeSpy:
    """Record every region polygon going INTO `enlarge_small_text`, keyed by
    `id(region)`. The pipeline imports the function at call time
    (`from .small_text import enlarge_small_text`), so patching the module
    attribute reaches it. Shape ids are assigned after, so the id() is what
    joins the record to the finished region."""

    def __init__(self):
        self.before: dict[int, object] = {}
        self._orig = _small_text.enlarge_small_text

    def __enter__(self):
        def wrapped(regions, *a, **kw):
            for r in regions:
                self.before.setdefault(id(r), r.polygon)
            return self._orig(regions, *a, **kw)
        _small_text.enlarge_small_text = wrapped
        return self

    def __exit__(self, *exc):
        _small_text.enlarge_small_text = self._orig


def _mask(p, poly) -> np.ndarray:
    """The grader's rasterisation (`preflight._region_color_errors`): rounded
    vertices, holes cut, eroded one pixel, background excluded."""
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h, w = p.rgb.shape[:2]

    def to_px(c):
        a = np.asarray(c, np.float64)
        return np.round(np.column_stack([a[:, 0] * p.px_per_mm + cx,
                                         a[:, 1] * p.px_per_mm + cy])).astype(np.int32)
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [to_px(poly.exterior.coords)], 1)
    for ring in poly.interiors:
        cv2.fillPoly(m, [to_px(ring.coords)], 0)
    sel = (cv2.erode(m, np.ones((3, 3), np.uint8)) > 0) & ~p.bg_mask
    if not sel.any():
        sel = (m > 0) & ~p.bg_mask
    return sel


def _colour(p, sel, chart, thread_index: int, loaded: list[int]) -> dict:
    px = p.rgb[sel].reshape(-1, 3)
    if len(px) == 0:
        return {"pixels": 0}
    lab = rgb_to_lab(px.astype(np.float64))
    de = {chart[t].number: float(np.median(deltaE_ciede2000(lab, chart.lab[t].reshape(1, 3))))
          for t in loaded}
    lum = px.mean(axis=1)
    return {"pixels": int(len(px)),
            "median_rgb": [int(v) for v in np.median(px, axis=0)],
            "white_share": round(float((lum > 200).mean()), 3),
            "dark_share": round(float((lum < 80).mean()), 3),
            "de_to_thread": round(de[chart[thread_index].number], 1),
            "nearest_loaded": min(de, key=de.get),
            "de_by_loaded": {k: round(v, 1) for k, v in sorted(de.items())}}


#: The grader before Kent's 2026-11-07 flip of the traced-letter grade (see
#: the docstring): the block this probe traces only exists there.
_PRE_TRACED_GRADE = {"thread_match_grade_traced_letter": False}


def trace(fixture: str, garment: str, width_mm: float = 80.0) -> dict:
    path = TESTDATA / fixture
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment, **_PRE_TRACED_GRADE)
    with EnlargeSpy() as spy:
        result, plan = digitize(path, cfg)
    on = dataclasses.replace(cfg, extra={**(cfg.extra or {}), FLAG: True})
    rep_off = run_preflight(result, plan, cfg, image=path)
    rep_on = run_preflight(result, plan, on, image=path)
    # The grader's own view: the stage-1 re-read, two-tone snapped when the
    # pipeline snapped it (`preflight._two_tone_view`).
    p = _two_tone_view(prep(path, cfg, design_class=result.design_class), plan, cfg)
    chart = chart_for(cfg)
    by_id = {r.shape_id: r for r in result.regions}
    loaded = sorted({b.thread_index for b in plan.blocks if any(len(r.points) for r in b.runs)})

    rows = []
    for f in rep_off["findings"]:
        if f["code"] != THREAD_MATCH_POOR:
            continue
        for off in f["extra"]["regions"]:
            r = by_id.get(str(off["shape_id"]).split(" shade ")[0])
            if r is None:
                continue
            pre = spy.before.get(id(r))
            enlarged = bool(r.meta.get("small_text_enlarged"))
            pre_poly = pre if pre is not None else r.polygon
            stage_art = _colour(p, _mask(p, pre_poly), chart, r.thread_index, loaded)
            sewn = _colour(p, _mask(p, r.polygon), chart, r.thread_index, loaded)
            on_letter = (float(r.polygon.intersection(pre_poly).area / r.polygon.area)
                         if r.polygon.area else None)
            pre_ok = stage_art.get("de_to_thread", 1e9) <= DELTA_E_VISIBLE
            post_bad = sewn.get("de_to_thread", 0.0) > DELTA_E_CLEARLY_DIFFERENT
            verdict = ("grader reads the ground an enlarged letter grew over (thread is right)"
                       if enlarged and pre_ok and post_bad else
                       "palette/thread match: the traced art is off its spool" if not pre_ok else
                       "unexplained")
            rows.append({
                "finding_thread": f"{f['extra']['thread_number']} {f['extra']['thread_name']}",
                "severity": f["severity"],
                "shape_id": r.shape_id,
                "text_cluster": r.meta.get("text_cluster_id"),
                "1_quantize_art_before_enlarge": stage_art,
                "2_palette": {"thread": chart[r.thread_index].number,
                              "name": chart[r.thread_index].name,
                              "rgb": [int(v) for v in chart[r.thread_index].rgb]},
                "3_thread_match_de": stage_art.get("de_to_thread"),
                "4_enlarge": {"enlarged": enlarged,
                              "scale": r.meta.get("small_text_enlarged"),
                              "reset": bool(r.meta.get("small_text_reset")),
                              "widened_mm": r.meta.get("text_cluster_widened_mm"),
                              "area_before_mm2": round(float(pre_poly.area), 2),
                              "area_sewn_mm2": round(float(r.polygon.area), 2),
                              "sewn_share_on_traced_letter": None if on_letter is None else round(on_letter, 3)},
                "5_block_grader": sewn,
                "verdict": verdict,
            })

    def blocks(rep):
        return sorted(f"{f['extra']['thread_number']}:{f['severity']}"
                      for f in rep["findings"] if f["code"] == THREAD_MATCH_POOR)
    return {"fixture": fixture, "garment": garment, "width_mm": width_mm,
            "design_class": result.design_class, "plan_md5": plan_md5(plan),
            "enlarged_regions": sum(1 for r in result.regions if r.meta.get("small_text_enlarged")),
            "off": {"grade": rep_off["grade"], "score": rep_off["score"],
                    "thread_findings": blocks(rep_off),
                    "has_skip_metric": "thread_match_enlarged_text_skipped" in rep_off["metrics"]},
            "on": {"grade": rep_on["grade"], "score": rep_on["score"],
                   "thread_findings": blocks(rep_on),
                   "skipped": rep_on["metrics"].get("thread_match_enlarged_text_skipped")},
            "rows": rows}


def matrix() -> dict:
    from tools.corpus_scorecard import FIXTURES, MATRIX
    out, f_block = {}, {"off": 0, "on": 0}
    for fixture in FIXTURES:
        for kw in MATRIX:
            path = TESTDATA / fixture
            if not path.exists():
                continue
            cfg = PipelineConfig(**{**kw, **_PRE_TRACED_GRADE})
            on = dataclasses.replace(cfg, extra={**(cfg.extra or {}), FLAG: True})
            try:
                result, plan = digitize(path, cfg)
                arms = {"off": run_preflight(result, plan, cfg, image=path),
                        "on": run_preflight(result, plan, on, image=path)}
            except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the run
                out[f"{fixture}/{kw['garment_id']}"] = {"error": repr(exc)}
                continue
            row = {"md5": plan_md5(plan)}
            for k, rep in arms.items():
                tb = sum(1 for f in rep["findings"]
                         if f["code"] == THREAD_MATCH_POOR and f["severity"] == "block")
                row[k] = {"grade": rep["grade"], "score": rep["score"], "tmp_blocks": tb}
                if rep["grade"] == "F" and tb:
                    f_block[k] += 1
            row["skipped"] = arms["on"]["metrics"].get("thread_match_enlarged_text_skipped")
            out[f"{fixture}/{kw['garment_id']}"] = row
            print(f"{fixture:45s} {kw['garment_id']:10s} {row['off']['grade']} {row['off']['score']:>4} "
                  f"tmp {row['off']['tmp_blocks']} -> {row['on']['grade']} {row['on']['score']:>4} "
                  f"tmp {row['on']['tmp_blocks']} skipped {row['skipped']} md5 {row['md5'][:8]}", flush=True)
    print(f"F entries carrying a THREAD_MATCH_POOR block: {f_block['off']} -> {f_block['on']}")
    return {"entries": out, "f_with_tmp_block": f_block}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("fixtures", nargs="*", default=list(DEFAULT_FIXTURES))
    ap.add_argument("--garment", action="append", choices=GARMENTS)
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    if a.matrix:
        data = matrix()
    else:
        data = [trace(fx, g, a.width) for fx in a.fixtures for g in (a.garment or GARMENTS)]
        for t in data:
            print(f"{t['fixture']} {t['garment']} [{t['design_class']}] md5 {t['plan_md5'][:8]} "
                  f"enlarged {t['enlarged_regions']}: {t['off']['grade']} {t['off']['score']} "
                  f"{t['off']['thread_findings']} -> flag {t['on']['grade']} {t['on']['score']} "
                  f"{t['on']['thread_findings']} (skipped {t['on']['skipped']})")
            for r in t["rows"]:
                a1, b5 = r["1_quantize_art_before_enlarge"], r["5_block_grader"]
                e = r["4_enlarge"]
                print(f"  {r['finding_thread']} {r['severity']} {r['shape_id']} ({r['text_cluster']})")
                print(f"    1 art before enlarge  rgb {a1.get('median_rgb')} white {a1.get('white_share')} "
                      f"nearest {a1.get('nearest_loaded')} {a1.get('de_by_loaded')}")
                print(f"    2 palette             {r['2_palette']['thread']} {r['2_palette']['name']} "
                      f"rgb {r['2_palette']['rgb']}")
                print(f"    3 thread match dE     {r['3_thread_match_de']}")
                print(f"    4 enlarge             x{e['scale']} reset {e['reset']} "
                      f"{e['area_before_mm2']} -> {e['area_sewn_mm2']} mm2, "
                      f"on traced letter {e['sewn_share_on_traced_letter']}")
                print(f"    5 grader (as sewn)    rgb {b5.get('median_rgb')} white {b5.get('white_share')} "
                      f"dE {b5.get('de_to_thread')} nearest {b5.get('nearest_loaded')}")
                print(f"    verdict: {r['verdict']}")
    if a.json:
        a.json.write_text(json.dumps(data, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
