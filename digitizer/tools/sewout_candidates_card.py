"""The sew-out card, v2: every open stitch candidate on ONE card (2026-10-13).

    python -m tools.sewout_candidates_card [--out ../docs/sewout/card-v2-2026-10-13]

(Not the customer's calibration card, `digitizer_core.calibration.card_v2` /
`tools/sewout_card_v2.py`: that one is a different thing.)

Card v1 (`tools/hairline_card.py`, `docs/sewout/hairline-card-2026-10-12/`)
holds the hairline blocks A-E and is NOT touched. This card carries the
candidates that landed after it, each as an OFF vs ON pair sewn side by side
and labelled, so one sew-out session settles several ROADMAP gate-1 questions:

- F  SMALL PRINT COUNTERS (`cfg.small_print_floor`, #873). The word BOARD
     (counters in B, O, A, R, D) at 4 mm and 3 mm cap, each OFF then ON. The
     candidate it settles: `machine.SMALL_PRINT_COUNTER_MIN_WIDTHS` = 1.0 laid
     thread widths (0.40 mm at 40 wt, ~0.32 mm at 60 wt) and the half-width
     hold-off of a column's thread from a counter.
- G  FORBID GAP (`cfg.forbid_gap_mm`, #874, WoK 44). A two-colour piece: an
     8 x 8 mm tatami fill with three 2.5 mm satin bars standing off it by 0.3,
     0.6 and 1.0 mm of bare fabric. Three arms: OFF, 0.4 and 0.8. The
     candidate it settles: which `forbid_gap_mm`, if any (0.4 and 0.8 are
     candidates, never a ruling). The 1.0 mm bar is the control no value here
     closes.
- H  COLUMN REACH (#863's sew-out item). A serif word (Roman AGS, OFL) at
     9 mm cap, `cfg.lettering_columns` OFF then ON: the Column lane's
     letters stand 0.06-0.07 mm inside the skeleton tier's reach, which is
     unsewn. Is that visible, and which edge reads closer to the drawn one?

Digitized pieces go through `digitizer_core.pipeline.digitize` at the file's
`thread_wt`, 1:1 (the ink's bounding box is sewn at the size the label says),
and every file through `digitizer_service.formats.write` (pystitch), read back
with pystitch; never the browser's DST codec. EVERY NUMBER HERE IS A CANDIDATE
UNTIL KENT SEWS IT (ROADMAP gate 1). No engine change: every arm is a
`PipelineConfig` field, and the shipped defaults are the engine as it is.

Colour stops (sew order). Each G arm is the digitizer's own sequence (the
fill, the three satin bars, then the fill's two edge-cap runs); arms are
interleaved by phase so each arm keeps its order, which is why the card has
three stops (dark, light, dark), not two:

    1 dark   everything else (index strips, labels, F, H) + each arm's fill
    2 light  each arm's three bars          3 dark  each arm's edge-cap runs
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
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitchviz  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.pipeline import digitize, fabric_for  # noqa: E402
from digitizer_core.stitches import StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402

REPO = hc.REPO
HOOP_MM = hc.HOOP_MM
WEIGHTS = hc.WEIGHTS
SERIF = REPO / "src" / "fonts" / "roman_ags.json"
MAX_RECORD_MM = 12.1        # the DST record's per-axis limit (the writer splits above it)

# The three stops, in sew order: dark, light, dark.
DARK_RGB, LIGHT_RGB = hc.STOPS[hc.DARK][1], hc.STOPS[hc.LIGHT][1]
STOPS = {
    0: ("dark", DARK_RGB, "dark: black or navy"),
    1: ("light", LIGHT_RGB, "light: white or cream"),
    2: ("dark", DARK_RGB, "dark: the same cone again"),
}
STOP_ORDER = (0, 1, 2)

# --- block F: small print ---------------------------------------------------------
F_WORD = "BOARD"
F_CAPS = (4.0, 3.0)
F_STATES = (("off", False), ("on", True))

# --- block G: forbid gap ----------------------------------------------------------
G_PPM = 40                       # artwork pixels per mm (1:1)
G_FILL_MM = 8.0
G_BAR_MM = 2.5
G_GAPS_MM = (0.3, 0.6, 1.0)      # left bar, right bar, bottom bar: bare fabric drawn into the art
G_ARMS = ((None, "off"), (0.4, "0.4"), (0.8, "0.8"))

# --- block H: column reach --------------------------------------------------------
H_WORD = "ROSE"
H_CAP = 9.0
H_STATES = (("off", False), ("on", True))

LETTERS = {      # 4 mm tall, 3 mm wide, origin top-left, y down; vertices are needle points
    "F": [(3, 0), (0, 0), (0, 2), (2.5, 2), (0, 2), (0, 4)],
    "G": [(3, 0), (0, 0), (0, 4), (3, 4), (3, 2), (1.5, 2)],
    "H": [(0, 0), (0, 4), (0, 2), (3, 2), (3, 0), (3, 4)],
}


class CardV2(hc.Card):
    """Runs by colour stop; the digitizer's own pieces keep its jump/cut calls."""

    DIGITIZED = ("F:", "G:", "H:")

    def __init__(self, wt: int):
        super().__init__(wt)
        self.arms: dict[str, tuple[float, float, float, float]] = {}

    def index(self, key: str, x0: float, y0: float, width: float) -> None:
        self.add(0, hc.corners([(x0 + a, y0 + b) for a, b in LETTERS[key]]), f"{key}:index")
        self.add(0, hc.corners([(x0 + 5.0, y0 + 5.0), (x0 + width, y0 + 5.0)]), f"{key}:rule")

    def plan(self, stops=STOP_ORDER, table=STOPS) -> StitchPlan:
        return super().plan(stops=stops, table=table)


