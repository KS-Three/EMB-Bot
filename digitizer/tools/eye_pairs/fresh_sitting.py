"""A fresh BLINDED eye-pairs sitting from a manifest (MASTER_SCOPE "Waiting on Kent" 42).

    python -m tools.eye_pairs.fresh_sitting check      --manifest M
    python -m tools.eye_pairs.fresh_sitting build      --manifest M --out DIR
    python -m tools.eye_pairs.fresh_sitting pitch-gate --manifest M --out DIR
    python -m tools.eye_pairs --serve  --out DIR           # Kent judges
    python -m tools.eye_pairs.fresh_sitting score      --out DIR

Pre-registration: docs/fresh-sitting-prereg-2026-10-12.md. This module is the
same thing as code: the six arms and their cfg knobs, the five pre-registered
instrument directions, and the analysis that will be run, all written before a
single pick exists. It adds NO new machinery: `build` is `eye_pairs --render`
then `--pair` (the sealed map, opaque ids, exactly half the pairs with the
shipped side on the left, the identical and repeat controls), driven from a
manifest instead of from the nine spent `REAL_ART` logos, with the seed
named in the manifest; `score` is `pooled.py`'s kappa and bootstrap and
`density_flow.py`'s candidates, read off the stored designs of the pairs
Kent judged.

What this module guards, on top of the existing sitting:

* Kent's own art stays local. A logo must live in a folder git ignores (the
  default is `digitizer/eye_pairs_local/`), or `build` refuses: no new client
  artwork reaches the public repo (ROADMAP / CLAUDE.md).
* Blinding is not spent twice. A logo byte-identical to one of the nine
  `REAL_ART` files is refused, unless the manifest says `"dry_run": true`, in
  which case every artefact is stamped NOT BLINDED.
* The judge sees opaque pair ids and pictures. Arm names, logo names and the
  seed live in `KEY.json` (and `arms.json`/`features.json`, which the picker
  never serves); `build` prints counts and nothing that names an arm.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import functools
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from tools.eye_pairs import density_flow as df
from tools.eye_pairs import pooled
from tools.eye_pairs.pairs import (ARMS, BASE, EXCLUDED_FIXTURES, N_IDENTICAL, N_REPEAT,
                                   load_picks, now_iso, unpicked)

DIGITIZER = Path(__file__).resolve().parents[2]
REPO = DIGITIZER.parent
KEY_NAME = "KEY.json"
DRY_MARKER = "NOT_BLINDED_DRY_RUN.txt"
DEFAULT_LOGOS_DIR = DIGITIZER / "eye_pairs_local"

# --------------------------------------------------------------- the arms ---
# The six arms of the pre-registration, each the exact PipelineConfig kwargs
# the existing sitting machinery lays on top of the shipped Studio config.
# Pinned against `pairs.ARMS` by test, so an edit there cannot move an arm
# under a pre-registration.
FRESH_ARMS: dict[str, dict] = {
    "design_angle": {"design_angle": True},
    "per_stroke": {"satin_per_stroke": True},
    "lettering_columns": {"lettering_columns": True},
    "columns_words": {"lettering_columns": True, "lettering_words": True},
    # NO KNOB OF ITS OWN. The "equal-pitch Column redraw" the instrument doc
    # asks for is `lettering_columns` once the rail pitch is equal, and it has
    # been equal on `main` since 1782fbea (2026-10-07: 0.40-0.46 mm against
    # the satin tier's 0.42-0.52). So this arm is an ALIAS: the same designs
    # as `lettering_columns`, presented under a second pair id. It is a
    # test-retest of the Column lane, not a sixth construction, and it is OFF
    # unless the manifest names it. The real separation of density from
    # construction is `pitch_gate`, below.
    "equal_pitch_columns": {"lettering_columns": True},
    "split_7mm": {"split_satin_above_mm": 7.0},
}
ALIASES: dict[str, str] = {"equal_pitch_columns": "lettering_columns"}
COLUMN_FAMILY = ("lettering_columns", "columns_words", "equal_pitch_columns")
DEFAULT_ARMS = ("design_angle", "per_stroke", "lettering_columns", "columns_words",
                "split_7mm")

# ------------------------------------------------- the pre-registered reads ---
# Direction of "better" per instrument, written BEFORE any pick exists. The
# five PRIMARY ones are the only readings the sitting can confirm; everything
# else is descriptive. `long_share` is LOWER: the reverse of
# `density_flow.CANDIDATES` (which keeps the hypothesis as first written) and
# the direction the 76-pair table suggested (-0.19 [-0.32, -0.06] with ties in).
PRIMARY_DIRECTIONS: dict[str, str] = {
    "flow_circvar": "lower",
    "longest_jump_mm": "lower",
    "long_share": "lower",
    "trims_per_1000": "lower",
    "thread_density": "higher",
}
# Share of logos each arm CHANGED (its design differed from shipped), counted
# over the 7 in-scope corpus logos in `docs/eye-pairs-2026-10-11/pooled-inputs.json`
# (becker, bridge, drone, enthusiast, fremont, golden_tee, tires): an arm that
# changes nothing on a logo is dropped as identical, so a pair budget is
# n_logos x the sum of these, not n_logos x arms. A planning figure, not a law:
# a different set of logos moves it, and `KEY.json` records the real count.
CHANGE_RATE: dict[str, float] = {
    "design_angle": 7 / 7, "per_stroke": 3 / 7, "lettering_columns": 6 / 7,
    "columns_words": 6 / 7, "split_7mm": 4 / 7,
}
DECIDED_SHARE = 0.43            # share of pairs on which Kent chose a side, 10-12 pool (49 of 115)
RESTATES_TRIMS_KAPPA = 0.5     # a candidate whose picks agree with the trim picks this well IS the trims
PITCH_TOL_MM = 0.15             # outer-rail median pitch, Column arm vs shipped (comparability, not cloth)
MIN_LOGOS = 8
BUDGET = (48, 60)               # live pairs, the instrument doc's range
MIN_DECIDED_EXIT = 20           # pairs where Kent chose a side AND the candidate did

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,23}$")
_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,39}$")


def directions() -> dict[str, tuple[str, str]]:
    """`pooled.INSTRUMENTS` + `density_flow.CANDIDATES`, with the primaries'
    pre-registered directions laid over them."""
    out = dict(df.directions())
    for m, d in PRIMARY_DIRECTIONS.items():
        out[m] = (d, out[m][1])
    return out


# --------------------------------------------------------------- manifest ---

@dataclasses.dataclass(frozen=True)
class Logo:
    name: str
    path: Path
    width_mm: float
    garment: str


@dataclasses.dataclass(frozen=True)
class Manifest:
    path: Path
    tag: str
    seed: int
    arms: tuple[str, ...]
    logos: tuple[Logo, ...]
    n_identical: int
    n_repeat: int
    dry_run: bool


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_manifest(path) -> Manifest:
    """Parse and shape-check a manifest; REFUSES (SystemExit) on the first
    problem. Paths resolve against the manifest's own folder."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"REFUSED: manifest {path} is missing")
    raw = json.loads(path.read_text(encoding="utf-8"))
    base = path.resolve().parent
    tag = raw.get("tag")
    if not isinstance(tag, str) or not _TAG.match(tag):
        raise SystemExit(f"REFUSED: manifest tag {tag!r} must be letters, digits, '.' or '-'")
    seed = raw.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise SystemExit("REFUSED: manifest `seed` must be an integer (a sitting is "
                         "reproducible from it; it is not drawn at build time)")
    arms = tuple(raw.get("arms") or DEFAULT_ARMS)
    unknown = [a for a in arms if a not in FRESH_ARMS]
    if unknown or len(set(arms)) != len(arms):
        raise SystemExit(f"REFUSED: arms must be distinct names from {sorted(FRESH_ARMS)}; "
                         f"got {list(arms)}")
    for alias, target in ALIASES.items():
        if alias in arms and target not in arms:
            raise SystemExit(f"REFUSED: arm {alias!r} re-presents {target!r}'s designs, "
                             f"so the manifest has to name {target!r} too")
    folder = base / raw.get("logos_dir", "logos")
    logos = []
    names: set[str] = set()
    for row in raw.get("logos") or []:
        name = row.get("name")
        if not isinstance(name, str) or not _NAME.match(name):
            raise SystemExit(f"REFUSED: logo name {name!r} must be a letter then letters, "
                             "digits or '-' (no underscore: file names split on '__')")
        if name in names or name in EXCLUDED_FIXTURES or name in ("base", "art"):
            raise SystemExit(f"REFUSED: logo name {name!r} repeats or is reserved")
        names.add(name)
        file = folder / row["file"] if "file" in row else None
        if file is None or not file.exists():
            raise SystemExit(f"REFUSED: logo {name!r}: file {file} is missing")
        width = row.get("width_mm")
        if isinstance(width, bool) or not isinstance(width, (int, float)) or width <= 0:
            raise SystemExit(f"REFUSED: logo {name!r}: width_mm must be a positive number")
        logos.append(Logo(name, file, float(width), str(row.get("garment") or "left_chest")))
    if not logos:
        raise SystemExit("REFUSED: the manifest names no logos")
    n_ident = raw.get("n_identical", 4)
    n_rep = raw.get("n_repeat", 6)
    for label, v in (("n_identical", n_ident), ("n_repeat", n_rep)):
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise SystemExit(f"REFUSED: {label} must be a non-negative integer")
    return Manifest(path, tag, seed, arms, tuple(logos), n_ident, n_rep,
                    bool(raw.get("dry_run", False)))


