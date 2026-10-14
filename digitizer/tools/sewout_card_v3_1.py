"""The sew-out card, v3.1: v3 plus the small-lettering skeleton arms and the lettering-ends check (2026-10-13).

    # 1. cut the pieces out of their digitizes (minutes and gigabytes each: ONE
    #    process at a time, one arm per call)
    python -m tools.sewout_card_v3_1 --cut today        # Fremont 81 mm Hat, everything pinned OFF
    python -m tools.sewout_card_v3_1 --cut skel         # + small_lettering_skeleton, default floor
    python -m tools.sewout_card_v3_1 --cut skel073      # + floor 0.73
    python -m tools.sewout_card_v3_1 --cut ends_on      # + both lettering-ends flags
    python -m tools.sewout_card_v3_1 --cut ent_skel073  # enthusiast 80 mm: cut FIRST, it names the box
    python -m tools.sewout_card_v3_1 --cut ent_today
    python -m tools.sewout_card_v3_1 --cut becker_off   # Becker 80 mm: MARINE
    python -m tools.sewout_card_v3_1 --cut becker_on
    # 2. build the card (no digitize; reads the committed cuts)
    python -m tools.sewout_card_v3_1 [--out ../docs/sewout/card-v3-2026-10-13]

Kent ruled (2026-10-13): card v3 waits for the skeleton-run arm (#913,
`cfg.small_lettering_skeleton`, merged, default OFF), so v3.1 is v3 with it added.
It sits in v3's folder beside v3's files (`card_v3_40wt.*`, kept for history) and is
written as `card_v3_1_40wt.*`. Blocks, arms in tooth order (a square wave counted
from the left; every arm is a flag set, nothing else differs):

- F3  unchanged from v3 (`sewout_card_v3.block_F3`): 2.2 mm cap APA, today /
      `small_print_floor` / `small_glyph_keep`.
- T   unchanged from v3: Fremont THE at 81 mm, today / `lettering_words` +
      `lettering_word_tiers`. The skeleton arm is NOT a third tooth: #913 says THE
      is unaffected (its T is declined on width), and the skeleton cuts of the THE
      box are checked (`the_is_unaffected`) to be point-for-point today's, so the
      arm is a duplicate and is dropped.
- N   unchanged from v3: Fremont 1895 at 81 mm, `small_glyph_keep` OFF / ON.
- G   unchanged from v3 (card v2's block G): `forbid_gap_mm` OFF / 0.4 / 0.8.
- S   NEW. The tagline EAT | STAY | PLAY at 81 mm Hat (the Studio request replay):
      1 tooth today (`small_lettering_skeleton` OFF), 2 teeth skeleton at the
      default floor (`small_lettering_skeleton_floor_mm` None = `MIN_STITCH_MM`
      1.0 mm), 3 teeth skeleton at floor 0.73 mm.
- E2  NEW. Enthusiast's "ENTERPRISES INC" at 80 mm (left chest profile, #913's
      corpus case): today / skeleton at floor 0.73. #913 flags the R of PRISES as
      reading close to an A, so the cloth has to show it.
- X   NEW, a VERIFICATION arm, not a gate (director, 2026-10-13). Fremont's E, M->O
      and N at 81 mm Hat (Kent's triage circles 5, 6, 7), then `lettering_columns_square_ends`
      + `lettering_columns_inside_connectors` OFF / ON (#907, #912).
- B   NEW, the same pair on Becker's MARINE at 80 mm left chest (the N's notch
      connector in #912).

Every flag that could move is pinned in every arm, not left to the default: the
ends flags (a flip lane is turning both ON), `small_lettering_skeleton`, its
floor, `small_glyph_keep`, `lettering_words` + `lettering_word_tiers`, and the two
small-text options that compose with the tier, `small_text_cap_mm` (#909) and
`small_text_restore_mm` (#911, "true size"), both OFF. 40 wt only.
Everything goes through `digitizer_service.formats.write` (pystitch) and is read
back with pystitch; never the browser's DST codec. EVERY NUMBER HERE IS A
CANDIDATE UNTIL KENT SEWS IT (ROADMAP gate 1). No engine change. No new client
artwork: both logos are already in the repo (`testdata/`).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
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
from digitizer_core.stitches import StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402

REPO = v3.REPO
HOOP_MM = v3.HOOP_MM
WT = 40
MAX_RECORD_MM = v3.MAX_RECORD_MM
NAME = "card_v3_1_40wt"
DEFAULT_OUT = v3.DEFAULT_OUT                     # the same folder as v3
DEFAULT_RENDERS = REPO / "docs" / "renders" / "claude-sewout-card-v3-1"
STEM = "cut31_"                                  # v3's own `cut_*.json` are left alone
STOP_ORDER, STOPS = v2.STOP_ORDER, v2.STOPS

# --- the cuts ---------------------------------------------------------------------------------

#: Every flag that could move a piece, pinned OFF. An arm changes only what it names.
PINS = {
    "small_glyph_keep": False,
    "small_lettering_skeleton": False,
    "small_lettering_skeleton_floor_mm": None,   # None = machine.MIN_STITCH_MM, 1.0 mm
    "small_text_cap_mm": None,                   # #909, OFF
    "small_text_restore_mm": None,               # #911, OFF
    "bean_letter_max_stroke_mm": None,           # #911's companions, OFF
    "bean_letter_stitch_mm": None,
    "lettering_words": False,
    "lettering_word_tiers": False,
    "lettering_columns_square_ends": False,      # #907
    "lettering_columns_inside_connectors": False,  # #912
}
ENDS_ON = {"lettering_columns_square_ends": True, "lettering_columns_inside_connectors": True}
SKEL = {"small_lettering_skeleton": True}

#: Fremont replay arms: the Studio request at 81 mm on a Hat plus PINS plus these.
CUT_ARMS = {
    "today": dict(PINS),
    "skel": {**PINS, **SKEL},
    "skel073": {**PINS, **SKEL, "small_lettering_skeleton_floor_mm": 0.73},
    "ends_on": {**PINS, **ENDS_ON},
}
#: Boxes cut from every Fremont digitize: key -> fremont_triage.ROIS key. A piece is
#: every non-white run lying wholly inside the box grown by CUT_MARGIN_MM. S is the
#: tagline (new); T is cut only to prove the skeleton arm is a duplicate there.
BOXES = {"S": "tagline", "T": "the"}
CUT_MARGIN_MM = 0.8
#: Fremont letters cut by SHAPE ID (the triage census of the 81 mm Hat replay;
#: Kent's circles 5, 6, 7): the row "HOTEL FREMONT" is 6.5 mm caps, so a box
#: would catch neighbours. E = HOTEL's E; MON = FREMONT's M, O, N in order.
ENDS_SHAPES = {
    "E": ("Se394be84",),
    "MON": ("S9a48e915", "Se645801a", "Sd4bf6420"),
}
FREMONT_TOTALS = {"today": (15306, 44), "skel": (15124, 44), "skel073": (14886, 44), "ends_on": (15320, 45)}

#: Enthusiast, "ENTERPRISES INC": digitized as #913's corpus does (80 mm, left
#: chest, 40 wt), cut to the box of the glyphs the tier is OFFERED.
ENT_FILE = "photo/enthusiast_logo.png"
ENT_WIDTH_MM = 80.0
ENT_GARMENT = "left_chest"
ENT_ARMS = {
    "ent_today": dict(PINS),
    "ent_skel073": {**PINS, **SKEL, "small_lettering_skeleton_floor_mm": 0.73},
}
ENT_MARGIN_MM = 0.8
ENT_TOTALS = {"ent_today": (2428, 8), "ent_skel073": (2102, 8)}

#: Becker MARINE, 80 mm left chest (#912's corpus case): six Column-lane letters,
#: M A R I N E in order, by shape id (asserted present in both arms).
BECKER_FILE = "becker_marine_logo.png"
BECKER_WIDTH_MM = 80.0
BECKER_GARMENT = "left_chest"
BECKER_ARMS = {"becker_off": dict(PINS), "becker_on": {**PINS, **ENDS_ON}}
BECKER_SHAPES = ("Saee8fbe5", "Sff8aab95", "S3a506002", "Sfac22dc3", "Sf795e8d1", "S714b55d9")
BECKER_TOTALS = {"becker_off": (6011, 22), "becker_on": (6150, 25)}

ALL_CUTS = list(CUT_ARMS) + list(ENT_ARMS) + list(BECKER_ARMS)


def _points(r) -> list:
    return [[round(q[0], 4), round(q[1], 4)] for q in r.points]


def _rec(b, r) -> dict:
    return {"kind": r.kind, "jump": bool(r.jump), "trim": bool(r.trim), "shape_id": r.shape_id,
            "rgb": [int(v) for v in b.rgb], "points": _points(r)}


def _runs_in_box(plan, box, margin):
    gx0, gy0, gx1, gy1 = box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin
    inside, crossing = [], []
    for b in plan.blocks:
        if min(b.rgb) >= v3.WHITE_MIN:
            continue
        for r in b.runs:
            xs = [q[0] for q in r.points]
            ys = [q[1] for q in r.points]
            if min(xs) >= gx0 and max(xs) <= gx1 and min(ys) >= gy0 and max(ys) <= gy1:
                inside.append(_rec(b, r))
            elif max(xs) >= gx0 and min(xs) <= gx1 and max(ys) >= gy0 and min(ys) <= gy1:
                crossing.append({"kind": r.kind, "shape_id": r.shape_id, "n_points": len(r.points),
                                 "bbox_mm": [round(min(xs), 2), round(min(ys), 2),
                                             round(max(xs), 2), round(max(ys), 2)]})
    return inside, crossing


def _runs_of(plan, ids):
    """Every run of these shapes, in plan order (all kinds: underlay, satin, travel)."""
    return [_rec(b, r) for b in plan.blocks for r in b.runs if r.shape_id in ids]


def _write(cuts: Path, arm: str, out: dict) -> Path:
    cuts.mkdir(parents=True, exist_ok=True)
    path = cuts / f"{STEM}{arm}.json"
    path.write_text(json.dumps(out), encoding="utf-8")
    return path


def cut_fremont(arm: str, cuts: Path, design_dir: Path | None = None) -> Path:
    """Digitize the Fremont fixture as the Studio does (81 mm, Hat) with this
    arm's flags; save the tagline and THE boxes and the E / MON letters."""
    from tools import fremont_triage as ft
    t = time.time()
    run = ft.run_arm("main", ft.KENT_WIDTH_MM, None, preflight=False, overrides=dict(CUT_ARMS[arm]))
    plan, p = run["plan"], run["gen"].p
    out = {"arm": arm, "overrides": CUT_ARMS[arm], "width_mm": ft.KENT_WIDTH_MM, "garment_id": "hat_front",
           "stitches_whole": plan.stats.stitch_count, "trims_whole": plan.stats.trims,
           "size_mm_whole": [round(v, 2) for v in plan.stats.size_mm], "boxes": {}}
    for key, roi in BOXES.items():
        box = ft.roi_mm(p, ft.ROIS[roi])
        inside, crossing = _runs_in_box(plan, box, CUT_MARGIN_MM)
        out["boxes"][key] = {"roi": roi, "box_mm": [round(v, 3) for v in box], "runs": inside,
                             "crossing_runs_dropped": len(crossing), "crossing_runs": crossing}
        print(f"{arm}/{key}: {len(inside)} runs, {sum(len(r['points']) for r in inside)} points, "
              f"{len(crossing)} crossing dropped", flush=True)
    for key, ids in ENDS_SHAPES.items():
        runs = _runs_of(plan, set(ids))
        seen = {r["shape_id"] for r in runs}
        assert seen == set(ids), (arm, key, sorted(seen), ids)     # ids stable across arms
        out["boxes"][key] = {"shapes": list(ids), "runs": runs}
        print(f"{arm}/{key}: {len(runs)} runs, {sum(len(r['points']) for r in runs)} points", flush=True)
    if design_dir is not None:
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / f"fremont31_{arm}.json").write_text(json.dumps(run["design"]), encoding="utf-8")
    path = _write(cuts, arm, out)
    print(f"{arm}: {plan.stats.stitch_count:,} stitches, {plan.stats.trims} trims "
          f"(expected {FREMONT_TOTALS[arm]}), {time.time() - t:.0f} s -> {path}", flush=True)
    return path


