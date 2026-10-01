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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SHUFFLE_SEED = 20260917
N_IDENTICAL = 8
N_REPEAT = 8

BASE = "base"
# Fixtures the page never shows. Kent, on the evening sitting of 2026-09-30:
# "dont use this image to judge", and again on the texture sitting that
# night: "please stop using this shitty logo" -- screenshot is a photo of a
# screen, not artwork a customer would send, and three sittings of verdicts on
# it were all "both bad" or "disregard". It stays in `REAL_ART` for the
# instruments (the corpus tables still count it); the render and the labelled
# page skip it.
EXCLUDED_FIXTURES = frozenset({"screenshot"})
REF_ARM = "ref_0827"
# `main` on 2026-08-27, the engine Kent's fourteen notes and his "60%" describe.
REF_COMMIT = "25da2fe"
# `main` on the morning of 2026-09-30 (the merge of #574): the envelope as it
# shipped that morning, before the day's three lettering changes -- the
# sibling rule (#577), the split comb (#578) and the minimum stretch length
# (#579). The evening sitting judges today against it.
REF_0930AM = "ref_0930am"
REF_0930AM_COMMIT = "1e5f8fe2"

# One change per arm, on top of the shipped Studio config. A ref arm carries
# `__ref__` instead of PipelineConfig kwargs. Adding a sitting is adding a row.
ARMS: dict[str, dict] = {
    "per_stroke": {"satin_per_stroke": True},
    "patch_junctions": {"satin_patch_junctions": "satin"},
    "polygon_axis": {"satin_polygon_axis": "artwork"},
    "area_weighted": {"classify_area_weighted": True},
    "design_angle": {"design_angle": True},
    # The 2026-09-18 labelled before/after page carried this arm; it stays so
    # the same six flags Kent already has in front of him keep their column.
    "rails_follow_edge": {"satin_rails_follow_edge": True},
    # `rail_envelope` shipped ON 2026-09-30 (Kent, on its own labelled sitting:
    # 2 after, 0 before), so `"envelope"` is the base now and no longer an arm;
    # `rails_follow_edge` stays, True against it.
    # `rail_comp` shipped ON 2026-09-28 (Kent, on the labelled sitting), so it
    # is the base now and no longer an arm.
    "wide_columns": {"wide_columns": True},
    "lettering_column": {"lettering_min_column_mm": 1.0},
    "phantom_dissolve": {"dissolve_phantom_blends": True},
    "directional_comp": {"directional_comp": True},
    REF_ARM: {"__ref__": REF_COMMIT},
    REF_0930AM: {"__ref__": REF_0930AM_COMMIT},
    # The lettering texture sitting (2026-09-30, late): the two levers Kent's
    # becker note points at -- "the lettering does not flow, satin stitching
    # is not smooth and structured pattern", the third time that day. The
    # pro's own Becker style (raw crosses to about 7 mm, no comb) and the
    # symmetric rails (the envelope OFF).
    "split_7mm": {"split_satin_above_mm": 7.0},
    "rails_symmetric": {"satin_rails_follow_edge": False},
    # The pro's own file beside ours (2026-10-01, Kent's pick after the
    # texture sitting left his becker note unanswered). A `__file__` arm
    # names one stitch file per fixture, relative to `digitizer/`; a fixture
    # without one gets no row. Becker's hat file is 101.9 mm wide against
    # our 100 mm fixture, the closest of the five professional files; a PES
    # rather than the DST beside it because the PES carries the thread list.
    "pro_file": {"__file__": {
        "becker": "testdata/reference/becker_hat_polo_large_beckers_logo_hat.pes",
    }},
    # The back-stitching sitting (2026-10-01, from Kent's verdict on the pro
    # pair: the pro's flows, and his words were the back stitching under the
    # lettering). What `tools/underlay_cover.py` measured against his words:
    # the scatter of holes inside MARINE's stems is the comb split -- every
    # stem is 5.5-6.9 mm wide, over the 5.0 mm split threshold, and the
    # split off takes the stems' interior top holes from 1,413 to 246
    # against the pro's 304. (The stems' own back stitching is already
    # there: a centre run and a ladder zigzag under every one; the pro's
    # crosshatch is denser, not different in kind.)
    "split_off": {"split_satin": False},
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

    # A repeat names its original by KEY — a fixture has one live pair per
    # arm — and the key becomes a pair id only once ids exist. It used to
    # hold the original's dict (`"of": orig`) and read `["pair"]` off it
    # later, which worked only because ids were written onto those same
    # objects in place: copy the entries anywhere in between and it was a
    # KeyError (review 2026-09-17). Same draws from `rng`, same output.
    def key(e: dict) -> tuple[str, str]:
        return (e["fixture"], e["arm"])

    for orig in rng.sample(live, min(n_repeat, len(live))):
        at = next(i for i, e in enumerate(order)
                  if e["kind"] == "live" and key(e) == key(orig))
        slots = [i for i in range(len(order) + 1) if i not in (at, at + 1)]
        if not slots:
            continue
        shown = order[at]          # the entry that carries `flip`, found by key
        order.insert(rng.choice(slots),
                     {"fixture": shown["fixture"], "arm": shown["arm"],
                      "kind": "repeat", "flip": not shown["flip"],
                      "design_only": shown["design_only"]})

    ids = [f"P{n:03d}" for n in range(1, len(order) + 1)]
    live_id = {key(e): pid for pid, e in zip(ids, order) if e["kind"] == "live"}

    public: list[dict] = []
    sealed: dict[str, dict] = {}
    for pid, entry in zip(ids, order):
        left, right = ((entry["arm"], BASE) if entry["flip"]
                       else (BASE, entry["arm"]))
        public.append({"pair": pid, "left": f"{pid}_L.jpg",
                       "right": f"{pid}_R.jpg", "art": f"{pid}_art.png"})
        sealed[pid] = {
            "fixture": entry["fixture"], "left_arm": left, "right_arm": right,
            "kind": entry["kind"],
            "repeat_of": live_id[key(entry)] if entry["kind"] == "repeat" else None,
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


def now_iso() -> str:
    """ISO 8601 local time WITH its UTC offset, to the second. A naive stamp
    cannot be ordered against a commit, a CI log, or a pick made on the far
    side of a DST change — and picks.jsonl is the one file here that cannot
    be regenerated (review 2026-09-17)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_pick(path: str | Path, pair: str, choice: str | None, ms: int,
                undo_of: str | None = None, ts: str | None = None) -> None:
    """One line per click, flushed to disk before returning. Never rewrites."""
    if undo_of is None and choice not in CHOICES:
        raise ValueError(f"choice must be one of {CHOICES}, got {choice!r}")
    line = {"pair": pair, "choice": None if undo_of else choice, "ms": int(ms),
            "ts": ts if ts is not None else now_iso(),
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