def expected_pairs(m: Manifest) -> dict:
    """Planning arithmetic for `check`: pooled (scorable) pairs expected from
    this manifest at the measured change rates, and how many of them Kent is
    expected to decide. The retest alias adds pairs but they are not pooled."""
    pooled_n = len(m.logos) * sum(CHANGE_RATE[a] for a in m.arms if a in CHANGE_RATE)
    return {"pooled": round(pooled_n, 1), "decided": round(DECIDED_SHARE * pooled_n, 1),
            "logos_for_budget": math.ceil(BUDGET[0] / sum(
                CHANGE_RATE[a] for a in m.arms if a in CHANGE_RATE))}


def spent_hashes() -> dict[str, str]:
    """sha256 -> corpus name, for the nine `REAL_ART` logos: blinding is spent
    on them (second-sitting-eleven-flags-2026-09-28; the instrument doc)."""
    from tools.thin_strokes import REAL_ART

    out = {}
    for name, (rel, _w, _g) in REAL_ART.items():
        p = DIGITIZER / "testdata" / rel
        if p.exists():
            out[sha256(p)] = name
    return out


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


@functools.lru_cache(maxsize=64)
def _in_work_tree(folder: str) -> bool:
    """One git call per folder, not per logo: a process start is the slow part."""
    r = _git(["rev-parse", "--is-inside-work-tree"], Path(folder))
    return r.returncode == 0 and r.stdout.strip() == "true"


