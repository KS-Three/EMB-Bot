"""The hairline sew-out card: two hoops of DST files, blocks A-E (2026-10-12).

    python -m tools.hairline_card [--out ../docs/sewout/hairline-card-2026-10-12]

Builds the card `docs/hairline-prototype-2026-10-12.md` ("The sew-out card as
DST files") lists, one hoop per thread weight, each no more than 100 x 100 mm:

    hairline_card_40wt.dst   sew in 40 wt   (75/11 needle)
    hairline_card_60wt.dst   sew in 60 wt   (twice: 65/9 and 70/10)

Blocks (each carries a labelled index strip: its letter sewn as a run, 4 mm
tall, with a rule 1 mm under it):

- A  single strands at 0.73 / 1.0 / 1.5 / 2.0 mm stitch length, straight and
     S-curve, as one pass and as a 3-pass bean; spirals of radius 2.0 / 1.5 /
     1.2 / 1.0 mm. Geometry is the same in both hoops.
- B  parallel single runs, five to a comb, at 0.4 / 0.6 / 0.8 / 1.2 mm spacing.
     The same in both hoops.
- C  narrow satin columns 0.6 / 0.8 / 1.0 / 1.2 mm wide, at the weight's own
     satin spacing (`machine.thread_profile`: 0.40 at 40 wt, 0.32 at 60 wt).
- D  a word at 4 / 3 / 2.5 mm cap height in one library font (Barstitch Bold,
     `src/fonts/barstitch_bold.json`, OFL): its authored satin columns are
     filled into a mask and digitized by THIS pipeline at the hoop's
     `thread_wt`, so the lettering is what the digitizer sews today.
- E  a 15 x 15 mm mid-tone tatami ground (the engine's own fill), then single
     runs over it in a dark and a light thread (two more colour stops), and
     the same runs on bare fabric beside it. The ground is not knocked out
     under the strands.

Every file goes through `digitizer_service.formats.write` (pystitch), the
trustworthy export path, and is read back with pystitch; never the browser's
DST codec. EVERY NUMBER HERE IS A CANDIDATE UNTIL KENT SEWS IT (ROADMAP gate
1): the stitch lengths, the spacings, the 60 wt widths. The card is how they
get settled. Stitches under 1.0 mm that are deliberate: block A's 0.73 mm
lines and C's 0.6 / 0.8 mm columns (the thing being tested), plus whatever
the digitizer sews in block D, as it does today; everything else holds the
1.0 mm floor, and the lock legs are the existing tie rule's 0.8 mm.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pystitch
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitchviz  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from digitizer_core.stage6_fill import stitch_shape  # noqa: E402
from digitizer_core.stitches import (RUN, SATIN, StitchBlock, StitchPlan,  # noqa: E402
                                     StitchRun, apply_ties, strip_ties)
from digitizer_service import formats  # noqa: E402

REPO = ROOT.parent
FONT = REPO / "src" / "fonts" / "barstitch_bold.json"
HOOP_MM = 100.0
WEIGHTS = (40, 60)

# Colour stops, in sew order. The ground goes down first so the strands lie on it.
GROUND, DARK, LIGHT = 0, 1, 2
STOPS = {
    GROUND: ("ground (mid-tone)", (176, 150, 110), "mid-tone: tan / grey, between the two below"),
    DARK: ("dark", (20, 24, 40), "dark: black or navy"),
    LIGHT: ("light", (244, 240, 226), "light: white or cream"),
}

SHORT_OK_NOTE = {
    "A": "0.73 mm lines (deliberate: today's bean stride, below Melco's 1.0 floor)",
    "C": "0.6 / 0.8 mm columns (deliberate: the column floor is the question)",
    "D": "the digitizer's own lettering, as it sews today",
}


# --- stitch helpers ------------------------------------------------------------

def _arc(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def resample(pts, stitch_mm: float, curved: bool = False) -> list[tuple[float, float]]:
    """A smooth polyline -> needle points at equal arc length. Under 1.0 mm
    the stride is the nearest equal division of the line (the card's 0.73 mm
    arm is deliberately below the floor). From 1.0 mm up it is never SHORTER
    than asked: the line is divided down, so a 1.0 mm arm holds the floor; on
    a curve the chord is a little shorter than its arc, so `curved` asks for
    1.2% more arc."""
    total = _arc(pts)
    if stitch_mm < machine.MIN_STITCH_MM:
        n = max(1, int(round(total / stitch_mm)))
    else:
        n = max(1, int(total // (stitch_mm * (1.012 if curved else 1.0) + 1e-9)))
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    out = []
    j = 0
    for i in range(n + 1):
        s = total * i / n
        while j < len(cum) - 2 and cum[j + 1] < s:
            j += 1
        seg = cum[j + 1] - cum[j]
        f = 0.0 if seg <= 0 else (s - cum[j]) / seg
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * f,
                    pts[j][1] + (pts[j + 1][1] - pts[j][1]) * f))
    return out


def corners(pts, stitch_mm: float = 1.5, floor_mm: float = machine.MIN_STITCH_MM):
    """A polyline whose vertices must be needle points (a letter) -> stitches:
    each segment in equal parts nearest `stitch_mm`, none under `floor_mm`."""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b)
        n = max(1, min(int(round(d / stitch_mm)), int(d // floor_mm) or 1))
        for i in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out


def bean(pts):
    """Every stitch sewn forward, back, forward: the 3-pass bean on the line."""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        out += [b, a, b]
    return out


def _run(points, shape_id, *, trim=True) -> StitchRun:
    return StitchRun(points=[(float(x), float(y)) for x, y in points], kind=RUN,
                     jump=True, trim=trim, shape_id=shape_id)


def s_curve(x0, y0, length=18.0, amp=1.5, wavelength=13.3, n=400):
    """A wave whose tightest bend has a ~3 mm radius (wavelength^2 / (4 pi^2 amp))."""
    x = np.linspace(0.0, length, n)
    y = amp * np.sin(2 * math.pi * x / wavelength)
    return [(x0 + a, y0 + b) for a, b in zip(x, y)]


def spiral(cx, cy, r, turns=1.4, n=240):
    a = np.linspace(0.0, 2 * math.pi * turns, n)
    rr = r * (1.0 - 0.25 * np.linspace(0.0, 1.0, n))
    return [(cx + rr[i] * math.cos(a[i]), cy + rr[i] * math.sin(a[i])) for i in range(n)]


def teeth(x, y, k, h=1.2):
    """A square wave of `k` teeth (the card's count label): runs right from (x, y)."""
    pts = [(x, y)]
    for i in range(k):
        x0 = x + i * 2.4
        pts += [(x0, y - h), (x0 + 1.2, y - h), (x0 + 1.2, y), (x0 + 2.4, y)]
    return pts[:-1]


LETTERS = {      # 4 mm tall, 3 mm wide, origin top-left, y down; vertices are needle points
    "A": [(0, 4), (1.5, 0), (3, 4), (2.45, 2.7), (0.55, 2.7)],
    "B": [(0, 4), (0, 0), (2.5, 0), (2.5, 2), (0, 2), (2.5, 2), (2.5, 4), (0, 4)],
    "C": [(3, 0), (0, 0), (0, 4), (3, 4)],
    "D": [(0, 0), (0, 4), (2, 4), (3, 3), (3, 1), (2, 0), (0, 0)],
    "E": [(3, 0), (0, 0), (0, 2), (2.5, 2), (0, 2), (0, 4), (3, 4)],
}


class Card:
    """Runs by colour stop, with the layout bookkeeping the read-back needs."""

    def __init__(self, wt: int):
        self.wt = wt
        self.prof = machine.thread_profile(wt)
        self.items: list[tuple[int, StitchRun]] = []
        self.boxes: dict[str, tuple[float, float, float, float]] = {}

    def add(self, stop: int, points, shape_id: str, *, trim=True) -> None:
        pts = [p for i, p in enumerate(points) if i == 0 or math.dist(p, points[i - 1]) > 1e-9]
        if len(pts) >= 2:
            self.items.append((stop, _run(pts, shape_id, trim=trim)))

    def add_run(self, stop: int, run: StitchRun) -> None:
        self.items.append((stop, run))

    def index(self, key: str, x0: float, y0: float, width: float) -> None:
        """The block's index strip: its letter as a run (4 mm), a rule 1 mm under."""
        self.add(DARK, corners([(x0 + a, y0 + b) for a, b in LETTERS[key]]), f"{key}:index")
        self.add(DARK, corners([(x0 + 5.0, y0 + 5.0), (x0 + width, y0 + 5.0)]), f"{key}:rule")

    def plan(self) -> StitchPlan:
        blocks = []
        for stop in (GROUND, DARK, LIGHT):
            runs = [r for s, r in self.items if s == stop]
            if not runs:
                continue
            # The digitizer's own lettering keeps ITS jump/cut decisions
            # (a hop under `TRIM_AT_MM` is a float, not a cut) with its folded
            # lock stitches stripped; the first run of each word is cut to
            # when the hop from the previous item is long. Everything else on
            # the card is cut after every run, locked at both ends.
            prev = None
            for r in runs:
                if r.shape_id.startswith("D:"):
                    r.points = strip_ties(r.points)
                    if prev is not None:
                        hop = math.dist(prev, r.points[0])
                        r.jump = hop >= machine.TINY_STITCH_MM
                        r.trim = hop > machine.TRIM_AT_MM
                prev = r.points[-1]
            runs[0].jump = False
            runs[0].trim = False
            apply_ties(runs)
            name, rgb, _hint = STOPS[stop]
            blocks.append(StitchBlock(thread_index=stop, thread_number=f"{stop + 1}", rgb=rgb,
                                      runs=runs))
        return StitchPlan(blocks=blocks, palette=[], warnings=[])


# --- the blocks ------------------------------------------------------------------

STITCH_LENGTHS = (0.73, 1.0, 1.5, 2.0)


def block_A(c: Card, x0: float, y0: float) -> None:
    c.index("A", x0, y0, 44.0)
    top = y0 + 7.0
    pitch = 5.0
    for form, bx in (("straight", x0 + 11.0), ("S", x0 + 29.0)):
        for arm, use_bean in (("one", False), ("bean", True)):
            for k, L in enumerate(STITCH_LENGTHS):
                row = (0 if arm == "one" else 4) + k
                y = top + row * pitch + (3.0 if arm == "bean" else 0.0) + 1.5
                line = ([(bx, y), (bx + 15.0, y)] if form == "straight"
                        else s_curve(bx, y, 15.0))
                pts = resample(line, L, curved=(form == "S"))
                pts = bean(pts) if use_bean else pts
                tag = f"A:{form}:{arm}:{L}"
                c.add(DARK, pts, tag)
                if form == "straight":     # the count label, left of the row
                    c.add(DARK, teeth(x0 + 0.0, y + 0.6, k + 1), f"A:label:{arm}:{k + 1}")
    cy = top + 8 * pitch + 3.0 + 2.5
    for i, r in enumerate((2.0, 1.5, 1.2, 1.0)):
        cx = x0 + 4.0 + i * 11.0
        c.add(DARK, resample(spiral(cx, cy, r), 1.5, curved=True), f"A:curl:{r}")
    c.boxes["A"] = (x0, y0, x0 + 44.0, cy + 3.0)


def block_B(c: Card, x0: float, y0: float) -> None:
    c.index("B", x0, y0, 44.0)
    top = y0 + 8.0
    spots = {0.4: (x0, top), 0.6: (x0 + 24.0, top), 0.8: (x0, top + 8.0), 1.2: (x0 + 24.0, top + 8.0)}
    for k, (sp, (bx, by)) in enumerate(spots.items(), start=1):
        c.add(DARK, teeth(bx, by - 0.8, k), f"B:label:{sp}")
        for j in range(5):
            y = by + j * sp
            pts = resample([(bx, y), (bx + 20.0, y)], 1.5)
            if j % 2:
                pts = pts[::-1]
            c.add(DARK, pts, f"B:comb:{sp}:{j}")
    c.boxes["B"] = (x0, y0, x0 + 44.0, top + 8.0 + 4 * 1.2 + 1.0)


def satin_column(x0, y, length, width, spacing):
    """Zigzag between two rails `width` apart, one station every `spacing` along
    the axis (the engine's own column construction: cross, diagonal, cross)."""
    n = max(2, int(round(length / spacing)))
    pts = []
    for i in range(n + 1):
        x = x0 + length * i / n
        pts += [(x, y - width / 2), (x, y + width / 2)]
    return pts


def block_C(c: Card, x0: float, y0: float) -> None:
    c.index("C", x0, y0, 44.0)
    top = y0 + 8.5
    sp = c.prof.satin_spacing_mm
    for k, w in enumerate((0.6, 0.8, 1.0, 1.2)):
        y = top + k * 3.6
        c.add(DARK, teeth(x0, y + 0.6, k + 1), f"C:label:{w}")
        pts = satin_column(x0 + 12.0, y, 20.0, w, sp)
        c.items.append((DARK, StitchRun(points=[(float(a), float(b)) for a, b in pts], kind=SATIN,
                                        jump=True, trim=True, shape_id=f"C:col:{w}")))
    c.boxes["C"] = (x0, y0, x0 + 44.0, top + 3 * 3.6 + 1.5)


def _font_words():
    font = json.loads(FONT.read_text(encoding="utf-8"))
    return font


def word_mask(text: str, cap_mm: float, px_per_mm: float = 20.0):
    """The word, from the font's authored satin columns filled between their
    rails -> (RGBA image, width mm, height mm). Cap height is measured from H."""
    font = _font_words()
    gl = font["glyphs"]

    def ys(g):
        return [p[1] for col in g["cols"] for r in (col["railA"], col["railB"]) for p in r]
    cap_units = max(ys(gl["H"])) - min(ys(gl["H"]))
    top_units = min(ys(gl["H"]))
    s = cap_mm / cap_units
    polys = []
    x = 0.0
    for ch in text:
        g = gl[ch]
        for col in g["cols"]:
            ring = [(x + p[0] * s, (p[1] - top_units) * s) for p in col["railA"]] + \
                   [(x + p[0] * s, (p[1] - top_units) * s) for p in reversed(col["railB"])]
            poly = Polygon(ring).buffer(0)
            if not poly.is_empty:
                polys.append(poly)
        x += g["adv"] * s
    shape = unary_union(polys)
    x0, y0, x1, y1 = shape.bounds
    pad = 1.0
    w = int(math.ceil((x1 - x0 + 2 * pad) * px_per_mm))
    h = int(math.ceil((y1 - y0 + 2 * pad) * px_per_mm))
    img = np.zeros((h, w, 4), np.uint8)
    for part in (shape.geoms if hasattr(shape, "geoms") else [shape]):
        for ring, val in [(part.exterior, 255)] + [(r, 0) for r in part.interiors]:
            px = np.round((np.asarray(ring.coords) - [x0 - pad, y0 - pad]) * px_per_mm).astype(np.int32)
            cv2.fillPoly(img, [px.reshape(-1, 1, 2)], (20, 24, 40, val), cv2.LINE_8)
    return img, w / px_per_mm, h / px_per_mm, pad


def block_D(c: Card, x0: float, y0: float, tmp: Path, word: str = "SKEIN") -> list[dict]:
    c.index("D", x0, y0, 44.0)
    y = y0 + 8.0
    report = []
    for cap in (4.0, 3.0, 2.5):
        img, w, h, pad = word_mask(word, cap)
        path = tmp / f"word_{c.wt}_{cap}.png"
        cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA))
        cfg = PipelineConfig(target_width_mm=w, forced_class="flat", thread_wt=c.wt)
        _result, plan = digitize(path, cfg)
        pts = [p for _b, r in plan.iter_runs() for p in r.points]
        bx0, by0 = min(p[0] for p in pts), min(p[1] for p in pts)
        # Put the lettering's top-left at (x0 + 5, y): the art's own pad is 1 mm.
        dx, dy = x0 + 5.0 - bx0, y - by0
        n_runs = 0
        for _b, r in plan.iter_runs():
            moved = StitchRun(points=[(px + dx, py + dy) for px, py in r.points], kind=r.kind,
                              jump=True, trim=False, shape_id=f"D:{cap}:{r.kind}")
            c.add_run(DARK, moved)
            n_runs += 1
        report.append({"cap_mm": cap, "word": word, "design_width_mm": round(w, 2),
                       "runs": n_runs, "kinds": sorted({r.kind for _b, r in plan.iter_runs()})})
        y += cap + 2.4
    c.boxes["D"] = (x0, y0, x0 + 44.0, y)
    return report


