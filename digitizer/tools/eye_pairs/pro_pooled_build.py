"""Build docs/eye-pairs-2026-11-01/pro-pair-inputs.json: Kent's labelled pairs
with a pro file, both arms re-digitized on the sitting's own tree, read beside
the pro's DST.

    python -m tools.eye_pairs.pro_pooled_build plan    [--decided-only]
    python -m tools.eye_pairs.pro_pooled_build render  --runs DIR [--decided-only] [--trees DIR]
                                                       [--take-min 20] [--no-slot] [--only SITTING ...]
    python -m tools.eye_pairs.pro_pooled_build measure --runs DIR [--no-words]
    python -m tools.eye_pairs.pro_pooled_build build   --runs DIR --out PATH

A ONE-OFF like `pooled_build.py`, kept so the committed inputs can be audited
and rebuilt. No labelled sitting's render directory survives on Kent's laptop
(searched 2026-11-01: the 09-18 `eye_pairs_out`, the `columns-sitting` and
`letterform-priors` lanes are all gone), so every pair's two designs are
drawn again:

* on the SITTING'S TREE (`SITTINGS[...]["tree"]`, the commit its README or
  kent-notes names), in a detached worktree outside the repository, with the
  primary checkout's venv and its rembg venv linked in, so the engine is the
  one Kent's pictures came from -- not today's;
* at the PRO'S width and garment (`FIXTURE_JOB`: the `pro_baseline.JOBS` row
  the fixture is paired with), not the sitting's 80 mm left-chest render, so
  ours and the pro's file are the same job;
* with the same `base_cfg` the sitting used (`PipelineConfig` at the Studio's
  six colours plus the arm's one change). A ref arm (`ref_0827`,
  `ref_0930am`) is the OLD engine's base: `before` is that tree, `after` is
  the sitting's.

Then every design is read beside the pro's DST through TODAY'S readers, the
same code on both files: `pro_pair.pro_counts` (cuts), `pro_baseline.needle_up`
(hops, needle-up mm), `pro_baseline.kappas` (stitch-type kappa over the shared
solid area), and `lettering_board.read_pair` (columns per pinned line and the
word-legibility cc, where the job has lines / words pinned). The pro's own
figures ride on every pair so `pro_pooled.py` can read each instrument as a
DISTANCE to the pro.

What this does NOT reproduce: the 77-pair flags sitting was judged on a
cloud render Kent's laptop never held; the Column lane at 2a87ba89 broke
ties from OS entropy (fixed one commit later), so its `density-1007` arm is a
sample of that engine, not the picture he saw. Both are stated in the doc.

A digitize is a heavy run on Kent's laptop: `render` takes the shared CPU
slot (`%TEMP%\\embwt\\cpu.lock`, `docs/superpowers/plans/2026-10-27-director-handoff.md`
section 5) for at most `--take-min` minutes at a time, releases it, waits 90 s
and takes it again; one design at a time, never two.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parents[2]
REPO = DIGITIZER.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools.eye_pairs import pooled                      # noqa: E402
from tools.eye_pairs.refarm import (CAPTURED, add_worktree, discard_worktree,  # noqa: E402
                                    guard_scratch, link_photo_prep)

OUT = REPO / "docs" / "eye-pairs-2026-11-01" / "pro-pair-inputs.json"
STUDIO_MAX_COLORS = 6
TAKE_MIN = 20.0
RELEASE_S = 90.0
POLL_S = 30.0
DESIGN_TIMEOUT_S = 1800.0

#: sitting id (as `pooled-inputs.json` names it) -> the tree its pairs were drawn on,
#: the base's kwargs over the Studio defaults, and each arm's one change. A `__ref__`
#: arm is an older engine: that commit's base is the pair's `before`.
SITTINGS: dict[str, dict] = {
    "flags-0918-0928": {
        "tree": "a5d78449",                      # the 09-18 render (Kent judged the 09-20 cloud twin)
        "base": {},
        "arms": {"per_stroke": {"satin_per_stroke": True},
                 "patch_junctions": {"satin_patch_junctions": "satin"},
                 "polygon_axis": {"satin_polygon_axis": "artwork"},
                 "area_weighted": {"classify_area_weighted": True},
                 "design_angle": {"design_angle": True},
                 "rails_follow_edge": {"satin_rails_follow_edge": True},
                 "rail_comp": {"satin_rail_comp": True},
                 "wide_columns": {"wide_columns": True},
                 "lettering_column": {"lettering_min_column_mm": 1.0},
                 "phantom_dissolve": {"dissolve_phantom_blends": True},
                 "directional_comp": {"directional_comp": True},
                 "ref_0827": {"__ref__": "25da2fe"}}},
    "envelope-0930": {"tree": "e54b5963", "base": {},
                      "arms": {"rail_envelope": {"satin_rails_follow_edge": "envelope"}}},
    "evening-0930": {"tree": "0803a7b2", "base": {},
                     "arms": {"ref_0930am": {"__ref__": "1e5f8fe2"},
                              "phantom_dissolve": {"dissolve_phantom_blends": True}}},
    "texture-0930": {"tree": "7cc76370", "base": {},
                     "arms": {"split_7mm": {"split_satin_above_mm": 7.0},
                              "rails_symmetric": {"satin_rails_follow_edge": False}}},
    # README: main 28c893e3 plus `satin_crown_cover` ON (63c56ffa, then local to its lane)
    "off-flags-1003": {"tree": "82c9838d", "base": {"satin_crown_cover": True},
                       "arms": {"cap_recentre": {"satin_cap_recentre": True},
                                "bean_letters": {"bean_letter_max_stroke_mm": 1.0},
                                "split_off": {"split_satin": False}}},
    # kent-notes: "rendered on origin/main + PR #660's 1cbef252 cherry-picked (2a87ba89)"
    "density-1007": {"tree": "2a87ba89", "base": {},
                     "arms": {"lettering_columns": {"lettering_columns": True}}},
    "letterform-1007": {"tree": "95c7eb07", "base": {},
                        "arms": {"letterform_priors": {"letterform_priors_k": 0.75}}},
    # README: main d17c5f7e plus PR #814 (f08f49e4)
    "columns-flip-1008": {"tree": "f08f49e4", "base": {},
                          "arms": {"columns_words": {"lettering_columns": True, "lettering_words": True}}},
    # scope-history 2026-10-08: "main + #667" (the merge of #667)
    "full-density-1008": {"tree": "62676060", "base": {},
                          "arms": {"lettering_columns": {"lettering_columns": True}}},
}

#: fixture -> the `pro_baseline.JOBS` row it is read against. Where the artwork has
#: several pro jobs the one nearest the sitting's render is taken, except becker:
#: the hat is the job `word_legibility` pins words on, and the pro's file for it is
#: the one `testdata/reference` carries.
FIXTURE_JOB = {"becker": "becker_hat_large", "bridge": "bridge_lc", "drone": "precision_drone",
               "fremont": "hotel_fremont_patch", "golden_tee": "goldentee_hat", "tires": "tires_hat_3d"}

#: fixture -> art under the TREE's testdata (the sitting's own file; `thin_strokes.REAL_ART`)
FIXTURE_ART = {"becker": "becker_marine_logo.png", "tires": "logo_script_tires.png",
               "fremont": "photo/logo_hotel_fremont.webp", "bridge": "photo/logo_bridge_bar.jpg",
               "golden_tee": "photo/logo_golden_tee.jpg", "drone": "photo/drone_render.png"}

#: the job's `lettering_board` lines, when it has any (columns, word cc)
BOARD_SLUGS = {"becker_hat_large", "hotel_fremont_patch", "precision_drone", "tires_hat_3d"}

DRIVER = r"""
import json, os, sys, time
root = os.path.normcase(os.path.realpath(os.getcwd()))
sys.path.insert(0, root)
import digitizer_core
found = os.path.normcase(os.path.realpath(digitizer_core.__file__))
if not found.startswith(root + os.sep):
    sys.exit("REFUSED: digitizer_core resolved to %s, not the engine under %s" % (found, root))
