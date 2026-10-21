"""Sew-out card v5: small letters as satin, at the pro's size (2026-10-20)

    # 1. cut Fremont's words at 92.5 mm Hat, once per arm (minutes each)
    python -m tools.sewout_card_v5 --cut today
    python -m tools.sewout_card_v5 --cut sat050      # ... every key of CUTS
    # 2. build the card (reads the cuts)
    python -m tools.sewout_card_v5 [--out ../docs/sewout/card-v5-2026-10-20]

Card v4's sew-out (same night) beside the pro's Fremont patch: "your lettering
is much smaller than the pro's". Rendered at the same width, ours sits in the
art's own footprint but as a hairline bean line; the pro sews each stroke as
0.8-0.9 mm satin (`docs/sewout/card-v4-2026-10-20/pro_vs_ours_92mm.png`). This
card asks the cloth how wide: one ROW per arm, each row Fremont's EST, 1895, THE
and EAT | STAY | PLAY at **92.5 mm Hat (the pro's size)**, so every row can be
held against the pro's patch.

- row 1  today (3-pass bean)
- row 2  `bean_letter_satin_mm` 0.5
- row 3  `bean_letter_satin_mm` 0.65
- row 4  `bean_letter_satin_mm` 0.85 (the pro's median column)

Everything else is today's default config. One dark cone, 40 wt, 4 x 4 in hoop.
Through `digitizer_service.formats.write` (pystitch), read back with pystitch.
EVERY NUMBER HERE IS A CANDIDATE UNTIL KENT SEWS IT (gate 1). No default changes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.stitches import StitchPlan  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402
from tools import sewout_card_v4 as c4  # noqa: E402

REPO = hc.REPO
WT = v3.WT
WIDTH_MM = 92.5                      # the pro's Fremont patch
NAME = "card_v5_40wt"
DEFAULT_OUT = REPO / "docs" / "sewout" / "card-v5-2026-10-20"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"

#: arm -> overrides on today's Studio request, in row (tooth) order
CUTS = {
    "today": {},
    "sat050": {"bean_letter_satin_mm": 0.5},
    "sat065": {"bean_letter_satin_mm": 0.65},
    "sat085": {"bean_letter_satin_mm": 0.85},
}
LABEL = {"today": "bean (today)", "sat050": "satin 0.5", "sat065": "satin 0.65", "sat085": "satin 0.85"}
WORDS = {k: c4.WORDS[k] for k in ("EST", "1895", "THE", "TAG")}
ROW_WORDS = ("EST", "1895", "THE", "TAG")


def cut(name: str, cuts: Path) -> Path:
    v3.CUT_ARMS[name] = dict(CUTS[name])
    return v3.cut_arm(name, cuts, width_mm=WIDTH_MM, boxes=WORDS)


class CardV5(v3.CardV3):
    DIGITIZED = ("R",)


WORD_GAP = 4.0
ROW_GAP = 4.0
TEETH_W = 6.0           # room left of each row for its teeth


def build(cuts: Path) -> tuple[StitchPlan, CardV5, dict]:
    c = CardV5(WT)
    report: list[dict] = []
    y = 0.0
    for k, arm in enumerate(CUTS, start=1):
        top = y + 1.5
        c.add(0, hc.teeth(0.0, top + 1.0, k), f"R:label:{arm}")
        x, bottom = TEETH_W + 1.2 * k, top
        for word in ROW_WORDS:
            runs = c4.word_runs(cuts, arm, word)
            box = v3.place_runs(c, runs, x, top, "R", f"{word}-{arm}")
            b = v3.load_cut(cuts, arm, word)
            report.append({"row": k, "arm": arm, "word": word, "overrides": CUTS[arm], "runs": len(runs),
                           "crossing_runs_dropped": b["crossing_runs_dropped"],
                           "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
            x = box[2] + WORD_GAP
            bottom = max(bottom, box[3])
        c.boxes[f"R{k}"] = (0.0, y, x - WORD_GAP, bottom)
        y = bottom + ROW_GAP
    plan = c.plan()
    xs = [p[0] for b in plan.blocks for r in b.runs for p in r.points]
    ys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for b in plan.blocks:
        for r in b.runs:
            r.points = [(px - cx, py - cy) for px, py in r.points]
    for table in (c.boxes, c.arms):
        for kk, (a, b2, c2, d) in list(table.items()):
            table[kk] = (a - cx, b2 - cy, c2 - cx, d - cy)
    plan.design_size_mm = (max(xs) - min(xs), max(ys) - min(ys))
    return plan, c, {"pieces": report}


README = """# Sew-out card v5 (2026-10-20): small letters as satin, at the pro's size

