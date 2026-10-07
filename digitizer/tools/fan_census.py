#!/usr/bin/env python
"""Fan census: over-long, radiating satin crosses per text-tagged letter, under
the flags that bear on a lettering junction, over the corpus.

Built 2026-10-07 for MASTER_SCOPE defect 59 (Becker's N under
`letterform_priors`: the diagonal / right-stem junction sewn as a fan of long
crosses). The question it answers is not "is there a fan" but "which
construction owns it": the skeleton satin tier as shipped, that tier with
`satin_join_square`, the Columns lane (`lettering_columns`, text sewn as
outline-cut Columns, no skeleton tier), and both.

Per text-tagged letter (`meta.text_candidate`), every satin cross (two
consecutive points of a `satin` run after `strip_ties` / `strip_splits`):

- **over-long**: longer than `FAN_LEN` x (W + 2 x PULL), W = 2 area /
  perimeter (the outline-cut spike's stroke width) and PULL the fabric's
  rail compensation, so a thin stroke's pulled cross is not read as long;
- **fan**: over-long AND its angle rotates more than `FAN_TURN` deg across a
  window of five crosses either side -- a smooth fan turns a few degrees per
  cross, so adjacent differences miss it (the first version of this tool
  read Becker's N as 1 fan cross; the window reads 3, and the over-long
  count 45 of 213, which is what the render shows).

A letter is a "long letter" / "fan letter" when three or more of its crosses
qualify and they carry over 5% of its thread. Bridge's eight tagged shapes
are segmentation blobs, not letters, and read as fans under every arm.

    .venv/Scripts/python tools/fan_census.py [case ...] [--arms shipped,join_square,columns,both]
                                             [--out DIR] [--render-n]

`--out` (default `scratch_fan_census/` at the repo root, gitignored by the
`scratch_*` pattern -- the renders hold client artwork) gets
`fan_census.json` (per letter: the cross lengths and angles, so the bars can
be re-read without a re-run) and, with `--render-n`, `becker_N_<arms>.png`:
Becker's N at the corpus size, every cross drawn, the over-long ones in red.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig                      # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from digitizer_core.stage6_satin import strip_splits           # noqa: E402
from digitizer_core.stitches import strip_ties                 # noqa: E402
from tools.thin_strokes import corpus_cases                    # noqa: E402

FAN_LEN = 1.6
FAN_TURN = 12.0
PULL = 0.3
WINDOW = 5
ARMS: dict[str, dict] = {
    "shipped": {},
    "join_square": {"satin_join_square": True},
    "columns": {"lettering_columns": True},
    "both": {"satin_join_square": True, "lettering_columns": True},
}
ORDER = ["becker", "bridge", "gaulke", "drone", "enthusiast", "fremont", "tires"]


def crosses_of(plan, sid: str) -> tuple[list, Counter]:
    kinds: Counter = Counter()
    cr = []
    for _b, run in plan.iter_runs():
        if run.shape_id != sid:
            continue
        kinds[run.kind] += 1
        if run.kind != "satin":
            continue
        pts = np.asarray(strip_splits(strip_ties(list(run.points))), float)
        for i in range(0, len(pts) - 1, 2):
            cr.append((pts[i], pts[i + 1]))
    return cr, kinds


def fan_stats(cr: list, W: float) -> dict:
    L = np.array([math.dist(a, b) for a, b in cr]) if cr else np.zeros(0)
    ang = (np.array([math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180 for a, b in cr])
           if cr else np.zeros(0))
    bar = FAN_LEN * (W + 2 * PULL)

    def adiff(i: int, j: int) -> float:
        d = abs(ang[i] - ang[j]) % 180
        return min(d, 180 - d)

    n_long = n_fan = 0
    long_len = fan_len = 0.0
    for i in range(len(cr)):
        if L[i] <= bar:
            continue
        n_long += 1
        long_len += L[i]
        lo, hi = max(0, i - WINDOW), min(len(cr) - 1, i + WINDOW)
        if max(adiff(i, lo), adiff(i, hi)) > FAN_TURN:
            n_fan += 1
            fan_len += L[i]
    tot = float(L.sum()) if len(L) else 0.0
    return dict(crosses=len(cr), bar=bar,
                long_crosses=n_long, long_share=long_len / tot if tot else 0.0,
                fan_crosses=n_fan, fan_share=fan_len / tot if tot else 0.0,
                max_over_W=float(L.max() / W) if len(L) and W else 0.0, thread=tot,
                lengths=[round(float(x), 2) for x in L], angles=[round(float(x), 1) for x in ang])


def marine_n(res):
    """Becker's N: the fifth of the six MARINE letters by x (14-19 mm tall at
    the corpus's 100 mm)."""
    marine = sorted([r for r in res.regions if r.meta.get("text_candidate")
                     and 14 < (r.polygon.bounds[3] - r.polygon.bounds[1]) < 19],
                    key=lambda r: r.polygon.centroid.x)
    return marine[4] if len(marine) >= 5 else None


