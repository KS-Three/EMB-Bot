"""Sew-out card v6: small letters RE-SET like the pro, at the pro's size (2026-10-21)

    # 1. cut Fremont's grown words at 92.5 mm Hat, once per arm (minutes each)
    python -m tools.sewout_card_v6 --cut condensed
    python -m tools.sewout_card_v6 --cut reset
    # 2. build the card (reads the cuts)
    python -m tools.sewout_card_v6 [--out ../docs/sewout/card-v6-2026-10-21]

PR #1029 re-sets grown small text the way the pro's files set it (rule R4 of
`docs/pro-digitizer-rules-2026-10-21.md`): letters grown to ~4 mm, the gaps
between them closed to ~0.25 mm of visible fabric, strokes bold with height.
Measured on our own DST it already sews the pro's column widths; whether the
GAPS are right is a cloth question (ROADMAP gate 1). One ROW per arm, each
Fremont's EST, 1895, THE and EAT STAY PLAY at **92.5 mm Hat (the pro's
size)**, to hold against his patch:

- row 1  #1024 + #1025 as built: condensed growth (cap 4.0, width 1.05,
         stroke 0.85) + `lettering_columns_small_bold`
- row 2  this PR: the same, re-set (`small_text_cap_letter_gap_mm` 0.25,
         `small_text_cap_bold_scale` 1.45; `max_width_scale` not read)

A word is the runs of its grown letters (`small_text_enlarged`), cut by shape
id in each arm's own frame -- re-set words MOVE (the date 3 mm down), so a
fixed box on the art would clip them. The tagline's `|` bars are another
colour on the patch and are left out of both rows. Everything else is today's
default config. One dark cone, 40 wt, 4 x 4 in hoop. Through
`digitizer_service.formats.write` (pystitch), read back with pystitch.
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
from digitizer_core.stitches import StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402
from tools import sewout_card_v4 as c4  # noqa: E402

REPO = hc.REPO
WT = v3.WT
WIDTH_MM = 92.5                      # the pro's Fremont patch
ART = ROOT / "testdata" / "photo" / "logo_hotel_fremont.webp"   # Kent's upload
NAME = "card_v6_40wt"
DEFAULT_OUT = REPO / "docs" / "sewout" / "card-v6-2026-10-21"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"

GROW = {"small_text_cap_mm": 4.0, "small_text_cap_min_stroke_mm": 0.85,
        "lettering_columns_small_bold": True}
#: arm -> overrides on today's Studio request, in row (tooth) order
CUTS = {
    "condensed": {**GROW, "small_text_cap_max_width_scale": 1.05},
    "reset": {**GROW, "small_text_cap_letter_gap_mm": 0.25, "small_text_cap_bold_scale": 1.45},
}
ROW_WORDS = ("EST", "1895", "THE", "TAG")


def _words(regions) -> dict[str, list[str]]:
    """Grown letters -> {word: [shape ids]}: lines by vertical centre (date,
    THE, tagline, top to bottom); on the date line, EST is the left half."""
    grown = [r for r in regions if r.meta.get("small_text_enlarged")]
    by_cid: dict[str, list] = {}
    for r in grown:
        by_cid.setdefault(r.meta.get("text_cluster_id") or r.shape_id, []).append(r)

    def box(rs):
        b = [r.polygon.bounds for r in rs]
        return min(v[0] for v in b), min(v[1] for v in b), max(v[2] for v in b), max(v[3] for v in b)
    lines: list[list[list]] = []
    for rs in sorted(by_cid.values(), key=lambda rs: (box(rs)[1] + box(rs)[3]) / 2):
        mid = (box(rs)[1] + box(rs)[3]) / 2
        if lines and abs(mid - (box(lines[-1][0])[1] + box(lines[-1][0])[3]) / 2) < 1.5:
            lines[-1].append(rs)
        else:
            lines.append([rs])
    if len(lines) != 3:
        raise SystemExit(f"expected 3 grown lines (date, THE, tagline), got {len(lines)}")
    date, the, tag = lines
    date.sort(key=lambda rs: box(rs)[0])
    if len(date) != 2:
        raise SystemExit(f"expected EST and 1895 on the date line, got {len(date)} clusters")
    ids = lambda groups: [r.shape_id for rs in groups for r in rs]
    return {"EST": ids(date[:1]), "1895": ids(date[1:]), "THE": ids(the), "TAG": ids(tag)}


def cut(arm: str, cuts: Path) -> Path:
    """Digitize Fremont at 92.5 mm Hat with this arm's overrides and save each
    word's runs (its grown letters' own runs, every kind) as JSON."""
    from tools import pro_pair
    d = pro_pair.digitize(ART, WIDTH_MM, "hat_front", extra=dict(CUTS[arm]))
    words = _words(d.result.regions)
    out = {"arm": arm, "overrides": CUTS[arm], "width_mm": WIDTH_MM, "words": {}}
    for word, sids in words.items():
        keep = set(sids)
        runs = [{"kind": r.kind, "shape_id": r.shape_id, "points": [[round(x, 4), round(y, 4)] for x, y in r.points]}
                for b in d.plan.blocks for r in b.runs if r.shape_id in keep and len(r.points) > 1]
        out["words"][word] = {"letters": len(sids), "runs": runs}
        print(f"{arm}/{word}: {len(sids)} letters, {len(runs)} runs", flush=True)
    cuts.mkdir(parents=True, exist_ok=True)
    path = cuts / f"{arm}.json"
    path.write_text(json.dumps(out), encoding="utf-8")
    return path


def word_runs(cuts: Path, arm: str, word: str) -> tuple[list[StitchRun], int]:
    data = json.loads((cuts / f"{arm}.json").read_text(encoding="utf-8"))["words"][word]
    return [StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=True, trim=False,
                      shape_id=r["shape_id"]) for r in data["runs"]], data["letters"]


class CardV6(v3.CardV3):
    DIGITIZED = ("R",)


WORD_GAP = 4.0
ROW_GAP = 4.0
TEETH_W = 6.0           # room left of each row for its teeth


def build(cuts: Path) -> tuple[StitchPlan, CardV6, dict]:
    c = CardV6(WT)
    report: list[dict] = []
    y = 0.0
    for k, arm in enumerate(CUTS, start=1):
        top = y + 1.5
        c.add(0, hc.teeth(0.0, top + 1.0, k), f"R:label:{arm}")
        x, bottom = TEETH_W + 1.2 * k, top
        for word in ROW_WORDS:
            runs, letters = word_runs(cuts, arm, word)
            box = v3.place_runs(c, runs, x, top, "R", f"{word}-{arm}")
            report.append({"row": k, "arm": arm, "word": word, "letters": letters, "runs": len(runs),
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


README = """# Sew-out card v6 (2026-10-21): small letters re-set like the pro