def tracked_or_unignored(path: Path) -> bool | None:
    """True when `path` is inside a git work tree and a `git add -A` could
    publish it (tracked, or not ignored); False when git ignores it; None when
    it is not in a work tree at all (a temp folder, another drive)."""
    path = Path(path).resolve()
    cwd = path.parent
    while not cwd.exists() and cwd != cwd.parent:       # the folder may not exist yet
        cwd = cwd.parent
    if not _in_work_tree(str(cwd)):
        return None
    if _git(["ls-files", "--error-unmatch", str(path)], cwd).returncode == 0:
        return True                                   # already committed
    rc = _git(["check-ignore", "-q", "--no-index", str(path)], cwd).returncode
    return {0: False, 1: True}.get(rc)


def problems(m: Manifest) -> list[str]:
    """Everything wrong with a manifest that is not its shape. Empty = go."""
    out: list[str] = []
    if len(m.logos) < MIN_LOGOS and not m.dry_run:
        out.append(f"{len(m.logos)} logos is under the pre-registered minimum of {MIN_LOGOS}")
    if not m.dry_run:
        spent = spent_hashes()
        for logo in m.logos:
            hit = spent.get(sha256(logo.path))
            if hit:
                out.append(f"logo {logo.name!r} is byte-identical to the corpus logo {hit!r}: "
                           "blinding is spent on it (a dry run may use it; a sitting may not)")
            if tracked_or_unignored(logo.path):
                out.append(f"logo {logo.name!r} ({logo.path}) is not in a git-ignored folder: "
                           "Kent's art must stay local. Use digitizer/eye_pairs_local/ "
                           "or add the folder to .gitignore")
    return out


# ------------------------------------------------------------------- build ---

def _clone_alias(out: Path, logos, alias: str, target: str) -> None:
    """Make `alias` carry exactly `target`'s designs, renders and feature rows:
    a test-retest of one set of stitches, not a second digitize."""
    feats_path = out / "features.json"
    feats = json.loads(feats_path.read_text(encoding="utf-8"))
    for logo in logos:
        row = feats.get(logo.name, {}).get(target)
        if not row or "error" in row:
            continue
        feats[logo.name][alias] = copy.deepcopy(row)
        for src, dst in (
                (out / "designs" / f"{logo.name}__{target}.json",
                 out / "designs" / f"{logo.name}__{alias}.json"),
                (out / "renders" / f"{logo.name}__{target}.jpg",
                 out / "renders" / f"{logo.name}__{alias}.jpg"),
                (out / "renders" / f"{logo.name}__{target}__holes.jpg",
                 out / "renders" / f"{logo.name}__{alias}__holes.jpg")):
            if src.exists():
                shutil.copyfile(src, dst)
    feats_path.write_text(json.dumps(feats, indent=1), encoding="utf-8")


