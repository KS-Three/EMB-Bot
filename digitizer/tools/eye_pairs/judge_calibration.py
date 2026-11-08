"""A calibrated vision judge, phase A: the split, the calibration kit, the page.

Kent, 2026-11-07: "why don't we develop a new yard stick that develops you
into reviewing these like a human? Maybe a side by side camparison of
ambiguous photos that can point you in the right direction."

The protocol is `docs/eye-pairs-2026-11-04/calibrated-judge/PRE-REGISTRATION.md`
(committed before any picture was opened). This module does three things and
judges nothing:

    python -m tools.eye_pairs.judge_calibration split   [--check]
    python -m tools.eye_pairs.judge_calibration kit     --out DIR [--runs DIR] [--trees DIR]
    python -m tools.eye_pairs.judge_calibration serve   --kit DIR [--port 8733]

* `split` pools every Kent-labelled pair the two session judges read (54 on
  11-04, 99 on 11-06), de-duplicated by (sitting, fixture, arm), and splits it
  ONCE under `SEED` into CALIBRATION (~40%) and HELD-OUT (~60%), stratified by
  design and by Kent's pick class. The manifest is two files of pair ids and
  nothing else (no label, no arm, no side): `split-calibration.json` and
  `split-held-out.json`. `--check` recomputes and compares.
* `kit` reads `split-calibration.json` ONLY (`_kit_read` refuses any other
  manifest file), picks up to `KIT_MAX` pairs where the old judge and Kent
  disagreed, from the verdict files already committed, and writes a review
  kit: both renders at one scale, a 3x crop of the region that differs most,
  Kent's original pick, the old judge's verdict and reason, and a box for
  Kent's one-line reason. 11-04 pictures are copied from the surviving
  `eye_pairs_out/pro-lettering-1102/img/`; the 11-06 kit's pictures are gone,
  so its calibration pairs' designs (and no others) are re-drawn on their
  sittings' trees exactly as `pro_pooled_build render --sitting-size` drew them.
* `serve` serves that page on localhost and saves every reason to
  `<kit>/reasons.json`, which phase B reads. Opened from disk instead, the page
  keeps reasons in the browser and offers the same JSON as a download.

    python -m tools.eye_pairs.judge_calibration heldout-kit [--out DIR] [--sealed DIR] [--reuse-runs DIR]

* `heldout-kit` (phase B, after the rubric freeze) draws every HELD-OUT pair
  plus the kits' identical controls the way `kit` drew its pairs, under blind
  ids H001.. in one seeded shuffle. The judge's folder gets `packets.json`
  (blind id + absolute picture paths, nothing else) and `img/`; the key
  (blind id -> pool id, kind, base side), the designs and any drop reasons go
  to a SEPARATE sealed folder the judge is never shown.

    python -m tools.eye_pairs.judge_calibration score [--out DIR]

* `score` (after the one blind run) reads `heldout-verdicts.jsonl` and the
  key copied beside it (`heldout-key.json`), maps L / R to before / after, and
  writes the pre-registered primary, secondaries and the old judges' baseline
  on the same pairs to `heldout-analysis.json`.

The held-out list is read by `split --check`, by tests, by phase B's scoring
and by `heldout-kit`, which writes no label, verdict, arm or side where the
judge reads. The calibration kit never reads it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
DIGITIZER = HERE.parents[2]
REPO = DIGITIZER.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools.eye_pairs import vlm_judge as vj  # noqa: E402

OUT = REPO / "docs" / "eye-pairs-2026-11-04" / "calibrated-judge"
CALIBRATION_FILE = "split-calibration.json"
HELD_OUT_FILE = "split-held-out.json"
SEED = 20261107
CAL_FRACTION = 0.40
KIT_MAX = 25

#: The two judged sets, by the directory their verdicts live in. A pool id is
#: `<set>:<kit pair id>`: the id the judge saw, so the manifest unseals nothing.
SET_1104 = "vlm-judge"
SET_1106 = "vlm-judge-100"
VERDICTS = {SET_1104: vj.OUT / f"verdicts-{vj.SESSION_MODEL}.jsonl",
            SET_1106: vj.PRO100_OUT / "verdicts-claude-opus-5-5-session.jsonl"}
#: 11-04: the pairs whose pick was seen while that kit was built (Amendment 1).
EXCLUDED_1104 = frozenset({"P001", "P002", "P003"})
SITTING_1102 = "pro-size-lettering-1102"

#: Disagreement classes (old judge vs Kent, ties in).
CLASS_JUDGE_TIE = "judge_tie_kent_side"
CLASS_KENT_TIE = "judge_side_kent_tie"
CLASS_OPPOSITE = "opposite_sides"
CLASSES = (CLASS_JUDGE_TIE, CLASS_KENT_TIE, CLASS_OPPOSITE)

#: The pass bar (PRE-REGISTRATION.md): both must hold, on HELD-OUT only.
PASS_KAPPA = 0.55
PASS_CI_LOWER = 0.34


# ------------------------------------------------------------------ the pool ----

def _arm_of(s: dict) -> str:
    return s["left_arm"] if s["left_arm"] != "base" else s["right_arm"]


def sealed_1104() -> dict:
    """11-04's sitting: sealed key per kit pair, with Kent's label, design and
    dedup key. Live pairs only, Amendment 1's exclusions out."""
    st = vj.load_sitting()
    out = {}
    for pid, s in sorted(st["sealed"].items()):
        if s["kind"] != "live" or pid in EXCLUDED_1104 or pid not in st["picks"]:
            continue
        out[pid] = {**s, "kent": vj.to_label(st["picks"][pid], s),
                    "design": st["design_of"][s["fixture"]],
                    "key": (SITTING_1102, s["fixture"], _arm_of(s))}
    return out


def sealed_1106() -> dict:
    """11-06's kit rebuilt (`vlm_judge.pro100_sealed`): live pairs only."""
    out = {}
    for pid, s in vj.pro100_sealed().items():
        if s["kind"] != "live":
            continue
        out[pid] = {**s, "design": s["fixture"], "key": (s["sitting"], s["fixture"], s["arm"])}
    return out


def pool(sets: dict[str, dict] | None = None) -> list[dict]:
    """Every Kent-labelled pair, de-duplicated by (sitting, fixture, arm): the
    first set listed keeps a pair both hold. -> rows {id, set, pair, design, kent}."""
    sets = sets if sets is not None else {SET_1104: sealed_1104(), SET_1106: sealed_1106()}
    seen, rows = set(), []
    for name, sealed in sets.items():
        for pid, s in sorted(sealed.items()):
            key = tuple(s["key"])
            if key in seen:
                continue
            seen.add(key)
            rows.append({"id": f"{name}:{pid}", "set": name, "pair": pid,
                         "design": s["design"], "kent": s["kent"]})
    return rows