from digitizer_core.config import PipelineConfig
from digitizer_core.adapter import plan_to_design
from digitizer_core.export import write_dst
import digitizer_core.pipeline as pl
image, out, width, garment, colors, kw = sys.argv[1:7]
cfg = PipelineConfig(target_width_mm=float(width), garment_id=garment, max_colors=int(colors),
                     **json.loads(kw))
t = time.time()
gen = pl.build_generation(image, cfg)
result = pl.finish_generation(gen.fork(), cfg)
plan = pl.plan_stitches(result, cfg)
secs = time.time() - t
os.makedirs(out, exist_ok=True)
write_dst(plan, os.path.join(out, "ours.dst"))
design = plan_to_design(plan)
with open(os.path.join(out, "design.json"), "w", encoding="utf-8") as fh:
    json.dump(design, fh)
warn = []
for w in (getattr(result, "warnings", None) or []):
    warn.append(w.get("code") if isinstance(w, dict) else str(w))
with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as fh:
    json.dump({"secs": round(secs, 1), "stitches": design.get("stitchCount"),
               "trims": sum(1 for s in design.get("stitches", []) if s.get("type") == "trim"),
               "warnings": warn, "width_mm": float(width), "garment": garment,
               "kwargs": json.loads(kw)}, fh)
"""


def _say(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


# ------------------------------------------------------------------ the plan

def job_of(fixture: str) -> tuple[str, str, float]:
    """-> (slug, garment, pro width mm) from `pro_baseline.JOBS`."""
    from tools.pro_baseline import JOBS
    slug = FIXTURE_JOB[fixture]
    garment, width = JOBS[slug][0], JOBS[slug][1]
    return slug, garment, float(width)


def labelled_pairs(inputs: dict | None = None) -> list[dict]:
    """Every judged pair of a fixture that has a pro file, with the two designs
    it needs: `before` / `after` = (tree, side name, kwargs)."""
    inputs = inputs or json.loads(pooled.INPUTS.read_text(encoding="utf-8"))
    out = []
    for p in pooled.pooled_pairs(inputs):
        if p["fixture"] not in FIXTURE_JOB:
            continue
        s = SITTINGS.get(p["sitting"])
        if s is None or p["arm"] not in s["arms"]:
            out.append({**p, "unscored_why": f"arm {p['arm']!r} is not in SITTINGS[{p['sitting']!r}]"})
            continue
        arm_kw = s["arms"][p["arm"]]
        base = (s["tree"], "base", dict(s["base"]))
        if "__ref__" in arm_kw:
            before, after = (arm_kw["__ref__"], "base", {}), base
        else:
            before, after = base, (s["tree"], p["arm"], {**s["base"], **arm_kw})
        out.append({**p, "before_design": before, "after_design": after})
    return out


def designs_needed(pairs: list[dict], *, decided_only: bool = False) -> list[tuple]:
    """Distinct (tree, fixture, side, kwargs) in render order: the designs of the
    pairs Kent chose a side on first, then the ties; within each, by tree so a
    worktree is made once and dropped."""
    order: dict[tuple, int] = {}
    for rank, decided in ((0, True), (1, False)):
        for p in pairs:
            if "before_design" not in p or (p["kent"] != "tie") != decided:
                continue
            for tree, side, kw in (p["before_design"], p["after_design"]):
                key = (tree, p["fixture"], side, json.dumps(kw, sort_keys=True))
                order.setdefault(key, rank)
    keys = [k for k, r in order.items() if r == 0 or not decided_only]
    return sorted(keys, key=lambda k: (order[k], k[0], k[1], k[2]))


def design_dir(runs: Path, tree: str, fixture: str, side: str) -> Path:
    return runs / tree / fixture / side


# ------------------------------------------------------------------ the slot

class Slot:
    """The laptop's shared CPU slot: a directory that exists while a heavy run
    holds it (handoff section 5). `acquire` waits, polling every POLL_S."""

    def __init__(self, path: Path | None, holder: str):
        self.path, self.holder, self.taken_at = path, holder, None

    def acquire(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.path.mkdir()
            except FileExistsError:
                who = ""
                try:
                    who = (self.path / "holder.txt").read_text(encoding="utf-8", errors="replace").strip()[:120]
                except OSError:
                    pass
                _say(f"slot {self.path} held ({who or 'no holder.txt'}); waiting {POLL_S:.0f} s")
                time.sleep(POLL_S)
                continue
            (self.path / "holder.txt").write_text(
                f"{self.holder}\ntaken {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")
            self.taken_at = time.time()
            _say(f"slot taken: {self.path}")
            return

    def release(self) -> None:
        if self.path is None or self.taken_at is None:
            return
        shutil.rmtree(self.path, ignore_errors=True)
        self.taken_at = None
        _say(f"slot released: {self.path}")

    def rotate_if_due(self, take_min: float) -> None:
        if self.path is None or self.taken_at is None or time.time() - self.taken_at < take_min * 60:
            return
        self.release()
        _say(f"waiting {RELEASE_S:.0f} s before taking the slot again")
        time.sleep(RELEASE_S)
        self.acquire()


def default_slot() -> Path | None:
    tmp = os.environ.get("TEMP") or os.environ.get("TMP")
    return Path(tmp) / "embwt" / "cpu.lock" if tmp else None


# ------------------------------------------------------------------ worktrees

def primary_checkout() -> Path:
    """The main worktree of this repository: a lane under `.claude/worktrees/`
    has no rembg venv of its own (handoff section 5), the primary does."""
    proc = subprocess.run(["git", "-C", str(REPO), "worktree", "list", "--porcelain"], **CAPTURED)
    for line in (proc.stdout or "").splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree "):].strip())
    return REPO


def _link_rembg(tree: Path) -> bool:
    """The primary checkout's rembg venv into the tree: a symlink, else (Windows
    without symlink rights) a directory junction, else nothing (logged)."""
    primary = primary_checkout()
    if link_photo_prep(primary, tree):
        return True
    src = primary / "digitizer" / "rembg_isolated" / "venv"
    dst = tree / "digitizer" / "rembg_isolated" / "venv"
    if not src.is_dir() or dst.exists():
        return dst.exists()
    if os.name == "nt":
        dst.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], **CAPTURED)
        return r.returncode == 0 and dst.exists()
    return False


def ensure_tree(trees: Path, sha: str) -> Path:
    path = guard_scratch(trees / sha, REPO)
    if not (path / "digitizer" / "digitizer_core").is_dir():
        if path.exists():
            discard_worktree(REPO, path)
        _say(f"git worktree add --detach {path} {sha}")
        add_worktree(REPO, sha, path)
    linked = _link_rembg(path)
    _say(f"tree {sha} at {path} (rembg venv {'linked' if linked else 'NOT linked'})")
    return path


def render_one(tree: Path, fixture: str, out: Path, kwargs: dict, python: str,
               size: tuple[float, str] | None = None) -> dict:
    """`size` = (width_mm, garment) overrides the pro job's: the vlm-judge repeat
    (2026-11-04) draws each pair at the SITTING's request, the picture Kent judged."""
    slug, garment, width = job_of(fixture)
    if size is not None:
        width, garment = float(size[0]), str(size[1])
    image = tree / "digitizer" / "testdata" / FIXTURE_ART[fixture]
    if not image.exists():
        raise FileNotFoundError(image)
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONUTF8": "1"}
    t = time.time()
    proc = subprocess.run([python, "-c", DRIVER, str(image), str(out), str(width), garment,
                           str(STUDIO_MAX_COLORS), json.dumps(kwargs)],
                          cwd=str(tree / "digitizer"), timeout=DESIGN_TIMEOUT_S, env=env, **CAPTURED)
    if proc.returncode != 0 or not (out / "ours.dst").exists():
        (out / "failed.txt").write_text((proc.stderr or proc.stdout or "")[-3000:], encoding="utf-8")
        raise RuntimeError(f"engine failed ({proc.returncode}): " + (proc.stderr or proc.stdout or "")[-400:])
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    meta.update(job=slug, fixture=fixture, tree=tree.name, wall_s=round(time.time() - t, 1),
                rendered=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def sitting_size(fixture: str) -> tuple[float, str]:
    """The width and garment the sitting rendered this fixture at (`thin_strokes.REAL_ART`:
    becker 100 mm left_chest, fremont 92.5 mm patch, the rest 80 mm left_chest)."""
    from tools.thin_strokes import REAL_ART
    _rel, width, garment = REAL_ART[fixture]
    return float(width), garment


def render(runs: Path, trees: Path, *, decided_only: bool, take_min: float, slot: Slot,
           only: set[str] | None, python: str, keep_trees: bool,
           size_of=None) -> None:
    """`size_of(fixture) -> (width_mm, garment)` replaces the pro job's size when given."""
    pairs = labelled_pairs()
    if only:
        pairs = [p for p in pairs if p["sitting"] in only]
    todo = [k for k in designs_needed(pairs, decided_only=decided_only)
            if not (design_dir(runs, k[0], k[1], k[2]) / "ours.dst").exists()]
    _say(f"{len(todo)} designs to render into {runs}")
    if not todo:
        return
    by_tree: dict[str, list[tuple]] = {}
    for k in todo:
        by_tree.setdefault(k[0], []).append(k)
    # decided-first order is kept: trees in the order their first design appears
    slot.acquire()
    try:
        for sha in dict.fromkeys(k[0] for k in todo):
            tree = ensure_tree(trees, sha)
            for _t, fixture, side, kw in by_tree[sha]:
                slot.rotate_if_due(take_min)
                out = design_dir(runs, sha, fixture, side)
                if (out / "ours.dst").exists():
                    continue
                _say(f"render {sha}/{fixture}/{side} {json.loads(kw)}")
                try:
                    meta = render_one(tree, fixture, out, json.loads(kw), python,
                                      size=size_of(fixture) if size_of else None)
                    _say(f"  done: {meta['stitches']} stitches, {meta['trims']} trims, "
                         f"{meta['secs']} s engine / {meta['wall_s']} s wall")
                except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                    _say(f"  FAILED: {str(e)[:300]}")
            if not keep_trees:
                discard_worktree(REPO, trees / sha)
                _say(f"tree {sha} removed")
    finally:
        slot.release()


# ------------------------------------------------------------------ measure

def _pro_file(slug: str) -> Path:
    from tools import pro_baseline as pb
    return pb.resolve(pb.JOBS[slug][3])


def pro_figures(slug: str) -> dict:
    from tools import pro_baseline as pb, pro_pair
    pro = _pro_file(slug)
    c = pro_pair.pro_counts(pro)
    return {"cuts": c["trims"], "stitches": c["stitches"], "colour_changes": c["colour_changes"],
            **pb.needle_up(pro), "file": pro.name}


def board_read(slug: str, ours_dst: Path, design: dict, width_mm: float, work: Path, ocr: bool) -> dict:
    """`lettering_board.read_pair` on ours.dst beside the pro's file: per pinned
    line, columns and the word cc on both sides. -> {ours: {columns, word_cc},
    pro: {...}, lines: [...]} with the sums over lines BOTH sides read."""
    from tools import lettering_board as lb
    cache = work / slug
    cache.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ours_dst, cache / "ours.dst")
    blocks = [[int(c.get("r", 0)), int(c.get("g", 0)), int(c.get("b", 0))] for c in design.get("colors") or []]
    (cache / "ours.json").write_text(json.dumps({"width_mm": width_mm, "blocks": blocks, "regions": []}),
                                     encoding="utf-8")
    spec = lb.load_lines()[slug]
    lines = lb.read_pair(slug, spec, work, ocr, log=lambda *_a, **_k: None)   # reads work/<slug>/ours.*
    out = {"ours": {}, "pro": {}, "lines": []}
    col_o = col_p = 0
    n_col = 0
    cc_o = cc_p = wt = 0.0
    for ln in lines:
        o, p = ln["ours"], ln["pro"]
        row = {"text": ln["text"], "columns": (o["columns"].get("v"), p["columns"].get("v")),
               "cc": (o["cc"].get("v"), p["cc"].get("v")), "cc_w": (o["cc"].get("w"), p["cc"].get("w"))}
        out["lines"].append(row)
        if o["columns"].get("v") is not None and p["columns"].get("v") is not None:
            col_o += o["columns"]["v"]
            col_p += p["columns"]["v"]
            n_col += 1
        if o["cc"].get("v") is not None and p["cc"].get("v") is not None and (o["cc"].get("w") or 0) > 0:
            w = float(o["cc"]["w"])
            cc_o += o["cc"]["v"] * w
            cc_p += p["cc"]["v"] * w
            wt += w
    if n_col:
        out["ours"]["columns"], out["pro"]["columns"], out["columns_lines"] = col_o, col_p, n_col
    if wt:
        out["ours"]["word_cc"], out["pro"]["word_cc"], out["word_letters"] = round(cc_o / wt, 4), round(cc_p / wt, 4), wt
    return out


