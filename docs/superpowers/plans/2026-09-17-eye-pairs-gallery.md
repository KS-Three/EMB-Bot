# Eye-Pairs Reveal Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After the blind eye-pairs sitting, one Artifact page that unblinds every pair — shipped vs arm, Kent's pick, sign chips — and records per pair *did the arm do its job* and per arm *his ruling*, persisted in the artifact's `db`, never in the page.

**Architecture:** One Python generator, `python -m tools.eye_pairs_gallery`, reads the yardstick's output files (`pairs.json`, `arms.json`, `picks.jsonl`, `features.json`, optional `skipped.json`, `renders/` or `img/`), refuses until every pair is picked, de-duplicates and re-encodes the images, and writes `index.html` (pair data inlined as JSON) plus `img/`. The page is a static HTML template with no framework; notes and rulings go to `claude.use("db")` with a `localStorage` fallback; `downloads` offers a JSON export. Published with the Artifact tool, images as `files`.

**Tech Stack:** Python 3.12, numpy, opencv (already in the venv), pytest; plain HTML/CSS/JS; Google Fonts (IBM Plex). **No new dependency.**

**Spec:** `docs/superpowers/specs/2026-09-17-eye-pairs-gallery-design.md` — read it first. One deviation from its §2: `results.json` is NOT read (its exit-clause rows are exactly "chips where `agrees` is false", which the generator computes itself); the spec's "disagreements" filter is defined as *any red chip*.

## Global Constraints

- Run everything from `digitizer/`. This lane has no `.venv`; use the main checkout's interpreter by its 8.3 path (the harness refuses a quoted path with a space): `PY=/c/Users/EE-LT-11030/CLAUDE~4/EMB-Bot/digitizer/.venv/Scripts/python.exe`. On Linux it is `.venv/bin/python`. Always `$PY -m pytest`, never pipe pytest to `tail`.
- `digitizer/tools/` is a NAMESPACE package (no `__init__.py`). Do not add one. Tests put `digitizer/` on `sys.path` the way `tests/test_dropped_elements.py` does (`sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`).
- **Import nothing from `tools/eye_pairs/`** — that package lands on lane `claude/eye-pairs-yardstick`, not this one. Copy the two small tables it shares (arm ids, metric directions) and pin them by test.
- **No digitize anywhere.** Tests build a synthetic `eye_pairs_out/` from the yardstick's schemas with 60×40 images written by `cv2.imwrite`.
- **Refuse before the sitting is complete.** The generator names arms; it raises `SystemExit` while any pair id is unpicked or any pick names an unknown pair.
- **No score, no `%`.** Nothing on the page is a quality number; `preflight_raw_score` is a chip name like any other. A test strips `<style>` and asserts no `%` remains in the emitted HTML.
- Output dir `digitizer/eye_pairs_out/` is gitignored on the yardstick lane by the line `digitizer/eye_pairs_out/`; Task 4 adds the same line here (merges clean).
- Never touch `.claude/worktrees/`. Edit source with the Edit tool, never a PowerShell `-replace | Set-Content` round trip. Stage files by explicit path; never `git add -A`. End every commit message with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Page contract (artifact-design skill): `<title>` first, tokens on bare `:root` with the dark redefinitions under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])` and again under `:root[data-theme="dark"]`; `body` has an explicit token background; 16 px side gutter; works at 400 px; external assets only from the CDN allowlist (Google Fonts stylesheet is allowed).
- Facts measured 2026-09-17 that the code relies on: the yardstick writes `renders/<fixture>__<arm>.jpg` and `renders/<fixture>__art.png` (unique per fixture × arm) AND per-pair copies `img/P###_L.jpg` / `_R.jpg` / `_art.png`; `picks.jsonl` lines are `{"pair","choice":"L"|"R"|"tie"|null,"ms","ts","undo_of":null|"P###"}` and an undo line carries `choice: null`; `features.json` is `fixture -> arm -> row` where a row has `stitches, stops, cones, trims_per_1000`, the metric keys, `refusals: {metric: reason}`, `notes`, and possibly `error`; `arms.json` is `pair -> {fixture, left_arm, right_arm, kind ("live"|"identical"|"repeat"), repeat_of}`; the base arm id is `"base"`.

## File Structure

| file | responsibility |
|---|---|
| `digitizer/tools/eye_pairs_gallery.py` | the generator: tables, picks, records, chips, tallies, images, HTML, CLI |
| `digitizer/tools/eye_pairs_gallery.html` | the page template; `__GALLERY_DATA__` is replaced by the JSON |
| `digitizer/tests/test_eye_pairs_gallery.py` | every test below, plus the synthetic-set builder |
| `.gitignore` (modify) | `digitizer/eye_pairs_out/` |
| `COOKBOOK.md` (modify) | one "Running things" entry |

---

### Task 1: Tables, picks, refusal, pair records (pure)

**Files:**
- Create: `digitizer/tools/eye_pairs_gallery.py`
- Test: `digitizer/tests/test_eye_pairs_gallery.py`

**Interfaces:**
- Produces: `ARM_INTENT: dict[str, tuple[str, str]]`, `METRIC_BETTER: dict[str, str]`, `BASE = "base"`, `final_picks(path) -> dict[str, dict]`, `refuse_if_incomplete(pair_ids: list[str], picks: dict) -> None` (raises `SystemExit`), `shipped_side(row) -> "L"|"R"|None`, `arm_of(row) -> str|None`, `picked_arm(row, pick) -> str`, `chips(feats, fixture, arm, choice, shipped, arm_side) -> list[dict]`, `pair_records(public, sealed, picks, feats, sizes) -> list[dict]`.

- [ ] **Step 1: Write the failing tests and the synthetic-set builder**