def tatami(poly: Polygon, shape_id: str):
    runs, _rep = stitch_shape(poly, shape_id, angle_deg=45.0, row_mm=machine.FILL_ROW_MM,
                              stitch_mm=machine.FILL_STITCH_MM, underlay_style="none",
                              trim_at_mm=machine.TRIM_AT_MM)
    return runs


def block_E(c: Card, x0: float, y0: float) -> None:
    c.index("E", x0, y0, 44.0)
    gx, gy = x0 + 1.0, y0 + 8.0
    ground = Polygon([(gx, gy), (gx + 15, gy), (gx + 15, gy + 15), (gx, gy + 15)])
    for r in tatami(ground, "E:ground"):
        c.add_run(GROUND, r)
    # Strands over the ground, then the same on bare fabric beside it.
    for part, sx in (("ground", gx - 1.0), ("bare", gx + 21.0)):
        ln = 21.0 if part == "ground" else 19.0
        spec = [(DARK, 3.0, "straight"), (LIGHT, 5.5, "straight"), (DARK, 8.5, "S"),
                (LIGHT, 11.0, "S"), (DARK, 13.0, "straight")]
        for stop, off, form in spec:
            y = gy + off
            line = [(sx, y), (sx + ln, y)] if form == "straight" else s_curve(sx, y, ln, 1.2, 11.0)
            c.add(stop, resample(line, 1.5, curved=(form == "S")), f"E:{part}:{'dark' if stop == DARK else 'light'}:{form}")
    c.boxes["E"] = (x0, y0, x0 + 44.0, gy + 15.0)