def cut_enthusiast(arm: str, cuts: Path) -> Path:
    """Digitize enthusiast_logo.png at 80 mm left chest and save the runs inside
    the box of the glyphs the skeleton tier is OFFERED (read from the
    `ent_skel073` run, which is cut first; the OFF arm offers nothing, so both
    arms use that box)."""
    from digitizer_core.pipeline import digitize
    from tools import small_lettering_skeleton as sls
    t = time.time()
    cfg = PipelineConfig(target_width_mm=ENT_WIDTH_MM, garment_id=ENT_GARMENT, **ENT_ARMS[arm])
    log: dict = {}
    with sls.spy_skeleton(log):
        result, plan = digitize(ROOT / "testdata" / ENT_FILE, cfg)
    if ENT_ARMS[arm]["small_lettering_skeleton"]:
        by = {r.shape_id: r for r in result.regions}
        bounds = [by[s].polygon.bounds for s in log if s in by]
        box = [min(b[0] for b in bounds), min(b[1] for b in bounds),
               max(b[2] for b in bounds), max(b[3] for b in bounds)]
    else:
        box = json.loads((cuts / f"{STEM}ent_skel073.json").read_text(encoding="utf-8"))["offered_box_mm"]
    inside, crossing = _runs_in_box(plan, box, ENT_MARGIN_MM)
    out = {"arm": arm, "overrides": ENT_ARMS[arm], "width_mm": ENT_WIDTH_MM, "garment_id": ENT_GARMENT,
           "file": ENT_FILE, "stitches_whole": plan.stats.stitch_count, "trims_whole": plan.stats.trims,
           "size_mm_whole": [round(v, 2) for v in plan.stats.size_mm],
           "offered": len(log), "skeleton_sewn": sum(1 for r in log.values() if not r["empty"]),
           "declined": sorted(str(r["declined"]) for r in log.values() if r["empty"]),
           "offered_box_mm": [round(v, 3) for v in box],
           "boxes": {"E2": {"box_mm": [round(v, 3) for v in box], "runs": inside,
                            "crossing_runs_dropped": len(crossing), "crossing_runs": crossing}}}
    path = _write(cuts, arm, out)
    print(f"{arm}: offered {out['offered']}, skeleton {out['skeleton_sewn']}, box {out['offered_box_mm']}, "
          f"{len(inside)} runs, {sum(len(r['points']) for r in inside)} points, {len(crossing)} crossing "
          f"dropped; whole {plan.stats.stitch_count:,} stitches, {plan.stats.trims} trims "
          f"(expected {ENT_TOTALS[arm]}), {time.time() - t:.0f} s -> {path}", flush=True)
    return path


