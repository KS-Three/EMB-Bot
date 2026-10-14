"""The sew-out card, v3.2: v3.1 re-cut on today's main plus the chaining block (2026-10-14).

    # 1. cut the pieces out of their digitizes (minutes and gigabytes each: ONE
    #    process at a time, one arm per call). Same eight cuts as v3.1, re-made on
    #    today's main (`cut32_*.json`), plus the owl pair.
    python -m tools.sewout_card_v3_2 --cut today        # Fremont 81 mm Hat, everything pinned OFF
    python -m tools.sewout_card_v3_2 --cut skel         # + small_lettering_skeleton, default floor
    python -m tools.sewout_card_v3_2 --cut skel073      # + floor 0.73
    python -m tools.sewout_card_v3_2 --cut ends_on      # + both lettering-ends flags
    python -m tools.sewout_card_v3_2 --cut ent_skel073  # enthusiast 80 mm: cut FIRST, it names the box
    python -m tools.sewout_card_v3_2 --cut ent_today
    python -m tools.sewout_card_v3_2 --cut becker_off   # Becker 80 mm: MARINE
    python -m tools.sewout_card_v3_2 --cut becker_on
    python -m tools.sewout_card_v3_2 --cut tn_today     # v3's own T / N cuts (THE, 1895), into cuts/tn/
    python -m tools.sewout_card_v3_2 --cut tn_wordtier
    python -m tools.sewout_card_v3_2 --cut tn_keep
    python -m tools.sewout_card_v3_2 --cut owl          # owl_kent 127 mm, line route: chain ON then chain OFF, one digitize
    #   (or --cut owl_chain_on, then --cut owl_chain_off: the ON cut names the window)
    # 2. build the card (no digitize but F3's three tiny ones; reads the committed cuts)
    python -m tools.sewout_card_v3_2 [--out ../docs/sewout/card-v3-2026-10-13]

Card v3.1 (`tools/sewout_card_v3_1.py`) stays as it was. v3.2 is its generator extended:

- Blocks F3, T, N, G, X, S, B, E2 are v3.1's, arm for arm and flag for flag, but their
  Fremont / enthusiast / Becker pieces are RE-CUT on today's main (`cut32_*.json`),
  because `digitizer_core` moved after v3.1's cuts (bean letters #922-era fixes, the
  small-lettering skeleton's second try #936, small_print_floor #923, ...). F3 is not
  a cut: it is digitized at build time, so it is today's by construction.
- O (new, hoop-fit layout below): the line route's chaining, `cfg.hairline_lines_chain`
  (#917, default OFF; Kent 2026-10-14: stays OFF until this sew-out), on `owl_kent.jpg`
  at 127 mm, 40 wt, the photo lane (#917's route). 1 tooth chain OFF (every hop between
  strands a float or a trim), 2 teeth chain ON (a hop of at most 8 mm that lies over
  laid thread is sewn needle-down). The piece is the run of consecutive strands whose
  window holds the most hops, with the fills under it CLIPPED to the window, so a hop
  that is "covered" in the design is covered here too. The fills sew in the light cone
  and the strands in the dark one, so a hop that shows reads as a dark line on a light
  field: the worst case for exposed travel (#917 measures 3 of 4 owl hops differing by
  12 L* or more).

Every flag that could move is pinned in every arm, as in v3.1. 40 wt only. Everything goes
through `digitizer_service.formats.write` (pystitch) and is read back with pystitch; never
the browser's DST codec. EVERY NUMBER HERE IS A CANDIDATE UNTIL KENT SEWS IT (ROADMAP
gate 1). No engine change, no flag flipped. No new client artwork: the owl, Fremont,
enthusiast and Becker are already in `testdata/`.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitches  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun, apply_ties, strip_ties  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402
from tools import sewout_card_v3_1 as v31  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402

REPO = v3.REPO
HOOP_MM = v3.HOOP_MM
WT = 40
MAX_RECORD_MM = v3.MAX_RECORD_MM
NAME = "card_v3_2_40wt"
DEFAULT_OUT = v3.DEFAULT_OUT                     # the same folder as v3 and v3.1
DEFAULT_RENDERS = REPO / "docs" / "renders" / "claude-sewout-card-v3-2"
STEM = "cut32_"                                  # v3.1's `cut31_*.json` are left alone
STOP_ORDER, STOPS = v2.STOP_ORDER, v2.STOPS
FILL_STOP, STRAND_STOP = 1, 2                    # the light cone under the dark one

# --- the cuts ---------------------------------------------------------------------------------

PINS, CUT_ARMS, ENT_ARMS, BECKER_ARMS = v31.PINS, v31.CUT_ARMS, v31.ENT_ARMS, v31.BECKER_ARMS

#: owl_kent at 127 mm, 40 wt, the photo lane, hairline line route (#882) with the strand
#: test OFF (#917's "line route" arms): the arms differ only by `hairline_lines_chain`.
OWL_FILE = "photo/owl_kent.jpg"
OWL_WIDTH_MM = 127.0
OWL_ROUTE = {"forced_class": "photo_subject", "photo_prep": False}
OWL_PINS = {"hairline": True, "hairline_from_lines": True, "hairline_lines_strand_test": False,
            "thread_wt": 40}
OWL_ARMS = {
    "owl_chain_off": {**OWL_PINS, "hairline_lines_chain": False},
    "owl_chain_on": {**OWL_PINS, "hairline_lines_chain": True},
}
#: the piece: the `OWL_WINDOW_MM` window (mm) of the chain-ON plan that holds the most hops sewn
#: needle-down (a hop counts only if its whole path is inside), the strands of that colour block and
#: the fills under them clipped to it (the fills to the window grown by `OWL_MARGIN_MM`)
OWL_WINDOW_MM = (14.0, 8.0)
OWL_MARGIN_MM = 0.6
HOP_CONTEXT_MM = 1.5          # a hop counts in a window only with this much of both strands round it
OWL_HOP_MAX_MM = 8.0                             # stage6_hairline_lines.HOP_MAX_MM, asserted at cut time

#: v3's own T / N cuts (`sewout_card_v3 --cut today|wordtier|keep`), re-made on today's main in a
#: sub-folder so v3's committed `cut_*.json` are not overwritten
TN_DIR = "tn"
TN_CUTS = ("tn_today", "tn_wordtier", "tn_keep")

ALL_CUTS = list(v31.ALL_CUTS) + list(TN_CUTS) + list(OWL_ARMS)
CUT_CHOICES = ALL_CUTS + ["owl"]                 # `owl`: both owl arms from one digitize (chain ON first)


@contextlib.contextmanager
def stem32():
    """v3.1's cut / load helpers read the module's `STEM`; point it at v3.2's files
    for the length of one call and put it back (the v3.1 tests share this process)."""
    old = v31.STEM
    v31.STEM = STEM
    try:
        yield
    finally:
        v31.STEM = old


def load_cut_file(cuts: Path, arm: str) -> dict:
    return json.loads((cuts / f"{STEM}{arm}.json").read_text(encoding="utf-8"))


def load_cut(cuts: Path, arm: str, box: str) -> dict:
    return load_cut_file(cuts, arm)["boxes"][box]


def _run_recs(plan):
    return [(b, r) for b in plan.blocks for r in b.runs if r.points]


def strand_sequence(runs) -> list[int]:
    """Indices (into `runs`) of the line route's strands, in sewing order."""
    from digitizer_core.stage6_hairline_lines import SHAPE_ID
    return [i for i, (_b, r) in enumerate(runs) if r.shape_id == SHAPE_ID and r.kind == stitches.RUN]


def _bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def is_hop(runs, i: int, j: int) -> bool:
    """Is the strand at runs[j] reached from the strand at runs[i] by a hop sewn needle-down?
    Yes when a travel run lies between them (a hop longer than one stitch) or when the next
    strand is not a jump although its first point is a stitch away (a one-stitch hop). A cut or
    a float is a jump."""
    a, b = runs[i][1].points[-1], runs[j][1].points[0]
    return j > i + 1 or (not runs[j][1].jump and math.dist(a, b) >= machine.TINY_STITCH_MM)


def hop_paths(runs) -> list[dict]:
    """Every hop sewn needle-down between two strands of one colour block: the strands' run
    indices and the path (strand end, any travel stitches, next strand start). Only a chain-ON
    plan has any."""
    out = []
    seq = strand_sequence(runs)
    for a, b in zip(seq, seq[1:]):
        if runs[a][0] is runs[b][0] and is_hop(runs, a, b):
            pts = [runs[a][1].points[-1]] + [p for k in range(a + 1, b) for p in runs[k][1].points] \
                + [runs[b][1].points[0]]
            out.append({"a": a, "b": b, "points": pts, "block": id(runs[a][0]),
                        "mm": sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))})
    return out