```python
# digitizer/tests/test_eye_pairs_gallery.py
"""The reveal gallery, on a synthetic eye_pairs_out/ built from the
yardstick's schemas (spec 2026-09-17-eye-pairs-design.md section 3.4).
No digitize, no real logo, no real render."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import eye_pairs_gallery as g  # noqa: E402

# Restated from the yardstick spec, sections 3.2 and 3.7 / analysis.BETTER.
SPEC_ARMS = ["per_stroke", "patch_junctions", "polygon_axis", "area_weighted",
             "design_angle", "rail_comp", "wide_columns", "lettering_column",
             "phantom_dissolve", "directional_comp", "ref_0827"]
SPEC_METRICS = {
    "trims_per_1000": "lower", "preflight_raw_score": "higher",
    "preflight_blocks": "lower", "uncovered_total_mm2": "lower",
    "thread_worst_delta_e": "lower", "artfid": "higher",
    "artfid_no_colour": "higher", "artfid_coverage": "higher",
    "artfid_structure": "higher", "artfid_colour": "higher",
    "lost_elements": "lower", "lost_frac": "lower", "ragged_mm": "lower",
    "hausdorff_mm": "lower", "roughness_deg": "lower", "thin_recall": "higher",
    "legibility": "higher",
}


def _row(**kw):
    base = {"stitches": 1000, "stops": 3, "cones": 4, "trims_per_1000": 3.0,
            "artfid": 70.0, "lost_elements": 2, "ragged_mm": 0.30,
            "legibility": None, "refusals": {}, "notes": {}}
    base.update(kw)
    return base


PUBLIC = [
    {"pair": "P001", "left": "P001_L.jpg", "right": "P001_R.jpg", "art": "P001_art.png"},
    {"pair": "P002", "left": "P002_L.jpg", "right": "P002_R.jpg", "art": "P002_art.png"},
    {"pair": "P003", "left": "P003_L.jpg", "right": "P003_R.jpg", "art": "P003_art.png"},
    {"pair": "P004", "left": "P004_L.jpg", "right": "P004_R.jpg", "art": "P004_art.png"},
]
SEALED = {
    "P001": {"fixture": "fx_a", "left_arm": "per_stroke", "right_arm": "base",
             "kind": "live", "repeat_of": None},
    "P002": {"fixture": "fx_a", "left_arm": "base", "right_arm": "base",
             "kind": "identical", "repeat_of": None},
    "P003": {"fixture": "fx_b", "left_arm": "base", "right_arm": "polygon_axis",
             "kind": "live", "repeat_of": None},
    "P004": {"fixture": "fx_a", "left_arm": "base", "right_arm": "per_stroke",
             "kind": "repeat", "repeat_of": "P001"},
}
FEATS = {
    "fx_a": {"base": _row(),
             "per_stroke": _row(stitches=1100, trims_per_1000=2.0, artfid=72.0,
                                ragged_mm=0.35)},
    "fx_b": {"base": _row(artfid=60.0, refusals={"artfid": "ink ambiguous"}),
             "polygon_axis": _row(artfid=65.0, lost_elements=1,
                                  refusals={"artfid": "ink ambiguous"})},
}
SKIPPED = [{"fixture": "fx_b", "arm": "design_angle", "reason": "identical_to_base"}]
PICKS = {"P001": "L", "P002": "tie", "P003": "R", "P004": "R"}


def _img(path: Path, colour: tuple[int, int, int], size=(40, 60)) -> None:
    arr = np.zeros((size[0], size[1], 3), np.uint8)
    arr[:] = colour
    cv2.imwrite(str(path), arr)


def make_set(tmp_path: Path, picks: dict[str, str] | None = PICKS,
             renders: bool = True, extra_lines: list[dict] | None = None) -> Path:
    src = tmp_path / "eye_pairs_out"
    (src / "img").mkdir(parents=True)
    (src / "pairs.json").write_text(json.dumps(PUBLIC), encoding="utf-8")
    (src / "arms.json").write_text(json.dumps(SEALED), encoding="utf-8")
    (src / "features.json").write_text(json.dumps(FEATS), encoding="utf-8")
    (src / "skipped.json").write_text(json.dumps(SKIPPED), encoding="utf-8")
    colours = {("fx_a", "base"): (10, 10, 10), ("fx_a", "per_stroke"): (20, 20, 20),
               ("fx_b", "base"): (30, 30, 30), ("fx_b", "polygon_axis"): (40, 40, 40)}
    if renders:
        (src / "renders").mkdir()
        for (fx, arm), c in colours.items():
            _img(src / "renders" / f"{fx}__{arm}.jpg", c)
        _img(src / "renders" / "fx_a__art.png", (200, 200, 200))
        _img(src / "renders" / "fx_b__art.png", (210, 210, 210))
    for p in PUBLIC:
        s = SEALED[p["pair"]]
        _img(src / "img" / p["left"], colours[(s["fixture"], s["left_arm"])])
        _img(src / "img" / p["right"], colours[(s["fixture"], s["right_arm"])])
        _img(src / "img" / p["art"], (200, 200, 200) if s["fixture"] == "fx_a" else (210, 210, 210))
    lines = []
    if picks:
        for n, (pid, choice) in enumerate(picks.items()):
            lines.append({"pair": pid, "choice": choice, "ms": 1000 + n,
                          "ts": "2026-09-17T20:00:00", "undo_of": None})
    lines += extra_lines or []
    (src / "picks.jsonl").write_text(
        "".join(json.dumps(l) + "\n" for l in lines), encoding="utf-8")
    return src


# ---- tables ---------------------------------------------------------------

def test_arm_table_pins_the_yardstick_spec():
    assert sorted(g.ARM_INTENT) == sorted(SPEC_ARMS)
    for arm, (change, intent) in g.ARM_INTENT.items():
        assert change and intent, arm


def test_metric_table_pins_the_yardstick_spec():
    assert g.METRIC_BETTER == SPEC_METRICS


def test_tables_match_the_yardstick_package_when_it_is_here():
    try:
        from tools.eye_pairs import pairs as yp  # noqa: F401
        from tools.eye_pairs import analysis as ya
    except ImportError:
        pytest.skip("yardstick package not on this checkout")
    assert set(yp.ARMS) == set(g.ARM_INTENT)
    assert {m: d for m, d in ya.METRICS.items() if d != "none"} == g.METRIC_BETTER


# ---- picks and the refusal ------------------------------------------------

def test_last_line_wins_and_undo_returns_the_pair(tmp_path):
    src = make_set(tmp_path, picks={"P001": "L"}, extra_lines=[
        {"pair": "P001", "choice": "R", "ms": 5, "ts": "t", "undo_of": None},
        {"pair": "P001", "choice": None, "ms": 6, "ts": "t", "undo_of": "P001"},
        {"pair": "P002", "choice": "tie", "ms": 7, "ts": "t", "undo_of": None},
    ])
    picks = g.final_picks(src / "picks.jsonl")
    assert "P001" not in picks
    assert picks["P002"]["choice"] == "tie"


def test_refuses_on_a_missing_pick(tmp_path):
    src = make_set(tmp_path, picks={"P001": "L", "P002": "tie", "P003": "R"})
    with pytest.raises(SystemExit, match=r"REFUSED.*1 of 4 pairs unpicked.*P004"):
        g.build(src, tmp_path / "gallery")


def test_refuses_on_an_undone_pick(tmp_path):
    src = make_set(tmp_path, extra_lines=[
        {"pair": "P003", "choice": None, "ms": 9, "ts": "t", "undo_of": "P003"}])
    with pytest.raises(SystemExit, match="P003"):
        g.build(src, tmp_path / "gallery")


def test_refuses_on_an_unknown_pair_id(tmp_path):
    src = make_set(tmp_path, extra_lines=[
        {"pair": "P999", "choice": "L", "ms": 9, "ts": "t", "undo_of": None}])
    with pytest.raises(SystemExit, match="unknown"):
        g.build(src, tmp_path / "gallery")


def test_missing_picks_file_is_a_refusal_not_a_crash(tmp_path):
    src = make_set(tmp_path, picks=None)
    (src / "picks.jsonl").unlink()
    with pytest.raises(SystemExit, match="4 of 4"):
        g.build(src, tmp_path / "gallery")


# ---- records --------------------------------------------------------------

def _records():
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in PICKS.items()}
    return {r["pair"]: r for r in g.pair_records(PUBLIC, SEALED, picks, FEATS,
                                                 {"fx_a": (100.0, "left_chest")})}


def test_sides_and_arms_are_read_off_the_sealed_map():
    r = _records()
    assert (r["P001"]["shipped_side"], r["P001"]["arm_side"], r["P001"]["arm"]) == ("R", "L", "per_stroke")
    assert (r["P003"]["shipped_side"], r["P003"]["arm_side"], r["P003"]["arm"]) == ("L", "R", "polygon_axis")
    assert (r["P002"]["shipped_side"], r["P002"]["arm_side"], r["P002"]["arm"]) == (None, None, None)


def test_picked_arm_names_the_arm_on_the_picked_side():
    r = _records()
    assert r["P001"]["picked_arm"] == "per_stroke"   # picked L, L is per_stroke
    assert r["P003"]["picked_arm"] == "polygon_axis"  # picked R, R is polygon_axis
    assert r["P002"]["picked_arm"] == "tie"


def test_width_and_garment_come_from_the_sizes_table_or_are_blank():
    r = _records()
    assert (r["P001"]["width_mm"], r["P001"]["garment"]) == (100.0, "left_chest")
    assert (r["P003"]["width_mm"], r["P003"]["garment"]) == (None, None)


def test_arm_change_and_intent_travel_with_the_record():
    r = _records()
    assert r["P001"]["arm_change"] == g.ARM_INTENT["per_stroke"][0]
    assert r["P002"]["arm_change"] == "" and r["P002"]["arm_intent"] == ""


def test_counts_are_per_side():
    r = _records()
    assert r["P001"]["counts"]["L"]["stitches"] == 1100   # per_stroke on the left
    assert r["P001"]["counts"]["R"]["stitches"] == 1000
    assert r["P001"]["counts"]["L"]["trims_per_1000"] == 2.0


def test_repeat_consistency_compares_the_arm_chosen_not_the_side():
    r = _records()
    # P001 picked L = per_stroke; P004 (sides swapped) picked R = per_stroke.
    assert r["P004"]["consistent"] is True
    assert r["P001"]["consistent"] is None


def test_repeat_flipped_and_tie_tie():
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {**PICKS, "P004": "L"}.items()}
    r = {x["pair"]: x for x in g.pair_records(PUBLIC, SEALED, picks, FEATS, {})}
    assert r["P004"]["consistent"] is False
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {**PICKS, "P001": "tie", "P004": "tie"}.items()}
    r = {x["pair"]: x for x in g.pair_records(PUBLIC, SEALED, picks, FEATS, {})}
    assert r["P004"]["consistent"] is True


# ---- chips ----------------------------------------------------------------

def _chip(chips, metric):
    return next(c for c in chips if c["metric"] == metric)


def test_chips_follow_direction_and_agreement():
    r = _records()
    c = r["P001"]["chips"]   # arm on L, Kent picked L
    assert _chip(c, "trims_per_1000")["prefers"] == "L"    # lower is better: 2.0 < 3.0
    assert _chip(c, "trims_per_1000")["agrees"] is True
    assert _chip(c, "artfid")["prefers"] == "L"            # higher: 72 > 70
    assert _chip(c, "ragged_mm")["prefers"] == "R"         # lower: 0.30 < 0.35
    assert _chip(c, "ragged_mm")["agrees"] is False


def test_no_chip_when_null_or_equal():
    r = _records()
    names = {c["metric"] for c in r["P001"]["chips"]}
    assert "legibility" not in names       # None on both
    assert "lost_elements" not in names    # 2 == 2
    assert "stitches" not in names         # descriptive, never a chip


def test_no_chips_on_ties_or_controls():
    r = _records()
    assert r["P002"]["chips"] == []
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {**PICKS, "P001": "tie"}.items()}
    r2 = {x["pair"]: x for x in g.pair_records(PUBLIC, SEALED, picks, FEATS, {})}
    assert r2["P001"]["chips"] == []


def test_refused_metric_is_flagged_not_dropped():
    r = _records()
    art = _chip(r["P003"]["chips"], "artfid")
    assert art["refused"] is True and art["prefers"] == "R" and art["agrees"] is True
```