# --- assemble, export, read back -------------------------------------------------------

def build(wt: int, tmp: Path) -> tuple[StitchPlan, Card, dict]:
    c = Card(wt)
    block_A(c, -47.0, -47.0)
    block_B(c, 3.0, -47.0)
    block_C(c, 3.0, -21.0)
    dlet = block_D(c, 3.0, 2.0, tmp)
    block_E(c, -47.0, 12.0)
    plan = c.plan()
    # Centre the card on the machine's origin.
    xs = [p[0] for b in plan.blocks for r in b.runs for p in r.points]
    ys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for b in plan.blocks:
        for r in b.runs:
            r.points = [(x - cx, y - cy) for x, y in r.points]
    for k, (a, b2, c2, d) in list(c.boxes.items()):
        c.boxes[k] = (a - cx, b2 - cy, c2 - cx, d - cy)
    plan.design_size_mm = (max(xs) - min(xs), max(ys) - min(ys))
    return plan, c, {"lettering": dlet, "offset_mm": (round(cx, 3), round(cy, 3))}


def readback(path: Path, plan: StitchPlan, wt: int) -> dict:
    """Read the DST back with pystitch and measure it."""
    pat = pystitch.read_dst(str(path))
    st = [(x / 10.0, y / 10.0) for x, y, cmd in pat.stitches if (cmd & pystitch.COMMAND_MASK) == pystitch.STITCH]
    all_xy = [(x / 10.0, y / 10.0) for x, y, cmd in pat.stitches
              if (cmd & pystitch.COMMAND_MASK) in (pystitch.STITCH, pystitch.JUMP)]
    changes = sum(1 for _x, _y, cmd in pat.stitches if (cmd & pystitch.COMMAND_MASK) == pystitch.COLOR_CHANGE)
    xs = [p[0] for p in st]
    ys = [p[1] for p in st]
    # Consecutive needle-down stitches only (a jump or cut breaks the chain).
    short = lock = 0
    prev = None
    for x, y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH:
            if prev is not None:
                d = math.dist(prev, (x / 10.0, y / 10.0))
                if 0.0 < d < machine.MIN_STITCH_MM - 1e-6:
                    if abs(d - machine.TIE_STITCH_MM) < 0.06:
                        lock += 1
                    else:
                        short += 1
            prev = (x / 10.0, y / 10.0)
        else:
            prev = None
    stats = plan.stats
    by_short = short_by_block(plan)
    by_block: dict[str, int] = {}
    for _b, r in plan.iter_runs():
        blk = r.shape_id.split(":")[0]
        by_block[blk] = by_block.get(blk, 0) + len(r.points)
    return {
        "short_by_block": by_short,
        "short_unexpected": sum(v for k, v in by_short.items() if k not in EXPECTED_SHORT),
        "stitches_by_block": dict(sorted(by_block.items())),
        "stops": [{"stop": i + 1, "thread": STOPS[b.thread_index][0], "stitches": b.stitch_count,
                   "thread_m": round(b.length_mm / 1000.0, 2)} for i, b in enumerate(plan.blocks)],
        "file": path.name, "bytes": path.stat().st_size, "wt": wt,
        "stitches_file": len(st), "stitches_plan": stats.stitch_count,
        "colour_changes_file": changes, "colour_changes_plan": stats.color_changes,
        "extent_mm": [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)],
        "within_hoop": bool(max(xs) - min(xs) <= HOOP_MM and max(ys) - min(ys) <= HOOP_MM),
        "x_range_mm": [round(min(xs), 1), round(max(xs), 1)],
        "y_range_mm": [round(min(ys), 1), round(max(ys), 1)],
        "under_1mm_not_lock": short, "lock_legs_0p8": lock,
        "plan_extent_mm": [round(plan.design_size_mm[0], 1), round(plan.design_size_mm[1], 1)],
        "longest_move_mm": round(max((math.dist(a, b) for a, b in zip(all_xy, all_xy[1:])), default=0.0), 1),
    }


