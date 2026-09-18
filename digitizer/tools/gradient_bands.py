#!/usr/bin/env python
"""What the gradient-band rule changes across the corpus, and the population
it judged.

For every fixture, run stages 0-4 on the flat lane (forced flat, as the
pro-parity harness does for the stage-0-misrouted logos). `run_stages` tags
bands itself and leaves `meta["gradient_band_soft"]` on EVERY ribbon-shaped
candidate, so this reads the whole judged population back — tagged or not —
next to what the classifier said about each shape. Only rows where the
classifier said SATIN and the rule tagged the shape are demotions, the rule's
whole effect; every one is a shape a person should look at. The untagged
rows near the line are the second thing to look at: a real stroke with a
high soft share is the false positive the threshold has to stay clear of.

  .venv/Scripts/python tools/gradient_bands.py                 # every fixture at 80 mm
  .venv/Scripts/python tools/gradient_bands.py --render OUTDIR # plus a crop per demotion
  .venv/Scripts/python tools/gradient_bands.py --all           # list every candidate, not just tagged

Written 2026-09-09 with the rule; DOCTRINE's classifier entries say why a
verdict change ships only with this survey beside it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.gradient_band import is_gradient_band  # noqa: E402
from digitizer_core.machine import SATIN_MAX_WIDTH_MM  # noqa: E402
from digitizer_core.pipeline import run_stages  # noqa: E402
from digitizer_core.stage6_satin import classify_ribbon, ribbon_width_mm  # noqa: E402
from digitizer_core.threads import chart_for  # noqa: E402

TESTDATA = ROOT / "testdata"
FIXTURES = sorted([*TESTDATA.glob("*.png"), *TESTDATA.glob("photo/*.png"),
                   *TESTDATA.glob("photo/*.jpg")])


def survey(path: Path, width_mm: float, brand: str | None):
    cfg = PipelineConfig(target_width_mm=width_mm, forced_class="flat",
                         thread_brand=brand)
    result = run_stages(path, cfg)
    chart = chart_for(cfg)
    satin_max = cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    rows = []
    for r in result.regions:
        if "gradient_band_soft" not in r.meta:
            continue
        v = classify_ribbon(r.polygon, satin_max, design_class="flat",
                            per_stroke=cfg.satin_per_stroke)
        rows.append(dict(
            shape=r.shape_id, area=r.polygon.area, width=ribbon_width_mm(r.polygon),
            thread=f"{r.thread_number} {chart[r.thread_index].name}",
            soft=r.meta["gradient_band_soft"], tagged=is_gradient_band(r),
            verdict=v.reason, satin=v.satin, region=r,
        ))
    return len(result.regions), rows, result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--brand", default=None)
    ap.add_argument("--all", action="store_true", help="list every judged candidate")
    ap.add_argument("--render", type=Path, default=None,
                    help="write a crop per DEMOTED shape into this directory")
    ap.add_argument("fixtures", nargs="*")
    args = ap.parse_args()
    fixtures = [Path(f) for f in args.fixtures] or FIXTURES

    tot_regions = tot_judged = tot_tagged = tot_demoted = 0
    print(f"{'fixture':<32}{'regions':>8}{'judged':>7}{'tagged':>7}{'demoted':>8}")
    demotions = []
    for f in fixtures:
        try:
            n, rows, result = survey(f, args.width, args.brand)
        except Exception as e:  # a fixture the flat lane cannot take is a row, not a crash
            print(f"{f.name:<32}  ERROR {type(e).__name__}: {e}")
            continue
        tagged = [r for r in rows if r["tagged"]]
        dem = [r for r in tagged if r["satin"]]
        tot_regions += n
        tot_judged += len(rows)
        tot_tagged += len(tagged)
        tot_demoted += len(dem)
        print(f"{f.name:<32}{n:>8}{len(rows):>7}{len(tagged):>7}{len(dem):>8}")
        for r in sorted(rows, key=lambda r: -r["soft"]):
            if not (args.all or r["tagged"]):
                continue
            mark = "   <-- DEMOTED" if r["tagged"] and r["satin"] else ("   tagged (was fill anyway)" if r["tagged"] else "")
            print(f"    {r['shape']:<12} {r['area']:7.1f} mm2  w {r['width']:4.2f}  soft {r['soft']:.2f}  "
                  f"{r['thread']:<22} classifier={r['verdict']}{mark}")
        demotions.extend((f, r, result) for r in dem)
    print(f"\nTOTAL regions {tot_regions}  judged {tot_judged}  tagged {tot_tagged}  demoted {tot_demoted}")

    if args.render and demotions:
        import cv2
        import numpy as np
        args.render.mkdir(parents=True, exist_ok=True)
        PX = 30.0
        chart = chart_for(PipelineConfig(thread_brand=args.brand))
        for f, r, result in demotions:
            poly = r["region"].polygon
            x0, y0, x1, y1 = poly.bounds
            x0 -= 4; y0 -= 4; x1 += 4; y1 += 4
            W, H = int((x1 - x0) * PX), int((y1 - y0) * PX)
            img = np.full((H, W, 3), 245, np.uint8)

            def to_px(pts):
                return np.array([[(x - x0) * PX, (y - y0) * PX] for x, y in pts],
                                np.int32).reshape(-1, 1, 2)

            for q in result.regions:
                g0 = q.polygon
                rgb = chart[q.thread_index].rgb
                col = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
                for g in (list(g0.geoms) if hasattr(g0, "geoms") else [g0]):
                    cv2.fillPoly(img, [to_px(list(g.exterior.coords))], col)
                    for hole in g.interiors:
                        cv2.fillPoly(img, [to_px(list(hole.coords))], (245, 245, 245))
            for g in (list(poly.geoms) if hasattr(poly, "geoms") else [poly]):
                cv2.polylines(img, [to_px(list(g.exterior.coords))], True, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(img, f"{f.name} {r['shape']} {r['thread']} {r['area']:.0f}mm2 w{r['width']:.2f} "
                        f"soft {r['soft']:.2f} was {r['verdict']}",
                        (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
            out = args.render / f"{f.stem}_{r['shape']}.png"
            cv2.imwrite(str(out), img)
            print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
