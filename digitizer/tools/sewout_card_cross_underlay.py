"""Sew-out card: the pro's crossing underlay under a fill (2026-10-21)

    # 1. cut the arms (seconds: a synthetic plate through the real pipeline)
    python -m tools.sewout_card_cross_underlay --cut
    # 2. build the two cards (reads the cuts)
    python -m tools.sewout_card_cross_underlay [--out ../docs/sewout/card-cross-underlay-2026-10-21]

Every dense fill on every job in the pro's zip sews ONE sparse tatami pass
first: ~1.0 mm rows, ~4 mm stitches, ~90 degrees to the top rows, 8-20% of the
fill's thread (`docs/underlay-audit-2026-10-05.md`;
`docs/settings-vs-pro-2026-10-21.md` rows 13-15). Our hat preset sews an edge
run and a 2.0 mm zigzag (`edge_zigzag`), left chest and beanie an edge run
alone (`edge_run`). `cfg.fill_underlay_cross` (built OFF) swaps the three to
`cross_tatami`. A fabric preset is gate 1, so this card is the sew-out.

Two machine files, one per garment, because underlay is a fabric question:

- `card_cross_underlay_hat_40wt.dst`  hat_front (structured_cap, 0.4 mm pull)
- `card_cross_underlay_polo_40wt.dst` left_chest (pique_knit; the beanie's
   jersey_tee preset sews the same `edge_run`, so a polo stands for both)

Each file: the same tatami plate (a 26 x 18 mm field with one R4 corner, and a
10 mm disc) twice, side by side. Teeth above a plate count its arm: 1 = the
preset as it ships, 2 = `fill_underlay_cross` ON. Every arm is the real
pipeline (`digitize`, flat class, the garment's own preset) with only that
flag changed; nothing hand-edited. Written through
`digitizer_service.formats.write` (pystitch, the service's /export path) and
read back with pystitch. EVERY NUMBER HERE IS A CANDIDATE UNTIL KENT SEWS IT.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from digitizer_core import PipelineConfig, stitches  # noqa: E402
from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from digitizer_core.stitches import StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402
from tools import sewout_card_v4 as c4  # noqa: E402

REPO = hc.REPO
WT = v3.WT
DEFAULT_OUT = REPO / "docs" / "sewout" / "card-cross-underlay-2026-10-21"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"

#: card -> the Studio garment it is sewn on
GARMENTS = {"hat": "hat_front", "polo": "left_chest"}
#: arms in tooth order: (label, overrides)
ARMS = (("preset", {"fill_underlay_cross": False}),
        ("cross", {"fill_underlay_cross": True}))

PLATE_W_MM, PLATE_H_MM, PPM = 39.0, 20.0, 20
FIELD = (1.0, 1.0, 27.0, 19.0)       # x0, y0, x1, y1 mm: 26 x 18
FIELD_RADIUS_MM = 4.0                # the top-right corner
DISC_CENTRE_MM = (33.0, 10.0)
DISC_RADIUS_MM = 5.0                 # 10 mm across


def plate_image() -> np.ndarray:
    """BGRA artwork: a 26 x 18 mm field (three square corners, one R4) and a 10 mm
    disc, one dark ink, on a transparent ground."""
    img = np.zeros((int(PLATE_H_MM * PPM), int(PLATE_W_MM * PPM), 4), np.uint8)
    x0, y0, x1, y1 = FIELD
    r = FIELD_RADIUS_MM
    pts = [(x0, y0), (x1 - r, y0)]
    for a in np.linspace(-90, 0, 40):
        pts.append((x1 - r + r * math.cos(math.radians(a)), y0 + r + r * math.sin(math.radians(a))))
    pts += [(x1, y1), (x0, y1)]
    ink = (30, 30, 30, 255)
    cv2.fillPoly(img, [np.array([[px * PPM, py * PPM] for px, py in pts], np.int32)], ink, cv2.LINE_AA)
    cv2.circle(img, (int(DISC_CENTRE_MM[0] * PPM), int(DISC_CENTRE_MM[1] * PPM)),
               int(DISC_RADIUS_MM * PPM), ink, -1, cv2.LINE_AA)
    return img


def arm_config(garment_id: str, overrides: dict) -> PipelineConfig:
    return PipelineConfig(target_width_mm=PLATE_W_MM, forced_class="flat", thread_wt=WT,
                          garment_id=garment_id, **overrides)


def underlay_stats(plan: StitchPlan) -> dict:
    """What the arm sews under its fills: thread by kind, and the underlay's median
    stitch (the pass's 4 mm against the walk's 2.5)."""
    mm = {stitches.UNDERLAY: 0.0, stitches.FILL: 0.0}
    steps = []
    for _b, r in plan.iter_runs():
        if r.kind in mm:
            mm[r.kind] += r.length_mm
        if r.kind == stitches.UNDERLAY:
            steps += [math.dist(a, b) for a, b in zip(r.points, r.points[1:]) if math.dist(a, b) > 1e-9]
    steps.sort()
    return {"underlay_mm": round(mm[stitches.UNDERLAY], 1), "fill_mm": round(mm[stitches.FILL], 1),
            "underlay_share_pct": round(100.0 * mm[stitches.UNDERLAY] / max(1e-9, mm[stitches.FILL]), 1),
            "underlay_median_stitch_mm": round(steps[len(steps) // 2], 2) if steps else None}


def cut(cuts: Path) -> Path:
    img = plate_image()
    out = {"plate_mm": [PLATE_W_MM, PLATE_H_MM], "field_mm": list(FIELD), "field_radius_mm": FIELD_RADIUS_MM,
           "disc_centre_mm": list(DISC_CENTRE_MM), "disc_diameter_mm": 2 * DISC_RADIUS_MM, "cards": {}}
    for card, garment in GARMENTS.items():
        out["cards"][card] = {"garment_id": garment, "arms": {}}
        for label, ov in ARMS:
            _res, plan = digitize(img, arm_config(garment, ov))
            runs = [{"kind": r.kind, "shape_id": r.shape_id,
                     "points": [[round(q[0], 4), round(q[1], 4)] for q in r.points]} for _b, r in plan.iter_runs()]
            a = {"overrides": ov, "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
                 **underlay_stats(plan), "runs": runs}
            out["cards"][card]["arms"][label] = a
            print(f"{card}/{label}: {a['stitches']:,} st, underlay {a['underlay_mm']} mm "
                  f"({a['underlay_share_pct']}% of fill), median {a['underlay_median_stitch_mm']} mm", flush=True)
    cuts.mkdir(parents=True, exist_ok=True)
    path = cuts / "cut.json"
    path.write_text(json.dumps(out), encoding="utf-8")
    return path


class CardCU(v3.CardV3):
    DIGITIZED = ("U:",)


ARM_GAP = 6.0


def build(cuts: Path, card_name: str) -> tuple[StitchPlan, CardCU, dict]:
    d = json.loads((cuts / "cut.json").read_text(encoding="utf-8"))["cards"][card_name]
    c = CardCU(WT)
    report: list[dict] = []
    x, top = 0.0, 2.5
    for k, (label, ov) in enumerate(ARMS, start=1):
        a = d["arms"][label]
        runs = [StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=True, trim=False,
                          shape_id=r["shape_id"]) for r in a["runs"]]
        c.add(0, hc.teeth(x, top - 0.8, k), f"U:label:{label}")
        box = v3.place_runs(c, runs, x, top, "U", label)
        report.append({"card": card_name, "arm": label, "teeth": k, "overrides": ov,
                       **{key: a[key] for key in ("stitches", "underlay_mm", "fill_mm", "underlay_share_pct",
                                                  "underlay_median_stitch_mm")},
                       "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
        c.boxes[f"U{k}"] = box
        x = box[2] + ARM_GAP
    plan = c.plan()
    xs = [p[0] for b in plan.blocks for r in b.runs for p in r.points]
    ys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for b in plan.blocks:
        for r in b.runs:
            r.points = [(px - cx, py - cy) for px, py in r.points]
    for table in (c.boxes, c.arms):
        for kk, (a0, b0, c0, d0) in list(table.items()):
            table[kk] = (a0 - cx, b0 - cy, c0 - cx, d0 - cy)
    plan.design_size_mm = (max(xs) - min(xs), max(ys) - min(ys))
    return plan, c, {"pieces": report, "garment_id": d["garment_id"]}


README = """# Sew-out card: the pro's crossing underlay under a fill (2026-10-21)