#: Where a stitch under 1.0 mm (not a lock leg) is EXPECTED: the thing a block
#: tests, or what the engine does anyway. Anything else is a bug in the card.
EXPECTED_SHORT = {
    "A:0.73 lines": "block A's 0.73 mm lines (today's bean stride, under Melco's 1.0 floor: the test)",
    "C:0.6 col": "block C's 0.6 mm column (its cross is under 1.0: the test)",
    "C:0.8 col": "block C's 0.8 mm column (its cross is under 1.0: the test)",
    "D:4.0 cap": "block D lettering, as the digitizer sews it today",
    "D:3.0 cap": "block D lettering, as the digitizer sews it today",
    "D:2.5 cap": "block D lettering, as the digitizer sews it today",
    "E:ground": "block E's tatami: row turns at the engine's 0.15 mm pitch",
}


def short_key(shape_id: str) -> str:
    parts = shape_id.split(":")
    blk = parts[0] or "?"
    if blk == "A":
        return "A:0.73 lines" if parts[-1] == "0.73" else "A:other"
    if blk == "C":
        return f"C:{parts[2]} col" if len(parts) > 2 and parts[1] == "col" else "C:other"
    if blk == "D":
        return f"D:{parts[1]} cap"
    if blk == "E":
        return "E:ground" if parts[1] == "ground" and len(parts) == 2 else "E:strands"
    return blk


