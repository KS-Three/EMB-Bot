"""Chaining the line route's strands, on the real photo (2026-10-13).

    python -m tools.hairline_lines_chain_trial --arms lines,lines_chain,strand,strand_chain
    python -m tools.hairline_lines_chain_trial --drawn       # hair_strands, hair_fine
    python -m tools.hairline_lines_chain_trial --compose     # strips, table

Follows #882 (`cfg.hairline_from_lines`: +45 trims on owl_kent) and #897
(`cfg.hairline_lines_strand_test`). This measures `cfg.hairline_lines_chain`
(`stage6_hairline_lines.strand_blocks`, `stage7_sequence`) on #882's route:
`classical` (photo lane, `photo_prep=False`), 40 wt, 127 mm. Arms: `lines`
(#882) and `strand` (#882 + #897), each with the chain flag off and on
(`*_chain`).

Per arm: stitches, trims, thread laid, the strand-block census, the hops the
chain sewed needle-down (count, mm, and how many show: the mean L* gap
between the dragged thread and the source under it, against the hairline
tier's own contrast floor), and the CORRECTED thread over bare fabric of
`tools.hairline_travel` (#895: a trimmed-jump flight carries no thread; the
legacy `tests/test_chaining.py::_thread_bare_mm` counts it as thread). The
strands themselves are compared run for run between the flag's two states.

Every number is a property of the FILE, not of cloth (ROADMAP gate 1); the
8 mm cap is a candidate (gate 3).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitches, stitchviz  # noqa: E402
from digitizer_core.adapter import UNITS_PER_MM, plan_to_design  # noqa: E402
from digitizer_core.pipeline import digitize, plan_stitches, run_stages  # noqa: E402
from digitizer_core.stage6_hairline import _SRC_MIN_CONTRAST  # noqa: E402
from digitizer_core.stage6_hairline_lines import SHAPE_ID  # noqa: E402
from tools.hairline_lines_trial import (PHOTO, ROUTE, SYN, WIDTH_MM,  # noqa: E402
                                        measure, write_jpeg)
from tools.hairline_travel import measure_plan  # noqa: E402

# arm -> (strand test, chain)
ARMS = {"lines": (False, False), "lines_chain": (False, True),
        "strand": (True, False), "strand_chain": (True, True)}
PARTS = ROOT / "debug_out" / "hairline_lines_chain_trial"
OUT = ROOT.parent / "docs" / "renders" / "claude-hairline-lines-chain"
PICKLE = False
PPM = 30.0
BOX_MM = (14.0, 9.0)


def arm_cfg(arm: str) -> PipelineConfig:
    test, chain = ARMS[arm]
    return PipelineConfig(target_width_mm=WIDTH_MM, hairline=True, hairline_from_lines=True,
                          hairline_lines_strand_test=test, hairline_lines_chain=chain,
                          thread_wt=40, **ROUTE)


def _runs(plan):
    return [(b, r) for b in plan.blocks for r in b.runs if r.points]


# A lock stitch is a few 0.8 mm legs back and forth at the end of a cut, so
# it stays within this distance of the run's end; a hop has none.
LOCK_REACH_MM = 2.5


def core(points) -> list:
    """The points further than `LOCK_REACH_MM` from both ends of the run."""
    a, b = points[0], points[-1]
    return [p for p in points
            if math.dist(p, a) > LOCK_REACH_MM and math.dist(p, b) > LOCK_REACH_MM]

def strand_signature(plan) -> str:
    """The line route's strands, in order: every RUN-kind run of the strand
    blocks, point for point but for `LOCK_REACH_MM` at each end, where
    the lock stitches of a cut sit (the chain flag must not move one)."""
    h = hashlib.md5()
    for _b, r in _runs(plan):
        if r.shape_id == SHAPE_ID and r.kind == stitches.RUN:
            h.update(json.dumps([[round(x, 4), round(y, 4)] for x, y in core(r.points)]).encode())
    return h.hexdigest()


def hops(plan) -> list[dict]:
    """Every needle-down hop of the strand blocks: the TRAVEL run between two
    strands, from the previous strand's last point to the next one's first."""
    runs = _runs(plan)
    out = []
    for i, (b, r) in enumerate(runs):
        if r.shape_id != SHAPE_ID or r.kind != stitches.TRAVEL:
            continue
        out.append({"a": runs[i - 1][1].points[-1], "b": runs[i + 1][1].points[0],
                    "rgb": tuple(b.rgb)})
    return out


def cuts(plan) -> list[dict]:
    """Every trimmed or untrimmed JUMP between two strands (not a block's
    first strand, which opens a colour change)."""
    runs = _runs(plan)
    out = []
    for i, (b, r) in enumerate(runs):
        if r.shape_id != SHAPE_ID or r.kind != stitches.RUN or not r.jump:
            continue
        prev = runs[i - 1][1]
        if prev.shape_id != SHAPE_ID:
            continue
        out.append({"a": prev.points[-1], "b": r.points[0], "trim": bool(r.trim)})
    return out


def _lab_l(rgb) -> float:
    px = np.array([[rgb]], np.uint8)
    return float(cv2.cvtColor(px, cv2.COLOR_RGB2LAB)[0, 0, 0]) * 100.0 / 255.0


def hop_visibility(plan, sp) -> dict:
    """How much a dragged hop shows: the mean absolute L* gap between the
    thread and the source under the hop, sampled every 0.25 mm. A hop at or
    over the hairline tier's own contrast floor (`_SRC_MIN_CONTRAST`, 12) is
    counted as showing. A file property, not a sew-out (gate 1)."""
    lab = cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2LAB)[..., 0].astype(np.float64) * 100.0 / 255.0
    h, w = lab.shape
    gaps, mm = [], []
    for hp in hops(plan):
        a, b = hp["a"], hp["b"]
        d = math.dist(a, b)
        n = max(2, int(d / 0.25))
        vals = []
        for i in range(n + 1):
            x, y = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
            px, py = sp.to_px(x, y)
            vals.append(lab[min(max(int(round(py)), 0), h - 1), min(max(int(round(px)), 0), w - 1)])
        gaps.append(abs(float(np.mean(vals)) - _lab_l(hp["rgb"])))
        mm.append(d)
    showing = [m for g, m in zip(gaps, mm) if g >= _SRC_MIN_CONTRAST]
    return {"hops": len(gaps), "hop_mm": round(sum(mm), 2),
            "showing_hops": len(showing), "showing_mm": round(sum(showing), 2),
            "mean_gap_L": round(float(np.mean(gaps)), 1) if gaps else 0.0,
            "max_hop_mm": round(max(mm), 2) if mm else 0.0}


def strand_trims(plan) -> int:
    """Trimmed jumps between two strands of the strand blocks."""
    return sum(1 for c in cuts(plan) if c["trim"])


def run_arm(arm: str, result=None) -> dict:
    cfg = arm_cfg(arm)
    if result is None:
        result = run_stages(PHOTO, cfg)
    plan = plan_stitches(result, cfg)
    row = measure(plan)
    t = measure_plan(plan, with_legacy=False)
    row.update({k: t[k] for k in ("thread_bare_mm", "thread_exposed_legs", "thread_by_leg",
                                  "flight_bare_mm", "trims_block_start", "trims_in_shape",
                                  "trims_between_shapes", "flight_total_mm")})
    sp = result.source_pixels
    strands = [r for _b, r in _runs(plan) if r.shape_id == SHAPE_ID and r.kind == stitches.RUN]
    row["strand_runs"] = len(strands)
    row["strand_signature"] = strand_signature(plan)
    row["strand_trims"] = strand_trims(plan)
    row["strand_jumps"] = len(cuts(plan))
    row["visibility"] = hop_visibility(plan, sp)
    w = [x for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"]
    row["census"] = {k: w[0].get(k) for k in ("strands", "dropped", "hops", "hop_mm",
                                              "refused_bar") if w and k in w[0]}
    PARTS.mkdir(parents=True, exist_ok=True)
    if PICKLE:
        import pickle
        (PARTS / f"{arm}.pkl").write_bytes(pickle.dumps((plan, sp)))
    render_parts(plan, sp, arm)
    (PARTS / f"{arm}.json").write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
    return row


# --- pictures ----------------------------------------------------------------

def _window(points, size) -> tuple[float, float, float, float]:
    """The `size` window (mm) holding the most of `points`."""
    best = (-1, None)
    for cx, cy in points:
        box = (cx - size[0] / 2, cy - size[1] / 2, cx + size[0] / 2, cy + size[1] / 2)
        n = sum(1 for x, y in points if box[0] <= x <= box[2] and box[1] <= y <= box[3])
        if n > best[0]:
            best = (n, box)
    return best[1]


def render_parts(plan, sp, arm: str) -> None:
    """Whole-design render at PPM, plus the cut / chained hops as segments (mm)
    saved for `compose`."""
    segs = {"hops": [(h["a"], h["b"]) for h in hops(plan)],
            "trims": [(c["a"], c["b"]) for c in cuts(plan) if c["trim"]],
            "jumps": [(c["a"], c["b"]) for c in cuts(plan) if not c["trim"]]}
    (PARTS / f"{arm}_segs.json").write_text(json.dumps(segs) + "\n", encoding="utf-8")
    design = plan_to_design(plan, name=f"owl {arm}")
    stitches_ = design.get("stitches") or []
    img = stitchviz.render_design(design, px_per_mm=PPM,
                                  thread_mm=machine.thread_profile(40).width_mm)
    _size, to_px = stitchviz._frame(stitches_, PPM, 2.0)
    origin = to_px({"x": 0.0, "y": 0.0})
    tx = to_px({"x": UNITS_PER_MM, "y": 0.0})
    ty = to_px({"x": 0.0, "y": -UNITS_PER_MM})
    meta = {"origin": list(origin), "x": [tx[0] - origin[0], tx[1] - origin[1]],
            "y": [ty[0] - origin[0], ty[1] - origin[1]], "shape": list(img.shape[:2])}
    (PARTS / f"{arm}_frame.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
    cv2.imwrite(str(PARTS / f"{arm}_full.png"), img)


def _px(meta, x, y):
    o, ax, ay = meta["origin"], meta["x"], meta["y"]
    return (o[0] + ax[0] * x + ay[0] * y, o[1] + ax[1] * x + ay[1] * y)


def _panel(arm: str, box, draw: set[str], label: str):
    meta = json.loads((PARTS / f"{arm}_frame.json").read_text(encoding="utf-8"))
    segs = json.loads((PARTS / f"{arm}_segs.json").read_text(encoding="utf-8"))
    img = cv2.imread(str(PARTS / f"{arm}_full.png"))
    a, b = _px(meta, box[0], box[1]), _px(meta, box[2], box[3])
    x0, x1 = sorted((int(a[0]), int(b[0])))
    y0, y1 = sorted((int(a[1]), int(b[1])))
    x0, y0 = max(x0, 0), max(y0, 0)
    crop = img[y0:y1, x0:x1].copy()
    colour = {"hops": (40, 40, 235), "trims": (235, 120, 20), "jumps": (200, 160, 20)}
    for kind in draw:
        for (p, q) in segs[kind]:
            pa, pb = _px(meta, *p), _px(meta, *q)
            cv2.line(crop, (int(pa[0]) - x0, int(pa[1]) - y0), (int(pb[0]) - x0, int(pb[1]) - y0),
                     colour[kind], 2, cv2.LINE_AA)
    band = np.full((34, crop.shape[1], 3), 255, np.uint8)
    cv2.putText(band, label, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2, cv2.LINE_AA)
    return np.vstack([band, crop])


def compose() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {a: json.loads((PARTS / f"{a}.json").read_text(encoding="utf-8"))
            for a in ARMS if (PARTS / f"{a}.json").exists()}
    for r in rows.values():
        r.pop("strand_signature", None)  # the unit test pins "no strand moved"
    drawn = (json.loads((PARTS / "drawn.json").read_text(encoding="utf-8"))
             if (PARTS / "drawn.json").exists() else {})
    (OUT / "table.json").write_text(json.dumps({"owl_classical_40wt": rows, "drawn": drawn},
                                               indent=1) + "\n", encoding="utf-8")
    for off, on, name in (("lines", "lines_chain", "lines"), ("strand", "strand_chain", "strand")):
        if on not in rows or off not in rows:
            continue
        segs = json.loads((PARTS / f"{on}_segs.json").read_text(encoding="utf-8"))
        mids = [((p[0] + q[0]) / 2, (p[1] + q[1]) / 2) for p, q in segs["hops"]]
        if not mids:
            continue
        box = _window(mids, BOX_MM)
        tiles = [_panel(off, box, {"trims", "jumps"}, f"{name}: chain OFF (cuts blue)"),
                 _panel(on, box, {"hops", "trims", "jumps"},
                        f"{name}: chain ON (red hop, blue cut)")]
        h, w = min(t.shape[0] for t in tiles), min(t.shape[1] for t in tiles)
        sep = np.full((h, 8, 3), 255, np.uint8)
        write_jpeg(OUT / f"owl_{name}_chain_{int(PPM)}pxmm.jpg",
                   np.hstack([tiles[0][:h, :w], sep, tiles[1][:h, :w]]))
    print(json.dumps(rows, indent=1))


def run_drawn() -> dict:
    """The drawn hair fixtures (gradient lane): the chain flag must change
    nothing, with the line route on and with the hairline tier alone."""
    out = {}
    for fixture in ("hair_strands.png", "hair_fine.png"):
        row = {}
        for arm, kw in (("on", dict(hairline=True)),
                        ("on_chain", dict(hairline=True, hairline_lines_chain=True)),
                        ("lines", dict(hairline=True, hairline_from_lines=True)),
                        ("lines_chain", dict(hairline=True, hairline_from_lines=True,
                                             hairline_lines_chain=True))):
            result, plan = digitize(SYN / fixture, PipelineConfig(target_width_mm=80.0, **kw))
            m = measure(plan)
            m["design_class"] = result.design_class
            row[arm] = m
        row["identical"] = len({row[a]["md5"] for a in row}) == 1
        out[fixture] = row
        print(fixture, json.dumps({a: (r["md5"], r["stitches"]) for a, r in row.items()
                                   if isinstance(r, dict)}), row["identical"], flush=True)
    PARTS.mkdir(parents=True, exist_ok=True)
    (PARTS / "drawn.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arms", help="comma list of " + ",".join(ARMS) + " (stages run once)")
    ap.add_argument("--drawn", action="store_true")
    ap.add_argument("--compose", action="store_true")
    ap.add_argument("--parts", type=Path, help="scratch folder for the per-arm parts")
    ap.add_argument("--pickle", action="store_true", help="also save each arm's plan")
    args = ap.parse_args(argv)
    global PARTS, PICKLE
    PICKLE = args.pickle
    if args.parts:
        PARTS = args.parts
    if args.arms:
        arms = args.arms.split(",")
        result = run_stages(PHOTO, arm_cfg(arms[0]))
        for arm in arms:
            print(arm, json.dumps(run_arm(arm, result)), flush=True)
    if args.drawn:
        run_drawn()
    if args.compose:
        compose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
