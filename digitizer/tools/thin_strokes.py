#!/usr/bin/env python
"""Thin-stroke recall: the strokes the ARTWORK carries under the detail
floor, and how much of each one the plan actually sews. Read on the stitches.

PR 1 of `docs/superpowers/plans/2026-09-08-real-logo-lane-and-thin-strokes.md`
(items 1 and 2 of `docs/quality-review-2026-09-08.md`, Kent's picks).

Why a new instrument. Kent's "whole elements missing" theme (7 of 14 designs,
`docs/kent-review-2026-08-27.md`) is mostly small lettering and line art —
Fremont's tagline, EST 1895 and rope, Bridge Bar's BAR & RESTAURANT — and no
instrument in this repo can see it lost:

  * `preflight.ARTWORK_UNCOVERED` is scoped to shapes the design already sews,
    so an element that never became a region is invisible to it.
  * `tools/dropped_elements.py` OPENS its disagreement mask by `HALO_OPEN_PX`
    = 5 at 10 px/mm, i.e. 0.5 mm, to drop the boundary hairline every shape
    carries — which also erases every lost stroke under 0.5 mm before it is
    counted. That is why Fremont reads 0.2% lost on a design whose small text
    Kent calls "completely lost".

So this reads the strokes FIRST, from the artwork, and then asks the plan
about each one. No opening anywhere.

What counts as a thin stroke. The artwork is read with the flat lane's own
quantizer (`stage2_quantize.quantize`: k-means, majority filter, phantom-blend
dissolve, colour cap), whichever lane the design was routed down — an
independent reading of the ink, not the routed segmenter's regions, which on
the photo lane have already lost the strokes this exists to find. Each
label's connected components are skeletonised; a component whose median full
width along its skeleton (twice the exact distance transform) is under
`cfg.min_detail_mm` — the linear size of the small-shape floor — and whose
skeleton is at least `RUN_MIN_LOOP_MM / 2` long (the loop constant applied to
an open stroke, which a bean run walks there and back) is a thin stroke. No
new constant: both numbers already gate the run tier.

The width is read on the SKELETON as a half-width and doubled here. Quote the
doubled number; `textcluster.py`'s docstring records the trap of quoting the
raw `dist/scale` radius as a width, and `docs/quality-review-2026-09-08.md`
§2b records the day it happened.

Recall. The plan's needle-down segments — consecutive `CMD_STITCH` points in
`stitches.iter_machine_commands`, the same chain rule the DST encoder uses,
so a jump or trim never paints thread — are drawn per block at
`COVERAGE_THREAD_W_MM`, and a stroke's skeleton pixel counts as sewn when it
lies inside the thread of a block within `TEXT_CLUSTER_DELTA_E_MAX` CIEDE2000
of the stroke's own colour. A stroke sewn in the wrong colour is lost, which
is what Bridge Bar's blue lettering painted in the ground yellow is.

    .venv/bin/python tools/thin_strokes.py photo/logo_hotel_fremont.webp --width 92.5 --garment patch
    .venv/bin/python tools/thin_strokes.py --corpus            # the ten real-art fixtures
    .venv/bin/python tools/thin_strokes.py --corpus --forced-class flat
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000
from skimage.morphology import skeletonize

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine                      # noqa: E402
from digitizer_core.pipeline import (build_generation, finish_generation,  # noqa: E402
                                     plan_stitches)
from digitizer_core.stage1_prep import Prep                            # noqa: E402
from digitizer_core.stage2_quantize import quantize                     # noqa: E402
from digitizer_core.stitches import (CMD_COLOR_CHANGE, CMD_JUMP,        # noqa: E402
                                     CMD_STITCH, CMD_TRIM, StitchPlan,
                                     iter_machine_commands)
from digitizer_core.textcluster import TEXT_CLUSTER_DELTA_E_MAX         # noqa: E402
from digitizer_core.threads import rgb_to_lab                           # noqa: E402

# The ten real-art fixtures at the Studio's own defaults — the set the review
# and its audit pass measured (`docs/quality-review-2026-09-08.md` §1).
REAL_ART: dict[str, tuple[str, float, str]] = {
    "becker": ("becker_marine_logo.png", 100.0, "left_chest"),
    "tires": ("logo_script_tires.png", 80.0, "left_chest"),
    "enthusiast": ("photo/enthusiast_logo.png", 80.0, "left_chest"),
    "fremont": ("photo/logo_hotel_fremont.webp", 92.5, "patch"),
    "bridge": ("photo/logo_bridge_bar.jpg", 80.0, "left_chest"),
    "golden_tee": ("photo/logo_golden_tee.jpg", 80.0, "left_chest"),
    "gaulke": ("photo/logo_gaulke_roofing.png", 80.0, "left_chest"),
    "drone": ("photo/drone_render.png", 80.0, "left_chest"),
    "thermal": ("photo/logo_drone_thermal_badge.png", 80.0, "left_chest"),
    "screenshot": ("photo/screenshot_phone_ui_golke.jpg", 80.0, "left_chest"),
}


def corpus_cases(root: Path = ROOT) -> list[tuple[str, Path, float, str]]:
    """-> [(name, path, width_mm, garment)] for `--corpus`, byte-duplicate
    artwork run ONCE.

    `photo/logo_drone_thermal_badge.png` is byte-identical to
    `photo/drone_render.png` (`tools/pro_parity/blockcensus.py` records the
    same, and the scorecard's FIXTURES carries both). REAL_ART keeps the ten
    names the review measured; a corpus run that scored both would print one
    design twice and weight it double in any average. Checked by digest at
    runtime, not remembered — if the two files ever diverge, both run.
    """
    seen: dict[str, str] = {}
    out: list[tuple[str, Path, float, str]] = []
    for name, (rel, w, g) in REAL_ART.items():
        path = root / "testdata" / rel
        digest = hashlib.md5(path.read_bytes()).hexdigest() if path.exists() else name
        if digest in seen:
            print(f"  [note] {name} ({rel}) is byte-identical to {seen[digest]}; run once")
            continue
        seen[digest] = name
        out.append((name, path, w, g))
    return out

# A component with fewer skeleton pixels than this is a speck the length
# floor would refuse anyway; skipping it early keeps the per-component loop
# cheap on a photograph's thousands of fragments.
_MIN_SKELETON_PX = 3
# A component narrower than this many PIXELS is the raster's anti-alias or
# compression halo, not ink: a halo is one or two pixels wide at any
# resolution, while the thinnest stroke a pro widened on Fremont is 0.24 mm =
# 6.5 px at that file's 27 px/mm. Measured 2026-09-08 on Fremont at the
# pipeline's default 12 colours: without this floor the "worst lost stroke"
# was a 34.6 mm sliver 0.07 mm (2 px) wide — the webp's ringing around the
# black band, quantised to its own label. A pixel floor, not a millimetre
# one, because the artefact is a raster phenomenon.
_MIN_STROKE_PX = 3.0
# The Studio sends this; the pipeline's own default is 12. The corpus runs at
# what a customer gets.
STUDIO_MAX_COLORS = 6


@dataclass
class ThinStroke:
    """One thin connected component of one artwork colour."""

    label: int
    rgb: tuple[int, int, int]
    length_mm: float          # 8-connected link length of the skeleton
    width_mm: float           # median FULL width along the skeleton
    bbox_mm: tuple[float, float, float, float]   # x0, y0, x1, y1, plan frame
    sewn_mm: float = 0.0      # skeleton length inside matching-colour thread

    @property
    def recall(self) -> float:
        return self.sewn_mm / self.length_mm if self.length_mm > 0 else 0.0

    @property
    def lost_mm(self) -> float:
        return self.length_mm - self.sewn_mm


def _link_length_mm(skel: np.ndarray, px_per_mm: float) -> float:
    """Length of a 1-px skeleton as the sum of its 8-connected links, in mm.

    Horizontal and vertical neighbours are one pixel apart, diagonal ones
    root-two. A junction pixel contributes every link it takes part in, so a
    branchy skeleton reads a little long; a lower-bound pixel count reads a
    diagonal stroke 29% short. Links are the closer of the two, and the same
    rule is applied to every stroke so recall (a ratio of the same
    measurement) is unaffected either way.
    """
    s = skel.astype(bool)
    h = np.count_nonzero(s[:, :-1] & s[:, 1:])
    v = np.count_nonzero(s[:-1, :] & s[1:, :])
    d1 = np.count_nonzero(s[:-1, :-1] & s[1:, 1:])
    d2 = np.count_nonzero(s[:-1, 1:] & s[1:, :-1])
    return (h + v + math.sqrt(2.0) * (d1 + d2)) / px_per_mm


def _plan_frame(p: Prep) -> tuple[float, float, float]:
    """-> (cx, cy, px_per_mm): the prepped raster's pixel that is the plan's
    (0, 0), and the scale. Stage 4's own mapping (`_to_mm`): mm =
    (px - centre of the art bbox) / px_per_mm, y down."""
    x0, y0, x1, y1 = p.art_bbox
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0, p.px_per_mm


def find_thin_strokes(p: Prep, cfg: PipelineConfig,
                      width_floor_mm: float | None = None,
                      min_length_mm: float | None = None) -> list[ThinStroke]:
    """Every thin stroke in the artwork, read with the flat lane's quantizer.

    `width_floor_mm` defaults to `cfg.min_detail_mm`; `min_length_mm` to
    `machine.RUN_MIN_LOOP_MM / 2`. Returned sorted longest first.
    """
    floor = cfg.min_detail_mm if width_floor_mm is None else width_floor_mm
    min_len = (machine.RUN_MIN_LOOP_MM / 2.0) if min_length_mm is None else min_length_mm
    q = quantize(p, cfg)
    cx, cy, ppm = _plan_frame(p)
    out: list[ThinStroke] = []
    for j in range(len(q.thread_indices)):
        label_mask = q.labels == j
        if not label_mask.any():
            continue
        # One distance transform and one skeleton per LABEL: components of one
        # label are disjoint, so a component's own distances and skeleton are
        # exactly the union's restricted to it.
        dt = cv2.distanceTransform(label_mask.astype(np.uint8), cv2.DIST_L2, 5)
        skel = skeletonize(label_mask)
        n, cc, stats, _ = cv2.connectedComponentsWithStats(label_mask.astype(np.uint8), connectivity=8)
        rgb = tuple(int(round(float(v))) for v in q.cluster_rgb[j])
        for c in range(1, n):
            bx, by, bw, bh, _area = (int(v) for v in stats[c, :5])
            comp = cc[by:by + bh, bx:bx + bw] == c
            sk = skel[by:by + bh, bx:bx + bw] & comp
            npx = int(sk.sum())
            if npx < _MIN_SKELETON_PX:
                continue
            width_px = 2.0 * float(np.median(dt[by:by + bh, bx:bx + bw][sk]))
            width = width_px / ppm
            if width >= floor or width_px < _MIN_STROKE_PX:
                continue
            length = _link_length_mm(sk, ppm)
            if length < min_len:
                continue
            out.append(ThinStroke(
                label=j, rgb=rgb, length_mm=length, width_mm=width,
                bbox_mm=((bx - cx) / ppm, (by - cy) / ppm,
                         (bx + bw - cx) / ppm, (by + bh - cy) / ppm)))
    out.sort(key=lambda s: -s.length_mm)
    return out


def thread_masks(plan: StitchPlan, shape: tuple[int, int], cx: float, cy: float,
                 px_per_mm: float) -> list[tuple[tuple[int, int, int], np.ndarray]]:
    """The thread each colour lays, painted on the prepped raster's frame.

    Consecutive `CMD_STITCH` points are a sewn segment; a jump, a trim or a
    colour change breaks the chain, so no thread is painted across them —
    `iter_machine_commands` is the one accounting, the same stream the DST
    encoder writes. Segments are drawn `COVERAGE_THREAD_W_MM` wide. Blocks of
    one colour share a mask.
    """
    tw = max(1, int(round(machine.COVERAGE_THREAD_W_MM * px_per_mm)))
    masks: dict[tuple[int, int, int], np.ndarray] = {}
    block_i = 0
    rgb = tuple(int(v) for v in plan.blocks[0].rgb) if plan.blocks else (0, 0, 0)
    last: tuple[int, int] | None = None

    def to_px(pt: tuple[float, float]) -> tuple[int, int]:
        return int(round(pt[0] * px_per_mm + cx)), int(round(pt[1] * px_per_mm + cy))

    for cmd, pt in iter_machine_commands(plan):
        if cmd == CMD_COLOR_CHANGE:
            block_i += 1
            rgb = tuple(int(v) for v in plan.blocks[block_i].rgb)
            last = None
        elif cmd in (CMD_JUMP, CMD_TRIM):
            last = None
        elif cmd == CMD_STITCH:
            here = to_px(pt)
            if last is not None:
                m = masks.get(rgb)
                if m is None:
                    m = masks[rgb] = np.zeros(shape, np.uint8)
                cv2.line(m, last, here, 255, tw, cv2.LINE_8)
            last = here
    return [(k, v > 0) for k, v in masks.items()]


def score_strokes(strokes: list[ThinStroke], p: Prep, cfg: PipelineConfig,
                  plan: StitchPlan, delta_e_max: float = TEXT_CLUSTER_DELTA_E_MAX) -> None:
    """Fill in `sewn_mm` for every stroke, in place: the fraction of its
    skeleton inside the thread of any block within `delta_e_max` of its own
    colour, times its length."""
    if not strokes:
        return
    cx, cy, ppm = _plan_frame(p)
    masks = thread_masks(plan, p.rgb.shape[:2], cx, cy, ppm)
    if not masks:
        for s in strokes:
            s.sewn_mm = 0.0
        return
    block_lab = rgb_to_lab(np.array([m[0] for m in masks], np.float64))
    # The strokes are re-derived from the same quantization so their pixels
    # can be located; `find_thin_strokes` keeps no raster to stay small.
    q = quantize(p, cfg)
    for s in strokes:
        lab = rgb_to_lab(np.array([s.rgb], np.float64))
        de = deltaE_ciede2000(np.repeat(lab, len(masks), axis=0), block_lab)
        union = None
        for (rgb, m), d in zip(masks, de):
            if d <= delta_e_max:
                union = m if union is None else (union | m)
        if union is None:
            s.sewn_mm = 0.0
            continue
        x0 = int(round(s.bbox_mm[0] * ppm + cx)); x1 = int(round(s.bbox_mm[2] * ppm + cx))
        y0 = int(round(s.bbox_mm[1] * ppm + cy)); y1 = int(round(s.bbox_mm[3] * ppm + cy))
        comp = (q.labels[y0:y1, x0:x1] == s.label)
        sk = skeletonize(comp)
        npx = int(sk.sum())
        if npx == 0:
            s.sewn_mm = 0.0
            continue
        covered = int((sk & union[y0:y1, x0:x1]).sum())
        s.sewn_mm = s.length_mm * covered / npx


# Width bands, in mm. A design-level recall is dominated by whatever thin
# structure is LONGEST — on Fremont the rope, which sews — while the strokes
# Kent misses are the hairline lettering, a few millimetres each. Reported
# per band so the band the loss lives in is visible: under the satin cross
# floor (`SATIN_MIN_CROSS_MM`, the hairline tier), from there to Law 31's
# 1.0 mm floor, and from there to the detail floor.
def _bands(floor_mm: float) -> list[tuple[str, float, float]]:
    return [(f"< {machine.SATIN_MIN_CROSS_MM:g}", 0.0, machine.SATIN_MIN_CROSS_MM),
            (f"{machine.SATIN_MIN_CROSS_MM:g}-1.0", machine.SATIN_MIN_CROSS_MM, 1.0),
            (f"1.0-{floor_mm:g}", 1.0, floor_mm)]


def measure(p: Prep, cfg: PipelineConfig, plan: StitchPlan) -> dict:
    strokes = find_thin_strokes(p, cfg)
    score_strokes(strokes, p, cfg, plan)
    total = sum(s.length_mm for s in strokes)
    sewn = sum(s.sewn_mm for s in strokes)
    lost = sorted(strokes, key=lambda s: -s.lost_mm)
    bands = []
    for name, lo, hi in _bands(cfg.min_detail_mm):
        members = [s for s in strokes if lo <= s.width_mm < hi]
        length = sum(s.length_mm for s in members)
        bands.append({"band_mm": name, "strokes": len(members),
                      "lost_strokes": sum(1 for s in members if s.recall < 0.5),
                      "length_mm": round(length, 1),
                      "recall": round(sum(s.sewn_mm for s in members) / length, 3) if length else None})
    return {
        "thin_strokes": len(strokes),
        "lost_strokes": sum(1 for s in strokes if s.recall < 0.5),
        "thin_length_mm": round(total, 2),
        "sewn_length_mm": round(sewn, 2),
        "recall": round(sewn / total, 4) if total > 0 else None,
        "bands": bands,
        "worst_lost": [
            {**asdict(s), "recall": round(s.recall, 3), "lost_mm": round(s.lost_mm, 2)}
            for s in lost[:5]
        ],
    }


def run(art: Path, width_mm: float, garment: str, forced_class: str | None = None,
        max_colors: int = STUDIO_MAX_COLORS) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         forced_class=forced_class, max_colors=max_colors)
    gen = build_generation(str(art), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    out = measure(gen.p, cfg, plan)
    out.update({
        "fixture": str(art), "width_mm": width_mm, "garment": garment,
        "design_class": result.design_class, "stitches": plan.stats.stitch_count,
        "regions": len(result.regions),
    })
    return out


def _fmt_row(name: str, r: dict) -> str:
    worst = r["worst_lost"][0] if r["worst_lost"] else None
    recall = "  n/a " if r["recall"] is None else f"{r['recall']:6.1%}"
    w = ("" if worst is None else
         f"  worst lost {worst['lost_mm']:6.1f} mm at {worst['width_mm']:.2f} mm wide, "
         f"({worst['bbox_mm'][0]:.1f},{worst['bbox_mm'][1]:.1f})")
    bands = "  ".join(
        f"[{bd['band_mm']} mm: {bd['strokes']}/{bd['lost_strokes']} lost, "
        f"{'n/a' if bd['recall'] is None else format(bd['recall'], '.0%')}]" for bd in r["bands"])
    return (f"  {name:12} {r['design_class']:12} thin {r['thin_strokes']:4d} lost {r['lost_strokes']:4d} "
            f"{r['thin_length_mm']:8.1f} mm  sewn {r['sewn_length_mm']:8.1f}  recall {recall}{w}\n"
            f"      bands {bands}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture", nargs="?", help="path under testdata/, or a full path")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--forced-class", default=None, dest="forced_class")
    ap.add_argument("--max-colors", type=int, default=STUDIO_MAX_COLORS, dest="max_colors")
    ap.add_argument("--corpus", action="store_true", help="the ten real-art fixtures at Studio defaults")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.corpus and not a.fixture:
        ap.error("a fixture or --corpus")
    results = []
    lane = f"  forced_class={a.forced_class}" if a.forced_class else ""
    print(f"thin-stroke recall — width floor {PipelineConfig().min_detail_mm} mm (and >= {_MIN_STROKE_PX:g} px), "
          f"min length {machine.RUN_MIN_LOOP_MM / 2:.2f} mm, thread {machine.COVERAGE_THREAD_W_MM} mm, "
          f"colour match <= {TEXT_CLUSTER_DELTA_E_MAX} dE00, max_colors {a.max_colors}{lane}")
    if a.corpus:
        cases = corpus_cases()
    else:
        art = Path(a.fixture)
        if not art.exists():
            art = ROOT / "testdata" / a.fixture
        cases = [(art.stem, art, a.width, a.garment)]
    for name, art, w, g in cases:
        r = run(art, w, g, a.forced_class, a.max_colors)
        results.append(r)
        print(_fmt_row(name, r))
    if a.json:
        print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