def short_by_block(plan: StitchPlan) -> dict[str, int]:
    """Plan-side stitches under 1.0 mm that are not lock legs, by block letter,
    so the read-back total can be attributed to the blocks that own them."""
    out: dict[str, int] = {}
    for _b, r in plan.iter_runs():
        key = short_key(r.shape_id)
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            if 0.0 < d < machine.MIN_STITCH_MM - 1e-6 and abs(d - machine.TIE_STITCH_MM) >= 0.06:
                out[key] = out.get(key, 0) + 1
    return out


def render(plan: StitchPlan, wt: int, out: Path) -> None:
    design = plan_to_design(plan, name=f"hairline card {wt} wt")
    img = stitchviz.render_design(design, px_per_mm=9.0, thread_mm=machine.thread_profile(wt).width_mm)
    cv2.imwrite(str(out), img)


README = """# Hairline sew-out card, 2026-10-12

Two DST files, one per thread weight. You sew each on cloth, score it on
`scoring-sheet.md`, and that settles the numbers the hairline work has been
guessing at. **Every number on this card is a candidate until you sew it**
(ROADMAP gate 1): the 60 wt laid width and spacing, the 0.73 / 1.0 / 1.5 /
2.0 mm stitch lengths, how close two strands can sit, the 1.0 mm column floor
at 60 wt, the cap-height note. Nothing here is a setting.

## What is in this folder

| File | What it is |
|---|---|
| `hairline_card_40wt.dst` | the card for **40 wt** thread. Sew once per fabric. |
| `hairline_card_60wt.dst` | the card for **60 wt** thread. Sew **twice** per fabric (two needles, below). |
| `hairline_card_40wt.png`, `hairline_card_60wt.png` | what each file looks like, thread drawn at the weight's laid width. A picture of the file, not of cloth. |
| `scoring-sheet.md` | one table per sew-out, one row per block. Print it. |
| `readback.md`, `readback.json` | the file checks (stitch count, size, short stitches), also quoted below. |

Both files are written by `python -m tools.hairline_card` (in `digitizer/`)
through the service's export path (pystitch), not the browser's DST codec,
and read back with pystitch (table at the bottom).

## What you need

- **Fabric, two kinds:** a pique polo and a twill. Use a **mid-tone** (grey or
  khaki). The card sews a dark thread and a light thread; on white cloth the
  light strands in block E will not show.
- **Hooping:**
  - **Pique:** cutaway stabilizer (medium) under it, and **water-soluble
    topping** on top. Do not skip the topping on pique: it keeps the single
    strands from sinking into the waffle.
  - **Twill:** **tearaway** stabilizer (medium). No topping.
  - The design is **94 x 82 mm**. Use a hoop with at least a 100 x 100 mm
    sewing field. A 4 x 4 in hoop is exactly that and leaves 3 mm each side;
    take a bigger hoop if you have one.
  - Hoop firm and flat. Do not change hoop, stabilizer or tension between
    the sew-outs without writing it on the sheet.
- **Thread, three cones per weight:** a dark (black or navy), a light (white
  or cream) and a mid-tone (tan or grey, between the two). Same maker and
  same weight for all three.
  - 40 wt hoop: **Madeira Polyneon No. 40**, or Isacord 40.
  - 60 wt hoop: **Madeira Polyneon No. 60**, or Isacord 60.
  - Pick the colours you have. The card does not care which, as long as dark,
    light and mid-tone are clearly different.
- **Bobbin:** the same bobbin thread for every sew-out.

## The six sew-outs

A DST carries no thread weight and no needle, so you sew the files like this.
The two needles on the 60 wt hoop are on purpose: the sources disagree (Madeira
says 60/8 to 65/9, Wilcom says 70/10 to 75/11) and only cloth can settle it.

| Sew-out | File | Thread | Needle | Fabric |
|---|---|---|---|---|
| 1 | `hairline_card_40wt.dst` | 40 wt | **75/11** | pique + cutaway + topping |
| 2 | `hairline_card_60wt.dst` | 60 wt | **65/9** | pique + cutaway + topping |
| 3 | `hairline_card_60wt.dst` | 60 wt | **70/10** | pique + cutaway + topping |
| 4 | `hairline_card_40wt.dst` | 40 wt | **75/11** | twill + tearaway |
| 5 | `hairline_card_60wt.dst` | 60 wt | **65/9** | twill + tearaway |
| 6 | `hairline_card_60wt.dst` | 60 wt | **70/10** | twill + tearaway |

Use **one** machine speed for all six and write it on the sheet (about 650
stitches a minute is a sensible start). Fresh needle for each sew-out. Each
hoop is about 4,000 stitches and a hundred or so trims: allow roughly 15
minutes (an estimate from the stitch count, not a measurement).

## How to sew one

1. Load the file. **Put the needle at the centre of the card**: the file's
   origin is the middle of the 94 x 82 mm box. Trace the outline to check it
   clears the hoop.
2. Turn **trims on**. The file cuts after every line in blocks A, B, C and E,
   and wherever the digitizer cut in block D.
3. **Three colour stops**, in this order:
   1. **Stop 1, mid-tone.** Block E's 15 x 15 mm ground (the tan square at the
      bottom left). Nothing else sews in this colour.
   2. **Stop 2, dark.** Everything else: the five index strips, blocks A, B,
      C and D, and block E's dark strands. This is the long one.
   3. **Stop 3, light.** Block E's light strands, over the ground and over
      bare cloth.
4. Count **thread breaks** from the machine's counter, per block if you can
   (stop the machine at the end of each block and read it). Write them on
   the sheet.
5. Do not press or steam before scoring. Photograph each block close up
   (a macro) and once at arm's length.
6. Score on `scoring-sheet.md`.

## Where things are, and what each block answers

Each block has an **index strip**: its letter sewn as a run, 4 mm tall, with
a rule 1 mm under it, so you can read which block you are looking at.

![](hairline_card_60wt.png)

| Block | Where | What it is | What it answers |
|---|---|---|---|
| **A** | top left | Two columns of 8 lines, each 15 mm: **straight** (left) and an **S-curve** with a 3 mm bend radius (right). Rows 1-4 are **one pass** at stitch lengths **0.73 / 1.0 / 1.5 / 2.0 mm**, rows 5-8 the same four as a **3-pass bean** (every stitch sewn forward, back, forward). A row of **square teeth** to the left of each line counts the stitch length: 1 tooth = 0.73, 2 = 1.0, 3 = 1.5, 4 = 2.0. Under the lines, **four spirals** of radius **2.0 / 1.5 / 1.2 / 1.0 mm** at 1.5 mm stitches. | Which stitch length a single strand wants, and does one pass hold up against a bean? Does a tight curl read as a curl or as a polygon? |
| **B** | top right | Four **combs** of five parallel 20 mm single runs at 1.5 mm stitches, spaced **0.4 / 0.6 / 0.8 / 1.2 mm** (1 / 2 / 3 / 4 teeth above each). | At what spacing do neighbouring strands stop reading as separate? |
| **C** | right, middle | Four **satin columns**, 20 mm long, **0.6 / 0.8 / 1.0 / 1.2 mm** wide (1 to 4 teeth), at the weight's own stitch spacing: **0.40 mm in the 40 wt file, 0.32 mm in the 60 wt file**. | Does 60 wt move Melco's 1.0 mm column floor? Does the 0.32 spacing cover? |
| **D** | right, lower | The word **SKEIN** in Barstitch Bold at **4.0, 3.0 and 2.5 mm cap height** (top to bottom), digitized by this pipeline at the file's thread weight. | The cap-height note: the smallest caps that stay legible at each weight. |
| **E** | bottom left | A **15 x 15 mm mid-tone tatami** (the tan square), then five single strands over it, top to bottom: dark straight, light straight, dark S-curve, light S-curve, dark straight. The **same five strands** are repeated on **bare fabric** to the right. | Does a strand read over a ground that runs under it? Does it read worse, better or the same as on bare cloth? Does the double layer under it pucker? |

## Short stitches you will see in the file, and why

The file keeps every stitch at or over 1.0 mm (Melco's floor, set by the
needle and not the thread) except in four places, and the 0.8 mm lock legs the
engine always adds at a start or a cut. The four places are the things being
tested:

- **A, the 0.73 mm lines** (rows 1 and 5): today's bean stride.
- **C, the 0.6 and 0.8 mm columns:** a column that narrow crosses in under
  1.0 mm.
- **D, the lettering:** as the digitizer sews it today.
- **E, the tatami:** its row turns, at the engine's 0.15 mm row pitch.

## The file checks (pystitch reading the DST back)

READBACK
Reproduce with `python -m tools.hairline_card` from `digitizer/`; the
tests are `digitizer/tests/test_hairline_card.py`.
"""