# --- placing a digitized piece -----------------------------------------------------

def _phases(plan: StitchPlan) -> list[list[StitchRun]]:
    """The plan's runs grouped into consecutive same-colour stretches, in order."""
    groups: list[list[StitchRun]] = []
    last = None
    for b in plan.blocks:
        if last is not None and b.rgb == last:
            groups[-1].extend(b.runs)
        else:
            groups.append(list(b.runs))
        last = b.rgb
    return groups


def place(c: CardV2, plan: StitchPlan, x0: float, y0: float, blk: str, arm: str,
          *, first_stop: int = 0, stretches: int = 1) -> tuple[float, float, float, float]:
    """Put a digitized piece's top-left at (x0, y0). Its colour stretches take
    stops first_stop, first_stop + 1, ... `stretches` is how many it must
    have (a one-colour word: 1; a G arm: at most 4). Returns the box it covers."""
    groups = _phases(plan)
    assert 1 <= len(groups) <= stretches, f"{blk}:{arm}: {len(groups)} colour stretches, wanted <= {stretches}"
    pts = [p for g in groups for r in g for p in r.points]
    bx0, by0 = min(p[0] for p in pts), min(p[1] for p in pts)
    dx, dy = x0 - bx0, y0 - by0
    for i, g in enumerate(groups):
        assert first_stop + i < len(STOP_ORDER), f"{blk}:{arm}: {len(groups)} colour stretches"
        for r in g:
            moved = StitchRun(points=[(px + dx, py + dy) for px, py in r.points], kind=r.kind,
                              jump=True, trim=False, shape_id=f"{blk}:{arm}:{r.kind}")
            c.add_run(first_stop + i, moved)
    xs = [p[0] + dx for p in pts]
    ys = [p[1] + dy for p in pts]
    box = (min(xs), min(ys), max(xs), max(ys))
    c.arms[f"{blk}:{arm}"] = box
    return box


# --- block F -------------------------------------------------------------------------

def board_image(word: str = F_WORD):
    """The word as heavy stroke lettering with counters, cv2's Hershey simplex
    at a stroke/cap of about 0.15 (the family `tools/small_print.py` measured:
    its synthetic word is the same face and stroke). Returns the BGR image and
    the ink's size in px, so a caller can sew the ink at an exact cap."""
    font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 6.0, 19
    (w, h), base = cv2.getTextSize(word, font, scale, thick)
    pad = 20
    img = np.full((h + base + 2 * pad, w + 2 * pad, 3), 255, np.uint8)
    cv2.putText(img, word, (pad, pad + h), font, scale, (20, 20, 20), thick, cv2.LINE_AA)
    ys, xs = np.where(img[:, :, 0] < 128)
    return img, int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def block_F(c: CardV2, x0: float, y0: float, report: list) -> None:
    img, ink_w, ink_h = board_image()
    c.index("F", x0, y0, 88.0)
    top = y0 + 9.0
    x = x0
    right = x0
    for cap in F_CAPS:
        for k, (state, on) in enumerate(F_STATES, start=1):
            cfg = PipelineConfig(target_width_mm=ink_w * cap / ink_h, forced_class="flat",
                                 thread_wt=c.wt, small_print_floor=on,
                                 small_text_true_size=False)    # pre-flip (2026-10-14), as cut
            _res, plan = digitize(img, cfg)
            box = place(c, plan, x, top, "F", f"{cap}-{state}")
            c.add(0, hc.teeth(x, top - 0.8, k), f"F:label:{cap}-{state}")
            report.append({"block": "F", "arm": f"{cap}-{state}", "word": F_WORD, "cap_mm": cap,
                           "small_print_floor": on, "width_mm": round(box[2] - box[0], 2),
                           "height_mm": round(box[3] - box[1], 2)})
            x = box[2] + 5.0
            right = max(right, box[2])
        x += 4.0
    c.boxes["F"] = (x0, y0, right, top + max(r["height_mm"] for r in report if r["block"] == "F"))


# --- block G -------------------------------------------------------------------------