def _inside(box, pts, grow: float = 0.0) -> bool:
    """Is the polyline `pts`, with its bounding box grown by `grow` mm, inside `box`?"""
    x0, y0, x1, y1 = _bbox(pts)
    return box[0] <= x0 - grow and x1 + grow <= box[2] and box[1] <= y0 - grow and y1 + grow <= box[3]


def pick_window(runs, size=OWL_WINDOW_MM, step: float = 0.5) -> dict:
    """The `size` window (mm) that holds the most hops sewn needle-down, a hop counting only if its
    whole path lies inside; ties go to the longer total hop. The window is then re-centred on
    those hops. -> {"box", "hops", "hop_mm", "block"}."""
    hops = hop_paths(runs)
    assert hops, "no hop in the plan: is hairline_lines_chain on?"
    allp = [p for h in hops for p in h["points"]]
    x0, y0, x1, y1 = _bbox(allp)
    best = None
    for block in sorted({h["block"] for h in hops}):
        hs = [h for h in hops if h["block"] == block]
        nx = int((x1 - x0 + size[0]) / step) + 1
        ny = int((y1 - y0 + size[1]) / step) + 1
        for ix in range(nx + 1):
            for iy in range(ny + 1):
                bx, by = x0 - size[0] + ix * step, y0 - size[1] + iy * step
                box = (bx, by, bx + size[0], by + size[1])
                got = [h for h in hs if _inside(box, h["points"], HOP_CONTEXT_MM)]
                key = (len(got), round(sum(h["mm"] for h in got), 3))
                if best is None or key > best["key"]:
                    best = {"key": key, "box": box, "hops": got, "block": block}
    gx0, gy0, gx1, gy1 = _bbox([p for h in best["hops"] for p in h["points"]])
    cx, cy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
    box = (round(cx - size[0] / 2, 3), round(cy - size[1] / 2, 3), round(cx + size[0] / 2, 3), round(cy + size[1] / 2, 3))
    assert all(_inside(box, h["points"], HOP_CONTEXT_MM) for h in best["hops"])
    return {"box": box, "hops": len(best["hops"]), "hop_mm": round(sum(h["mm"] for h in best["hops"]), 3),
            "block": best["block"]}


def _clip(points, box):
    """The stitch points of one run that lie inside `box`, as fragments of consecutive points (at
    least 2 each), with whether the fragment began / ended where the run left or entered the box.
    No point is moved or invented. -> [(points, start_clipped, end_clipped)]"""
    x0, y0, x1, y1 = box
    out, cur, sc = [], [], False
    for k, p in enumerate(points):
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
            if not cur:
                sc = k > 0
            cur.append([round(p[0], 4), round(p[1], 4)])
        else:
            if len(cur) >= 2:
                out.append((cur, sc, True))
            cur = []
    if len(cur) >= 2:
        out.append((cur, sc, False))
    return out


def owl_piece(plan, sp, window: dict | None = None) -> dict:
    """The O block's piece from one owl plan: the window's strands (clipped to it), the fills under
    them (clipped to it grown by `OWL_MARGIN_MM`), the hops in it and how much each shows. With
    `window` (the chain-ON cut's record) the same window and colour block are cut from the chain-OFF
    plan, whose strands are the same points (#917's test) and whose hops are cuts and floats."""
    from digitizer_core.stage6_hairline_lines import SHAPE_ID
    runs = _run_recs(plan)
    if window is None:
        pw = pick_window(runs)
        box, rgb = pw["box"], tuple(int(v) for v in next(
            b.rgb for i, (b, _r) in enumerate(runs) if id(b) == pw["block"]))
    else:
        box, rgb = tuple(window["window_mm"]), tuple(window["strand_rgb"])
    fill_box = (box[0] - OWL_MARGIN_MM, box[1] - OWL_MARGIN_MM, box[2] + OWL_MARGIN_MM, box[3] + OWL_MARGIN_MM)
    # the strand block's runs in sewing order; a fragment is joined to the one before it by the ENGINE's
    # own decision only if its run directly followed the previous fragment's run and neither was cut by
    # the window; every other join (a clip artifact, the same in both arms) follows the card's distance rule
    strands, last = [], None
    for i, (b, r) in enumerate(runs):
        if r.shape_id != SHAPE_ID or tuple(int(v) for v in b.rgb) != rgb:
            continue
        frags = ([(list(map(list, r.points)), False, False)] if r.kind == stitches.TRAVEL and _inside(box, r.points)
                 else [] if r.kind == stitches.TRAVEL else _clip(r.points, box))
        for pts, sc, ec in frags:
            adj = last is not None and last[0] == i - 1 and not last[1] and not sc
            if r.kind == stitches.TRAVEL and not adj:
                continue                            # a hop whose strands are not both here is not a hop
            strands.append({"kind": r.kind, "jump": bool(r.jump), "trim": bool(r.trim), "orig": i,
                            "link": "engine" if adj else "gap", "shape_id": r.shape_id,
                            "rgb": list(rgb), "points": [[round(p[0], 4), round(p[1], 4)] for p in pts]})
            last = (i, ec)
    # a hop whose next strand fragment did not survive the window is not a hop: drop its travel run
    strands = [s for k, s in enumerate(strands)
               if s["kind"] != stitches.TRAVEL or (k + 1 < len(strands) and strands[k + 1]["link"] == "engine"
                                                    and strands[k + 1]["orig"] == s["orig"] + 1)]
    fills = []
    for b, r in runs:
        if r.shape_id == SHAPE_ID:
            continue
        for pts, _sc, _ec in _clip(r.points, fill_box):
            fills.append({"kind": r.kind, "jump": True, "trim": False, "shape_id": r.shape_id,
                          "rgb": [int(v) for v in b.rgb], "points": pts})
    # the hops that survived the window, read off the fragments the card will sew (the same reading as
    # `chain_piece`): an engine-joined RUN fragment reached through a travel run, or one stitch away
    # and not a jump
    hop_pts, links, prev, via = [], [], None, None
    for s in strands:
        if s["kind"] == stitches.TRAVEL:
            via = s["points"]
            continue
        if prev is not None and s["link"] == "engine":
            a, b = prev["points"][-1], s["points"][0]
            if via is not None or (not s["jump"] and math.dist(a, b) >= machine.TINY_STITCH_MM):
                pts = [a] + (via or []) + [b]
                hop_pts.append(pts)
                links.append({"a": a, "b": b, "travel_run": via is not None,
                              "mm": round(sum(math.dist(p, q) for p, q in zip(pts, pts[1:])), 3)})
        prev, via = s, None
    return {"window_mm": [round(v, 4) for v in box], "fill_box_mm": [round(v, 4) for v in fill_box],
            "strand_rgb": list(rgb), "strands": strands, "fill": fills,
            "strand_count": sum(1 for s in strands if s["kind"] == stitches.RUN),
            "links": links, "visibility": hop_gaps(hop_pts, sp, rgb)}


