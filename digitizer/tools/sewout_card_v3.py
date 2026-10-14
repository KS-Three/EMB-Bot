"""The sew-out card, v3: Kent's Hotel Fremont 81 mm small-lettering questions on ONE card (2026-10-13).

    # 1. cut the Fremont boxes out of the Studio-request replay (a digitize is
    #    minutes and gigabytes: ONE process at a time, one arm per call)
    python -m tools.sewout_card_v3 --cut today    --cuts DIR
    python -m tools.sewout_card_v3 --cut wordtier --cuts DIR
    python -m tools.sewout_card_v3 --cut keep     --cuts DIR
    # 2. build the card (no Fremont digitize; reads the committed cuts)
    python -m tools.sewout_card_v3 [--out ../docs/sewout/card-v3-2026-10-13]

Card v1 (`tools/hairline_card.py`) holds the hairline blocks A-E and card v2
(`tools/sewout_candidates_card.py`) holds F small print, G forbid gap, H column
reach. Neither is touched. Card v3 settles the questions Kent's Hotel Fremont
81 mm Hat stitch-out left (PRs #898, #902, #905), each as arms sewn side by side
and labelled with teeth (a square wave, counted from the left):

- F3 SMALL CAP COUNTERS. A 2.2 mm cap "APA" (Fremont's tagline caps are
     2.17 mm; the A's counter there is 0.50 mm across at 81 mm) at 40 wt on the
     Hat profile, in three arms: 1 tooth today's default (`small_glyph_keep`
     OFF, `small_print_floor` OFF), 2 teeth `small_print_floor` ON, 3 teeth
     `small_glyph_keep` ON. (#905's recommendation 1.)
- T   Fremont's "THE" at 81 mm, cut from the replay of the Studio request:
     1 tooth today, 2 teeth `lettering_words` + `lettering_word_tiers` ON.
     The third arm (#905's pick, the skeleton run, `cfg.small_lettering_skeleton`)
     is left out: that branch has not merged. (#905's recommendation 2.)
- N   Fremont's "1895" box at 81 mm Hat: 1 tooth `small_glyph_keep` OFF,
     2 teeth ON (Kent's flip-ruling follow-up from #902).
- G   Card v2's block G, reused unchanged (`sewout_candidates_card.block_G`):
     `forbid_gap_mm` OFF / 0.4 / 0.8 on three bars standing off an 8 x 8 mm
     fill by 0.3 / 0.6 / 1.0 mm. Card v2 has not been sewn (MASTER_SCOPE
     "Waiting on Kent" 44, 47), so its block G is not settled; v3 carries it so
     one session settles it.

40 wt only (the Fremont job is 40 wt). Every piece goes through the pipeline at
the file's `thread_wt`, the Hat profile (`garment_id="hat_front"`, 0.4 mm
pull) for F3/T/N and the default profile for G (as on card v2), and every file
through `digitizer_service.formats.write` (pystitch), read back with pystitch;
never the browser's DST codec. EVERY NUMBER HERE IS A CANDIDATE UNTIL KENT SEWS
IT (ROADMAP gate 1). No engine change.

Colour stops (sew order), the same three as card v2: 1 dark (everything but
G's bars and edge caps, and G's fills), 2 light (G's bars), 3 dark (G's edge
caps). The Fremont cuts are the logo's non-white thread, sewn in the card's
dark cone.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pystitch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitchviz  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from digitizer_core.stitches import StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402

REPO = hc.REPO
HOOP_MM = hc.HOOP_MM
WT = 40
MAX_RECORD_MM = v2.MAX_RECORD_MM
NAME = "card_v3_40wt"
DEFAULT_OUT = REPO / "docs" / "sewout" / "card-v3-2026-10-13"
DEFAULT_RENDERS = REPO / "docs" / "renders" / "claude-sewout-card-v3"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"
STOP_ORDER, STOPS = v2.STOP_ORDER, v2.STOPS

# --- the Fremont cuts -----------------------------------------------------------------

#: Arms of the Fremont replay (the Studio request at 81 mm on a Hat plus these
#: overrides). `small_glyph_keep` is pinned OFF in every arm but its own, so the
#: card does not move if that default flips (it is OFF on origin/main as of
#: 2026-10-13; the flip branch `claude/small-glyph-keep-on` is not merged).
CUT_ARMS = {
    "today": {"small_glyph_keep": False},
    "wordtier": {"small_glyph_keep": False, "lettering_words": True, "lettering_word_tiers": True},
    "keep": {"small_glyph_keep": True},
}
#: box name -> (fremont_triage.ROIS key, the arms it is cut from, in tooth order)
CUT_BOXES = {
    "T": ("the", ("today", "wordtier")),
    "N": ("1895", ("today", "keep")),
}
CUT_MARGIN_MM = 0.8          # a run belongs to a box if its extent lies inside the box grown by this
WHITE_MIN = 215              # a block whose every channel is this high is the white patch (fremont_triage.WHITE_MIN)


def cut_arm(arm: str, cuts: Path, design_dir: Path | None = None) -> Path:
    """Digitize the Fremont fixture as the Studio does (81 mm, Hat) with this
    arm's flags, and save the runs of the non-white thread that lie inside the
    T ("THE") and N ("1895") boxes, as JSON. Returns the file."""
    import time
    from tools import fremont_triage as ft
    t = time.time()
    run = ft.run_arm("main", ft.KENT_WIDTH_MM, None, preflight=False, overrides=dict(CUT_ARMS[arm]))
    plan, p = run["plan"], run["gen"].p
    out = {"arm": arm, "overrides": CUT_ARMS[arm], "width_mm": ft.KENT_WIDTH_MM,
           "stitches_whole": plan.stats.stitch_count, "trims_whole": plan.stats.trims,
           "size_mm_whole": [round(v, 2) for v in plan.stats.size_mm], "boxes": {}}
    for key, (roi, _arms) in CUT_BOXES.items():
        x0, y0, x1, y1 = ft.roi_mm(p, ft.ROIS[roi])
        gx0, gy0, gx1, gy1 = x0 - CUT_MARGIN_MM, y0 - CUT_MARGIN_MM, x1 + CUT_MARGIN_MM, y1 + CUT_MARGIN_MM
        inside, crossing = [], []
        for b in plan.blocks:
            if min(b.rgb) >= WHITE_MIN:
                continue
            for r in b.runs:
                xs = [q[0] for q in r.points]
                ys = [q[1] for q in r.points]
                if min(xs) >= gx0 and max(xs) <= gx1 and min(ys) >= gy0 and max(ys) <= gy1:
                    inside.append({"kind": r.kind, "jump": bool(r.jump), "trim": bool(r.trim),
                                   "shape_id": r.shape_id, "rgb": [int(v) for v in b.rgb],
                                   "points": [[round(q[0], 4), round(q[1], 4)] for q in r.points]})
                elif (max(xs) >= gx0 and min(xs) <= gx1 and max(ys) >= gy0 and min(ys) <= gy1):
                    crossing.append({"kind": r.kind, "shape_id": r.shape_id, "n_points": len(r.points),
                                     "bbox_mm": [round(min(xs), 2), round(min(ys), 2),
                                                 round(max(xs), 2), round(max(ys), 2)]})
        out["boxes"][key] = {"roi": roi, "box_mm": [round(v, 3) for v in (x0, y0, x1, y1)],
                             "runs": inside, "crossing_runs_dropped": len(crossing),
                             "crossing_runs": crossing}
        print(f"{arm}/{key}: {len(inside)} runs, {sum(len(r['points']) for r in inside)} points, "
              f"{len(crossing)} crossing runs dropped: {crossing}", flush=True)
    if design_dir is not None:      # the whole design, for 	ools/glyph_legibility.py --design (not committed)
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / f"fremont_{arm}.json").write_text(json.dumps(run["design"]), encoding="utf-8")
    cuts.mkdir(parents=True, exist_ok=True)
    path = cuts / f"cut_{arm}.json"
    path.write_text(json.dumps(out), encoding="utf-8")
    print(f"{arm}: {plan.stats.stitch_count:,} stitches, {plan.stats.trims} trims, "
          f"{time.time() - t:.0f} s -> {path}", flush=True)
    return path


def load_cut(cuts: Path, arm: str, box: str) -> dict:
    return json.loads((cuts / f"cut_{arm}.json").read_text(encoding="utf-8"))["boxes"][box]


# --- the card -----------------------------------------------------------------------------

LETTERS = {**v2.LETTERS,
           "T": [(0, 0), (3, 0), (1.5, 0), (1.5, 4)],
           "N": [(0, 4), (0, 0), (3, 4), (3, 0)]}

# F3: the small-cap counters
F3_WORD = "APA"
F3_CAP_MM = 2.2
F3_STROKE_PER_CAP = 0.105          # Fremont's tagline: 0.23 mm stroke on a 2.17 mm cap
F3_ARMS = (("today", dict(small_print_floor=False, small_glyph_keep=False)),
           ("floor", dict(small_print_floor=True, small_glyph_keep=False)),
           ("keep", dict(small_print_floor=False, small_glyph_keep=True)))
GARMENT = "hat_front"              # the Hat profile, 0.4 mm pull: Kent's Fremont job

#: block -> arms in tooth order (1 tooth, 2 teeth, ...). The piece key is `block:arm`.
BLOCKS = {
    "F3": ("today", "floor", "keep"),
    "T": ("today", "wordtier"),
    "N": ("keep-off", "keep-on"),
    "G": ("gap-off", "gap-0.4", "gap-0.8"),
}
INDEX_STRIP = {"F3": "F", "T": "T", "N": "N", "G": "G"}


class CardV3(v2.CardV2):
    """Card v2's colour stops and digitized-piece rule, with v3's pieces."""

    DIGITIZED = ("F3:", "T:", "N:", "G:")

    def index(self, key: str, x0: float, y0: float, width: float) -> None:
        self.add(0, hc.corners([(x0 + a, y0 + b) for a, b in LETTERS[key]]), f"{key}:index")
        self.add(0, hc.corners([(x0 + 5.0, y0 + 5.0), (x0 + width, y0 + 5.0)]), f"{key}:rule")


def f3_image(word: str = F3_WORD):
    """The word as thin-stroke lettering with counters on a transparent
    background (as Fremont's artwork is), Hershey simplex, stroke about 0.105
    of the cap. Returns (BGRA image, ink w px, ink h px, stroke px)."""
    font, scale = cv2.FONT_HERSHEY_SIMPLEX, 6.0
    pad = 20
    best = None
    for thick in range(2, 40):      # the thickness whose stroke/ink-height is closest to the target
        (w, h), base = cv2.getTextSize(word, font, scale, thick)
        img = np.zeros((h + base + 2 * pad, w + 2 * pad, 4), np.uint8)
        cv2.putText(img, word, (pad, pad + h), font, scale, (20, 24, 40, 255), thick, cv2.LINE_AA)
        ys, xs = np.where(img[:, :, 3] > 127)
        ink_h = int(ys.max() - ys.min() + 1)
        err = abs(thick / ink_h - F3_STROKE_PER_CAP)
        if best is None or err < best[0]:
            best = (err, img, int(xs.max() - xs.min() + 1), ink_h, thick)
    return best[1], best[2], best[3], best[4]


def f3_counters(img: np.ndarray, mm_per_px: float) -> list[dict]:
    """The word's counters, left to right: area and inscribed width in mm."""
    ink = (img[:, :, 3] > 127).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(1 - ink)
    dt = cv2.distanceTransform(1 - ink, cv2.DIST_L2, 5)
    out = [(cen[i][0], {"area_mm2": round(float(st[i, 4]) * mm_per_px ** 2, 3),
                        "inscribed_width_mm": round(float(2 * dt[lab == i].max()) * mm_per_px, 2)})
           for i in range(1, n) if st[i, 4] < ink.size * 0.5]
    return [d for _x, d in sorted(out, key=lambda t: t[0])]


def place_runs(c: CardV3, runs: list[StitchRun], x0: float, y0: float, blk: str, arm: str,
               stop: int = 0) -> tuple[float, float, float, float]:
    """Put these runs' top-left at (x0, y0) in colour stop `stop`; the box they cover."""
    pts = [p for r in runs for p in r.points]
    bx0, by0 = min(p[0] for p in pts), min(p[1] for p in pts)
    dx, dy = x0 - bx0, y0 - by0
    for r in runs:
        c.add_run(stop, StitchRun(points=[(px + dx, py + dy) for px, py in r.points], kind=r.kind,
                                  jump=True, trim=False, shape_id=f"{blk}:{arm}:{r.kind}"))
    xs = [p[0] + dx for p in pts]
    ys = [p[1] + dy for p in pts]
    box = (min(xs), min(ys), max(xs), max(ys))
    c.arms[f"{blk}:{arm}"] = box
    return box


def block_F3(c: CardV3, x0: float, y0: float, report: list) -> None:
    img, ink_w, ink_h, stroke_px = f3_image()
    mm_per_px = F3_CAP_MM / ink_h
    c.index("F", x0, y0, 29.0)
    top = y0 + 9.0
    x = x0
    right = x0
    bottom = top
    for k, (arm, flags) in enumerate(F3_ARMS, start=1):
        cfg = PipelineConfig(target_width_mm=ink_w * mm_per_px, forced_class="flat", thread_wt=c.wt,
                             garment_id=GARMENT, **flags)
        _res, plan = digitize(img, cfg)
        runs = [r for _b, r in plan.iter_runs()]
        box = place_runs(c, runs, x, top, "F3", arm)
        c.add(0, hc.teeth(x, top - 0.8, k), f"F3:label:{arm}")
        report.append({"block": "F3", "arm": arm, "word": F3_WORD, "cap_mm": F3_CAP_MM,
                       "stroke_mm": round(stroke_px * mm_per_px, 3), "garment_id": GARMENT, **flags,
                       "counters": f3_counters(img, mm_per_px),
                       "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
        x = box[2] + 6.0
        right = max(right, box[2])
        bottom = max(bottom, box[3])
    c.boxes["F3"] = (x0, y0, max(right, x0 + 29.0), bottom)


def block_cut(c: CardV3, blk: str, x0: float, y0: float, width: float, cuts: Path, report: list) -> None:
    """Block T or N: the Fremont box's runs, one arm per cut file."""
    roi, cut_arms = CUT_BOXES[blk]
    c.index(INDEX_STRIP[blk], x0, y0, width)
    top = y0 + 9.0
    x = x0
    right = x0
    bottom = top
    for k, (arm, cut) in enumerate(zip(BLOCKS[blk], cut_arms), start=1):
        b = load_cut(cuts, cut, blk)
        runs = [StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=True, trim=False,
                          shape_id=r["shape_id"]) for r in b["runs"]]
        box = place_runs(c, runs, x, top, blk, arm)
        c.add(0, hc.teeth(x, top - 0.8, k), f"{blk}:label:{arm}")
        report.append({"block": blk, "arm": arm, "roi": roi, "cut": cut, "overrides": CUT_ARMS[cut],
                       "runs": len(runs), "garment_id": GARMENT,
                       "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
        x = box[2] + 5.0
        right = max(right, box[2])
        bottom = max(bottom, box[3])
    c.boxes[blk] = (x0, y0, max(right, x0 + width), bottom)


def build(cuts: Path) -> tuple[StitchPlan, CardV3, dict]:
    c = CardV3(WT)
    report: list[dict] = []
    block_F3(c, 0.0, 0.0, report)
    block_cut(c, "T", c.boxes["F3"][2] + 6.0, 0.0, 26.0, cuts, report)
    block_cut(c, "N", c.boxes["T"][2] + 6.0, 0.0, 20.0, cuts, report)
    row1 = max(c.boxes[k][3] for k in ("F3", "T", "N"))
    v2.block_G(c, 0.0, row1 + 5.0, report)
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


# --- renders ------------------------------------------------------------------------------------

def render(plan: StitchPlan, out: Path, ppm: float = 12.0) -> np.ndarray:
    design = plan_to_design(plan, name=f"card v3 {WT} wt")
    img = stitchviz.render_design(design, px_per_mm=ppm, thread_mm=machine.thread_profile(WT).width_mm)
    cv2.imwrite(str(out), img)
    return img


ROWS = (
    ("F3 small cap, 2.2 mm APA: today | small_print_floor | small_glyph_keep (1 / 2 / 3 teeth)",
     ("F3:today", "F3:floor", "F3:keep")),
    ("T THE at 81 mm: today | lettering_words + lettering_word_tiers (1 / 2 teeth)",
     ("T:today", "T:wordtier")),
    ("N 1895 at 81 mm: small_glyph_keep OFF | ON (1 / 2 teeth)", ("N:keep-off", "N:keep-on")),
    ("G forbid gap: OFF | 0.4 | 0.8 (bars at 0.3 / 0.6 / 1.0 mm; 1 / 2 / 3 teeth)",
     ("G:gap-off", "G:gap-0.4", "G:gap-0.8")),
)


def panel(plan: StitchPlan, card: CardV3, out: Path, ppm: float = 60.0) -> None:
    """One sheet: every arm cropped from the card at `ppm` px/mm (thread at the
    laid width), the arms of a block side by side."""
    design = plan_to_design(plan, name=f"card v3 {WT} wt")
    img = stitchviz.render_design(design, px_per_mm=ppm, pad_mm=2.0,
                                  thread_mm=machine.thread_profile(WT).width_mm)
    (_h, _w), to_px = stitchviz._frame(design["stitches"], ppm, 2.0)
    u = stitchviz.UNITS_PER_MM

    def crop(box, pad=0.3):
        a = to_px({"x": (box[0] - pad) * u, "y": -(box[1] - pad) * u})
        b = to_px({"x": (box[2] + pad) * u, "y": -(box[3] + pad) * u})
        xa, xb = sorted((a[0], b[0]))
        ya, yb = sorted((a[1], b[1]))
        return img[max(0, ya):yb, max(0, xa):xb].copy()

    rows = [v2._label(v2._hstack([crop(card.arms[k]) for k in keys]), title) for title, keys in ROWS]
    w = max(r.shape[1] for r in rows)
    rows = [np.hstack([r, np.full((r.shape[0], w - r.shape[1], 3), 255, np.uint8)]) for r in rows]
    cv2.imwrite(str(out), np.vstack([np.vstack([r, np.full((16, w, 3), 255, np.uint8)]) for r in rows]))


# --- the file checks --------------------------------------------------------------------------------

def readback(path: Path, plan: StitchPlan, card: CardV3) -> dict:
    """Read the DST back with pystitch and measure it (card v2's read-back)."""
    return v2.readback(path, plan, WT, card)


def readback_markdown(rb: dict) -> str:
    rows = [
        ("file", f"`{rb['file']}` ({rb['bytes']:,} bytes)"),
        ("blocks on the card", rb["blocks"]),
        ("stitches in the file / in the plan", f"{rb['stitches_file']:,} / {rb['stitches_plan']:,}"),
        ("colour changes in the file / planned", f"{rb['colour_changes_file']} / {rb['colour_changes_plan']}"),
        ("colours (stops)", rb["colours"]),
        ("extent (mm), x by y", f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}"),
        ("x range / y range (mm)", f"{rb['x_range_mm']} / {rb['y_range_mm']}"),
        ("inside 100 x 100 mm", "yes" if rb["within_hoop"] else "NO"),
        ("longest needle stitch (mm)", rb["max_needle_stitch_mm"]),
        (f"longest record, per axis (mm; the format's limit is {MAX_RECORD_MM})", rb["max_record_axis_mm"]),
        ("trims", rb["trims"]),
        ("0.8 mm lock-leg stitches", rb["lock_legs_0p8"]),
    ]
    out = ["| | 40 wt |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows]
    out += ["", "Stitches per piece:", "", "| piece | stitches |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in sorted(rb["stitches_by_piece"].items())]
    out += ["", "Stitches per colour stop:", "", "| stop | thread | stitches (thread m) |", "|---|---|---|"]
    out += [f"| {s['stop']} | {s['thread']} | {s['stitches']:,} ({s['thread_m']}) |" for s in rb["stops"]]
    out += ["", "Where each piece sits (mm, x0 y0 x1 y1, centre of the card at 0, 0):", "",
            "| piece | box |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in sorted(rb["pieces_mm"].items())]
    return "\n".join(out) + "\n"


def pair_notes(rb: dict) -> str:
    """Per-arm facts read off the file; the sewn effect is the sew-out's to say."""
    n = rb["stitches_by_piece"]
    lines = ["| piece | arm | stitches | vs arm 1 |", "|---|---|---|---|"]
    for blk, arms in BLOCKS.items():
        base = n[f"{blk}:{arms[0]}"]
        for arm in arms:
            v = n[f"{blk}:{arm}"]
            lines.append(f"| {blk} | {arm} | {v:,} | {'-' if arm == arms[0] else f'{v - base:+,}'} |")
    f3 = next(p for p in rb["pieces"] if p["block"] == "F3")
    cs = ", ".join(f"{w} {c['inscribed_width_mm']} mm ({c['area_mm2']} mm^2)"
                   for w, c in zip("APA", f3["counters"]))
    return ("\n".join(lines) + f"\n\nF3's counters as drawn (inscribed width, left to right: {cs}); the stroke is "
            f"{f3['stroke_mm']} mm on a {f3['cap_mm']} mm cap. A counter has to be at least one laid thread "
            f"({machine.thread_profile(WT).width_mm} mm at 40 wt) across for `small_print_floor` to keep it.\n")


# --- docs ---------------------------------------------------------------------------------------------

README = """# Sew-out card v3, 2026-10-13

One DST file (**40 wt**) for the questions Kent's Hotel Fremont 81 mm Hat
report left open. Each question is a block of arms sewn **side by side** and
labelled with teeth. You sew it once, read each block on `scoring-sheet.md`,
and that settles several ROADMAP gate-1 questions together. **Every number on
this card is a candidate until you sew it.** Nothing here is a setting.

It does not replace card v1 (`../hairline-card-2026-10-12/`, hairline blocks
A-E) or card v2 (`../card-v2-2026-10-13/`, blocks F small print, G forbid gap,
H column reach). Both are untouched and **neither has been sewn** (MASTER_SCOPE
"Waiting on Kent" 44, 45, 47). Card v3 carries v2's block G unchanged, so the
forbid-gap question is settled by whichever you sew; v2's F and H, and v1, are
still theirs. SIZE_MM mm, STITCHES stitches: allow roughly 5 minutes (an estimate from the
stitch count, not a measurement).

## What is in this folder

| File | What it is |
|---|---|
| `card_v3_40wt.dst` | the card, **40 wt** thread. |
| `card_v3_40wt.png` | what the file looks like, thread drawn at the laid width, 12 px/mm. A picture of the file, not of cloth. |
| `card_v3_40wt_blocks.png` | every arm cropped at 60 px/mm, the arms of a block side by side, for comparing them before you sew. |
| `scoring-sheet.md` | the readout sheet: one table per block. Print it. |
| `cuts/cut_*.json` | the Fremont runs the T and N blocks sew: the replay of the Studio request, cut to each box (see below). |
| `readback.md`, `readback.json` | the file checks, also quoted below. |

The file is written by `python -m tools.sewout_card_v3` (in `digitizer/`)
through the service's export path (pystitch), not the browser's DST codec,
and read back with pystitch. The test is `digitizer/tests/test_sewout_card_v3.py`.

## What you need

- **Fabric:** the **cap** (or a scrap of the same structured twill) is the
  honest test: F3, T and N are digitized on the **Hat profile** (0.4 mm pull
  per side), as your Fremont job was. A pique polo would sew them with a pull
  the cloth does not want. Block G is the default profile, as on card v2.
- **Stabilizer:** the backing you used for the Fremont hat; else tearaway
  (medium) under twill, no topping.
- **Thread, two cones:** a **dark** (black or navy) and a **light** (white or
  cream), the same maker and weight. 40 wt: **Madeira Polyneon No. 40**, or
  Isacord 40. The Fremont blocks sew in the **dark** cone (the card sews only
  the logo's non-white thread: there is no white patch under THE or 1895).
- **Needle:** 40 wt **75/11**. **Bobbin:** the same for every sew-out.
- The design is SIZE_MM mm, well inside a 100 x 100 mm field (a 4 x 4 in hoop).

## How to sew it

1. Load `card_v3_40wt.dst`. **Put the needle at the centre of the card**: the
   file's origin is the middle of the SIZE_MM mm box. Trace the outline.
2. Turn **trims on**. The file cuts between pieces and wherever the
   digitizer cut inside one.
3. **Three colour stops** (two cones; the machine asks for the dark one twice):
   1. **Stop 1, dark.** The four index strips, every label, blocks F3, T and
      N, and the **fill** of each block G arm.
   2. **Stop 2, light.** Block G's **bars**.
   3. **Stop 3, dark.** Block G's two edge runs round each fill (short).
4. Count **thread breaks** from the machine's counter, per block if you can.
5. Do not press or steam before scoring. Photograph each block close up (a
   macro) and once at arm's length; the F3, T and N pieces are 2-10 mm.

## How to read the arms

Every block has an **index strip**: its letter sewn as a run, 4 mm tall (F for
F3, T, N, G), with a rule 1 mm under it. Arms are labelled by **teeth** (a
square wave sewn above each), counted from the left: **1 tooth** is the first
arm named in the table below, **2 teeth** the second, **3 teeth** the third.

![](card_v3_40wt.png)

## Block map

| Block | Where | Arms (1 / 2 / 3 teeth) | What it settles |
|---|---|---|---|
| **F3** | top row, left | The word **APA**, **2.2 mm cap**, stroke about 0.23 mm, counters as measured under "What the files say" (Fremont's tagline: 2.17 mm caps, 0.23 mm strokes, A counters about 0.50 mm across). **1** today (`small_print_floor` OFF, `small_glyph_keep` OFF), **2** `small_print_floor` ON, **3** `small_glyph_keep` ON. | #905's recommendation 1: does `small_print_floor` keep an A's triangle open at the size of Fremont's tagline, which the 81 mm replay said it shuts? And does `small_glyph_keep`? Success = the triangle is a visible bare hole under a loupe in an arm and not in 1. |
| **T** | top row, middle | Fremont's **THE** at 81 mm (box about @WTHE@ x @HTHE@ mm), cut from the replay. **1** today (T a run outline, H and E Column-lane satin, sewn 2.1-2.4 x their 0.40 mm drawn stroke: the blob); **2** `lettering_words` + `lettering_word_tiers` (three run outlines of one weight). The skeleton-run arm (`cfg.small_lettering_skeleton`) is **not on the card**: that branch has not merged. | #905's recommendation 2: does the one-tier-per-word pair read as THE where today's is a blob? The flip is not ripe until this is sewn (or a legibility score shows it). |
| **N** | top row, right | Fremont's **1895** box at 81 mm (about @WN@ x @HN@ mm), cut from the replay. **1** `small_glyph_keep` OFF (the 1 is not sewn at all, so the box reads "098"; the 8 and 9 sew as solid outlines), **2** ON (the 1 is sewn; the 8 and 9 keep counters). | Kent's flip-ruling follow-up from #902: does ON read 1895 where OFF reads "098"? |
| **G** | second row | Card v2's **block G**, unchanged: an 8 x 8 mm tatami **fill** with three 2.5 mm satin **bars** standing off it by **0.3 mm** (left), **0.6 mm** (right) and **1.0 mm** (bottom). **1** OFF, **2** `forbid_gap_mm` **0.4**, **3** **0.8** (#874, WoK 44). | `forbid_gap_mm`: 0.4 (closes the 0.3 gap only), 0.8 (closes 0.3 and 0.6), or neither. The 1.0 bar is the control. |

## What the files say about each arm (the FILE, not the cloth)

PAIRNOTES

## Where the Fremont pieces come from

The T and N pieces are not drawn: they are the **stitches the engine sews for
Kent's job**. `tools/fremont_triage.py` replays the Studio request (81 mm, Hat,
6 colours, bean edge cap, the committed `testdata/photo/logo_hotel_fremont.webp`)
through the service's own steps. The arms differ only by the flags in the
table. Each box is the artwork rectangle `fremont_triage.ROIS` names, grown by
0.8 mm, and a piece is every non-white run lying wholly inside it:
CUTNOTES

`small_glyph_keep` is OFF on `origin/main` as of 2026-10-13 (a flip branch,
`claude/small-glyph-keep-on`, is not merged), and the card pins it explicitly in
every arm, so it does not move if that default flips.

## A legibility screen, read before you sew (not a verdict)

`tools/glyph_legibility.py` (#906) reads the sewn thread of each Fremont word
glyph by glyph against the artwork, on the whole 81 mm design of each arm
(the replay above; thread render, no pull, no nap). `legib` is the weakest of
strokes / clean / counters; `+space` adds the negative-space read. Its own
caveats apply (#906, "What it can and cannot say"): the pro's own legible THE
scores 0.04-0.08 on `+space`, and an outline run laid round a bold letter
leaves a hollow the artwork does not have, which the counters read bills as a
spurious hole. So it is a screen for where to look, and these two flips are
for the cloth to decide.

| box | arm | legib | +space | counters | worst glyph | OCR recovered |
|---|---|---|---|---|---|---|
| THE | today | 0.982 | 0.186 | 1.00 | 0.97 | 1/3 |
| THE | `lettering_words` + `lettering_word_tiers` | 0.333 | 0.186 | 0.33 | 0.00 | 1/3 |
| 1895 | `small_glyph_keep` OFF | 0.846 | 0.291 | 0.88 | 0.50 | 1/4 |
| 1895 | `small_glyph_keep` ON | 0.551 | 0.062 | 0.63 | 0.00 | 1/4 |

By this screen neither candidate improves its box: the one-tier-per-word THE
loses on counters (three outlines read as holes), and `small_glyph_keep` on
1895 sews the missing 1 (strokes 0.96 to 1.00) but in two pieces and with
extra holes (worst glyph 0.00). F3 (a synthetic word) and G (no artwork glyphs)
have no source boxes and are not scored. Whether THE or 1895 READS is the
question block T and block N put to the cloth.

## The file checks (pystitch reading the DST back)

READBACK
Reproduce with `python -m tools.sewout_card_v3` from `digitizer/` (the cuts
are re-made with `--cut today|wordtier|keep`, one process at a time, a few
minutes each).

## Things to know before you sew

- **F3, T and N are small.** The pieces are 2-10 mm; read them under a loupe
  AND at arm's length, and score the two separately. "Looks the same at arm's
  length" is a finding.
- **The 1895 digits are TAN thread in the logo** (rgb 163,150,135, a mid-tone), sewn here in the dark cone for contrast: read shape, not colour. THE is black in the logo.
- **The cloth is not the logo's ground.** The Fremont logo's white patch is not
  on the card, so THE and 1895 sew straight onto the cap or twill.
- **Short stitches.** The digitizer sews some stitches under 1.0 mm in lettering
  as it does today. The index strips and labels hold the 1.0 mm floor, and the
  lock legs are the engine's 0.8 mm.
"""

SCORING = """# Readout sheet, sew-out card v3

One table per block, one row per arm, for the one sew-out
(`card_v3_40wt.dst`, 40 wt, needle 75/11). **Thread breaks** come from the
machine counter. **Y/N** cells: write Y or N. Read the arms of a block together
(1 tooth first), at arm's length first and then under a loupe, and score every
arm the same way.

Date: ________  Machine: ____________  Speed (spm): ______  Fabric / backing: ______________________
Thread (dark / light): ______________________  Needle: 75/11  Fresh needle: Y/N

## F3: 2.2 mm cap APA (does the counter stay open?)

| Arm | Thread breaks | Counter open (Y/N): A1 / P / A2 | Bare line along a counter (Y/N) | Reads APA at arm's length (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: today | ___ | A1:_ P:_ A2:_ | _ | _ | |
| 2 teeth: `small_print_floor` ON | ___ | A1:_ P:_ A2:_ | _ | _ | |
| 3 teeth: `small_glyph_keep` ON | ___ | A1:_ P:_ A2:_ | _ | _ | |

## T: Fremont THE at 81 mm (is it a blob?)

| Arm | Thread breaks | Reads THE at arm's length (Y/N) | Letters distinct, T H E (Y/N each) | Blob: strokes fused or fat (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: today | ___ | _ | T:_ H:_ E:_ | _ | |
| 2 teeth: `lettering_words` + `lettering_word_tiers` | ___ | _ | T:_ H:_ E:_ | _ | |

## N: Fremont 1895 at 81 mm (does it read 1895?)

| Arm | Thread breaks | Reads 1895 at arm's length (Y/N) | Each digit reads (Y/N): 1 / 8 / 9 / 5 | 8 and 9 counters open (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: `small_glyph_keep` OFF | ___ | _ | 1:_ 8:_ 9:_ 5:_ | 8:_ 9:_ | |
| 2 teeth: `small_glyph_keep` ON | ___ | _ | 1:_ 8:_ 9:_ 5:_ | 8:_ 9:_ | |

## G: forbid gap (card v2's block G)

| Arm | Thread breaks | Fabric visible in the seam (Y/N), per gap | Seam ridge or pucker (Y/N) | Free note |
|---|---|---|---|---|
| 1 tooth: OFF | ___ | 0.3:_ 0.6:_ 1.0:_ | _ | |
| 2 teeth: `forbid_gap_mm` 0.4 | ___ | 0.3:_ 0.6:_ 1.0:_ | _ | |
| 3 teeth: `forbid_gap_mm` 0.8 | ___ | 0.3:_ 0.6:_ 1.0:_ | _ | |

Arm's length read of the whole card: ______________________________________

Candidate numbers under test; none of them is settled until this sheet is
filled in.

| Candidate | Value | What settles it |
|---|---|---|
| `small_print_floor` at 2.2 mm cap | ON keeps an A's triangle open | block F3: counter open in arm 2 and not in arm 1 |
| counter minimum / hold-off | 1.0 laid width (0.40 mm at 40 wt), half-width hold-off (0.20 mm) | block F3: arm 2's A counters (about 0.5 mm) open with no bare line |
| `small_glyph_keep` flip | ON | blocks F3 (arm 3) and N: counters open and digits read |
| `lettering_words` + `lettering_word_tiers` flip | ON | block T: THE reads in arm 2 and not in arm 1 |
| `forbid_gap_mm` | 0.4 or 0.8 (or none) | block G: which arm shows no fabric in the 0.3 / 0.6 mm seams, with no ridge |
"""


def cut_notes(cuts: Path) -> str:
    lines = ["", "| arm (cut) | flags on the Studio request | whole design | THE box mm | 1895 box mm |",
             "|---|---|---|---|---|"]
    for arm, flags in CUT_ARMS.items():
        f = cuts / f"cut_{arm}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        lines.append(f"| `{arm}` | `{flags}` | {d['stitches_whole']:,} stitches, {d['trims_whole']} trims, "
                     f"{d['size_mm_whole'][0]} x {d['size_mm_whole'][1]} mm | "
                     f"{d['boxes']['T']['box_mm']} ({len(d['boxes']['T']['runs'])} runs) | "
                     f"{d['boxes']['N']['box_mm']} ({len(d['boxes']['N']['runs'])} runs) |")
    return "\n".join(lines) + "\n"


def write_docs(out: Path, rb: dict, cuts: Path) -> None:
    size = f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}"
    pieces = rb["pieces_mm"]

    def wh(key):
        b = pieces[key]
        return round(b[2] - b[0], 1), round(b[3] - b[1], 1)
    text = (README.replace("READBACK", readback_markdown(rb)).replace("PAIRNOTES", pair_notes(rb))
            .replace("CUTNOTES", cut_notes(cuts)).replace("SIZE_MM", size)
            .replace("STITCHES", f"{rb['stitches_file']:,}")
            .replace("@WTHE@", str(wh("T:today")[0])).replace("@HTHE@", str(wh("T:today")[1]))
            .replace("@WN@", str(wh("N:keep-off")[0])).replace("@HN@", str(wh("N:keep-off")[1])))
    (out / "README.md").write_text(text, encoding="utf-8")
    (out / "scoring-sheet.md").write_text(SCORING, encoding="utf-8")


def generate(out: Path, renders: Path | None = None, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    """Write the whole card into `out` (and the PNGs into `renders`, if given)
    from the cuts in `cuts` (default: `<out>/cuts`); returns the read-back."""
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "CARDV3 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    render(plan, out / f"{NAME}.png")
    panel(plan, card, out / f"{NAME}_blocks.png")
    rb = readback(path, plan, card)
    rb["pieces"] = extra["pieces"]
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items() if k not in ("pieces", "pieces_mm", "stitches_by_piece")}))
    (out / "readback.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    (out / "readback.md").write_text(readback_markdown(rb), encoding="utf-8")
    write_docs(out, rb, cuts)
    if renders is not None:
        renders.mkdir(parents=True, exist_ok=True)
        for f in out.glob("*.png"):
            (renders / f.name).write_bytes(f.read_bytes())
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=list(CUT_ARMS), help="digitize the Fremont fixture with this arm and save its cuts")
    ap.add_argument("--cuts", default=str(DEFAULT_CUTS))
    ap.add_argument("--design-dir", help="with --cut: also save the whole Fremont design here (for glyph_legibility)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--renders", default=str(DEFAULT_RENDERS), help="copy the PNGs here too ('' to skip)")
    args = ap.parse_args(argv)
    if args.cut:
        cut_arm(args.cut, Path(args.cuts), Path(args.design_dir) if args.design_dir else None)
        return 0
    generate(Path(args.out), Path(args.renders) if args.renders else None, Path(args.cuts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