def gap_art():
    """The forbid-gap piece, 1:1: an 8 x 8 mm fill (blue) with a 2.5 mm bar (red)
    off its left side by 0.3 mm, off its right side by 0.6 mm, and along its
    bottom by 1.0 mm. Colours are the pipeline's to classify; the card sews
    the first colour it plans in the first stop's thread and the second in the
    second's. Returns the BGR image and the ink's width in mm."""
    f, b = G_FILL_MM, G_BAR_MM
    gl, gr, gb = G_GAPS_MM
    left, right = -(b + gl), f + gr + b
    top, bottom = 0.0, f + gb + b
    pad = 2.0
    img = np.full((int(round((bottom - top + 2 * pad) * G_PPM)),
                   int(round((right - left + 2 * pad) * G_PPM)), 3), 255, np.uint8)

    def rect(x, y, w, h, col):
        px = lambda v, o: int(round((v - o + pad) * G_PPM))  # noqa: E731
        cv2.rectangle(img, (px(x, left), px(y, top)), (px(x + w, left) - 1, px(y + h, top) - 1), col, -1)

    rect(0, 0, f, f, (200, 90, 30))                    # the fill
    rect(-(b + gl) + 0.0, 0, b, f, (30, 30, 200))       # left bar, ends at x = -gl
    rect(f + gr, 0, b, f, (30, 30, 200))                # right bar
    rect(0, f + gb, f, b, (30, 30, 200))                # bottom bar
    return img, right - left


def block_G(c: CardV2, x0: float, y0: float, report: list) -> None:
    img, ink_w = gap_art()
    width = 3 * (G_FILL_MM + 2 * G_BAR_MM + 2.0) + 2 * 3.0
    c.index("G", x0, y0, width)
    top = y0 + 9.0
    x = x0
    right = x0
    bottom = top
    for k, (gap, name) in enumerate(G_ARMS, start=1):
        cfg = PipelineConfig(target_width_mm=ink_w, forced_class="flat", thread_wt=c.wt,
                             forbid_gap_mm=gap, max_colors=2, small_text_true_size=False)
        _res, plan = digitize(img, cfg)
        box = place(c, plan, x, top, "G", f"gap-{name}", stretches=len(STOP_ORDER))
        c.add(0, hc.teeth(x, top - 0.8, k), f"G:label:gap-{name}")
        report.append({"block": "G", "arm": f"gap-{name}", "forbid_gap_mm": gap,
                       "colour_stretches": len(_phases(plan)),
                       "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
        x = box[2] + 3.0
        right = max(right, box[2])
        bottom = max(bottom, box[3])
    c.boxes["G"] = (x0, y0, right, bottom)


# --- block H -------------------------------------------------------------------------

def block_H(c: CardV2, x0: float, y0: float, report: list) -> None:
    img, w, _h, pad = hc.word_mask(H_WORD, H_CAP, font_path=SERIF)
    path = c._tmp / f"word_{c.wt}.png"
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA))
    ink_w = w - 2 * pad
    c.index("H", x0, y0, 40.0)
    y = y0 + 9.0
    bottom = y
    right = x0
    for k, (state, on) in enumerate(H_STATES, start=1):
        cfg = PipelineConfig(target_width_mm=ink_w, forced_class="flat", thread_wt=c.wt,
                             lettering_columns=on, small_text_true_size=False)
        _res, plan = digitize(path, cfg)
        box = place(c, plan, x0, y, "H", f"reach-{state}")
        c.add(0, hc.teeth(x0, y - 0.8, k), f"H:label:reach-{state}")
        report.append({"block": "H", "arm": f"reach-{state}", "word": H_WORD, "cap_mm": H_CAP,
                       "lettering_columns": on, "width_mm": round(box[2] - box[0], 2),
                       "height_mm": round(box[3] - box[1], 2)})
        right = max(right, box[2])
        y = box[3] + 4.0
        bottom = box[3]
    c.boxes["H"] = (x0, y0, max(right, x0 + 40.0), bottom)


# --- assemble, export, read back -------------------------------------------------------

def build(wt: int, tmp: Path) -> tuple[StitchPlan, CardV2, dict]:
    tmp.mkdir(parents=True, exist_ok=True)
    c = CardV2(wt)
    c._tmp = tmp
    report: list[dict] = []
    block_F(c, 0.0, 0.0, report)
    fb = c.boxes["F"]
    gy = fb[3] + 5.0
    block_G(c, 0.0, gy, report)
    block_H(c, 54.0, gy, report)
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


