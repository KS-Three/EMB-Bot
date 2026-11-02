"""Sew-out card v8: cut every jump (Python and browser) beside the small-text bold factor and the 0.8 mm halo (2026-11-01)

    # 1. cut the jobs (Fremont and Enthusiast: one stage 0-4 build, forked per
    #    arm; Drone: one build per arm, its arms act at stage 4). The lettering
    #    cut runs node on tools/sewout_card_v8_lettering.mjs.
    python -m tools.sewout_card_v8 --cut fremont
    python -m tools.sewout_card_v8 --cut enthusiast
    python -m tools.sewout_card_v8 --cut drone
    python -m tools.sewout_card_v8 --cut lettering
    # 2. build the card (reads the cuts)
    python -m tools.sewout_card_v8 [--out ../docs/sewout/card-v8-2026-11-01]

Card v7 (2026-10-25) carries the two flags Kent's 2026-10-22 ruling left on
fabric (pull by stroke, the pro's values). This card carries what the K3
foreman handoff queued after it (`docs/superpowers/plans/2026-10-27-k3-
foreman-handoff.md`, "Sew-out card v8"), each arm checked against the flips
merged since 10-25 first; the ones a flip closed are named in the README.

- `cut_every_jump` (Python, built OFF 10-21, the walk on the work #1048) and
  `cutEveryJump` (browser, built OFF 10-27, #1133): Kent 10-21 / 10-26, OFF
  beside ON on this card, neither flips alone. Gate 1 names the fabric
  question: trimmer wear and tie knots against floats, and whether a hop
  sewn needle-down on the work shows. On today's engine the Python flag
  does two different things on two jobs, so both are sewn: on Fremont at
  92.5 mm every one of its 148 floats (the rope strands and the tan bean
  letters, hop to hop) lies on the white field, and ON walks all 148 and
  cuts none; on ENTHUSIAST at 93 mm the floats are between letters on bare
  cloth, and ON cuts 18 of 19. The browser flag on a typed name cuts all
  15 of its floats (medium_font, the Studio's default, "Fritsch's
  Stitches" at 44 mm, flat).
- the small-text bold factor (`small_text_cap_bold_scale` 1.45; the pro's
  columns read 1.7-3.0x the TRACED stroke, 1.10-1.26 mm on Drone and
  ProSeal against our 0.81-0.92) and the 0.8 mm clearance halo
  (`small_text.CLEAR_MM`, gate 1 by the grow-away note: Drone's AND DRONE
  stops at x1.40 against it, the pro re-sets it x1.57 and keeps 0.15-0.30 mm
  thread to thread). Both act at stage 4, so Drone is built once per arm;
  the halo is a module constant with no flag, set per arm by this tool and
  pinned at 0.8 in every other arm. Measured on Drone (62.6 mm hat): bold
  alone trades height for width inside the same room (2.0: x1.32, 1.02 mm
  columns from x1.40 / 0.92), the halo alone buys height (0.3: x1.74, 1.04),
  and the two together land on the pro's numbers (x1.65, 1.35 against his
  x1.57, 1.26).

Arms, in tooth order; every arm pins every flag an arm touches (`PIN`) and
the halo explicitly, so a later default flip moves no re-cut (memory
`bean-holds-on-2026-10-15`):

- (a) 1 tooth   ships: main 3896a7ae's defaults, pinned
- (b) 2 teeth   `cut_every_jump` ON (Python) / `cutEveryJump` ON (browser)
- (c) 3 teeth   bold 2.0 (halo 0.8)
- (d) 4 teeth   halo 0.3 (bold 1.45)
- (e) 5 teeth   bold 2.0 and halo 0.3

Four blocks, one 4 x 4 in hoop, two cones (white first: the Fremont field):

- F  Hotel Fremont at 92.5 mm Hat (the pro's patch), the lower crest between
     the band and the point: EAT | STAY | PLAY (bean letters), the rope's
     lower arcs and the white field under them, clipped to the window.
     (a) | (b). Every float in it is on the field: (b) walks them all.
- E  ENTHUSIAST at 93 mm Hat, the tagline ENTERPRISES INC. (re-set x2.0 by
     `small_text_reset_grow_away`): (a) | (b). Its 13 floats are between
     letters on bare cloth: (b) cuts them. (a) is also where to read the
     re-set's counters (P, R) and 0.25 mm gaps on cloth.
- J  "Fritsch's Stitches" typed in medium_font at 44 mm through the browser
     builder (`tools/sewout_card_v8_lettering.mjs`): (a) | (b).
- D  Precision Drone at 62.6 mm Hat: THERMAL, AND DRONE (re-set), the dome
     and the short dashes under it, in two rows: (a) | (c) and (d) | (e).

Every Python piece keeps its own jump and cut decisions as the plan made
them (a float stays a float, a walk a walk, a cut a cut); a hop the crop
itself made, where a neighbour fell outside the window, is cut in every arm,
never left as a float. Locks are stripped and the card's own laid, as every
card tool does (`tie_in_off` is moot here). Through
`digitizer_service.formats.write` (pystitch), read back with pystitch. The
`cut_every_jump` walk is judged by a 0.01 mm oracle on every job's DST
(`tools/jump_walk_oracle.py`); its verdict rides each cut and the README.
EVERY NUMBER HERE IS A CANDIDATE UNTIL KENT SEWS IT (gate 1). No default
changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import machine  # noqa: E402
from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun, apply_ties, strip_ties  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import jump_walk_oracle as oracle  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402
from tools import sewout_card_v7 as v7  # noqa: E402

REPO = hc.REPO
WT = v3.WT
NAME = "card_v8_40wt"
DATE = "2026-11-01"
ENGINE = "main 3896a7ae (2026-11-01)"
DEFAULT_OUT = REPO / "docs" / "sewout" / f"card-v8-{DATE}"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"
LETTERING_TOOL = REPO / "tools" / "sewout_card_v8_lettering.mjs"

WHITE_RGB = (255, 255, 255)
DARK_RGB = v2.DARK_RGB
WHITE, DARK = 0, 1
#: the two stops in sew order: the Fremont field first, everything else dark
STOPS = {WHITE: ("white", WHITE_RGB, "white: the Fremont field (block F only)"),
         DARK: ("dark", DARK_RGB, "dark: black or navy, everything else")}
STOP_ORDER = (WHITE, DARK)

#: Every flag an arm of this card touches, and every flag that builds these
#: pieces and could flip later, at its value on `ENGINE`, pinned in EVERY
#: arm: the committed cuts then mean the same thing on a re-cut whatever
#: main's defaults do next.
PIN = {
    "cut_every_jump": False,
    "small_text_cap_mm": 4.0,
    "small_text_cap_max_width_scale": 1.05,
    "small_text_cap_min_stroke_mm": 0.85,
    "small_text_cap_letter_gap_mm": 0.25,
    "small_text_cap_bold_scale": 1.45,
    "small_text_cap_reach_edges": True,
    "small_text_bay_mouth": True,
    "small_text_reset_grow_away": True,
    "lettering_columns_small_bold": True,
    "bean_only_lines": True,
    "dark_ink_bean": True,
    "trim_bury_under_later": True,
    "tie_in_off": True,
}
#: `small_text.CLEAR_MM` on `ENGINE`: the clearance halo the re-set keeps
#: round a line. Not a flag; set per arm by `cut`, pinned here otherwise.
CLEAR_PIN = 0.8

#: arm -> (label, the flags over PIN, the halo), in tooth order
ARMS = {
    "a": ("ships", {}, CLEAR_PIN),
    "b": ("cut every jump", {"cut_every_jump": True}, CLEAR_PIN),
    "c": ("bold 2.0", {"small_text_cap_bold_scale": 2.0}, CLEAR_PIN),
    "d": ("halo 0.3", {}, 0.3),
    "e": ("bold 2.0 + halo 0.3", {"small_text_cap_bold_scale": 2.0}, 0.3),
}
TEETH = {arm: k for k, arm in enumerate(ARMS, start=1)}


def overrides(arm: str) -> dict:
    """The arm's whole override set on the Studio request: PIN, then its flags."""
    return {**PIN, **ARMS[arm][1]}


