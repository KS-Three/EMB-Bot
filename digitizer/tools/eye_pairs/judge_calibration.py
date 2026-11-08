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

The held-out list is read by `split --check`, by tests, and by phase B's
scoring, never by anything that builds or shows a picture.
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


def render_1106(picked: list[dict], sealed: dict, runs: Path, trees: Path, *,
                python: str, use_slot: bool = True) -> None:
    """Re-draw the designs of the 11-06 pairs in the kit, and no others, under
    the 11-06 rule (`pro_pooled_build.render_one`, the sitting's tree and
    size, the laptop's CPU slot; a design already on disk is kept)."""
    from tools.eye_pairs import pro_pooled_build as pb
    keys: dict[tuple, None] = {}
    for x in picked:
        if x["set"] != SET_1106:
            continue
        s = sealed[x["pair"]]
        for tree, side, kw in (s["before_design"], s["after_design"]):
            keys[(tree, s["fixture"], side, json.dumps(kw, sort_keys=True))] = None
    todo = [k for k in keys if not (pb.design_dir(runs, k[0], k[1], k[2]) / "design.json").exists()]
    print(f"{len(keys)} designs for the 11-06 pairs in the kit; {len(todo)} to draw", flush=True)
    if not todo:
        return
    slot = pb.Slot(pb.default_slot() if use_slot else None, "judge_calibration kit (calibration pairs only)")
    slot.acquire()
    try:
        for sha in dict.fromkeys(k[0] for k in todo):
            tree = pb.ensure_tree(trees, sha)
            for _t, fixture, side, kw in (k for k in todo if k[0] == sha):
                slot.rotate_if_due(pb.TAKE_MIN)
                meta = pb.render_one(tree, fixture, pb.design_dir(runs, sha, fixture, side), json.loads(kw),
                                     python, size=pb.sitting_size(fixture))
                print(f"  {sha}/{fixture}/{side}: {meta['stitches']} stitches, {meta['wall_s']} s", flush=True)
            pb.discard_worktree(pb.REPO, trees / sha)
    finally:
        slot.release()


def sources_1106(pair: str, sealed: dict, runs: Path, work: Path) -> tuple[Path, Path, Path]:
    """One 11-06 pair's pictures, as `vlm_judge.kit_pro100` made them: each
    design through `_design_jpg`, the base on the side the sealed key says."""
    from tools.artfid_eye_rank import _normalise_art
    from tools.eye_pairs import pro_pooled_build as pb
    s = sealed[pair]
    before = vj._design_jpg(pb.design_dir(runs, s["before_design"][0], s["fixture"], s["before_design"][1]))
    after = vj._design_jpg(pb.design_dir(runs, s["after_design"][0], s["fixture"], s["after_design"][1]))
    art = work / f"{SET_1106}_{pair}_art.png"
    work.mkdir(parents=True, exist_ok=True)
    _normalise_art(DIGITIZER / "testdata" / pb.FIXTURE_ART[s["fixture"]], art)
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
    sv = sub.add_parser("serve", help="serve the page; reasons save to <kit>/reasons.json")
    sv.add_argument("--kit", required=True)
    sv.add_argument("--port", type=int, default=8733)
    sv.set_defaults(fn=do_serve)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