**What it asks.** The pro sews one sparse crossing pass under every dense fill
on every job in his zip (~1.0 mm rows, ~4 mm stitches, ~90 degrees to the top
rows). Our hat preset sews an edge run plus a 2.0 mm zigzag; left chest and
beanie an edge run alone. `fill_underlay_cross` (built OFF) puts the pro's pass
in those three presets. Does it lie flatter, cover better, pucker less?
Every number is a candidate until you sew it (ROADMAP gate 1).

**What to sew:** two files, each **one dark cone, 40 wt**, 75/11, a **4 x 4 in
hoop**, trims on.

| File | Sew it on | Size | Stitches |
|---|---|---|---|
| `card_cross_underlay_hat_40wt.dst` | a cap front (or twill with your cap backing) | HAT_SIZE mm | HAT_ST |
| `card_cross_underlay_polo_40wt.dst` | a polo (pique) with cutaway; stands for the beanie too | POLO_SIZE mm | POLO_ST |

## How to read it

Each file is the same plate twice: a 26 x 18 mm field (one rounded corner) and a
10 mm disc. The **teeth** above a plate count its arm:

| Teeth | Arm |
|---|---|
| 1 | the preset as it ships (hat: edge run + 2.0 mm zigzag; polo: edge run) |
| 2 | `fill_underlay_cross` ON: the pro's crossing pass, no edge run |