def measure_one(d: Path, *, words: bool) -> dict:
    from tools import pro_baseline as pb, pro_pair
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    slug = meta["job"]
    ours, pro = d / "ours.dst", _pro_file(slug)
    c = pro_pair.pro_counts(ours)
    row = {"job": slug, "tree": meta["tree"], "cuts": c["trims"], "stitches": c["stitches"],
           "colour_changes": c["colour_changes"], **pb.needle_up(ours),
           "width_mm": c["width_mm"], "height_mm": c["height_mm"]}
    try:
        from tools.lane_census import sttype_kappa
        from tools.pro_parity import scorecard
        work = d / "score"
        work.mkdir(parents=True, exist_ok=True)
        pb.write_side(work, "pro", pro)
        pb.write_side(work, "ours", ours)
        k = sttype_kappa(scorecard.score_design(work))
        # `scorecard.chance_correct` CLAMPS at 0: a design below the chance floor
        # reads 0.0 there, which would tie two arms that are both below it. The
        # instrument here is the unclamped kappa, (raw - chance) / (1 - chance).
        raw, chance = k["raw"], k["chance"]
        unclamped = (None if chance is None or chance >= 1.0 - 1e-9
                     else round((raw - chance) / (1.0 - chance), 6))
        row.update(sttype_kappa=unclamped, sttype_kappa_clamped=k["kappa"], sttype_raw=raw,
                   sttype_chance=chance, direction_kappa=k["direction_kappa"], solid_iou=k["solid_iou"])
    except Exception as e:                                        # noqa: BLE001 -- a row, not a crash
        row["kappa_error"] = f"{type(e).__name__}: {e}"[:300]
    if slug in BOARD_SLUGS:
        try:
            design = json.loads((d / "design.json").read_text(encoding="utf-8"))
            b = board_read(slug, ours, design, meta["width_mm"], d / "board", words)
            row.update({k: v for k, v in b["ours"].items()})
            row["pro_board"] = b["pro"]
            row["board_lines"] = b["lines"]
            for key in ("columns_lines", "word_letters"):
                if key in b:
                    row[key] = b[key]
        except Exception as e:                                    # noqa: BLE001
            row["board_error"] = f"{type(e).__name__}: {e}"[:300]
    (d / "measure.json").write_text(json.dumps(row, indent=1), encoding="utf-8")
    return row