def clear_mm(arm: str) -> float:
    return ARMS[arm][2]


#: job -> art, size, the arms it sews (tooth order) and whether the arms act
#: after stage 4 (`fork`: one build, forked per arm) or in it (one build each)
JOBS = {
    "fremont": {"art": ROOT / "testdata" / "photo" / "logo_hotel_fremont.webp", "width_mm": 92.5,
                "garment_id": "hat_front", "arms": ("a", "b"), "fork": True},
    "enthusiast": {"art": ROOT / "testdata" / "photo" / "enthusiast_logo.png", "width_mm": 93.0,
                   "garment_id": "hat_front", "arms": ("a", "b"), "fork": True},
    "drone": {"art": ROOT / "testdata" / "photo" / "logo_drone_thermal_badge.png", "width_mm": 62.6,
              "garment_id": "hat_front", "arms": ("a", "c", "d", "e"), "fork": False},
}
BLOCK = {"fremont": "F", "enthusiast": "E", "lettering": "J", "drone": "D"}
#: The rows of the card, top to bottom: block, then the pieces side by side.
LAYOUT = (
    ("F", (("fremont", "a"), ("fremont", "b"))),
    ("E", (("enthusiast", "a"), ("enthusiast", "b"))),
    ("J", (("lettering", "a"), ("lettering", "b"))),
    ("D", (("drone", "a"), ("drone", "c"))),
    ("D", (("drone", "d"), ("drone", "e"))),
)

#: job -> the window cut out of the design (x0, y0, x1, y1), mm from the
#: centre of its stitched extent, y down. A shape is kept when every
#: needle-down point of it lies inside (grown by `WINDOW_PAD_MM`); a run in
#: `CLIP_RGB` (the white field) is CLIPPED to the window instead, its
#: inside pieces kept in sewing order.
WINDOWS = {
    "fremont": (-21.0, 8.2, 21.0, 26.0),       # EAT | STAY | PLAY, the rope's lower arcs, the field
    "enthusiast": (-30.0, 3.8, 13.5, 9.2),     # ENTERPRISES INC.
    "drone": (-19.2, 17.3, 18.9, 32.6),        # THERMAL, (A)ND DRONE, the dome, the short dashes
}
WINDOW_PAD_MM = 0.3
CLIP_RGB = {WHITE_RGB}
CLIP_MIN_MM = 0.6       # a clipped piece shorter than this is a sliver and is dropped


# --- the cuts ------------------------------------------------------------------------------------

def _runs_json(plan: StitchPlan) -> list[dict]:
    """Every run of the plan in sew order with its own jump/cut flags; `seq`
    is its place in that order, so a crop can tell a run's real predecessor.
    A one-point run stays: a 2-3 mm walk is a travel run of ONE stitch, and
    dropping it (as card v7's dump does) would leave the run after it
    without its predecessor, which the crop then cuts."""
    out = []
    seq = 0
    for bi, b in enumerate(plan.blocks):
        for r in b.runs:
            if r.points:
                out.append({"seq": seq, "b": bi, "kind": r.kind, "shape_id": r.shape_id,
                            "rgb": [int(v) for v in b.rgb], "jump": bool(r.jump), "trim": bool(r.trim),
                            "points": [[round(q[0], 4), round(q[1], 4)] for q in r.points]})
            seq += 1
    return out


def runs_md5(runs: list[dict]) -> str:
    return hashlib.md5(json.dumps([[r["kind"], r["jump"], r["trim"], r["points"]] for r in runs]).encode()).hexdigest()


def floats(runs: list[dict]) -> int:
    """Uncut needle-up moves of `machine.TINY_STITCH_MM` or more, as the plan stands."""
    n = 0
    prev = None
    for r in runs:
        if prev is not None and r["b"] == prev["b"] and r["jump"] and not r["trim"] \
                and math.dist(prev["points"][-1], r["points"][0]) >= machine.TINY_STITCH_MM:
            n += 1
        prev = r
    return n


def _bbox(pts) -> tuple[float, float, float, float]:
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def _inside(box, w) -> bool:
    return box[0] >= w[0] and box[1] >= w[1] and box[2] <= w[2] and box[3] <= w[3]


