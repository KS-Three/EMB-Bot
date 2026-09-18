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

`--labelled` is the other page this file makes: every rendered arm beside
shipped, BEFORE left and AFTER right, the flag named, Kent's verdict taken on
the page. It needs only `--render`'s output and never a pick — and for that
reason its verdicts are rulings evidence, not the yardstick's statistic.
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
REF_ARM = "ref_0827"
# The yardstick's ref arm runs the old engine in a worktree with no rembg
# venv, so a photo-class fixture's old arm skipped photo prep for an
# ENVIRONMENT reason; its pairs are shown, and marked.
PHOTO_CLASSES = ("photo_subject", "photo_scene")   # digitizer_core.config.PHOTO_CLASSES
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
    "rails_follow_edge": (
        "satin_rails_follow_edge=True",
        "Each satin rail reaches its OWN edge instead of both sitting at the "
        "nearer edge's distance, so the far rail stops falling short of serifs "
        "and tapers (less bare satin); cost is a jitterier rail, more short "
        "stitches on bends, and more thread."),
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
        change, intent = ARM_INTENT.get(arm, (arm or "", "")) if arm else ("", "")
        is_ref = arm == REF_ARM
        base_class = (feats.get(fx, {}).get(BASE) or {}).get("design_class")
        recs.append({
            "pair": pid, "kind": s["kind"], "repeat_of": s.get("repeat_of"),
            "fixture": fx, "width_mm": width, "garment": garment,
            "shipped_side": shipped, "arm_side": arm_side, "arm": arm,
            "arm_change": change, "arm_intent": intent,
            "is_ref": is_ref, "confounded": is_ref and base_class in PHOTO_CLASSES,
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
    """-> (pair id -> {L, R, art} relative names, bytes written). One output
    file per DISTINCT source (sha256 of the source bytes), so a fixture's base
    render — shown in every one of its pairs — is shipped once."""
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
# re-render, a new arm, and a republish.

REVEAL_TITLE = "Eye Pairs Reveal"
LABELLED_TITLE = "Flag Before After"
TITLE_TOKEN = "__GALLERY_TITLE__"


def _stitches(designs: Path, fixture: str, arm: str):
    path = designs / f"{fixture}__{arm}.json"
    if not path.exists():
        raise SystemExit(f"REFUSED: {path} is missing for {fixture} / {arm} "
                         f"-- the yardstick's --render did not finish")
    return json.loads(path.read_text(encoding="utf-8")).get("stitches")


def labelled_sides(rec: dict) -> tuple[str, str]:
    """-> (left arm, right arm). BEFORE is the left side: the shipped engine
    for a flag, the OLD engine for the 08-27 arm, whose AFTER is today."""
    return (rec["arm"], BASE) if rec["is_ref"] else (BASE, rec["arm"])


def labelled_records(src: Path, feats: dict, sizes: dict[str, tuple[float, str]]
                     ) -> tuple[list[dict], list[dict], list[dict]]:
    """-> (pair records, skipped rows, failed rows). One pair per (fixture,
    arm) in features.json whose stitches differ from the base's. An arm that
    raised is a failed row, an identical one a skipped row; neither is shown.
    Arms in the spec's order, then fixtures by name."""
    designs = Path(src) / "designs"
    order = {arm: n for n, arm in enumerate(ARM_INTENT)}
    recs: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for fx in sorted(k for k in feats if k != "__sources__"):
        by_arm = feats[fx]
        base_row = by_arm.get(BASE)
        if not base_row or "error" in base_row:
            failed.append({"fixture": fx, "arm": BASE,
                           "reason": (base_row or {}).get("error", "not rendered")})
            continue
        base_stitches = _stitches(designs, fx, BASE)
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
            is_ref = arm == REF_ARM
            shipped, arm_side = ("R", "L") if is_ref else ("L", "R")
            change, intent = ARM_INTENT.get(arm, (arm, ""))
            rec = {
                "pair": f"{arm}__{fx}", "kind": "live", "repeat_of": None,
                "fixture": fx, "width_mm": width, "garment": garment,
                "shipped_side": shipped, "arm_side": arm_side, "arm": arm,
                "arm_change": change, "arm_intent": intent,
                "is_ref": is_ref, "confounded": is_ref and base_class in PHOTO_CLASSES,
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
        change, intent = ARM_INTENT.get(arm, (arm, ""))
        arms[arm] = {"change": change, "intent": intent, "is_ref": arm == REF_ARM,
                     "n_pairs": sum(1 for r in recs if r["arm"] == arm),
                     "skipped": sum(1 for s in skipped if s["arm"] == arm),
                     "failed": sum(1 for f in failed if f["arm"] == arm)}
    return arms


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


def build(src: Path, out: Path, budget: int = BUDGET_BYTES, labelled: bool = False) -> dict:
    """Reveal: refuse until every pair is picked, then join, copy, emit.
    Labelled: no sitting to wait for; every rendered arm beside shipped.
    Returns the data the page was given, for the caller and the tests."""
    src, out = Path(src), Path(out)
    feats = _read_json(src / "features.json")
    failed: list[dict] = []
    if labelled:
        recs, skipped, failed = labelled_records(src, feats, fixture_sizes())
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
        arms = {arm: {"change": ARM_INTENT.get(arm, (arm, ""))[0],
                      "intent": ARM_INTENT.get(arm, (arm, ""))[1], **t}
                for arm, t in sorted(tally.items())}
        title = REVEAL_TITLE

    names, total = collect_images(src, public, sealed, out / "img", budget)
    for r in recs:
        r["img"] = names[r["pair"]]
    data = {"generated": time.strftime("%Y-%m-%d"), "n_pairs": len(recs),
            "arms": arms, "pairs": recs, "labelled": labelled}
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
    args = ap.parse_args(argv)
    src = Path(args.src)
    out = Path(args.out) if args.out else src / "gallery"
    data = build(src, out, labelled=args.labelled)
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
