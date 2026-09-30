"""Calibration card v2 — the CUSTOMER's card (Kent's call, 2026-09-30).

v1 (`tools/sewout_card.py`) is Kent's gate-1 instrument: one hooping, six
questions, answers read off the fabric by eye with a paper key. It stays
exactly as it is. This card is what a customer sews so that
`tools/sewout_reader.py` can read a phone photo of it and draft a fabric
profile (`docs/sewout-calibration-brief-2026-09-30.md`). Three things
differ, each one a decision the brief put to Kent and he made:

  * **Corner fiducials.** Four 2.5 mm satin squares 1 mm outside the
    artwork's bounding box, sewn FIRST in block 1's thread, so a photo
    registers off marks instead of off the artwork and a global shrink of
    the whole card is measured rather than absorbed. No extra colour stop.
  * **A 0.15 mm density arm** — square D beside v1's A / B / C. The
    professional's adjacent-row pitch measured 0.14-0.17 mm on two
    commissioned files (`docs/sewout-findings-2026-09-03.md`, `tools/
    row_pitch_union.py`); v1's densest arm stops at 0.20, so nothing on v1
    shows the customer what the pro's coverage looks like on their cloth.
  * **A 5x7 hoop target** (130 x 180 mm), not 4x4. 4x4 would have forced a
    block off the card; 5x7 keeps every arm with room. A customer with only
    a 4x4 machine cannot calibrate with this card — accepted.

Everything else is v1's own builders, imported and called, so a block that
changes in v1 changes here. The blocks and their questions are documented in
`docs/sewout-card-2026-07-31.md`; the reader's per-block → profile-field map
is §5 of the brief.

In the package since 2026-09-30 so the service can serve this card in any
machine format (`/calibration/card`); `tools/sewout_card_v2.py` is the
command line that writes the files.

Usage (from digitizer/):
  PYTHONPATH=. .venv/bin/python tools/sewout_card_v2.py       # generate
Then, from the repo root, the same bridge v1 uses:
  node tools/sewout_bridge.mjs \\
      digitizer/debug_out/sewout/EMBBOT_CALIBRATION_CARD_V2.design.json \\
      digitizer/debug_out/sewout/EMBBOT_CALIBRATION_CARD_V2.dst
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import box

from .. import machine
from ..stage6_fill import stitch_shape
from ..stage7_sequence import _apply_ties
from ..stitches import SATIN, StitchBlock, StitchPlan, StitchRun, tie_run
from ..threads import CHART
from . import card as v1

OUT = v1.OUT
NAME = "EMBBOT_CALIBRATION_CARD_V2"
LABEL = "EMBBOT CALIB CARD V2"

# 5x7 in, the second-smallest home preset (`src/garments.js` HOOPS). Kept
# this far inside the hoop so the customer's own hooping slack is not what
# decides whether the corner marks sew.
HOOP_MM = (130.0, 180.0)
HOOP_MARGIN_MM = 10.0

# The marks. 2.5 mm is the smallest satin square the reader's centroid
# finder separates from the artwork at 6 px/mm (`sewout_reader.simulate_photo`);
# the 1 mm gap keeps a mark from merging with the lock bar's tie under blur.
FIDUCIAL_MM = 2.5
FIDUCIAL_GAP_MM = 1.0
FIDUCIAL_SHAPE = "__fiducial__"        # what `sewout_reader.fiducial_points` looks for

# The professional's adjacent-row pitch, as measured — NOT a constant this
# repo sets (gate 1). The card sews it so the customer's cloth can be asked.
DENSE_ROW_MM = 0.15
DENSE_X0 = 60.0                          # beside square C (x 40-55), same row


def block2_fill_v2() -> tuple[list[StitchRun], dict]:
    """v1's three squares, then D at the professional's pitch."""
    runs, info = v1.block2_fill()
    y0, sq = 7.2, 15.0
    cursor = runs[-1].points[-1]
    r, rep = stitch_shape(box(DENSE_X0, y0, DENSE_X0 + sq, y0 + sq), "fill-D-0.15",
                          angle_deg=0.0, row_mm=DENSE_ROW_MM,
                          stitch_mm=machine.FILL_STITCH_MM,
                          underlay_style=v1.FILL_UNDERLAY, trim_at_mm=v1.TRIM_AT,
                          start_near=cursor)
    v1.link(cursor, r)
    runs.extend(r)
    ys = v1.fill_row_ys(r)
    pitch = float(np.median(np.diff(ys))) if len(ys) > 2 else math.nan
    assert abs(pitch - DENSE_ROW_MM) < 0.02, (
        f"square D rows {pitch:.3f} mm apart, wanted {DENSE_ROW_MM} — emitter changed; card invalid")
    info["fill-D-0.15"] = {"row_mm": DENSE_ROW_MM, "underlay": v1.FILL_UNDERLAY,
                           "points": sum(len(x.points) for x in r),
                           "measured_row_pitch_mm": round(pitch, 4), "report": rep}
    return runs, info


def fiducial_runs(bbox: tuple[float, float, float, float]) -> list[StitchRun]:
    """Four tied satin squares just outside `bbox`, TL, TR, BR, BL — the
    order the reader lists them in. Each is its own cut run: the hops
    between corners cross the whole card."""
    x0, y0, x1, y1 = bbox
    g, s = FIDUCIAL_GAP_MM, FIDUCIAL_MM
    corners = [(x0 - g - s, y0 - g - s), (x1 + g, y0 - g - s),
               (x1 + g, y1 + g), (x0 - g - s, y1 + g)]
    runs = []
    for cx, cy in corners:
        pts = v1.zigzag_bar(cx, cy, s, s)
        run = StitchRun(points=pts, kind=SATIN, jump=True, trim=True, shape_id=FIDUCIAL_SHAPE)
        head = tie_run(run.points[0], run.points[1]).points
        run.points = head[:-1] + run.points
        tail = tie_run(run.points[-1], run.points[-2]).points
        run.points = run.points + tail[1:]
        runs.append(run)
    return runs


BLOCKS = [(name, block2_fill_v2 if name == "2 FILL" else builder, rgb, self_tied)
          for name, builder, rgb, self_tied in v1.BLOCKS]


def build_card_v2() -> tuple[StitchPlan, dict]:
    """v1's assembly with the marks prepended to block 1 after every block's
    extent is known — the marks frame the artwork, so they are placed last
    and sewn first."""
    built = []
    report: dict = {"blocks": {}, "version": 2}
    for name, builder, _rgb, self_tied in BLOCKS:
        runs, info = builder()
        if not self_tied:
            _apply_ties(runs)
        built.append((name, runs))
        report["blocks"][name] = info

    art_bbox = v1.runs_bbox([r for _, runs in built for r in runs])
    marks = fiducial_runs(art_bbox)
    built[0] = (built[0][0], marks + built[0][1])
    report["fiducials"] = {"size_mm": FIDUCIAL_MM, "gap_mm": FIDUCIAL_GAP_MM,
                           "artwork_bbox_mm": [round(v, 2) for v in art_bbox],
                           "centres_mm": [[round(x, 2), round(y, 2)] for x, y in
                                          ((v1.runs_bbox([m])[0] + FIDUCIAL_MM / 2,
                                            v1.runs_bbox([m])[1] + FIDUCIAL_MM / 2) for m in marks)]}

    blocks: list[StitchBlock] = []
    palette: list[dict] = []
    prev_end = None
    all_runs: list[StitchRun] = []
    snapped = CHART.snap_palette(np.array([rgb for _, _, rgb, _ in BLOCKS], float))
    for (name, runs), ti in zip(built, snapped):
        v1.link(prev_end, runs)
        runs[0].jump = True
        runs[0].trim = True
        thread = CHART[ti]
        blocks.append(StitchBlock(thread_index=ti, thread_number=thread.number,
                                  rgb=tuple(thread.rgb), runs=runs))
        palette.append({"brand": "isacord", "number": thread.number,
                        "name": name, "rgb": list(thread.rgb)})
        prev_end = runs[-1].points[-1]
        all_runs.extend(runs)

    x0, y0, x1, y1 = v1.runs_bbox(all_runs)
    w, h = x1 - x0, y1 - y0
    limit = (HOOP_MM[0] - 2 * HOOP_MARGIN_MM, HOOP_MM[1] - 2 * HOOP_MARGIN_MM)
    assert w <= limit[0] and h <= limit[1], (
        f"card {w:.1f} x {h:.1f} mm does not fit {HOOP_MM} with {HOOP_MARGIN_MM} mm margin")
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    for r in all_runs:
        r.points = [(x - cx, y - cy) for x, y in r.points]
    report["hoop"] = {"target_mm": list(HOOP_MM), "margin_mm": HOOP_MARGIN_MM,
                      "card_mm": [round(w, 2), round(h, 2)]}
    plan = StitchPlan(blocks=blocks, palette=palette, design_size_mm=(w, h))
    return plan, report