def _short_by_arm(plan: StitchPlan) -> dict[str, int]:
    """Plan-side stitches under 1.0 mm that are not 0.8 mm lock legs, by piece
    (`block:arm`). The digitizer's own lettering and fills sew some as they do
    today; the strips, labels and rules hold the floor."""
    out: dict[str, int] = {}
    for _b, r in plan.iter_runs():
        parts = r.shape_id.split(":")
        key = ":".join(parts[:2]) if len(parts) >= 3 and parts[1] != "label" else parts[0] + ":strips"
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            if 0.0 < d < machine.MIN_STITCH_MM - 1e-6 and abs(d - machine.TIE_STITCH_MM) >= 0.06:
                out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def readback(path: Path, plan: StitchPlan, wt: int, card: CardV2) -> dict:
    """Read the DST back with pystitch and measure it."""
    pat = pystitch.read_dst(str(path))
    mask = pystitch.COMMAND_MASK
    st = [(x / 10.0, y / 10.0) for x, y, cmd in pat.stitches if (cmd & mask) == pystitch.STITCH]
    moves = [(x / 10.0, y / 10.0) for x, y, cmd in pat.stitches
             if (cmd & mask) in (pystitch.STITCH, pystitch.JUMP)]
    changes = sum(1 for _x, _y, cmd in pat.stitches if (cmd & mask) == pystitch.COLOR_CHANGE)
    xs, ys = [p[0] for p in st], [p[1] for p in st]
    longest = 0.0
    prev = None
    for x, y, cmd in pat.stitches:
        if (cmd & mask) == pystitch.STITCH:
            cur = (x / 10.0, y / 10.0)
            if prev is not None:
                longest = max(longest, math.dist(prev, cur))
            prev = cur
        else:
            prev = None
    axis = max((max(abs(b[0] - a[0]), abs(b[1] - a[1])) for a, b in zip(moves, moves[1:])), default=0.0)
    by_arm: dict[str, int] = {}
    for _b, r in plan.iter_runs():
        parts = r.shape_id.split(":")
        key = ":".join(parts[:2]) if len(parts) >= 3 and parts[1] != "label" else parts[0] + ":strips"
        by_arm[key] = by_arm.get(key, 0) + len(r.points)
    short = _short_by_arm(plan)
    lock = sum(1 for _b, r in plan.iter_runs() for a, b in zip(r.points, r.points[1:])
               if 0.0 < math.dist(a, b) < machine.MIN_STITCH_MM - 1e-6
               and abs(math.dist(a, b) - machine.TIE_STITCH_MM) < 0.06)
    return {
        "file": path.name, "bytes": path.stat().st_size, "wt": wt,
        "blocks": len(card.boxes),
        "stitches_file": len(st), "stitches_plan": plan.stats.stitch_count,
        "colour_changes_file": changes, "colour_changes_plan": plan.stats.color_changes,
        "colours": changes + 1,
        "extent_mm": [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)],
        "within_hoop": bool(max(xs) - min(xs) <= HOOP_MM and max(ys) - min(ys) <= HOOP_MM),
        "x_range_mm": [round(min(xs), 1), round(max(xs), 1)],
        "y_range_mm": [round(min(ys), 1), round(max(ys), 1)],
        "max_needle_stitch_mm": round(longest, 2),
        "max_record_axis_mm": round(axis, 2),
        "stops": [{"stop": i + 1, "thread": STOPS[b.thread_index][0], "stitches": b.stitch_count,
                   "thread_m": round(b.length_mm / 1000.0, 2)} for i, b in enumerate(plan.blocks)],
        "stitches_by_piece": dict(sorted(by_arm.items())),
        "under_1mm_by_piece": short,
        "lock_legs_0p8": lock,
        "trims": plan.stats.trims,
        "blocks_mm": {k: [round(float(v), 1) for v in box] for k, box in sorted(card.boxes.items())},
        "pieces_mm": {k: [round(float(v), 1) for v in box] for k, box in sorted(card.arms.items())},
    }


# --- renders -------------------------------------------------------------------------------

def render(plan: StitchPlan, wt: int, out: Path, ppm: float = 12.0) -> np.ndarray:
    design = plan_to_design(plan, name=f"card v2 {wt} wt")
    img = stitchviz.render_design(design, px_per_mm=ppm, thread_mm=machine.thread_profile(wt).width_mm)
    cv2.imwrite(str(out), img)
    return img