def render_letter(region, plan, label: str, ppm: int = 24):
    import cv2
    poly = region.polygon
    b = poly.bounds
    x0, y0 = b[0] - 1.5, b[1] - 1.5
    Wd, H = int((b[2] - b[0] + 3) * ppm), int((b[3] - b[1] + 3) * ppm)
    im = np.full((H, Wd, 3), 255, np.uint8)

    def px(P):
        return np.round((np.asarray(P, float) - (x0, y0)) * ppm).astype(np.int32)

    cr, _k = crosses_of(plan, region.shape_id)
    W = 2 * poly.area / poly.length
    st = fan_stats(cr, W)
    for (a, c), L in zip(cr, st["lengths"]):
        col = (0, 0, 220) if L > st["bar"] else (90, 90, 90)
        cv2.line(im, tuple(px(a)), tuple(px(c)), col, 1, cv2.LINE_AA)
    for ring in [poly.exterior, *poly.interiors]:
        cv2.polylines(im, [px(ring.coords)], True, (200, 60, 0), 2, cv2.LINE_AA)
    bar = np.full((22, Wd, 3), 230, np.uint8)
    cv2.putText(bar, f"{label}: crosses {st['crosses']} long {st['long_crosses']} fan "
                     f"{st['fan_crosses']} ({st['fan_share']:.0%}) max {st['max_over_W']:.1f}W",
                (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack([bar, im])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*", help="corpus case names (default: the seven)")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--out", default=str(ROOT.parent / "scratch_fan_census"))
    ap.add_argument("--render-n", action="store_true", help="Becker's N per arm, crosses drawn")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    arms = {k: ARMS[k] for k in a.arms.split(",")}
    cases = {c[0]: c for c in corpus_cases()}
    names = a.cases or [n for n in ORDER if n in cases]
    report: dict = {}
    panels = []
    for name in names:
        _n, path, width, garment = cases[name]
        report[name] = {}
        for arm, kw in arms.items():
            t = time.time()
            cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6, **kw)
            res = run_stages(path, cfg)
            plan = plan_stitches(res, cfg)
            letters = [r for r in res.regions if r.meta.get("text_candidate")]
            rows = []
            kinds_all: Counter = Counter()
            for r in letters:
                W = 2 * r.polygon.area / max(r.polygon.length, 1e-9)
                cr, kinds = crosses_of(plan, r.shape_id)
                kinds_all += kinds
                st = fan_stats(cr, W)
                st.update(shape_id=r.shape_id, char=r.meta.get("ocr_char"), W=W,
                          prior=r.meta.get("letterform_prior"))
                rows.append(st)
            long_letters = sum(1 for s in rows if s["long_share"] > 0.05 and s["long_crosses"] >= 3)
            fan_letters = sum(1 for s in rows if s["fan_share"] > 0.05 and s["fan_crosses"] >= 3)
            tot = sum(s["thread"] for s in rows)
            report[name][arm] = dict(
                letters=len(rows), long_letters=long_letters, fan_letters=fan_letters,
                long_crosses=sum(s["long_crosses"] for s in rows),
                fan_crosses=sum(s["fan_crosses"] for s in rows),
                long_share=sum(s["long_share"] * s["thread"] for s in rows) / tot if tot else 0.0,
                fan_share=sum(s["fan_share"] * s["thread"] for s in rows) / tot if tot else 0.0,
                stitches=plan.stats.stitch_count, trims=plan.stats.trims,
                kinds=dict(kinds_all), per=rows, secs=round(time.time() - t))
            e = report[name][arm]
            print(f"{name:10} {arm:11} letters {e['letters']:2} long-letters {e['long_letters']:2} "
                  f"long {e['long_crosses']:4} ({e['long_share']:.1%}) fan-letters {e['fan_letters']:2} "
                  f"fan {e['fan_crosses']:4} ({e['fan_share']:.1%}) st {e['stitches']} trims {e['trims']} "
                  f"{e['secs']}s", flush=True)
            if a.render_n and name == "becker":
                n = marine_n(res)
                if n is not None:
                    panels.append(render_letter(n, plan, arm))
            (out / "fan_census.json").write_text(json.dumps(report, indent=1, default=str),
                                                 encoding="utf-8")
    if panels:
        import cv2
        Hm = max(p.shape[0] for p in panels)
        row = []
        for p in panels:
            row.append(np.vstack([p, np.full((Hm - p.shape[0], p.shape[1], 3), 255, np.uint8)]))
            row.append(np.full((Hm, 8, 3), 120, np.uint8))
        path = out / f"becker_N_{a.arms.replace(',', '_')}.png"
        cv2.imwrite(str(path), np.hstack(row))
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