Look for: fabric showing through the field; puckering or tunnelling round the
field and the disc; edges that wave or pull in; how flat the field lies when
the hoop comes off.

ARMS_TABLE

![hat](card_cross_underlay_hat_40wt.png)
![polo](card_cross_underlay_polo_40wt.png)
"""

SCORING = """# Readout sheet: crossing underlay

40 wt, 75/11, one dark cone. Y/N cells: write Y or N.

| File | Teeth | Fabric shows through (Y/N) | Pucker round the field (Y/N) | Disc round, not oval (Y/N) | Lies flat off the hoop (Y/N) | Note |
|---|---|---|---|---|---|---|
| hat | 1: preset | _ | _ | _ | _ | |
| hat | 2: cross | _ | _ | _ | _ | |
| polo | 1: preset | _ | _ | _ | _ | |
| polo | 2: cross | _ | _ | _ | _ | |

Better on the hat: ______   Better on the polo: ______
"""


def arms_table(pieces: list[dict]) -> str:
    lines = ["| File | Teeth | Arm | Stitches | Underlay thread | % of the fill's |",
             "|---|---|---|---|---|---|"]
    for p in pieces:
        lines.append(f"| {p['card']} | {p['teeth']} | {p['arm']} | {p['stitches']:,} | {p['underlay_mm']} mm | "
                     f"{p['underlay_share_pct']}% |")
    return "\n".join(lines)


def generate(out: Path, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    result: dict = {"cards": {}}
    pieces: list[dict] = []
    for card_name in GARMENTS:
        plan, card, extra = build(cuts, card_name)
        name = f"card_cross_underlay_{card_name}_40wt"
        pattern = plan_to_pattern(plan)
        pattern.metadata("name", f"CROSS UL {card_name.upper()}")
        path = out / f"{name}.dst"
        path.write_bytes(formats.write(pattern, "dst"))
        v3.render(plan, out / f"{name}.png")
        rb = v2.readback(path, plan, WT, card)
        rb["garment_id"] = extra["garment_id"]
        rb["pieces"] = extra["pieces"]
        rb["arm_md5"] = c4.arm_digests(plan)
        pieces += extra["pieces"]
        result["cards"][card_name] = rb
        if not quiet:
            print(json.dumps({k: v for k, v in rb.items() if k not in
                              ("pieces", "pieces_mm", "stitches_by_piece", "arm_md5")}))
    (out / "readback.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    h, p = result["cards"]["hat"], result["cards"]["polo"]
    text = (README.replace("ARMS_TABLE", arms_table(pieces))
            .replace("HAT_SIZE", f"{h['extent_mm'][0]} x {h['extent_mm'][1]}")
            .replace("POLO_SIZE", f"{p['extent_mm'][0]} x {p['extent_mm'][1]}")
            .replace("HAT_ST", f"{h['stitches_file']:,}")
            .replace("POLO_ST", f"{p['stitches_file']:,}"))
    (out / "README.md").write_text(text, encoding="utf-8")
    (out / "scoring-sheet.md").write_text(SCORING, encoding="utf-8")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", action="store_true", help="digitize the arms into --cuts")
    ap.add_argument("--cuts", default=str(DEFAULT_CUTS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    if args.cut:
        cut(Path(args.cuts))
        return 0
    generate(Path(args.out), Path(args.cuts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