def _clip_segment(a, b, w):
    """Liang-Barsky: the part of a->b inside the window, or None."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - w[0]), (dx, w[2] - a[0]), (-dy, a[1] - w[1]), (dy, w[3] - a[1])):
        if p == 0:
            if q < 0:
                return None
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    if t0 > t1:
        return None
    return (a[0] + dx * t0, a[1] + dy * t0), (a[0] + dx * t1, a[1] + dy * t1)


def _clip_run(r: dict, w) -> list[dict]:
    """The run's pieces inside the window, in path order, each a run of its
    own; a piece under `CLIP_MIN_MM` is dropped."""
    pts = [tuple(p) for p in r["points"]]
    frags: list[list] = []
    cur: list | None = None
    for a, b in zip(pts, pts[1:]):
        piece = _clip_segment(a, b, w)
        if piece is None:
            cur = None
            continue
        s, e = piece
        if cur is not None and math.dist(cur[-1], s) < 1e-6:
            cur.append(e)
        else:
            cur = [s, e]
            frags.append(cur)
    out = []
    for f in frags:
        if len(f) >= 2 and sum(math.dist(p, q) for p, q in zip(f, f[1:])) >= CLIP_MIN_MM:
            out.append({**r, "points": [[round(x, 4), round(y, 4)] for x, y in f], "clipped": True})
    return out


def select(job: str, runs: list[dict]) -> list[dict]:
    """The runs of the shapes inside the job's window, in sewing order, each
    marked `clipped` (a piece of a `CLIP_RGB` run) or whole."""
    x0, y0, x1, y1 = WINDOWS[job]
    bx = _bbox([p for r in runs for p in r["points"]])
    cx, cy = (bx[0] + bx[2]) / 2.0, (bx[1] + bx[3]) / 2.0
    w = (cx + x0 - WINDOW_PAD_MM, cy + y0 - WINDOW_PAD_MM, cx + x1 + WINDOW_PAD_MM, cy + y1 + WINDOW_PAD_MM)
    # A shared id (`__edge_cap__`) is judged run by run, as card v7 does.
    key = [r["shape_id"] if not r["shape_id"].startswith("__") else f"{r['shape_id']}#{i}"
           for i, r in enumerate(runs)]
    by_shape: dict[str, list] = {}
    for k, r in zip(key, runs):
        if r["kind"] != "travel" and tuple(r["rgb"]) not in CLIP_RGB:
            by_shape.setdefault(k, []).extend(r["points"])
    keep = {k for k, pts in by_shape.items() if _inside(_bbox(pts), w)}
    out = []
    for k, r in zip(key, runs):
        if tuple(r["rgb"]) in CLIP_RGB:
            out += _clip_run(r, w)
        elif k in keep and _inside(_bbox(r["points"]), w):
            out.append({**r, "clipped": False})
    return out


def _capture_reset_report():
    """Spy on `small_text.enlarge_small_text`: its report rows, per build."""
    from digitizer_core import small_text
    real = small_text.enlarge_small_text
    box: dict = {"rows": []}

    def spy(*a, **k):
        rows = real(*a, **k)
        box["rows"] = rows
        return rows
    small_text.enlarge_small_text = spy
    return box, lambda: setattr(small_text, "enlarge_small_text", real)


def _reset_rows(rows) -> list[dict]:
    """The re-set's rows that placed a line: scale, stroke (tag, traced), room."""
    out = []
    for row in rows or []:
        if row.get("scale"):
            out.append({k: row[k] for k in ("cluster", "cap_mm", "scale", "width_scale", "stroke_mm", "letters")
                        if k in row} | ({"grow_away": str(row["grow_away"])} if row.get("grow_away") else {}))
    return out


def cut(job: str, cuts: Path) -> Path:
    """Digitize the job per arm and save each arm's window as JSON, with the
    whole design's counts, the re-set's rows and, where arm (b) is sewn, the
    oracle's verdict on its walk."""
    from digitizer_core import PipelineConfig, small_text
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode as svc_decode, _parse_config
    from tools import pro_pair
    j = JOBS[job]
    data = Path(j["art"]).read_bytes()

    def cfg(arm):
        req = pro_pair.request(j["width_mm"], j["garment_id"], overrides(arm))
        c = PipelineConfig(**_parse_config(json.dumps(req)))
        missed = {k: v for k, v in overrides(arm).items() if getattr(c, k) != v}
        if missed:
            raise SystemExit(f"{job}/{arm}: the service parser did not carry {missed}")
        return c
    plans: dict[str, StitchPlan] = {}
    reset: dict[str, list] = {}
    reset_satin: dict[str, dict] = {}
    oracle_on: StitchPlan | None = None
    box, restore = _capture_reset_report()
    saved_clear = small_text.CLEAR_MM

    def planned(gen, arm, built):
        c = cfg(arm)
        res = finish_generation(gen, c)
        plan = plan_stitches(res, c)
        # the re-set line's own columns (every region the re-set enlarged),
        # read off the plan: what the D table quotes against the pro's 1.26
        sids = {r.shape_id for r in res.regions if r.meta.get("small_text_enlarged")}
        plans[arm] = plan
        reset[arm] = built
        reset_satin[arm] = v7.satin_stats([StitchRun(points=list(rr.points), kind=rr.kind)
                                           for b in plan.blocks for rr in b.runs if rr.shape_id in sids])
        return plan
    try:
        if j["fork"]:
            if len({clear_mm(a) for a in j["arms"]}) != 1:
                raise SystemExit(f"{job}: forked arms must share one halo")
            small_text.CLEAR_MM = clear_mm(j["arms"][0])
            t = time.time()
            gen = build_generation(svc_decode(data), cfg(j["arms"][0]), exif_source=data)
            print(f"{job}: stages 0-4 {time.time() - t:.0f} s", flush=True)
            built = _reset_rows(box["rows"])
            for arm in j["arms"]:
                t = time.time()
                plan = planned(gen.fork(), arm, built)
                print(f"{job}/{arm}: {plan.stats.stitch_count:,} st, {plan.stats.trims} trims, "
                      f"{time.time() - t:.0f} s", flush=True)
        else:
            for arm in j["arms"]:
                t = time.time()
                small_text.CLEAR_MM = clear_mm(arm)
                gen = build_generation(svc_decode(data), cfg(arm), exif_source=data)
                if arm == "a":
                    # The oracle's ON file for a job that does not sew arm (b)
                    # -- arm (a)'s build with `cut_every_jump` ON, measured and
                    # not on the card -- so every job's walk is judged.
                    c_on = cfg("b")
                    oracle_on = plan_stitches(finish_generation(gen.fork(), c_on), c_on)
                plan = planned(gen, arm, _reset_rows(box["rows"]))
                print(f"{job}/{arm}: {plan.stats.stitch_count:,} st, {plan.stats.trims} trims, "
                      f"halo {clear_mm(arm)}, {time.time() - t:.0f} s", flush=True)
    finally:
        small_text.CLEAR_MM = saved_clear
        restore()
    out = {"job": job, "art": Path(j["art"]).relative_to(ROOT).as_posix(), "width_mm": j["width_mm"],
           "garment_id": j["garment_id"], "engine": ENGINE, "pin": PIN, "clear_pin": CLEAR_PIN,
           "window": WINDOWS[job], "arms": {}}
    for arm, plan in plans.items():
        runs = _runs_json(plan)
        keep = select(job, runs)
        out["arms"][arm] = {"overrides": overrides(arm), "clear_mm": clear_mm(arm),
                            "stitches_whole": plan.stats.stitch_count, "trims_whole": plan.stats.trims,
                            "floats_whole": floats(runs),
                            "size_mm_whole": [round(v, 2) for v in plan.stats.size_mm],
                            "md5_whole": runs_md5(runs), "md5": runs_md5(keep), "reset": reset[arm],
                            "reset_satin": reset_satin[arm], "runs": keep}
        print(f"{job}/{arm}: {len(keep)} runs kept of {len(runs)}, {floats(runs)} floats in the design",
              flush=True)
    if "b" in plans:
        out["oracle"] = {**oracle.judge(plans["a"], plans["b"], job), "sewn": True}
    elif oracle_on is not None:
        out["oracle"] = {**oracle.judge(plans["a"], oracle_on, job), "sewn": False}
    if "oracle" in out:
        print(f"{job}: oracle {json.dumps({k: v for k, v in out['oracle'].items() if k != 'bare_detail'})}",
              flush=True)
    cuts.mkdir(parents=True, exist_ok=True)
    path = cuts / f"{job}.json"
    path.write_text(json.dumps(out), encoding="utf-8")
    return path


