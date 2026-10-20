"""The lettering-arms swatch: counter hold (#952) and spread ties (#956) on Fremont's small letters (2026-10-14)

    # 1. cut Fremont's small words out of the Studio-request replay, once per
    #    cut (a digitize is minutes and gigabytes: ONE process at a time)
    python -m tools.sewout_card_lettering_arms --cut s81      --cuts DIR
    python -m tools.sewout_card_lettering_arms --cut s81_hold --cuts DIR
    python -m tools.sewout_card_lettering_arms --cut s81_ties --cuts DIR
    python -m tools.sewout_card_lettering_arms --cut s925      --cuts DIR
    python -m tools.sewout_card_lettering_arms --cut s925_ties --cuts DIR
    # 2. build the card (no Fremont digitize; reads the cuts)
    python -m tools.sewout_card_lettering_arms [--out ../docs/sewout/card-lettering-arms-2026-10-14]

Two flags that were built OFF and have never met cloth, each as arms sewn
side by side on ONE 4x4 in card (Kent holds card v3.2 unsewn; this is a
separate card, not a v3.3):

- A  `bean_letter_counter_hold_mm` (#952): OFF vs 0.25 mm. The 8 in "1895"
     sews both counters shut under the bean letters (0.33 / 0.28 of their
     area bare); held 0.25 mm off the counter the thread lies on the
     stroke's outer side (0.63 / 0.54 bare). Fremont's EST and 1895, 81 mm
     Hat.
- B  `small_letter_ties` (#956): OFF vs ON. The ordinary lock bounces four
     legs on one 0.45 mm station gap at both ends of every trimmed letter;
     the spread tie lays the lock along the letter. Fremont's small words
     at 81 mm and at 92.5 mm Hat.

`small_text_true_size` is ON in EVERY arm (an override here, not the default:
its flip, #955, is not merged). Nothing else differs between the arms of a
block. The blocks are cut from the replay of the Studio request exactly as
card v3's T and N are (`sewout_card_v3.cut_arm`) and placed with v3's pieces
(index strip, teeth, render, read-back). The #950 pass-count swatch is a
different card and is NOT re-cut here (`docs/sewout/card-passes-2026-10-14`).
The file goes through `digitizer_service.formats.write` (pystitch) and is read
back with pystitch, never the browser's DST codec. 40 wt, one colour. EVERY
NUMBER HERE IS A CANDIDATE UNTIL KENT SEWS IT (ROADMAP gate 1: this card IS
the sew-out). The default config is untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.stitches import StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402

REPO = hc.REPO
WT = v3.WT
NAME = "card_lettering_arms_40wt"
DEFAULT_OUT = REPO / "docs" / "sewout" / "card-lettering-arms-2026-10-14"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"

#: ON in every arm, by override; both holds pinned OFF so the cuts mean what
#: they did when the card was cut (2026-10-14; the holds are ON by default
#: since 2026-10-15), and block A's hold arm sets its own.
SWITCH = {"small_text_true_size": True,
          "bean_letter_counter_hold_mm": None, "bean_letter_bay_hold": None,
          "bean_letter_straight_mm": None}
HOLD_MM = 0.25                                # #952's candidate

#: cut -> (Studio width in mm, the replay's overrides). `s81` is the shared
#: base: block A's OFF arm AND block B's OFF arm at 81 mm.
CUTS = {
    "s81": (81.0, dict(SWITCH)),
    "s81_hold": (81.0, {**SWITCH, "bean_letter_counter_hold_mm": HOLD_MM}),
    "s81_ties": (81.0, {**SWITCH, "small_letter_ties": True}),
    "s925": (92.5, dict(SWITCH)),
    "s925_ties": (92.5, {**SWITCH, "small_letter_ties": True}),
}
#: word -> (fremont_triage.ROIS key, ()) -- every cut saves all four boxes
WORDS = {"EST": ("est", ()), "1895": ("1895", ()), "THE": ("the", ()), "TAG": ("tagline", ())}

#: block -> (index letter, size tag, [(arm label, cut), ...] in tooth order, words in row order)
BLOCKS = {
    "A": ("A", "81", [("off", "s81"), ("hold", "s81_hold")], ("EST", "1895")),
    "B1": ("B", "81", [("off", "s81"), ("ties", "s81_ties")], ("EST", "1895", "THE", "TAG")),
    "B2": ("B", "92.5", [("off", "s925"), ("ties", "s925_ties")], ("EST", "1895", "THE", "TAG")),
}


def cut(name: str, cuts: Path) -> Path:
    """Digitize Fremont at this cut's width on a Hat with its overrides and save
    the runs inside the four word boxes (`sewout_card_v3.cut_arm`)."""
    width, overrides = CUTS[name]
    v3.CUT_ARMS[name] = dict(overrides)
    return v3.cut_arm(name, cuts, width_mm=width, boxes=WORDS)


# --- the card ---------------------------------------------------------------------------

LETTERS = {**hc.LETTERS,
           "1": [(1.0, 1.0), (1.5, 0), (1.5, 4)],
           "2": [(0, 0), (3, 0), (3, 2), (0, 2), (0, 4), (3, 4)]}
#: the index strip's second glyph: which size row of block B this is
DIGIT = {"A": None, "B1": "1", "B2": "2"}


class CardArms(v3.CardV3):
    """Card v3's colour stop and digitized-piece rule, with this card's blocks."""

    DIGITIZED = ("A:", "B1:", "B2:")

    def index(self, key: str, x0: float, y0: float, width: float) -> None:
        letter = BLOCKS[key][0]
        self.add(0, hc.corners([(x0 + a, y0 + b) for a, b in LETTERS[letter]]), f"{key}:index")
        if DIGIT[key]:
            self.add(0, hc.corners([(x0 + 4.5 + a, y0 + b) for a, b in LETTERS[DIGIT[key]]]), f"{key}:index")
        self.add(0, hc.corners([(x0 + 9.0, y0 + 5.0), (x0 + width, y0 + 5.0)]), f"{key}:rule")


def word_runs(cuts: Path, cut_name: str, word: str) -> list[StitchRun]:
    b = v3.load_cut(cuts, cut_name, word)
    return [StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=True, trim=False,
                      shape_id=r["shape_id"]) for r in b["runs"]]


def block(c: CardArms, key: str, x0: float, y0: float, cuts: Path, report: list) -> float:
    """One block: the index strip, then a row per group of words, the arms of
    each word side by side (teeth = the arm's number). Returns the block's bottom y."""
    _letter, size, arms, words = BLOCKS[key]
    groups = [words[:3], words[3:]] if len(words) > 3 else [words]
    c.index(key, x0, y0, 30.0)
    top = y0 + 9.0
    right, bottom = x0, top
    for group in groups:
        x = x0
        row_bottom = top
        for word in group:
            for k, (label, cut_name) in enumerate(arms, start=1):
                arm = f"{word}-{label}"
                runs = word_runs(cuts, cut_name, word)
                box = v3.place_runs(c, runs, x, top, key, arm)
                c.add(0, hc.teeth(x, top - 0.8, k), f"{key}:label:{arm}")
                b = v3.load_cut(cuts, cut_name, word)
                report.append({"block": key, "arm": arm, "word": word, "label": label, "cut": cut_name,
                               "size_mm": float(size), "overrides": CUTS[cut_name][1], "roi": b["roi"],
                               "runs": len(runs), "crossing_runs_dropped": b["crossing_runs_dropped"],
                               "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
                x = max(box[2], x + 4.8) + 4.0          # room for the arm's own teeth
                row_bottom = max(row_bottom, box[3])
            x += 4.0
        right = max(right, x)
        bottom = row_bottom
        top = row_bottom + 6.5
    c.boxes[key] = (x0, y0, max(right, x0 + 30.0), bottom)
    return bottom


def build(cuts: Path) -> tuple[StitchPlan, CardArms, dict]:
    c = CardArms(WT)
    report: list[dict] = []
    y = block(c, "A", 0.0, 0.0, cuts, report)
    y = block(c, "B1", 0.0, y + 5.0, cuts, report)
    block(c, "B2", 0.0, y + 5.0, cuts, report)
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


def block_digests(plan: StitchPlan) -> dict[str, str]:
    """md5 of each block's stitch output (the digitized pieces, labels and
    index strip of block A / B1 / B2), points rounded to 0.001 mm: the test
    pins these, so a change to a cut, a placement or an arm shows up."""
    h: dict[str, "hashlib._Hash"] = {}
    for _b, r in plan.iter_runs():
        key = r.shape_id.split(":")[0]
        m = h.setdefault(key, hashlib.md5())
        m.update(r.shape_id.encode() + b"|" + (b"J" if r.jump else b"-") + (b"T" if r.trim else b"-"))
        m.update(np.round(np.asarray(r.points, float), 3).tobytes())
    return {k: v.hexdigest() for k, v in sorted(h.items())}


def arm_digests(plan: StitchPlan) -> dict[str, str]:
    """md5 per arm (`block:word-label`): the arm's own stitches, label excluded,
    taken from the arm's own top-left so WHERE it sits on the card does not
    count (block A's OFF arm and block B1's OFF arm are the same stitches)."""
    runs: dict[str, list] = {}
    for _b, r in plan.iter_runs():
        parts = r.shape_id.split(":")
        if len(parts) < 3 or parts[1] in ("label", "strips"):
            continue
        runs.setdefault(":".join(parts[:2]), []).append(np.asarray(r.points, float))
    out = {}
    for k, rs in sorted(runs.items()):
        x0 = min(a[:, 0].min() for a in rs)
        y0 = min(a[:, 1].min() for a in rs)
        m = hashlib.md5()
        for a in rs:
            # floor with a nudge: a translated copy must not flip a value sitting on a rounding edge
            m.update(np.floor((a - (x0, y0)) * 1000 + 0.5 + 1e-6).astype(np.int64).tobytes())
        out[k] = m.hexdigest()
    return out


# --- renders ----------------------------------------------------------------------------

def rows() -> tuple:
    out = []
    for key, (_letter, size, arms, words) in BLOCKS.items():
        what = "hold_mm" if key == "A" else "ties"
        names = " | ".join(f"{lbl} ({k})" for k, (lbl, _c) in enumerate(arms, start=1))
        # the title is clipped to the row's width, so a row holds several words
        for group in (words[:3], words[3:]) if len(words) > 3 else (words,):
            out.append((f"{key} {'/'.join(group)} at {size} mm, each word: {what} {names} teeth",
                        tuple(f"{key}:{w}-{lbl}" for w in group for lbl, _c in arms)))
    return tuple(out)


def panel(plan: StitchPlan, card: CardArms, out: Path, ppm: float = 60.0) -> None:
    saved = v3.ROWS
    v3.ROWS = rows()
    try:
        v3.panel(plan, card, out, ppm)
    finally:
        v3.ROWS = saved


# --- docs -----------------------------------------------------------------------------------

README = """# Sew-out card: lettering arms (2026-10-14)