def build(manifest_path, out, *, render_fn=None, pair_fn=None, say=print) -> dict:
    """Render every (logo, arm), alias the retest arm, build the sealed
    sitting under the manifest's seed, write `KEY.json`. -> the key dict.

    `render_fn` / `pair_fn` default to `tools.eye_pairs`' own `render` / `pair`
    (imported late: they pull cv2 and the engine); a test passes fakes."""
    m = load_manifest(manifest_path)
    bad = problems(m)
    if bad:
        raise SystemExit("REFUSED:\n  " + "\n  ".join(bad))
    out = Path(out)
    picks = out / "picks.jsonl"
    if picks.exists() and picks.stat().st_size:
        raise SystemExit(f"REFUSED: {picks} holds picks; a sitting that has been judged is "
                         "never rebuilt in place. Use a fresh --out.")
    if render_fn is None or pair_fn is None:
        from tools.eye_pairs import __main__ as cli

        render_fn = render_fn or cli.render
        pair_fn = pair_fn or cli.pair
    out.mkdir(parents=True, exist_ok=True)
    canonical = [a for a in m.arms if a not in ALIASES]
    cases = [(lg.name, lg.path, lg.width_mm, lg.garment) for lg in m.logos]
    render_fn(out, cases=cases, arms={a: FRESH_ARMS[a] for a in canonical})
    for alias, target in ALIASES.items():
        if alias in m.arms:
            _clone_alias(out, m.logos, alias, target)
    n_pairs = pair_fn(out, seed=m.seed, n_identical=m.n_identical, n_repeat=m.n_repeat)

    sealed = json.loads((out / "arms.json").read_text(encoding="utf-8"))
    skipped = json.loads((out / "skipped.json").read_text(encoding="utf-8"))
    live = sum(1 for s in sealed.values() if s["kind"] == "live")
    feats = json.loads((out / "features.json").read_text(encoding="utf-8"))
    # A logo the scorecard refuses on (ink ambiguous, ...) still scores on every
    # primary instrument - they read stitches, not the artwork - but loses the
    # fidelity rows; the key says which, so the choice of logos can be revisited.
    refused = {lg.name: next(iter(base["refusals"].values()))
               for lg in m.logos
               if (base := feats.get(lg.name, {}).get(BASE) or {}).get("refusals")}
    key = {
        "WARNING": "UNBLINDING KEY. Do not open before the last pick.",
        "dry_run": m.dry_run,
        "tag": m.tag, "seed": m.seed, "built_ts": now_iso(),
        "manifest_sha256": sha256(m.path),
        "prereg": "docs/fresh-sitting-prereg-2026-10-12.md",
        "arms": {a: {"cfg": FRESH_ARMS[a], "alias_of": ALIASES.get(a)} for a in m.arms},
        "logos": {lg.name: {"sha256": sha256(lg.path), "width_mm": lg.width_mm,
                            "garment": lg.garment} for lg in m.logos},
        "controls": {"n_identical": m.n_identical, "n_repeat": m.n_repeat},
        "primary_directions_at_build": dict(PRIMARY_DIRECTIONS),
        "scorecard_refusals": refused,
        "n_pairs": n_pairs, "n_live": live,
        "below_budget": live < BUDGET[0],
        "sealed": sealed, "skipped": skipped,
    }
    (out / KEY_NAME).write_text(json.dumps(key, indent=1), encoding="utf-8")
    if m.dry_run:
        (out / DRY_MARKER).write_text(
            "NOT BLINDED. This directory is a PIPELINE CHECK on logos blinding is already\n"
            "spent on. Nothing in it is evidence about Kent's eye.\n", encoding="utf-8")
    # Counts only: the builder's terminal is not judge-safe if it names an arm.
    say(f"{n_pairs} pairs ({live} live, {n_pairs - live} controls) from {len(m.logos)} logos "
        f"-> {out}")
    if live < BUDGET[0]:
        say(f"WARNING: {live} live pairs is under the pre-registered {BUDGET[0]}-{BUDGET[1]}; "
            "see KEY.json for which arm-logo cells were identical to shipped")
    if m.dry_run:
        say("DRY RUN: NOT BLINDED - pipeline check only")
    return key


# ------------------------------------------------------------- pitch gate ---

def pitch_gate(manifest_path, out, *, measure=None, say=print) -> dict:
    """Per logo and Column-family arm: the outer-rail median pitch of the
    shipped satin tier against the arm's (`tools/satin_pitch.py`, 2026-10-07:
    "a pair whose two sides sew at different pitch cannot be judged on
    construction"). A pair whose gap exceeds `PITCH_TOL_MM` is a DENSITY pair
    and `score` leaves it out of the construction readings. Stored in
    `KEY.json` under `pitch_gate`."""
    m = load_manifest(manifest_path)
    out = Path(out)
    key_path = out / KEY_NAME
    key = json.loads(key_path.read_text(encoding="utf-8"))
    if measure is None:
        from tools import satin_pitch

        measure = satin_pitch.measure
    gate: dict = {"tolerance_mm": PITCH_TOL_MM, "logos": {}}
    for lg in m.logos:
        shipped = None
        for arm in (a for a in m.arms if a in COLUMN_FAMILY):
            if shipped is None:
                shipped = measure(lg.name, lg.path, lg.width_mm, lg.garment, {})
            row = measure(lg.name, lg.path, lg.width_mm, lg.garment, FRESH_ARMS[arm])
            s, a = shipped.get("outer_p50"), row.get("outer_p50")
            entry = {"shipped_outer_p50": s, "arm_outer_p50": a}
            if s is None or a is None:
                entry.update(delta_mm=None, ok=None,
                             why="no text-tagged satin run on one side: no lettering to compare")
            else:
                entry.update(delta_mm=round(abs(a - s), 3), ok=abs(a - s) <= PITCH_TOL_MM)
            gate["logos"].setdefault(lg.name, {})[arm] = entry
    key["pitch_gate"] = gate
    key_path.write_text(json.dumps(key, indent=1), encoding="utf-8")
    failed = sum(1 for lg in gate["logos"].values() for e in lg.values() if e["ok"] is False)
    say(f"pitch gate: {failed} logo-arm cell(s) over {PITCH_TOL_MM} mm (see KEY.json)")
    return gate