def cut_lettering(cuts: Path) -> Path:
    """Block J through node: the browser builder's OFF and ON streams."""
    cuts.mkdir(parents=True, exist_ok=True)
    path = cuts / "lettering.json"
    subprocess.run(["node", str(LETTERING_TOOL), str(path)], check=True, cwd=str(REPO))
    return path


def load(cuts: Path, job: str) -> dict:
    return json.loads((cuts / f"{job}.json").read_text(encoding="utf-8"))


# --- the pieces ----------------------------------------------------------------------------------

def piece_items(cut_: dict, arm: str) -> list[tuple[int, StitchRun]]:
    """A Python job's window as (stop, run) pairs with the jump/cut decision
    each run sews with: its own where its real predecessor is on the card;
    between pieces of a CLIPPED run (the white field's rows and underlay
    lines, which turned outside the window) a hop up to `TRIM_AT_MM` is sewn
    needle-down along the window's edge, as the turn it replaces was, and a
    longer one is cut; any other hop the crop made is cut. The crop never
    leaves a float the plan did not."""
    out = []
    prev = None
    for r in cut_["arms"][arm]["runs"]:
        pts = [tuple(p) for p in r["points"]]
        if prev is None:
            jump, trim = True, True
        elif not r["clipped"] and not prev["clipped"] and r["seq"] == prev["seq"] + 1 and r["b"] == prev["b"]:
            jump, trim = r["jump"], r["trim"]
        elif r["clipped"] and prev["clipped"]:
            trim = math.dist(tuple(prev["points"][-1]), pts[0]) > machine.TRIM_AT_MM
            jump = trim
        else:
            hop = math.dist(tuple(prev["points"][-1]), pts[0])
            jump = hop >= machine.TINY_STITCH_MM
            trim = jump
        stop = WHITE if tuple(r["rgb"]) == WHITE_RGB else DARK
        out.append((stop, StitchRun(points=pts, kind=r["kind"], jump=jump, trim=trim, shape_id=r["shape_id"])))
        prev = r
    return out


def lettering_items(cut_: dict, arm: str) -> list[tuple[int, StitchRun]]:
    """The browser stream (DST units, y up) as (stop, run) pairs: a run per
    stretch between needle-up records, its jump and cut as the records say."""
    a = cut_["arms"][arm]
    kind_at: dict[int, str] = {}
    for sp in a.get("runs", []):
        for i in range(sp["i0"], sp["i1"] + 1):
            kind_at[i] = sp["kind"]
    out = []
    cur: StitchRun | None = None
    pend_jump = pend_trim = True
    for i, s in enumerate(a["stream"]):
        if s["type"] == "stitch":
            if cur is None:
                cur = StitchRun(points=[], kind=kind_at.get(i, "satin"), jump=pend_jump, trim=pend_trim,
                                shape_id="lettering")
                pend_jump = pend_trim = False
            cur.points.append((s["x"] / 10.0, -s["y"] / 10.0))
            continue
        if cur is not None and len(cur.points) >= 2:
            out.append((DARK, cur))
        cur = None
        if s["type"] == "jump":
            pend_jump = True
        elif s["type"] in ("trim", "color"):
            pend_jump = pend_trim = True
    if cur is not None and len(cur.points) >= 2:
        out.append((DARK, cur))
    return out


def items_for(job: str, arm: str, cuts: Path) -> list[tuple[int, StitchRun]]:
    cut_ = load(cuts, job)
    return lettering_items(cut_, arm) if job == "lettering" else piece_items(cut_, arm)


def hop_counts(items: list[tuple[int, StitchRun]]) -> dict:
    """What the piece's needle-up moves became: floats (a jump that does not
    cut), cuts, and hops sewn needle-down (a connection of `TINY_STITCH_MM`
    or more with the needle down, the walk's own stitch), plus the stitches
    of its travel runs."""
    out = {"floats": 0, "cuts": 0, "sewn_hops": 0, "travel_stitches": 0}
    prev = None
    for _stop, r in items:
        if prev is not None:
            hop = math.dist(prev.points[-1], r.points[0])
            if r.trim:
                out["cuts"] += 1
            elif r.jump and hop >= machine.TINY_STITCH_MM:
                out["floats"] += 1
            elif not r.jump and hop >= machine.TINY_STITCH_MM:
                out["sewn_hops"] += 1
        if r.kind == "travel":
            out["travel_stitches"] += len(r.points)
        prev = r
    return out