def stratum(row: dict) -> tuple[str, str]:
    return (row["design"], row["kent"])


def split(rows: list[dict], *, seed: int = SEED, fraction: float = CAL_FRACTION) -> dict:
    """Seeded, stratified, systematic: strata (design, Kent's class) in sorted
    order, each one's ids shuffled, then every position i of the concatenation
    goes to CALIBRATION when floor(f*(i+1)+u) > floor(f*i+u), u drawn once from
    the seed. Each stratum gets its share to within one pair; the whole gets
    round(f*n) to within one."""
    rng = random.Random(seed)
    by: dict[tuple, list[str]] = {}
    for r in rows:
        by.setdefault(stratum(r), []).append(r["id"])
    order: list[str] = []
    for key in sorted(by):
        ids = sorted(by[key])
        rng.shuffle(ids)
        order += ids
    u = rng.random()
    cal, held = [], []
    for i, pid in enumerate(order):
        (cal if math.floor(fraction * (i + 1) + u) > math.floor(fraction * i + u) else held).append(pid)
    return {"calibration": sorted(cal), "held_out": sorted(held)}


def pool_sha(rows: list[dict]) -> str:
    """Hash of the pool's ids and strata: a changed input moves it, so a stale
    manifest is caught by `--check` and by the test."""
    blob = json.dumps(sorted([r["id"], *stratum(r)] for r in rows), separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def manifest_payloads(rows: list[dict]) -> dict[str, dict]:
    sp = split(rows)
    common = {"seed": SEED, "fraction": CAL_FRACTION, "n_pool": len(rows), "pool_sha256": pool_sha(rows),
              "rule": "PRE-REGISTRATION.md, 'The split'"}
    return {CALIBRATION_FILE: {**common, "part": "calibration", "ids": sp["calibration"]},
            HELD_OUT_FILE: {**common, "part": "held_out", "ids": sp["held_out"]}}


def do_split(a) -> int:
    rows = pool()
    payloads = manifest_payloads(rows)
    out = Path(a.out)
    if a.check:
        bad = [n for n, p in payloads.items()
               if json.loads((out / n).read_text(encoding="utf-8")) != p]
        print(json.dumps({"n_pool": len(rows), "stale": bad}))
        return 1 if bad else 0
    out.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        path = out / name
        text = json.dumps(payload, indent=1) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != text:
            raise SystemExit(f"REFUSED: {path} exists and differs; the split is made once.")
        path.write_text(text, encoding="utf-8")
    cal = payloads[CALIBRATION_FILE]["ids"]
    print(json.dumps({"n_pool": len(rows), "calibration": len(cal),
                      "held_out": len(payloads[HELD_OUT_FILE]["ids"])}))
    return 0


# ------------------------------------------------------------- phase B's read ----

def primary(rows: list[tuple[str, str, str]]) -> dict:
    """The pre-registered primary on HELD-OUT: `rows` = (kent, judge, design)
    labels in before / tie / after. The repo's own `vlm_judge._kappas` (3-way
    linear-weighted kappa, ties in; percentile bootstrap over pairs and over
    designs; `pooled.reading`), plus the pass bar."""
    res = vj._kappas(rows)
    k, ci = res.get("kappa_3way"), res.get("ci3_pairs")
    res["passes"] = bool(k is not None and ci and ci[0] is not None
                         and k >= PASS_KAPPA and ci[0] > PASS_CI_LOWER)
    res["bar"] = {"kappa_at_least": PASS_KAPPA, "ci_pairs_lower_above": PASS_CI_LOWER}
    return res


# ------------------------------------------------------------ the kit: reads ----

def _kit_read(name: str, out: Path | None = None) -> dict:
    """The ONLY way the kit builder reads the manifest. It opens the
    calibration file and refuses every other name, the held-out file first."""
    if name != CALIBRATION_FILE:
        raise PermissionError(f"the kit builder reads {CALIBRATION_FILE} only, not {name!r}")
    return json.loads(((out or OUT) / name).read_text(encoding="utf-8"))


def disagreement_class(kent: str, judge: str) -> str | None:
    """before / tie / after on both sides -> the class, or None when they agree."""
    if kent == judge:
        return None
    if judge == "tie":
        return CLASS_JUDGE_TIE
    if kent == "tie":
        return CLASS_KENT_TIE
    return CLASS_OPPOSITE


def _verdict_rows(path: Path, wanted: set[str]) -> dict[str, dict]:
    """Order-A rows of one verdicts file, for the wanted pair ids only (the
    last row per pair wins, as in `vlm_judge.load_verdicts`)."""
    out: dict[str, dict] = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if raw.strip():
            r = json.loads(raw)
            if r.get("order", "A") == "A" and r["pair"] in wanted:
                out[r["pair"]] = r
    return out


def _side_of(label: str, s: dict) -> str:
    """before / tie / after -> L / R / tie in the kit's frame (the inverse of
    `vlm_judge.to_label`)."""
    if label == "tie":
        return "tie"
    want = "base" if label == "before" else _arm_of(s)
    return "L" if s["left_arm"] == want else "R"


def select(cal_ids: list[str], sets: dict[str, dict], verdict_files: dict[str, Path], *,
           seed: int = SEED, k: int = KIT_MAX) -> list[dict]:
    """Every CALIBRATION pair where the committed verdict and Kent disagree,
    up to `k` (a seeded round-robin across the classes when there are more),
    in class order then pool id. -> rows with Kent's and the judge's pick in
    the kit's L / R frame, the judge's confidence and reason."""
    cal = set(cal_ids)
    by_set: dict[str, list[str]] = {}
    for pid in cal_ids:
        name, pair = pid.split(":", 1)
        by_set.setdefault(name, []).append(pair)
    found: dict[str, list[dict]] = {c: [] for c in CLASSES}
    for name, pairs in sorted(by_set.items()):
        rows = _verdict_rows(verdict_files[name], set(pairs))
        for pair in sorted(pairs):
            s, r = sets[name].get(pair), rows.get(pair)
            if s is None or r is None or r.get("choice") is None:
                continue
            judge = vj.to_label(r["choice_frame_a"], s)
            cls = disagreement_class(s["kent"], judge)
            if cls is None:
                continue
            found[cls].append({"id": f"{name}:{pair}", "set": name, "pair": pair, "class": cls,
                               "kent": _side_of(s["kent"], s), "judge": r["choice_frame_a"],
                               "confidence": r.get("confidence"), "reason": r.get("reason")})
    total = sum(len(v) for v in found.values())
    if total > k:
        rng = random.Random(seed)
        pools = {c: sorted(v, key=lambda x: x["id"]) for c, v in found.items()}
        for v in pools.values():
            rng.shuffle(v)
        keep: list[dict] = []
        while len(keep) < k:
            for c in CLASSES:
                if pools[c] and len(keep) < k:
                    keep.append(pools[c].pop(0))
        found = {c: [x for x in keep if x["class"] == c] for c in CLASSES}
    picked = [x for c in CLASSES for x in sorted(found[c], key=lambda x: x["id"])]
    for x in picked:
        assert x["id"] in cal, f"{x['id']} is not a CALIBRATION pair"
    return picked


# ----------------------------------------------------------- the kit: pictures ----

def _pad(img, h: int, w: int):
    import numpy as np
    out = np.full((h, w, 3), 255, dtype=np.uint8)
    y, x = (h - img.shape[0]) // 2, (w - img.shape[1]) // 2
    out[y:y + img.shape[0], x:x + img.shape[1]] = img
    return out


def diff_window(a, b) -> dict:
    """Two renders on one canvas -> the square window where they differ most:
    the integer shift that best aligns b to a (phase correlation; ignored past
    a tenth of the canvas), then the box of side `s` whose summed |a - b| is
    largest. -> {x, y, s, dx, dy} in canvas pixels; b's window is a's shifted
    by (dx, dy)."""
    import cv2
    import numpy as np
    ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = ga.shape
    (dx, dy), _resp = cv2.phaseCorrelate(ga, gb)
    dx, dy = int(round(dx)), int(round(dy))
    if abs(dx) > w // 10 or abs(dy) > h // 10:
        dx = dy = 0
    m = np.float32([[1, 0, -dx], [0, 1, -dy]])
    gb_aligned = cv2.warpAffine(gb, m, (w, h), borderValue=255.0)
    diff = np.abs(ga - gb_aligned)
    s = int(max(48, min(240, min(h, w) // 4)))
    s = min(s, h, w)
    score = cv2.boxFilter(diff, -1, (s, s), normalize=False, borderType=cv2.BORDER_CONSTANT)
    cy, cx = np.unravel_index(int(np.argmax(score)), score.shape)
    x = int(min(max(cx - s // 2, 0), w - s))
    y = int(min(max(cy - s // 2, 0), h - s))
    return {"x": x, "y": y, "s": s, "dx": dx, "dy": dy, "differs": bool(diff.max() > 0)}


def _crop3(img, x: int, y: int, s: int):
    import cv2
    h, w = img.shape[:2]
    x, y = min(max(x, 0), w - s), min(max(y, 0), h - s)
    return cv2.resize(img[y:y + s, x:x + s], (3 * s, 3 * s), interpolation=cv2.INTER_NEAREST), x, y


def write_pair_images(kid: str, left: Path, right: Path, art: Path, img_dir: Path) -> dict:
    """LEFT / RIGHT padded to one canvas (same scale: both were drawn at
    14 px/mm), the artwork, and the 3x crops. -> the window, in canvas px."""
    import cv2
    import shutil
    a, b = cv2.imread(str(left)), cv2.imread(str(right))
    if a is None or b is None:
        raise FileNotFoundError(f"{kid}: unreadable render ({left}, {right})")
    h, w = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    pa, pb_ = _pad(a, h, w), _pad(b, h, w)
    img_dir.mkdir(parents=True, exist_ok=True)
    q = [cv2.IMWRITE_JPEG_QUALITY, 95]
    for src, orig, padded, side in ((left, a, pa, "L"), (right, b, pb_, "R")):
        dst = img_dir / f"{kid}_{side}.jpg"
        if orig.shape[:2] == (h, w) and src.suffix.lower() in (".jpg", ".jpeg"):
            shutil.copyfile(src, dst)                     # already the canvas: the bytes Kent saw
        elif not cv2.imwrite(str(dst), padded, q):
            raise OSError(f"could not write {dst}")
    win = diff_window(pa, pb_)
    ca, xa, ya = _crop3(pa, win["x"], win["y"], win["s"])
    cb, xb, yb = _crop3(pb_, win["x"] + win["dx"], win["y"] + win["dy"], win["s"])
    for crop, side in ((ca, "L"), (cb, "R")):
        if not cv2.imwrite(str(img_dir / f"{kid}_{side}x3.png"), crop):
            raise OSError(f"could not write the {side} crop of {kid}")
    shutil.copyfile(art, img_dir / f"{kid}_art.png")
    return {"w": w, "h": h, "s": win["s"], "L": [xa, ya], "R": [xb, yb],
            "shift": [win["dx"], win["dy"]], "differs": win["differs"]}


def sources_1104(pair: str, src: Path) -> tuple[Path, Path, Path]:
    """The surviving 11-04 pictures: exactly the files Kent and the judge saw."""
    img = src / "img"
    return img / f"{pair}_L.jpg", img / f"{pair}_R.jpg", img / f"{pair}_art.png"


def designs_1106(s: dict) -> list[tuple[str, str, str, str]]:
    """The designs one 11-06 sealed pair shows, as (tree, fixture, side, kwargs
    json): both for a live pair, the base alone for an identical control (as
    `vlm_judge.kit_pro100` drew it on both sides)."""
    shown = (s["before_design"],) if s["kind"] == "identical" else (s["before_design"], s["after_design"])
    return [(tree, s["fixture"], side, json.dumps(kw, sort_keys=True)) for tree, side, kw in shown]


def draw_designs(keys: list[tuple], runs: Path, trees: Path, *, python: str, use_slot: bool = True,
                 holder: str = "judge_calibration", tolerate: bool = False) -> dict[tuple, str]:
    """Draw every design key not already on disk under the 11-06 rule
    (`pro_pooled_build.render_one`, the sitting's tree and size, the laptop's
    CPU slot, one design at a time). -> {key: error} for the designs that
    failed; with `tolerate` False the first failure raises instead."""
    from tools.eye_pairs import pro_pooled_build as pb
    keys = list(dict.fromkeys(keys))
    todo = [k for k in keys if not (pb.design_dir(runs, k[0], k[1], k[2]) / "design.json").exists()]
    print(f"{len(keys)} designs; {len(todo)} to draw", flush=True)
    failed: dict[tuple, str] = {}
    if not todo:
        return failed
    slot = pb.Slot(pb.default_slot() if use_slot else None, holder)
    slot.acquire()
    try:
        for sha in dict.fromkeys(k[0] for k in todo):
            mine = [k for k in todo if k[0] == sha]
            try:
                tree = pb.ensure_tree(trees, sha)
            except Exception as e:  # noqa: BLE001 - a tree that will not check out fails its designs
                if not tolerate:
                    raise
                for k in mine:
                    failed[k] = f"tree {sha}: {type(e).__name__}: {str(e)[-300:]}"
                print(f"  tree {sha} FAILED: {e}", flush=True)
                continue
            try:
                for _t, fixture, side, kw in mine:
                    slot.rotate_if_due(pb.TAKE_MIN)
                    try:
                        meta = pb.render_one(tree, fixture, pb.design_dir(runs, sha, fixture, side),
                                             json.loads(kw), python, size=pb.sitting_size(fixture))
                    except Exception as e:  # noqa: BLE001
                        if not tolerate:
                            raise
                        failed[(sha, fixture, side, kw)] = f"{type(e).__name__}: {str(e)[-300:]}"
                        print(f"  {sha}/{fixture}/{side}: FAILED {str(e)[-200:]}", flush=True)
                        continue
                    print(f"  {sha}/{fixture}/{side}: {meta['stitches']} stitches, {meta['wall_s']} s", flush=True)
            finally:
                pb.discard_worktree(pb.REPO, trees / sha)
    finally:
        slot.release()
    return failed


def render_1106(picked: list[dict], sealed: dict, runs: Path, trees: Path, *,
                python: str, use_slot: bool = True) -> None:
    """Re-draw the designs of the 11-06 pairs in the kit, and no others, under
    the 11-06 rule (`draw_designs`; a design already on disk is kept)."""
    keys = [k for x in picked if x["set"] == SET_1106 for k in designs_1106(sealed[x["pair"]])]
    print("the 11-06 pairs in the kit:", end=" ", flush=True)
    draw_designs(keys, runs, trees, python=python, use_slot=use_slot,
                 holder="judge_calibration kit (calibration pairs only)")


def sources_1106(pair: str, sealed: dict, runs: Path, work: Path) -> tuple[Path, Path, Path]:
    """One 11-06 pair's pictures, as `vlm_judge.kit_pro100` made them: each
    design through `_design_jpg`, the base on the side the sealed key says (an
    identical control shows the base on both)."""
    from tools.artfid_eye_rank import _normalise_art
    from tools.eye_pairs import pro_pooled_build as pb
    s = sealed[pair]
    before = vj._design_jpg(pb.design_dir(runs, s["before_design"][0], s["fixture"], s["before_design"][1]))
    art = work / f"{SET_1106}_{pair}_art.png"
    work.mkdir(parents=True, exist_ok=True)
    _normalise_art(DIGITIZER / "testdata" / pb.FIXTURE_ART[s["fixture"]], art)
    if s["kind"] == "identical":
        return before, before, art
    after = vj._design_jpg(pb.design_dir(runs, s["after_design"][0], s["fixture"], s["after_design"][1]))
    return (before, after, art) if s["left_arm"] == "base" else (after, before, art)


def build_kit(out: Path, *, sources, sets: dict[str, dict] | None = None,
              verdict_files: dict[str, Path] | None = None, manifest_dir: Path | None = None) -> dict:
    """The review kit in `out`: `img/`, `kit.json`, `index.html`. `sources(row)
    -> (left, right, art)` paths for one selected pair. Reads the CALIBRATION
    manifest and nothing from the held-out part."""
    cal = _kit_read(CALIBRATION_FILE, manifest_dir)["ids"]
    sets = sets if sets is not None else {SET_1104: sealed_1104(), SET_1106: sealed_1106()}
    picked = select(cal, sets, verdict_files or VERDICTS)
    entries = []
    for i, x in enumerate(picked, 1):
        kid = f"C{i:02d}"
        left, right, art = sources(x)
        win = write_pair_images(kid, Path(left), Path(right), Path(art), out / "img")
        entries.append({"kit": kid, **x, "window": win})
    blob = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    kit = {"built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "kit_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
           "seed": SEED, "n": len(entries),
           "per_class": {c: sum(e["class"] == c for e in entries) for c in CLASSES},
           "per_set": {n: sum(e["set"] == n for e in entries) for n in (SET_1104, SET_1106)},
           "pairs": entries}
    out.mkdir(parents=True, exist_ok=True)
    (out / "kit.json").write_text(json.dumps(kit, indent=1), encoding="utf-8")
    (out / "index.html").write_text(page_html(kit), encoding="utf-8")
    return kit


def do_kit(a) -> int:
    from tools.eye_pairs import pro_pooled_build as pb
    out = Path(a.out).resolve()
    src_1102 = Path(a.src_1102) if a.src_1102 else (pb.primary_checkout() / "digitizer" / "eye_pairs_out"
                                                    / "pro-lettering-1102")
    runs = Path(a.runs).resolve() if a.runs else out / "runs"
    trees = Path(a.trees).resolve() if a.trees else Path(os.environ.get("TEMP", ".")) / "embwt" / "trees"
    sets = {SET_1104: sealed_1104(), SET_1106: sealed_1106()}
    cal = _kit_read(CALIBRATION_FILE)["ids"]
    picked = select(cal, sets, VERDICTS)
    render_1106(picked, sets[SET_1106], runs, trees, python=a.python, use_slot=not a.no_slot)

    def sources(x):
        if x["set"] == SET_1104:
            return sources_1104(x["pair"], src_1102)
        return sources_1106(x["pair"], sets[SET_1106], runs, out / "work")

    kit = build_kit(out, sources=sources, sets=sets)
    print(json.dumps({"page": str(out / "index.html"), "n": kit["n"], "per_class": kit["per_class"],
                      "per_set": kit["per_set"]}, indent=1))
    return 0


# ------------------------------------------------------- the held-out packets ----
#
# Phase B's blind run. Every HELD-OUT pair, plus the identical controls of the
# two kits (PRE-REGISTRATION.md, "Controls"), drawn exactly as the calibration
# kit drew its pairs: the same sources (11-04: the surviving files Kent and the
# old judge saw; 11-06: re-drawn on the sitting's tree at the sitting's size,
# `stitchviz` at 14 px/mm, JPEG 92), the same one-canvas padding, the same
# `diff_window` and 3x crops. LEFT / RIGHT stay in each kit's own sealed frame
# (order A, "as Kent saw it"), which those kits' seeded shuffles randomised.
#
# The judge's folder holds `packets.json` (blind id + absolute picture paths,
# nothing else) and `img/H###_*`. Everything that unseals a pair (the blind id
# -> pool id, kind, which side is the base, the crop window, the designs, the
# drop reasons) lives in a SEPARATE sealed folder the judge is never shown.

HELDOUT_SEED = SEED
HELDOUT_NAME = "judge-heldout-1107"
SEALED_SUFFIX = "-sealed"
PACKET_KEYS = ("pair", "left", "right", "art", "left_x3", "right_x3")
PACKETS_FILE = "packets.json"
KEY_FILE = "key.json"


def heldout_ids(out: Path | None = None) -> list[str]:
    """The HELD-OUT pool ids: the one place a picture builder reads that file."""
    return list(json.loads(((out or OUT) / HELD_OUT_FILE).read_text(encoding="utf-8"))["ids"])


def control_ids(sealed_sets: dict[str, dict]) -> list[str]:
    """The identical-pair controls of the two kits, as `<set>:<pair>`, minus
    Amendment 1's exclusions (11-04: P002)."""
    out = []
    for name, sealed in sealed_sets.items():
        for pid, s in sorted(sealed.items()):
            if s.get("kind") == "identical" and not (name == SET_1104 and pid in EXCLUDED_1104):
                out.append(f"{name}:{pid}")
    return out


def blind_layout(held: list[str], controls: list[str], *, seed: int = HELDOUT_SEED) -> list[dict]:
    """Held-out pairs and controls in one seeded shuffle, numbered H001.. in
    turn. -> [{blind, pool_id, kind}] (kind = live / identical)."""
    rows = [(i, "live") for i in sorted(held)] + [(i, "identical") for i in sorted(controls)]
    assert len({r[0] for r in rows}) == len(rows), "a control is also a held-out pair"
    random.Random(seed).shuffle(rows)
    return [{"blind": f"H{n:03d}", "pool_id": pid, "kind": kind} for n, (pid, kind) in enumerate(rows, 1)]


def _base_side(s: dict) -> str:
    if s.get("kind") == "identical":
        return "both"
    return "L" if s["left_arm"] == "base" else "R"


def build_heldout(out: Path, sealed_dir: Path, *, layout: list[dict], sealed_sets: dict[str, dict],
                  sources) -> dict:
    """The blind packets in `out` (`packets.json`, `img/`) and the key in
    `sealed_dir` (`key.json`, `dropped.json`). `sources(row) -> (left, right,
    art)` for one layout row; a row whose sources or pictures fail is dropped
    with its reason in the sealed folder. -> {packets, dropped, key}."""
    out, sealed_dir = Path(out).resolve(), Path(sealed_dir).resolve()
    if out == sealed_dir or out in sealed_dir.parents or sealed_dir in out.parents:
        raise ValueError(f"the sealed folder {sealed_dir} must sit apart from the judge's folder {out}")
    img = out / "img"
    packets, key, dropped = [], {}, []
    for row in layout:
        hid = row["blind"]
        name, pair = row["pool_id"].split(":", 1)
        s = sealed_sets[name][pair]
        try:
            left, right, art = sources(row)
            win = write_pair_images(hid, Path(left), Path(right), Path(art), img)
        except Exception as e:  # noqa: BLE001 - a pair that cannot be drawn is dropped, with why
            dropped.append({"blind": hid, "pool_id": row["pool_id"], "kind": row["kind"],
                            "reason": f"{type(e).__name__}: {str(e)[-400:]}"})
            continue
        packets.append({"pair": hid, "left": str(img / f"{hid}_L.jpg"), "right": str(img / f"{hid}_R.jpg"),
                        "art": str(img / f"{hid}_art.png"), "left_x3": str(img / f"{hid}_Lx3.png"),
                        "right_x3": str(img / f"{hid}_Rx3.png")})
        key[hid] = {"pool_id": row["pool_id"], "kind": row["kind"], "base_side": _base_side(s), "window": win}
    assert all(tuple(p) == PACKET_KEYS for p in packets)
    out.mkdir(parents=True, exist_ok=True)
    sealed_dir.mkdir(parents=True, exist_ok=True)
    (out / PACKETS_FILE).write_text(json.dumps(packets, indent=1), encoding="utf-8")
    blob = json.dumps(key, sort_keys=True, separators=(",", ":"))
    (sealed_dir / KEY_FILE).write_text(json.dumps(
        {"built": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": HELDOUT_SEED,
         "frame": "order A: each kit's own sealed LEFT / RIGHT",
         "packets_sha256": hashlib.sha256((out / PACKETS_FILE).read_bytes()).hexdigest(),
         "key_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
         "n_live": sum(v["kind"] == "live" for v in key.values()),
         "n_identical": sum(v["kind"] == "identical" for v in key.values()),
         "pairs": key}, indent=1), encoding="utf-8")
    (sealed_dir / "dropped.json").write_text(json.dumps(dropped, indent=1), encoding="utf-8")
    return {"packets": packets, "dropped": dropped, "key": key}


def do_heldout_kit(a) -> int:
    from tools.eye_pairs import pro_pooled_build as pb
    base = pb.primary_checkout() / "digitizer" / "eye_pairs_out"
    out = Path(a.out).resolve() if a.out else base / HELDOUT_NAME
    sealed_dir = Path(a.sealed).resolve() if a.sealed else out.parent / (out.name + SEALED_SUFFIX)
    src_1102 = Path(a.src_1102) if a.src_1102 else base / "pro-lettering-1102"
    runs = Path(a.runs).resolve() if a.runs else sealed_dir / "runs"
    trees = Path(a.trees).resolve() if a.trees else Path(os.environ.get("TEMP", ".")) / "embwt" / "trees"
    st = vj.load_sitting()
    sets = {SET_1104: st["sealed"], SET_1106: vj.pro100_sealed()}
    layout = blind_layout(heldout_ids(), control_ids(sets))
    for row in layout:
        name, pair = row["pool_id"].split(":", 1)
        if row["kind"] == "live":
            assert sets[name][pair]["kind"] == "live", row["pool_id"]
    keys = [k for r in layout if r["pool_id"].startswith(SET_1106 + ":")
            for k in designs_1106(sets[SET_1106][r["pool_id"].split(":", 1)[1]])]
    reuse = [Path(d).resolve() for d in (a.reuse_runs or [])]
    for k in dict.fromkeys(keys):
        dst = pb.design_dir(runs, k[0], k[1], k[2])
        for r in reuse:
            src = pb.design_dir(r, k[0], k[1], k[2])
            if not (dst / "design.json").exists() and (src / "design.json").exists():
                import shutil
                shutil.copytree(src, dst, dirs_exist_ok=True)
    failed = draw_designs(keys, runs, trees, python=a.python, use_slot=not a.no_slot,
                          holder="judge_calibration heldout-kit (one design at a time)", tolerate=True)

    def sources(row):
        name, pair = row["pool_id"].split(":", 1)
        if name == SET_1104:
            paths = sources_1104(pair, src_1102)
            for p in paths:
                if not p.exists():
                    raise FileNotFoundError(f"the surviving 11-04 picture {p.name} is missing")
            return paths
        bad = [failed[k] for k in designs_1106(sets[SET_1106][pair]) if k in failed]
        if bad:
            raise RuntimeError("design render failed: " + bad[0])
        return sources_1106(pair, sets[SET_1106], runs, sealed_dir / "work")

    res = build_heldout(out, sealed_dir, layout=layout, sealed_sets=sets, sources=sources)
    print(json.dumps({"packets": str(out / PACKETS_FILE), "key": str(sealed_dir / KEY_FILE),
                      "n": len(res["packets"]), "dropped": res["dropped"]}, indent=1))
    return 0


# ------------------------------------------------------- phase B: the score ----
#
# After the one blind run, the sealed key is copied next to the verdicts
# (`heldout-key.json`) so the score can be re-run from the repo alone. The
# verdicts are in the packets' frame, which is each kit's own order-A frame
# (`key.json` "frame"), so `base_side` maps L / R to before / after and
# `vlm_judge.to_label` on the kit's sealed row must agree; `score` checks both.

#: Amendment 1's freeze. A verdict row carrying any other value is not scored.
RUBRIC_SHA256 = "16836a48790c2738ab581dda75de9e4eac83ee4e8eb30ea8cdb875ec1b81b243"
HELDOUT_VERDICTS_FILE = "heldout-verdicts.jsonl"
HELDOUT_KEY_COPY = "heldout-key.json"
HELDOUT_ANALYSIS_FILE = "heldout-analysis.json"


def blind_label(choice: str, base_side: str) -> str:
    """L / R / tie in the packet frame -> before / tie / after."""
    if choice == "tie":
        return "tie"
    if choice not in ("L", "R") or base_side not in ("L", "R"):
        raise ValueError(f"cannot map {choice!r} with base on {base_side!r}")
    return "before" if choice == base_side else "after"


def score(verdict_rows: list[dict], key: dict, *, held: list[str], pool_rows: list[dict],
          sealed_sets: dict[str, dict], old_verdicts: dict[str, Path] | None = None) -> dict:
    """The pre-registered primary and secondaries on HELD-OUT. `verdict_rows`
    are the blind run's rows (order A; the last row per pair wins), `key` the
    sealed key's `pairs`, `held` the held-out pool ids, `pool_rows` the pool
    (Kent's original labels and designs), `sealed_sets` each kit's sealed rows
    (for the `to_label` cross-check and the baseline)."""
    by_pool = {r["id"]: r for r in pool_rows}
    last: dict[str, dict] = {}
    for r in verdict_rows:
        if r.get("order", "A") == "A":
            last[r["pair"]] = r
    rows, ids, detail, unscored, ctrl = [], [], [], [], []
    for hid in sorted(key):
        k = key[hid]
        v = last.get(hid)
        if v is None:
            unscored.append({"blind": hid, "why": "no verdict"})
            continue
        if v.get("rubric_sha256") != RUBRIC_SHA256:
            unscored.append({"blind": hid, "why": "rubric_sha256 differs"})
            continue
        if k["kind"] == "identical":
            ctrl.append({"blind": hid, "pool_id": k["pool_id"], "choice": v["choice"]})
            continue
        name, pair = k["pool_id"].split(":", 1)
        label = blind_label(v["choice"], k["base_side"])
        assert vj.to_label(v["choice"], sealed_sets[name][pair]) == label, (hid, k["pool_id"])
        p = by_pool[k["pool_id"]]
        rows.append((p["kent"], label, p["design"]))
        ids.append(k["pool_id"])
        detail.append({"blind": hid, "pool_id": k["pool_id"], "set": name, "design": p["design"],
                       "kent": p["kent"], "judge": label, "choice": v["choice"],
                       "confidence": v.get("confidence"), "reason": v.get("reason")})
    assert sorted(ids) == sorted(held), "the scored pairs are not the held-out list"
    res = {"rubric_sha256": RUBRIC_SHA256, "n_verdicts": len(last), "unscored": unscored,
           "primary": primary(rows)}
    res["by_set"] = {s: primary([r for r, d in zip(rows, detail) if d["set"] == s])
                     for s in (SET_1104, SET_1106)}
    res["judge_tie_on_kent_side"] = sum(1 for k, j, _ in rows if k != "tie" and j == "tie")
    res["judge_side_on_kent_tie"] = sum(1 for k, j, _ in rows if k == "tie" and j != "tie")
    res["opposite_sides"] = sum(1 for k, j, _ in rows if "tie" not in (k, j) and k != j)
    live_choices = [d["choice"] for d in detail]
    confs = [d["confidence"] for d in detail if isinstance(d["confidence"], int)]
    res["controls"] = {"identical": len(ctrl), "identical_called_tie": sum(c["choice"] == "tie" for c in ctrl),
                       "rows": ctrl, "left_picks": live_choices.count("L"),
                       "right_picks": live_choices.count("R"), "ties_live": live_choices.count("tie"),
                       "mean_confidence": round(sum(confs) / len(confs), 2) if confs else None}
    # The baseline: the old judges' committed verdicts on the same pairs, same function.
    old = old_verdicts if old_verdicts is not None else VERDICTS
    base_rows, base_by_set = [], {}
    for pid in sorted(held):
        name, pair = pid.split(":", 1)
        r = _verdict_rows(old[name], {pair}).get(pair)
        if r is None or r.get("choice") is None:
            continue
        lab = vj.to_label(r["choice_frame_a"], sealed_sets[name][pair])
        row = (by_pool[pid]["kent"], lab, by_pool[pid]["design"])
        base_rows.append(row)
        base_by_set.setdefault(name, []).append(row)
    res["baseline_old_judges_same_pairs"] = primary(base_rows)
    res["baseline_by_set"] = {s: primary(r) for s, r in sorted(base_by_set.items())}
    res["pairs"] = detail
    return res


def do_score(a) -> int:
    out = Path(a.out)
    key = json.loads((out / HELDOUT_KEY_COPY).read_text(encoding="utf-8"))["pairs"]
    verdicts = [json.loads(x) for x in (out / HELDOUT_VERDICTS_FILE).read_text(encoding="utf-8").splitlines()
                if x.strip()]
    sets = {SET_1104: vj.load_sitting()["sealed"], SET_1106: vj.pro100_sealed()}
    res = score(verdicts, key, held=heldout_ids(out), pool_rows=pool(), sealed_sets=sets)
    (out / HELDOUT_ANALYSIS_FILE).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n",
                                             encoding="utf-8")
    p = res["primary"]
    print(json.dumps({"kappa_3way": p["kappa_3way"], "ci3_pairs": p["ci3_pairs"],
                      "ci3_designs": p["ci3_designs"], "passes": p["passes"],
                      "table_kent_rows_judge_cols": p["table_kent_rows_judge_cols"],
                      "baseline": res["baseline_old_judges_same_pairs"]["kappa_3way"]}, indent=1))
    return 0


# ---------------------------------------------------------- the kit: the page ----

PAGE = """<!doctype html>
<meta charset="utf-8"><title>Judge calibration</title>
<style>
body{margin:0;background:#2b2b2b;color:#ddd;font:14px system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:#222;padding:8px 12px;display:flex;gap:14px;align-items:center;border-bottom:1px solid #444}
#msg{color:#ffb454}
main{padding:8px 12px 80px}
.pair{border:1px solid #444;border-radius:6px;margin:14px 0;padding:10px;background:#333}
.pair h2{font-size:15px;margin:0 0 6px;font-weight:600}
.cls{color:#9ad;font-weight:400}
.row{display:flex;gap:8px;align-items:flex-start}
.view{flex:1 1 0;position:relative;background:#fff;overflow:hidden;cursor:zoom-in}
.view img{width:100%;display:block;transform-origin:50% 50%}
.art{flex:0 0 12%;background:#fff}.art img{width:100%;display:block}
.box{position:absolute;border:2px solid #e33;pointer-events:none}
.crops{display:flex;gap:8px;margin-top:8px;justify-content:center}
.crops figure{margin:0;flex:0 1 46%;background:#fff}.crops img{width:100%;display:block;image-rendering:pixelated}
figcaption,.cap{color:#999;font-size:12px;padding:2px 4px;background:#2b2b2b}
.picks{margin:8px 0;line-height:1.5}
.picks b{color:#fff}
input.reason{width:100%;box-sizing:border-box;font:inherit;padding:6px;background:#1e1e1e;color:#eee;border:1px solid #555}
.saved{color:#7c7;font-size:12px;min-height:1.2em}
button{font:inherit;padding:5px 12px}
</style>
<header><b>Judge calibration</b><span id="count"></span>
<button id="dl">Download reasons.json</button><span id="msg"></span></header>
<main>
<p>Each pair is one where the old vision judge and your original pick disagreed. LEFT and RIGHT are the
pictures the judge saw, on one canvas at one scale; the red box marks the window where they differ most,
shown 3x underneath. Click a picture to zoom 3x at the pointer. In one line: <b>what made you pick what you
picked?</b> What should the judge have looked at?</p>
<div id="pairs"></div>
</main>
<script id="kit" type="application/json">__KIT__</script>
<script>
const KIT=JSON.parse(document.getElementById('kit').textContent);
const SERVED=location.protocol.startsWith('http');
const KEY='judge-calibration:'+KIT.kit_sha256;
const NAMES={L:'LEFT',R:'RIGHT',tie:'tie (can\\'t tell)'};
const CLASS={judge_tie_kent_side:'the judge called a tie, you picked a side',
  judge_side_kent_tie:'the judge picked a side, you called a tie',
  opposite_sides:'you and the judge picked opposite sides'};
let reasons={};
const $=id=>document.getElementById(id);
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function payload(){
  return {kit_sha256:KIT.kit_sha256,updated:new Date().toISOString(),
    reasons:Object.fromEntries(Object.entries(reasons).filter(([k,v])=>v.reason).map(([k,v])=>[k,{pool_id:v.pool_id,reason:v.reason,ts:v.ts}]))};
}
function count(){
  const n=Object.values(reasons).filter(v=>v.reason&&v.reason.trim()).length;
  $('count').textContent=n+' / '+KIT.pairs.length+' reasons';
}
function card(p){
  const w=p.window, pct=v=>(100*v)+'%';
  const box=xy=>'<div class="box" style="left:'+pct(xy[0]/w.w)+';top:'+pct(xy[1]/w.h)+';width:'+pct(w.s/w.w)+';height:'+pct(w.s/w.h)+'"></div>';
  const conf=p.confidence==null?'':' (confidence '+esc(p.confidence)+' of 5)';
  return '<section class="pair" id="'+p.kit+'"><h2>'+p.kit+' <span class="cls">&middot; '+CLASS[p['class']]+'</span></h2>'+
   '<div class="row"><div class="view"><img src="img/'+p.kit+'_L.jpg" alt="LEFT">'+box(w.L)+'<div class="cap">LEFT</div></div>'+
   '<div class="art"><img src="img/'+p.kit+'_art.png" alt="artwork"><div class="cap">artwork</div></div>'+
   '<div class="view"><img src="img/'+p.kit+'_R.jpg" alt="RIGHT">'+box(w.R)+'<div class="cap">RIGHT</div></div></div>'+
   '<div class="crops"><figure><img src="img/'+p.kit+'_Lx3.png" alt=""><figcaption>LEFT, 3x</figcaption></figure>'+
   '<figure><img src="img/'+p.kit+'_Rx3.png" alt=""><figcaption>RIGHT, 3x</figcaption></figure></div>'+
   (w.differs?'':'<p class="cap">The two pictures are pixel-identical.</p>')+
   '<div class="picks">Your original pick: <b>'+NAMES[p.kent]+'</b><br>The judge: <b>'+NAMES[p.judge]+'</b>'+conf+
   ' &mdash; &ldquo;'+esc(p.reason)+'&rdquo;</div>'+
   '<input class="reason" data-kit="'+p.kit+'" maxlength="400" placeholder="Your one-line reason">'+
   '<div class="saved" id="s_'+p.kit+'"></div></section>';
}
async function save(kit){
  const v=reasons[kit];
  try{localStorage.setItem(KEY,JSON.stringify(reasons));}catch(e){}
  if(!SERVED){$('s_'+kit).textContent='kept in this browser; use Download to hand it over';return;}
  try{
    const r=await fetch('/reason',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({kit:kit,reason:v.reason})});
    if(!r.ok)throw new Error('HTTP '+r.status);
    $('s_'+kit).textContent='saved';$('msg').textContent='';
  }catch(err){$('s_'+kit).textContent='';$('msg').textContent='Not saved ('+err.message+'); it is kept in this browser.';}
}
async function load(){
  try{reasons=JSON.parse(localStorage.getItem(KEY)||'{}');}catch(e){reasons={};}
  if(SERVED){
    try{const r=await (await fetch('/reasons')).json();
      for(const [k,v] of Object.entries(r.reasons||{}))reasons[k]={pool_id:v.pool_id,reason:v.reason,ts:v.ts};}catch(e){}
  }
  $('pairs').innerHTML=KIT.pairs.map(card).join('');
  const timers={};
  for(const el of document.querySelectorAll('input.reason')){
    const kit=el.dataset.kit, p=KIT.pairs.find(q=>q.kit===kit);
    if(reasons[kit])el.value=reasons[kit].reason||'';
    el.addEventListener('input',()=>{
      reasons[kit]={pool_id:p.id,reason:el.value,ts:new Date().toISOString()};count();
      clearTimeout(timers[kit]);timers[kit]=setTimeout(()=>save(kit),600);
    });
  }
  for(const v of document.querySelectorAll('.view')){
    const im=v.querySelector('img');
    v.addEventListener('click',e=>{
      const b=v.getBoundingClientRect();
      const on=im.style.transform!=='scale(3)';
      im.style.transformOrigin=(100*(e.clientX-b.left)/b.width)+'% '+(100*(e.clientY-b.top)/b.height)+'%';
      im.style.transform=on?'scale(3)':'scale(1)';v.style.cursor=on?'zoom-out':'zoom-in';
    });
  }
  count();
  window.PAGE_READY=true;
}
$('dl').onclick=()=>{
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([JSON.stringify(payload(),null,1)],{type:'application/json'}));
  a.download='reasons.json';a.click();
};
load();
</script>
"""


def page_html(kit: dict) -> str:
    data = json.dumps(kit).replace("</", "<\\/")
    return PAGE.replace("__KIT__", data)


def read_reasons(kit_dir: Path) -> dict:
    """`<kit>/reasons.json` -> {kit_sha256, updated, reasons: {C01: {pool_id, reason, ts}}}.
    What phase B reads; an absent file is an empty one."""
    p = Path(kit_dir) / "reasons.json"
    if not p.exists():
        kit = json.loads((Path(kit_dir) / "kit.json").read_text(encoding="utf-8"))
        return {"kit_sha256": kit["kit_sha256"], "updated": None, "reasons": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def make_server(kit_dir, port: int = 8733, host: str = "127.0.0.1"):
    """localhost only. GET / (the page), /img/<name> for the names kit.json
    lists and nothing else, /reasons; POST /reason {kit, reason} writes
    `reasons.json` (temp file, fsync, replace) before it answers."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import unquote, urlparse
    kd = Path(kit_dir)
    kit = json.loads((kd / "kit.json").read_text(encoding="utf-8"))
    page = (kd / "index.html").read_bytes()
    by_kit = {p["kit"]: p for p in kit["pairs"]}
    allowed = {f"{k}_{s}" for k in by_kit for s in ("L.jpg", "R.jpg", "Lx3.png", "Rx3.png", "art.png")}
    lock = threading.Lock()

    def write(data: dict) -> None:
        tmp = kd / "reasons.json.tmp"
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=1, ensure_ascii=False))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, kd / "reasons.json")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            path = unquote(urlparse(self.path).path)
            if path in ("/", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            elif path == "/reasons":
                with lock:
                    body = json.dumps(read_reasons(kd)).encode("utf-8")
                self._send(200, body, "application/json")
            elif path.startswith("/img/") and path[5:] in allowed:
                name = path[5:]
                self._send(200, (kd / "img" / name).read_bytes(),
                           "image/png" if name.endswith(".png") else "image/jpeg")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):  # noqa: N802
            if urlparse(self.path).path != "/reason":
                self._send(404, b"not found", "text/plain")
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if not 0 <= n <= 4096:
                    raise ValueError
                body = json.loads(self.rfile.read(n) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._send(400, b"bad json", "text/plain")
                return
            if (not isinstance(body, dict) or body.get("kit") not in by_kit
                    or not isinstance(body.get("reason"), str) or len(body["reason"]) > 400):
                self._send(400, b"bad reason", "text/plain")
                return
            with lock:
                data = read_reasons(kd)
                k = body["kit"]
                data["reasons"][k] = {"pool_id": by_kit[k]["id"], "reason": body["reason"].strip(),
                                      "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                if not data["reasons"][k]["reason"]:
                    del data["reasons"][k]
                data["kit_sha256"] = kit["kit_sha256"]
                data["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                write(data)
            self._send(200, b'{"ok": true}', "application/json")

    return ThreadingHTTPServer((host, port), Handler)


def do_serve(a) -> int:
    srv = make_server(a.kit, port=a.port)
    print(f"http://127.0.0.1:{srv.server_address[1]}/  (reasons -> {Path(a.kit) / 'reasons.json'}; Ctrl+C stops)",
          flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


# ------------------------------------------------------------------- main ----

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("split", help="write (or --check) the calibration / held-out manifest")
    sp.add_argument("--out", default=str(OUT))
    sp.add_argument("--check", action="store_true")
    sp.set_defaults(fn=do_split)
    kt = sub.add_parser("kit", help="build the calibration review page (CALIBRATION pairs only)")
    kt.add_argument("--out", required=True, help="a gitignored folder, e.g. eye_pairs_out/judge-calibration-1107")
    kt.add_argument("--src-1102", default=None, help="the surviving pro-lettering-1102 kit (default: primary checkout's)")
    kt.add_argument("--runs", default=None, help="where 11-06 designs are drawn (default <out>/runs)")
    kt.add_argument("--trees", default=None, help="detached worktrees, outside the repo (default %%TEMP%%/embwt/trees)")
    kt.add_argument("--python", default=sys.executable)
    kt.add_argument("--no-slot", action="store_true", help="do not take the laptop's CPU slot")
    kt.set_defaults(fn=do_kit)
    ho = sub.add_parser("heldout-kit", help="draw the blind HELD-OUT packets (key kept in a sealed folder)")
    ho.add_argument("--out", default=None,
                    help=f"the judge's folder (default: primary checkout's eye_pairs_out/{HELDOUT_NAME})")
    ho.add_argument("--sealed", default=None, help=f"the key's folder (default: <out>{SEALED_SUFFIX}, a sibling)")
    ho.add_argument("--src-1102", default=None, help="the surviving pro-lettering-1102 kit (default: primary checkout's)")
    ho.add_argument("--runs", default=None, help="where 11-06 designs are drawn (default <sealed>/runs)")
    ho.add_argument("--reuse-runs", action="append", default=None,
                    help="a runs folder whose designs (same tree, fixture, side) are copied instead of re-drawn")
    ho.add_argument("--trees", default=None, help="detached worktrees, outside the repo (default %%TEMP%%/embwt/trees)")
    ho.add_argument("--python", default=sys.executable)
    ho.add_argument("--no-slot", action="store_true", help="do not take the laptop's CPU slot")
    ho.set_defaults(fn=do_heldout_kit)
    sc = sub.add_parser("score", help="score the blind HELD-OUT verdicts against Kent's original picks")
    sc.add_argument("--out", default=str(OUT))
    sc.set_defaults(fn=do_score)
    sv = sub.add_parser("serve", help="serve the page; reasons save to <kit>/reasons.json")
    sv.add_argument("--kit", required=True)
    sv.add_argument("--port", type=int, default=8733)
    sv.set_defaults(fn=do_serve)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