- [ ] **Step 2: Run to verify failure**

Run from `digitizer/`: `$PY -m pytest tests/test_eye_pairs_gallery.py -q`
Expected: `ImportError` / `ModuleNotFoundError: No module named 'tools.eye_pairs_gallery'` at collection.

- [ ] **Step 3: Write the module through `pair_records`**

```python
# digitizer/tools/eye_pairs_gallery.py
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


def build(src: Path, out: Path, budget: int = BUDGET_BYTES) -> dict:  # Task 3 fills this in
    public = json.loads((src / "pairs.json").read_text(encoding="utf-8"))
    picks = final_picks(src / "picks.jsonl")
    refuse_if_incomplete([p["pair"] for p in public], picks)
    raise NotImplementedError
```

- [ ] **Step 4: Run the Task 1 tests**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q`
Expected: every test in the tables / picks / records / chips groups PASSES (`test_tables_match_the_yardstick_package_when_it_is_here` SKIPS on this lane). Nothing else is collected yet.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/eye_pairs_gallery.py digitizer/tests/test_eye_pairs_gallery.py
git commit -m "Eye-pairs gallery: pair records, sign chips, and the refusal that waits for the last pick"
```

---

### Task 2: Per-arm tallies and fixture sizes (pure)

**Files:**
- Modify: `digitizer/tools/eye_pairs_gallery.py`
- Test: `digitizer/tests/test_eye_pairs_gallery.py`

**Interfaces:**
- Produces: `arm_tally(recs: list[dict], skipped: list[dict]) -> dict[str, dict]` with keys `wins, losses, ties, skipped, by_fixture: {fixture: "win"|"loss"|"tie"}`; `fixture_sizes() -> dict[str, tuple[float, str]]`.

- [ ] **Step 1: Write the failing tests**

```python
# append to digitizer/tests/test_eye_pairs_gallery.py

# ---- tallies --------------------------------------------------------------

def test_arm_tally_counts_live_pairs_only_and_identical_skips():
    recs = list(_records().values())
    t = g.arm_tally(recs, SKIPPED)
    assert t["per_stroke"] == {"wins": 1, "losses": 0, "ties": 0, "skipped": 0,
                               "by_fixture": {"fx_a": "win"}}   # the repeat P004 is not counted
    assert t["polygon_axis"]["wins"] == 1
    assert t["design_angle"] == {"wins": 0, "losses": 0, "ties": 0, "skipped": 1,
                                 "by_fixture": {}}
    assert BASE not in t


def test_arm_tally_loss_and_tie():
    picks = {pid: {"pair": pid, "choice": c, "ms": 1, "ts": "t", "undo_of": None}
             for pid, c in {**PICKS, "P001": "R", "P003": "tie"}.items()}
    recs = g.pair_records(PUBLIC, SEALED, picks, FEATS, {})
    t = g.arm_tally(recs, [])
    assert (t["per_stroke"]["losses"], t["per_stroke"]["by_fixture"]) == (1, {"fx_a": "loss"})
    assert (t["polygon_axis"]["ties"], t["polygon_axis"]["by_fixture"]) == (1, {"fx_b": "tie"})


def test_fixture_sizes_reads_the_real_art_table():
    sizes = g.fixture_sizes()
    assert sizes["becker"] == (100.0, "left_chest")
    assert sizes["fremont"] == (92.5, "patch")
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q -k "tally or sizes"`
Expected: `AttributeError: module ... has no attribute 'arm_tally'`.

- [ ] **Step 3: Implement**

```python
# insert after pair_records() in digitizer/tools/eye_pairs_gallery.py

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
```