def measure(runs: Path, *, words: bool, slot: Slot, take_min: float = TAKE_MIN) -> None:
    """The readers are a census over many designs (the scorecard rasterises each
    pair, tesseract reads each word): a heavy run, so it holds the slot too."""
    dirs = sorted(p.parent for p in runs.glob("*/*/*/ours.dst"))
    todo = [d for d in dirs if not (d / "measure.json").exists()]
    _say(f"{len(todo)} designs to measure ({len(dirs)} rendered)")
    pros = {}
    if todo:
        slot.acquire()
    try:
        for d in todo:
            slot.rotate_if_due(take_min)
            t = time.time()
            row = measure_one(d, words=words)
            pros.setdefault(row["job"], pro_figures(row["job"]))
            _say(f"{d.relative_to(runs)}: cuts {row['cuts']} hops {row['hops']} up {row['needle_up_mm']} "
                 f"kappa {row.get('sttype_kappa')} cols {row.get('columns')} cc {row.get('word_cc')} "
                 f"({time.time() - t:.0f} s)")
    finally:
        slot.release()
    pro_path = runs / "pro.json"
    held = json.loads(pro_path.read_text(encoding="utf-8")) if pro_path.exists() else {}
    for slug in {FIXTURE_JOB[f] for f in FIXTURE_JOB}:
        held.setdefault(slug, pro_figures(slug))
    pro_path.write_text(json.dumps(held, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ build

READ_KEYS = ("cuts", "hops", "needle_up_mm", "stitches", "colour_changes", "sttype_kappa",
             "direction_kappa", "solid_iou", "columns", "word_cc")


def _side(runs: Path, design: tuple) -> tuple[dict, str | None]:
    tree, side, _kw = design
    return tree, side


def build(runs: Path, out: Path, inputs: dict | None = None) -> dict:
    inputs = inputs or json.loads(pooled.INPUTS.read_text(encoding="utf-8"))
    pros = json.loads((runs / "pro.json").read_text(encoding="utf-8")) if (runs / "pro.json").exists() else {}
    sittings: dict[str, dict] = {}
    for p in labelled_pairs(inputs):
        src = inputs["sittings"][p["sitting"]]
        sit = sittings.setdefault(p["sitting"], {
            "date": src.get("date"), "labels": src.get("labels"),
            "tree": SITTINGS.get(p["sitting"], {}).get("tree"),
            "instruments": "both arms re-digitized on the sitting's tree at the pro's width and garment "
                           "(tools.eye_pairs.pro_pooled_build), read beside the pro's DST with today's readers",
            "pairs": []})
        row = {"id": p["id"], "arm": p["arm"], "fixture": p["fixture"], "label": p["label"],
               "judged": p.get("judged"), "job": FIXTURE_JOB[p["fixture"]], "before": {}, "after": {}}
        if "before_design" not in p:
            row["unscored_why"] = p["unscored_why"]
            sit["pairs"].append(row)
            continue
        why = []
        for name, design in (("before", p["before_design"]), ("after", p["after_design"])):
            tree, side, _kw = design
            d = design_dir(runs, tree, p["fixture"], side)
            m = d / "measure.json"
            if not m.exists():
                why.append(f"{name}: {tree}/{p['fixture']}/{side} not rendered"
                           + (" (engine failed)" if (d / "failed.txt").exists() else ""))
                continue
            r = json.loads(m.read_text(encoding="utf-8"))
            row[name] = {k: r[k] for k in READ_KEYS if r.get(k) is not None}
            row[name]["engine"] = f"{tree}:{side}"
            if r.get("pro_board"):
                # the pro's board figures are read in a frame registered to OUR file,
                # so they are kept per side, not merged
                row.setdefault("pro_side", {})[name] = dict(r["pro_board"])
        row["pro"] = dict(pros.get(row["job"], {}))
        if why:
            row["unscored_why"] = "; ".join(why)
        sit["pairs"].append(row)
    data = {"schema": 1, "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "tools.eye_pairs.pro_pooled_build", "fixture_job": FIXTURE_JOB,
            "trees": {s: v["tree"] for s, v in SITTINGS.items()}, "sittings": sittings}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


# ------------------------------------------------------------------ cli

def plan_report(decided_only: bool) -> str:
    pairs = labelled_pairs()
    designs = designs_needed(pairs, decided_only=decided_only)
    L = [f"labelled pairs with a pro file: {len(pairs)} "
         f"(Kent chose a side on {sum(1 for p in pairs if p['kent'] != 'tie')})",
         f"designs to render{' (decided pairs only)' if decided_only else ''}: {len(designs)}", ""]
    by: dict[str, int] = {}
    for tree, _f, _s, _k in designs:
        by[tree] = by.get(tree, 0) + 1
    L += [f"  {t}: {n}" for t, n in by.items()]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("plan", "render", "measure", "build"))
    ap.add_argument("--runs", type=Path)
    ap.add_argument("--trees", type=Path, help="where the detached worktrees go (outside the repo)")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--decided-only", action="store_true")
    ap.add_argument("--only", nargs="*", help="sitting ids")
    ap.add_argument("--take-min", type=float, default=TAKE_MIN)
    ap.add_argument("--no-slot", action="store_true", help="do not take the laptop's CPU slot")
    ap.add_argument("--no-words", action="store_true", help="skip the tesseract word reads")
    ap.add_argument("--keep-trees", action="store_true")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--sitting-size", action="store_true",
                    help="render at the sitting's own width and garment (REAL_ART), not the pro job's")
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        print(plan_report(a.decided_only))
        return 0
    if a.runs is None:
        ap.error("--runs is required")
    # The engine driver runs with the detached TREE as its cwd: a relative --runs
    # sends every design into the temp tree, which is then removed (2026-11-04).
    a.runs = a.runs.resolve()
    if a.trees is not None:
        a.trees = a.trees.resolve()
    if a.cmd == "render":
        trees = a.trees or (Path(os.environ.get("TEMP", ".")) / "embwt" / "trees")
        slot = Slot(None if a.no_slot else default_slot(), "pro_pooled_build render (yardstick pro-pair)")
        render(a.runs, trees, decided_only=a.decided_only, take_min=a.take_min, slot=slot,
               only=set(a.only) if a.only else None, python=a.python, keep_trees=a.keep_trees,
               size_of=sitting_size if a.sitting_size else None)
    elif a.cmd == "measure":
        slot = Slot(None if a.no_slot else default_slot(), "pro_pooled_build measure (yardstick pro-pair)")
        measure(a.runs, words=not a.no_words, slot=slot, take_min=a.take_min)
    else:
        data = build(a.runs, a.out)
        n = sum(len(s["pairs"]) for s in data["sittings"].values())
        scored = sum(1 for s in data["sittings"].values() for p in s["pairs"] if p["before"] and p["after"])
        print(f"wrote {a.out}: {n} pairs, {scored} with both designs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