A **separate** small card for two switches that were built OFF and have never
met cloth. It is not card v3.3: Kent's card v3.2
(`../card-v3-2026-10-13/`) is still unsewn and is not superseded; this one
asks only about the lettering of Fremont's hat. **Every number on it is a
candidate until you sew it** (ROADMAP gate 1: this card is the sew-out; no
value is settled, the default config is untouched).

**What to sew:** `card_lettering_arms_40wt.dst`, ONE colour (dark), **40 wt**,
a **4 x 4 in hoop** (the design is SIZE_MM mm, inside the 100 x 100 mm
sewable field), on a hat front like the Fremont job. STITCHES stitches: allow
roughly 8 minutes (an estimate from the stitch count, not a measurement).

## What is in this folder

| File | What it is |
|---|---|
| `card_lettering_arms_40wt.dst` | the card, 40 wt, written through the service's export path (pystitch), read back with pystitch. |
| `card_lettering_arms_40wt.png` | the whole card as a thread render, 12 px/mm. A picture of the file, not of cloth. |
| `card_lettering_arms_40wt_blocks.png` | every arm cropped at 60 px/mm, the arms of a word side by side, the key printed on each row. |
| `scoring-sheet.md` | the readout sheet: one row per arm. Print it. |
| `readback.json` | the file checks, quoted below. |
| `cuts/cut_*.json` | the Fremont runs each arm sews: the replay of the Studio request, cut to each word box (see below). |