- [ ] **Step 4: Run**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q`
Expected: all pass (one skip).

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/eye_pairs_gallery.py digitizer/tests/test_eye_pairs_gallery.py
git commit -m "Eye-pairs gallery: per-arm win/loss/tie counts and fixture sizes"
```

---

### Task 3: Images — de-duplicate, re-encode, budget

**Files:**
- Modify: `digitizer/tools/eye_pairs_gallery.py`
- Test: `digitizer/tests/test_eye_pairs_gallery.py`

**Interfaces:**
- Produces: `collect_images(src: Path, public, sealed, out_img: Path, budget=BUDGET_BYTES) -> tuple[dict[str, dict[str, str]], int]` — pair id → `{"L": "img/<hash>.jpg", "R": ..., "art": "img/<hash>.png"}` and total bytes written.

- [ ] **Step 1: Write the failing tests**

```python
# append to digitizer/tests/test_eye_pairs_gallery.py

# ---- images ---------------------------------------------------------------

def test_images_are_deduplicated_by_content(tmp_path):
    src = make_set(tmp_path)
    names, total = g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img")
    files = sorted(p.name for p in (tmp_path / "g" / "img").iterdir())
    # 4 distinct renders + 2 artworks; P001/P002/P004 share fx_a base, P002 is base|base.
    assert len(files) == 6
    assert names["P001"]["R"] == names["P002"]["L"] == names["P002"]["R"] == names["P004"]["L"]
    assert names["P001"]["L"] == names["P004"]["R"]
    assert names["P001"]["art"] == names["P002"]["art"] == names["P004"]["art"]
    assert names["P003"]["art"] != names["P001"]["art"]
    assert all(v.startswith("img/") for v in names["P001"].values())
    assert total == sum((tmp_path / "g" / "img" / f).stat().st_size for f in files)


def test_images_fall_back_to_the_per_pair_copies_without_renders(tmp_path):
    src = make_set(tmp_path, renders=False)
    names, _ = g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img")
    assert len(list((tmp_path / "g" / "img").iterdir())) == 6
    assert names["P001"]["R"] == names["P004"]["L"]


def test_renders_are_capped_to_the_long_edge(tmp_path, monkeypatch):
    src = make_set(tmp_path)
    big = np.zeros((300, 3000, 3), np.uint8)
    cv2.imwrite(str(src / "renders" / "fx_a__base.jpg"), big)
    monkeypatch.setattr(g, "MAX_EDGE", 1000)
    names, _ = g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img")
    out = cv2.imread(str(tmp_path / "g" / names["P001"]["R"]))
    assert out.shape[1] == 1000 and out.shape[0] == 100


def test_over_budget_is_refused_with_the_total_named(tmp_path):
    src = make_set(tmp_path)
    with pytest.raises(SystemExit, match=r"REFUSED: gallery images total .* over the 0 MB"):
        g.collect_images(src, PUBLIC, SEALED, tmp_path / "g" / "img", budget=10)
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q -k images`
Expected: `AttributeError ... 'collect_images'`.

- [ ] **Step 3: Implement**

```python
# insert after fixture_sizes() in digitizer/tools/eye_pairs_gallery.py

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
```

- [ ] **Step 4: Run**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q`
Expected: all pass (one skip).

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/eye_pairs_gallery.py digitizer/tests/test_eye_pairs_gallery.py
git commit -m "Eye-pairs gallery: ship each distinct render once, capped and under the artifact budget"
```

---

### Task 4: The HTML emitter, `build`, the CLI, `.gitignore`

**Files:**
- Modify: `digitizer/tools/eye_pairs_gallery.py`
- Create: `digitizer/tools/eye_pairs_gallery.html` (a STUB here; Task 5 writes the real page)
- Modify: `.gitignore`
- Test: `digitizer/tests/test_eye_pairs_gallery.py`

**Interfaces:**
- Produces: `build_html(data: dict) -> str`, `build(src, out, budget) -> dict` (the data it inlined), `main(argv=None) -> int`. The inlined `data` is `{"generated": "YYYY-MM-DD", "n_pairs": int, "arms": {arm: {"change","intent","wins","losses","ties","skipped","by_fixture"}}, "pairs": [record + "img": {L,R,art}]}`.

- [ ] **Step 1: Write the failing tests**

```python
# append to digitizer/tests/test_eye_pairs_gallery.py

# ---- html and the whole build ---------------------------------------------

def _strip_style(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "", html, flags=re.S)


def test_build_writes_index_and_every_referenced_image_exists(tmp_path):
    src = make_set(tmp_path)
    out = tmp_path / "gallery"
    data = g.build(src, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert g.DATA_TOKEN not in html
    refs = set(re.findall(r'img/[0-9a-f]{12}\.(?:jpg|png)', html))
    assert refs and all((out / r).exists() for r in refs)
    assert data["n_pairs"] == 4
    assert data["pairs"][0]["img"]["L"].startswith("img/")
    assert set(data["arms"]) == {"per_stroke", "polygon_axis", "design_angle"}
    assert data["arms"]["design_angle"]["skipped"] == 1
    assert data["arms"]["per_stroke"]["intent"] == g.ARM_INTENT["per_stroke"][1]


def test_html_carries_no_absolute_path_and_no_percent_outside_css(tmp_path):
    src = make_set(tmp_path)
    out = tmp_path / "gallery"
    g.build(src, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert str(tmp_path) not in html and "C:\\" not in html and 'src="/' not in html
    assert "%" not in _strip_style(html)


def test_inlined_json_cannot_close_the_script_tag():
    html = g.build_html({"pairs": [{"arm_intent": "a </script> b"}], "arms": {},
                         "generated": "d", "n_pairs": 1})
    assert "</script> b" not in html and "<\\/script> b" in html


def test_cli_refuses_before_the_sitting_is_complete(tmp_path, capsys):
    src = make_set(tmp_path, picks={"P001": "L"})
    with pytest.raises(SystemExit, match="3 of 4"):
        g.main(["--src", str(src), "--out", str(tmp_path / "gallery")])


def test_cli_builds_and_prints_the_totals(tmp_path, capsys):
    src = make_set(tmp_path)
    assert g.main(["--src", str(src), "--out", str(tmp_path / "gallery")]) == 0
    out = capsys.readouterr().out
    assert "4 pairs" in out and "6 images" in out and "index.html" in out
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q -k "html or cli or build"`
Expected: `NotImplementedError` from the Task 1 stub and `AttributeError ... 'build_html'`.

- [ ] **Step 3: Write the stub template**

```html
<!-- digitizer/tools/eye_pairs_gallery.html — STUB, replaced in Task 5 -->
<title>Eye Pairs Reveal</title>
<style>:root{--bg:#F4F3EF;--ink:#1B1D21}body{background:var(--bg);color:var(--ink);padding-inline:16px}</style>
<main id="main">Loading pairs…</main>
<script>const DATA = __GALLERY_DATA__;</script>
<script>
document.getElementById("main").textContent = DATA.n_pairs + " pairs";
for (const p of DATA.pairs) for (const k of ["L", "R", "art"]) {
  const img = document.createElement("img"); img.src = p.img[k]; document.body.appendChild(img);
}
</script>
```

- [ ] **Step 4: Replace the `build` stub and add the emitter + CLI**