def _label(img: np.ndarray, text: str) -> np.ndarray:
    bar = np.full((34, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def _hstack(imgs, gap=14):
    h = max(i.shape[0] for i in imgs)
    out = []
    for i in imgs:
        pad = np.full((h - i.shape[0], i.shape[1], 3), 255, np.uint8)
        out += [np.vstack([i, pad]), np.full((h, gap, 3), 255, np.uint8)]
    return np.hstack(out[:-1])


def panel(plan: StitchPlan, card: CardV2, wt: int, out: Path, ppm: float = 36.0) -> None:
    """One sheet: every OFF/ON piece cropped from the card at `ppm` px/mm
    (thread at the weight's laid width), the OFF/ON pair side by side."""
    design = plan_to_design(plan, name=f"card v2 {wt} wt")
    img = stitchviz.render_design(design, px_per_mm=ppm, pad_mm=2.0,
                                  thread_mm=machine.thread_profile(wt).width_mm)
    (_h, _w), to_px = stitchviz._frame(design["stitches"], ppm, 2.0)
    u = stitchviz.UNITS_PER_MM

    def crop(box, pad=0.3):
        a = to_px({"x": (box[0] - pad) * u, "y": -(box[1] - pad) * u})
        b = to_px({"x": (box[2] + pad) * u, "y": -(box[3] + pad) * u})
        xa, xb = sorted((a[0], b[0]))
        ya, yb = sorted((a[1], b[1]))
        return img[max(0, ya):yb, max(0, xa):xb].copy()

    rows = []
    for title, keys in (
        (f"F small print, {wt} wt: OFF | ON, 4 mm cap", ("F:4.0-off", "F:4.0-on")),
        (f"F small print, {wt} wt: OFF | ON, 3 mm cap", ("F:3.0-off", "F:3.0-on")),
        (f"G forbid gap, {wt} wt: OFF | 0.4 | 0.8 (bars at 0.3 / 0.6 / 1.0 mm)",
         ("G:gap-off", "G:gap-0.4", "G:gap-0.8")),
        (f"H column reach, {wt} wt: Column lane OFF | ON", ("H:reach-off", "H:reach-on")),
    ):
        rows.append(_label(_hstack([crop(card.arms[k]) for k in keys]), title))
    w = max(r.shape[1] for r in rows)
    rows = [np.hstack([r, np.full((r.shape[0], w - r.shape[1], 3), 255, np.uint8)]) for r in rows]
    cv2.imwrite(str(out), np.vstack([np.vstack([r, np.full((16, w, 3), 255, np.uint8)]) for r in rows]))


# --- docs --------------------------------------------------------------------------------------

def readback_markdown(table: dict) -> str:
    """The read-back table the README quotes (pystitch reading the DST back)."""
    cols = list(table)
    rows = [
        ("file", lambda r: f"`{r['file']}` ({r['bytes']:,} bytes)"),
        ("blocks on the card", lambda r: r["blocks"]),
        ("stitches in the file / in the plan", lambda r: f"{r['stitches_file']:,} / {r['stitches_plan']:,}"),
        ("colour changes in the file / planned", lambda r: f"{r['colour_changes_file']} / {r['colour_changes_plan']}"),
        ("colours (stops)", lambda r: r["colours"]),
        ("extent (mm), x by y", lambda r: f"{r['extent_mm'][0]} x {r['extent_mm'][1]}"),
        ("x range / y range (mm)", lambda r: f"{r['x_range_mm']} / {r['y_range_mm']}"),
        ("inside 100 x 100 mm", lambda r: "yes" if r["within_hoop"] else "NO"),
        ("longest needle stitch (mm)", lambda r: r["max_needle_stitch_mm"]),
        (f"longest record, per axis (mm; the format's limit is {MAX_RECORD_MM})", lambda r: r["max_record_axis_mm"]),
        ("trims", lambda r: r["trims"]),
        ("0.8 mm lock-leg stitches", lambda r: r["lock_legs_0p8"]),
    ]
    out = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for label, fn in rows:
        out.append(f"| {label} | " + " | ".join(str(fn(table[c])) for c in cols) + " |")
    out += ["", "Stitches per piece (an OFF piece and its ON partner differ only by the flag):", "",
            "| piece | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    keys = sorted({k for c in cols for k in table[c]["stitches_by_piece"]})
    for k in keys:
        out.append(f"| {k} | " + " | ".join(str(table[c]["stitches_by_piece"].get(k, 0)) for c in cols) + " |")
    out += ["", "Stitches per colour stop:", "", "| stop | thread | " + " | ".join(f"{c} stitches (thread m)" for c in cols) + " |",
            "|---|---|" + "---|" * len(cols)]
    for i, s in enumerate(table[cols[0]]["stops"]):
        out.append(f"| {s['stop']} | {s['thread']} | " + " | ".join(
            f"{table[c]['stops'][i]['stitches']:,} ({table[c]['stops'][i]['thread_m']})" for c in cols) + " |")
    out += ["", "Where each piece sits (mm, x0 y0 x1 y1, centre of the card at 0, 0):", "",
            "| piece | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for k in sorted(table[cols[0]]["pieces_mm"]):
        out.append(f"| {k} | " + " | ".join(str(table[c]["pieces_mm"][k]) for c in cols) + " |")
    return "\n".join(out) + "\n"


README = """# Sew-out card v2, 2026-10-13

Two DST files, one per thread weight. Every candidate that has landed since
the hairline card, on **one** card, each as an **OFF vs ON pair sewn side by
side**. You sew each on cloth, score it on `scoring-sheet.md`, and that
settles several ROADMAP gate-1 questions at once. **Every number on this card
is a candidate until you sew it.** Nothing here is a setting.

This does not replace the hairline card (`../hairline-card-2026-10-12/`,
blocks A-E: single strands, combs, narrow columns, SKEIN, strands over a
ground). That card is untouched, and its questions (stitch length of a single
strand, strand spacing, the 60 wt column floor) are still its to settle. This
one is SIZE_MM mm of new questions, and the hoop is the same or smaller.

## What is in this folder

| File | What it is |
|---|---|
| `card_v2_40wt.dst` | the card for **40 wt** thread. |
| `card_v2_60wt.dst` | the card for **60 wt** thread. |
| `card_v2_40wt.png`, `card_v2_60wt.png` | what each file looks like, thread drawn at the weight's laid width. A picture of the file, not of cloth. |
| `card_v2_40wt_blocks.png`, `card_v2_60wt_blocks.png` | every OFF / ON piece cropped at 36 px/mm, side by side, for comparing the two before you sew. |
| `scoring-sheet.md` | one table per sew-out, one row per piece. Print it. |
| `readback.md`, `readback.json` | the file checks (stitch count, size, colours, longest stitch), also quoted below. |

Both files are written by `python -m tools.sewout_candidates_card` (in `digitizer/`)
through the service's export path (pystitch), not the browser's DST codec, and
read back with pystitch (table at the bottom). The test is
`digitizer/tests/test_sewout_candidates_card.py`: it regenerates the card and checks
the read-back against `readback.json`.

## What you need

- **Fabric, two kinds:** a pique polo and a twill, the same two as card v1.
  Use a **mid-tone** (grey or khaki): the card sews a dark and a light thread.
- **Hooping:**
  - **Pique:** cutaway stabilizer (medium) under it, and **water-soluble
    topping** on top. Do not skip the topping on pique: block F's 3 mm print
    is small enough to sink into the waffle without it.
  - **Twill:** **tearaway** stabilizer (medium). No topping.
  - The design is **SIZE_MM mm**. Use a hoop with at least a 100 x 100 mm
    sewing field (a 4 x 4 in hoop is exactly that), as for card v1.
  - Hoop firm and flat. Do not change hoop, stabilizer or tension between
    the sew-outs without writing it on the sheet.
- **Thread, two cones per weight:** a **dark** (black or navy) and a **light**
  (white or cream). Same maker and same weight for both.
  - 40 wt file: **Madeira Polyneon No. 40**, or Isacord 40.
  - 60 wt file: **Madeira Polyneon No. 60**, or Isacord 60.
  - Pick the colours you have, as long as the two are clearly different from
    each other and from the cloth.
- **Needle:** 40 wt **75/11**. 60 wt: the needle that scored best on card v1
  (65/9 or 70/10). If v1 is not sewn yet, use **65/9**. Write it on the sheet.
- **Bobbin:** the same bobbin thread for every sew-out.

## The four sew-outs

A DST carries no thread weight and no needle, so you sew the files like this.

| Sew-out | File | Thread | Needle | Fabric |
|---|---|---|---|---|
| 1 | `card_v2_40wt.dst` | 40 wt | **75/11** | pique + cutaway + topping |
| 2 | `card_v2_60wt.dst` | 60 wt | v1's pick (else 65/9) | pique + cutaway + topping |
| 3 | `card_v2_40wt.dst` | 40 wt | **75/11** | twill + tearaway |
| 4 | `card_v2_60wt.dst` | 60 wt | v1's pick (else 65/9) | twill + tearaway |

Use **one** machine speed for all four and write it on the sheet (about 650
stitches a minute is a sensible start). Fresh needle for each sew-out. Each
hoop is about STITCHES stitches: allow roughly 12 minutes (an estimate from the
stitch count, not a measurement).

## How to sew one

1. Load the file. **Put the needle at the centre of the card**: the file's
   origin is the middle of the SIZE_MM mm box. Trace the outline to check it
   clears the hoop.
2. Turn **trims on**. The file cuts between pieces and wherever the
   digitizer cut inside one.
3. **Three colour stops**, in this order (two cones, dark and light; the
   machine asks for the dark one twice):
   1. **Stop 1, dark.** The three index strips (F, G, H), every label, the
      block F words, the block H words, and the **fill** of each block G arm.
   2. **Stop 2, light.** Block G's **bars** (all three arms).
   3. **Stop 3, dark.** Block G's two edge runs round each fill (short: about
      80 stitches in all). They are there because each G arm is the
      digitizer's own sew order, and the order is part of what is being tested.
4. Count **thread breaks** from the machine's counter, per block if you can.
5. Do not press or steam before scoring. Photograph each block close up
   (a macro) and once at arm's length.
6. Score on `scoring-sheet.md`.

## How to read the pairs

Every block has an **index strip**: its letter sewn as a run, 4 mm tall, with
a rule 1 mm under it. Each OFF / ON pair is labelled by **teeth** (a square
wave sewn above it), counted from the left: **1 tooth is OFF** (the engine as
shipped today), **2 teeth is ON** (the candidate). Block G has three arms:
**1 tooth OFF, 2 teeth `forbid_gap_mm` 0.4, 3 teeth `forbid_gap_mm` 0.8**.

![](card_v2_60wt.png)

## Block map

| Block | Where | What it is | Candidate it settles |
|---|---|---|---|
| **F** | top row | The word **BOARD** (counters in B, O, A, R, D). Left pair: **4 mm cap**, OFF then ON. Right pair: **3 mm cap**, OFF then ON. ON is `cfg.small_print_floor` (#873): counters at least one laid thread across are punched back open, and the column beside a counter holds half a laid width off it. | `SMALL_PRINT_COUNTER_MIN_WIDTHS` = **1.0** laid widths: counter kept open down to **0.40 mm at 40 wt, 0.32 mm at 60 wt**; and the **half-width hold-off** (0.20 / 0.16 mm). |
| **G** | middle row, left | Three **arms** of one two-colour piece: an 8 x 8 mm tatami **fill** with three 2.5 mm satin **bars** standing off it by **0.3 mm** (left), **0.6 mm** (right) and **1.0 mm** (bottom) of bare fabric drawn into the art. Arm 1 OFF; arm 2 `forbid_gap_mm` **0.4**; arm 3 `forbid_gap_mm` **0.8** (#874, WoK 44). With a value set, the colour sewn first spans a gap narrower than the value and tucks under the colour sewn on top. | `forbid_gap_mm`: **0.4** (closes the 0.3 gap only), **0.8** (closes 0.3 and 0.6), or neither. The 1.0 mm bar is the control: no value on the card closes it. |
| **H** | middle row, right | The word **ROSE** in a serif face (Roman AGS, OFL) at **9 mm cap**: top **Column lane OFF** (the skeleton satin tier), bottom **Column lane ON** (`cfg.lettering_columns`, the shipped default since 2026-10-12). | **Column reach** (#863's sew-out item): the Column lane's letters stand **0.06-0.07 mm** inside the skeleton tier's reach on the drawn edge. Is that visible, and which edge reads closer to the drawn letter? |

## What the files say about each pair (the FILE, not the cloth)

PAIRNOTES

## The file checks (pystitch reading the DST back)

READBACK
Reproduce with `python -m tools.sewout_candidates_card` from `digitizer/`.

## Things to know before you sew

- **Block F's ON and OFF words can look the same at arm's length.** That is a
  finding. Score the counters under a loupe and at arm's length separately.
- **Block G: which colour is on top.** The fill sews first (stop 1) and the
  bars sew on top of it (stop 2), so the **bars** own the seams and the fill
  spans the gap. With `forbid_gap_mm` set, the fill reaches across the gap
  and tucks under the bar's edge.
- **The cap heights are measured on the ink.** The words are sewn 1:1: the
  ink's bounding box is scaled to the size the label says, so the drawn cap is
  the label (the sewn height is a few tenths more: pull and the thread's own
  width). Card v1's block D scales its whole mask, 1 mm padding each side
  included, so its labels run small by about 14%: measured 2026-10-13, the
  letter regions of its "4.0 mm" SKEIN stand 4.6-4.8 mm tall and the "3.0"
  3.5-3.8 mm. Score v1's D by the sewn size, not the label.
- **Short stitches.** The digitizer sews some stitches under 1.0 mm in
  lettering and in tatami row turns, as it does today. The index strips and
  labels hold the 1.0 mm floor, and the lock legs are the engine's 0.8 mm.
"""

SCORING = """# Scoring sheet, sew-out card v2

One table per sew-out, one row per piece. **Thread breaks** come from the
machine counter. **Y/N** columns: write Y or N; a cell that does not apply is
marked `n/a`. Where a cell asks for several values (`B:_ O:_ ...`), fill in
each. The free note is for anything else, including the photo
(`macro: Y/N, arm's length: Y/N`).

Read each pair OFF then ON (OFF is 1 tooth, ON is 2 teeth; block G arms are
1, 2, 3 teeth). **Score OFF and ON the same way**, and score the pair together
before you move on.

- **Counters open (Y/N), per letter:** the bare cloth inside the letter shows
  as a hole (Y) or is filled in with thread (N).
- **Bare line along a counter (Y/N):** a line of cloth shows between a counter
  and the column that borders it (the column did not cover its own ink).
- **Legible at arm's length (Y/N):** you can read the word without being told.
- **Fabric visible in the seam (Y/N), per gap:** bare cloth shows between the
  bar and the fill at that gap, at arm's length and under a loupe.
- **Seam ridge or pucker (Y/N):** the bar's edge sits on a hard ridge, or the
  cloth puckers along the seam (the tuck-under is too much).
- **Edge reads closer to the drawn outline (OFF / ON / same):** compare the
  two H words against the picture in `card_v2_*wt.png`: which letter edge sits
  closer to the drawn one?
- **Letter looks thinner (Y/N):** the stroke reads lighter than its partner.

Candidate numbers under test; none of them is settled until this sheet is
filled in.

| Candidate | Value | What settles it |
|---|---|---|
| `SMALL_PRINT_COUNTER_MIN_WIDTHS` | 1.0 laid widths: 0.40 mm at 40 wt, ~0.32 mm at 60 wt | block F: counters open ON where OFF shut, at 3 and 4 mm |
| counter hold-off | half a laid width: 0.20 mm at 40 wt, 0.16 mm at 60 wt | block F: no bare line along a counter ON, counter stays its drawn size |
| `forbid_gap_mm` | 0.4 or 0.8 (or none) | block G: which arm shows no fabric in the 0.3 / 0.6 mm seams, with no ridge |
| Column reach | the Column lane's 0.06-0.07 mm shortfall | block H: does ON look thinner, or its edge farther from the drawn one? |

SHEETS"""

SHEET = """## Sew-out {n}: `{file}`, {wt} wt, needle {needle}, {fabric}

Date: ________  Machine: ____________  Speed (spm): ______  Thread (dark / light): ______________________

| Piece | Thread breaks (count) | Counters open (Y/N), per letter | Bare line along a counter (Y/N) | Legible at arm's length (Y/N) | Fabric visible in the seam (Y/N), per gap | Seam ridge or pucker (Y/N) | Edge closer to the drawn outline (OFF / ON / same) | Letter thinner (Y/N) | Free note |
|---|---|---|---|---|---|---|---|---|---|
| **F** 4 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 4 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **G** arm 1, OFF | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 2, 0.4 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 3, 0.8 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **H** Column lane OFF | ___ | n/a | n/a | _ | n/a | n/a | _ | _ | |
| **H** Column lane ON | ___ | n/a | n/a | _ | n/a | n/a | (same cell as above) | _ | |

Arm's length read of the whole hoop: ______________________________________
"""


def pair_notes(table: dict) -> str:
    """Per-pair facts read off the files, quoted in the README. The stitch
    deltas are the cost of ON; the sewn effect is the sew-out's to say."""
    lines = ["| piece | " + " | ".join(f"{c} stitches OFF / ON" for c in table) + " |",
             "|---|" + "---|" * len(table)]
    for label, off, on in (
        ("F, 4 mm BOARD", "F:4.0-off", "F:4.0-on"), ("F, 3 mm BOARD", "F:3.0-off", "F:3.0-on"),
        ("G, forbid_gap OFF / 0.4", "G:gap-off", "G:gap-0.4"), ("G, forbid_gap OFF / 0.8", "G:gap-off", "G:gap-0.8"),
        ("H, Column lane OFF / ON", "H:reach-off", "H:reach-on"),
    ):
        cells = [f"{table[c]['stitches_by_piece'][off]:,} / {table[c]['stitches_by_piece'][on]:,}" for c in table]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write_docs(out: Path, table: dict, fabric_label: str) -> None:
    first = table[next(iter(table))]
    size = f"{first['extent_mm'][0]} x {first['extent_mm'][1]}"
    stitches = f"{min(t['stitches_file'] for t in table.values()):,}-{max(t['stitches_file'] for t in table.values()):,}"
    text = (README.replace("READBACK", readback_markdown(table)).replace("PAIRNOTES", pair_notes(table))
            .replace("SIZE_MM", size).replace("STITCHES", stitches))
    text += f"\nDigitized pieces use the pipeline's default fabric profile ({fabric_label}).\n"
    (out / "README.md").write_text(text, encoding="utf-8")
    sheets, n = [], 0
    for fabric in ("pique + cutaway + topping", "twill + tearaway"):
        for file, wt, needle in (("card_v2_40wt.dst", 40, "75/11"), ("card_v2_60wt.dst", 60, "65/9 or v1's pick")):
            n += 1
            sheets.append(SHEET.format(n=n, file=file, wt=wt, needle=needle, fabric=fabric))
    (out / "scoring-sheet.md").write_text(SCORING.replace("SHEETS", "\n".join(sheets)), encoding="utf-8")


def generate(out: Path, renders: Path | None = None, *, quiet: bool = False) -> dict:
    """Write the whole card into `out` (and the PNGs into `renders`, if given);
    returns the read-back table."""
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)
    table = {}
    for wt in WEIGHTS:
        plan, card, extra = build(wt, tmp)
        pattern = plan_to_pattern(plan)
        pattern.metadata("name", f"CARDV2{wt}WT")
        path = out / f"card_v2_{wt}wt.dst"
        path.write_bytes(formats.write(pattern, "dst"))
        render(plan, wt, out / f"card_v2_{wt}wt.png")
        panel(plan, card, wt, out / f"card_v2_{wt}wt_blocks.png")
        rb = readback(path, plan, wt, card)
        rb["pieces"] = extra["pieces"]
        table[f"{wt}wt"] = rb
        if not quiet:
            print(json.dumps({k: v for k, v in rb.items() if k not in ("pieces", "pieces_mm", "stitches_by_piece")}))
    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()
    (out / "readback.json").write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    (out / "readback.md").write_text(readback_markdown(table), encoding="utf-8")
    write_docs(out, table, fabric_for(PipelineConfig()).label)
    if renders is not None:
        renders.mkdir(parents=True, exist_ok=True)
        for f in out.glob("*.png"):
            (renders / f.name).write_bytes(f.read_bytes())
    return table


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(REPO / "docs" / "sewout" / "card-v2-2026-10-13"))
    ap.add_argument("--renders", default=str(REPO / "docs" / "renders" / "claude-sewout-card-v2"),
                    help="copy the PNGs here too ('' to skip)")
    args = ap.parse_args(argv)
    generate(Path(args.out), Path(args.renders) if args.renders else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