def hop_gaps(paths, sp, rgb) -> dict:
    """How much each hop shows: the mean absolute L* gap between the thread and the source under the
    hop (sampled every 0.25 mm), against the hairline tier's own contrast floor (12) -- #917's
    reading (`tools.hairline_lines_chain_trial.hop_visibility`) for hops with or without a travel run.
    A file property, not a sew-out (gate 1)."""
    import cv2
    from digitizer_core.stage6_hairline import _SRC_MIN_CONTRAST
    from tools.hairline_lines_chain_trial import _lab_l
    lab = cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2LAB)[..., 0].astype(np.float64) * 100.0 / 255.0
    h, w = lab.shape
    gaps, mm = [], []
    for pts in paths:
        vals = []
        for a, b in zip(pts, pts[1:]):
            n = max(2, int(math.dist(a, b) / 0.25))
            for k in range(n + 1):
                px, py = sp.to_px(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                vals.append(lab[min(max(int(round(py)), 0), h - 1), min(max(int(round(px)), 0), w - 1)])
        gaps.append(abs(float(np.mean(vals)) - _lab_l(rgb)))
        mm.append(sum(math.dist(p, q) for p, q in zip(pts, pts[1:])))
    showing = [m for g, m in zip(gaps, mm) if g >= _SRC_MIN_CONTRAST]
    return {"hops": len(gaps), "hop_mm": round(sum(mm), 2), "showing_hops": len(showing),
            "showing_mm": round(sum(showing), 2),
            "mean_gap_L": round(float(np.mean(gaps)), 1) if gaps else 0.0,
            "max_hop_mm": round(max(mm), 2) if mm else 0.0}

def owl_whole(plan, sp) -> dict:
    """The instrument's numbers for the WHOLE owl design (#917's table rows, on
    #937's corrected reader)."""
    from tools import hairline_lines_chain_trial as clt
    from tools import hairline_lines_trial as hlt
    from tools.hairline_travel import measure_plan
    row = hlt.measure(plan)
    t = measure_plan(plan, with_legacy=False)
    row.update({k: t[k] for k in ("thread_bare_mm", "thread_exposed_legs", "thread_by_leg", "flight_bare_mm",
                                  "trims_block_start", "trims_in_shape", "trims_between_shapes",
                                  "flight_total_mm")})
    strands = [r for _b, r in clt._runs(plan) if r.shape_id == clt.SHAPE_ID and r.kind == stitches.RUN]
    row["strand_runs"] = len(strands)
    row["strand_trims"] = clt.strand_trims(plan)
    row["strand_jumps"] = len(clt.cuts(plan))
    row["visibility"] = clt.hop_visibility(plan, sp)
    w = [x for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"]
    row["census"] = {k: w[0].get(k) for k in ("strands", "dropped", "hops", "hop_mm", "refused_bar")
                     if w and k in w[0]}
    return row


def owl_cut_from(arm: str, plan, sp, cuts: Path, t0: float | None = None) -> Path:
    """One owl arm's cut file from its plan: the O piece (the chain-ON piece names the window, the
    chain-OFF one reads it from the chain-ON cut) and the whole design's instrument numbers."""
    window = None if arm == "owl_chain_on" else load_cut_file(cuts, "owl_chain_on")["boxes"]["O"]
    piece = owl_piece(plan, sp, window)
    if window is not None:
        assert piece["window_mm"] == window["window_mm"]
    out = {"arm": arm, "overrides": {**OWL_ARMS[arm], **OWL_ROUTE}, "width_mm": OWL_WIDTH_MM,
           "file": OWL_FILE, "garment_id": None,
           "stitches_whole": plan.stats.stitch_count, "trims_whole": plan.stats.trims,
           "size_mm_whole": [round(v, 2) for v in plan.stats.size_mm], "whole": owl_whole(plan, sp),
           "window_size_mm": list(OWL_WINDOW_MM), "boxes": {"O": piece}}
    path = _write(cuts, arm, out)
    print(f"{arm}: whole {plan.stats.stitch_count:,} stitches, {plan.stats.trims} trims; piece "
          f"{len(piece['strands'])} strand fragments of {piece['strand_count']} runs, {len(piece['links'])} hops, "
          f"{len(piece['fill'])} fill fragments, window {piece['window_mm']}"
          + (f"; {time.time() - t0:.0f} s" if t0 else "") + f" -> {path}", flush=True)
    return path


def cut_owl(arms: tuple[str, ...], cuts: Path) -> Path:
    """Digitize owl_kent at 127 mm (the stages once) and plan it with each arm's chain flag; save each
    arm's cut. Chain ON is always cut first: it names the window."""
    from digitizer_core.pipeline import plan_stitches, run_stages
    from digitizer_core.stage6_hairline_lines import HOP_MAX_MM
    from tools import hairline_lines_trial as hlt
    assert HOP_MAX_MM == OWL_HOP_MAX_MM, HOP_MAX_MM
    arms = tuple(sorted(arms, key=lambda a: a != "owl_chain_on"))
    t = time.time()
    result = run_stages(hlt.PHOTO, PipelineConfig(target_width_mm=OWL_WIDTH_MM, **OWL_ARMS[arms[0]], **OWL_ROUTE))
    path = None
    for arm in arms:
        cfg = PipelineConfig(target_width_mm=OWL_WIDTH_MM, **OWL_ARMS[arm], **OWL_ROUTE)
        path = owl_cut_from(arm, plan_stitches(result, cfg), result.source_pixels, cuts, t)
    return path

def _write(cuts: Path, arm: str, out: dict) -> Path:
    cuts.mkdir(parents=True, exist_ok=True)
    path = cuts / f"{STEM}{arm}.json"
    path.write_text(json.dumps(out), encoding="utf-8")
    return path


def cut(arm: str, cuts: Path, design_dir: Path | None = None) -> Path:
    if arm == "owl":
        return cut_owl(tuple(OWL_ARMS), cuts)
    if arm in OWL_ARMS:
        return cut_owl((arm,), cuts)
    if arm in TN_CUTS:
        return v3.cut_arm(arm[3:], cuts / TN_DIR, design_dir)
    with stem32():
        if arm in CUT_ARMS:
            return v31.cut_fremont(arm, cuts, design_dir)
        if arm in ENT_ARMS:
            return v31.cut_enthusiast(arm, cuts)
        return v31.cut_becker(arm, cuts)


# --- the card -----------------------------------------------------------------------------

LETTERS = {**v31.LETTERS, "O": [(0, 0), (3, 0), (3, 4), (0, 4), (0, 0)]}
O_ARMS = ("chain-off", "chain-on")
BLOCKS = {**v31.BLOCKS, "O": O_ARMS}
INDEX_STRIP = {**v31.INDEX_STRIP, "O": "O"}
O_SOURCE = {"chain-off": "owl_chain_off", "chain-on": "owl_chain_on"}
SOURCES = {**v31.SOURCES, "O": {a: (O_SOURCE[a], ["O"]) for a in O_ARMS}}
ORIENT = {**v31.ORIENT, "E2": "v", "O": "h"}     # E2 stacks so O fits beside it in the hoop
GARMENT_OF = {**v31.GARMENT_OF, "O": None}
ROW_GAP = 3.0            # between the rows S / B / E2+O (v3.1: 4.0), to keep the card inside the hoop
NEW_DIGITIZED = v31.NEW_DIGITIZED + tuple(f"O:{a}:" for a in O_ARMS)


class Card(v31.Card):
    """v3.1's card with the O block's runs: the strands keep the ENGINE's jump / trim
    decisions (a chained hop is NOT a jump, an unchained one is a float or a trim);
    the fills under them are cut to the window, so their joins follow the card's
    rule (a hop under `TRIM_AT_MM` is a float, beyond it a trim)."""

    DIGITIZED = v31.Card.DIGITIZED + tuple(f"O:{a}:" for a in O_ARMS)
    LETTERS = LETTERS

    def index(self, key: str, x0: float, y0: float, width: float) -> None:
        self.add(0, hc.corners([(x0 + a, y0 + b) for a, b in LETTERS[key]]), f"{key}:index")
        self.add(0, hc.corners([(x0 + 5.0, y0 + 5.0), (x0 + width, y0 + 5.0)]), f"{key}:rule")

    def strip(self, key: str, x0: float, y0: float) -> None:
        self.add(0, hc.corners([(x0 + a, y0 + b) for a, b in LETTERS[key]]), f"{key}:index")

    def plan(self, stops=STOP_ORDER, table=STOPS) -> StitchPlan:
        blocks = []
        for stop in stops:
            runs = [r for s, r in self.items if s == stop]
            if not runs:
                continue
            prev, prev_arm = None, None
            for r in runs:
                arm = ":".join(r.shape_id.split(":")[:2])
                if r.shape_id.startswith(self.DIGITIZED):
                    r.points = strip_ties(r.points)
                    engine = r.shape_id.endswith(":strand") and arm == prev_arm
                    if prev is not None and not engine:
                        hop = math.dist(prev, r.points[0])
                        r.jump = hop >= machine.TINY_STITCH_MM
                        r.trim = hop > machine.TRIM_AT_MM
                prev, prev_arm = r.points[-1], arm
            runs[0].jump = False
            runs[0].trim = False
            apply_ties(runs)
            name, rgb, _hint = table[stop]
            blocks.append(StitchBlock(thread_index=stop, thread_number=f"{stop + 1}", rgb=rgb, runs=runs))
        return StitchPlan(blocks=blocks, palette=[], warnings=[])


def _o_runs(recs: list[dict], tag, dx: float, dy: float) -> list[StitchRun]:
    return [StitchRun(points=[(p[0] + dx, p[1] + dy) for p in r["points"]], kind=r["kind"],
                      jump=bool(r["jump"]), trim=bool(r["trim"]), shape_id=tag(r) if callable(tag) else tag)
            for r in recs]


def block_o(c: Card, x0: float, y0: float, cuts: Path, report: list) -> None:
    """The chaining block: the index letter at the left, the two arms beside it.
    The fills (light cone) go first, the strands (dark cone) on top, as the engine
    sews them."""
    c.strip("O", x0, y0)
    x, y = x0 + v31.HEADER_LEFT, y0 + v31.ARM_TOP
    right, bottom = x0 + 3.0, y0 + 4.0
    for k, arm in enumerate(O_ARMS, start=1):
        data = load_cut_file(cuts, O_SOURCE[arm])
        piece = data["boxes"]["O"]
        fb = piece["fill_box_mm"]
        dx, dy = x - fb[0], y - fb[1]
        for r in _o_runs(piece["fill"], f"O:{arm}:fill", dx, dy):
            c.add_run(FILL_STOP, r)
        # a fragment the ENGINE joined to the one before keeps its flags (`strand`); every other join is
        # a clip artifact, the same in both arms, and follows the card's distance rule (`gap`)
        for r in _o_runs(piece["strands"], lambda s: f"O:{arm}:{'strand' if s['link'] == 'engine' else 'gap'}",
                         dx, dy):
            c.add_run(STRAND_STOP, r)
        box = (x, y, x + (fb[2] - fb[0]), y + (fb[3] - fb[1]))
        c.arms[f"O:{arm}"] = box
        c.add(0, hc.teeth(x, y - 0.8, k), f"O:label:{arm}")
        report.append({"block": "O", "arm": arm, "cut": O_SOURCE[arm], "overrides": data["overrides"],
                       "garment_id": None, "runs": len(piece["strands"]) + len(piece["fill"]),
                       "strands": piece["strand_count"],
                       "chained_hops": len(piece["links"]),
                       "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
        right, bottom = max(right, box[2]), max(bottom, box[3])
        x = box[2] + v31.H_GAP
    c.boxes["O"] = (x0, y0, right, bottom)


def block_stacked(c: Card, blk: str, x0: float, y0: float, cuts: Path, report: list) -> None:
    """v3.1's `block_new` with this module's cuts and orientation (E2 stacked)."""
    with stem32():
        saved = v31.ORIENT
        v31.ORIENT = {**saved, blk: ORIENT[blk]}
        try:
            v31.block_new(c, blk, x0, y0, cuts, report)
        finally:
            v31.ORIENT = saved


def build(cuts: Path) -> tuple[StitchPlan, Card, dict]:
    c = Card(WT)
    report: list[dict] = []
    with stem32():
        v3.block_F3(c, 0.0, 0.0, report)
        v3.block_cut(c, "T", c.boxes["F3"][2] + 6.0, 0.0, 26.0, cuts / TN_DIR, report)   # v3's cuts, re-made
        v3.block_cut(c, "N", c.boxes["T"][2] + 6.0, 0.0, 20.0, cuts / TN_DIR, report)
        row1 = max(c.boxes[k][3] for k in ("F3", "T", "N"))
        v2.block_G(c, 0.0, row1 + 5.0, report)
        v31.block_new(c, "X", c.boxes["G"][2] + 6.0, row1 + 5.0, cuts, report)
        row2 = max(c.boxes[k][3] for k in ("G", "X"))
        v31.block_new(c, "S", 0.0, row2 + ROW_GAP, cuts, report)
        v31.block_new(c, "B", 0.0, c.boxes["S"][3] + ROW_GAP, cuts, report)
    y = c.boxes["B"][3] + ROW_GAP
    block_stacked(c, "E2", 0.0, y, cuts, report)
    block_o(c, c.boxes["E2"][2] + 6.0, y, cuts, report)
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


def the_is_unaffected(cuts: Path) -> dict:
    """#913: THE is unaffected by the skeleton tier. On the v3.2 cuts: the THE box of each
    skeleton arm is point for point today's, and today's is the T block's own cut."""
    def pts(file_arm):
        return [(r["kind"], r["points"]) for r in load_cut(cuts, file_arm, "T")["runs"]]
    today = pts("today")
    t_block = [(r["kind"], r["points"]) for r in v3.load_cut(cuts / TN_DIR, "today", "T")["runs"]]
    return {"skel_same_as_today": pts("skel") == today, "skel073_same_as_today": pts("skel073") == today,
            "today_same_as_t_block_cut": today == t_block, "runs": len(today),
            "points": sum(len(p) for _k, p in today)}


# --- renders ------------------------------------------------------------------------------------

ROWS = v31.ROWS + (
    ("O owl hairline, line route, 127 mm: chain OFF | chain ON (1 / 2 teeth; fills light, strands dark)",
     ("O:chain-off", "O:chain-on"), "h"),
)


def render(plan: StitchPlan, out: Path, ppm: float = 12.0):
    return v31.render(plan, out, ppm)


def panel(plan: StitchPlan, card: Card, out: Path, ppm: float = 60.0) -> None:
    """v3.1's blocks sheet with the O row added (the owl pair at the same 60 px/mm)."""
    saved = v31.ROWS
    v31.ROWS = ROWS
    try:
        v31.panel(plan, card, out, ppm)
    finally:
        v31.ROWS = saved


# --- the chaining block's numbers -----------------------------------------------------------------

def _arm_runs(plan: StitchPlan, arm: str) -> list[StitchRun]:
    return [r for b in plan.blocks for r in b.runs if r.shape_id.startswith(f"O:{arm}:")]


def chain_piece(plan: StitchPlan, arm: str) -> dict:
    """The O piece of one arm as the FILE's plan holds it: the instrument's reading
    (`tools.hairline_travel.measure_plan`, #895 / #937: a trimmed jump is a flight, not thread)
    on the piece alone, plus the joins between strands (hops sewn needle-down, floats = untrimmed
    jumps, trims) and the length of each."""
    from tools.hairline_travel import _thread_zone, bare_profile, measure_plan
    runs = _arm_runs(plan, arm)
    fill = [r for r in runs if r.shape_id.endswith(":fill")]
    strand = [r for r in runs if r.shape_id.endswith((":strand", ":gap"))]
    mini = StitchPlan(blocks=[StitchBlock(thread_index=0, thread_number="1", rgb=(0, 0, 0),
                                          runs=fill + strand)], palette=[], warnings=[])
    m = measure_plan(mini, with_legacy=False)
    zone = _thread_zone(mini)
    floats, trims, hop_mm, hop_bare, clip_joins = [], [], [], [], 0
    prev, via = None, None
    for r in strand:
        if r.kind == stitches.TRAVEL:
            via = list(r.points)
            continue
        if prev is not None:
            a, b = prev.points[-1], r.points[0]
            d = math.dist(a, b)
            if r.shape_id.endswith(":gap"):
                clip_joins += d >= machine.TINY_STITCH_MM         # a window artifact, the same in both arms
            elif via is not None or (not r.jump and d >= machine.TINY_STITCH_MM):
                pts = [a] + (via or []) + [b]
                hop_mm.append(round(sum(math.dist(p, q) for p, q in zip(pts, pts[1:])), 2))
                hop_bare.append(round(bare_profile(zone, pts)[0], 3))      # the hop over fabric nothing laid
            elif r.jump:
                (trims if r.trim else floats).append(round(d, 2))
        prev, via = r, None
    return {"arm": arm, "stitches": sum(len(r.points) for r in runs),
            "strand_runs": sum(1 for r in strand if r.kind == stitches.RUN),
            "travel_runs": sum(1 for r in strand if r.kind == stitches.TRAVEL),
            "chained_hops": len(hop_mm), "chained_hop_mm": hop_mm, "chained_hop_bare_mm": hop_bare,
            "window_joins": int(clip_joins),
            "floats_untrimmed": len(floats), "float_mm": floats,
            "trims_between_strands": len(trims), "trim_flight_mm": trims,
            "instrument": {k: m[k] for k in ("thread_bare_mm", "thread_exposed_legs", "thread_by_leg",
                                              "flight_bare_mm", "flight_legs", "trims_block_start",
                                              "trims_in_shape", "trims_between_shapes", "flight_total_mm")}}


def chain_block(plan: StitchPlan, cuts: Path) -> dict:
    out = {"pieces": {a: chain_piece(plan, a) for a in O_ARMS}, "whole": {}, "window": {}}
    for a in O_ARMS:
        d = load_cut_file(cuts, O_SOURCE[a])
        out["whole"][a] = {**d["whole"], "stitches_whole": d["stitches_whole"], "trims_whole": d["trims_whole"]}
        out["window"][a] = {"window_mm": d["boxes"]["O"]["window_mm"],
                            "strand_count": d["boxes"]["O"]["strand_count"],
                            "strand_fragments": len(d["boxes"]["O"]["strands"]),
                            "links": d["boxes"]["O"]["links"],
                            "visibility": d["boxes"]["O"]["visibility"],
                            "fill_fragments": len(d["boxes"]["O"]["fill"])}
    return out


def _trims_in(p: dict) -> int:
    i = p["instrument"]
    return i["trims_block_start"] + i["trims_in_shape"] + i["trims_between_shapes"]


def chain_markdown(cb: dict) -> str:
    off, on = (cb["pieces"][a] for a in O_ARMS)
    woff, won = (cb["whole"][a] for a in O_ARMS)
    vis = cb["window"]["chain-on"]["visibility"]
    lines = [
        "The card's O pieces, as the FILE's plan holds them (the instrument is `tools/hairline_travel.measure_plan`, "
        "#895's reader as #937 fixed it: a trimmed jump is a flight, not thread laid on the fabric; "
        "run on each piece alone, fills and strands):", "",
        "| O piece | chain OFF | chain ON |", "|---|---|---|",
        f"| strands | {off['strand_runs']} | {on['strand_runs']} |",
        f"| stitches | {off['stitches']:,} | {on['stitches']:,} |",
        f"| hops sewn needle-down (count; mm each, through the travel stitches) | {off['chained_hops']} | "
        f"{on['chained_hops']}; {on['chained_hop_mm']} |",
        f"| of which over bare fabric (mm each; the cover test says 0) | - | {on['chained_hop_bare_mm']} |",
        f"| untrimmed jumps between strands (floats: thread dragged, no needle; count; mm each) | "
        f"{off['floats_untrimmed']}; {off['float_mm']} | {on['floats_untrimmed']}; {on['float_mm']} |",
        f"| trimmed jumps between strands (cuts; count; mm each) | {off['trims_between_strands']}; "
        f"{off['trim_flight_mm']} | {on['trims_between_strands']}; {on['trim_flight_mm']} |",
        f"| thread over bare fabric, instrument (mm) | {off['instrument']['thread_bare_mm']} | "
        f"{on['instrument']['thread_bare_mm']} |",
        f"| exposed travel legs, instrument | {off['instrument']['thread_exposed_legs']} | "
        f"{on['instrument']['thread_exposed_legs']} |",
        f"| trimmed flights over bare, not thread (mm) | {off['instrument']['flight_bare_mm']} | "
        f"{on['instrument']['flight_bare_mm']} |",
        f"| trims in the piece (the first strand's cut, fill joins and strand cuts together) | "
        f"{_trims_in(off)} | {_trims_in(on)} |",
        "",
        f"The chained hops' gap to the source (mean L* difference between the dragged thread and the source under "
        f"the hop; the tier's own contrast floor is 12): {vis['showing_hops']} of {vis['hops']} hops differ by 12 or "
        f"more, {vis['showing_mm']} of {vis['hop_mm']} mm, mean gap {vis['mean_gap_L']} L*, longest "
        f"{vis['max_hop_mm']} mm (a reading of the photo, not of cloth).", "",
        "The whole owl design (127 mm, 40 wt, photo lane, the line route; #917's table rows re-measured on this tree):",
        "",
        "| owl_kent, whole design | chain OFF | chain ON |", "|---|---|---|",
        f"| stitches | {woff['stitches_whole']:,} | {won['stitches_whole']:,} |",
        f"| trims | {woff['trims_whole']} | {won['trims_whole']} |",
        f"| trims between two strands | {woff['strand_trims']} | {won['strand_trims']} |",
        f"| jumps between strands (trimmed or not) | {woff['strand_jumps']} | {won['strand_jumps']} |",
        f"| hops sewn needle-down (count / mm) | {woff['census'].get('hops', 0)} / {woff['census'].get('hop_mm', 0.0)} | "
        f"{won['census'].get('hops', 0)} / {won['census'].get('hop_mm', 0.0)} |",
        f"| strands sewn / dropped | {woff['census'].get('strands')} / {woff['census'].get('dropped')} | "
        f"{won['census'].get('strands')} / {won['census'].get('dropped')} |",
        f"| thread over bare fabric, instrument (mm) | {woff['thread_bare_mm']} | {won['thread_bare_mm']} |",
        f"| trimmed flights over bare (mm) | {woff['flight_bare_mm']} | {won['flight_bare_mm']} |",
        f"| thread laid (m) | {woff['thread_m']} | {won['thread_m']} |",
        f"| hops showing against the source (of count / mm) | - | {won['visibility']['showing_hops']} of "
        f"{won['visibility']['hops']} / {won['visibility']['showing_mm']} of {won['visibility']['hop_mm']} |",
        f"| plan md5 | `{woff['md5'][:8]}...` | `{won['md5'][:8]}...` |",
        "",
    ]
    return "\n".join(lines)


# --- the file checks --------------------------------------------------------------------------------

def readback(path: Path, plan: StitchPlan, card: Card, cuts: Path) -> dict:
    rb = v31.readback(path, plan, card)
    rb["chain"] = chain_block(plan, cuts)
    return rb


def readback_markdown(rb: dict) -> str:
    return v31.readback_markdown(rb) + "\n" + chain_markdown(rb["chain"])


# --- docs ---------------------------------------------------------------------------------------------

def _between(text: str, start: str, end: str | None) -> str:
    i = text.index(start)
    j = text.index(end, i) if end else len(text)
    return text[i:j]


O_ROW = ("| **O** | bottom row, right of E2 (arms side by side) | **NEW (v3.2): the line route's chaining.** The owl "
         "(`owl_kent.jpg`, 127 mm, 40 wt, the photo lane's hairline line route, #882 / #917): one run of consecutive "
         "strands with the fills under it clipped to the window. **1** `hairline_lines_chain` OFF (today: every hop "
         "between strands is a float or a trim), **2** ON (a hop of at most 8 mm that lies over laid thread is "
         "sewn needle-down). The fills sew in the **light** cone and the strands in the **dark** one, so a hop that "
         "shows is a dark line on a light field. | Does a hop sewn on top of the fill read worse than the cut it "
         "replaces? Exposed travel (thread on the fabric between hops), floating thread, cut ends, and whether "
         "the strands still read as one hair line. #917 leaves the flip, and the 8 mm cap, to the sew-out. |")


def _rows_match(a: dict, b: dict, keys) -> list[str]:
    return [f"| {k} | {a.get(k, '-')} | {b.get(k, '-')} |" for k in keys]


def drift_table(rb: dict) -> str:
    """Piece by piece, the v3.1 FILE's stitches against this file's (both from the read-backs)."""
    old = json.loads((DEFAULT_OUT / "readback.json").read_text(encoding="utf-8"))["stitches_by_piece"]
    new = rb["stitches_by_piece"]
    lines = ["| piece | v3.1 file | v3.2 file | change |", "|---|---|---|---|"]
    for blk, arms in v31.BLOCKS.items():
        for arm in arms:
            k = f"{blk}:{arm}"
            lines.append(f"| {k} | {old[k]:,} | {new[k]:,} | {new[k] - old[k]:+,} |")
    return "\n".join(lines) + "\n"


def cut_drift(cuts: Path) -> str:
    """Whole-design stitch / trim counts of each re-cut against the v3.1 cut they replace."""
    lines = ["| cut | whole design, v3.1 cut | whole design, v3.2 cut |", "|---|---|---|"]
    for arm in v31.ALL_CUTS:
        a = json.loads((DEFAULT_OUT / "cuts" / f"cut31_{arm}.json").read_text(encoding="utf-8"))
        b = load_cut_file(cuts, arm)
        lines.append(f"| `{arm}` | {a['stitches_whole']:,} stitches, {a['trims_whole']} trims | "
                     f"{b['stitches_whole']:,} stitches, {b['trims_whole']} trims |")
    for arm in ("today", "wordtier", "keep"):
        a = json.loads((DEFAULT_OUT / "cuts" / f"cut_{arm}.json").read_text(encoding="utf-8"))
        b = json.loads((cuts / TN_DIR / f"cut_{arm}.json").read_text(encoding="utf-8"))
        lines.append(f"| T / N cut `{arm}` (v3's) | {a['stitches_whole']:,} stitches, {a['trims_whole']} trims | "
                     f"{b['stitches_whole']:,} stitches, {b['trims_whole']} trims |")
    return "\n".join(lines) + "\n"


def e2_note(cuts: Path) -> str:
    old = json.loads((DEFAULT_OUT / "cuts" / "cut31_ent_skel073.json").read_text(encoding="utf-8"))
    new = load_cut_file(cuts, "ent_skel073")
    return (f"**E2 (enthusiast, skeleton at floor 0.73).** v3.1's file sewed {old['skeleton_sewn']} of {old['offered']} "
            f"offered glyphs as a skeleton run ({old['stitches_whole']:,} stitches whole), as #913 measured. #936 "
            f"(the small-glyph second try, flag still OFF) takes more of them: live on this tree the same flags "
            f"sew **{new['skeleton_sewn']} of {new['offered']}** ({new['stitches_whole']:,} stitches whole). "
            f"**v3.2's E2 arm 2 is the re-cut, so it sews {new['skeleton_sewn']}, not {old['skeleton_sewn']}**: the "
            f"card is for what main does today, and the flag the sew-out asks about is the one that would be "
            f"flipped. Declined on this tree: {len(new['declined'])} (reason: {', '.join(new['declined']) or 'none'}).")


def f3_note(rb: dict) -> str:
    oldrb = json.loads((DEFAULT_OUT / "readback.json").read_text(encoding="utf-8"))
    old, new = oldrb["stitches_by_piece"], rb["stitches_by_piece"]
    ext = lambda r, a: r["decoded_pieces"][f"F3:{a}"]["file"]        # noqa: E731
    parts = []
    for a, label in (("today", "today"), ("floor", "`small_print_floor` ON"), ("keep", "`small_glyph_keep` ON")):
        o, n = ext(oldrb, a), ext(rb, a)
        parts.append(f"{label} {old[f'F3:{a}']} to {new[f'F3:{a}']} stitches ({new[f'F3:{a}'] - old[f'F3:{a}']:+d}), "
                     f"{o['w']} x {o['h']} to {n['w']} x {n['h']} mm")
    return ("**F3 (small caps).** #923 (`small_print_floor`, the counters that still shut at 3 mm) was said to move "
            "v3.1's F3 arm 2 by one stitch and 0.1 mm or less; the VP accepted that. F3 is not a cut: the card "
            "digitizes APA when it is built, so **v3.2's F3 is regenerated on today's main**, not carried. Measured "
            "on this tree against v3.1's file (file stitches, file extent): " + "; ".join(parts) + ". **That is not "
            "#923:** the same three arms digitized with `lettering_columns_square_ends` and "
            "`lettering_columns_inside_connectors` OFF give 94 / 114 / 94 stitches, v3.1's counts exactly, so #923 "
            "is 0 stitches here and the whole change is the two ends flags, which #922 turned ON by default after "
            "v3.1 was built. F3's arms do not pin them (v3's generator, unchanged), so F3 follows main's default "
            "and the arms still differ only by the flag each names. "
            "The readout is unchanged: does the counter open in arm 2 and arm 3 and not in arm 1.")

README = """# Sew-out card v3.2, 2026-10-14

One DST file (**40 wt**): card v3.1's eight blocks **re-cut on today's main**,
**plus one new block, O: the line route's chaining** (`cfg.hairline_lines_chain`,
#917, default OFF; Kent 2026-10-14: it **stays OFF until this sew-out**). Each
question is a block of arms sewn **side by side** (or stacked, for the wide ones)
and labelled with teeth. You sew it once, read each block on
`scoring-sheet-v3.2.md`, and that settles several ROADMAP gate-1 questions
together. **Every number on this card is a candidate until you sew it.** Nothing
here is a setting; no flag is flipped by it.

SIZE_MM mm, STITCHES stitches, TRIMS trims, COLOURS colour stops (two cones),
allow roughly MINUTES minutes (an estimate from the stitch count at 650 spm, not
a measurement). **Inside a 4 x 4 in hoop (100 x 100 mm).**

**This card replaces v3.1.** v3.1 (`card_v3_1_40wt.dst`, `README.md`,
`scoring-sheet.md`, `readback.*`, `cuts/cut31_*.json`) and v3 (`*-v3.*`) are
kept in this folder untouched, for history; do not sew two of them. v3.2 carries
every v3.1 block (F3, T, N, G, X, S, B, E2) arm for arm and flag for flag. It
does not replace card v1 (`../hairline-card-2026-10-12/`) or card v2
(`../card-v2-2026-10-13/`); neither has been sewn (MASTER_SCOPE "Waiting on Kent"
44, 45, 47).

## What changed from v3.1

1. **Block O is new: the line route's chaining.** See the block map and "The
   chaining block" below. Nothing was dropped to fit it: it sits right of E2.
2. LAYOUTNOTE
3. F3NOTE
4. E2NOTE
5. **Every cut was re-made on today's main** (`cuts/cut32_*.json`, and
   `cuts/tn/cut_*.json` for T and N), because `digitizer_core` moved after
   v3.1's cuts were taken. The flags are pinned exactly as in v3.1, so the
   differences below are the engine's, not the card's. Whole-design totals, the
   v3.1 cut against the v3.2 cut:

CUTDRIFT
   And the pieces as the two FILES hold them (stitches):

DRIFT

## What is in this folder

| File | What it is |
|---|---|
| `card_v3_2_40wt.dst` | the card, **40 wt** thread. |
| `card_v3_2_40wt.png` | what the file looks like, thread drawn at the laid width, 12 px/mm. A picture of the file, not of cloth. |
| `card_v3_2_40wt_blocks.png` | every arm cropped at 60 px/mm, the arms of a block side by side (stacked for S, E2, X and B), for comparing them before you sew. |
| `scoring-sheet-v3.2.md` | the readout sheet: one table per block. Print it. |
| `cuts/cut32_*.json`, `cuts/tn/cut_*.json` | the runs the pieces sew: Fremont tagline / E / M, O, N / THE and 1895, enthusiast's line, Becker's MARINE, and the owl's O pair (see below). |
| `readback-v3.2.md`, `readback-v3.2.json` | the file checks, also quoted below. |
| `README.md`, `scoring-sheet.md`, `readback.*`, `card_v3_1_40wt.*`, `cuts/cut31_*.json` | card v3.1, for history. |
| `README-v3.md`, `scoring-sheet-v3.md`, `readback-v3.*`, `card_v3_40wt.*`, `cuts/cut_*.json` | card v3, for history. |

The file is written by `python -m tools.sewout_card_v3_2` (in `digitizer/`)
through the service's export path (pystitch), not the browser's DST codec, and
read back with pystitch. The test is `digitizer/tests/test_sewout_card_v3_2.py`.

## What you need

- **Fabric:** the **cap** (or a scrap of the same structured twill) is the
  honest test. F3, T, N, S and X are digitized on the **Hat profile** (0.4 mm
  pull per side), as your Fremont job was. **E2 and B are digitized on the
  left-chest profile** (#913's and #912's own corpus runs), and **O on the
  pipeline's default profile** (#917's owl run), so a cap is a harder test of
  them than they were made for; read them as a flag check, not as a size for
  the hat. Block G is the default profile, as on card v2.
- **Stabilizer:** the backing you used for the Fremont hat; else tearaway
  (medium) under twill, no topping.
- **Thread, two cones:** a **dark** (black or navy) and a **light** (white or
  cream), the same maker and weight. 40 wt: **Madeira Polyneon No. 40**, or
  Isacord 40. Every v3.1 block sews in the **dark** cone; **O sews its fills in
  the light cone and its strands in the dark one.**
- **Needle:** 40 wt **75/11**. **Bobbin:** the same for every sew-out.
- The design is SIZE_MM mm, inside a 100 x 100 mm field (a 4 x 4 in hoop).
  It is tall: **hoop it with the whole card inside the field and trace the
  outline before sewing.**

## How to sew it

1. Load `card_v3_2_40wt.dst`. **Put the needle at the centre of the card**: the
   file's origin is the middle of the SIZE_MM mm box. Trace the outline.
2. Turn **trims on**. The file cuts between pieces and wherever the
   digitizer cut inside one. Block O's chain-ON arm has **fewer** cuts on
   purpose: its hops are stitched.
3. **Three colour stops** (two cones; the machine asks for the dark one twice):
   1. **Stop 1, dark.** Every index strip and label, blocks F3, T, N, S, E2, X
      and B, and the **fill** of each block G arm.
   2. **Stop 2, light.** Block G's **bars** and block O's **fills** (the owl's
      fill rows under the strands, both arms).
   3. **Stop 3, dark.** Block G's two edge runs round each fill (short) and
      block O's **strands and hops** (both arms), on top of the owl's fills.
4. Count **thread breaks** from the machine's counter, per block if you can.
   S's two skeleton arms put 0.73 mm and 1.0 mm stitches in a 0.4 mm line:
   note shredding, looping and needle heat on them.
5. Do not press or steam before scoring. Photograph each block close up (a
   macro) and once at arm's length; most pieces are 2-10 mm tall. For O,
   photograph the pair side by side in raking light: the hops are the thing.

## How to read the arms

Every block has an **index strip**: its letter sewn as a run, 4 mm tall (F for
F3, T, N, G, S, E for E2, X, B, and O for the owl block). Blocks F3, T, N and G
keep v3's layout (strip above the arms, rule under it); the new blocks S, E2, X,
B, O put the strip to the **left** of their arms. Arms are labelled by
**teeth** (a square wave sewn above each), counted from the left, or from the
top for the stacked blocks (X, B, E2): **1 tooth** is the first arm named in the
table below, **2 teeth** the second, **3 teeth** the third.

![](card_v3_2_40wt.png)

## Block map

BLOCKMAP

## The chaining block (O)

CHAINDOC

## What the files say about each arm (the FILE, not the cloth)

PAIRNOTES

The skeleton arms in S: the shape counts, pieces and widths are in the
read-back below; #913's table (per glyph, sewn width 0.42-0.43 mm against
0.47-0.73 mm today) is the source for what each glyph does. **A counter 0.5 mm
wide under a 0.40 mm thread is mostly covered (#913: 20-40% stays bare at
0.73), so the A may read as a filled triangle in both arms: that is the trade,
and the cloth is the judge.**

## Where the pieces come from

None of the pieces but F3 and the labels are drawn; they are the **stitches the
engine sews** for a design that is already in the repo. The cut files hold the
runs exactly as the engine laid them (kind, points, the engine's jump and trim
calls). The card places each cut's top-left, one translation per piece, and the
card's plan keeps the engine's own jump/trim decisions for these runs (a hop
under `TRIM_AT_MM` is a float). Block O's strands keep them exactly (a chained
hop is NOT a jump); its fills are clipped to the window, so their joins follow
the card's rule.

CUTNOTES

## The file checks (pystitch reading the DST back)

READBACK
Reproduce with `python -m tools.sewout_card_v3_2` from `digitizer/` (the cuts
are re-made with `--cut today|skel|skel073|ends_on|ent_today|ent_skel073|becker_off|becker_on|tn_today|tn_wordtier|tn_keep|owl_chain_on|owl_chain_off`,
one process at a time, a minute to ten each; `owl_chain_on` first, it names the window).

## Things to know before you sew

THINGS
- **Block O is a window, not the owl.** It is a run of consecutive strands with
  the fills clipped under them, at 1:1 (127 mm design scale). The fills sew in
  the light cone so exposure is the worst case; in the photo the thread colours
  differ and #917 measured the same reading from the source, not from cloth.
- **The 8 mm cap is not tested above the longest hop in the window**
  (LONGHOP mm here; #917's longest on the whole owl is 5.8 mm). It is a
  candidate (gate 3), not a measurement.
"""

CHAINDOC = """`hairline_lines_chain` (#917) is OFF on `main`, and stays OFF until Kent has
sewn this block. It acts only when the hairline line route (`hairline_from_lines`,
#882) runs. Strands are sewn nearest end first, as before. A hop between two
strands of at most `HOP_MAX_MM` (**8.0 mm**, candidate, borrowed from the
streamline tier's no-topcoat reasoning) is sewn **needle-down**, as a travel run
at 2.5 mm, when every point of the hop (sampled every 0.1 mm) is within half a
thread width of a stitch the fills and detail layer already laid; every other
hop is a jump, **a trim past 3.0 mm** (`trim_at_mm`), exactly as today. A hop
under 3.0 mm that is not chained is an **untrimmed jump**: the thread is dragged
across, a float. So the two arms differ in what they leave between strands:
arm 1, floats (thread above the fabric, no needle) and cuts (two locks and a
trim each); arm 2, short stitched hops lying on the fills.

**What the piece is.** The owl at 127 mm, 40 wt, #917's route (photo lane,
`photo_prep` off, hairline line route, strand test OFF), digitized on this
tree twice (chain OFF, chain ON). The window is the WINDOWSIZE mm patch of the
chain-ON plan that holds the most hops sewn needle-down, a hop counting only
with 1.5 mm of both its strands round it (HOPS_IN_WINDOW hops, STRANDS_IN_WINDOW
strand runs, window WINDOWBOX mm in the design's frame; #917's whole owl has 9
hops, 4 with a travel run). The same window is cut from the chain-OFF plan: the
strands themselves do not move (#917's test; the cut asserts the same window and
the same fills). **Strands are clipped to the window** (no stitch is moved or
invented; where a strand leaves the window the piece simply ends, and the join
to the next fragment follows the card's rule: a hop under 3.0 mm is a float, a
longer one a trim; those WINDOWJOINS window joins are the same in both arms and
are not hops). Under the strands sit the fills of the design clipped to the
window grown by 0.6 mm (FILLFRAGS fragments), so a hop that is "covered" in the
design is covered on the card. The fills sew in the light cone, the strands in
the dark one. The fills are several layers of the owl's colours: they sew as a
dense light pile and carry their own cuts (the piece's trim count is mostly
those, equal in both arms).

**What the instrument says** (the FILE, never the cloth; ROADMAP gate 1).
`tools/hairline_travel.measure_plan` is #895's reader as #937 corrected it (a
trimmed jump is a flight, no thread; an untrimmed jump or a chained hop is
thread). It is quoted for both arms below, on the whole owl and on the card's
piece.

CHAINTABLE

**How to read the sheet.** Score what is between the strands: thread you can
see on the fabric where nothing was sewn (floats, long hops), cut ends and
stray tails, thread lying on top of a fill, a ridge or pucker under a hop, and
whether the strands still read as one continuous hair line. #917's open
question is whether a short dark hop sewn on top of a lighter fill (3 of its 4
owl hops that get a travel run differ by 12 L* or more, mean 25.7) reads
worse than the cut it replaces. The 8 mm cap and the flip are Kent's after
this sew-out."""


def _layout_note(rb: dict) -> str:
    x, y = rb["extent_mm"]
    return (f"**Layout.** v3.1 was 93.8 x 92.8 mm. To fit O inside the same 100 x 100 mm hoop, **E2's two arms are "
            f"stacked instead of side by side** (they were 75 mm wide in one row, 31.8 mm wide stacked) and O sits "
            f"to the right of them in the same row; the gap between the S, B and E2+O rows is 3.0 mm instead of "
            f"4.0. Nothing was dropped or moved to another block. The card is **{x} x {y} mm** "
            f"(v3.1: 93.8 x 92.8): inside the hoop with {round((100 - max(x, y)) / 2, 1)} mm to spare each side.")


def cut_notes(cuts: Path) -> str:
    lines = ["| cut | flags on the request (beyond the pins) | whole design | what was cut |",
             "|---|---|---|---|"]
    notes = dict(CUT_NOTES)
    allarms = {**CUT_ARMS, **ENT_ARMS, **BECKER_ARMS, **OWL_ARMS}
    for arm in ALL_CUTS:
        if arm.startswith("tn_"):
            continue
        f = cuts / f"{STEM}{arm}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        base = OWL_PINS if arm in OWL_ARMS else PINS
        diff = {k: v for k, v in allarms[arm].items() if v != base.get(k)}
        pins = "owl line route, strand test OFF, " if arm in OWL_ARMS else ""
        lines.append(f"| `{arm}` | {pins}`{diff or 'none: every flag pinned OFF'}` | {d['stitches_whole']:,} stitches, "
                     f"{d['trims_whole']} trims, {d['size_mm_whole'][0]} x {d['size_mm_whole'][1]} mm "
                     f"({d.get('garment_id') or 'default'}) | {notes[arm]} |")
    for arm, what in (("today", "THE (T arm 1), 1895 with `small_glyph_keep` OFF (N arm 1)"),
                      ("wordtier", "THE with `lettering_words` + `lettering_word_tiers` (T arm 2)"),
                      ("keep", "1895 with `small_glyph_keep` ON (N arm 2)")):
        f = cuts / TN_DIR / f"cut_{arm}.json"
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            lines.append(f"| T / N `{arm}` (v3's cut) | `{d['overrides']}` | {d['stitches_whole']:,} stitches, "
                         f"{d['trims_whole']} trims ({d['size_mm_whole'][0]} x {d['size_mm_whole'][1]} mm, Hat) | {what} |")
    return "\n".join(lines) + "\n"


CUT_NOTES = {
    "today": "tagline box (S arm 1), THE box (checked against the skeleton arms), E and M, O, N (X arm 1)",
    "skel": "tagline box (S arm 2); THE box (check)",
    "skel073": "tagline box (S arm 3); THE box (check)",
    "ends_on": "E and M, O, N (X arm 2)",
    "ent_today": "ENTERPRISES INC (E2 arm 1)",
    "ent_skel073": "ENTERPRISES INC (E2 arm 2)",
    "becker_off": "MARINE (B arm 1)",
    "becker_on": "MARINE (B arm 2)",
    "owl_chain_off": "the O window: strands and clipped fills (O arm 1)",
    "owl_chain_on": "the O window (O arm 2); cut first, it names the window",
}

SCORING_O = """## O: owl hairline, line route at 127 mm (chain OFF | chain ON): what is left between the strands

The fills sew light and the strands dark: a hop that shows is a dark line on a
light field. Arm 2's hops are the short straight dark joins between two strands,
sewn needle-down; arm 1 has floats (thread dragged, no needle) and cuts there.
Read the pair together in raking light, at arm's length first and then under a
loupe.

| Arm | Thread breaks | Thread visible on the fabric between strands, off the fill (Y/N) | Loose floating thread between strands (Y/N) | Cut ends / stray tails between strands (count) | A hop shows as a line ON the fill at arm's length (Y/N; arm 2) | Ridge or pucker under a hop (Y/N) | Strands read as one continuous hair line (Y/N) | Free note |
|---|---|---|---|---|---|---|---|---|
| 1 tooth: chain OFF | ___ | _ | _ | ___ | n/a | _ | _ | |
| 2 teeth: chain ON (8 mm cap) | ___ | _ | _ | ___ | _ | _ | _ | |

Which arm you would ship for hair strands (1 / 2 / no difference): ____

"""

SCORING_CANDIDATE = ("| `hairline_lines_chain` flip, and its 8 mm hop cap (`HOP_MAX_MM`) | stays OFF until sewn; the cap is a "
                     "candidate | block O: arm 2 shows no visible thread between strands and no hop line at arm's "
                     "length, no ridge, and arm 1's floats or cut ends are visible; the longest hop on the card is "
                     "LONGHOP mm, so the cap is NOT tested above that |\n")


def write_docs(out: Path, rb: dict, cuts: Path) -> None:
    size = f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}"
    cb = rb["chain"]
    on = cb["pieces"]["chain-on"]
    longhop = max(on["chained_hop_mm"] + [0.0])
    owl = load_cut_file(cuts, "owl_chain_on")["boxes"]["O"]
    chaindoc = (CHAINDOC.replace("WINDOWSIZE", f"{OWL_WINDOW_MM[0]} x {OWL_WINDOW_MM[1]}")
                .replace("HOPS_IN_WINDOW", str(on["chained_hops"])).replace("STRANDS_IN_WINDOW", str(owl["strand_count"]))
                .replace("WINDOWBOX", str([round(v, 1) for v in owl["window_mm"]]))
                .replace("WINDOWJOINS", str(on["window_joins"]))
                .replace("FILLFRAGS", f"{len(owl['fill']):,}").replace("CHAINTABLE", chain_markdown(cb)))
    blockmap = _between(v31.README, "| Block | Where |", "### Pinned flags").rstrip() + "\n" + O_ROW + "\n\n" \
        + _between(v31.README, "### Pinned flags", "## What the files say")
    blockmap = blockmap.replace("| **E2** | bottom row |", "| **E2** | bottom row, left (arms stacked) |")
    the = rb["the_is_unaffected"]
    if the["skel_same_as_today"] and the["skel073_same_as_today"]:
        blockmap = blockmap.replace("THE_NOTE", (
            f"the skeleton tier leaves THE as it is (#913: the T is declined on width; the THE box cut from the "
            f"skeleton arms at both floors is point for point today's, {the['runs']} runs, {the['points']} points), so "
            f"a skeleton arm would be a duplicate of arm 1 and is dropped."))
    else:
        blockmap = blockmap.replace("THE_NOTE", "the skeleton arms DIFFER from today's here: see the cuts.")
    blockmap += ("\nBlock O's cuts pin `hairline`, `hairline_from_lines`, `hairline_lines_strand_test` OFF and `thread_wt` "
                 "40 on the photo lane (`forced_class` photo_subject, `photo_prep` off), differing only by "
                 "`hairline_lines_chain`; `cuts/cut32_owl_*.json` record the flag set each came from.\n")
    things = _between(v31.README, "## Things to know before you sew", None).split("\n", 2)[2].rstrip() + "\n"
    things = things.replace("v3.1", "v3.2")
    text = (README.replace("READBACK", readback_markdown(rb)).replace("PAIRNOTES", pair_notes(rb))
            .replace("CUTNOTES", cut_notes(cuts)).replace("BLOCKMAP", blockmap).replace("CHAINDOC", chaindoc)
            .replace("THINGS", things).replace("LAYOUTNOTE", _layout_note(rb)).replace("F3NOTE", f3_note(rb))
            .replace("E2NOTE", e2_note(cuts)).replace("CUTDRIFT", cut_drift(cuts)).replace("DRIFT", drift_table(rb))
            .replace("SIZE_MM", size).replace("STITCHES", f"{rb['stitches_file']:,}")
            .replace("TRIMS", str(rb["trims"])).replace("COLOURS", str(rb["colours"]))
            .replace("MINUTES", str(rb["sew_minutes_est"])).replace("LONGHOP", str(longhop)))
    (out / "README-v3.2.md").write_text(text, encoding="utf-8")
    scoring = v31.SCORING.replace("sew-out card v3.1", "sew-out card v3.2").replace("card_v3_1_40wt.dst", "card_v3_2_40wt.dst")
    scoring = scoring.replace("Arm's length read of the whole card:", SCORING_O + "Arm's length read of the whole card:")
    scoring = scoring.rstrip("\n") + "\n" + SCORING_CANDIDATE.replace("LONGHOP", str(longhop))
    scoring = scoring.replace("(`card_v3_2_40wt.dst`, 40 wt, needle 75/11)",
                              "(`card_v3_2_40wt.dst`, 40 wt, needle 75/11; E2's arms are stacked, O's side by side)")
    (out / "scoring-sheet-v3.2.md").write_text(scoring, encoding="utf-8")


def pair_notes(rb: dict) -> str:
    n = rb["stitches_by_piece"]
    lines = ["| piece | arm | stitches | vs arm 1 |", "|---|---|---|---|"]
    for blk, arms in BLOCKS.items():
        base = n[f"{blk}:{arms[0]}"]
        for arm in arms:
            v = n[f"{blk}:{arm}"]
            lines.append(f"| {blk} | {arm} | {v:,} | {'-' if arm == arms[0] else f'{v - base:+,}'} |")
    return "\n".join(lines) + "\n"


def generate(out: Path, renders: Path | None = None, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    """Write the whole card into `out` (and the PNGs into `renders`, if given)
    from the cuts in `cuts` (default: `<out>/cuts`); returns the read-back."""
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "CARDV3.2 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    render(plan, out / f"{NAME}.png")
    panel(plan, card, out / f"{NAME}_blocks.png")
    rb = readback(path, plan, card, cuts)
    rb["sew_minutes_est"] = v31.sew_minutes(rb)
    rb["pieces"] = extra["pieces"]
    rb["the_is_unaffected"] = the_is_unaffected(cuts)
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items()
                          if k not in ("pieces", "pieces_mm", "stitches_by_piece", "decoded_pieces", "chain")}))
    (out / "readback-v3.2.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    (out / "readback-v3.2.md").write_text(readback_markdown(rb), encoding="utf-8")
    write_docs(out, rb, cuts)
    if renders is not None:
        renders.mkdir(parents=True, exist_ok=True)
        for name in (f"{NAME}.png", f"{NAME}_blocks.png"):
            (renders / name).write_bytes((out / name).read_bytes())
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=CUT_CHOICES, help="digitize this arm and save its cuts")
    ap.add_argument("--cuts", default=str(v3.DEFAULT_CUTS))
    ap.add_argument("--design-dir", help="with a Fremont --cut: also save the whole design here (not committed)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--renders", default=str(DEFAULT_RENDERS), help="copy the PNGs here too ('' to skip)")
    a = ap.parse_args(argv)
    if a.cut:
        cut(a.cut, Path(a.cuts), Path(a.design_dir) if a.design_dir else None)
        return 0
    generate(Path(a.out), Path(a.renders) if a.renders else None, Path(a.cuts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