**Sew this beside the pro's Fremont patch.** Card v4's sew-out showed our small
letters reading far smaller than the pro's. Rendered at the same size they sit
in the art's own footprint, but as a thin bean line; the pro fills each stroke
with ~0.85 mm satin (`../card-v4-2026-10-20/pro_vs_ours_92mm.png`). This card
asks how wide the satin should be. Every number is a candidate until you sew it.

**What to sew:** `card_v5_40wt.dst`, **one dark cone**, **40 wt**, 75/11, a
**4 x 4 in hoop** (the design is SIZE_MM mm), cap front or twill with your
Fremont backing. STITCHES stitches, TRIMS trims, about MINUTES minutes. Trims on.

## How to read it

Four **rows**, each Fremont's EST, 1895, THE and EAT | STAY | PLAY at
**92.5 mm, the pro's size** (hold each row up to his patch). The **teeth** at
the left of a row count it:

| Teeth | Row |
|---|---|
| 1 | today: 3-pass bean line |
| 2 | satin column **0.5 mm** wide |
| 3 | satin column **0.65 mm** |
| 4 | satin column **0.85 mm** (the pro's median) |

Look for: which row reads most like the pro's; do the 8's two holes, the 9's, the
E's and the A's stay open; do the letters stay crisp or turn to blobs; thread
breaks; puckering.

![](card_v5_40wt.png)

## The file (pystitch reading the DST back)

READBACK
"""

SCORING = """# Readout sheet, sew-out card v5

`card_v5_40wt.dst`, 40 wt, 75/11, one dark cone. Hold each row against the pro's
Fremont patch. Y/N cells: write Y or N.

| Row (teeth) | Breaks | Reads like the pro's (Y/N) | 8 holes open | 9 hole open | E / A gaps open | Crisp, not blobby (Y/N) | Note |
|---|---|---|---|---|---|---|---|
| 1: bean (today) | ___ | _ | _ | _ | _ | _ | |
| 2: satin 0.5 | ___ | _ | _ | _ | _ | _ | |
| 3: satin 0.65 | ___ | _ | _ | _ | _ | _ | |
| 4: satin 0.85 | ___ | _ | _ | _ | _ | _ | |

Best row: ______
"""


def generate(out: Path, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "CARD V5 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    v3.render(plan, out / f"{NAME}.png")
    rb = v2.readback(path, plan, WT, card)
    rb["pieces"] = extra["pieces"]
    rb["arm_md5"] = c4.arm_digests(plan)
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items() if k not in
                          ("pieces", "pieces_mm", "stitches_by_piece", "arm_md5")}))
    (out / "readback.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    text = (README.replace("READBACK", v3.readback_markdown(rb))
            .replace("SIZE_MM", f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}")
            .replace("STITCHES", f"{rb['stitches_file']:,}")
            .replace("TRIMS", f"{rb.get('trims', '?')}")
            .replace("MINUTES", f"{rb['stitches_file'] / 650:.0f}"))
    (out / "README.md").write_text(text, encoding="utf-8")
    (out / "scoring-sheet.md").write_text(SCORING, encoding="utf-8")
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=list(CUTS))
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