Reproduce with `python -m tools.sewout_card_lettering_arms` from
`digitizer/` (the cuts are re-made with `--cut s81|s81_hold|s81_ties|s925|s925_ties`,
one process at a time, a few minutes each). The test is
`digitizer/tests/test_sewout_card_lettering_arms.py`.

## What you need

- **Fabric:** the cap (or a scrap of the same structured twill). Every piece is
  digitized on the **Hat profile** (0.4 mm pull), as your Fremont job was.
- **Stabilizer:** the backing you used for the Fremont hat; else tearaway
  (medium) under twill, no topping.
- **Thread:** one cone, a **dark** (black or navy), **40 wt**: Madeira
  Polyneon No. 40, or Isacord 40. The card sews only the logo's non-white
  thread, so there is no white patch and no second cone.
- **Needle:** 40 wt **75/11**. **Bobbin:** the same as the other cards.

## How to sew it

1. Load the DST. **Put the needle at the centre of the card** (the file's
   origin is the middle of the SIZE_MM mm box). Trace the outline.
2. Turn **trims on**: the file cuts between letters and between pieces.
3. **One colour.** No colour stop, no second cone.
4. Count **thread breaks** from the machine's counter, per block if you can.
5. Do not press or steam before scoring. Photograph each block close up (a
   macro) and once at arm's length. The words are 2-4 mm tall: read them under
   a loupe AND at arm's length, and score the two separately.