```python
# replace the Task 1 `build` stub at the end of digitizer/tools/eye_pairs_gallery.py

# ---- the page ---------------------------------------------------------------

def build_html(data: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    if DATA_TOKEN not in template:
        raise SystemExit(f"REFUSED: {TEMPLATE.name} has no {DATA_TOKEN} token")
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return template.replace(DATA_TOKEN, payload)


def _read_json(path: Path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise SystemExit(f"REFUSED: {path} is missing -- run the yardstick's --render first")
    return json.loads(path.read_text(encoding="utf-8"))


def build(src: Path, out: Path, budget: int = BUDGET_BYTES) -> dict:
    """Refuse until every pair is picked, then join, copy, emit. Returns the
    data the page was given, for the caller and the tests."""
    src, out = Path(src), Path(out)
    public = _read_json(src / "pairs.json")
    sealed = _read_json(src / "arms.json")
    feats = _read_json(src / "features.json")
    skipped = _read_json(src / "skipped.json", default=[])
    picks = final_picks(src / "picks.jsonl")
    refuse_if_incomplete([p["pair"] for p in public], picks)

    recs = pair_records(public, sealed, picks, feats, fixture_sizes())
    names, total = collect_images(src, public, sealed, out / "img", budget)
    for r in recs:
        r["img"] = names[r["pair"]]
    tally = arm_tally(recs, skipped)
    arms = {arm: {"change": ARM_INTENT.get(arm, (arm, ""))[0],
                  "intent": ARM_INTENT.get(arm, (arm, ""))[1], **t}
            for arm, t in sorted(tally.items())}
    data = {"generated": time.strftime("%Y-%m-%d"), "n_pairs": len(recs),
            "arms": arms, "pairs": recs}
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(build_html(data), encoding="utf-8")
    data["_images"] = len({v for d in names.values() for v in d.values()})
    data["_bytes"] = total
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", default="eye_pairs_out",
                    help="the yardstick's output dir (default: eye_pairs_out)")
    ap.add_argument("--out", default=None, help="default: <src>/gallery")
    args = ap.parse_args(argv)
    src = Path(args.src)
    out = Path(args.out) if args.out else src / "gallery"
    data = build(src, out)
    print(f"{data['n_pairs']} pairs, {len(data['arms'])} arms, "
          f"{data['_images']} images ({data['_bytes'] / 1e6:.1f} MB) -> {out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Add the ignore line**

Append to `.gitignore` (root), after the `digitizer/artfid_eye_out/` line:

```
# Regenerable output of tools/eye_pairs and tools/eye_pairs_gallery -- renders,
# the SEALED arm map, picks, the gallery. The audit-trail copies live in docs/.
digitizer/eye_pairs_out/
```

- [ ] **Step 6: Run everything**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q`
Expected: all pass (one skip). Then from `digitizer/`: `$PY -m tools.eye_pairs_gallery --src /nonexistent` → `REFUSED: ... pairs.json is missing`.

- [ ] **Step 7: Commit**

```bash
git add digitizer/tools/eye_pairs_gallery.py digitizer/tools/eye_pairs_gallery.html digitizer/tests/test_eye_pairs_gallery.py .gitignore
git commit -m "Eye-pairs gallery: emit index.html with the pair data inlined, and the CLI"
```

---

### Task 5: The page

**Files:**
- Replace: `digitizer/tools/eye_pairs_gallery.html`
- Test: the Task 4 tests still pass; the page is verified in the browser pane on the synthetic set (Step 4).

**Interfaces:**
- Consumes: `DATA` as inlined by `build_html` (shape in Task 4).
- Produces: `db` docs `notes/<pair>` = `{job_done, note, updated}` and `rulings/<arm>` = `{ruling, note, updated}`; the export JSON `{exported, notes, rulings}`.

Design plan (artifact-design skill): utilitarian review tool. **Color** — linen ground `#F4F3EF`, surface `#FFFFFF`, ink `#1B1D21`, muted `#676B73`, rule `#DCDAD3`, accent teal `#0E6E66` (the pick ring, focus, buttons), agree `#1E7F4C`, against `#B83A2C`; dark: ground `#141618`, surface `#1D2023`, ink `#E6E7E9`, muted `#9AA0A8`, rule `#2E3237`, accent `#3FB3A8`, agree `#4CC08A`, against `#E8705F`. **Type** — IBM Plex Sans for text, IBM Plex Mono for the subject's own units (mm, stitch counts, trims/1000, arm ids). **Layout** — a sticky bar (group toggle, filter chips, sync mark, save); groups of pair cards; each card: header, arm line, artwork thumb, two renders with synced zoom, counts, chips, the two inputs.

- [ ] **Step 1: Write the page**