# ----------------------------------------------------------------- scoring ---
# Everything below is pure given the sitting directory: it reads the stored
# designs of the pairs Kent judged and never re-digitizes (a re-digitize scores
# today's engine, not the one he looked at - density_flow's first rule).

def _load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def kent_label(choice: str | None, left_arm: str, right_arm: str) -> str | None:
    """The picker's L / R / tie in the pool's frame: `before` = the shipped
    side, `after` = the arm's. The blind picker has no `both_bad`; a tie is
    `same` (Kent's "can't tell") and nothing else."""
    if choice is None:
        return None
    if choice == "tie":
        return "same"
    picked = left_arm if choice == "L" else right_arm
    return "before" if picked == BASE else "after"


def sitting_inputs(out, *, include_retest: bool = False) -> dict:
    """A finished sitting directory -> `pooled`-shaped inputs: one `live` pair
    per row, with the pooled instruments (from `features.json`) and every
    `density_flow` candidate (from the stored designs) on both sides.
    Controls (`identical`, `repeat`) are not pooled; see `controls_report`.
    A pair the pitch gate failed, or the retest alias, is `scorable: false`."""
    from tools.eye_pairs_price import changed_shapes, records, scoped
    from tools.eye_pairs.pooled_build import _feature_values

    out = Path(out)
    key = _load(out / KEY_NAME)
    sealed = _load(out / "arms.json")
    feats = _load(out / "features.json")
    picks = load_picks(out / "picks.jsonl")
    gate = (key.get("pitch_gate") or {}).get("logos", {})
    tag = key["tag"]
    pairs = []
    for pid in sorted(sealed):
        s = sealed[pid]
        if s["kind"] != "live":
            continue
        fx = s["fixture"]
        arm = s["right_arm"] if s["left_arm"] == BASE else s["left_arm"]
        pick = picks.get(pid)
        label = kent_label(pick["choice"] if pick else None, s["left_arm"], s["right_arm"])
        db = _load(out / "designs" / f"{fx}__{BASE}.json")
        da = _load(out / "designs" / f"{fx}__{arm}.json")
        ch = changed_shapes(db, da) or None
        vb, rb = _feature_values(feats[fx][BASE], db, None)
        va, ra = _feature_values(feats[fx][arm], da, None)
        vb["changed_trims"], va["changed_trims"] = scoped(db, ch or set())["trims"], \
            scoped(da, ch or set())["trims"]
        for side, d, vals in (("b", db, vb), ("a", da, va)):
            m = df.measure(d, ch, support=True)
            vals.update({k: v for k, v in m.items() if v is not None})
            vals["trims"] = records(d)["trims"]
        p = {"id": f"{tag}:{arm}:{fx}", "pair": pid, "arm": arm, "fixture": fx,
             "label": label, "judged": (pick or {}).get("ts", "")[:10],
             "before": {k: v for k, v in vb.items() if v is not None},
             "after": {k: v for k, v in va.items() if v is not None},
             "refused": {"before": rb, "after": ra},
             "designs": {"changed_shapes": len(ch) if ch else 0}}
        why = None
        if arm in ALIASES and not include_retest:
            why = f"retest of {ALIASES[arm]}: reported as consistency, not pooled"
        elif (gate.get(fx, {}).get(arm) or {}).get("ok") is False:
            why = "pitch gate failed: a density pair, not a construction pair"
        elif ch is None:
            why = "designs identical in every shape"
        if why:
            p["scorable"], p["unscored_why"] = False, why
        pairs.append(p)
    return {"schema": 1, "sittings": {tag: {"date": key["built_ts"][:10], "pairs": pairs}}}


