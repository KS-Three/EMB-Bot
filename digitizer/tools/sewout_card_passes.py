"""The pass-count swatch: how wide does a bean letter really sew? (2026-10-14)

    # 1. cut THE and 1895 out of the Studio-request replay (81 mm, Hat), once per
    #    arm (a digitize is minutes and gigabytes: ONE process at a time)
    python -m tools.sewout_card_passes --cut p1 --cuts DIR
    python -m tools.sewout_card_passes --cut p2 --cuts DIR
    python -m tools.sewout_card_passes --cut p3 --cuts DIR
    # 2. build the card (no Fremont digitize; reads the cuts)
    python -m tools.sewout_card_passes [--out ../docs/sewout/card-passes-2026-10-14]

Kent, 2026-10-14: *"Thread can be mushed together, can you do some research
on what happens if we just stitch on top of the other stitch for coverage?"*
A bean letter already IS thread on top of thread: `BEAN_PASSES` (3) laps of
one run through the same holes. `stitchviz` draws those laps as ONE thread
(DOCTRINE: "The renderer draws three bean passes as one thread", suspected,
never measured), so no render can say how wide a stacked line sews, whether
the 5's small opening survives it, or whether 0.45 mm holes hit three times
hold on a hat. This card asks the cloth.

Two blocks, each Fremont's own lettering cut from the replay of the Studio
request at 81 mm on a Hat, with `small_text_true_size` ON (bean letters,
pitch 0.45, corner stations) and the lap count the only thing that differs:

- T  "THE":  1 tooth one pass, 2 teeth two passes, 3 teeth three (today).
- N  "1895": the same three arms.

Every other setting is today's default (`small_glyph_keep` ON since card
v3; pinning it OFF as v3 did drops the 1 and the 9 and sews 1895 as plain
outlines, which no pass count reaches). Built with card v3's pieces (cut, place,
index strip, teeth, render, read-back); the file goes through
`digitizer_service.formats.write` (pystitch) and is read back with pystitch,
never the browser's DST codec. 40 wt, one colour. EVERY NUMBER HERE IS A
CANDIDATE UNTIL KENT SEWS IT (ROADMAP gate 1). No engine change.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.stitches import StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402

REPO = hc.REPO
WT = v3.WT
NAME = "card_passes_40wt"
DEFAULT_OUT = REPO / "docs" / "sewout" / "card-passes-2026-10-14"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"

#: arm -> the replay's overrides. Only `bean_letter_passes` differs; the two
#: holds are pinned OFF (they are ON by default since 2026-10-15, after this
#: card was cut) so a re-cut sews what the committed cuts record.
ARMS = {f"p{n}": {"small_text_true_size": True, "bean_letter_passes": n,
                  "bean_letter_counter_hold_mm": None, "bean_letter_bay_hold": None,
                  "bean_letter_straight_mm": None}
        for n in (1, 2, 3)}
ARM_ORDER = ("p1", "p2", "p3")
#: block -> card v3's cut box (`sewout_card_v3.CUT_BOXES`): T is "THE", N is "1895".
BLOCKS = ("T", "N")
BLOCK_WIDTH_MM = {"T": 26.0, "N": 20.0}


def cut(arm: str, cuts: Path) -> Path:
    """Digitize Fremont at 81 mm on a Hat with this arm's overrides and save
    the runs inside card v3's T and N boxes (`sewout_card_v3.cut_arm`)."""
    v3.CUT_ARMS[arm] = dict(ARMS[arm])
    return v3.cut_arm(arm, cuts)