**Sew this beside the pro's Fremont patch.** The pro raises Fremont's small
words to ~4 mm and re-sets them as bold block letters with the gaps between
letters closed to 0.15-0.35 mm (`docs/pro-digitizer-rules-2026-10-21.md`,
R4). Card v5 asked how wide the satin should be; this card asks whether the
**spacing** is right. Every number is a candidate until you sew it.

**What to sew:** `card_v6_40wt.dst`, **one dark cone**, **40 wt**, 75/11, a
**4 x 4 in hoop** (the design is SIZE_MM mm), cap front or twill with your
Fremont backing. STITCHES stitches, TRIMS trims, about MINUTES minutes. Trims on.

## How to read it

Two **rows**, each Fremont's EST, 1895, THE and EAT STAY PLAY at **92.5 mm,
the pro's size** (hold each row up to his patch). The tagline's `|` bars are
left out of both rows (another colour on the patch). The **teeth** at the
left of a row count it:

| Teeth | Row |
|---|---|
| 1 | #1024 + #1025 as built: grown condensed to 4 mm, bold satin |
| 2 | **re-set (PR #1029)**: same size and stroke, letters spaced ~0.25 mm apart |

Measured off the files (not the cloth): row 2's letter gaps read 0.27-0.47 mm
against the pro's 0.15-0.6; its columns 0.80-0.90 mm against his 0.90. Row 1's
letters within a word touch.

**Known before you sew:** on row 2 the 5 of 1895 and the S close their
openings (1895 can read "1898"); the pro draws those digits wider.

Look for: does row 2 read like the pro's letters, letter by letter; are the
gaps open on the cloth, or too wide; do the A's and the 8's counters stay open;
thread breaks; puckering.

![](card_v6_40wt.png)

## The file (pystitch reading the DST back)

READBACK
"""

SCORING = """# Readout sheet, sew-out card v6

`card_v6_40wt.dst`, 40 wt, 75/11, one dark cone. Hold each row against the pro's
Fremont patch. Y/N cells: write Y or N.

| Row (teeth) | Breaks | Reads like the pro's (Y/N) | Gaps between letters open | Gaps too wide (Y/N) | 8 / A counters open | 5 reads as 5 (Y/N) | Note |
|---|---|---|---|---|---|---|---|
| 1: condensed (#1024+#1025) | ___ | _ | _ | _ | _ | _ | |
| 2: re-set (#1029) | ___ | _ | _ | _ | _ | _ | |

Better row: ______
"""


def generate(out: Path, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "CARD V6 40WT")
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