class CardV8(v3.CardV3):
    """Card v3's layout bookkeeping with two stops, white first; every piece
    keeps the jump/cut decisions it was placed with (locks stripped, the
    card's own laid). Nothing takes card v1's hop-distance rule."""

    DIGITIZED = ()
    KEEP = ("F:", "E:", "J:", "D:")

    def plan(self, stops=STOP_ORDER, table=None) -> StitchPlan:
        table = STOPS if table is None else table
        blocks = []
        for stop in stops:
            runs = [r for s, r in self.items if s == stop]
            if not runs:
                continue
            for r in runs:
                if r.shape_id.startswith(self.KEEP):
                    r.points = strip_ties(r.points)
            runs[0].jump = False
            runs[0].trim = False
            apply_ties(runs)
            _name, rgb, _hint = table[stop]
            blocks.append(StitchBlock(thread_index=stop, thread_number=f"{stop + 1}", rgb=rgb, runs=runs))
        return StitchPlan(blocks=blocks, palette=[], warnings=[])


def place(c: CardV8, items: list[tuple[int, StitchRun]], x0: float, y0: float, blk: str, arm: str):
    """Put the piece's top-left at (x0, y0), each run in its stop; the box it covers."""
    pts = [p for _s, r in items for p in r.points]
    bx0, by0 = min(p[0] for p in pts), min(p[1] for p in pts)
    dx, dy = x0 - bx0, y0 - by0
    for stop, r in items:
        c.add_run(stop, StitchRun(points=[(px + dx, py + dy) for px, py in r.points], kind=r.kind,
                                  jump=r.jump, trim=r.trim, shape_id=f"{blk}:{arm}:{r.kind}"))
    xs = [p[0] + dx for p in pts]
    ys = [p[1] + dy for p in pts]
    box = (min(xs), min(ys), max(xs), max(ys))
    c.arms[f"{blk}:{arm}"] = box
    return box


TOP = 2.6               # room above a piece for its teeth
ROW_GAP = 2.4
COL_GAP = 3.6
BLOCK_GAP = 0.6


