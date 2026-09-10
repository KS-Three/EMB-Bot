#!/usr/bin/env python
"""Which regions have a mean colour no pixel of them carries?

Step 6 of `stage2_photo_segment` hands `select_palette` ONE Lab per kept
region, and until 2026-09-10 that was always the region's MEAN. A region full
of inclusions does not carry its own mean anywhere: Bridge Bar's yellow disc
is (251, 235, 65) by its pixels, 1.0 ΔE00 from `0501` Sun, and the mean the
palette saw is (223, 220, 77) — the black lettering, the bird and the rope
inside the disc contribute their anti-aliased edges and grey halos. The
k-medoids palette then rightly picks `6031` Limelight for the colour it was
handed, 7.0 ΔE00 off a logo's MAIN colour, and since
`bind_resnap_all_classes` shipped ON (2026-09-10) the re-snap can no longer
correct it downstream.

This counts the population that defect belongs to, and prices the two robust
arms `cfg.region_color` offers against the shipped one. It changes nothing:
every arm is computed on the SAME regions, from the same run, because the
region set is settled by the RAG merge before this colour is ever taken.

    .venv/bin/python -m tools.region_color_census                 # whole corpus
    .venv/bin/python -m tools.region_color_census --fixture bridge_bar
    .venv/bin/python -m tools.region_color_census --colors 12 --mm 100

Three numbers per region, all in ΔE00 on the chart the config selects:

  `mean-modal`   how far the shipped colour sits from the region's own
                 dominant colour. This is the defect's size.
  `spool`        the chart entry each arm's colour snaps to on its own
                 (nearest_index). A row where the arms disagree is a row
                 where the palette is being argued to about a different
                 thread — necessary for a cone to move, not sufficient,
                 since k-medoids answers over every region at once.
  `share`        the fraction of the region's pixels inside the modal ball.
                 A low share on a big region is the signature: most of the
                 region is one colour and the mean is somewhere else.

Read `spool` disagreement as the upper bound and the flip sheet's arm as the
real reading — this tool never runs the palette.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np                                            # noqa: E402
from skimage.color import deltaE_ciede2000                    # noqa: E402

from digitizer_core import stage2_photo_segment as seg        # noqa: E402
from digitizer_core.config import PipelineConfig              # noqa: E402
from digitizer_core.pipeline import digitize                  # noqa: E402
from digitizer_core.threads import chart_for                  # noqa: E402

ARMS = ("mean", "median", "modal")
REPORT_DE00 = 2.0          # rows quieter than this are not worth a line


def _de00(a: np.ndarray, b: np.ndarray) -> float:
    return float(deltaE_ciede2000(np.asarray(a).reshape(1, 3),
                                  np.asarray(b).reshape(1, 3))[0])


def census_one(path: Path, cfg: PipelineConfig) -> list[dict]:
    """Digitize `path` once, recording every region colour step 6 asks for.

    The recorder wraps `region_lab` and returns the arm the config asked for,
    so the run itself is exactly the run without this tool attached.
    """
    rows: list[dict] = []
    chart = chart_for(cfg)
    original = seg.region_lab

    def recorder(px: np.ndarray, method: str = "mean") -> np.ndarray:
        labs = {arm: original(px, arm) for arm in ARMS}
        lab = seg.rgb_to_lab(px.reshape(-1, 3))
        mode = seg._geometric_median(lab)
        near = deltaE_ciede2000(
            lab, np.repeat(mode[None, :], len(lab), 0)) <= seg._REGION_MODAL_DE00
        rows.append({
            "px": int(len(px)),
            "share": float(near.mean()),
            "labs": labs,
            "spools": {arm: chart.nearest_index(labs[arm]) for arm in ARMS},
            "mean_modal": _de00(labs["mean"], labs["modal"]),
            "mean_median": _de00(labs["mean"], labs["median"]),
            "median_modal": _de00(labs["median"], labs["modal"]),
        })
        return labs[method]

    seg.region_lab = recorder
    try:
        digitize(str(path), cfg)
    finally:
        seg.region_lab = original
    return rows


def report(name: str, rows: list[dict], chart) -> dict:
    total_px = sum(r["px"] for r in rows) or 1
    moved = [r for r in rows if r["mean_modal"] >= REPORT_DE00]
    spool_split = [r for r in rows
                   if len({r["spools"][a] for a in ARMS}) > 1]
    print(f"\n{name}: {len(rows)} regions, "
          f"{len(moved)} at or past {REPORT_DE00:.0f} dE00 from their own mode, "
          f"{len(spool_split)} whose arms snap to different spools")
    worst = sorted(rows, key=lambda r: -r["mean_modal"])[:8]
    if worst and worst[0]["mean_modal"] >= REPORT_DE00:
        print(f"  {'px':>8} {'area%':>6} {'share':>6} {'mean-modal':>10} "
              f"{'mean ->':<21} {'median ->':<21} {'modal ->':<21}")
        for r in worst:
            if r["mean_modal"] < REPORT_DE00:
                break
            names = {arm: chart.threads[r["spools"][arm]] for arm in ARMS}
            print(f"  {r['px']:>8} {100 * r['px'] / total_px:>5.1f}% "
                  f"{r['share']:>6.2f} {r['mean_modal']:>10.1f} "
                  + " ".join(f"{t.number + ' ' + t.name:<21}"
                             for t in (names["mean"], names["median"],
                                       names["modal"])))
    # The confident population: BOTH robust arms name the same thread and
    # the mean names a different one. A row here is a region where the
    # estimator choice does not matter and the shipped answer is the odd one
    # out — the count to quote when arguing that the mean is the error.
    agreed = [r for r in rows
              if r["spools"]["median"] == r["spools"]["modal"] != r["spools"]["mean"]]
    return {
        "regions": len(rows),
        "moved": len(moved),
        "spool_split": len(spool_split),
        "agreed": len(agreed),
        "agreed_area": sum(r["px"] for r in agreed) / total_px,
        # Area-weighted, because a 40-px sliver being wrong costs nothing and
        # the disc that carries a logo is one region.
        "moved_area": sum(r["px"] for r in moved) / total_px,
        "worst": max((r["mean_modal"] for r in rows), default=0.0),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default=None,
                    help="substring; default is every corpus fixture")
    ap.add_argument("--colors", type=int, default=6,
                    help="max_colors (Studio default 6)")
    ap.add_argument("--mm", type=float, default=80.0)
    args = ap.parse_args(argv)

    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES

    names = [f for f in FIXTURES
             if args.fixture is None or args.fixture in f]
    if not names:
        print(f"no fixture matches {args.fixture!r}")
        return 2

    cfg = PipelineConfig(target_width_mm=args.mm, garment_id="left_chest",
                         max_colors=args.colors)
    chart = chart_for(cfg)
    summary: dict[str, dict] = {}
    for name in names:
        path = TESTDATA / name
        if not path.exists():
            print(f"  (missing: {name})")
            continue
        rows = census_one(path, cfg)
        if not rows:
            print(f"\n{name}: flat lane - no SLIC+RAG regions, nothing to read")
            continue
        summary[name] = report(name, rows, chart)

    if summary:
        print(f"\n=== corpus, max_colors={args.colors}, {args.mm:.0f} mm ===")
        print(f"  {'fixture':<38} {'regions':>7} {'>=2dE':>6} {'area%':>6} "
              f"{'spools':>7} {'agreed':>7} {'ag.area':>8} {'worst':>6}")
        for name, s in summary.items():
            print(f"  {name:<38} {s['regions']:>7} {s['moved']:>6} "
                  f"{100 * s['moved_area']:>5.1f}% {s['spool_split']:>7} "
                  f"{s['agreed']:>7} {100 * s['agreed_area']:>7.1f}% "
                  f"{s['worst']:>6.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