```html
<title>Eye Pairs Reveal</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#F4F3EF;--surface:#FFFFFF;--ink:#1B1D21;--muted:#676B73;--rule:#DCDAD3;
  --accent:#0E6E66;--accent-ink:#FFFFFF;--agree:#1E7F4C;--against:#B83A2C;--warn:#8A6D1F;
  --chip-bg:#ECEBE6;--well:#ECEBE6;--paper:#FFFFFF;
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#141618;--surface:#1D2023;--ink:#E6E7E9;--muted:#9AA0A8;--rule:#2E3237;
  --accent:#3FB3A8;--accent-ink:#0F1A19;--agree:#4CC08A;--against:#E8705F;--warn:#E0A84A;--chip-bg:#262A2F;--well:#0F1112;}}
:root[data-theme="dark"]{
  --bg:#141618;--surface:#1D2023;--ink:#E6E7E9;--muted:#9AA0A8;--rule:#2E3237;
  --accent:#3FB3A8;--accent-ink:#0F1A19;--agree:#4CC08A;--against:#E8705F;--warn:#E0A84A;--chip-bg:#262A2F;--well:#0F1112;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 var(--sans);padding-inline:16px;padding-block:0 48px}
h1,h2,h3{margin:0;text-wrap:balance}
code,.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
button{font:inherit;color:inherit;background:none;border:1px solid var(--rule);border-radius:6px;padding:5px 10px;cursor:pointer}
button:focus-visible,textarea:focus-visible,.view:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);border-bottom:1px solid var(--rule);margin-inline:-16px;padding:10px 16px;display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center}
.bar h1{font-size:16px;font-weight:600}
.bar .meta{color:var(--muted);font-size:12px}
.seg{display:inline-flex;border:1px solid var(--rule);border-radius:6px;overflow:hidden}
.seg button{border:0;border-radius:0;padding:5px 10px}
.seg button+button{border-left:1px solid var(--rule)}
.seg button.on{background:var(--accent);color:var(--accent-ink)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{border:1px solid var(--rule);border-radius:999px;padding:2px 10px;font-size:12px;background:var(--chip-bg);cursor:pointer}
.chip.on{border-color:var(--accent);color:var(--accent);background:transparent}
.sync{font-size:12px;color:var(--muted)}
.sync.bad{color:var(--warn)}
.grow{flex:1}
main{display:flex;flex-direction:column;gap:28px;padding-top:20px;max-width:1280px;margin-inline:auto}
.group{display:flex;flex-direction:column;gap:14px}
.armhead{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:14px 16px;display:grid;grid-template-columns:1fr auto;gap:8px 24px;align-items:start}
.armhead h2{font-size:18px;font-weight:600}
.armhead .change{font-family:var(--mono);font-size:12px;color:var(--accent)}
.armhead p{margin:4px 0 0;color:var(--muted);max-width:70ch}
.tally{display:flex;flex-wrap:wrap;gap:6px 14px;font-family:var(--mono);font-size:12px;margin-top:6px}
.tally .w{color:var(--agree)}.tally .l{color:var(--against)}.tally .s{color:var(--muted)}
.strip{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.strip span{font-family:var(--mono);font-size:11px;padding:1px 7px;border-radius:4px;border:1px solid var(--rule)}
.strip .win{border-color:var(--agree);color:var(--agree)}.strip .loss{border-color:var(--against);color:var(--against)}
.ruling{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;border-top:1px solid var(--rule);padding-top:10px}
.ruling label{font-weight:500}
textarea{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--rule);border-radius:6px;padding:6px 8px;min-height:38px;resize:vertical;flex:1;min-width:200px}
.pair{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:12px 16px 14px;display:flex;flex-direction:column;gap:10px}
.pair header{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline}
.pair header .pid{font-family:var(--mono);color:var(--muted)}
.pair header h3{font-size:15px;font-weight:600}
.pair header .size{font-family:var(--mono);font-size:12px;color:var(--muted)}
.kind{font-size:12px;padding:1px 8px;border-radius:4px;border:1px solid var(--rule);color:var(--muted)}
.kind.ok{color:var(--agree);border-color:var(--agree)}.kind.bad{color:var(--against);border-color:var(--against)}
.armline{font-size:13px;color:var(--muted)}
.armline code{color:var(--accent);margin-right:8px}
.art{display:flex;justify-content:center}
.art img{max-height:110px;width:auto;max-width:100%;border:1px solid var(--rule);background:var(--paper)}
.views{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:700px){.views{grid-template-columns:1fr}.armhead{grid-template-columns:1fr}}
.view{position:relative;overflow:hidden;border:2px solid var(--rule);border-radius:8px;background:var(--well);touch-action:none;cursor:grab;aspect-ratio:var(--ar,3/2)}
.view.picked{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 25%,transparent)}
.view img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;transform-origin:0 0;user-select:none;-webkit-user-drag:none;pointer-events:none}
.cap{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline;font-size:12px;margin-top:6px}
.cap .who{font-weight:600}
.cap .who.arm{color:var(--accent)}
.cap .picked{color:var(--accent);font-weight:600}
.cap .n{font-family:var(--mono);color:var(--muted)}
.metrics{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.metrics .lbl{font-size:12px;color:var(--muted);margin-right:4px}
.m{font-family:var(--mono);font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid;cursor:help}
.m.yes{color:var(--agree);border-color:var(--agree)}.m.no{color:var(--against);border-color:var(--against)}
.m.ref{border-style:dashed}
.inputs{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;border-top:1px solid var(--rule);padding-top:10px}
.inputs label{font-weight:500}
.saved{font-size:12px;color:var(--muted);min-width:5ch}
.zoomhint{font-size:11px;color:var(--muted)}
#export{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:12px 16px;display:flex;flex-direction:column;gap:8px}
#export textarea{min-height:120px;font-family:var(--mono);font-size:12px}
.empty{color:var(--muted);padding:40px 0;text-align:center}
@media (prefers-reduced-motion:no-preference){.view img{transition:transform 40ms linear}}
</style>

<header class="bar">
  <div><h1>Eye pairs · reveal</h1><div class="meta" id="meta"></div></div>
  <div class="seg" id="group" role="group" aria-label="Group pairs">
    <button type="button" data-g="arm" class="on" id="g-arm">by arm</button>
    <button type="button" data-g="fixture" id="g-fixture">by fixture</button>
  </div>
  <div class="chips" id="filters" role="group" aria-label="Filter pairs"></div>
  <span class="grow"></span>
  <span class="sync" id="sync">loading…</span>
  <button type="button" id="save">Save notes</button>
</header>
<main id="main"></main>
<section id="export" hidden>
  <strong>Notes as JSON</strong>
  <span class="zoomhint">Saving was not available in this view. Copy this and paste it back to Claude.</span>
  <textarea id="export-text" readonly></textarea>
  <div><button type="button" id="copy">Copy</button> <span class="saved" id="copied"></span></div>
</section>

<script>const DATA = __GALLERY_DATA__;</script>
<script>
(() => {
"use strict";
const FILTERS = [
  ["all", "all", () => true],
  ["arm", "picked arm", p => p.pick !== "tie" && p.pick === p.arm_side],
  ["shipped", "picked shipped", p => p.pick !== "tie" && p.pick === p.shipped_side],
  ["ties", "ties", p => p.pick === "tie"],
  ["controls", "controls", p => p.kind !== "live"],
  ["against", "disagreements", p => p.chips.some(c => !c.agrees)],
];
const JOB = [["yes", "yes"], ["no", "no"], ["unsure", "can't tell"]];
const RULING = [["flip_on", "flip ON"], ["keep_off", "keep OFF"], ["needs_work", "needs work"]];
const state = {group: "arm", filter: "all", notes: {}, rulings: {}};
const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v; else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
  }
  for (const k of kids) if (k != null) n.append(k);
  return n;
};
const fmt = n => n == null ? "—" : Number(n).toLocaleString();

// ---- storage: db when the viewer grants it, localStorage meanwhile --------
const store = {db: null, downloads: null, queue: new Map()};
const lsKey = (kind, id) => `eyepairs:${kind}:${id}`;
function readLocal() {
  try {
    for (const key of Object.keys(localStorage)) {
      const m = /^eyepairs:(notes|rulings):(.+)$/.exec(key);
      if (m) state[m[1]][m[2]] = JSON.parse(localStorage.getItem(key));
    }
  } catch (e) { /* storage unavailable: render without it */ }
}
function writeLocal(kind, id, body) {
  try { localStorage.setItem(lsKey(kind, id), JSON.stringify(body)); } catch (e) { /* ignore */ }
}
async function connect() {
  const sync = $("#sync");
  const claude = window.claude;
  if (!claude || typeof claude.use !== "function") { sync.textContent = "not synced · local only"; sync.classList.add("bad"); return; }
  const [db, downloads] = await Promise.all([claude.use("db"), claude.use("downloads")]);
  store.downloads = downloads;
  if (!db) { sync.textContent = "not synced · local only"; sync.classList.add("bad"); return; }
  store.db = db;
  try {
    for (const kind of ["notes", "rulings"]) {
      const snap = await db.collection(kind).get();
      for (const d of snap.docs) { state[kind][d.id] = d.data(); writeLocal(kind, d.id, d.data()); }
    }
    sync.textContent = "synced"; sync.classList.remove("bad");
    render();
  } catch (e) {
    sync.textContent = "not synced · " + (e && e.code ? e.code : "error"); sync.classList.add("bad");
  }
}
// One write in flight per document; a burst collapses to the last body.
async function persist(kind, id, body, savedEl) {
  state[kind][id] = body; writeLocal(kind, id, body);
  if (!store.db) { if (savedEl) savedEl.textContent = "kept locally"; return; }
  const key = kind + "/" + id;
  if (store.queue.has(key)) { store.queue.set(key, body); return; }
  store.queue.set(key, body);
  try {
    let pending;
    while ((pending = store.queue.get(key)) !== undefined) {
      store.queue.set(key, undefined);
      await store.db.doc(key).set(pending);
      if (savedEl) savedEl.textContent = "saved";
    }
  } catch (e) {
    if (savedEl) savedEl.textContent = "not saved · " + (e && e.code ? e.code : "error");
    $("#sync").textContent = "not synced"; $("#sync").classList.add("bad");
  } finally { store.queue.delete(key); }
}
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

// ---- export ----------------------------------------------------------------
function exportJSON() {
  return JSON.stringify({exported: new Date().toISOString(), notes: state.notes, rulings: state.rulings}, null, 1);
}
async function saveNotes() {
  const text = exportJSON();
  const name = "eye-pairs-notes-" + new Date().toISOString().slice(0, 10) + ".json";
  if (store.downloads) {
    try { await store.downloads.save({filename: name, data: text}); return; }
    catch (e) { if (e && e.code === "declined") return; }
  }
  $("#export").hidden = false; $("#export-text").value = text; $("#export").scrollIntoView({block: "nearest"});
}

// ---- synced zoom -------------------------------------------------------------
function attachZoom(views) {
  const z = {s: 1, x: 0, y: 0};
  const apply = () => { for (const v of views) v.img.style.transform = `translate(${z.x}px,${z.y}px) scale(${z.s})`; };
  for (const v of views) {
    v.box.addEventListener("wheel", e => {
      e.preventDefault();
      const r = v.box.getBoundingClientRect();
      const px = e.clientX - r.left, py = e.clientY - r.top;
      const factor = Math.exp(-e.deltaY * 0.0015);
      const ns = Math.min(12, Math.max(1, z.s * factor));
      z.x = px - (px - z.x) * (ns / z.s); z.y = py - (py - z.y) * (ns / z.s); z.s = ns;
      if (z.s === 1) { z.x = 0; z.y = 0; }
      apply();
    }, {passive: false});
    let drag = null;
    v.box.addEventListener("pointerdown", e => { drag = {x: e.clientX - z.x, y: e.clientY - z.y}; v.box.setPointerCapture(e.pointerId); });
    v.box.addEventListener("pointermove", e => { if (!drag || z.s === 1) return; z.x = e.clientX - drag.x; z.y = e.clientY - drag.y; apply(); });
    const end = () => { drag = null; };
    v.box.addEventListener("pointerup", end); v.box.addEventListener("pointercancel", end);
    v.box.addEventListener("dblclick", () => { z.s = 1; z.x = 0; z.y = 0; apply(); });
  }
}

// ---- render --------------------------------------------------------------------
function kindBadge(p) {
  if (p.kind === "identical") return el("span", {class: "kind", text: "identical control"});
  if (p.kind === "repeat") {
    const ok = p.consistent === true;
    return el("span", {class: "kind " + (ok ? "ok" : "bad"), text: `repeat of ${p.repeat_of} · ${ok ? "consistent" : "flipped"}`});
  }
  return null;
}
function viewFor(p, side) {
  const who = p.shipped_side === null ? "shipped (both)" : (side === p.shipped_side ? "shipped" : p.arm);
  const isArm = p.shipped_side !== null && side !== p.shipped_side;
  const picked = p.pick === side;
  const img = el("img", {src: p.img[side], alt: `${p.fixture} ${who}`, loading: "lazy"});
  const box = el("div", {class: "view" + (picked ? " picked" : ""), tabindex: "0", title: "wheel to zoom, drag to pan, double-click to reset"}, img);
  img.addEventListener("load", () => { box.style.setProperty("--ar", `${img.naturalWidth}/${img.naturalHeight}`); }, {once: true});
  const c = p.counts[side] || {};
  const cap = el("div", {class: "cap"},
    el("span", {class: "who" + (isArm ? " arm" : ""), text: who}),
    picked ? el("span", {class: "picked", text: "picked"}) : (p.pick === "tie" ? el("span", {class: "n", text: "tie"}) : null),
    el("span", {class: "n", text: `${fmt(c.stitches)} st`}),
    el("span", {class: "n", text: `${c.trims_per_1000 == null ? "—" : c.trims_per_1000} trims/1000`}),
    el("span", {class: "n", text: `${fmt(c.cones)} cones`}));
  return {box, img, fig: el("figure", {style: "margin:0"}, box, cap)};
}
function chipsRow(p) {
  if (!p.chips.length) return null;
  const row = el("div", {class: "metrics"}, el("span", {class: "lbl", text: "instruments"}));
  for (const c of p.chips) {
    const dir = c.prefers === p.arm_side ? p.arm : "shipped";
    row.append(el("span", {class: "m " + (c.agrees ? "yes" : "no") + (c.refused ? " ref" : ""),
      text: c.metric, title: `${c.metric} prefers ${dir}: shipped ${c.base} vs ${p.arm} ${c.arm}${c.refused ? " · instrument refused this artwork" : ""}`}));
  }
  return row;
}
function segControl(options, current, onPick) {
  const seg = el("div", {class: "seg"});
  for (const [val, label] of options) {
    const b = el("button", {type: "button", class: val === current ? "on" : "", text: label});
    b.addEventListener("click", () => { for (const x of seg.children) x.classList.toggle("on", x === b); onPick(val); });
    seg.append(b);
  }
  return seg;
}
function pairCard(p) {
  const L = viewFor(p, "L"), R = viewFor(p, "R");
  attachZoom([L, R]);
  const note = state.notes[p.pair] || {job_done: null, note: ""};
  const saved = el("span", {class: "saved"});
  const write = body => persist("notes", p.pair, {...body, updated: new Date().toISOString()}, saved);
  const ta = el("textarea", {id: `note-${p.pair}`, placeholder: "note — what your eye saw", text: note.note || ""});
  ta.addEventListener("input", debounce(() => write({job_done: (state.notes[p.pair] || {}).job_done ?? null, note: ta.value}), 600));
  const card = el("article", {class: "pair", id: p.pair},
    el("header", {},
      el("span", {class: "pid", text: p.pair}),
      el("h3", {text: p.fixture}),
      p.width_mm != null ? el("span", {class: "size", text: `${p.width_mm} mm · ${p.garment}`}) : null,
      kindBadge(p)),
    p.arm ? el("div", {class: "armline"}, el("code", {text: p.arm_change}), p.arm_intent) : null,
    el("div", {class: "art"}, el("img", {src: p.img.art, alt: `${p.fixture} artwork`, loading: "lazy"})),
    el("div", {class: "views"}, L.fig, R.fig),
    chipsRow(p),
    p.arm ? el("div", {class: "inputs"},
      el("label", {for: `note-${p.pair}`, text: "Did the arm do what it claims?"}),
      segControl(JOB, note.job_done, v => write({job_done: v, note: ta.value})),
      ta, saved) : null);
  return card;
}
function armHead(arm, a) {
  const r = state.rulings[arm] || {ruling: null, note: ""};
  const saved = el("span", {class: "saved"});
  const write = body => persist("rulings", arm, {...body, updated: new Date().toISOString()}, saved);
  const ta = el("textarea", {id: `ruling-${arm}`, placeholder: "why", text: r.note || ""});
  ta.addEventListener("input", debounce(() => write({ruling: (state.rulings[arm] || {}).ruling ?? null, note: ta.value}), 600));
  const strip = el("div", {class: "strip"});
  for (const [fx, res] of Object.entries(a.by_fixture || {})) strip.append(el("span", {class: res, text: `${fx} ${res}`}));
  return el("section", {class: "armhead"},
    el("div", {}, el("h2", {text: arm}), el("div", {class: "change", text: a.change}), el("p", {text: a.intent})),
    el("div", {},
      el("div", {class: "tally"},
        el("span", {class: "w", text: `${a.wins} wins`}), el("span", {class: "l", text: `${a.losses} losses`}),
        el("span", {text: `${a.ties} ties`}), el("span", {class: "s", text: `${a.skipped} identical, not shown`})),
      strip),
    el("div", {class: "ruling"},
      el("label", {for: `ruling-${arm}`, text: "Your ruling"}),
      segControl(RULING, r.ruling, v => write({ruling: v, note: ta.value})),
      ta, saved));
}
function render() {
  const main = $("#main");
  main.replaceChildren();
  const keep = FILTERS.find(f => f[0] === state.filter)[2];
  const pairs = DATA.pairs.filter(keep);
  $("#meta").textContent = `${DATA.n_pairs} pairs · ${Object.keys(DATA.arms).length} arms · built ${DATA.generated} · ${pairs.length} shown`;
  if (!pairs.length) { main.append(el("div", {class: "empty", text: "No pairs match this filter."})); return; }
  const groups = new Map();
  for (const p of pairs) {
    const key = state.group === "arm" ? (p.arm || "controls") : p.fixture;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(p);
  }
  const keys = [...groups.keys()].sort((a, b) => (a === "controls") - (b === "controls") || a.localeCompare(b));
  for (const key of keys) {
    const g = el("section", {class: "group"});
    if (state.group === "arm" && DATA.arms[key]) g.append(armHead(key, DATA.arms[key]));
    else g.append(el("h2", {text: key, style: "font-size:18px"}));
    for (const p of groups.get(key)) g.append(pairCard(p));
    main.append(g);
  }
}
function boot() {
  readLocal();
  const filters = $("#filters");
  for (const [id, label] of FILTERS) {
    const b = el("button", {type: "button", class: "chip" + (id === state.filter ? " on" : ""), text: label});
    b.addEventListener("click", () => { state.filter = id; for (const x of filters.children) x.classList.toggle("on", x === b); render(); });
    filters.append(b);
  }
  for (const b of $("#group").children) b.addEventListener("click", () => {
    state.group = b.dataset.g; for (const x of $("#group").children) x.classList.toggle("on", x === b); render();
  });
  $("#save").addEventListener("click", saveNotes);
  $("#copy").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("#export-text").value); $("#copied").textContent = "copied"; }
    catch (e) { $("#export-text").select(); $("#copied").textContent = "select and copy"; }
  });
  render();
  connect();
}
boot();
})();
</script>
```