def point_kappas(rows: list[dict], metric: str, dirs: dict) -> dict:
    """Both kappas, no bootstrap: the cheap read the leave-one-logo-out loop
    needs. Same definitions as `pooled.agreement`."""
    scored = []
    for p in rows:
        b, a = p["before"].get(metric), p["after"].get(metric)
        if b is None or a is None or pooled._refused(p, metric):
            continue
        scored.append((p, pooled.instrument_pick(metric, float(b), float(a), directions=dirs)))
    k3 = i3 = None
    if scored:
        kent3 = np.array([pooled.SIDES.index(p["kent"]) for p, _ in scored], dtype=int)
        inst3 = np.array([pooled.SIDES.index(i) for _, i in scored], dtype=int)
        k3 = pooled.kappa_from_table(pooled._table(kent3, inst3, 3), "linear")
    dec = [(p, i) for p, i in scored if p["kent"] != "tie" and i != "tie"]
    k2 = None
    if dec:
        ka = np.array([0 if p["kent"] == "before" else 1 for p, _ in dec], dtype=int)
        ia = np.array([0 if i == "before" else 1 for _, i in dec], dtype=int)
        k2 = pooled.kappa_from_table(pooled._table(ka, ia, 2))
    return {"n_scored": len(scored), "n_decided": len(dec), "kappa_3way": k3, "kappa_decided": k2}


def leave_one_logo_out(rows: list[dict], metric: str, dirs: dict) -> dict:
    """Point kappa with each logo dropped. `n_nonpositive` counts the drops
    that leave the sides-only kappa at or below zero: a reading one logo
    carries is not a finding (pre-registered: at most one may)."""
    logos = sorted({p["fixture"] for p in rows})
    drops = {}
    for lg in logos:
        r = point_kappas([p for p in rows if p["fixture"] != lg], metric, dirs)
        drops[lg] = r["kappa_decided"]
    bad = [lg for lg, k in drops.items() if k is None or k <= 0]
    return {"drops": drops, "n_nonpositive": len(bad), "nonpositive": bad}


def verdict(r: dict, loo: dict, restates: dict | None, metric: str) -> str:
    """The pre-registered reading of ONE primary instrument. Order matters:
    the first line that applies is the answer."""
    rd2 = pooled.reading(r["n_decided"], (r["ci2_lo"], r["ci2_hi"]), r["ci2_cluster"])
    rd3 = pooled.reading(r["n_scored"], (r["ci3_lo"], r["ci3_hi"]), r["ci3_cluster"])
    if rd2.startswith("n too small") or rd3.startswith("n too small"):
        return "n too small to read"
    if rd2 == "below chance" or rd3 == "below chance":
        return "REVERSED: below chance against the stated direction"
    if not (rd2 == "above chance" and rd3 == "above chance"):
        return "no evidence either way"
    if loo["n_nonpositive"] > 1:
        return "above chance but carried by one or two logos"
    if metric == "trims_per_1000":
        return "above chance: the trim count, a price column (known since #842)"
    if restates and restates["kappa"] is not None and restates["kappa"] >= RESTATES_TRIMS_KAPPA:
        return "above chance but restates the trims"
    return "CONFIRMED: above chance on both statistics, both intervals, not the trims"


def vs_trims(rows: list[dict], metric: str, dirs: dict) -> dict:
    """Kappa between `metric`'s picks and `trims_per_1000`'s over pairs where
    both chose a side (no label in it): does the candidate restate the trims?
    `density_flow.instrument_vs_instrument` with THIS sitting's directions."""
    a, b = [], []
    for p in rows:
        v = [p["before"].get(metric), p["after"].get(metric),
             p["before"].get("trims_per_1000"), p["after"].get("trims_per_1000")]
        if None in v:
            continue
        p1 = pooled.instrument_pick(metric, float(v[0]), float(v[1]), directions=dirs)
        p2 = pooled.instrument_pick("trims_per_1000", float(v[2]), float(v[3]), directions=dirs)
        if "tie" in (p1, p2):
            continue
        a.append(0 if p1 == "before" else 1)
        b.append(0 if p2 == "before" else 1)
    if not a:
        return {"n": 0, "kappa": None}
    return {"n": len(a), "kappa": pooled.kappa_from_table(pooled._table(np.array(a), np.array(b), 2))}


def controls_report(out) -> dict:
    """The sitting's own controls, reported as COUNTS: Kent against himself on
    repeated pairs, his answer to the identical pairs, and the retest arm."""
    from tools.eye_pairs import analysis as an

    out = Path(out)
    sealed = _load(out / "arms.json")
    picks = load_picks(out / "picks.jsonl")
    rep = {"ceiling": an.ceiling(sealed, picks), "controls": an.controls(sealed, picks)}
    by_arm: dict[tuple[str, str], str | None] = {}
    for pid, s in sealed.items():
        if s["kind"] != "live":
            continue
        arm = s["right_arm"] if s["left_arm"] == BASE else s["left_arm"]
        by_arm[(s["fixture"], arm)] = kent_label(
            (picks.get(pid) or {}).get("choice"), s["left_arm"], s["right_arm"])
    retest = []
    for alias, target in ALIASES.items():
        for (fx, arm), lab in sorted(by_arm.items()):
            if arm == alias and (fx, target) in by_arm:
                retest.append({"fixture": fx, "arm": alias,
                               "same_answer": lab == by_arm[(fx, target)]})
    rep["retest"] = {"n": len(retest), "same_answer": sum(r["same_answer"] for r in retest)}
    return rep