def cut_becker(arm: str, cuts: Path) -> Path:
    """Digitize Becker's MARINE logo at 80 mm left chest; save the six letters."""
    from digitizer_core.pipeline import digitize
    t = time.time()
    cfg = PipelineConfig(target_width_mm=BECKER_WIDTH_MM, garment_id=BECKER_GARMENT, **BECKER_ARMS[arm])
    _result, plan = digitize(ROOT / "testdata" / BECKER_FILE, cfg)
    runs = _runs_of(plan, set(BECKER_SHAPES))
    seen = {r["shape_id"] for r in runs}
    assert seen == set(BECKER_SHAPES), (arm, sorted(seen))
    out = {"arm": arm, "overrides": BECKER_ARMS[arm], "width_mm": BECKER_WIDTH_MM, "garment_id": BECKER_GARMENT,
           "file": BECKER_FILE, "stitches_whole": plan.stats.stitch_count, "trims_whole": plan.stats.trims,
           "size_mm_whole": [round(v, 2) for v in plan.stats.size_mm],
           "boxes": {"B": {"shapes": list(BECKER_SHAPES), "runs": runs}}}
    path = _write(cuts, arm, out)
    print(f"{arm}: {len(runs)} runs, {sum(len(r['points']) for r in runs)} points; whole "
          f"{plan.stats.stitch_count:,} stitches, {plan.stats.trims} trims (expected {BECKER_TOTALS[arm]}), "
          f"{time.time() - t:.0f} s -> {path}", flush=True)
    return path


def load_cut(cuts: Path, arm: str, box: str) -> dict:
    return json.loads((cuts / f"{STEM}{arm}.json").read_text(encoding="utf-8"))["boxes"][box]


def load_cut_file(cuts: Path, arm: str) -> dict:
    return json.loads((cuts / f"{STEM}{arm}.json").read_text(encoding="utf-8"))


# --- the card -----------------------------------------------------------------------------

LETTERS = {**hc.LETTERS, **v3.LETTERS,
           "S": [(3, 0), (0, 0), (0, 2), (3, 2), (3, 4), (0, 4)],
           "X": [(0, 0), (3, 4), (1.5, 2), (3, 0), (0, 4)]}

#: block -> arms in tooth order (1 tooth, 2 teeth, ...). The piece key is `block:arm`.
#: F3, T, N, G are v3's, unchanged (`v3.BLOCKS`).
BLOCKS = {
    **v3.BLOCKS,
    "S": ("today", "floor-1.0", "floor-0.73"),
    "E2": ("today", "floor-0.73"),
    "X": ("ends-off", "ends-on"),
    "B": ("ends-off", "ends-on"),
}
INDEX_STRIP = {**v3.INDEX_STRIP, "S": "S", "E2": "E", "X": "X", "B": "B"}
#: where each new piece comes from: block -> arm -> (cut file arm, [box keys, laid out left to right])
SOURCES = {
    "S": {"today": ("today", ["S"]), "floor-1.0": ("skel", ["S"]), "floor-0.73": ("skel073", ["S"])},
    "E2": {"today": ("ent_today", ["E2"]), "floor-0.73": ("ent_skel073", ["E2"])},
    "X": {"ends-off": ("today", ["E", "MON"]), "ends-on": ("ends_on", ["E", "MON"])},
    "B": {"ends-off": ("becker_off", ["B"]), "ends-on": ("becker_on", ["B"])},
}
#: which way a new block's arms run on the card (the tall ones stack)
ORIENT = {"S": "h", "E2": "h", "X": "v", "B": "v"}
GARMENT_OF = {"S": "hat_front", "E2": ENT_GARMENT, "X": "hat_front", "B": BECKER_GARMENT}
HEADER_LEFT = 8.0        # the index strip sits left of a new block's arms (3 mm wide), not above them
ARM_TOP = 2.0            # first arm's top, under its teeth label
H_GAP = 4.0              # between arms side by side
V_GAP = 3.2              # between stacked arms (a teeth label sits in it)
GROUP_GAP = 3.0          # between the letter groups of one arm (X: E | MON)
NEW_DIGITIZED = tuple(f"{b}:{a}:" for b in ("S", "E2", "X", "B") for a in BLOCKS[b])