- [ ] **Step 2: Run the generator tests again**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q`
Expected: all pass — in particular `test_html_carries_no_absolute_path_and_no_percent_outside_css` (the only `%` in the page is inside `<style>`).

- [ ] **Step 3: Build the synthetic gallery for the browser**

From `digitizer/`, a throwaway script in the scratchpad that calls `tests.test_eye_pairs_gallery.make_set(<scratch>)` then `g.build(src, <scratch>/gallery)`. Serve it: add to `.claude/launch.json` a configuration

```json
{
  "name": "eye-pairs-gallery",
  "runtimeExecutable": "python",
  "runtimeArgs": ["-m", "http.server", "8741", "--directory", "<absolute scratch path>/gallery"],
  "port": 8741
}
```

(The scratch path is machine-local; do NOT commit this launch entry — add it, use it, and `git checkout .claude/launch.json` before the PR. The 8.3 path avoids the space.)

- [ ] **Step 4: Verify in the browser pane and keep the evidence**

`preview_start {name: "eye-pairs-gallery"}`, then: `read_console_messages` (no errors; `claude.use` is absent here so the sync mark reads *not synced · local only*), `read_page` (4 cards, two arm headers, the `controls` group, the `repeat of P001 · consistent` badge, chips `trims_per_1000` / `artfid` green and `ragged_mm` red on P001), click `by fixture` and `disagreements` and confirm the card set changes, type a note and reload — it comes back (localStorage), click `Save notes` — the export box appears with the JSON, `resize_window` mobile — one column, no horizontal scroll, `colorScheme: "dark"` — tokens swap. Screenshot light, dark, mobile. Fix anything found in the template, re-run Step 2.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/eye_pairs_gallery.html
git commit -m "Eye-pairs gallery: the page -- synced zoom, sign chips, and notes that live in the artifact's db"
```