def arm_manipulation(rows: list[dict], metrics=tuple(PRIMARY_DIRECTIONS)) -> dict:
    """Descriptive, before any kappa: per arm, on how many pairs each primary
    instrument moved to its better side, its worse side, or not at all. This is
    the check that the arm moved what it was chosen to move."""
    out: dict = {}
    dirs = directions()
    for p in rows:
        for m in metrics:
            b, a = p["before"].get(m), p["after"].get(m)
            if b is None or a is None:
                continue
            pick = pooled.instrument_pick(m, float(b), float(a), directions=dirs)
            cell = out.setdefault(p["arm"], {}).setdefault(m, {"arm_better": 0, "base_better": 0,
                                                              "no_change": 0})
            cell["no_change" if pick == "tie" else "arm_better" if pick == "after"
                 else "base_better"] += 1
    return out


def analyse(inputs: dict, *, include_candidates: bool = True) -> dict:
    """The pre-registered analysis over `pooled`-shaped inputs."""
    dirs = directions()
    pairs = pooled.pooled_pairs(inputs)                    # validates the label vocabulary
    rows = pooled.select(pairs)
    n_logos = len({p["fixture"] for p in rows})
    res: dict = {"n_judged_live": len(pairs), "n_scored": len(rows), "n_logos": n_logos,
                 "primary": {}, "other": {}, "worse": {}, "manipulation": arm_manipulation(rows)}
    metrics = list(PRIMARY_DIRECTIONS)
    if include_candidates:
        metrics += [m for m in df.CANDIDATES if m not in PRIMARY_DIRECTIONS
                    and m != "density_pro_gap"]
    for m in metrics:
        r = pooled.agreement(rows, m, directions=dirs)
        c = pooled.agreement(rows, m, cluster=True, directions=dirs)
        r["ci2_cluster"], r["ci3_cluster"] = (c["ci2_lo"], c["ci2_hi"]), (c["ci3_lo"], c["ci3_hi"])
        loo = leave_one_logo_out(rows, m, dirs)
        restates = vs_trims(rows, m, dirs) if m != "trims_per_1000" else None
        r["loo"], r["restates_trims"] = loo, restates
        r["worse_pairs"] = pooled.worse_pairs(rows, m, directions=dirs)
        if m in PRIMARY_DIRECTIONS:
            r["direction"] = PRIMARY_DIRECTIONS[m]
            r["verdict"] = verdict(r, loo, restates, m)
            res["primary"][m] = r
        else:
            r["direction"] = dirs[m][0]
            res["other"][m] = r
    res["exit"] = exit_reading(res)
    return res


def exit_reading(res: dict) -> dict:
    """ROADMAP phase-1 exit, restated against the fresh sitting. Evidence for
    the exit needs a CONFIRMED primary that is not the trims; the sitting can
    only ever be evidence, the call is Kent's."""
    confirmed = [m for m, r in res["primary"].items()
                 if r["verdict"].startswith("CONFIRMED")]
    enough = []
    for m in confirmed:
        r = res["primary"][m]
        if r["n_decided"] >= MIN_DECIDED_EXIT and res["n_logos"] >= MIN_LOGOS:
            enough.append(m)
    worse = {m: len(res["primary"][m]["worse_pairs"]) for m in confirmed}
    return {
        "clause_1_agrees": bool(enough),
        "confirmed_primaries": confirmed,
        "with_enough_pairs_and_logos": enough,
        "clause_2_never_worse": bool(enough) and all(worse[m] == 0 for m in enough),
        "worse_pairs_on_confirmed": worse,
        "note": ("Evidence for the phase-1 exit needs clause 1 AND clause 2 on at least one "
                 "confirmed non-trim primary; a trims-only result is not evidence. The "
                 "advance is Kent's call either way."),
    }


def _f(v, nd=2):
    return pooled._f(v, nd)