SCORING = """# Scoring sheet, hairline sew-out card

One table per sew-out, one row per block. **Thread breaks** come from the
machine counter. **Y/N** columns: write Y or N; a cell that does not apply to
a block is marked `n/a` and left alone. Where a cell asks for several
values (`0.73:_ 1.0:_ ...`), fill in each. The free note is for anything else,
including the photo (`macro: Y/N, arm's length: Y/N`).

- **Strands continuous (Y/N):** the line is unbroken from end to end at arm's
  length and under a loupe, no gaps, no skipped stitches, no thread lying
  loose.
- **Strands merged at spacing X (Y/N):** at that spacing, do neighbouring
  strands read as one band (Y) or as separate lines (N)?
- **Cap height legible (Y/N):** at that height, can you read the word at
  arm's length without being told what it says?
- **Bare fabric visible (Y/N):** can you see cloth where thread should be: a
  gap in a column, cloth between a strand and its ground?

Candidate numbers under test, from `docs/hairline-prototype-2026-10-12.md`;
none of them is settled until this sheet is filled in.

SHEETS"""

SHEET = """## Sew-out {n}: `{file}`, {wt} wt, needle {needle}, {fabric}

Date: ________  Machine: ____________  Speed (spm): ______  Thread (dark / light / mid-tone): ______________________

| Block | Thread breaks (count) | Strands continuous (Y/N) | Strands merged at spacing X (Y/N) | Cap height legible (Y/N) | Bare fabric visible (Y/N) | Free note |
|---|---|---|---|---|---|---|
| **A** strands, curls | ___ | 0.73:_ 1.0:_ 1.5:_ 2.0:_ (one pass)  0.73:_ 1.0:_ 1.5:_ 2.0:_ (bean) | n/a | n/a | n/a | curls (r 2.0 / 1.5 / 1.2 / 1.0): round or polygon? |
| **B** combs | ___ | 0.4:_ 0.6:_ 0.8:_ 1.2:_ | 0.4:_ 0.6:_ 0.8:_ 1.2:_ | n/a | n/a | |
| **C** satin columns | ___ | 0.6:_ 0.8:_ 1.0:_ 1.2:_ | n/a | n/a | 0.6:_ 0.8:_ 1.0:_ 1.2:_ | |
| **D** lettering | ___ | n/a | n/a | 4.0:_ 3.0:_ 2.5:_ | n/a | |
| **E** ground + strands | ___ | on ground: _  on bare: _ | n/a | n/a | on ground: _  on bare: _ | pucker under the strands? |

Arm's length read of the whole hoop: ______________________________________
"""


