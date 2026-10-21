"""Sew-out card v4: one hoop, one cone, today's engine (2026-10-20)

    # 1. cut Fremont's words out of the Studio-request replay at 81 mm Hat,
    #    once per cut (a digitize is minutes and gigabytes: ONE process at a time)
    python -m tools.sewout_card_v4 --cut today
    python -m tools.sewout_card_v4 --cut straight_off
    ...                                             # every key of CUTS
    # 2. build the card (no digitize; reads the cuts)
    python -m tools.sewout_card_v4 [--out ../docs/sewout/card-v4-2026-10-20]

Replaces the three unsewn cards (v3.2, lettering arms, bay hold / edge cap) for
Kent's next sew-out: those were cut on 10-14/15, and about ten flips have landed
since, so their "today" arms are no longer what ships. Every arm here is
TODAY'S DEFAULT CONFIG except the one flag its block names, so the 1-tooth arm
of every block is what a customer gets tonight.

Kent asked for ONE piece of fabric, one evening: 4 x 4 in hoop, one dark cone,
the Fremont 81 mm Hat job (the job he sews). The blocks are the questions a
sew-out can settle on that job:

- B  `bean_letter_straight_mm`: 0.7 (today, Kent's flip 10-20) | OFF | 0.9.
     "1 is wiggly", "EAT STAY PLAY are wiggly": does a long straight stitch
     read straighter, and does a 3-pass stitch that long hold?
- H  the bean holds (counter 0.25 + bay 0.2, ON 10-15, unsewn) | both OFF.
     Do the 8's / 9's counters stay open, at what fattening?
- K  `small_letter_ties`: OFF (today) | ON. Knots at letter ends?
- P  `bean_letter_passes`: 3 (today) | 2 | 1. Thread laid on itself: wider or
     only higher? Holes hit three times 0.45 mm apart?

Cut and dropped (DROPPED_CUTS): `small_lettering_skeleton` and
`lettering_columns_fold_cuts` sewed the same stitches in both arms on every
word at 81 mm, so cloth could answer nothing. Dropped on purpose: detail spokes (the star is WHITE on a black host: two cones),
forbid gap and overlap-by-angle (seams between two colours: two cones), the edge
cap's bean pitch (a different fixture), line chaining (two cones, a photo).

The file goes through `digitizer_service.formats.write` (pystitch) and is read
back with pystitch, never the browser's DST codec. 40 wt. EVERY NUMBER HERE IS
A CANDIDATE UNTIL KENT SEWS IT (ROADMAP gate 1: this card IS the sew-out). No
default is changed by this tool.
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
from tools import sewout_card_lettering_arms as la  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402

REPO = hc.REPO
WT = v3.WT
WIDTH_MM = 81.0
NAME = "card_v4_40wt"
DEFAULT_OUT = REPO / "docs" / "sewout" / "card-v4-2026-10-20"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"

#: cut -> overrides on today's Studio request (empty = today's defaults exactly)
CUTS = {
    "today": {},
    "straight_off": {"bean_letter_straight_mm": None},
    "straight_09": {"bean_letter_straight_mm": 0.9},
    "holds_off": {"bean_letter_counter_hold_mm": None, "bean_letter_bay_hold": None},
    "ties_on": {"small_letter_ties": True},
    "passes_2": {"bean_letter_passes": 2},
    "passes_1": {"bean_letter_passes": 1},
}
#: cut 2026-10-20 and DROPPED from the card: on today's engine both arms of every
#: word came out the SAME stitches at 81 mm (the skeleton's tagline is a bean letter
#: now; fold cuts do not touch FREMONT's M->O or final T), so cloth could tell
#: nothing. Kept so `--cut` can re-check that after an engine change.
DROPPED_CUTS = {
    "skel_on": {"small_lettering_skeleton": True},
    "folds_off": {"lettering_columns_fold_cuts": False},
}
#: word -> fremont_triage.ROIS key; every cut saves every box
WORDS = {"EST": ("est", ()), "1895": ("1895", ()), "THE": ("the", ()), "TAG": ("tagline", ()),
         "MO": ("m_o_junction", ()), "T": ("final_t", ())}

ROW_BREAK = "/"          # in a block's words: start the block's next row
#: block -> (index letter, [(arm label, cut), ...] in tooth order, words in row order)
BLOCKS = {
    "B": ("B", [("0.7", "today"), ("off", "straight_off"), ("0.9", "straight_09")], ("TAG", ROW_BREAK, "1895")),
    "H": ("H", [("on", "today"), ("off", "holds_off")], ("1895", "THE")),
    "K": ("K", [("off", "today"), ("ties", "ties_on")], ("EST", "THE")),
    "P": ("P", [("3", "today"), ("2", "passes_2"), ("1", "passes_1")], ("1895", "THE")),
}


def cut(name: str, cuts: Path) -> Path:
    """Digitize Fremont at 81 mm Hat with this cut's overrides on today's
    defaults and save the runs inside every word box (`sewout_card_v3.cut_arm`)."""
    v3.CUT_ARMS[name] = dict({**CUTS, **DROPPED_CUTS}[name])
    return v3.cut_arm(name, cuts, width_mm=WIDTH_MM, boxes=WORDS)


# --- the card ---------------------------------------------------------------------------

LETTERS = {**la.LETTERS,
           "B": [(0, 0), (0, 4), (2.5, 4), (3, 3), (2.5, 2), (0, 2), (2.5, 2), (3, 1), (2.5, 0), (0, 0)],
           "H": [(0, 4), (0, 0), (0, 2), (3, 2), (3, 4), (3, 0)],
           "K": [(0, 4), (0, 0), (0, 2), (3, 4), (0, 2), (3, 0)],
           "P": [(0, 4), (0, 0), (2.5, 0), (3, 1), (2.5, 2), (0, 2)]}


class CardV4(v3.CardV3):
    """Card v3's colour stop and digitized-piece rule, with this card's blocks."""

    DIGITIZED = tuple(f"{k}:" for k in BLOCKS)

    def index(self, key: str, x0: float, y0: float, width: float) -> None:
        self.add(0, hc.corners([(x0 + a, y0 + b) for a, b in LETTERS[BLOCKS[key][0]]]), f"{key}:index")
        self.add(0, hc.corners([(x0 + 5.0, y0 + 5.0), (x0 + width, y0 + 5.0)]), f"{key}:rule")


def word_runs(cuts: Path, cut_name: str, word: str) -> list[StitchRun]:
    b = v3.load_cut(cuts, cut_name, word)
    return [StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=True, trim=False,
                      shape_id=r["shape_id"]) for r in b["runs"]]


ARM_GAP = 3.0           # between the arms of a word (each arm's teeth sit over it)
WORD_GAP = 3.0          # extra, between words of a block
BLOCK_GAP = 3.5         # between block rows


def block(c: CardV4, key: str, x0: float, y0: float, cuts: Path, report: list) -> tuple[float, float]:
    """One block on one row: the index strip, then each word's arms side by
    side (teeth = the arm's number). Returns the block's (right, bottom)."""
    _letter, arms, _words = BLOCKS[key]
    top = y0 + 7.5
    x, bottom, right = x0, top, x0
    for word in _words:
        if word == ROW_BREAK:                   # the block's next row of words
            right = max(right, x - WORD_GAP - ARM_GAP)
            x, top = x0, bottom + 6.0
            continue
        for k, (label, cut_name) in enumerate(arms, start=1):
            arm = f"{word}-{label}"
            runs = word_runs(cuts, cut_name, word)
            box = v3.place_runs(c, runs, x, top, key, arm)
            c.add(0, hc.teeth(x, top - 0.8, k), f"{key}:label:{arm}")
            b = v3.load_cut(cuts, cut_name, word)
            report.append({"block": key, "arm": arm, "word": word, "label": label, "cut": cut_name,
                           "overrides": CUTS[cut_name], "roi": b["roi"], "runs": len(runs),
                           "crossing_runs_dropped": b["crossing_runs_dropped"],
                           "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
            x = max(box[2], x + 1.2 * k + 1.0) + ARM_GAP
            bottom = max(bottom, box[3])
        x += WORD_GAP
    right = max(right, x - WORD_GAP - ARM_GAP)
    c.index(key, x0, y0, max(right - x0, 12.0))
    c.boxes[key] = (x0, y0, max(right, x0 + 12.0), bottom)
    return right, bottom


#: rows of blocks, top to bottom; blocks in a row sit left to right
LAYOUT = (("B",), ("H", "K"), ("P",))


def words_of(key: str) -> tuple[str, ...]:
    return tuple(w for w in BLOCKS[key][2] if w != ROW_BREAK)


def build(cuts: Path) -> tuple[StitchPlan, CardV4, dict]:
    c = CardV4(WT)
    report: list[dict] = []
    y = 0.0
    for row in LAYOUT:
        x, bottom = 0.0, y
        for key in row:
            right, b = block(c, key, x, y, cuts, report)
            x = right + 6.0
            bottom = max(bottom, b)
        y = bottom + BLOCK_GAP
    plan = c.plan()
    xs = [p[0] for b in plan.blocks for r in b.runs for p in r.points]
    ys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for b in plan.blocks:
        for r in b.runs:
            r.points = [(px - cx, py - cy) for px, py in r.points]
    for table in (c.boxes, c.arms):
        for k, (a, b2, c2, d) in list(table.items()):
            table[k] = (a - cx, b2 - cy, c2 - cx, d - cy)
    plan.design_size_mm = (max(xs) - min(xs), max(ys) - min(ys))
    return plan, c, {"pieces": report, "offset_mm": (round(cx, 3), round(cy, 3))}


block_digests = la.block_digests
arm_digests = la.arm_digests


def rows() -> tuple:
    out = []
    for key, (_letter, arms, _w) in BLOCKS.items():
        words = words_of(key)
        names = " | ".join(f"{lbl} ({k})" for k, (lbl, _c) in enumerate(arms, start=1))
        out.append((f"{key} {'/'.join(words)}: {names} teeth",
                    tuple(f"{key}:{w}-{lbl}" for w in words for lbl, _c in arms)))
    return tuple(out)


def panel(plan: StitchPlan, card: CardV4, out: Path, ppm: float = 60.0) -> None:
    saved = v3.ROWS
    v3.ROWS = rows()
    try:
        v3.panel(plan, card, out, ppm)
    finally:
        v3.ROWS = saved


def same_arms(rb: dict) -> list[str]:
    """Words whose arms are the same stitches (the flag changed nothing there)."""
    md5 = rb["arm_md5"]
    out = []
    for key, (_l, arms, _w) in BLOCKS.items():
        for w in words_of(key):
            ds = [md5.get(f"{key}:{w}-{lbl}") for lbl, _c in arms]
            if len(set(ds)) < len(ds):
                same = [arms[i][0] for i in range(len(ds)) for j in range(len(ds)) if i != j and ds[i] == ds[j]]
                out.append(f"{key} {w}: arms {', '.join(sorted(set(same)))} identical")
    return out


# --- docs -----------------------------------------------------------------------------------

README = """# Sew-out card v4 (2026-10-20)

**Sew this one. It replaces card v3.2, the lettering-arms card and the bay-hold /
edge-cap card**, which were cut before about ten flips landed (10-15 to 10-20);
their baseline arms are no longer what ships. Those folders stay for history.
Don't sew them.

Every arm here is **today's default engine** except the one flag its block
names, so the **1-tooth arm of every block is what a customer gets tonight**.
Every number is a candidate until you sew it (ROADMAP gate 1).

**What to sew:** `card_v4_40wt.dst`, **one colour (dark)**, **40 wt**, a **4 x 4 in
hoop** (the design is SIZE_MM mm), on a **cap front or the same structured
twill**, with your Fremont backing. STITCHES stitches, TRIMS trims: allow about
MINUTES minutes (from the stitch count at 650 spm, not a measurement).

## How to sew it

1. Load the DST. Needle at the centre (the file's origin is the middle of the
   box). Trace the outline.
2. **Trims on.** One colour, no stop.
3. Count thread breaks, per block if you can.
4. Don't press. Photograph each block close up and the whole card at arm's
   length, and send the photos.

## How to read it

Each block has an **index letter** (B, H, K, P, sewn as a run with a rule
beside it). The arms of each word sit side by side, labelled by **teeth** above
them, counted from the left.

![](card_v4_40wt.png)

| Block | Words | 1 tooth | 2 teeth | 3 teeth | The question |
|---|---|---|---|---|---|
| **B** | 1895, EAT STAY PLAY | straight stretches **0.7 mm** (today) | OFF (all 0.45 beads) | **0.9 mm** | Your "1 is wiggly / tagline wiggly": does the longer straight stitch read straighter? Does a 3-pass stitch that long lie flat and hold? |
| **H** | 1895, THE | bean holds **ON** (today: counter 0.25, bay 0.2) | holds OFF | | Do the 8's two counters and the 9's stay open in 1 and shut in 2? Are the held letters visibly fatter? |
| **K** | EST, THE | ties OFF (today) | `small_letter_ties` **ON** | | A knot at the letter ends in 1 and not in 2? Does 2's lock hold after a rub? |
| **P** | 1895, THE | **3 passes** (today) | 2 passes | 1 pass | Thread laid on itself: does each extra pass make the line wider, or only higher? Holes torn by three hits 0.45 mm apart? Which reads best? |

SAMENOTE

## Not on this card, on purpose

- **Small-lettering skeleton, fold cuts:** cut, then dropped. On today's engine
  both arms came out the **same stitches** on the tagline (skeleton) and on
  FREMONT's M->O and final T (fold cuts) at 81 mm, so the cloth could not tell
  them apart.

- **Detail spokes / the star:** the star is white on a black host; one cone
  can't show it.
- **Forbid gap, overlap by angle:** seams between two colours; one cone can't
  show them.
- **Edge-cap bean pitch, line chaining:** other fixtures, and chaining needs two
  cones.

## What the file says (pystitch reading the DST back)

READBACK

## Where the pieces come from

`tools/fremont_triage.py` replays the Studio request for your Fremont job
(`testdata/photo/logo_hotel_fremont.webp`, **81 mm, Hat**, 6 colours) through
the service's own steps once per cut. A piece is every non-white run lying
wholly inside the word's box grown by 0.8 mm (`sewout_card_v3.cut_arm`).

CUTNOTES

Reproduce: `python -m tools.sewout_card_v4 --cut <name>` per cut, then
`python -m tools.sewout_card_v4`, from `digitizer/`. Test:
`digitizer/tests/test_sewout_card_v4.py`.
"""

SCORING = """# Readout sheet, sew-out card v4

`card_v4_40wt.dst`, 40 wt, needle 75/11, one dark cone, cap / twill. Read the
arms of a word together, at arm's length first, then close up. Y/N cells: write
Y or N.

Date: ________  Machine: ____________  Speed (spm): ______  Fabric / backing: ______________

## B: straight stretches (`bean_letter_straight_mm`), 1895 and EAT STAY PLAY

| Arm | Breaks | 1 reads straight (Y/N) | Tagline reads straight (Y/N) | Long stitches lie flat, no loops (Y/N) | Reads at arm's length (Y/N) | Note |
|---|---|---|---|---|---|---|
| 1 tooth: 0.7 (today) | ___ | _ | _ | _ | _ | |
| 2 teeth: OFF | ___ | _ | _ | _ | _ | |
| 3 teeth: 0.9 | ___ | _ | _ | _ | _ | |

## H: bean holds, 1895 and THE

| Arm | Breaks | 8 upper / lower counter open | 9 counter open | Letters visibly fatter | Reads 1895 / THE at arm's length | Note |
|---|---|---|---|---|---|---|
| 1 tooth: holds ON (today) | ___ | U:_ L:_ | _ | _ | 1:_ T:_ | |
| 2 teeth: holds OFF | ___ | U:_ L:_ | _ | _ | 1:_ T:_ | |

## K: spread ties (`small_letter_ties`), EST and THE

| Arm | Breaks | Knot visible at letter ends, EST / THE | Lock holds after a rub | Note |
|---|---|---|---|---|
| 1 tooth: ties OFF (today) | ___ | E:_ T:_ | _ | |
| 2 teeth: ties ON | ___ | E:_ T:_ | _ | |

## P: bean passes (`bean_letter_passes`), 1895 and THE

| Arm | Breaks | Line visibly wider than 1 pass (Y/N) | 8 / 9 counters open | Torn or enlarged holes (Y/N) | Reads at arm's length, 1895 / THE | Note |
|---|---|---|---|---|---|---|
| 1 tooth: 3 passes (today) | ___ | _ | 8:_ 9:_ | _ | 1:_ T:_ | |
| 2 teeth: 2 passes | ___ | _ | 8:_ 9:_ | _ | 1:_ T:_ | |
| 3 teeth: 1 pass | ___ | n/a | 8:_ 9:_ | _ | 1:_ T:_ | |

Best-looking arm overall: ______________________
"""


def cut_notes(cuts: Path) -> str:
    lines = ["| cut | overrides on today's request | whole design |", "|---|---|---|"]
    for name, overrides in CUTS.items():
        f = cuts / f"cut_{name}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        lines.append(f"| `{name}` | `{overrides or 'none: today'}` | {d['stitches_whole']:,} stitches, "
                     f"{d['trims_whole']} trims, {d['size_mm_whole'][0]} x {d['size_mm_whole'][1]} mm |")
    return "\n".join(lines) + "\n"


def write_docs(out: Path, rb: dict, cuts: Path) -> None:
    same = same_arms(rb)
    samenote = ("**Arms that are the same stitches** (the flag changes nothing on that word; "
                "if they differ on cloth, it is the cloth): " + "; ".join(same) + "."
                if same else "Every arm differs from its neighbours in the file.")
    text = (README.replace("READBACK", v3.readback_markdown(rb)).replace("CUTNOTES", cut_notes(cuts))
            .replace("SAMENOTE", samenote)
            .replace("SIZE_MM", f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}")
            .replace("STITCHES", f"{rb['stitches_file']:,}")
            .replace("TRIMS", f"{rb.get('trims_file', '?')}")
            .replace("MINUTES", f"{rb['stitches_file'] / 650:.0f}"))
    (out / "README.md").write_text(text, encoding="utf-8")
    (out / "scoring-sheet.md").write_text(SCORING, encoding="utf-8")


def generate(out: Path, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "CARD V4 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    v3.render(plan, out / f"{NAME}.png")
    panel(plan, card, out / f"{NAME}_blocks.png")
    rb = v2.readback(path, plan, WT, card)
    rb["pieces"] = extra["pieces"]
    rb["block_md5"] = block_digests(plan)
    rb["arm_md5"] = arm_digests(plan)
    rb["same_arms"] = same_arms(rb)
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items() if k not in
                          ("pieces", "pieces_mm", "stitches_by_piece", "block_md5", "arm_md5")}))
    (out / "readback.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    write_docs(out, rb, cuts)
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=list(CUTS) + list(DROPPED_CUTS), help="digitize Fremont with this cut's overrides and save its boxes")
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
