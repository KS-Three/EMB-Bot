"""The eye-pairs reveal gallery: after the blind sitting, one page that
unblinds every pair and collects what the picks cannot carry.

Reads the yardstick's output files (`tools/eye_pairs`, spec section 3.4) and
nothing else; it imports nothing from that package, so the two tables it
shares are restated here and pinned by `tests/test_eye_pairs_gallery.py`.
Refuses until every pair has a pick — the same rule as `--reveal` — because
this page names arms, and naming one before the last pick breaks the repeat
controls. Spec: docs/superpowers/specs/2026-09-17-eye-pairs-gallery-design.md.

    python -m tools.eye_pairs_gallery [--src eye_pairs_out] [--out <src>/gallery]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

BASE = "base"
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "eye_pairs_gallery.html"
DATA_TOKEN = "__GALLERY_DATA__"
BUDGET_BYTES = 60_000_000      # the artifact's per-version limit is 64 MB
MAX_EDGE = 1400                # a render's long edge after re-encoding
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
    "patch_junctions": (
        'satin_patch_junctions="satin"',
        "Cover the bare hole where satin arms meet (a K's crotch) with a small "
        "satin column sewn first, under the arms, instead of a tatami patch "
        "appended last."),
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
    "rail_comp": (
        "satin_rail_comp=True",
        "Put the pull compensation on the rails: satin widens outward along its "
        "cross instead of the polygon buffer, so thread stops landing outside "
        "the artwork."),
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
}

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


def chips(feats: dict, fixture: str, arm: str, choice: str,
          shipped: str, arm_side: str) -> list[dict]:
    """One chip per directional metric that is non-null on both arms and
    differs: which side it prefers, and whether that is the side picked. A
    refusal is carried as a flag, never a drop (yardstick spec section 3.7)."""
    if choice not in ("L", "R"):
        return []
    base_row = feats.get(fixture, {}).get(BASE) or {}
    arm_row = feats.get(fixture, {}).get(arm) or {}
    out: list[dict] = []
    for metric, better in METRIC_BETTER.items():
        bv, av = base_row.get(metric), arm_row.get(metric)
        if bv is None or av is None or bv == av:
            continue
        prefers_arm = av > bv if better == "higher" else av < bv
        prefers = arm_side if prefers_arm else shipped
        refused = bool((base_row.get("refusals") or {}).get(metric)
                       or (arm_row.get("refusals") or {}).get(metric))
        out.append({"metric": metric, "prefers": prefers, "agrees": prefers == choice,
                    "base": bv, "arm": av, "refused": refused})
    return out


def pair_records(public: list[dict], sealed: dict[str, dict], picks: dict[str, dict],
                 feats: dict, sizes: dict[str, tuple[float, str]]) -> list[dict]:
    recs: list[dict] = []
    for p in sorted(public, key=lambda x: x["pair"]):
        pid = p["pair"]
        s, pk = sealed[pid], picks[pid]
        fx, arm, shipped = s["fixture"], arm_of(s), shipped_side(s)
        arm_side = None if shipped is None else ("R" if shipped == "L" else "L")
        width, garment = sizes.get(fx, (None, None))
        change, intent = ARM_INTENT.get(arm, (arm or "", "")) if arm else ("", "")
        recs.append({
            "pair": pid, "kind": s["kind"], "repeat_of": s.get("repeat_of"),
            "fixture": fx, "width_mm": width, "garment": garment,
            "shipped_side": shipped, "arm_side": arm_side, "arm": arm,
            "arm_change": change, "arm_intent": intent,
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


def build(src: Path, out: Path, budget: int = BUDGET_BYTES) -> dict:
    public = json.loads((Path(src) / "pairs.json").read_text(encoding="utf-8"))
    picks = final_picks(Path(src) / "picks.jsonl")
    refuse_if_incomplete([p["pair"] for p in public], picks)
    raise NotImplementedError
