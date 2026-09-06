"""Which shapes does `revalidate_threads` REFUSE to re-ask, and would the
answer have changed?

`stage4_vectorize.revalidate_threads` is the fix for a thread chosen at stage 2
from pixels the shape no longer covers after simplification (fix #6.3,
2026-08-11). It is gated on `THREAD_REVALIDATE_MIN_PX = 200`.
`preflight._MIN_COLOR_PIXELS` is **50**. Every shape between those two numbers
can be scored and BLOCKED by preflight and never corrected by stage 4, and that
gap is where `THREAD_MATCH_POOR` puts two of the corpus's seven F grades
(MASTER_SCOPE 28, scope-history 2026-09-06).

This tool wraps the real function — it does not reimplement it. For each shape
it records the gate actually hit:

    asked      >= THREAD_REVALIDATE_MIN_PX, the function did its job
    enclosed   `meta["enclosed_background"]`, skipped by design (its colour IS
               the background's; re-matching it is a category error)
    refused    under the pixel floor
    no_px      the final polygon rasterises to nothing

and for every `refused` shape asks the question anyway, using the function's
OWN estimator (median per-pixel dE00 over `_sample_lab`), its own argmin —
palette-restricted on photo classes exactly as the function restricts it — and
its own `THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00`. So "would move" means the
shipped function would have re-snapped this shape had the floor let it.

    python -m tools.revalidate_floor                 # the seven F fixtures
    python -m tools.revalidate_floor photo/foo.png   # one, with the shape list

Reading it: a fixture with a large `refused` column is one whose thread grade
is a floor artefact rather than a palette or yardstick problem. A fixture with
`refused` 0 and a large `encl` column (gaulke_roofing) is a different story
entirely — see defect 27.
"""
from __future__ import annotations

import collections
import pathlib
import sys

import numpy as np
from skimage.color import deltaE_ciede2000

from digitizer_core import pipeline as pl
from digitizer_core import run_stages
from digitizer_core import stage4_vectorize as s4
from digitizer_core.config import PipelineConfig, is_photographic
from digitizer_core.threads import chart_for, rgb_to_lab

# preflight's own floor, quoted rather than imported so this tool keeps working
# if that module moves; the point of the number here is the COMPARISON.
PREFLIGHT_MIN_COLOR_PX = 50

TESTDATA = pathlib.Path(__file__).resolve().parents[1] / "testdata"

# The seven fixtures THREAD_MATCH_POOR grades F 0 (2026-09-06).
F_FIXTURES = [
    "photo/logo_golden_tee.jpg",
    "photo/drone_render.png",
    "photo/region_blobs.png",
    "photo/summit_badge.png",
    "photo/logo_gaulke_roofing.png",
    "photo/logo_bridge_bar.jpg",
    "photo/screenshot_phone_ui_golke.jpg",
]


def _probe(log: list):
    """A `revalidate_threads` stand-in that records, then delegates.

    Patched over `pipeline.revalidate_threads`, NOT the stage-4 attribute:
    `pipeline` binds the name at import, so patching the module the function
    lives in does nothing. (Cost me a silent empty run.)
    """
    real = pl.revalidate_threads

    def probe(regions, p, cfg, *, palette_indices=None, design_class="flat"):
        chart = chart_for(cfg)
        x0, y0, x1, y1 = p.art_bbox
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        shape = p.rgb.shape[:2]
        flat_lab = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(*shape, 3)
        allowed = None
        if is_photographic(cfg, design_class) and palette_indices:
            allowed = np.unique(np.asarray(list(palette_indices), np.int64))

        for r in regions:
            if r.meta.get("enclosed_background"):
                log.append(("enclosed", r.shape_id, r.area_mm2, 0, None, None, 0.0))
                continue
            fp = s4._region_footprint(r, shape, cx, cy, p.px_per_mm)
            n = int(fp.sum())
            if n >= s4.THREAD_REVALIDATE_MIN_PX:
                log.append(("asked", r.shape_id, r.area_mm2, n, None, None, 0.0))
                continue
            if n == 0:
                log.append(("no_px", r.shape_id, r.area_mm2, 0, None, None, 0.0))
                continue
            per_spool = np.median(
                deltaE_ciede2000(s4._sample_lab(flat_lab[fp])[:, None, :],
                                 chart.lab[None, :, :]), axis=0)
            best = (int(np.argmin(per_spool)) if allowed is None
                    else int(allowed[np.argmin(per_spool[allowed])]))
            gain = (float(per_spool[r.thread_index]) - float(per_spool[best])
                    if best != r.thread_index else 0.0)
            log.append(("refused", r.shape_id, r.area_mm2, n,
                        chart[r.thread_index].number, chart[best].number, gain))
        # The real pass still runs, so the design this measures is the shipped
        # one — the probe must not change a single stitch.
        return real(regions, p, cfg, palette_indices=palette_indices,
                    design_class=design_class)

    return probe, real


def run(fixture: str) -> tuple[int, list]:
    log: list = []
    probe, real = _probe(log)
    pl.revalidate_threads = probe
    try:
        result = run_stages(TESTDATA / fixture, PipelineConfig())
    finally:
        pl.revalidate_threads = real
    return len(result.regions), log


def main(argv: list[str]) -> int:
    fixtures = argv[1:] or F_FIXTURES
    gate = s4.THREAD_REVALIDATE_MIN_PX
    print(f"THREAD_REVALIDATE_MIN_PX = {gate}   "
          f"preflight._MIN_COLOR_PIXELS = {PREFLIGHT_MIN_COLOR_PX}   "
          f"min gain = {s4.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00}\n")
    print(f"{'fixture':<34}{'regs':>5}{'asked':>7}{'encl':>6}{'refused':>9}"
          f"{f'{PREFLIGHT_MIN_COLOR_PX}-{gate - 1}':>9}{'would move':>12}"
          f"{'best gain':>11}")
    for fx in fixtures:
        n_regions, log = run(fx)
        c = collections.Counter(e[0] for e in log)
        refused = [e for e in log if e[0] == "refused"]
        band = [e for e in refused if PREFLIGHT_MIN_COLOR_PX <= e[3] < gate]
        movers = [e for e in refused
                  if e[6] >= s4.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00]
        best = max((e[6] for e in movers), default=0.0)
        print(f"{pathlib.Path(fx).name:<34}{n_regions:>5}{c['asked']:>7}"
              f"{c['enclosed']:>6}{len(refused):>9}{len(band):>9}"
              f"{len(movers):>12}{best:>11.1f}")
        if len(fixtures) == 1:
            print()
            for _g, sid, area, n, had, want, gain in sorted(
                    movers, key=lambda e: -e[6]):
                print(f"    {sid:>12} {area:8.2f} mm^2 {n:5d} px  "
                      f"wears {had} -> would take {want}   gain {gain:5.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