## How to read the arms

Every block has an **index strip** (its letter sewn as a run, 4 mm tall, with
a rule under it; block B's two size rows add a **1** or **2** beside the B).
The arms of each word are sewn side by side and labelled with **teeth** (a
square wave sewn above each), counted from the left: **1 tooth** is the first
arm named in the key below, **2 teeth** the second. The same key is printed on
every row of `card_lettering_arms_40wt_blocks.png`.

![](card_lettering_arms_40wt.png)

## Key and block map

`small_text_true_size` is **ON in every arm** (set as an override on the
replay, not the default: its flip, #955, is not merged). Within a block the
two arms differ **only** in the flag named; every other setting is today's
default.

| Block | Where | 1 tooth | 2 teeth | What it asks |
|---|---|---|---|---|
| **A** | top | `bean_letter_counter_hold_mm` OFF | `bean_letter_counter_hold_mm` **0.25** (#952) | **EST** and **1895** at **81 mm** Hat. The 8 in 1895 sews both counters shut under bean letters (the stroke is 0.22 mm of ink under a 0.40 mm thread); held 0.25 mm off the counter, the thread lies on the stroke's outer side. Does the 8 show two open counters, and the 9 and 5? Is the letter visibly fatter outward (up to ~0.1 mm)? |
| **B1** | middle | `small_letter_ties` OFF | `small_letter_ties` **ON** (#956) | **EST, 1895, THE** and the **EAT / STAY / PLAY** tagline at **81 mm** Hat. OFF locks each trimmed letter with the ordinary four-leg bounce on one 0.45 mm station gap (a knot of thread on a 0.2 mm stroke); ON lays the lock along the letter. Is a knot visible at the letter ends in 1 and not in 2? Does the ON lock hold (no pulled-out ends after a gentle rub)? |
| **B2** | bottom | `small_letter_ties` OFF | `small_letter_ties` **ON** (#956) | The same four words at **92.5 mm** Hat, the size the pro sews. |
| **C** | not on this card | | | **Bean passes 1 / 2 / 3** (#950): already cut as a separate card, `../card-passes-2026-10-14/` (THE and 1895, `bean_letter_passes` 1, 2, 3). It is **not** re-cut here; sew it too if you want that question answered. |

**What to look for**, per arm: counters open or shut (the 8's two, the 9's,
the 5's top opening); knots visible or not at the ends of letters; the
letter's width against the 0.40 mm thread; any shredded or enlarged needle
holes, puckering or thread breaks; and **legibility at arm's length**: does the
word read, and which arm reads best?

**Read the render with care.** `stitchviz` draws a three-pass bean letter as
**one** thread width, so the thread render under-draws the sewn weight of every
bean letter here: the arms will look alike, and thinner than they sew. The
cloth is the only judge. The render shows layout and stitch placement, not
bulk.

## What the files say about each arm (the FILE, not the cloth)

PAIRNOTES

## Where the Fremont pieces come from

The pieces are not drawn: they are the **stitches the engine sews for Kent's
job**. `tools/fremont_triage.py` replays the Studio request (the committed
`testdata/photo/logo_hotel_fremont.webp`, Hat profile, 6 colours) through the
service's own steps, once per cut below, and a piece is every non-white run
lying wholly inside the word's artwork box grown by 0.8 mm (the same cut as
card v3's T and N, `sewout_card_v3.cut_arm`):

CUTNOTES

Block A's OFF arm and block B1's OFF arm are the same cut (`s81`): the same
stitches, sewn twice.

## The file checks (pystitch reading the DST back)

READBACK
## Things to know before you sew

- **The pieces are small** (2-4 mm tall). "Looks the same at arm's length" is a
  finding, not a failure.
- **Some arms are the same stitches on purpose.** EST has no counter, so
  block A's EST arms are identical (EST is the control: if EST differs on the
  cloth, it is the cloth), and the 81 mm EST arms of block B1 are identical
  too (the ties flag changed no stitch of EST at 81 mm; it does at 92.5 mm).
- **The 1895 digits are TAN thread in the logo** (a mid-tone), sewn here in
  the dark cone for contrast: read shape, not colour.
- **Short stitches.** Bean letters sew at a 0.45 mm station pitch; the index
  strips and labels hold the 1.0 mm floor, and the engine's own lock legs are
  0.8 mm (the `small_letter_ties` arms lay shorter spread legs on purpose).
"""

SCORING = """# Readout sheet, sew-out card: lettering arms

One row per arm, for the one sew-out (`card_lettering_arms_40wt.dst`, 40 wt,
needle 75/11, one colour). **Thread breaks** come from the machine counter.
**Y/N** cells: write Y or N. Read the two arms of a word together (1 tooth
first), at arm's length first and then under a loupe, and score every arm the
same way. Bean passes are the other card, `../card-passes-2026-10-14/`.

Date: ________  Machine: ____________  Speed (spm): ______  Fabric / backing: ______________________
Thread: ______________________  Needle: 75/11  Fresh needle: Y/N

## A: counter hold (`bean_letter_counter_hold_mm`), EST and 1895 at 81 mm

| Arm | Thread breaks | 8: upper / lower counter open (Y/N) | 9 counter open (Y/N) | 5 top opening open (Y/N) | Letters visibly fatter (Y/N) | Reads 1895 at arm's length (Y/N) | Reads EST at arm's length (Y/N) | Free note |
|---|---|---|---|---|---|---|---|---|
| 1 tooth: hold OFF | ___ | U:_ L:_ | _ | _ | _ | _ | _ | |
| 2 teeth: hold 0.25 mm | ___ | U:_ L:_ | _ | _ | _ | _ | _ | |

## B1: spread ties (`small_letter_ties`) at 81 mm

| Arm | Thread breaks | Knot visible at letter ends, EST / 1895 / THE / tagline (Y/N each) | Lock holds after a gentle rub (Y/N) | Bump or pucker at ends (Y/N) | Reads at arm's length: EST / 1895 / THE / tagline (Y/N each) | Free note |
|---|---|---|---|---|---|---|
| 1 tooth: ties OFF | ___ | E:_ 1:_ T:_ G:_ | _ | _ | E:_ 1:_ T:_ G:_ | |
| 2 teeth: ties ON | ___ | E:_ 1:_ T:_ G:_ | _ | _ | E:_ 1:_ T:_ G:_ | |

## B2: spread ties (`small_letter_ties`) at 92.5 mm

| Arm | Thread breaks | Knot visible at letter ends, EST / 1895 / THE / tagline (Y/N each) | Lock holds after a gentle rub (Y/N) | Bump or pucker at ends (Y/N) | Reads at arm's length: EST / 1895 / THE / tagline (Y/N each) | Free note |
|---|---|---|---|---|---|---|
| 1 tooth: ties OFF | ___ | E:_ 1:_ T:_ G:_ | _ | _ | E:_ 1:_ T:_ G:_ | |
| 2 teeth: ties ON | ___ | E:_ 1:_ T:_ G:_ | _ | _ | E:_ 1:_ T:_ G:_ | |

Which arm reads best from arm's length, whole card: ______________________________

Candidate numbers under test; none of them is settled until this sheet is
filled in.

| Candidate | Value | What settles it |
|---|---|---|
| `bean_letter_counter_hold_mm` | 0.25 mm (0.2 is half the 40 wt laid width) | block A: the 8's two counters open in 2 teeth and shut in 1 tooth, with no fat-letter cost you mind |
| `small_letter_ties` | ON | blocks B1 / B2: no knot at the letter ends in 2 teeth, a lock that holds, at both sizes |
"""


def pair_notes(rb: dict) -> str:
    """Per-arm facts read off the file; the sewn effect is the sew-out's to say."""
    n = rb["stitches_by_piece"]
    lines = ["| block | word | arm 1 | arm 2 | stitches arm 1 | stitches arm 2 | difference |",
             "|---|---|---|---|---|---|---|"]
    for key, (_l, _size, arms, words) in BLOCKS.items():
        for word in words:
            a, b = (n[f"{key}:{word}-{lbl}"] for lbl, _c in arms)
            lines.append(f"| {key} | {word} | {arms[0][0]} | {arms[1][0]} | {a:,} | {b:,} | {b - a:+,} |")
    return "\n".join(lines) + "\n"


def cut_notes(cuts: Path) -> str:
    lines = ["", "| cut | width | overrides on the Studio request | whole design |", "|---|---|---|---|"]
    for name, (width, overrides) in CUTS.items():
        f = cuts / f"cut_{name}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        lines.append(f"| `{name}` | {width:g} mm | `{overrides}` | {d['stitches_whole']:,} stitches, "
                     f"{d['trims_whole']} trims, {d['size_mm_whole'][0]} x {d['size_mm_whole'][1]} mm |")
    return "\n".join(lines) + "\n"


def write_docs(out: Path, rb: dict, cuts: Path) -> None:
    text = (README.replace("READBACK", v3.readback_markdown(rb)).replace("PAIRNOTES", pair_notes(rb))
            .replace("CUTNOTES", cut_notes(cuts))
            .replace("SIZE_MM", f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}")
            .replace("STITCHES", f"{rb['stitches_file']:,}"))
    (out / "README.md").write_text(text, encoding="utf-8")
    (out / "scoring-sheet.md").write_text(SCORING, encoding="utf-8")


def generate(out: Path, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "LETTERARMS 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    v3.render(plan, out / f"{NAME}.png")
    panel(plan, card, out / f"{NAME}_blocks.png")
    rb = v2.readback(path, plan, WT, card)
    rb["pieces"] = extra["pieces"]
    rb["block_md5"] = block_digests(plan)
    rb["arm_md5"] = arm_digests(plan)
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items() if k not in
                          ("pieces", "pieces_mm", "stitches_by_piece", "block_md5", "arm_md5")}))
    (out / "readback.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    write_docs(out, rb, cuts)
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=list(CUTS), help="digitize Fremont with this cut's overrides and save its boxes")
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