def block(c: v3.CardV3, blk: str, x0: float, y0: float, cuts: Path, report: list) -> None:
    """One block: the box's runs from each arm's cut, side by side, teeth = passes."""
    c.index(blk, x0, y0, BLOCK_WIDTH_MM[blk])
    top = y0 + 9.0
    x = x0
    right, bottom = x0, top
    for k, arm in enumerate(ARM_ORDER, start=1):
        b = v3.load_cut(cuts, arm, blk)
        runs = [StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=True, trim=False,
                          shape_id=r["shape_id"]) for r in b["runs"]]
        box = v3.place_runs(c, runs, x, top, blk, arm)
        c.add(0, hc.teeth(x, top - 0.8, k), f"{blk}:label:{arm}")
        report.append({"block": blk, "arm": arm, "passes": k, "roi": b["roi"], "overrides": ARMS[arm],
                       "runs": len(runs), "stitches": sum(len(r.points) for r in runs),
                       "crossing_runs_dropped": b["crossing_runs_dropped"],
                       "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
        x = box[2] + 5.0
        right, bottom = max(right, box[2]), max(bottom, box[3])
    c.boxes[blk] = (x0, y0, max(right, x0 + BLOCK_WIDTH_MM[blk]), bottom)


def build(cuts: Path) -> tuple[StitchPlan, v3.CardV3, dict]:
    c = v3.CardV3(WT)
    report: list[dict] = []
    block(c, "T", 0.0, 0.0, cuts, report)
    block(c, "N", 0.0, c.boxes["T"][3] + 5.0, cuts, report)
    plan = c.plan()
    xs = [p[0] for b in plan.blocks for r in b.runs for p in r.points]
    ys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for b in plan.blocks:
        for r in b.runs:
            r.points = [(x - cx, y - cy) for x, y in r.points]
    for table in (c.boxes, c.arms):
        for k, (a, b2, c2, d) in list(table.items()):
            table[k] = (a - cx, b2 - cy, c2 - cx, d - cy)
    plan.design_size_mm = (max(xs) - min(xs), max(ys) - min(ys))
    return plan, c, {"pieces": report, "offset_mm": (round(cx, 3), round(cy, 3))}


ROWS = (("T  THE at 81 mm: 1 | 2 | 3 passes (1 / 2 / 3 teeth)", ("T:p1", "T:p2", "T:p3")),
        ("N  1895 at 81 mm: 1 | 2 | 3 passes (1 / 2 / 3 teeth)", ("N:p1", "N:p2", "N:p3")))


def panel(plan: StitchPlan, card: v3.CardV3, out: Path, ppm: float = 60.0) -> None:
    saved = v3.ROWS
    v3.ROWS = ROWS
    try:
        v3.panel(plan, card, out, ppm)
    finally:
        v3.ROWS = saved


README = """# Sew-out card: bean passes (2026-10-14)

Kent asked what happens when thread is stitched on top of thread. A bean
letter already is: three passes of one run through the same holes. Our
renderer draws those three passes as ONE thread, so no picture can say how
wide they really sew. This card asks the cloth.

**What to sew:** `card_passes_40wt.dst`, one colour (dark), 40 wt, on a hat
front like the Fremont job.

**What is on it:** Fremont's own "THE" (row T) and "1895" (row N) at 81 mm,
cut from the logo's replay with `small_text_true_size` ON. The teeth above
each copy count its passes: 1 tooth = one pass, 2 = two, 3 = three (what the
switch sews today). Nothing else differs between the copies.

**What to look at, per copy:**

1. Line width: does each extra pass make the line visibly wider, or just
   higher / glossier?
2. The 5 in 1895: is the small opening at its top still open?
3. The 8's two holes and the 9's hole: open or filled?
4. The fabric: any shredded or enlarged holes, puckering, or thread breaks
   (three passes put three needle hits in holes 0.45 mm apart)?
5. Which one reads best from arm's length?

The pictures in `card_passes_40wt_blocks.png` are the renderer's view: all
three copies look nearly the same there. That is the point of sewing it.

## Pieces

PIECES

## The file checks (pystitch reading the DST back)

READBACK
"""


def pieces_markdown(pieces: list[dict]) -> str:
    out = ["| block | arm | passes | stitches | runs | size (mm) |", "|---|---|---|---|---|---|"]
    for p in pieces:
        out.append(f"| {p['block']} | {p['arm']} | {p['passes']} | {p['stitches']:,} | {p['runs']} | "
                   f"{p['width_mm']} x {p['height_mm']} |")
    return "\n".join(out)


def generate(out: Path, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "PASSES 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    v3.render(plan, out / f"{NAME}.png")
    panel(plan, card, out / f"{NAME}_blocks.png")
    rb = v2.readback(path, plan, WT, card)
    rb["pieces"] = extra["pieces"]
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items() if k not in ("pieces", "pieces_mm", "stitches_by_piece")}))
    (out / "readback.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    text = (README.replace("PIECES", pieces_markdown(extra["pieces"]))
            .replace("READBACK", v3.readback_markdown(rb)))
    (out / "README.md").write_text(text, encoding="utf-8")
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=list(ARMS), help="digitize Fremont with this arm and save its cuts")
    ap.add_argument("--cuts", default=str(DEFAULT_CUTS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    if args.cut:
        cut(args.cut, Path(args.cuts))
        return 0
    generate(Path(args.out), Path(args.cuts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