---

### Task 6: Write it down, review, PR

**Files:**
- Modify: `COOKBOOK.md` ("Running things")
- The PR

- [ ] **Step 1: COOKBOOK entry**

Under "Running things", after the entry for `tools/eye_pairs` if the yardstick PR has merged, else at the end of the list:

```markdown
- **Eye-pairs reveal gallery** — `cd digitizer && python -m tools.eye_pairs_gallery`
  reads `eye_pairs_out/` (the yardstick's `pairs.json`, `arms.json`,
  `picks.jsonl`, `features.json`, `renders/`) and writes
  `eye_pairs_out/gallery/index.html` + `img/`. **Refuses until every pair is
  picked** — it names arms. Publish `index.html` as an Artifact with `img/*`
  as `files` and `capabilities: {db: {}, downloads: true}`; Kent's per-pair
  "did it do its job" and per-arm rulings land in the artifact's `db`
  (`notes/<pair>`, `rulings/<arm>`), read back with `ArtifactData` and
  committed as `docs/eye-pairs-<date>/kent-notes.json`. Spec:
  `docs/superpowers/specs/2026-09-17-eye-pairs-gallery-design.md`.
```

- [ ] **Step 2: Full suite touch-point**

Run: `$PY -m pytest tests/test_eye_pairs_gallery.py -q` and `$PY -m pytest tests/test_thin_strokes.py -q` (the one existing module the generator imports). Expected: green.

- [ ] **Step 3: Adversarial re-read**

Dispatch `emb-bot-reviewer` on the diff (`git diff origin/main...HEAD`). Fix what it finds; re-run Step 2.

- [ ] **Step 4: Commit docs, push, open the PR ready-for-review, arm auto-merge**

```bash
git add COOKBOOK.md
git commit -m "COOKBOOK: how to build and publish the eye-pairs reveal gallery"
git push -u origin claude/eye-pairs-gallery
```

PR body: what it is (the after-the-sitting page), what it refuses, what it does not do (no picking, no statistic, no engine change), the browser-pane evidence, and the note that it consumes the yardstick lane's file contracts and pins its two tables by test. Mark ready for review; arm auto-merge while `mergeable_state` is `blocked`.

## After the PR — publishing (not code)

Once the yardstick PR has merged and Kent has finished the sitting (`--reveal` ran): `python -m tools.eye_pairs_gallery`, then `Artifact` publish `eye_pairs_out/gallery/index.html` with `files` = every `img/*`, `capabilities: {db: {}, downloads: true}`, favicon `🧵`, description *"Every eye-pairs pair unblinded — shipped vs arm, Kent's pick, sign chips — with his notes and rulings."* Read `notes/` and `rulings/` back with `ArtifactData` and commit them as `docs/eye-pairs-<date>/kent-notes.json` with a short `docs/kent-review-<date>.md`.