class Card(v3.CardV3):
    """v3's card with v3.1's index letters and its own digitized-piece prefixes
    (an arm's `block:arm:` prefix, so a label or index strip never matches)."""

    DIGITIZED = v3.CardV3.DIGITIZED + NEW_DIGITIZED

    def index(self, key: str, x0: float, y0: float, width: float) -> None:
        self.add(0, hc.corners([(x0 + a, y0 + b) for a, b in LETTERS[key]]), f"{key}:index")
        self.add(0, hc.corners([(x0 + 5.0, y0 + 5.0), (x0 + width, y0 + 5.0)]), f"{key}:rule")

    def strip(self, key: str, x0: float, y0: float) -> None:
        """A new block's index letter alone (no rule): its arms start to the right of it."""
        self.add(0, hc.corners([(x0 + a, y0 + b) for a, b in LETTERS[key]]), f"{key}:index")


def _runs(recs: list[dict]) -> list[StitchRun]:
    return [StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=True, trim=False,
                      shape_id=r["shape_id"]) for r in recs]


def place_groups(c: Card, groups: list[list[StitchRun]], x0: float, y0: float, blk: str, arm: str,
                 ) -> tuple[float, float, float, float]:
    """Put one arm's letter groups side by side, GROUP_GAP apart, top-left at
    (x0, y0), their relative heights kept (one baseline). Returns the box."""
    dy = y0 - min(p[1] for g in groups for r in g for p in r.points)
    cur = x0
    xs, ys = [], []
    for g in groups:
        gx0 = min(p[0] for r in g for p in r.points)
        gx1 = max(p[0] for r in g for p in r.points)
        dx = cur - gx0
        for r in g:
            c.add_run(0, StitchRun(points=[(px + dx, py + dy) for px, py in r.points], kind=r.kind,
                                   jump=True, trim=False, shape_id=f"{blk}:{arm}:{r.kind}"))
            xs += [p[0] + dx for p in r.points]
            ys += [p[1] + dy for p in r.points]
        cur += (gx1 - gx0) + GROUP_GAP
    box = (min(xs), min(ys), max(xs), max(ys))
    c.arms[f"{blk}:{arm}"] = box
    return box