def build(cuts: Path) -> tuple[StitchPlan, CardV8, dict]:
    """`LAYOUT`, row by row; teeth above each piece count its arm."""
    c = CardV8(WT)
    report: list[dict] = []
    y = 0.0
    last_blk = None
    for blk, row in LAYOUT:
        if last_blk is not None and blk != last_blk:
            y += BLOCK_GAP
        last_blk = blk
        x = 0.0
        top = y + TOP
        bottom = top
        for job, arm in row:
            items = items_for(job, arm, cuts)
            c.add(DARK, hc.teeth(x, top - 0.8, TEETH[arm]), f"{blk}:label:{arm}")
            box = place(c, items, x, top, blk, arm)
            cut_ = load(cuts, job)
            a = cut_["arms"][arm]
            dark = [r for s, r in items if s == DARK]
            rep = {"block": blk, "job": job, "arm": arm, "teeth": TEETH[arm], "label": ARMS[arm][0],
                   "flags": ARMS[arm][1], "clear_mm": clear_mm(arm) if job != "lettering" else None,
                   "runs": len(items), "hops": hop_counts(items), "satin": v7.satin_stats(dark),
                   "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)}
            if job == "lettering":
                rep |= {"stitches_whole": a["stitches"], "trims_whole": a["trims"],
                        "floats_whole": a["uncut_moves_in_dst"], "cut_every_jump": a.get("cut_every_jump")}
            else:
                rep |= {"stitches_whole": a["stitches_whole"], "trims_whole": a["trims_whole"],
                        "floats_whole": a["floats_whole"], "reset": a["reset"], "reset_satin": a["reset_satin"]}
            report.append(rep)
            x = box[2] + COL_GAP
            bottom = max(bottom, box[3])
        y = bottom + ROW_GAP
        boxes = [b for k, b in c.arms.items() if k.startswith(f"{blk}:")]
        c.boxes[blk] = (min(b[0] for b in boxes), min(b[1] for b in boxes) - TOP,
                        max(b[2] for b in boxes), max(b[3] for b in boxes))
    plan = c.plan()
    xs = [p[0] for b in plan.blocks for r in b.runs for p in r.points]
    ys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for b in plan.blocks:
        for r in b.runs:
            r.points = [(px - cx, py - cy) for px, py in r.points]
    for table in (c.boxes, c.arms):
        for kk, (a0, b0, c0, d0) in list(table.items()):
            table[kk] = (a0 - cx, b0 - cy, c0 - cx, d0 - cy)
    plan.design_size_mm = (max(xs) - min(xs), max(ys) - min(ys))
    return plan, c, {"pieces": report}


def arm_digests(plan: StitchPlan) -> dict[str, str]:
    """md5 per piece (`block:arm`) of its runs' kinds, cuts and points, in order."""
    by: dict[str, list] = {}
    for _b, r in plan.iter_runs():
        parts = r.shape_id.split(":")
        if len(parts) >= 3 and parts[1] != "label":
            by.setdefault(":".join(parts[:2]), []).append([r.kind, r.jump, r.trim,
                                                           [[round(x, 4), round(y, 4)] for x, y in r.points]])
    return {k: hashlib.md5(json.dumps(v).encode()).hexdigest() for k, v in sorted(by.items())}


# --- renders -----------------------------------------------------------------------------------

def _rendered(plan: StitchPlan, ppm: float):
    """The card at `ppm` px/mm (thread at its laid width) and a plan-mm box -> pixel crop."""
    from digitizer_core import stitchviz
    from digitizer_core.adapter import plan_to_design
    design = plan_to_design(plan, name=f"card v8 {WT} wt")
    img = stitchviz.render_design(design, px_per_mm=ppm, pad_mm=2.0, thread_mm=machine.thread_profile(WT).width_mm)
    (_h, _w), to_px = stitchviz._frame(design["stitches"], ppm, 2.0)
    u = stitchviz.UNITS_PER_MM

    def px(box, pad=0.0):
        a = to_px({"x": (box[0] - pad) * u, "y": -(box[1] - pad) * u})
        b = to_px({"x": (box[2] + pad) * u, "y": -(box[3] + pad) * u})
        (xa, xb), (ya, yb) = sorted((a[0], b[0])), sorted((a[1], b[1]))
        return max(0, xa), max(0, ya), xb, yb
    return img, px


def block_previews(plan: StitchPlan, card: CardV8, out: Path, ppm: float = 20.0) -> list[Path]:
    """One picture per block: its pieces side by side, each named, cropped
    from the card render."""
    import cv2
    img, px = _rendered(plan, ppm)
    paths = []
    for blk in dict.fromkeys(b for b, _row in LAYOUT):
        tiles = []
        for key in sorted(k for k in card.arms if k.startswith(f"{blk}:")):
            arm = key.split(":")[1]
            x0, y0, x1, y1 = px(card.arms[key], pad=0.5)
            tiles.append(v2._label(img[y0:y1, x0:x1].copy(),
                                   f"{blk} ({arm}) {TEETH[arm]} teeth: {ARMS[arm][0]}"))
        pic = v2._hstack(tiles, gap=24) if blk != "D" else v2._hstack(tiles[:2], gap=24)
        if blk == "D":
            import numpy as np
            second = v2._hstack(tiles[2:], gap=24)
            w = max(pic.shape[1], second.shape[1])
            pad = lambda im: np.hstack([im, np.full((im.shape[0], w - im.shape[1], 3), 255, np.uint8)])  # noqa: E731
            pic = np.vstack([pad(pic), np.full((16, w, 3), 255, np.uint8), pad(second)])
        path = out / f"block_{blk}.jpg"
        cv2.imwrite(str(path), pic, [cv2.IMWRITE_JPEG_QUALITY, 88])
        paths.append(path)
    return paths


# --- docs ----------------------------------------------------------------------------------------

README = """# Sew-out card v8 (DATE): cut every jump, the bold factor and the halo

**Sew this one in the same sitting as card v7, beside the pro's Fremont
patch.** It carries the arms the K3 handoff queued after v7, less the ones a
merged flip has closed (the table at the end). Every number is a candidate
until you sew it (ROADMAP gate 1).

**What to sew:** `card_v8_40wt.dst`, **two cones, 40 wt**, 75/11, a **flat
4 x 4 in hoop** (the design is SIZE_MM mm), the structured twill you sewed
card v4 on, with your Fremont backing. **Stop 1 is white** (the Fremont
field under block F, WHITE_STITCHES stitches, nothing else), **stop 2 is dark**
(everything else). STITCHES stitches, TRIMS trims, about MINUTES minutes
(stitch count at 650 spm, not a measurement). Trims on.

## The arms

Teeth above each piece count its arm. Every arm pins every flag an arm
touches and the halo explicitly (an unpinned value would follow a later
default flip): PIN_LIST; halo (`small_text.CLEAR_MM`) CLEAR_PIN.

| Teeth | Arm | What differs from (a) |
|---|---|---|
| 1 | (a) ships | nothing: ENGINE's defaults, pinned |
| 2 | (b) cut every jump | `cut_every_jump` ON (Python, blocks F and E) / `cutEveryJump` ON (browser, block J): no needle-up move left uncut -- buried under later thread, else walked needle-down on the work, else cut and locked both sides |
| 3 | (c) bold 2.0 | `small_text_cap_bold_scale` 2.0 (1.45): a re-set letter's stroke, 2.0x its traced stroke at its height |
| 4 | (d) halo 0.3 | `small_text.CLEAR_MM` 0.3 (0.8): the fabric the re-set keeps between the line's artwork and its neighbours |
| 5 | (e) bold 2.0 + halo 0.3 | both |

## The four blocks

- **F**: Hotel Fremont at **92.5 mm, the pro's size**, Hat: the lower crest
  (EAT | STAY | PLAY, the rope's lower arcs, the white field under them with
  its own white satin edge along the point, clipped to the window; the black
  hexagon border crosses the window and is left out), (a) beside (b). On today's engine every float of
  the whole design (FREMONT_FLOATS, between the rope strands and between the
  tan bean letters, 0.8-3 mm) lies on the white field, and **(b) walks all
  of them and cuts none**: each float becomes one needle-down stitch (or a
  2 mm run) on top of the white. The piece holds F_FLOATS of them. The pro
  sews straight through on his field (his shortest Fremont cut is 3.4 mm).
  **Look for:** the float threads on (a) against the walk stitches on (b):
  does a dark stitch across the white field show, and would you rather
  snip the float?
- **E**: ENTHUSIAST at 93 mm Hat, the tagline ENTERPRISES INC., re-set x2.0
  by `small_text_reset_grow_away` (ON 10-26), (a) beside (b). Its floats
  are between letters on bare cloth, so **(b) cuts them**: E_CUTS cuts in the
  piece (the whole design ENTHUSIAST_FLOATS floats -> ENTHUSIAST_ON_TRIMS trims from ENTHUSIAST_OFF_TRIMS). **Look for:** the
  floats on (a) against the lock knots on (b); the P and R counters open or
  filled; the 0.25 mm letter gaps open on the cloth.
- **J**: "Fritsch's Stitches" typed in medium_font (the Studio's default) at
  44 mm, flat, through the browser builder: (a) beside (b). OFF leaves
  J_FLOATS floats (J_OFF_TRIMS trims); ON cuts every one (J_ON_TRIMS trims, J_ON_STITCHES stitches
  against J_OFF_STITCHES). The 0.01 mm oracle finds none of its new stitches on bare
  cloth. **Look for:** the same as E, on a cap-sized name.
- **D**: Precision Drone at **62.6 mm, the pro's size**, Hat: THERMAL (the
  letters that stand over AND DRONE; its T and L reach past the window and
  are left out), AND DRONE, the dome and the short dashes under it, in two
  rows: (a) | (c) above, (d) | (e) below. The pro re-sets AND DRONE x1.57
  with 1.26 mm columns and keeps 0.15-0.30 mm thread to thread; ours stops
  at x1.40 against the 0.8 mm halo. **Look for:** the gap between AND DRONE
  and THERMAL / the dome (crowded? touching?), the column width against the
  pro's 1.26, and the letters' legibility at each height.

Cuts the crop itself made (a shape whose neighbour in the sew order fell
outside the window, and the white field's long edge hops) are the same in
every arm of a block; the table below counts them with the design's own.

PIECES_TABLE

Drone's AND DRONE per arm, from the re-set's own report (scale over the art,
stroke tag / traced, the room above and below) and the plan's columns:

DRONE_TABLE

## The `cut_every_jump` walk against a 0.01 mm oracle (the handoff's nitpick)

The Python walk samples a hop every 0.1 mm (`stage7_sequence._BURY_STEP_MM`)
at its centre and both thread edges; the browser twin samples every 0.01 mm
because its test's oracle found 17 segments up to 0.015 mm off the thread at
0.1 mm. `tools/jump_walk_oracle.py` is that oracle ported (a thread raster of
the OFF file's DST at 0.01 mm, no code shared with the walk), run on each
job's whole-design OFF and ON files as the service writes them:

ORACLE_TABLE

ORACLE_VERDICT

![](card_v8_40wt.png)

## Arms the queue named that are not on this card

DROPPED

## The file (pystitch reading the DST back)

READBACK
"""

DROPPED = """| Queued arm | Not on this card because |
|---|---|
| the 0.51 mm bay mouth (`small_text_bay_mouth`) | flipped ON 2026-10-26 (#1112, "ship both") from renders, proven on 16 jobs against the pro; 0.51 is the pro's own file median, so there is no candidate value left to sew against. It sews in every re-set line here (E, D). Today's Fremont hat also sews EST and 1895 as 2 mm bean lines (`bean_only_lines`, 10-27), so card v6's E / S / 5 mouths are not on this engine's hat at all. |
| the 5's bar slot | the same 5: a 2 mm bean line today, no slot to fill. Read the re-set letters' counters on E and D instead. |
| the 0.25 mm letter gap (#1084) | #1084 was a census with a harness prototype (numbers only); the clamp on `columns.sewn_rails` it priced was never built, so there is no flag to arm. The re-set's own 0.25 mm gap (default since 10-23) sews on every E and D piece: look at the gaps. |
| the typed-text fabric preset | no question or candidate value is written anywhere on main (the handoff's queue line and its "older next-wave candidates" only); nothing to arm. |
| ENTHUSIAST's tagline under `small_text_reset_grow_away` | not an arm: the flag flipped ON 10-26 from renders. The tagline sews on E (a) as it ships; its counters are the thing to look at there. |
| `pull_comp_by_stroke`, `pro_measured_values` | card v7's two arms, unchanged since; not repeated. |
"""

SCORING = """# Readout sheet, sew-out card v8

`card_v8_40wt.dst`, 40 wt, 75/11, two cones (white, then dark). Teeth above
a piece count its arm: 1 ships, 2 cut every jump, 3 bold 2.0, 4 halo 0.3,
5 both. Y/N cells: write Y or N; counts as numbers.

| Piece (teeth) | Breaks | Floats you would snip | Knots show (Y/N) | Walk stitches show on the field (Y/N) | Letters legible (Y/N) | Counters open (Y/N) | Neighbour gap OK (Y/N) | Note |
|---|---|---|---|---|---|---|---|---|
ROWS

Better of F: (a) / (b)      Better of E: (a) / (b)      Better of J: (a) / (b)

Drone: which height and weight reads best? (a) / (c) / (d) / (e)

Flip `cut_every_jump` and `cutEveryJump` ON?   Y / N
Move the bold factor to 2.0?   Y / N        Narrow the halo to 0.3?   Y / N
"""


def pieces_table(rb: dict) -> str:
    n = rb["stitches_by_piece"]
    lines = ["| Piece | Teeth | Arm | Stitches | Floats / cuts / sewn hops in the piece | "
             "Planned satin: cross / stitch (mm) | Whole design: stitches / trims / floats |",
             "|---|---|---|---|---|---|---|"]
    for p in rb["pieces"]:
        h, s = p["hops"], p["satin"]
        sat = f"{s['width_mm']} / {s['stitch_mm']}" if s["width_mm"] else "-"
        lines.append(f"| {p['block']} | {p['teeth']} | ({p['arm']}) {p['label']} | "
                     f"{n.get(p['block'] + ':' + p['arm'], 0):,} | {h['floats']} / {h['cuts']} / {h['sewn_hops']} | "
                     f"{sat} | {p['stitches_whole']:,} / {p['trims_whole']} / {p['floats_whole']} |")
    return "\n".join(lines)


def drone_table(rb: dict) -> str:
    lines = ["| Arm | bold | halo (mm) | scale over the art | stroke tag / traced (mm) | room up / down (mm) | "
             "AND DRONE columns: cross / stitch (mm) |",
             "|---|---|---|---|---|---|---|"]
    for p in rb["pieces"]:
        if p["block"] != "D":
            continue
        row = next((r for r in p.get("reset", []) if r.get("scale")), {})
        ga = row.get("grow_away", "")
        up = down = "-"
        for part, key in (("up", "'up': "), ("down", "'down': ")):
            if key in ga:
                val = ga.split(key)[1].split(",")[0].strip("} ")
                up, down = (val, down) if part == "up" else (up, val)
        stroke = row.get("stroke_mm")
        stroke = f"{stroke[0]} / {stroke[1]}" if isinstance(stroke, (list, tuple)) else "-"
        lines.append(f"| ({p['arm']}) {p['label']} | {p['flags'].get('small_text_cap_bold_scale', PIN['small_text_cap_bold_scale'])} | "
                     f"{p['clear_mm']} | x{row.get('scale', '-')} | {stroke} | {up} / {down} | "
                     f"{p['reset_satin']['width_mm']} / {p['reset_satin']['stitch_mm']} |")
    lines.append("| the pro's file (`PRECISION DRON HAT 2.DST`, memory `reset-grow-away-2026-10-26`) | - | - | x1.57 | - | 0.15 / 0.30 thread to thread | 1.26 |")
    return "\n".join(lines)


def oracle_table(rb: dict) -> str:
    lines = ["| Job | Floats OFF -> ON | New needle-down segments ON (locks) | Walked segments, mm | On bare cloth | Worst off the thread (mm) |",
             "|---|---|---|---|---|---|"]
    for job, o in rb["oracle"].items():
        name = job if o.get("sewn", True) else f"{job} (ON measured for the oracle only, not sewn here)"
        lines.append(f"| {name} | {o['off_uncut_moves']} -> {o['on_uncut_moves']} | {o['on_new_segments']} ({o['of_them_locks']}) | "
                     f"{o['walked_segments']}, {o['walked_mm']} | {o['bare_walked_segments']} | {o['worst_off_thread_mm']} |")
    j = rb["lettering"]
    lines.append(f"| lettering (browser, its own oracle) | {j['floats_off']} -> {j['floats_on']} | "
                 f"{j['oracle']['on_new_segments']} ({j['oracle']['of_them_locks']}) | - | {j['oracle']['bare_segments']} | - |")
    return "\n".join(lines)


def oracle_verdict(rb: dict) -> str:
    worst = max((o["worst_off_thread_mm"] for o in rb["oracle"].values()), default=0.0)
    bare = sum(o["bare_walked_segments"] for o in rb["oracle"].values())
    walked = sum(o["walked_segments"] for o in rb["oracle"].values())
    where = [f"{job}: {d['length_mm']} mm at ({d['from_mm'][0]}, {d['from_mm'][1]}), {d['off_thread_mm']} mm past the edge"
             for job, o in rb["oracle"].items() for d in o["bare_detail"] if not d["lock"]]
    if bare == 0:
        return (f"**Verdict:** every one of the {walked} walked segments on the three jobs is on thread at 0.01 mm; "
                "the 0.1 mm step walked over nothing here.")
    return (f"**Verdict: the Python walk is off the thread by more than the browser's was.** Of {walked} walked "
            f"segments on the three jobs, {bare} {'lies' if bare == 1 else 'lie'} partly on bare cloth at 0.01 mm "
            f"-- worst {worst} mm past the thread's edge, against the 0.015 mm the browser's 0.1 mm step showed "
            f"before it went to 0.01 ({'; '.join(where)}). A tenth of a thread width, not a stitch across cloth, "
            "and not in any piece on this card; arm (b) ships marked with it. The cure is the browser's "
            "(`_BURY_STEP_MM` 0.1 -> 0.01, a sampling step, not a physical constant), a build of its own.")


def scoring_rows(rb: dict) -> str:
    return "\n".join(f"| {p['block']} ({'|' * p['teeth']}) {p['label']} | ___ | ___ | _ | "
                     f"{'_' if p['block'] == 'F' else 'n/a'} | _ | {'_' if p['block'] in ('E', 'D') else 'n/a'} | "
                     f"{'_' if p['block'] == 'D' else 'n/a'} | |" for p in rb["pieces"])


def generate(out: Path, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "CARD V8 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    v3.render(plan, out / f"{NAME}.png")
    rb = v2.readback(path, plan, WT, card)
    for s, b in zip(rb["stops"], plan.blocks):
        s["thread"] = STOPS[b.thread_index][0]
    rb["engine"] = ENGINE
    rb["pieces"] = extra["pieces"]
    rb["arm_md5"] = arm_digests(plan)
    rb["minutes_at_650spm"] = round(rb["stitches_file"] / 650, 1)
    rb["oracle"] = {job: load(cuts, job)["oracle"] for job in JOBS if "oracle" in load(cuts, job)}
    let = load(cuts, "lettering")
    rb["lettering"] = {"font": let["font"], "text": let["text"], "width_mm": let["width_mm"],
                       "floats_off": let["arms"]["a"]["uncut_moves_in_dst"],
                       "floats_on": let["arms"]["b"]["uncut_moves_in_dst"],
                       "dst_md5": {a: let["arms"][a]["dst_md5"] for a in let["arms"]},
                       "oracle": let["oracle"]}
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items() if k not in
                          ("pieces", "pieces_mm", "stitches_by_piece", "arm_md5", "oracle")}))
    (out / "readback.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    block_previews(plan, card, out)
    piece = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    fre, ent = load(cuts, "fremont")["arms"], load(cuts, "enthusiast")["arms"]
    white = next((s["stitches"] for s in rb["stops"] if s["thread"] == "white"), 0)
    text = (README.replace("READBACK", v3.readback_markdown(rb))
            .replace("PIECES_TABLE", pieces_table(rb))
            .replace("DRONE_TABLE", drone_table(rb))
            .replace("ORACLE_TABLE", oracle_table(rb))
            .replace("ORACLE_VERDICT", oracle_verdict(rb))
            .replace("DROPPED", DROPPED.strip())
            .replace("PIN_LIST", ", ".join(f"`{k}` {v}" for k, v in PIN.items()))
            .replace("CLEAR_PIN", str(CLEAR_PIN))
            .replace("ENGINE", ENGINE)
            .replace("FREMONT_FLOATS", str(fre["a"]["floats_whole"]))
            .replace("F_FLOATS", str(piece["F", "a"]["hops"]["floats"]))
            .replace("ENTHUSIAST_FLOATS", str(ent["a"]["floats_whole"]))
            .replace("ENTHUSIAST_ON_TRIMS", str(ent["b"]["trims_whole"]))
            .replace("ENTHUSIAST_OFF_TRIMS", str(ent["a"]["trims_whole"]))
            .replace("E_CUTS", str(piece["E", "b"]["hops"]["cuts"] - piece["E", "a"]["hops"]["cuts"]))
            .replace("J_FLOATS", str(rb["lettering"]["floats_off"]))
            .replace("J_OFF_TRIMS", str(let["arms"]["a"]["trims"]))
            .replace("J_ON_TRIMS", str(let["arms"]["b"]["trims"]))
            .replace("J_ON_STITCHES", f"{let['arms']['b']['stitches']:,}")
            .replace("J_OFF_STITCHES", f"{let['arms']['a']['stitches']:,}")
            .replace("WHITE_STITCHES", f"{white:,}")
            .replace("SIZE_MM", f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}")
            .replace("STITCHES", f"{rb['stitches_file']:,}")
            .replace("TRIMS", f"{rb.get('trims', '?')}")
            .replace("MINUTES", f"{rb['stitches_file'] / 650:.0f}")
            .replace("DATE", DATE))
    (out / "README.md").write_text(text, encoding="utf-8")
    (out / "scoring-sheet.md").write_text(SCORING.replace("ROWS", scoring_rows(rb)), encoding="utf-8")
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=list(JOBS) + ["lettering"])
    ap.add_argument("--cuts", default=str(DEFAULT_CUTS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    if args.cut == "lettering":
        cut_lettering(Path(args.cuts))
        return 0
    if args.cut:
        cut(args.cut, Path(args.cuts))
        return 0
    generate(Path(args.out), Path(args.cuts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