def write_docs(out: Path, table: dict) -> None:
    (out / "README.md").write_text(README.replace("READBACK", readback_markdown(table)), encoding="utf-8")
    sheets = []
    fabrics = ("pique + cutaway + topping", "twill + tearaway")
    n = 0
    for fab_i, fabric in enumerate(fabrics):
        for file, wt, needle in (("hairline_card_40wt.dst", 40, "75/11"),
                                 ("hairline_card_60wt.dst", 60, "65/9"),
                                 ("hairline_card_60wt.dst", 60, "70/10")):
            n += 1
            sheets.append(SHEET.format(n=n, file=file, wt=wt, needle=needle, fabric=fabric))
    (out / "scoring-sheet.md").write_text(SCORING.replace("SHEETS", "\n".join(sheets)), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(REPO / "docs" / "sewout" / "hairline-card-2026-10-12"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)
    table = {}
    for wt in WEIGHTS:
        plan, card, extra = build(wt, tmp)
        pattern = plan_to_pattern(plan)
        pattern.metadata("name", f"HAIR{wt}WT")
        data = formats.write(pattern, "dst")
        path = out / f"hairline_card_{wt}wt.dst"
        path.write_bytes(data)
        render(plan, wt, out / f"hairline_card_{wt}wt.png")
        rb = readback(path, plan, wt)
        rb["blocks_mm"] = {k: [round(v, 1) for v in box] for k, box in card.boxes.items()}
        rb["lettering"] = extra["lettering"]
        table[f"{wt}wt"] = rb
        print(json.dumps(rb))
    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()
    (out / "readback.json").write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    (out / "readback.md").write_text(readback_markdown(table), encoding="utf-8")
    write_docs(out, table)
    return 0


def readback_markdown(table: dict) -> str:
    """The read-back table the README quotes (pystitch reading the DST back)."""
    cols = list(table)
    rows = [
        ("file", lambda r: f"`{r['file']}` ({r['bytes']:,} bytes)"),
        ("stitches in the file / in the plan", lambda r: f"{r['stitches_file']:,} / {r['stitches_plan']:,}"),
        ("colour changes in the file / planned", lambda r: f"{r['colour_changes_file']} / {r['colour_changes_plan']}"),
        ("extent (mm), x by y", lambda r: f"{r['extent_mm'][0]} x {r['extent_mm'][1]}"),
        ("x range / y range (mm)", lambda r: f"{r['x_range_mm']} / {r['y_range_mm']}"),
        ("inside 100 x 100 mm", lambda r: "yes" if r["within_hoop"] else "NO"),
        ("longest move (mm; the writer splits above 12.1)", lambda r: r["longest_move_mm"]),
        ("stitches under 1.0 mm that are not 0.8 mm lock legs", lambda r: r["under_1mm_not_lock"]),
        ("  of those, outside the expected places", lambda r: r["short_unexpected"]),
        ("0.8 mm lock-leg stitches", lambda r: r["lock_legs_0p8"]),
    ]
    out = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for label, fn in rows:
        out.append(f"| {label} | " + " | ".join(str(fn(table[c])) for c in cols) + " |")
    out += ["", "Stitches under 1.0 mm, by where they are:", "",
            "| where | " + " | ".join(cols) + " | why |", "|---|" + "---|" * len(cols) + "---|"]
    keys = sorted({k for c in cols for k in table[c]["short_by_block"]})
    for k in keys:
        out.append(f"| {k} | " + " | ".join(str(table[c]["short_by_block"].get(k, 0)) for c in cols)
                   + f" | {EXPECTED_SHORT.get(k, 'NOT EXPECTED')} |")
    out += ["", "Stitches per colour stop:", "", "| stop | thread | " + " | ".join(f"{c} stitches (thread m)" for c in cols) + " |",
            "|---|---|" + "---|" * len(cols)]
    for i, s in enumerate(table[cols[0]]["stops"]):
        out.append(f"| {s['stop']} | {s['thread']} | " + " | ".join(
            f"{table[c]['stops'][i]['stitches']:,} ({table[c]['stops'][i]['thread_m']})" for c in cols) + " |")
    out += ["", "Block boxes in the hoop (mm, x0 y0 x1 y1, centre of the card at 0, 0):", "",
            "| block | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for k in sorted(table[cols[0]]["blocks_mm"]):
        out.append(f"| {k} | " + " | ".join(str(table[c]["blocks_mm"][k]) for c in cols) + " |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
