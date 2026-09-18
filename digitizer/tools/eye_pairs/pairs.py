"""Pair building and the picks log. Pure: no engine, no network.

The blinding lives here. `build_pairs` returns a PUBLIC list that names
nothing (opaque pair ids and image names) and a SEALED map from pair id to
what was actually shown. Only the public half is ever served to the picker.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path

SHUFFLE_SEED = 20260917
N_IDENTICAL = 8
N_REPEAT = 8

BASE = "base"
REF_ARM = "ref_0827"
# `main` on 2026-08-27, the engine Kent's fourteen notes and his "60%" describe.
REF_COMMIT = "25da2fe"

# One change per arm, on top of the shipped Studio config. A ref arm carries
# `__ref__` instead of PipelineConfig kwargs. Adding a sitting is adding a row.
ARMS: dict[str, dict] = {
    "per_stroke": {"satin_per_stroke": True},
    "patch_junctions": {"satin_patch_junctions": "satin"},
    "polygon_axis": {"satin_polygon_axis": "artwork"},
    "area_weighted": {"classify_area_weighted": True},
    "design_angle": {"design_angle": True},
    "rail_comp": {"satin_rail_comp": True},
    "wide_columns": {"wide_columns": True},
    "lettering_column": {"lettering_min_column_mm": 1.0},
    "phantom_dissolve": {"dissolve_phantom_blends": True},
    "directional_comp": {"directional_comp": True},
    REF_ARM: {"__ref__": REF_COMMIT},
}


@dataclass(frozen=True)
class ArmRun:
    fixture: str
    arm: str
    design_hash: str
    # True for an arm that produced only a Design dict (an older engine run
    # out of process), so it carries the design-only metrics and nothing
    # else. STORED on the sealed map, never inferred from the arm's name:
    # the analysis used to pick the ref bucket by the literal `REF_ARM`,
    # and a second `__ref__` row would have been pooled into the flag
    # statistics with real values (review finding 6, 2026-09-17).
    design_only: bool = False


def design_hash(design: dict) -> str:
    """Identity of what would be SEWN: the stitch records and nothing else."""
    blob = json.dumps(design["stitches"], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_pairs(runs: list[ArmRun], seed: int = SHUFFLE_SEED,
                n_identical: int = N_IDENTICAL, n_repeat: int = N_REPEAT,
                ) -> tuple[list[dict], dict[str, dict], list[dict]]:
    """-> (public pairs in show order, sealed map, skipped arms)."""
    rng = random.Random(seed)
    by_fx: dict[str, dict[str, ArmRun]] = {}
    for r in runs:
        by_fx.setdefault(r.fixture, {})[r.arm] = r

    live: list[dict] = []
    skipped: list[dict] = []
    for fx in sorted(by_fx):
        base = by_fx[fx].get(BASE)
        if base is None:
            continue
        for arm in sorted(a for a in by_fx[fx] if a != BASE):
            if by_fx[fx][arm].design_hash == base.design_hash:
                skipped.append({"fixture": fx, "arm": arm,
                                "reason": "identical_to_base"})
            else:
                live.append({"fixture": fx, "arm": arm, "kind": "live",
                             "design_only": by_fx[fx][arm].design_only})

    with_base = sorted(fx for fx in by_fx if BASE in by_fx[fx])
    rng.shuffle(with_base)
    identical = [{"fixture": fx, "arm": BASE, "kind": "identical", "design_only": False}
                 for fx in with_base[:n_identical]]

    order = live + identical
    rng.shuffle(order)
    # Exactly half the pairs put the base on the left: a coin per pair can
    # land 40/60 at this n, and a side habit would then read as a preference.
    flips = [i % 2 == 0 for i in range(len(order))]
    rng.shuffle(flips)
    for entry, flip in zip(order, flips):
        entry["flip"] = flip

    for orig in rng.sample(live, min(n_repeat, len(live))):
        at = next(i for i, e in enumerate(order) if e is orig)
        slots = [i for i in range(len(order) + 1) if i not in (at, at + 1)]
        if not slots:
            continue
        order.insert(rng.choice(slots),
                     {"fixture": orig["fixture"], "arm": orig["arm"],
                      "kind": "repeat", "flip": not orig["flip"], "of": orig,
                      "design_only": orig["design_only"]})

    for n, entry in enumerate(order, start=1):
        entry["pair"] = f"P{n:03d}"

    public: list[dict] = []
    sealed: dict[str, dict] = {}
    for entry in order:
        pid = entry["pair"]
        left, right = ((entry["arm"], BASE) if entry["flip"]
                       else (BASE, entry["arm"]))
        public.append({"pair": pid, "left": f"{pid}_L.jpg",
                       "right": f"{pid}_R.jpg", "art": f"{pid}_art.png"})
        sealed[pid] = {
            "fixture": entry["fixture"], "left_arm": left, "right_arm": right,
            "kind": entry["kind"],
            "repeat_of": entry["of"]["pair"] if entry["kind"] == "repeat" else None,
            "design_only": entry["design_only"],
        }
    return public, sealed, skipped


def sealed_hash(sealed: dict[str, dict]) -> str:
    """The identity of a SITTING: what each pair id actually shows. The
    public list cannot carry this (it names nothing, by design), so a guard
    that compared public lists could not see an arm swap at equal count —
    review finding 2, 2026-09-17, shown empirically."""
    blob = json.dumps(sealed, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---- the picks log ---------------------------------------------------------

CHOICES = ("L", "R", "tie")


def append_pick(path: str | Path, pair: str, choice: str | None, ms: int,
                undo_of: str | None = None, ts: str | None = None) -> None:
    """One line per click, flushed to disk before returning. Never rewrites."""
    if undo_of is None and choice not in CHOICES:
        raise ValueError(f"choice must be one of {CHOICES}, got {choice!r}")
    line = {"pair": pair, "choice": None if undo_of else choice, "ms": int(ms),
            "ts": ts if ts is not None else time.strftime("%Y-%m-%dT%H:%M:%S"),
            "undo_of": undo_of}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def load_picks(path: str | Path) -> dict[str, dict]:
    """pair id -> its FINAL pick, in CLICK order. An undo line removes the
    pair again; a re-pick moves it to the end (pop first — re-assigning an
    existing key would keep its old position), so the picker's Undo after a
    reload takes back the pair judged last."""
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
            picks.pop(row["pair"], None)
            picks[row["pair"]] = row
    return picks


def unpicked(pair_ids: list[str], picks: dict[str, dict]) -> list[str]:
    return [p for p in pair_ids if p not in picks]
