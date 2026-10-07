"""The eye-pairs reveal gallery: after the blind sitting, one page that
unblinds every pair and collects what the picks cannot carry.

Reads the yardstick's output files (`tools/eye_pairs`, spec section 3.4) and
nothing else; it imports nothing from that package, so the two tables it
shares are restated here and pinned by `tests/test_eye_pairs_gallery.py`.
Refuses until every pair has a pick — the same rule as `--reveal` — because
this page names arms, and naming one before the last pick breaks the repeat
controls. Spec: docs/superpowers/specs/2026-09-17-eye-pairs-gallery-design.md.

    python -m tools.eye_pairs_gallery [--src eye_pairs_out] [--out <src>/gallery]
    python -m tools.eye_pairs_gallery --labelled    # before | after with the arm named; no sitting
    python -m tools.eye_pairs_gallery --labelled --tables corpus.json   # a measured table under an arm's head
    python -m tools.eye_pairs_gallery --labelled --sitting fold-fix     # a second look at an arm already judged

`--labelled` is the other page this file makes: every rendered arm beside
shipped, BEFORE left and AFTER right, the flag named, Kent's verdict taken on
the page. It needs only `--render`'s output and never a pick — and for that
reason its verdicts are rulings evidence, not the yardstick's statistic.
`--tables` puts a table the instruments measured (the whole corpus under the
arm, say) under that arm's head, so the eye and the numbers sit on one page;
the JSON is `{arm: {caption, columns, rows}}`, refused for an arm the page
does not show. `--sitting <tag>` keys the page's notes `<arm>__<fixture>__<tag>`
for a second look at an arm Kent has judged before (2026-09-30: the dissolve
after the fold fix, judged once on 09-28), so the earlier verdict neither
pre-fills the new pair nor is overwritten by the new one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import cv2
import numpy as np

BASE = "base"
# Fixtures the page never shows -- `tools.eye_pairs.pairs.EXCLUDED_FIXTURES`,
# restated and pinned by test. Kent, 2026-09-30, twice: screenshot is not a
# logo to judge digitizing by. A sitting rendered before the rule still has
# its rows; the labelled page drops them and counts them as excluded.
EXCLUDED_FIXTURES = frozenset({"screenshot"})
# The yardstick's `__ref__` arms: an engine snapshot run out of process, and
# the label the page gives it (BEFORE is that engine on the left, AFTER is
# today on the right). Restated from `tools.eye_pairs.pairs.ARMS` and pinned
# by test; the page reads `is_ref` and `ref_label` off the record, never an
# id, so a second snapshot (2026-09-30, the morning's engine) is a row here.
REF_ARMS: dict[str, str] = {
    "ref_0827": "08-27 engine",
    "ref_0930am": "09-30 morning engine",
}
# The yardstick's `__file__` arms: a professional's machine file for the
# same logo, read as a Design (2026-10-01). OURS is the left side and the
# file the right, under these labels; no flag to flip, so the head takes a
# note and the pair a verdict, like a ref arm.
FILE_ARMS: dict[str, str] = {
    "pro_file": "the pro's file",
}


def arm_kind(arm: str | None) -> str:
    """'ref' (an older engine), 'file' (a stitch file) or 'flag' (a config
    change on today's engine): what the page says on each side and whether
    the arm's head takes a ruling."""
    if arm in REF_ARMS:
        return "ref"
    if arm in FILE_ARMS:
        return "file"
    return "flag"


def side_labels(arm: str | None, kind: str) -> dict[str, str] | None:
    """Labelled page: what each side is called. None for a flag, whose
    labels the page composes itself ('BEFORE · shipped', 'AFTER · <arm> ON')."""
    if kind == "ref":
        return {"L": f"BEFORE · {REF_ARMS[arm]}", "R": "AFTER · today"}
    if kind == "file":
        return {"L": "OURS · today", "R": f"THE PRO · {FILE_ARMS[arm]}"}
    return None
# A ref arm runs the old engine in a worktree, and unless the yardstick
# linked the primary checkout's rembg venv into it (`photo_prep_env` on the
# arm's row, 2026-09-30) a photo-class fixture's old arm skipped photo prep
# for an ENVIRONMENT reason; its pairs are shown, and marked.
PHOTO_CLASSES = ("photo_subject", "photo_scene")   # digitizer_core.config.PHOTO_CLASSES


def confounded(is_ref: bool, base_class, arm_row: dict | None) -> bool:
    """A ref pair on a photo-class fixture whose old engine had no photo
    prep compares lanes, not engines. Kent's one 'before better' of the
    2026-09-30 evening sitting was exactly such a pair (tires)."""
    return bool(is_ref and base_class in PHOTO_CLASSES
                and not (arm_row or {}).get("photo_prep_env", False))
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "eye_pairs_gallery.html"
DATA_TOKEN = "__GALLERY_DATA__"
BUDGET_BYTES = 60_000_000      # the artifact's per-version limit is 64 MB
# A render's long edge after re-encoding. render_design pads 2 mm a side at
# 14 px/mm, so becker at 100 mm is 1456 px: 1500 leaves every fixture unresampled.
MAX_EDGE = 1500
ART_MAX_EDGE = 800
JPEG_Q = 85

# arm id -> (the one change, what it claims to fix). Ids are the yardstick
# spec's section 3.2 table; the intents are each flag's own field doc in
# `digitizer_core/config.py`, shortened, so the page says what the flag
# says of itself.
ARM_INTENT: dict[str, tuple[str, str]] = {
    "per_stroke": (
        "satin_per_stroke=True",
        "Classify each thin stroke on its own, so a stroke pooled with a blob "
        "keeps its satin; a stroke over the width cap is vetoed to fill rather "
        "than sewn as capped satin beside bare cloth."),
    "polygon_axis": (
        'satin_polygon_axis="artwork"',
        "Read the satin axis off the artwork polygon instead of stage 5's grown "
        "one, whose round joins over-stitched drone's M; the rails still sew on "
        "the grown polygon."),
    "area_weighted": (
        "classify_area_weighted=True",
        "Weight the pooled satin/fill gate by area, so a stroke region carrying "
        "a small irregular scrap is promoted to satin (promotion only; scoped "
        "to shapes that are actually strokes)."),
    "design_angle": (
        "design_angle=True",
        "One house angle per design — the lettering stems' perpendicular, else "
        "the design's shared angle — so adjacent fills and non-lettering satin "
        "stop landing on different angles."),
    "rails_follow_edge": (
        "satin_rails_follow_edge=True",
        "Each satin rail reaches its OWN edge instead of both sitting at the "
        "nearer edge's distance, so the far rail stops falling short of serifs "
        "and tapers (less bare satin); cost is a jitterier rail, more short "
        "stitches on bends, and more thread."),
    # `rail_comp` left this table 2026-09-28 and `rail_envelope` 2026-09-30:
    # Kent flipped each on after its labelled sitting, so both are the shipped
    # path, not pending arms.
    "wide_columns": (
        "wide_columns=True",
        "Raise the satin ceiling to 6.5 mm (read off the pro's Becker files) "
        "with per-station curvature caps, so wide letters sew as satin instead "
        "of splitting or dropping to fill."),
    "lettering_column": (
        "lettering_min_column_mm=1.0",
        "Widen sub-floor lettering to a 1.0 mm sewable column instead of the "
        "bean run; known to fill counters at a 2.2 mm cap height."),
    "phantom_dissolve": (
        "dissolve_phantom_blends=True",
        "Dissolve JPEG ringing colours on the photo/gradient lane, so a logo's "
        "anti-alias halo stops sewing as extra grey threads."),
    "directional_comp": (
        "directional_comp=True",
        "Compensate pull along the stitch direction and push across it, per "
        "tier, instead of one isotropic buffer; open satin ends are cut back."),
    "ref_0827": (
        "engine at 25da2fe (main on 2026-08-27)",
        "The engine behind Kent's fourteen 08-27 notes and his 'sixty of a "
        "hundred against Ember' — today against then, drawn by today's renderer."),
    "ref_0930am": (
        "engine at 1e5f8fe2 (main on the morning of 2026-09-30)",
        "The envelope as it shipped that morning, before the day's three "
        "lettering changes: the sibling rule (a reach may not end in another "
        "stroke's corridor, #577), the split comb (one split decision per column, "
        "#578) and the minimum stretch length (a reach shorter than the window is "
        "not a reach, #579). Today against that morning, drawn by today's renderer; "
        "the needle-holes toggle shows the comb the thread render cannot."),
    "split_7mm": (
        "split_satin_above_mm=7.0",
        "Raw satin crosses to about 7 mm and no comb: the house style of the pro "
        "who sewed Becker's own files (they split 1-2% of legs up to 5.5 mm; the "
        "corpus-wide vote is 5.0). The letters' 5-7 mm columns sew as one cross "
        "each -- fewer mid-column holes (the needle-holes toggle shows them), "
        "longer floats. A physical constant under gate 1: the page can say which "
        "reads right, only cloth says which sews right."),
    "pro_file": (
        "the pro's own Becker file (hat, 101.9 mm, PES)",
        "LEFT is our engine's stitches for the Becker logo at 100 mm, as shipped "
        "today. RIGHT is the professional digitizer's stitches for the same logo, "
        "read from the file they sewed (the 101.9 mm hat version) and drawn by the "
        "same renderer; the needle-holes toggle works on both. Nothing to flip: "
        "say which lettering flows, and what the difference is -- the note is the "
        "point."),
    "split_off": (
        "split_satin=False",
        "No comb at all: every satin cross sews rail to rail in one stitch, "
        "however long -- the pro's own style on these letters (his Becker file "
        "sews a quarter of its legs over 5 mm and caps near 7). On Becker every "
        "MARINE stem is 5.5-6.9 mm wide, over the 5.0 mm split threshold, so "
        "today's comb puts a staggered hole in the middle of every cross there: "
        "1,413 holes inside the stems against the pro's 304, and 246 with the "
        "comb off. The needle-holes toggle is where this lives; the thread "
        "render barely moves. The price is the float: legs to 12 mm where a "
        "stroke is that wide (3.4% over 7 mm). A physical constant under gate 1: "
        "the page says which reads right, only cloth says which sews right."),
    "rails_symmetric": (
        "satin_rails_follow_edge=False",
        "Both rails at the nearer edge's distance, as shipped before the envelope: "
        "no reach for the far edge, so the far rail falls short of serifs and "
        "tapers, and the rail carries a third of the envelope's jitter where the "
        "envelope reached. The envelope's coverage against its texture, on the "
        "letters. Say in your own words what 'flow' and 'structured' mean on a "
        "satin letter -- that note is worth more than the verdict."),
    "keep_counters": (
        "keep_counters=True",
        "A letter's counter on a COLOURED ground stays a hole: today a counter "
        "under the small-shape floor is absorbed into the letter around it and "
        "the letter sews as one bar. It cannot read a counter the image has "
        "already closed (bridge's JPEG), and it puts no ground thread in the "
        "hole."),
    "bean_letters": (
        "bean_letter_max_stroke_mm=1.0",
        "Small lettering whose INK strokes are under 1.0 mm sews as three-pass "
        "bean runs along the skeleton of its source ink instead of as satin "
        "blobs, and the ground under it sews through. Its own listed prices, "
        "measured at 80 mm: bridge's RESTAURANT reads R-E-S-T with both A's as "
        "a Y, and HOTEL FREMONT's main wordmark goes bean and loses its slab "
        "serifs. The 1.0 mm line is a gate-1 number set without cloth: the page "
        "says which reads right, only cloth says which sews right."),
    "letterform_priors": (
        "letterform_priors_k=0.75 (built OFF 2026-10-06)",
        "A low-resolution upload's lettering is refit to straight segments and "
        "circular arcs under the word's own stem direction, stroke widths and "
        "baseline before anything is constructed, every vertex moved at most "
        "0.75 of a source pixel and a letter the lines and arcs do not explain "
        "left as traced. Only an upload the engine upscaled is touched: becker "
        "(0.66 mm pixels), bridge (0.29) and gaulke (0.21). Drone, enthusiast "
        "and fremont are byte-identical by design -- that identity is the "
        "flag's first promise, not a failure to act -- and tires has no tagged "
        "lettering. On today's satin the refit sews becker with more columns "
        "and trims (55 -> 66) for less bare cloth."),
}

# Arms that left the pending table because they SHIPPED. A sitting rendered
# before the flip still carries their rows, and the page still names them.
RETIRED_ARM_INTENT: dict[str, tuple[str, str]] = {
    "rail_comp": (
        "satin_rail_comp=True (shipped ON 2026-09-28)",
        "Put the pull compensation on the rails: satin widens outward along its "
        "cross instead of the polygon buffer, so thread stops landing outside "
        "the artwork. Kent flipped it on after the 2026-09-28 sitting."),
    "rail_envelope": (
        'satin_rails_follow_edge="envelope" (shipped ON 2026-09-30)',
        "The far rail extends only where its own edge is at least 0.3 mm "
        "further out than the symmetric width, to the running minimum of that "
        "edge over seven stations. Kent flipped it on after the 2026-09-30 "
        "sitting (2 after, 0 before, golden_tee 'did its job')."),
    # No flip of its own: the junction stack's part C has handed the cover
    # this setting since 2026-09-19, so the arm was identical to the base.
    "patch_junctions": (
        'satin_patch_junctions="satin" (shipped inside satin_junction_stack, '
        "ON 2026-09-19)",
        "Cover the bare hole where satin arms meet (a K's crotch) with a small "
        "satin column sewn first, under the arms. Already the engine as "
        "shipped: the junction stack sews this cover as its part C, so the "
        "flag off and the flag on are one design. Nothing to rule."),
    "cap_recentre": (
        "satin_cap_recentre=True (shipped ON 2026-10-03)",
        "A satin stroke's flat end is rebuilt square where its spine ends in a "
        "surviving cap fork, where it used to taper to a point at one corner "
        "and leave the other bare. Kent flipped it on after the 2026-10-03 "
        "sitting (2 after -- becker and tires, the two the locator boxed -- "
        "0 before)."),
}


def arm_intent(arm: str | None) -> tuple[str, str]:
    """(change, intent) for a pending or a shipped arm; an unknown arm shows
    its id and no intent, and no arm (an identical control) shows nothing."""
    if not arm:
        return ("", "")
    return ARM_INTENT.get(arm) or RETIRED_ARM_INTENT.get(arm) or (arm, "")

# metric -> which way is better. The yardstick spec's section 3.7; `stitches`,
# `stops`, `cones` have no direction and are shown as counts, never chips.
METRIC_BETTER: dict[str, str] = {
    "trims_per_1000": "lower",
    "preflight_raw_score": "higher",
    "preflight_blocks": "lower",
    "uncovered_total_mm2": "lower",
    "thread_worst_delta_e": "lower",
    "artfid": "higher",
    "artfid_no_colour": "higher",
    "artfid_coverage": "higher",
    "artfid_structure": "higher",
    "artfid_colour": "higher",
    "lost_elements": "lower",
    "lost_frac": "lower",
    "ragged_mm": "lower",
    "hausdorff_mm": "lower",
    "roughness_deg": "lower",
    "thin_recall": "higher",
    "legibility": "higher",
}
COUNT_KEYS = ("stitches", "trims_per_1000", "cones")


# ---- picks ------------------------------------------------------------------

def final_picks(path: str | Path) -> dict[str, dict]:
    """pair id -> its FINAL pick; an undo line removes the pair again. The same
    reading as the yardstick's `load_picks`, restated so nothing is imported."""
    picks: dict[str, dict] = {}
    p = Path(path)
    if not p.exists():
        return picks
    for raw in p.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("undo_of"):
            picks.pop(row["undo_of"], None)
        else:
            picks[row["pair"]] = row
    return picks


def refuse_if_incomplete(pair_ids: list[str], picks: dict[str, dict]) -> None:
    missing = [p for p in pair_ids if p not in picks]
    unknown = sorted(set(picks) - set(pair_ids))
    if not missing and not unknown:
        return
    msg = "REFUSED: the sitting is not complete -- "
    msg += f"{len(missing)} of {len(pair_ids)} pairs unpicked"
    if missing:
        msg += f" (first: {missing[0]})"
    if unknown:
        msg += f"; {len(unknown)} pick(s) name unknown pairs: {unknown[:3]}"
    msg += ". This page names arms, so it waits for the last pick, as --reveal does."
    raise SystemExit(msg)


# ---- records ----------------------------------------------------------------

def shipped_side(row: dict) -> str | None:
    left, right = row["left_arm"], row["right_arm"]
    if left == BASE and right == BASE:
        return None
    return "L" if left == BASE else "R"


def arm_of(row: dict) -> str | None:
    left, right = row["left_arm"], row["right_arm"]
    if left == BASE and right == BASE:
        return None
    return right if left == BASE else left


def picked_arm(row: dict, pick: dict) -> str:
    """The ARM NAME on the side Kent picked; a tie is 'tie'. Two showings of
    one pair with swapped sides agree when this agrees, not when the side does."""
    choice = pick["choice"]
    if choice == "tie":
        return "tie"
    return row["left_arm"] if choice == "L" else row["right_arm"]


def _counts(feats: dict, fixture: str, arm: str) -> dict:
    row = feats.get(fixture, {}).get(arm) or {}
    return {k: row.get(k) for k in COUNT_KEYS}


def chip_directions(feats: dict, fixture: str, arm: str,
                    shipped: str, arm_side: str) -> list[dict]:
    """One chip per directional metric that is non-null on both arms and
    differs: which side it prefers, and whether an instrument refused. A
    refusal is carried as a flag, never a drop (yardstick spec section 3.7).
    Direction only: the values stay in features.json, because a review
    sheet carries no scorecard number (acceptance_ab's rule, ROADMAP gate 4)."""
    base_row = feats.get(fixture, {}).get(BASE) or {}
    arm_row = feats.get(fixture, {}).get(arm) or {}
    out: list[dict] = []
    for metric, better in METRIC_BETTER.items():
        bv, av = base_row.get(metric), arm_row.get(metric)
        if bv is None or av is None or bv == av:
            continue
        prefers_arm = av > bv if better == "higher" else av < bv
        refused = bool((base_row.get("refusals") or {}).get(metric)
                       or (arm_row.get("refusals") or {}).get(metric))
        out.append({"metric": metric, "prefers": arm_side if prefers_arm else shipped,
                    "refused": refused})
    return out


def chips(feats: dict, fixture: str, arm: str, choice: str,
          shipped: str, arm_side: str) -> list[dict]:
    """The directions, each with whether it is the side Kent picked. No pick
    (a tie, a control), no chips."""
    if choice not in ("L", "R"):
        return []
    return [{"metric": c["metric"], "prefers": c["prefers"],
             "agrees": c["prefers"] == choice, "refused": c["refused"]}
            for c in chip_directions(feats, fixture, arm, shipped, arm_side)]


def pair_records(public: list[dict], sealed: dict[str, dict], picks: dict[str, dict],
                 feats: dict, sizes: dict[str, tuple[float, str]]) -> list[dict]:
    recs: list[dict] = []
    for p in sorted(public, key=lambda x: x["pair"]):
        pid = p["pair"]
        s, pk = sealed[pid], picks[pid]
        fx, arm, shipped = s["fixture"], arm_of(s), shipped_side(s)
        arm_side = None if shipped is None else ("R" if shipped == "L" else "L")
        width, garment = sizes.get(fx, (None, None))
        change, intent = arm_intent(arm)
        is_ref = arm in REF_ARMS
        base_class = (feats.get(fx, {}).get(BASE) or {}).get("design_class")
        recs.append({
            "pair": pid, "kind": s["kind"], "repeat_of": s.get("repeat_of"),
            "fixture": fx, "width_mm": width, "garment": garment,
            "shipped_side": shipped, "arm_side": arm_side, "arm": arm,
            "arm_change": change, "arm_intent": intent,
            "is_ref": is_ref, "ref_label": REF_ARMS.get(arm),
            "confounded": confounded(is_ref, base_class, feats.get(fx, {}).get(arm)),
            "pick": pk["choice"], "picked_arm": picked_arm(s, pk), "ms": pk.get("ms"),
            "counts": {"L": _counts(feats, fx, s["left_arm"]),
                       "R": _counts(feats, fx, s["right_arm"])},
            "chips": chips(feats, fx, arm, pk["choice"], shipped, arm_side) if arm else [],
            "consistent": None,
        })
    by_id = {r["pair"]: r for r in recs}
    for r in recs:
        if r["kind"] == "repeat" and r["repeat_of"] in by_id:
            r["consistent"] = r["picked_arm"] == by_id[r["repeat_of"]]["picked_arm"]
    return recs


def _empty_tally() -> dict:
    return {"wins": 0, "losses": 0, "ties": 0, "skipped": 0, "by_fixture": {}}


def arm_tally(recs: list[dict], skipped: list[dict]) -> dict[str, dict]:
    """Per arm, its live pairs against shipped as COUNTS, per fixture and
    pooled, plus how many fixtures skipped it as identical. Repeats are the
    consistency control and are not counted twice; never a rate."""
    tally: dict[str, dict] = {}
    for r in recs:
        if r["kind"] != "live" or not r["arm"]:
            continue
        t = tally.setdefault(r["arm"], _empty_tally())
        if r["pick"] == "tie":
            t["ties"] += 1
            t["by_fixture"][r["fixture"]] = "tie"
        elif r["pick"] == r["arm_side"]:
            t["wins"] += 1
            t["by_fixture"][r["fixture"]] = "win"
        else:
            t["losses"] += 1
            t["by_fixture"][r["fixture"]] = "loss"
    for s in skipped:
        tally.setdefault(s["arm"], _empty_tally())["skipped"] += 1
    return tally


def fixture_sizes() -> dict[str, tuple[float, str]]:
    """Width and garment per fixture from the yardstick's own source,
    `tools.thin_strokes.REAL_ART`; an unknown fixture shows blanks."""
    try:
        from tools.thin_strokes import REAL_ART
    except ImportError:
        return {}
    return {name: (float(w), g) for name, (_rel, w, g) in REAL_ART.items()}


# ---- images -----------------------------------------------------------------

def _source_render(src: Path, per_pair_name: str, fixture: str, arm: str) -> Path:
    """The yardstick writes one render per (fixture, arm) under renders/ and a
    copy per pair side under img/; prefer the former, take the latter."""
    unique = src / "renders" / f"{fixture}__{arm}.jpg"
    return unique if unique.exists() else src / "img" / per_pair_name


def _source_art(src: Path, per_pair_name: str, fixture: str) -> Path:
    unique = src / "renders" / f"{fixture}__art.png"
    return unique if unique.exists() else src / "img" / per_pair_name


HOLES_SUFFIX = "__holes"        # tools.eye_pairs.holes_path: renders/<fixture>__<arm>__holes.jpg


def _source_holes(src: Path, fixture: str, arm: str) -> Path | None:
    """The penetration map the yardstick draws beside a render (from
    2026-09-30), when it drew one: a sitting rendered before that has none,
    and the page then shows no toggle. There is no per-pair copy of a map,
    so there is no fallback either."""
    path = src / "renders" / f"{fixture}__{arm}{HOLES_SUFFIX}.jpg"
    return path if path.exists() else None


def _reencode(data: bytes, max_edge: int, png: bool) -> bytes:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise SystemExit("REFUSED: an image could not be decoded")
    h, w = img.shape[:2]
    scale = max_edge / max(h, w)
    if scale < 1.0:
        img = cv2.resize(img, (max(1, round(w * scale)), max(1, round(h * scale))),
                         interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png" if png else ".jpg", img,
                           [] if png else [cv2.IMWRITE_JPEG_QUALITY, JPEG_Q])
    if not ok:
        raise SystemExit("REFUSED: an image could not be re-encoded")
    return buf.tobytes()


def collect_images(src: Path, public: list[dict], sealed: dict[str, dict],
                   out_img: Path, budget: int = BUDGET_BYTES
                   ) -> tuple[dict[str, dict[str, str]], int]:
    """-> (pair id -> {L, R, art[, Lh, Rh]} relative names, bytes written).
    One output file per DISTINCT source (sha256 of the source bytes), so a
    fixture's base render — shown in every one of its pairs — is shipped
    once. `Lh` / `Rh` are the sides' penetration maps, carried only when the
    yardstick drew them."""
    out_img.mkdir(parents=True, exist_ok=True)
    names: dict[str, dict[str, str]] = {}
    seen: dict[str, str] = {}
    total = 0
    for p in public:
        pid = p["pair"]
        s = sealed[pid]
        sources = {
            "L": (_source_render(src, p["left"], s["fixture"], s["left_arm"]), False),
            "R": (_source_render(src, p["right"], s["fixture"], s["right_arm"]), False),
            "art": (_source_art(src, p["art"], s["fixture"]), True),
        }
        for key, arm in (("Lh", s["left_arm"]), ("Rh", s["right_arm"])):
            holes = _source_holes(src, s["fixture"], arm)
            if holes is not None:
                sources[key] = (holes, False)
        names[pid] = {}
        for key, (path, png) in sources.items():
            if not path.exists():
                raise SystemExit(f"REFUSED: {path} is missing for pair {pid} "
                                 f"-- the yardstick's --render did not finish")
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()[:12]
            if digest not in seen:
                encoded = _reencode(data, ART_MAX_EDGE if png else MAX_EDGE, png)
                fname = f"{digest}.{'png' if png else 'jpg'}"
                (out_img / fname).write_bytes(encoded)
                seen[digest] = f"img/{fname}"
                total += len(encoded)
            names[pid][key] = seen[digest]
    if total > budget:
        raise SystemExit(f"REFUSED: gallery images total {total / 1e6:.1f} MB, "
                         f"over the {budget / 1e6:.0f} MB artifact budget "
                         f"(lower MAX_EDGE or JPEG_Q and rerun)")
    return names, total


# ---- change locator ---------------------------------------------------------
# Where a pair changed, as boxes the page outlines and can zoom to. Kent read
# 30 of 77 labelled pairs as "no difference" and 59 of 68 job questions as
# "can't tell" on changes the 2026-09-18 review had measured as LOCAL (0.05
# to 38 percent of a design after a 0.6 mm blur) -- the page pointed at
# nothing (docs/kent-review-2026-09-28.md). The blur drops the stitch-line
# texture and keeps shape, coverage and shade; the threshold is on the blurred
# difference, per channel, so a cone swap at equal brightness still counts.
# Boxes are fractions of the LEFT render, direction only: no share, count or
# value reaches the page.
RENDER_PX_PER_MM = 14.0         # tools.artfid_eye_rank.VIEW_PX_PER_MM, pinned by test
LOCATOR_BLUR_MM = 0.6           # the 09-18 review's blur
LOCATOR_THRESHOLD = 24          # grey levels of 255, on the blurred difference
LOCATOR_MIN_AREA_MM2 = 1.0      # smaller is texture, not a change
MAX_HOTSPOTS = 3


def change_hotspots(left: bytes, right: bytes, px_per_mm: float = RENDER_PX_PER_MM
                    ) -> list[dict]:
    """-> up to MAX_HOTSPOTS boxes {x, y, w, h} in fractions of the left image,
    largest change first; [] when the two renders agree after the blur. A
    right render of another size is resampled to the left's."""
    a = cv2.imdecode(np.frombuffer(left, np.uint8), cv2.IMREAD_COLOR)
    b = cv2.imdecode(np.frombuffer(right, np.uint8), cv2.IMREAD_COLOR)
    if a is None or b is None:
        return []
    if b.shape != a.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    sigma = LOCATOR_BLUR_MM * px_per_mm
    k = int(2 * round(3 * sigma) + 1)
    diff = cv2.absdiff(cv2.GaussianBlur(a, (k, k), sigma),
                       cv2.GaussianBlur(b, (k, k), sigma)).max(axis=2)
    mask = (diff > LOCATOR_THRESHOLD).astype(np.uint8)
    r = max(1, int(round(LOCATOR_BLUR_MM * px_per_mm)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)     # one change, one box
    n, _labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    h, w = mask.shape
    min_area = LOCATOR_MIN_AREA_MM2 * px_per_mm * px_per_mm
    found = sorted((tuple(int(v) for v in stats[i]) for i in range(1, n)
                    if stats[i][cv2.CC_STAT_AREA] >= min_area),
                   key=lambda s: -s[cv2.CC_STAT_AREA])
    boxes = []
    for x, y, bw, bh, _area in found[:MAX_HOTSPOTS]:
        x0, y0 = max(0, x - r), max(0, y - r)
        x1, y1 = min(w, x + bw + r), min(h, y + bh + r)
        boxes.append({"x": round(x0 / w, 4), "y": round(y0 / h, 4),
                      "w": round((x1 - x0) / w, 4), "h": round((y1 - y0) / h, 4)})
    return boxes


def locate_changes(src: Path, public: list[dict], sealed: dict[str, dict]
                   ) -> dict[str, list[dict]]:
    """pair id -> its hotspots, read off the SOURCE renders (full resolution),
    the same files `collect_images` ships. A pair of one render with itself
    (an identical control) gets none."""
    out: dict[str, list[dict]] = {}
    cache: dict[tuple[Path, Path], list[dict]] = {}
    for p in public:
        s = sealed[p["pair"]]
        left = _source_render(src, p["left"], s["fixture"], s["left_arm"])
        right = _source_render(src, p["right"], s["fixture"], s["right_arm"])
        key = (left, right)
        if key not in cache:
            cache[key] = ([] if left == right or not (left.exists() and right.exists())
                          else change_hotspots(left.read_bytes(), right.read_bytes()))
        out[p["pair"]] = cache[key]
    return out


# ---- labelled mode ----------------------------------------------------------
# Before | after with the arm NAMED, built from the rendered arms directly: no
# sitting, no picks, nothing sealed. Kent asked for it on 2026-09-18 ("side by
# side before and after ... feedback for what's working"); the first copy was
# made by hand from this page, published as "Flag Before After", and its
# generator never reached the repo. This is that copy, reproducible. It is NOT
# the yardstick's sitting: a verdict given here is given knowing which side is
# the flag, so it is evidence for his rulings and never the agreement
# statistic (yardstick spec section 4 needs the blind picks). Ids are
# `<arm>__<fixture>` rather than opaque, so a note keyed by one survives a
# re-render, a new arm, and a republish. The same key is a trap the second
# time an arm is judged: Kent's 09-28 verdicts on `phantom_dissolve__*` would
# have pre-filled the fold-fixed renders of 09-30 and been overwritten by his
# new clicks. A sitting tag makes that look its own row: `<arm>__<fixture>__<tag>`.
# The tag has no underscore, so the id still splits on `__`.
SITTING_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,39}$")


def check_sitting(sitting: str | None, labelled: bool) -> str | None:
    """The tag as given, or a refusal: only the labelled page keys notes by
    arm and fixture, and a tag with `__` or a space would not survive as a
    document id."""
    if sitting is None:
        return None
    if not labelled:
        raise SystemExit("REFUSED: --sitting names a labelled page; the reveal keys its pairs itself")
    if not SITTING_TAG.match(sitting):
        raise SystemExit(f"REFUSED: --sitting {sitting!r} must be letters, digits, '.' or '-' "
                         "(no underscore: the id splits on '__')")
    return sitting

REVEAL_TITLE = "Eye Pairs Reveal"
LABELLED_TITLE = "Flag Before After"
TITLE_TOKEN = "__GALLERY_TITLE__"


def _require(path: Path, fixture: str, arm: str) -> Path:
    """Labelled mode has no per-pair copies, so a missing file is named by
    its `--render` path, never by an `img/` fallback that never existed."""
    if not path.exists():
        raise SystemExit(f"REFUSED: {path} is missing for {fixture} / {arm} "
                         f"-- the yardstick's --render did not finish")
    return path


def _stitches(designs: Path, fixture: str, arm: str):
    path = _require(designs / f"{fixture}__{arm}.json", fixture, arm)
    return json.loads(path.read_text(encoding="utf-8")).get("stitches")


def labelled_sides(rec: dict) -> tuple[str, str]:
    """-> (left arm, right arm). BEFORE is the left side: the shipped engine
    for a flag, the OLD engine for a ref arm, whose AFTER is today."""
    return (rec["arm"], BASE) if rec["is_ref"] else (BASE, rec["arm"])


def labelled_records(src: Path, feats: dict, sizes: dict[str, tuple[float, str]],
                     sitting: str | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    """-> (pair records, skipped rows, failed rows). One pair per (fixture,
    arm) in features.json whose stitches differ from the base's. An arm that
    raised is a failed row, an identical one a skipped row; neither is shown.
    The records come in the spec's arm order, then fixture name; the page
    groups by arm and orders the groups itself. `sitting` suffixes every id
    (`<arm>__<fixture>__<sitting>`) for a second look at an arm."""
    designs = Path(src) / "designs"
    renders = Path(src) / "renders"
    order = {arm: n for n, arm in enumerate(ARM_INTENT)}
    recs: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for fx in sorted(k for k in feats if k != "__sources__"):
        if fx in EXCLUDED_FIXTURES:
            continue
        by_arm = feats[fx]
        base_row = by_arm.get(BASE)
        if not base_row or "error" in base_row:
            failed.append({"fixture": fx, "arm": BASE,
                           "reason": (base_row or {}).get("error", "not rendered")})
            continue
        base_stitches = _stitches(designs, fx, BASE)
        _require(renders / f"{fx}__{BASE}.jpg", fx, BASE)
        _require(renders / f"{fx}__art.png", fx, "art")
        width, garment = sizes.get(fx, (None, None))
        base_class = base_row.get("design_class")
        for arm, row in by_arm.items():
            if arm == BASE:
                continue
            if "error" in row:
                failed.append({"fixture": fx, "arm": arm, "reason": row["error"]})
                continue
            if _stitches(designs, fx, arm) == base_stitches:
                skipped.append({"fixture": fx, "arm": arm, "reason": "identical_to_base"})
                continue
            _require(renders / f"{fx}__{arm}.jpg", fx, arm)
            is_ref = arm in REF_ARMS
            kind = arm_kind(arm)
            shipped, arm_side = ("R", "L") if is_ref else ("L", "R")
            change, intent = arm_intent(arm)
            rec = {
                "pair": f"{arm}__{fx}" + (f"__{sitting}" if sitting else ""),
                "kind": "live", "repeat_of": None,
                "fixture": fx, "width_mm": width, "garment": garment,
                "shipped_side": shipped, "arm_side": arm_side, "arm": arm,
                "arm_change": change, "arm_intent": intent,
                "is_ref": is_ref, "ref_label": REF_ARMS.get(arm),
                "arm_kind": kind, "labels": side_labels(arm, kind),
                "confounded": confounded(is_ref, base_class, row),
                "pick": None, "picked_arm": None, "ms": None,
                "chips": chip_directions(feats, fx, arm, shipped, arm_side),
                "consistent": None,
            }
            left_arm, right_arm = labelled_sides(rec)
            rec["counts"] = {"L": _counts(feats, fx, left_arm), "R": _counts(feats, fx, right_arm)}
            recs.append(rec)
    recs.sort(key=lambda r: (order.get(r["arm"], len(order)), r["arm"], r["fixture"]))
    return recs, skipped, failed


def labelled_manifest(recs: list[dict]) -> tuple[list[dict], dict[str, dict]]:
    """The (public, sealed) shape `collect_images` reads, so the labelled page
    ships its renders through the same de-duplicating path as the reveal.
    There is no per-pair copy here, so the fallback names ARE the render
    names: a refusal then says which `--render` file is missing."""
    public, sealed = [], {}
    for r in recs:
        left_arm, right_arm = labelled_sides(r)
        fx = r["fixture"]
        public.append({"pair": r["pair"], "left": f"{fx}__{left_arm}.jpg",
                       "right": f"{fx}__{right_arm}.jpg", "art": f"{fx}__art.png"})
        sealed[r["pair"]] = {"fixture": fx, "left_arm": left_arm, "right_arm": right_arm,
                             "kind": "live", "repeat_of": None}
    return public, sealed


def labelled_arms(recs: list[dict], skipped: list[dict], failed: list[dict]
                  ) -> dict[str, dict]:
    """Per arm: what it is, and how many fixtures it changed, left identical,
    or failed on. No wins or losses -- the page counts Kent's verdicts as he
    gives them, and a null pick is not a loss."""
    order = {arm: n for n, arm in enumerate(ARM_INTENT)}
    seen = [r["arm"] for r in recs] + [s["arm"] for s in skipped] + [f["arm"] for f in failed]
    arms: dict[str, dict] = {}
    for arm in sorted({a for a in seen if a != BASE}, key=lambda a: (order.get(a, len(order)), a)):
        change, intent = arm_intent(arm)
        arms[arm] = {"change": change, "intent": intent, "is_ref": arm in REF_ARMS,
                     "kind": arm_kind(arm),
                     "n_pairs": sum(1 for r in recs if r["arm"] == arm),
                     "skipped": sum(1 for s in skipped if s["arm"] == arm),
                     "failed": sum(1 for f in failed if f["arm"] == arm)}
    return arms


def attach_tables(arms: dict[str, dict], tables: dict | None) -> None:
    """A measured table rides under its arm's head (2026-09-30: the corpus,
    symmetric against envelope, beside the envelope's pairs). Refuses a
    table for an arm the page does not show and a ragged one, so a wrong id
    or a short row never publishes as an empty or a shifted column."""
    for arm, table in (tables or {}).items():
        if arm not in arms:
            raise SystemExit(f"REFUSED: a table for {arm}, which this page does not show")
        cols = table.get("columns") if isinstance(table, dict) else None
        rows = table.get("rows") if isinstance(table, dict) else None
        if not (isinstance(cols, list) and cols and all(isinstance(c, str) for c in cols)):
            raise SystemExit(f"REFUSED: the {arm} table needs a `columns` list of names")
        if not isinstance(rows, list) or any(not isinstance(r, list) or len(r) != len(cols)
                                             for r in rows):
            raise SystemExit(f"REFUSED: every row of the {arm} table needs {len(cols)} cells")
        arms[arm]["table"] = {"caption": str(table.get("caption") or ""),
                              "columns": list(cols), "rows": [list(r) for r in rows]}


# ---- the page ---------------------------------------------------------------

def build_html(data: dict, title: str = REVEAL_TITLE) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    for token in (DATA_TOKEN, TITLE_TOKEN):
        if token not in template:
            raise SystemExit(f"REFUSED: {TEMPLATE.name} has no {token} token")
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return template.replace(DATA_TOKEN, payload).replace(TITLE_TOKEN, title)


def _read_json(path: Path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise SystemExit(f"REFUSED: {path} is missing -- run the yardstick's --render first")
    return json.loads(path.read_text(encoding="utf-8"))


def build(src: Path, out: Path, budget: int = BUDGET_BYTES, labelled: bool = False,
          tables: dict | None = None, sitting: str | None = None) -> dict:
    """Reveal: refuse until every pair is picked, then join, copy, emit.
    Labelled: no sitting to wait for; every rendered arm beside shipped.
    `tables` ({arm: {caption, columns, rows}}) ride under their arms' heads.
    `sitting` (labelled only) tags every pair id and the page's rulings, so a
    second look at an arm keeps its own notes. Returns the data the page was
    given, for the caller and the tests."""
    src, out = Path(src), Path(out)
    sitting = check_sitting(sitting, labelled)
    feats = _read_json(src / "features.json")
    failed: list[dict] = []
    if labelled:
        recs, skipped, failed = labelled_records(src, feats, fixture_sizes(), sitting)
        public, sealed = labelled_manifest(recs)
        arms = labelled_arms(recs, skipped, failed)
        title = LABELLED_TITLE
    else:
        public = _read_json(src / "pairs.json")
        sealed = _read_json(src / "arms.json")
        skipped = _read_json(src / "skipped.json", default=[])
        picks = final_picks(src / "picks.jsonl")
        refuse_if_incomplete([p["pair"] for p in public], picks)
        recs = pair_records(public, sealed, picks, feats, fixture_sizes())
        tally = arm_tally(recs, skipped)
        arms = {arm: {"change": arm_intent(arm)[0], "intent": arm_intent(arm)[1],
                      "is_ref": arm in REF_ARMS, **t}
                for arm, t in sorted(tally.items())}
        title = REVEAL_TITLE
    attach_tables(arms, tables)

    names, total = collect_images(src, public, sealed, out / "img", budget)
    hotspots = locate_changes(src, public, sealed)
    for r in recs:
        r["img"] = names[r["pair"]]
        r["hotspots"] = hotspots[r["pair"]]
    data = {"generated": time.strftime("%Y-%m-%d"), "n_pairs": len(recs),
            "arms": arms, "pairs": recs, "labelled": labelled, "sitting": sitting}
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(build_html(data, title), encoding="utf-8")
    data["_images"] = len({v for d in names.values() for v in d.values()})
    data["_bytes"] = total
    data["_skipped"] = skipped
    data["_failed"] = failed
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", default="eye_pairs_out",
                    help="the yardstick's output dir (default: eye_pairs_out)")
    ap.add_argument("--out", default=None, help="default: <src>/gallery")
    ap.add_argument("--labelled", action="store_true",
                    help="before | after with the arm named, straight from --render's "
                         "output; no sitting, no picks (Kent's flag-review page)")
    ap.add_argument("--tables", default=None,
                    help="JSON {arm: {caption, columns, rows}}: a measured table shown "
                         "under that arm's head (refused for an arm not on the page)")
    ap.add_argument("--sitting", default=None, metavar="TAG",
                    help="labelled only: key this page's notes <arm>__<fixture>__TAG, "
                         "for a second look at an arm judged before (letters, digits, . -)")
    args = ap.parse_args(argv)
    src = Path(args.src)
    out = Path(args.out) if args.out else src / "gallery"
    tables = None
    if args.tables:
        if not Path(args.tables).exists():
            raise SystemExit(f"REFUSED: --tables {args.tables} is missing")
        tables = _read_json(Path(args.tables))
    data = build(src, out, labelled=args.labelled, tables=tables, sitting=args.sitting)
    print(f"{data['n_pairs']} pairs, {len(data['arms'])} arms, "
          f"{data['_images']} images ({data['_bytes'] / 1e6:.1f} MB) -> {out / 'index.html'}")
    if args.labelled:
        print(f"labelled: {len(data['_skipped'])} arm-runs identical to shipped (not shown), "
              f"{len(data['_failed'])} failed")
        for f in data["_failed"]:
            print(f"  FAILED {f['fixture']} / {f['arm']}: {f['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
