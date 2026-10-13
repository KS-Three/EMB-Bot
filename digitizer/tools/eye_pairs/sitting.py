"""A blinded eye-pairs sitting, prepared from a pre-registered spec.

    python -m tools.eye_pairs.sitting check   SPEC
    python -m tools.eye_pairs.sitting prepare SPEC --out DIR [--workers N] [--manifest PATH]
    python -m tools.eye_pairs.sitting analyse SPEC --out DIR [--markdown PATH] [--inputs PATH]

`SPEC` is `docs/eye-pairs-2026-10-13/wok42/spec.json` (MASTER_SCOPE
Waiting-on-Kent 42; its PRE-REGISTRATION was committed before anything was
rendered). The spec names the logos (each with a provenance, none of them one
Kent has already judged), the base flags, the arms and the pre-registered
expected pick and manipulation expectations of each, and the leads and
statistics the analysis will read.

* `check` validates the spec and prints nothing about any design.
* `prepare` draws the generator logos, renders base and every arm
  (`tools.eye_pairs.render`, optionally in parallel lanes merged by
  `merge.merge_lanes`), runs the MANIPULATION CHECK from the designs alone and
  swaps a failing arm for its stratum's reserve once, builds the blind pairs
  (`tools.eye_pairs.pair`: sides shuffled, opaque ids, sealed key
  `arms.json`) and writes a public `manifest.json` that carries the sealed
  map's hash and no arm-to-pair mapping.
* `analyse` REFUSES until every pair is picked, then reports Cohen's kappa
  with percentile bootstrap intervals over pairs and over designs (ROADMAP
  gate 4: no raw agreement figure anywhere) for the registered leads, the
  trims-held split, and how well the pre-registered expected picks predicted
  him. Serve the picker with `python -m tools.eye_pairs --serve --out DIR`.

Pure helpers (`validate_spec`, `manipulation_check`, `labelled_inputs`,
`confirmatory`) take plain dicts so the tests need no engine.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from digitizer_core.config import PipelineConfig

from . import analysis as an
from . import density_flow as df
from . import pooled
from .pairs import BASE, load_picks, unpicked

ROOT = Path(__file__).resolve().parents[2]            # digitizer/
REPO = ROOT.parent
TESTDATA = ROOT / "testdata"
DEFAULT_SPEC = REPO / "docs" / "eye-pairs-2026-10-13" / "wok42" / "spec.json"
PHOTO_PREP_VENV = Path("digitizer") / "rembg_isolated" / "venv"

KINDS = frozenset({"client_art_already_committed", "synthetic_generator", "synthetic_committed"})
PICKS = frozenset({"arm", "base", "tie"})
DIRECTIONS = frozenset({"lower", "higher"})
# Drawn by a committed generator, never stored: id -> (module, function). The
# function returns a BGR uint8 image and has no arguments.
GENERATORS = {
    "fritsch_serif": ("tools.make_hard_cases", "serif_text"),
    "board_80": ("tools.small_print", "synthetic_text"),
}
NAME = re.compile(r"^[a-z][a-z0-9_]*$")
# The label each side of a pair carries in `pooled`'s vocabulary: LEFT is
# `before`, RIGHT is `after`, whatever arm is there.
LABEL = {"L": "before", "R": "after", "tie": "same"}


class SpecError(ValueError):
    """The spec cannot be built from; the message lists every problem."""


# ----------------------------------------------------------------- spec ----

def load_spec(path: Path = DEFAULT_SPEC) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha16(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def _md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def judged_files(testdata: Path = TESTDATA) -> dict[str, Path]:
    """name -> the file of every logo Kent has judged (`thin_strokes.REAL_ART`:
    nine of them, plus `thermal`, byte-equal to drone)."""
    from tools.thin_strokes import REAL_ART

    return {name: testdata / rel for name, (rel, _w, _g) in REAL_ART.items()}


def _config_defaults() -> dict:
    out = {}
    for f in dataclasses.fields(PipelineConfig):
        if f.default is not dataclasses.MISSING:
            out[f.name] = f.default
    return out


def _check_arm(name: str, arm: dict, spec: dict, fields: set, defaults: dict,
               problems: list[str]) -> None:
    thr = spec["manipulation"]["thresholds"]
    flags = arm.get("flags")
    if not isinstance(flags, dict) or not flags:
        problems.append(f"arm {name!r}: no flags")
        flags = {}
    for k, v in flags.items():
        if k not in fields:
            problems.append(f"arm {name!r}: {k!r} is not a PipelineConfig field")
            continue
        base_v = spec["base_flags"].get(k, defaults.get(k))
        if base_v == v:
            problems.append(f"arm {name!r}: {k}={v!r} is what the base already runs, so it "
                            "would be identical to base")
    if arm.get("expected_pick") not in PICKS:
        problems.append(f"arm {name!r}: expected_pick must be one of {sorted(PICKS)}")
    if not arm.get("variable") or not arm.get("stratum"):
        problems.append(f"arm {name!r}: needs a `variable` and a `stratum`")
    for m, d in (arm.get("moves") or {}).items():
        if m not in thr or d not in ("up", "down"):
            problems.append(f"arm {name!r}: moves {m!r}={d!r} (no threshold for that metric, "
                            "or the direction is not up or down)")
    for m in arm.get("holds") or []:
        if m not in thr:
            problems.append(f"arm {name!r}: holds {m!r}, which has no threshold")


def validate_spec(spec: dict, *, testdata: Path = TESTDATA,
                  judged: dict[str, Path] | None = None) -> None:
    """Raises `SpecError` listing EVERY problem. The blinding guard lives
    here: a logo named like, or byte-equal to, one Kent has judged is refused
    (blinding is spent on those), and so is a logo with no provenance."""
    problems: list[str] = []
    for key in ("sitting", "seed", "base_flags", "logos", "arms", "reserve_arms",
                "manipulation", "leads", "judged_fixtures"):
        if key not in spec:
            problems.append(f"spec has no {key!r}")
    if problems:
        raise SpecError("; ".join(problems))
    if spec.get("schema") != 1:
        problems.append(f"schema {spec.get('schema')!r} is not 1")
    for k in ("seed", "n_identical", "n_repeat"):
        if not isinstance(spec.get(k), int) or spec[k] < 0:
            problems.append(f"{k} must be a non-negative integer")
    fields = {f.name for f in dataclasses.fields(PipelineConfig)}
    defaults = _config_defaults()
    for k in spec["base_flags"]:
        if k not in fields:
            problems.append(f"base flag {k!r} is not a PipelineConfig field")

    judged_names = set(spec["judged_fixtures"])
    if judged is None:
        judged = judged_files(testdata)
    judged_md5 = {_md5(p): n for n, p in judged.items() if Path(p).exists()}
    seen_names, seen_md5 = set(), {}
    for lg in spec["logos"]:
        name = lg.get("name", "?")
        if not NAME.match(str(name)):
            problems.append(f"logo name {name!r} is not [a-z][a-z0-9_]*")
        if name in seen_names:
            problems.append(f"logo {name!r} is listed twice")
        seen_names.add(name)
        if name in judged_names or name in judged or lg.get("design") in judged_names:
            problems.append(f"logo {name!r} is one Kent has judged; blinding is spent on it")
        if not str(lg.get("provenance", "")).strip():
            problems.append(f"logo {name!r} has no provenance")
        if lg.get("kind") not in KINDS:
            problems.append(f"logo {name!r}: kind {lg.get('kind')!r} not in {sorted(KINDS)}")
        if not lg.get("design"):
            problems.append(f"logo {name!r} has no `design` (its independence cluster)")
        if not (isinstance(lg.get("width_mm"), (int, float)) and lg.get("garment")):
            problems.append(f"logo {name!r} needs width_mm and garment")
        src = lg.get("source") or {}
        if src.get("kind") == "file":
            p = Path(testdata).parent / src.get("path", "")
            if not p.exists():
                problems.append(f"logo {name!r}: {src.get('path')!r} does not exist")
                continue
            if _sha16(p) != src.get("sha256_16"):
                problems.append(f"logo {name!r}: {src.get('path')!r} is not the file the spec "
                                "pinned (sha256 differs)")
            m = _md5(p)
            if m in judged_md5:
                problems.append(f"logo {name!r} is byte-equal to the judged {judged_md5[m]!r}")
            if m in seen_md5:
                problems.append(f"logo {name!r} is byte-equal to logo {seen_md5[m]!r}")
            seen_md5[m] = name
        elif src.get("kind") == "generator":
            if src.get("id") not in GENERATORS:
                problems.append(f"logo {name!r}: generator {src.get('id')!r} is not registered")
        else:
            problems.append(f"logo {name!r}: source kind {src.get('kind')!r}")
    if not spec["logos"]:
        problems.append("no logos")

    names = set()
    for name, arm in spec["arms"].items():
        names.add(name)
        if name == BASE or name.startswith("ref_"):
            problems.append(f"arm name {name!r} is reserved")
        _check_arm(name, arm, spec, fields, defaults, problems)
    for r in spec["reserve_arms"]:
        if r.get("name") in names:
            problems.append(f"reserve {r.get('name')!r} repeats an arm name")
        names.add(r.get("name"))
        _check_arm(r.get("name", "?"), r, spec, fields, defaults, problems)
    flagsets = [json.dumps(a["flags"], sort_keys=True) for a in spec["arms"].values()]
    if len(set(flagsets)) != len(flagsets):
        problems.append("two arms carry the same flags")
    for lead in spec["leads"].get("primary", []) + spec["leads"].get("secondary", []):
        if lead.get("direction") not in DIRECTIONS or lead.get("metric") not in df.directions():
            problems.append(f"lead {lead!r}: metric unknown or direction not lower/higher")
    if problems:
        raise SpecError("; ".join(problems))


# --------------------------------------------------------------- inputs ----

def draw_generator(gid: str):
    mod, fn = GENERATORS[gid]
    return getattr(importlib.import_module(mod), fn)()


def materialise(spec: dict, dest: Path) -> list[dict]:
    """Writes every generator logo under `dest/inputs/` and returns, per logo,
    {name, design, path, sha256, width_mm, garment, kind, provenance}."""
    import cv2

    inputs = Path(dest) / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    out = []
    for lg in spec["logos"]:
        src = lg["source"]
        if src["kind"] == "file":
            path = TESTDATA.parent / src["path"]
        else:
            path = inputs / f"{lg['name']}.png"
            if not cv2.imwrite(str(path), draw_generator(src["id"])):
                raise OSError(f"could not write {path}")
        out.append({"name": lg["name"], "design": lg["design"], "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "width_mm": float(lg["width_mm"]), "garment": lg["garment"],
                    "kind": lg["kind"], "provenance": lg["provenance"]})
    return out


def _cases(logos: list[dict], names=None) -> list[tuple]:
    return [(lg["name"], Path(lg["path"]), lg["width_mm"], lg["garment"])
            for lg in logos if names is None or lg["name"] in names]


# ---------------------------------------------------- manipulation check ----

_MEMO: dict[tuple, dict] = {}


def _metric_values(design: dict, metrics) -> dict:
    """The thresholded metrics of one whole design. Memoised on the stitch
    stream: `df.measure` unions every stitch as a thread footprint, which costs
    seconds on a 10,000-stitch design, and the base is read once per arm."""
    key = (hashlib.sha1(_stitch_stream(design).encode("utf-8")).hexdigest(), tuple(sorted(metrics)))
    if key not in _MEMO:
        m = df.measure(design, None, support=False)
        _MEMO[key] = {k: m.get(k) for k in metrics}
    return _MEMO[key]


def _delta(kind: str, base, arm):
    if base is None or arm is None:
        return None
    if kind == "rel":
        return None if base == 0 else (arm - base) / base
    return arm - base


def manipulation_check(spec: dict, designs: dict, arms: dict | None = None) -> dict:
    """`designs[(logo, arm)]` -> Design dict, `BASE` included. Per arm, on every
    logo where its stitch stream differs from base: did every `moves` metric
    move the stated way by its threshold and every `holds` metric by less than
    its threshold? An arm passes on at least 2 logos AND at least half of the
    logos it changes, and fails when it is byte-identical to base on 4 or more
    of the spec's logos (an inert arm spends his time on nothing). Designs
    only: nothing here has seen a pick."""
    thr = spec["manipulation"]["thresholds"]
    arms = spec["arms"] if arms is None else arms
    logos = [lg["name"] for lg in spec["logos"]]
    table = {}
    for name, arm in arms.items():
        per, identical = {}, []
        for lg in logos:
            b, a = designs.get((lg, BASE)), designs.get((lg, name))
            if b is None or a is None:
                continue
            if _stitch_stream(b) == _stitch_stream(a):
                identical.append(lg)
                continue
            vb, va = _metric_values(b, thr), _metric_values(a, thr)
            cells, ok = {}, True
            for m, t in thr.items():
                d = _delta(t["kind"], vb[m], va[m])
                cells[m] = {"base": vb[m], "arm": va[m], "delta": d}
            for m, direction in (arm.get("moves") or {}).items():
                d = cells[m]["delta"]
                good = d is not None and (d >= thr[m]["value"] if direction == "up"
                                          else d <= -thr[m]["value"])
                cells[m]["moved_as_registered"] = good
                ok &= good
            for m in arm.get("holds") or []:
                d = cells[m]["delta"]
                held = d is None or abs(d) < thr[m]["value"]
                cells[m]["held"] = held
                ok &= held
            per[lg] = {"metrics": cells, "ok": ok}
        active = list(per)
        n_ok = sum(1 for v in per.values() if v["ok"])
        if len(identical) >= 4:
            passes, why = False, f"identical to base on {len(identical)} of {len(logos)} logos"
        elif len(active) < 2:
            passes, why = False, f"changes {len(active)} logo(s); at least 2 are needed"
        elif n_ok * 2 < len(active):
            passes, why = False, f"moved and held as registered on {n_ok} of {len(active)} logos"
        else:
            passes, why = True, f"as registered on {n_ok} of {len(active)} logos"
        table[name] = {"stratum": arm["stratum"], "active": active, "identical": identical,
                       "per_logo": per, "passes": passes, "why": why}
    return table


def _stitch_stream(design: dict) -> str:
    return json.dumps(design["stitches"], sort_keys=True, separators=(",", ":"))


def settle_arms(spec: dict, designs_for, render_arm) -> tuple[dict, list[dict], dict]:
    """-> (final arms, replacements, manipulation table of the final arms).

    `designs_for()` returns the `designs` dict `manipulation_check` reads;
    `render_arm(reserve)` renders one reserve. A failing arm is replaced by
    the first unused reserve of its stratum, ONCE: a reserve that fails too
    stays, flagged, so nothing is swapped twice in search of a pass."""
    arms = dict(spec["arms"])
    table = manipulation_check(spec, designs_for(), arms)
    used, replacements = set(), []
    for name in list(arms):
        if table[name]["passes"]:
            continue
        reserve = next((r for r in spec["reserve_arms"]
                        if r["stratum"] == arms[name]["stratum"] and r["name"] not in used), None)
        if reserve is None:
            replacements.append({"arm": name, "reason": table[name]["why"], "replaced_by": None})
            continue
        used.add(reserve["name"])
        reason = table.pop(name)["why"]
        render_arm(reserve)
        del arms[name]
        arms[reserve["name"]] = reserve
        new = manipulation_check(spec, designs_for(), {reserve["name"]: reserve})
        table.update(new)
        replacements.append({"arm": name, "reason": f"failed: {reason}",
                             "replaced_by": reserve["name"],
                             "reserve_passes": new[reserve["name"]]["passes"]})
    return arms, replacements, table


# -------------------------------------------------------------- prepare ----

def _load_designs(out: Path) -> dict:
    designs = {}
    for f in sorted((Path(out) / "designs").glob("*.json")):
        if "__" in f.stem:
            logo, arm = f.stem.split("__", 1)
            designs[(logo, arm)] = json.loads(f.read_text(encoding="utf-8"))
    return designs


def _render_lane(spec_path: str, lane: str, logos_json: str, arms_json: str) -> int:
    """One render lane in a worker process (top level so it can be pickled)."""
    from . import __main__ as cli

    spec = load_spec(Path(spec_path))
    return cli.render(Path(lane), cases=_cases(json.loads(logos_json)),
                      arms={k: v["flags"] for k, v in json.loads(arms_json).items()},
                      base=dict(spec["base_flags"]))


def render_all(spec: dict, spec_path: Path, out: Path, logos: list[dict], arms: dict,
               workers: int = 1) -> None:
    from . import __main__ as cli
    from .merge import merge_lanes

    if workers <= 1 or len(logos) < 2:
        cli.render(out, cases=_cases(logos), arms={k: v["flags"] for k, v in arms.items()},
                   base=dict(spec["base_flags"]))
        return
    from concurrent.futures import ProcessPoolExecutor

    lanes = [Path(out) / "_lanes" / f"lane{i}" for i in range(min(workers, len(logos)))]
    groups = [logos[i::len(lanes)] for i in range(len(lanes))]
    with ProcessPoolExecutor(max_workers=len(lanes)) as ex:
        futures = [ex.submit(_render_lane, str(spec_path), str(lane), json.dumps(g),
                             json.dumps(arms)) for lane, g in zip(lanes, groups)]
        for f in futures:
            f.result()
    merge_lanes(Path(out), lanes)
    shutil.rmtree(Path(out) / "_lanes", ignore_errors=True)


def _git_head() -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True,
                           text=True, timeout=20)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def manifest(spec: dict, spec_bytes: bytes, logos: list[dict], arms: dict, replacements: list,
             table: dict, out: Path, n_pairs: int, photo_prep_venv: bool) -> dict:
    """The PUBLIC description of the kit. It names the arms and counts the
    pairs; it never says which pair is which arm or which side is which, and
    carries a hash of the sealed map so the key cannot change afterwards."""
    out = Path(out)
    sealed = json.loads((out / "arms.json").read_text(encoding="utf-8"))
    sitting = json.loads((out / "sitting.json").read_text(encoding="utf-8"))
    feats = json.loads((out / "features.json").read_text(encoding="utf-8"))
    lines = sorted(f"{fx}|{arm}|{row['design_hash']}" for fx, by in feats.items()
                   if fx != "__sources__" for arm, row in by.items()
                   if "error" not in row and (arm == BASE or arm in arms))
    kinds = [s["kind"] for s in sealed.values()]
    per_logo = {lg["name"]: sum(1 for s in sealed.values()
                                if s["kind"] == "live" and s["fixture"] == lg["name"])
                for lg in logos}
    return {
        "schema": 1, "sitting": spec["sitting"], "built": datetime.now().astimezone().isoformat(
            timespec="seconds"),
        "spec_sha256": hashlib.sha256(spec_bytes).hexdigest(),
        "engine": {"git_head": _git_head(), "python": platform.python_version(),
                   "platform": platform.platform(), "photo_prep_venv": photo_prep_venv},
        "base_flags": spec["base_flags"], "seed": spec["seed"],
        "logos": [{k: lg[k] for k in ("name", "design", "kind", "sha256", "width_mm", "garment",
                                      "provenance")} for lg in logos],
        "arms": {n: {"flags": a["flags"], "stratum": a["stratum"],
                     "expected_pick": a["expected_pick"], "moves": a.get("moves") or {},
                     "holds": a.get("holds") or []} for n, a in arms.items()},
        "replacements": replacements,
        "manipulation": {n: {"passes": t["passes"], "why": t["why"]} for n, t in table.items()},
        "pairs": {"total": n_pairs, "live": kinds.count("live"),
                  "identical": kinds.count("identical"), "repeat": kinds.count("repeat"),
                  "live_base_left": sum(1 for s in sealed.values()
                                        if s["kind"] == "live" and s["left_arm"] == BASE),
                  "live_per_logo": per_logo},
        "sealed_sha256": sitting["sealed_sha256"],
        "designs_sha256": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(),
        "commands": [
            "cd digitizer",
            "python -m tools.eye_pairs --serve --out <OUT>      # Kent's sitting; picks go to <OUT>/picks.jsonl",
            "python -m tools.eye_pairs.sitting analyse <SPEC> --out <OUT>   # refuses until every pair is picked",
        ],
    }


def prepare(spec_path: Path, out: Path, *, workers: int = 1, manifest_to: Path | None = None,
            link_photo_prep: Path | None = None) -> dict:
    from . import __main__ as cli
    from . import refarm

    spec_path = Path(spec_path)
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8"))
    validate_spec(spec)
    out = Path(out)
    if (out / "picks.jsonl").exists() and (out / "picks.jsonl").stat().st_size:
        raise SystemExit("REFUSED: picks.jsonl holds picks; a kit is not rebuilt over a sitting.")
    if link_photo_prep is not None:
        refarm.link_photo_prep(Path(link_photo_prep), REPO)
    venv = (REPO / PHOTO_PREP_VENV).is_dir()
    if not venv:
        print("WARNING: no rembg_isolated/venv here, so a photo-class logo (mfab) is prepped "
              "without the cutout the product ships; pass --link-photo-prep <primary checkout>",
              file=sys.stderr)
    out.mkdir(parents=True, exist_ok=True)
    logos = materialise(spec, out)
    arms = dict(spec["arms"])
    render_all(spec, spec_path, out, logos, arms, workers)

    def render_reserve(reserve: dict) -> None:
        cli.render(out, cases=_cases(logos), arms={reserve["name"]: reserve["flags"]},
                   base=dict(spec["base_flags"]))

    final, replacements, table = settle_arms(spec, lambda: _load_designs(out), render_reserve)
    n = cli.pair(out, seed=spec["seed"], n_identical=spec["n_identical"],
                 n_repeat=spec["n_repeat"], arms=set(final), balance_live=True)
    (out / "manipulation.json").write_text(json.dumps(table, indent=1), encoding="utf-8")
    man = manifest(spec, spec_bytes, logos, final, replacements, table, out, n, venv)
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    if manifest_to:
        Path(manifest_to).parent.mkdir(parents=True, exist_ok=True)
        Path(manifest_to).write_text(json.dumps(man, indent=1), encoding="utf-8")
    return man


# -------------------------------------------------------------- analyse ----

def _label_of_expected(expected: str, arm: str, s: dict) -> str:
    if expected == "tie":
        return "same"
    side_arm = "after" if s["right_arm"] == arm else "before"
    side_base = "before" if side_arm == "after" else "after"
    return side_arm if expected == "arm" else side_base


def require_complete(out: Path) -> tuple[dict, dict]:
    """-> (sealed, picks) or refuses: no statistic is read off a part-picked
    sitting, the same rule as `--reveal`."""
    out = Path(out)
    public = json.loads((out / "pairs.json").read_text(encoding="utf-8"))
    sealed = json.loads((out / "arms.json").read_text(encoding="utf-8"))
    picks = load_picks(out / "picks.jsonl")
    ids = [p["pair"] for p in public]
    unknown = sorted(set(picks) - set(ids))
    if unknown:
        raise SystemExit(f"REFUSED: picks name pairs that do not exist: {', '.join(unknown)}")
    missing = unpicked(ids, picks)
    if missing:
        raise SystemExit(f"REFUSED: {len(missing)} of {len(ids)} pairs have no pick yet "
                         f"(first: {missing[0]}). Every pair is picked before any figure is read.")
    return sealed, picks


def labelled_inputs(spec: dict, man: dict, sealed: dict, picks: dict, designs: dict) -> dict:
    """`density_flow`'s input format for ONE sitting: every LIVE pair, LEFT as
    `before` and RIGHT as `after`, Kent's pick as the label, every candidate
    measured from the stored designs on the shapes the arm changed. Identical
    and repeat pairs are controls and are not here."""
    from tools.eye_pairs_price import changed_shapes

    design_of = {lg["name"]: lg["design"] for lg in man["logos"]}
    tol = spec["manipulation"]["density_matched_tolerance"]
    trims_thr = spec["manipulation"]["thresholds"]["trims_per_1000"]["value"]
    pairs = []
    for pid in sorted(sealed):
        s = sealed[pid]
        if s["kind"] != "live":
            continue
        fx = s["fixture"]
        arm = s["right_arm"] if s["left_arm"] == BASE else s["left_arm"]
        dl, dr = designs[(fx, s["left_arm"])], designs[(fx, s["right_arm"])]
        ch = changed_shapes(designs[(fx, BASE)], designs[(fx, arm)]) or None
        sides = {}
        for side, d in (("before", dl), ("after", dr)):
            m = df.measure(d, ch, support=False)
            sides[side] = {k: (round(v, 6) if isinstance(v, float) else v)
                           for k, v in m.items() if v is not None}
        exp = man["arms"][arm]["expected_pick"]
        want = _label_of_expected(exp, arm, s)
        sides["before"]["prereg_pick"], sides["after"]["prereg_pick"] = (
            (1, 0) if want == "before" else (0, 1) if want == "after" else (0, 0))
        b, a = sides["before"], sides["after"]
        dens_b, dens_a = b.get("thread_density_whole"), a.get("thread_density_whole")
        dens_ok = (dens_b not in (None, 0) and dens_a is not None
                   and abs(dens_a - dens_b) / dens_b <= tol)
        tb, ta = b.get("trims_per_1000"), a.get("trims_per_1000")
        pairs.append({
            "id": pid, "arm": arm, "fixture": design_of[fx], "logo": fx,
            "stratum": man["arms"][arm]["stratum"], "label": LABEL[picks[pid]["choice"]],
            "expected_label": want, "before": b, "after": a,
            "designs": {"changed_shapes": len(ch) if ch else 0},
            "density_matched": bool(dens_ok),
            "arm_isolates": bool((man.get("manipulation") or {}).get(arm, {}).get("passes")),
            "trims_held": tb is not None and ta is not None and abs(ta - tb) < trims_thr})
    return {"schema": 1, "built": datetime.now().astimezone().date().isoformat(),
            "labels_from": f"{man['sitting']} picks.jsonl via the sealed map (LEFT=before, RIGHT=after)",
            "candidates": {k: list(v) for k, v in df.CANDIDATES.items()},
            "sittings": {man["sitting"]: {"date": man["built"][:10], "labels": "blind picker",
                                          "designs": "the sitting's render directory",
                                          "pairs": pairs}}}


def _directions(spec: dict) -> dict:
    d = dict(df.directions())
    for lead in spec["leads"]["primary"] + spec["leads"]["secondary"]:
        d[lead["metric"]] = (lead["direction"], d.get(lead["metric"], ("", "registered lead"))[1])
    d["prereg_pick"] = ("higher", "the pre-registered expected pick, as a side")
    return d


def _read(r: dict, c: dict) -> dict:
    c2, c3 = (c["ci2_lo"], c["ci2_hi"]), (c["ci3_lo"], c["ci3_hi"])
    return {"n_scored": r["n_scored"], "n_decided": r["n_decided"],
            "silent_on_decided": r["n_instrument_silent_on_decided"],
            "kappa_sides": r["kappa_decided"], "ci_sides_pairs": [r["ci2_lo"], r["ci2_hi"]],
            "ci_sides_designs": list(c2),
            "reading_sides": pooled.reading(r["n_decided"], (r["ci2_lo"], r["ci2_hi"]), c2),
            "kappa_ties": r["kappa_3way"], "ci_ties_pairs": [r["ci3_lo"], r["ci3_hi"]],
            "ci_ties_designs": list(c3),
            "reading_ties": pooled.reading(r["n_scored"], (r["ci3_lo"], r["ci3_hi"]), c3)}


def _agree(rows: list[dict], metric: str, dirs: dict) -> dict:
    return _read(pooled.agreement(rows, metric, directions=dirs),
                 pooled.agreement(rows, metric, cluster=True, directions=dirs))


def confirmatory(inputs: dict, spec: dict) -> dict:
    """The pre-registered reading: each primary and secondary lead over the
    live pairs, the same lead on the trims-held and trims-moved halves, and the
    pre-registration's own expected picks as one more instrument. Kappa and
    its two intervals only; a raw agreement figure is never computed."""
    rows = pooled.select(pooled.pooled_pairs(inputs))
    dirs = _directions(spec)
    out = {"n_live_pairs": len(rows),
           "n_decided_by_kent": sum(1 for p in rows if p["label"] != "same"),
           "leads": {}, "trims_split": {}, "isolating_only": {}, "prereg": None,
           "density_matched": {"matched": sum(1 for p in rows if p["density_matched"]),
                               "not_matched": sum(1 for p in rows if not p["density_matched"])}}
    held = [p for p in rows if p["trims_held"]]
    moved = [p for p in rows if not p["trims_held"]]
    isolating = [p for p in rows if p["arm_isolates"]]
    for tier in ("primary", "secondary"):
        for lead in spec["leads"][tier]:
            m = lead["metric"]
            out["leads"][m] = {"tier": tier, "direction": lead["direction"], **_agree(rows, m, dirs)}
            if tier == "primary":
                out["isolating_only"][m] = {"n_pairs": len(isolating), **_agree(isolating, m, dirs)}
                out["trims_split"][m] = {"trims_held": {"n_pairs": len(held),
                                                        **_agree(held, m, dirs)},
                                         "trims_moved": {"n_pairs": len(moved),
                                                         **_agree(moved, m, dirs)}}
    out["prereg"] = _agree(rows, "prereg_pick", dirs)
    ctrl = out["leads"].get("trims_per_1000")
    out["control_replicates"] = (ctrl is not None and "above chance" in
                                 (ctrl["reading_sides"], ctrl["reading_ties"]))
    return out


def controls_report(sealed: dict, picks: dict) -> dict:
    """Counts of his own answers on the two control kinds, with their n. Used
    to flag a side habit or a noisy sitting; never an agreement figure."""
    ident = [picks[p]["choice"] for p, s in sealed.items() if s["kind"] == "identical"]
    ceil = an.ceiling(sealed, picks)
    sided = [c for c in (picks[p]["choice"] for p in sealed) if c != "tie"]
    return {"identical_pairs": len(ident), "identical_called_tie": ident.count("tie"),
            "repeat_pairs": ceil["n"], "repeat_answered_differently": ceil["n"] - ceil["consistent"],
            "left_picks": sided.count("L"), "right_picks": sided.count("R")}


def _f(v) -> str:
    return "n/a" if v is None else f"{v:+.2f}"


def _ci(v) -> str:
    return "n/a" if v is None or v[0] is None else f"[{v[0]:+.2f}, {v[1]:+.2f}]"


def markdown(rep: dict, ctrl: dict, man: dict) -> str:
    L = [f"# {man['sitting']}: analysis (kappa with 95% bootstrap intervals; n beside every figure)", "",
         f"{rep['n_live_pairs']} live pairs, Kent chose a side on {rep['n_decided_by_kent']}. "
         f"Density held within tolerance on {rep['density_matched']['matched']} pairs, not on "
         f"{rep['density_matched']['not_matched']}.", ""]
    head = ("| metric | tier | better | n scored | n Kent decided | kappa sides only | CI pairs | "
            "CI designs | reading | kappa ties in | CI pairs | CI designs | reading |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    L += [head]
    for m, r in rep["leads"].items():
        L.append(f"| `{m}` | {r['tier']} | {r['direction']} | {r['n_scored']} | {r['n_decided']} | "
                 f"{_f(r['kappa_sides'])} | {_ci(r['ci_sides_pairs'])} | {_ci(r['ci_sides_designs'])} | "
                 f"{r['reading_sides']} | {_f(r['kappa_ties'])} | {_ci(r['ci_ties_pairs'])} | "
                 f"{_ci(r['ci_ties_designs'])} | {r['reading_ties']} |")
    L += ["", f"**Control `trims_per_1000` replicates: {'yes' if rep['control_replicates'] else 'NO'}.** "
          "If no, read nothing else in this table.", "",
          "## Trims held against trims moved (the separation)", "",
          "| metric | split | n pairs | n decided | kappa sides only | CI pairs | CI designs | "
          "reading | kappa ties in | reading |", "|---|---|---|---|---|---|---|---|---|---|"]
    for m, halves in rep["trims_split"].items():
        for name, r in halves.items():
            L.append(f"| `{m}` | {name} | {r['n_pairs']} | {r['n_decided']} | {_f(r['kappa_sides'])} | "
                     f"{_ci(r['ci_sides_pairs'])} | {_ci(r['ci_sides_designs'])} | {r['reading_sides']} | "
                     f"{_f(r['kappa_ties'])} | {r['reading_ties']} |")
    L += ["", "## Arms that passed the manipulation check, alone", "",
          "| metric | n pairs | n decided | kappa sides only | CI pairs | CI designs | reading | "
          "kappa ties in | reading |", "|---|---|---|---|---|---|---|---|---|"]
    for m, r in rep["isolating_only"].items():
        L.append(f"| `{m}` | {r['n_pairs']} | {r['n_decided']} | {_f(r['kappa_sides'])} | "
                 f"{_ci(r['ci_sides_pairs'])} | {_ci(r['ci_sides_designs'])} | {r['reading_sides']} | "
                 f"{_f(r['kappa_ties'])} | {r['reading_ties']} |")
    p = rep["prereg"]
    L += ["", "## Did the pre-registration predict his eye?", "",
          f"Expected picks against his, over {p['n_scored']} pairs: kappa sides only {_f(p['kappa_sides'])} "
          f"{_ci(p['ci_sides_pairs'])} (designs {_ci(p['ci_sides_designs'])}), {p['reading_sides']}; "
          f"ties in {_f(p['kappa_ties'])} {_ci(p['ci_ties_pairs'])} (designs {_ci(p['ci_ties_designs'])}), "
          f"{p['reading_ties']}.", "",
          "## Controls (counts of his own answers)", "",
          f"- identical pairs called a tie: {ctrl['identical_called_tie']} of {ctrl['identical_pairs']}",
          f"- repeats answered differently: {ctrl['repeat_answered_differently']} of {ctrl['repeat_pairs']}",
          f"- sides picked: {ctrl['left_picks']} left, {ctrl['right_picks']} right (a lopsided count "
          "is a side habit)"]
    return "\n".join(L) + "\n"


def merge_inputs(existing: dict, new: dict) -> dict:
    """The sitting appended to a density-flow inputs file (the 76 measured
    pairs), so the pooled instrument can be re-run at the larger n."""
    out = json.loads(json.dumps(existing))
    for sid, sitting in new["sittings"].items():
        if sid in out["sittings"]:
            raise SpecError(f"sitting {sid!r} is already in the pooled inputs")
        out["sittings"][sid] = sitting
    return out


def analyse(spec_path: Path, out: Path, *, markdown_to: Path | None = None,
            inputs_to: Path | None = None, append_to: Path | None = None) -> dict:
    spec = load_spec(spec_path)
    validate_spec(spec)
    out = Path(out)
    sealed, picks = require_complete(out)
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    inputs = labelled_inputs(spec, man, sealed, picks, _load_designs(out))
    rep = confirmatory(inputs, spec)
    ctrl = controls_report(sealed, picks)
    text = markdown(rep, ctrl, man)
    (out / "analysis.json").write_text(json.dumps({"report": rep, "controls": ctrl}, indent=1),
                                       encoding="utf-8")
    if markdown_to:
        Path(markdown_to).write_text(text, encoding="utf-8")
    if inputs_to:
        Path(inputs_to).write_text(json.dumps(inputs, indent=1), encoding="utf-8")
    if append_to:
        merged = merge_inputs(json.loads(Path(append_to).read_text(encoding="utf-8")), inputs)
        Path(append_to).with_name("density-flow-inputs-with-wok42.json").write_text(
            json.dumps(merged, indent=1), encoding="utf-8")
    print(text)
    return {"report": rep, "controls": ctrl}


# ------------------------------------------------------------------ cli ----

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["check", "prepare", "analyse"])
    ap.add_argument("spec", type=Path, nargs="?", default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--manifest", type=Path, help="also write the public manifest here")
    ap.add_argument("--link-photo-prep", type=Path,
                    help="primary checkout whose rembg venv is linked into this worktree")
    ap.add_argument("--markdown", type=Path)
    ap.add_argument("--inputs", type=Path, help="write the labelled pairs in density-flow format")
    ap.add_argument("--append-to", type=Path,
                    help="a density-flow inputs file; writes it merged beside itself")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        spec = load_spec(args.spec)
        validate_spec(spec)
        print(f"{spec['sitting']}: spec ok, {len(spec['logos'])} logos, {len(spec['arms'])} arms "
              f"({', '.join(spec['arms'])}), {len(spec['reserve_arms'])} reserves")
        return 0
    if not args.out:
        ap.error("--out is required")
    if args.cmd == "prepare":
        man = prepare(args.spec, args.out, workers=args.workers, manifest_to=args.manifest,
                      link_photo_prep=args.link_photo_prep)
        p = man["pairs"]
        print(f"{p['total']} pairs ({p['live']} live, {p['identical']} identical, {p['repeat']} repeat); "
              f"sealed {man['sealed_sha256'][:12]}; arms {', '.join(man['arms'])}; "
              f"replacements: {len(man['replacements'])}")
        return 0
    analyse(args.spec, args.out, markdown_to=args.markdown, inputs_to=args.inputs,
            append_to=args.append_to)
    return 0


if __name__ == "__main__":
    sys.exit(main())