def report_markdown(res: dict, controls: dict, *, dry_run: bool) -> str:
    head = ["# Fresh sitting - scored"]
    if dry_run:
        head.append("\n**DRY RUN - NOT BLINDED - SYNTHETIC PICKS. A pipeline check, not evidence.**")
    head.append(f"\nlive pairs judged: {res['n_judged_live']}; pooled (scorable): {res['n_scored']}; "
                f"logos: {res['n_logos']}")
    c = controls
    head.append(f"controls: repeats consistent {c['ceiling']['consistent']} of {c['ceiling']['n']}; "
                f"identical pairs answered tie {c['controls']['identical_tie_rate']} of "
                f"{c['controls']['identical_n']}; retest arm same answer "
                f"{c['retest']['same_answer']} of {c['retest']['n']}")
    lines = ["\n## Primary readings (pre-registered directions)\n",
             "| instrument | better is | n scored | n decided | kappa decided | 95% CI pairs | "
             "95% CI logos | kappa ties in | 95% CI pairs | 95% CI logos | logo drops <= 0 | "
             "kappa vs trims (n) | verdict |", "|" + "---|" * 13]
    for m, r in res["primary"].items():
        rt = r["restates_trims"]
        rt_s = "-" if rt is None else (f"{_f(rt['kappa'])} ({rt['n']})" if rt["n"] else "n/a (0)")
        lines.append(
            f"| `{m}` | {r['direction']} | {r['n_scored']} | {r['n_decided']} "
            f"| {_f(r['kappa_decided'])} | {pooled._ci(r['ci2_lo'], r['ci2_hi'])} "
            f"| {pooled._ci(*r['ci2_cluster'])} | {_f(r['kappa_3way'])} "
            f"| {pooled._ci(r['ci3_lo'], r['ci3_hi'])} | {pooled._ci(*r['ci3_cluster'])} "
            f"| {r['loo']['n_nonpositive']} of {len(r['loo']['drops'])} | {rt_s} | {r['verdict']} |")
    if res["other"]:
        lines += ["\n## Other candidates (descriptive; original directions)\n",
                  "| candidate | better is | n scored | n decided | kappa decided | 95% CI pairs | "
                  "kappa ties in | 95% CI pairs |", "|" + "---|" * 8]
        for m, r in res["other"].items():
            lines.append(f"| `{m}` | {r['direction']} | {r['n_scored']} | {r['n_decided']} "
                         f"| {_f(r['kappa_decided'])} | {pooled._ci(r['ci2_lo'], r['ci2_hi'])} "
                         f"| {_f(r['kappa_3way'])} | {pooled._ci(r['ci3_lo'], r['ci3_hi'])} |")
    lines.append("\n## Manipulation check (instrument moves per arm, counts of pairs)\n")
    lines.append("| arm | instrument | arm better | base better | no change |\n|---|---|---|---|---|")
    for arm, by_m in sorted(res["manipulation"].items()):
        for m, cell in by_m.items():
            lines.append(f"| `{arm}` | `{m}` | {cell['arm_better']} | {cell['base_better']} "
                         f"| {cell['no_change']} |")
    ex = res["exit"]
    lines.append(f"\n## Phase-1 exit\n\nclause 1 (agrees): {ex['clause_1_agrees']}; "
                 f"clause 2 (never worse): {ex['clause_2_never_worse']}; confirmed primaries: "
                 f"{ex['confirmed_primaries'] or 'none'}. {ex['note']}")
    return "\n".join(head + lines)


def score(out, *, include_retest: bool = False, say=print) -> dict:
    """Refuses until every pair has a pick (as `--reveal` does: this reads
    arms), then runs the pre-registered analysis and writes `score.json` /
    `score.md` beside the sitting."""
    out = Path(out)
    key = _load(out / KEY_NAME)
    sealed = _load(out / "arms.json")
    picks = load_picks(out / "picks.jsonl")
    missing = unpicked(sorted(sealed), picks)
    if missing:
        raise SystemExit(f"REFUSED: {len(missing)} of {len(sealed)} pairs have no pick "
                         f"(first: {missing[0]}). Every pair is picked before any score is read.")
    inputs = sitting_inputs(out, include_retest=include_retest)
    res = analyse(inputs)
    ctl = controls_report(out)
    res["controls_report"] = ctl
    (out / "score.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    md = report_markdown(res, ctl, dry_run=bool(key.get("dry_run")))
    (out / "score.md").write_text(md, encoding="utf-8")
    say(md)
    return res


# --------------------------------------------------------------------- CLI ---

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["check", "build", "pitch-gate", "score"])
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--include-retest", action="store_true",
                    help="score: pool the retest alias arm as well (default: report only)")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        if not args.manifest:
            ap.error("check needs --manifest")
        m = load_manifest(args.manifest)
        bad = problems(m)
        print(f"{len(m.logos)} logos, arms {list(m.arms)}, seed {m.seed}, "
              f"{'DRY RUN' if m.dry_run else 'blinded sitting'}")
        e = expected_pairs(m)
        print(f"expected: ~{e['pooled']} pooled pairs, ~{e['decided']} decided "
              f"(pre-registered {BUDGET[0]}-{BUDGET[1]}; {BUDGET[0]} needs ~{e['logos_for_budget']} "
              f"logos with these arms)")
        for b in bad:
            print("PROBLEM:", b)
        return 1 if bad else 0
    if args.cmd in ("build", "pitch-gate"):
        if not (args.manifest and args.out):
            ap.error(f"{args.cmd} needs --manifest and --out")
        (build if args.cmd == "build" else pitch_gate)(args.manifest, args.out)
        return 0
    if not args.out:
        ap.error("score needs --out")
    score(args.out, include_retest=args.include_retest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