def block_new(c: Card, blk: str, x0: float, y0: float, cuts: Path, report: list) -> None:
    """A new block (S, E2, X, B): the index letter at the left, the arms beside it."""
    c.strip(INDEX_STRIP[blk], x0, y0)
    x, y = x0 + HEADER_LEFT, y0 + ARM_TOP
    right, bottom = x0 + 3.0, y0 + 4.0
    for k, arm in enumerate(BLOCKS[blk], start=1):
        cut, keys = SOURCES[blk][arm]
        data = load_cut_file(cuts, cut)
        groups = [_runs(data["boxes"][key]["runs"]) for key in keys]
        box = place_groups(c, groups, x, y, blk, arm)
        c.add(0, hc.teeth(x, y - 0.8, k), f"{blk}:label:{arm}")
        report.append({"block": blk, "arm": arm, "cut": cut, "boxes": keys, "overrides": data["overrides"],
                       "garment_id": data.get("garment_id", GARMENT_OF[blk]),
                       "runs": sum(len(g) for g in groups),
                       "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
        right, bottom = max(right, box[2]), max(bottom, box[3])
        if ORIENT[blk] == "h":
            x = box[2] + H_GAP
        else:
            y = box[3] + V_GAP
    c.boxes[blk] = (x0, y0, right, bottom)


def the_is_unaffected(cuts: Path) -> dict:
    """#913 says THE is unaffected by the skeleton tier. Prove it on the cuts:
    the THE box of each skeleton arm is point-for-point today's (and today's is
    v3's own T cut). If so the T block needs no skeleton arm."""
    def pts(file_arm, box="T"):
        return [(r["kind"], r["points"]) for r in load_cut(cuts, file_arm, box)["runs"]]
    today = pts("today")
    v3_today = [(r["kind"], r["points"]) for r in v3.load_cut(cuts, "today", "T")["runs"]]
    return {"skel_same_as_today": pts("skel") == today, "skel073_same_as_today": pts("skel073") == today,
            "today_same_as_v3_cut": today == v3_today, "runs": len(today),
            "points": sum(len(p) for _k, p in today)}


def build(cuts: Path) -> tuple[StitchPlan, Card, dict]:
    c = Card(WT)
    report: list[dict] = []
    v3.block_F3(c, 0.0, 0.0, report)
    v3.block_cut(c, "T", c.boxes["F3"][2] + 6.0, 0.0, 26.0, cuts, report)
    v3.block_cut(c, "N", c.boxes["T"][2] + 6.0, 0.0, 20.0, cuts, report)
    row1 = max(c.boxes[k][3] for k in ("F3", "T", "N"))
    v2.block_G(c, 0.0, row1 + 5.0, report)
    block_new(c, "X", c.boxes["G"][2] + 6.0, row1 + 5.0, cuts, report)      # right of G
    row2 = max(c.boxes[k][3] for k in ("G", "X"))
    block_new(c, "S", 0.0, row2 + 4.0, cuts, report)
    block_new(c, "B", 0.0, c.boxes["S"][3] + 4.0, cuts, report)
    block_new(c, "E2", 0.0, c.boxes["B"][3] + 4.0, cuts, report)
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
    return plan, c, {"pieces": report, "offset_mm": (round(cx, 3), round(cy, 3)),
                     "the_is_unaffected": the_is_unaffected(cuts)}


# --- renders ------------------------------------------------------------------------------------

def render(plan: StitchPlan, out: Path, ppm: float = 12.0) -> np.ndarray:
    design = plan_to_design(plan, name=f"card v3.1 {WT} wt")
    img = stitchviz.render_design(design, px_per_mm=ppm, thread_mm=machine.thread_profile(WT).width_mm)
    cv2.imwrite(str(out), img)
    return img


#: (title, piece keys, "h" arms side by side | "v" stacked). Tall pieces stack in the sheet too.
ROWS = (
    ("F3 small cap, 2.2 mm APA: today | small_print_floor | small_glyph_keep (1 / 2 / 3 teeth)",
     ("F3:today", "F3:floor", "F3:keep"), "h"),
    ("T THE at 81 mm: today | lettering_words + lettering_word_tiers (1 / 2 teeth)",
     ("T:today", "T:wordtier"), "h"),
    ("N 1895 at 81 mm: small_glyph_keep OFF | ON (1 / 2 teeth)", ("N:keep-off", "N:keep-on"), "h"),
    ("G forbid gap: OFF | 0.4 | 0.8 (bars at 0.3 / 0.6 / 1.0 mm; 1 / 2 / 3 teeth)",
     ("G:gap-off", "G:gap-0.4", "G:gap-0.8"), "h"),
    ("S tagline EAT | STAY | PLAY at 81 mm Hat: today | skeleton, floor 1.0 | skeleton, floor 0.73 (1 / 2 / 3 teeth)",
     ("S:today", "S:floor-1.0", "S:floor-0.73"), "v"),
    ("E2 enthusiast ENTERPRISES INC at 80 mm: today | skeleton, floor 0.73 (1 / 2 teeth)",
     ("E2:today", "E2:floor-0.73"), "v"),
    ("X Fremont E, M->O, N at 81 mm Hat: square_ends + inside_connectors OFF | ON (1 / 2 teeth)",
     ("X:ends-off", "X:ends-on"), "h"),
    ("B Becker MARINE at 80 mm: square_ends + inside_connectors OFF | ON (1 / 2 teeth)",
     ("B:ends-off", "B:ends-on"), "v"),
)


def _vstack(imgs, gap=14):
    w = max(i.shape[1] for i in imgs)
    out = []
    for i in imgs:
        out += [np.hstack([i, np.full((i.shape[0], w - i.shape[1], 3), 255, np.uint8)]),
                np.full((gap, w, 3), 255, np.uint8)]
    return np.vstack(out[:-1])


def panel(plan: StitchPlan, card: Card, out: Path, ppm: float = 60.0) -> None:
    """One sheet: every arm cropped from the card at `ppm` px/mm (thread at the
    laid width), the arms of a block side by side (or stacked, for the wide ones)."""
    design = plan_to_design(plan, name=f"card v3.1 {WT} wt")
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

    rows = []
    for title, keys, how in ROWS:
        crops = [crop(card.arms[k]) for k in keys]
        rows.append(v2._label(v2._hstack(crops) if how == "h" else _vstack(crops), title))
    w = max(r.shape[1] for r in rows)
    rows = [np.hstack([r, np.full((r.shape[0], w - r.shape[1], 3), 255, np.uint8)]) for r in rows]
    cv2.imwrite(str(out), np.vstack([np.vstack([r, np.full((16, w, 3), 255, np.uint8)]) for r in rows]))


# --- the file checks --------------------------------------------------------------------------------

def sew_minutes(rb: dict) -> float:
    """An ESTIMATE, not a measurement: stitches at 650 spm, 3 s per trim, 30 s per colour change."""
    return round(rb["stitches_file"] / 650.0 + rb["trims"] * 0.05 + rb["colour_changes_file"] * 0.5, 1)


def readback(path: Path, plan: StitchPlan, card: Card) -> dict:
    """Read the DST back with pystitch (card v2's read-back) and add, per block,
    the stitches and extents the FILE holds, so a decoded file can be compared
    with the plan block by block."""
    rb = v2.readback(path, plan, WT, card)
    rb["sew_minutes_est"] = sew_minutes(rb)
    rb["decoded_pieces"] = decode_blocks(path, plan, card)
    return rb


PIECE_MARGIN_MM = 0.3      # a piece owns the file stitches inside its box grown by this


def decode_blocks(path: Path, plan: StitchPlan, card: Card) -> dict:
    """Read-back, piece by piece: DECODE the written DST and, for every arm, count
    the STITCH records inside its box and measure their extent; do the same on the
    in-memory pattern the file was written from. A piece that lost stitches or
    moved in the write shows here. Arms are 3 mm or more apart (the test checks),
    so a file stitch has one owner or none (index strips and labels).
    -> {piece: {"file": {"stitches", "w", "h"}, "plan": {...}, "box": [w, h]}}"""
    mask = pystitch.COMMAND_MASK

    def stitches(pat):
        return [(x / 10.0, y / 10.0) for x, y, cmd in pat.stitches if (cmd & mask) == pystitch.STITCH]

    f, m = stitches(pystitch.read_dst(str(path))), stitches(plan_to_pattern(plan))
    pys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
    fy = [y for _x, y in f]
    same = abs(min(fy) - min(pys)) + abs(max(fy) - max(pys))
    flip = abs(min(fy) + max(pys)) + abs(max(fy) + min(pys))
    sign = 1.0 if same <= flip else -1.0          # the file's y axis against the plan's

    def measure(pts, box):
        x0, y0, x1, y1 = box
        sel = [(x, sign * y) for x, y in pts if x0 - PIECE_MARGIN_MM <= x <= x1 + PIECE_MARGIN_MM
               and y0 - PIECE_MARGIN_MM <= sign * y <= y1 + PIECE_MARGIN_MM]
        if not sel:
            return {"stitches": 0, "w": 0.0, "h": 0.0}
        xs, ys = [p[0] for p in sel], [p[1] for p in sel]
        return {"stitches": len(sel), "w": round(max(xs) - min(xs), 1), "h": round(max(ys) - min(ys), 1)}

    return {key: {"file": measure(f, box), "plan": measure(m, box),
                  "box": [round(box[2] - box[0], 1), round(box[3] - box[1], 1)]}
            for key, box in sorted(card.arms.items())}


def readback_markdown(rb: dict) -> str:
    text = v3.readback_markdown(rb)
    text += (f"\nSew time, estimated (650 spm, 3 s per trim, 30 s per colour change): about "
             f"{rb['sew_minutes_est']} minutes.\n")
    text += ("\nRead back piece by piece (the DST decoded with pystitch: STITCH records inside each arm's box, "
             "against the in-memory pattern the file was written from; extent = width x height in mm):\n\n"
             "| piece | stitches in the file | in the plan | extent in the file | extent in the plan |\n"
             "|---|---|---|---|---|\n")
    for k, d in sorted(rb["decoded_pieces"].items()):
        text += (f"| {k} | {d['file']['stitches']:,} | {d['plan']['stitches']:,} | "
                 f"{d['file']['w']} x {d['file']['h']} | {d['plan']['w']} x {d['plan']['h']} |\n")
    return text


def pair_notes(rb: dict) -> str:
    """Per-arm facts read off the file; the sewn effect is the sew-out's to say."""
    n = rb["stitches_by_piece"]
    lines = ["| piece | arm | stitches | vs arm 1 |", "|---|---|---|---|"]
    for blk, arms in BLOCKS.items():
        base = n[f"{blk}:{arms[0]}"]
        for arm in arms:
            v = n[f"{blk}:{arm}"]
            lines.append(f"| {blk} | {arm} | {v:,} | {'-' if arm == arms[0] else f'{v - base:+,}'} |")
    return "\n".join(lines) + "\n"


# --- docs ---------------------------------------------------------------------------------------------

README = """# Sew-out card v3.1, 2026-10-13

One DST file (**40 wt**) for the questions Kent's Hotel Fremont 81 mm Hat
report left open, **plus the small-lettering skeleton arms** that card v3 was
waiting on (#913, merged, `cfg.small_lettering_skeleton`, default OFF), **plus a
lettering-ends check**. Each question is a block of arms sewn **side by side**
(or stacked, for the wide ones) and labelled with teeth. You sew it once, read
each block on `scoring-sheet.md`, and that settles several ROADMAP gate-1
questions together. **Every number on this card is a candidate until you sew
it.** Nothing here is a setting.

SIZE_MM mm, STITCHES stitches, TRIMS trims, COLOURS colour stops (two cones),
allow roughly MINUTES minutes (an estimate from the stitch count at 650 spm, not
a measurement). **Inside a 4 x 4 in hoop (100 x 100 mm).**

**This card replaces v3.** Card v3 (`card_v3_40wt.dst`, its README, scoring
sheet and read-back, now `*-v3.*`) is kept in this folder for history; do not
sew both: v3.1 carries every v3 block unchanged (F3, T, N, G) and adds S, E2,
X and B. It also does not replace card v1 (`../hairline-card-2026-10-12/`) or
card v2 (`../card-v2-2026-10-13/`); neither has been sewn (MASTER_SCOPE
"Waiting on Kent" 44, 45, 47). v3.1 carries v2's block G as v3 did.

## What is in this folder

| File | What it is |
|---|---|
| `card_v3_1_40wt.dst` | the card, **40 wt** thread. |
| `card_v3_1_40wt.png` | what the file looks like, thread drawn at the laid width, 12 px/mm. A picture of the file, not of cloth. |
| `card_v3_1_40wt_blocks.png` | every arm cropped at 60 px/mm, the arms of a block side by side (stacked for S, E2 and B), for comparing them before you sew. |
| `scoring-sheet.md` | the readout sheet: one table per block. Print it. |
| `cuts/cut31_*.json` | the runs the new blocks sew: Fremont tagline / E / M, O, N, enthusiast's line, Becker's MARINE (see below). `cuts/cut_*.json` are v3's T and N. |
| `readback.md`, `readback.json` | the file checks, also quoted below. |
| `card_v3_40wt.*`, `README-v3.md`, `scoring-sheet-v3.md`, `readback-v3.*` | card v3, for history. |

The file is written by `python -m tools.sewout_card_v3_1` (in `digitizer/`)
through the service's export path (pystitch), not the browser's DST codec,
and read back with pystitch. The test is
`digitizer/tests/test_sewout_card_v3_1.py`.

## What you need

- **Fabric:** the **cap** (or a scrap of the same structured twill) is the
  honest test. F3, T, N, S and X are digitized on the **Hat profile** (0.4 mm
  pull per side), as your Fremont job was. **E2 and B are digitized on the
  left-chest profile** (#913's and #912's own corpus runs: enthusiast and
  Becker at 80 mm), so a cap is a harder test of them than they were made
  for; read them as a flag check, not as a size for the hat. Block G is the
  default profile, as on card v2.
- **Stabilizer:** the backing you used for the Fremont hat; else tearaway
  (medium) under twill, no topping.
- **Thread, two cones:** a **dark** (black or navy) and a **light** (white or
  cream), the same maker and weight. 40 wt: **Madeira Polyneon No. 40**, or
  Isacord 40. Every new block sews in the **dark** cone.
- **Needle:** 40 wt **75/11**. **Bobbin:** the same for every sew-out.
- The design is SIZE_MM mm, inside a 100 x 100 mm field (a 4 x 4 in hoop).
  It is tall: **hoop it with the whole card inside the field and trace the
  outline before sewing.**

## How to sew it

1. Load `card_v3_1_40wt.dst`. **Put the needle at the centre of the card**: the
   file's origin is the middle of the SIZE_MM mm box. Trace the outline.
2. Turn **trims on**. The file cuts between pieces and wherever the
   digitizer cut inside one.
3. **Three colour stops** (two cones; the machine asks for the dark one twice):
   1. **Stop 1, dark.** Every index strip and label, blocks F3, T, N, S, E2, X
      and B, and the **fill** of each block G arm.
   2. **Stop 2, light.** Block G's **bars**.
   3. **Stop 3, dark.** Block G's two edge runs round each fill (short).
4. Count **thread breaks** from the machine's counter, per block if you can.
   S's two skeleton arms put 0.73 mm and 1.0 mm stitches in a 0.4 mm line:
   note shredding, looping and needle heat on them.
5. Do not press or steam before scoring. Photograph each block close up (a
   macro) and once at arm's length; most pieces are 2-10 mm tall.

## How to read the arms

Every block has an **index strip**: its letter sewn as a run, 4 mm tall (F for
F3, T, N, G, S, E for E2, X, B). Blocks F3, T, N and G keep v3's layout (strip
above the arms, rule under it); the new blocks S, E2, X, B put the strip to the
**left** of their arms. Arms are labelled by **teeth** (a square wave sewn
above each), counted from the left, or from the top for the stacked blocks
(X, B; and S, E2 sew left to right): **1 tooth** is the first arm named in the table
below, **2 teeth** the second, **3 teeth** the third.

![](card_v3_1_40wt.png)

## Block map

| Block | Where | Arms (1 / 2 / 3 teeth) | What it settles |
|---|---|---|---|
| **F3** | top row, left | v3's, unchanged. The word **APA**, **2.2 mm cap**, stroke about 0.23 mm. **1** today, **2** `small_print_floor` ON, **3** `small_glyph_keep` ON. | #905's recommendation 1: does `small_print_floor` / `small_glyph_keep` keep an A's triangle open at the size of Fremont's tagline? |
| **T** | top row, middle | v3's, unchanged. Fremont's **THE** at 81 mm: **1** today, **2** `lettering_words` + `lettering_word_tiers`. **No skeleton arm: THE_NOTE** | #905's recommendation 2: does the one-tier-per-word pair read as THE where today's is a blob? |
| **N** | top row, right | v3's, unchanged. Fremont's **1895** at 81 mm: **1** `small_glyph_keep` OFF, **2** ON. | Does ON read 1895 where OFF reads "098"? (#902) |
| **G** | second row, left | v3's (card v2's block G), unchanged. An 8 x 8 mm fill with three bars standing off it by 0.3 / 0.6 / 1.0 mm. **1** OFF, **2** `forbid_gap_mm` 0.4, **3** 0.8. | `forbid_gap_mm`: 0.4, 0.8, or neither. |
| **X** | second row, right (arms stacked) | **NEW, a verification arm, not a gate.** Fremont's **E** (HOTEL) and **M, O, N** (FREMONT) at 81 mm Hat: Kent's triage circles 5, 6, 7. **1** `lettering_columns_square_ends` + `lettering_columns_inside_connectors` OFF, **2** both ON (#907, #912). | Does the E's upper arm end square, does the M's vertex stand on its foot with no loop to the O, does the N's diagonal end on the baseline rather than in an ear? |
| **S** | third row | **NEW.** The tagline **EAT, bar, STAY, bar, PLAY** at 81 mm Hat (the Studio request replay, 13 glyphs, caps 2.17 mm, strokes 0.22-0.30 mm). **1** today (`small_lettering_skeleton` OFF), **2** skeleton at the default floor (`small_lettering_skeleton_floor_mm` None = `MIN_STITCH_MM`, **1.0 mm**), **3** skeleton at floor **0.73 mm**. | #913's question: does one run down the middle of each letter read better than the bean outline round it, and do 0.73 mm stitches hold (`MIN_STITCH_MM`)? #913 prices 6 glyphs sewn as skeleton runs at 1.0 and 13 offered / 11 sewn at 0.73 (its table: 4 of 13 and 11 of 13 as one run on the render). |
| **B** | fourth row (arms stacked) | **NEW, a verification arm, not a gate.** Becker's **MARINE** at 80 mm left chest (6 Column-lane letters, 13.4 mm tall): **1** both ends flags OFF, **2** both ON. | #912's N: the travel stitch across the notch at the top of the N is gone with ON. Does the N read cleaner on cloth? |
| **E2** | bottom row | **NEW.** Enthusiast's **ENTERPRISES INC** at 80 mm left chest (14 letters, 31.8 mm wide). **1** today, **2** skeleton at floor **0.73 mm**. | #913 flags that the **R of PRISES** reads close to an **A** with the tier ON (the floor-limited route closes the bowl). Does it on cloth? |

### Pinned flags (every arm; the card does not move if a default flips)

`small_glyph_keep`, `small_lettering_skeleton`, `small_lettering_skeleton_floor_mm`,
`lettering_words`, `lettering_word_tiers`, `lettering_columns_square_ends`,
`lettering_columns_inside_connectors`, `bean_letter_max_stroke_mm`,
`bean_letter_stitch_mm`, and the two small-text options that compose with the
tier: **`small_text_cap_mm` (#909) and `small_text_restore_mm` (#911, "true
size")**, both OFF, alongside the skeleton tier in S, E2 and the cuts, as
#913's table composes #909. The ends flags are being turned ON by default
elsewhere (`claude/letter-ends-on`); the cuts pin them explicitly (`cuts/cut31_*.json`
record the flag set each came from).

## What the files say about each arm (the FILE, not the cloth)

PAIRNOTES

The skeleton arms in S: the shape counts, pieces and widths are in the
read-back below; #913's table (per glyph, sewn width 0.42-0.43 mm against
0.47-0.73 mm today) is the source for what each glyph does. Declined glyphs
(E, S, T, P, L, the left A) stay the bean outline in the 1.0 mm arm. **A
counter 0.5 mm wide under a 0.40 mm thread is mostly covered (#913: 20-40%
stays bare at 0.73), so the A may read as a filled triangle in both arms: that
is the trade, and the cloth is the judge.**

## Where the new pieces come from

None of the new pieces are drawn; they are the **stitches the engine sews** for
a design that is already in the repo. The cut files hold the runs exactly as
the engine laid them (kind, points, the engine's jump and trim calls). The card
places each cut's top-left, one translation per piece, and the card's plan
keeps the engine's own jump/trim decisions for these runs (a hop under
`TRIM_AT_MM` is a float).

CUTNOTES

## The file checks (pystitch reading the DST back)

READBACK
Reproduce with `python -m tools.sewout_card_v3_1` from `digitizer/` (the cuts
are re-made with `--cut today|skel|skel073|ends_on|ent_today|ent_skel073|becker_off|becker_on`,
one process at a time, a minute to five each).

## Things to know before you sew

- **The pieces are small.** Read them under a loupe AND at arm's length, and
  score the two separately. "Looks the same at arm's length" is a finding.
- **A fat line is still 0.40 mm.** The skeleton arms in S are one pass of one
  thread down the middle of a stroke narrower than the thread; the sewn width
  is the thread's, not the stroke's. The picture is a render, not cloth.
- **The Fremont tagline is TAN in the logo** (rgb 163,150,135) with two black
  bars; every colour sews in the dark cone here: read shape, not colour.
  Two small marks beside the tagline's letters in the artwork (the banner's
  rope edge) are not on the card.
- **The cloth is not the logo's ground.** The Fremont logo's white patch is not
  on the card, so the pieces sew straight onto the cap or twill.
- **Short stitches.** The skeleton arms deliberately sew stitches down to
  1.0 mm and 0.73 mm in lettering; the index strips and labels hold the
  1.0 mm floor, and the lock legs are the engine's 0.8 mm.
- **The ends arms are a verification, not a gate.** Nothing is flipped by
  this card; if X and B show no difference on cloth, say so on the sheet.
"""

SCORING = """# Readout sheet, sew-out card v3.1

One table per block, one row per arm, for the one sew-out
(`card_v3_1_40wt.dst`, 40 wt, needle 75/11). **Thread breaks** come from the
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

(No skeleton arm: the skeleton tier leaves THE as it is.)

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

## X: Fremont E, M->O, N at 81 mm (verification: do the ends come out clean?)

Letters, left to right in the arm: **E** (HOTEL's), then **M, O, N** (FREMONT's).

| Arm | Thread breaks | E: upper arm ends square, no slanted stub (Y/N) | M: vertex stands on its foot, no wedge (Y/N) | M to O: a loop or bar across the notch (Y/N) | N: diagonal ends on the baseline, no ear (Y/N) | Free note |
|---|---|---|---|---|---|---|
| 1 tooth: both flags OFF | ___ | _ | _ | _ | _ | |
| 2 teeth: `lettering_columns_square_ends` + `lettering_columns_inside_connectors` ON | ___ | _ | _ | _ | _ | |

## S: Fremont tagline EAT | STAY | PLAY at 81 mm (does one run down the middle read?)

| Arm | Thread breaks | Thread shred / loop / needle heat (Y/N) | Reads EAT STAY PLAY at arm's length (Y/N) | Weight: letters look one thread, not fat (Y/N) | A counters read as holes (Y/N): EAT / STAY / PLAY | A crossbar reads (Y/N) | Free note |
|---|---|---|---|---|---|---|---|
| 1 tooth: today (skeleton OFF) | ___ | _ | _ | _ | E:_ S:_ P:_ | _ | |
| 2 teeth: skeleton, floor 1.0 mm | ___ | _ | _ | _ | E:_ S:_ P:_ | _ | |
| 3 teeth: skeleton, floor 0.73 mm | ___ | _ | _ | _ | E:_ S:_ P:_ | _ | |

## B: Becker MARINE at 80 mm (verification: the N's notch)

| Arm | Thread breaks | A thread or stitch across the notch at the top of the N (Y/N) | N reads cleaner than the other arm (Y/N) | Reads MARINE at arm's length (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: both flags OFF | ___ | _ | _ | _ | |
| 2 teeth: both flags ON | ___ | _ | _ | _ | |

## E2: enthusiast ENTERPRISES INC at 80 mm (does the R of PRISES read as an A?)

| Arm | Thread breaks | Reads ENTERPRISES INC at arm's length (Y/N) | R of PRISES reads R / A / unclear | Thread shred / loop / needle heat (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: today (skeleton OFF) | ___ | _ | _ | _ | |
| 2 teeth: skeleton, floor 0.73 mm | ___ | _ | _ | _ | |

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
| `small_lettering_skeleton` flip | ON | blocks S and E2: arm 2 or 3 reads better than arm 1 with no breaks, and the A crossbars and the enthusiast R survive |
| `small_lettering_skeleton_floor_mm` | None (1.0 mm) or 0.73 mm | block S: arm 3 reads better than arm 2, and its 0.73 mm stitches hold (no shred or loop); this is the question behind `MIN_STITCH_MM` = 1.0 |
| `lettering_columns_square_ends` + `lettering_columns_inside_connectors` flips | ON | blocks X and B: ON ends clean, no loop at the M, no travel across the N's notch; none is a gate |
"""


def cut_notes(cuts: Path) -> str:
    lines = ["| cut | flags on the request (beyond the pins above) | whole design | what was cut |",
             "|---|---|---|---|"]
    notes = {
        "today": "tagline box (S arm 1), THE box (checked against the skeleton arms), E and M, O, N (X arm 1)",
        "skel": "tagline box (S arm 2); THE box (check)",
        "skel073": "tagline box (S arm 3); THE box (check)",
        "ends_on": "E and M, O, N (X arm 2)",
        "ent_today": "ENTERPRISES INC (E2 arm 1)",
        "ent_skel073": "ENTERPRISES INC (E2 arm 2)",
        "becker_off": "MARINE (B arm 1)",
        "becker_on": "MARINE (B arm 2)",
    }
    allarms = {**CUT_ARMS, **ENT_ARMS, **BECKER_ARMS}
    for arm in ALL_CUTS:
        f = cuts / f"{STEM}{arm}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        diff = {k: v for k, v in allarms[arm].items() if v != PINS.get(k)}
        lines.append(f"| `{arm}` | `{diff or 'none: every flag pinned OFF'}` | {d['stitches_whole']:,} stitches, "
                     f"{d['trims_whole']} trims, {d['size_mm_whole'][0]} x {d['size_mm_whole'][1]} mm "
                     f"({d.get('garment_id', 'hat_front')}) | {notes[arm]} |")
    return "\n".join(lines) + "\n"


def write_docs(out: Path, rb: dict, cuts: Path) -> None:
    size = f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}"
    the = rb["the_is_unaffected"]
    if the["skel_same_as_today"] and the["skel073_same_as_today"]:
        the_note = (f"the skeleton tier leaves THE as it is (#913: the T is declined on width; here the THE box "
                    f"cut from the skeleton arms at both floors is point for point today's, {the['runs']} runs, "
                    f"{the['points']} points), so a skeleton arm would be a duplicate of arm 1 and is dropped.")
    else:
        the_note = "the skeleton arms DIFFER from today's here: see the cuts."
    text = (README.replace("READBACK", readback_markdown(rb)).replace("PAIRNOTES", pair_notes(rb))
            .replace("CUTNOTES", cut_notes(cuts)).replace("THE_NOTE", the_note).replace("SIZE_MM", size)
            .replace("STITCHES", f"{rb['stitches_file']:,}").replace("TRIMS", str(rb["trims"]))
            .replace("COLOURS", str(rb["colours"])).replace("MINUTES", str(rb["sew_minutes_est"])))
    (out / "README.md").write_text(text, encoding="utf-8")
    (out / "scoring-sheet.md").write_text(SCORING, encoding="utf-8")


def generate(out: Path, renders: Path | None = None, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    """Write the whole card into `out` (and the PNGs into `renders`, if given)
    from the cuts in `cuts` (default: `<out>/cuts`); returns the read-back."""
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "CARDV3.1 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    render(plan, out / f"{NAME}.png")
    panel(plan, card, out / f"{NAME}_blocks.png")
    rb = readback(path, plan, card)
    rb["pieces"] = extra["pieces"]
    rb["the_is_unaffected"] = extra["the_is_unaffected"]
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items()
                          if k not in ("pieces", "pieces_mm", "stitches_by_piece", "decoded_pieces")}))
    (out / "readback.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    (out / "readback.md").write_text(readback_markdown(rb), encoding="utf-8")
    write_docs(out, rb, cuts)
    if renders is not None:
        renders.mkdir(parents=True, exist_ok=True)
        for name in (f"{NAME}.png", f"{NAME}_blocks.png"):
            (renders / name).write_bytes((out / name).read_bytes())
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=ALL_CUTS, help="digitize this arm and save its cuts")
    ap.add_argument("--cuts", default=str(v3.DEFAULT_CUTS))
    ap.add_argument("--design-dir", help="with a Fremont --cut: also save the whole design here (not committed)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--renders", default=str(DEFAULT_RENDERS), help="copy the PNGs here too ('' to skip)")
    a = ap.parse_args(argv)
    if a.cut:
        cuts = Path(a.cuts)
        if a.cut in CUT_ARMS:
            cut_fremont(a.cut, cuts, Path(a.design_dir) if a.design_dir else None)
        elif a.cut in ENT_ARMS:
            cut_enthusiast(a.cut, cuts)
        else:
            cut_becker(a.cut, cuts)
        return 0
    generate(Path(a.out), Path(a.renders) if a.renders else None, Path(a.cuts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
