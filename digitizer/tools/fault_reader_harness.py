"""Does a fault reader land where Kent pointed? Scored against chance.

    python -m tools.fault_reader_harness pins  --marks MARKS.json [--out PINS.json]
    python -m tools.fault_reader_harness score --marks MARKS.json --flags DIR [--json OUT]

The 2026-11-10 defect-marks sitting (`docs/defect-marks-2026-11-10/`) left 95
pins: where on one render Kent saw a fault, what kind, how bad, and a note. A
"fault reader" is anything that says WHERE a design has a given fault: a list
of flagged locations, each with a strength, in the same mm frame as the pins
(`defect_marks.mark_mm`: from the render's top-left, pad undone, y down).

This module asks one question of a reader and nothing else: of the pins Kent
placed for this fault, how many have a flag within `RADIUS_MM`, and how many
would the SAME flags catch if the pins were placed at random on the stitched
area? A raw hit rate means nothing alone (ROADMAP gate 4): a reader that flags
every edge "hits" every edge pin. So every figure here is printed beside its
chance figure, and pooling is clustered by item, since pins on one design are
not independent.

What is fixed before any result, and why, is
`docs/defect-marks-2026-11-10/edge-reader-preregistration.md`. The constants
below are that page's numbers; changing one after seeing a result is the thing
that page exists to prevent.

Pure helpers (`select_edge_pins`, `hits`, `chance_rate`, `item_score`,
`pool`, `strength_auc`) take plain lists and numpy arrays, so the tests need
no engine. The stitched-area mask is passed in by the caller.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

RADIUS_MM = 3.0                       # the verdict's radius (pre-registered)
SENSITIVITY_MM = (2.0, 5.0)           # reported beside it, never the verdict
CHANCE_DRAWS = 2000
BOOT_DRAWS = 5000
SEED = 20261110
EDGE_BAND_MM = 1.0                    # the harder null: thread within this of fabric

# ------------------------------------------------------------ pin selection ----
# The NOTE decides, the kind is a hint (SITTING.md). Rules 1-4 of the
# pre-registration, in that order.
EDGE_WORDS = ("jag", "smooth", "crisp", "sawtooth", "stair", "wav", "wobbl", "lump", "bump",
              "straight", "flat")
EDGE_KINDS = ("jagged", "wavy", "lumpy_curve")
OTHER_FAULT_WORDS = ("gap", "missing", "colour", "color", "spacing", "read", "stitch")
EDGE_NOUNS = ("edge", "border", "circle", "outline", "curve", "line", "letter")
SAME_AS = re.compile(r"same (issue|for)")


def _has(text: str, words) -> bool:
    return any(w in text for w in words)


def edge_reason(pin: dict) -> str | None:
    """-> which rule makes this pin an edge-smoothness pin, or None. Rule 4
    (bare pins inheriting) needs the item, so it lives in `select_edge_pins`."""
    note = (pin.get("note") or "").lower()
    kind = pin.get("what") or ""
    rule1 = _has(note, EDGE_WORDS)
    rule2 = kind in EDGE_KINDS and not _has(note, OTHER_FAULT_WORDS)
    if rule2:
        return "edge kind"
    if rule1:
        if "stitch" in note and not _has(note, EDGE_NOUNS):
            return None                                    # rule 3: stitch flow, not an edge
        return "edge word"
    return None


def select_edge_pins(marks: dict, prefix: str = "L_") -> list[dict]:
    """Every relevant pin of `marks.json` on items whose id starts with
    `prefix`, with the rule that admitted it. Pin numbers are 1-based in the
    item's own order, as `SITTING.md` prints them."""
    out = []
    for iid, item in (marks.get("items") or {}).items():
        if not iid.startswith(prefix):
            continue
        pins = item.get("pins") or []
        reasons = [edge_reason(p) for p in pins]
        # rule 4: a noted pin that says the bare marks are the same issue
        donor = next((i for i, p in enumerate(pins) if SAME_AS.search((p.get("note") or "").lower())), None)
        for i, p in enumerate(pins):
            why = reasons[i]
            if why is None and donor is not None and not p.get("note") and not p.get("what") \
                    and reasons[donor] is not None:
                why = f"same as pin {donor + 1}"
            if why is not None:
                out.append({"item": iid, "pin": i + 1, "x_mm": p["x_mm"], "y_mm": p["y_mm"],
                            "what": p.get("what"), "severity": p.get("severity"),
                            "note": p.get("note") or "", "rule": why})
    return out


# Second fault: letters that close up, merge or cannot be read. Rules 1-4 of
# `docs/defect-marks-2026-11-10/letter-reader-preregistration.md`, in order.
CLOSE_WORDS = ("spacing", "space between", "merg", "hole", "join", "touch", "intersect",
               "closed up", "filled in")
READ_RE = re.compile(r"\bread|can'?t tell|cannot tell|can not tell")
LETTER_RE = re.compile(r"\"[a-z&]\"|\bletter|\bsymbol")
LETTER_KINDS = ("letter_shape",)


def letter_reason(pin: dict) -> str | None:
    """-> which rule makes this pin a closed/merged/unreadable-letter pin, or
    None. Rule 4 (bare pins inheriting) needs the item: `select_letter_pins`."""
    note = (pin.get("note") or "").lower()
    kind = pin.get("what") or ""
    rule1 = _has(note, CLOSE_WORDS)
    rule2 = bool(READ_RE.search(note)) and (kind in LETTER_KINDS or bool(LETTER_RE.search(note)))
    if edge_reason(pin) is not None:
        # rule 3: a pin the edge rule already claimed is shared only when its
        # own note names a closure as well (Gaulke 3: "white spacing ... jagged")
        return "closure word, also edge" if rule1 else None
    if rule1:
        return "closure word"
    if rule2:
        return "read word on a letter"
    return None


def select_pins(marks: dict, reason, prefix: str = "L_") -> list[dict]:
    """`select_edge_pins` with any reason function (rule 4 included)."""
    out = []
    for iid, item in (marks.get("items") or {}).items():
        if not iid.startswith(prefix):
            continue
        pins = item.get("pins") or []
        reasons = [reason(p) for p in pins]
        donor = next((i for i, p in enumerate(pins) if SAME_AS.search((p.get("note") or "").lower())), None)
        for i, p in enumerate(pins):
            why = reasons[i]
            if why is None and donor is not None and not p.get("note") and not p.get("what") \
                    and reasons[donor] is not None:
                why = f"same as pin {donor + 1}"
            if why is not None:
                out.append({"item": iid, "pin": i + 1, "x_mm": p["x_mm"], "y_mm": p["y_mm"],
                            "what": p.get("what"), "severity": p.get("severity"),
                            "note": p.get("note") or "", "rule": why})
    return out


def select_letter_pins(marks: dict, prefix: str = "L_") -> list[dict]:
    """The letter-fault pins of `marks.json` (the letter pre-registration)."""
    return select_pins(marks, letter_reason, prefix)


# Third fault: the same kind of feature stitched in some places and not in
# others (Kent's "extra in-fill, some empty spaces have it while others
# don't"). Rules 1-5 of `docs/infill-fault-reader-2026-11-11/preregistration.md`.
INFILL_RE = re.compile(r"in-?fill")
CONTRAST_RE = re.compile(
    r"\bsome\b.*\b(while|others?)\b"            # "some ... have it while others don't"
    r"|\bonly\b"                                 # "the only lettering in-fill"
    r"|\b(doesn'?t|don'?t|does not|do not) match"
    r"|\bdiffere?n?t from\b"                     # "look different from eachother"
    r"|\binconsist[ae]nt from\b"                 # "inconsistant from the right nostrel"
    r"|\b(look|looked|be) the same\b"
    r"|\bselect spots\b")
COLOUR_RE = re.compile(r"colou?r")
PRO_RE = re.compile(r"\bpros?\b")                 # "doesnt match the pros": against the pro, not between places
RANGE_RE = re.compile(r"#?(\d+)\s*[-–]\s*#?(\d+)")


def infill_reason(pin: dict) -> str | None:
    """-> which rule makes this pin an uneven-treatment pin, or None. Rules 4
    (pins another reader claimed) and 5 (shorthand) need the item:
    `select_infill_pins`."""
    note = (pin.get("note") or "").lower()
    if not note or COLOUR_RE.search(note):
        return None                                        # rule 3: a thread-colour fault
    if INFILL_RE.search(note):
        return "in-fill word"                              # rule 2
    if CONTRAST_RE.search(note) and not PRO_RE.search(note):
        return "contrast between places"                   # rule 1
    return None


def note_ranges(note: str, n_pins: int) -> list[int]:
    """Pin numbers a note names by range ("#1-#28", "(#5-#6)", "for 7-8"),
    1-based, clipped to the item's pins, in order, no repeats."""
    out: list[int] = []
    for a, b in RANGE_RE.findall(note or ""):
        lo, hi = sorted((int(a), int(b)))
        out += [k for k in range(max(1, lo), min(hi, n_pins) + 1) if k not in out]
    return out


def select_infill_pins(marks: dict, prefix: str = "L_") -> list[dict]:
    """The uneven-treatment pins of `marks.json`. Each carries `note_pin`, the
    pin whose note admitted it, so 28 pins from one note can be counted as one
    judgement."""
    claimed = {(p["item"], p["pin"]) for p in select_edge_pins(marks, prefix)}
    claimed |= {(p["item"], p["pin"]) for p in select_letter_pins(marks, prefix)}
    out = []
    for iid, item in (marks.get("items") or {}).items():
        if not iid.startswith(prefix):
            continue
        pins = item.get("pins") or []
        why = {i + 1: infill_reason(p) for i, p in enumerate(pins)}
        donor_of = {k: k for k, w in why.items() if w}
        for k in sorted(donor_of):                          # rule 5a: a range in an admitted note
            for j in note_ranges(pins[k - 1].get("note"), len(pins)):
                if j not in donor_of and not pins[j - 1].get("note"):
                    donor_of[j] = k
        same = next((i + 1 for i, p in enumerate(pins) if SAME_AS.search((p.get("note") or "").lower())),
                    None)
        if same is not None and why.get(same):              # rule 5b: same-as, as the edge rule
            for j, p in enumerate(pins, start=1):
                if j not in donor_of and not p.get("note") and not p.get("what"):
                    donor_of[j] = same
        for j in sorted(donor_of):
            if (iid, j) in claimed:
                continue                                    # rule 4: another reader answers for it
            p, k = pins[j - 1], donor_of[j]
            out.append({"item": iid, "pin": j, "x_mm": p["x_mm"], "y_mm": p["y_mm"],
                        "what": p.get("what"), "severity": p.get("severity"),
                        "note": p.get("note") or "", "note_pin": k,
                        "rule": why[j] if j == k else f"named by pin {k}"})
    return out


FAULTS = {
    "edge": (select_edge_pins, "docs/defect-marks-2026-11-10/edge-reader-preregistration.md"),
    "letters": (select_letter_pins, "docs/defect-marks-2026-11-10/letter-reader-preregistration.md"),
    "infill": (select_infill_pins, "docs/infill-fault-reader-2026-11-11/preregistration.md"),
}


# ------------------------------------------------------------------ scoring ----

def _xy(points) -> np.ndarray:
    a = np.asarray([(p["x_mm"], p["y_mm"]) if isinstance(p, dict) else p for p in points], float)
    return a.reshape(-1, 2)


def nearest_mm(points, flags) -> np.ndarray:
    """Distance from each point to its nearest flag (inf with no flags)."""
    P, F = _xy(points), _xy(flags)
    if not len(F):
        return np.full(len(P), np.inf)
    if not len(P):
        return np.zeros(0)
    return np.sqrt(((P[:, None, :] - F[None, :, :]) ** 2).sum(-1)).min(1)


def hits(points, flags, radius_mm: float = RADIUS_MM) -> np.ndarray:
    """Bool per point: a flag lies within `radius_mm`."""
    return nearest_mm(points, flags) <= radius_mm


def local_strength(points, flags, radius_mm: float = RADIUS_MM) -> np.ndarray:
    """Per point, the strongest flag within the radius, 0 with none."""
    P, F = _xy(points), _xy(flags)
    s = np.asarray([f.get("strength", 1.0) for f in flags], float) if flags else np.zeros(0)
    if not len(F) or not len(P):
        return np.zeros(len(P))
    d = np.sqrt(((P[:, None, :] - F[None, :, :]) ** 2).sum(-1))
    return np.where(d <= radius_mm, s[None, :], 0.0).max(1)


def mask_points_mm(mask: np.ndarray, n: int, rng: np.random.Generator, px_per_mm: float,
                   pad_mm: float) -> np.ndarray:
    """`n` points uniform over the True pixels of `mask` (row = y), jittered
    within the pixel, in the pins' frame (`defect_marks.mark_mm`)."""
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError("empty mask: no stitched area to draw chance points from")
    k = rng.integers(0, len(xs), n)
    jx, jy = rng.random(n), rng.random(n)
    return np.stack([(xs[k] + jx) / px_per_mm - pad_mm, (ys[k] + jy) / px_per_mm - pad_mm], 1)


def edge_band(mask: np.ndarray, px_per_mm: float, band_mm: float = EDGE_BAND_MM) -> np.ndarray:
    """Thread pixels within `band_mm` of a non-thread pixel.

    "Non-thread" is FABRIC: the mask is thread against bare cloth, so a
    colour change between two threads is not an edge here. On a design whose
    faults sit inside a sewn field the band is only the field's outer rim,
    and `chance_edge` is 0 exactly when no flag lies within the radius of
    that rim: `L_bridge_hat` (letter reader, nearest flag 3.27 mm from the
    band) and `C_silhouette_logo` (9.19 mm). That is the band's definition,
    not a sampling fault (`test_edge_band_null_is_zero_for_flags_inside_a_field`).
    It is the right null only for a reader whose flags sit at fabric edges."""
    from scipy.ndimage import distance_transform_edt
    inside = distance_transform_edt(np.pad(mask, 1, constant_values=False))[1:-1, 1:-1]
    return mask & (inside <= band_mm * px_per_mm)


def chance_rate(flags, mask: np.ndarray, n_pins: int, px_per_mm: float, pad_mm: float,
                radius_mm: float = RADIUS_MM, draws: int = CHANCE_DRAWS, seed: int = SEED) -> float:
    """Mean hit rate of `flags` against `n_pins` random mask points, over
    `draws` draws. Same seed, same answer."""
    if n_pins <= 0:
        return float("nan")
    rng = np.random.default_rng(seed)
    pts = mask_points_mm(mask, n_pins * draws, rng, px_per_mm, pad_mm)
    return float(hits(pts, flags, radius_mm).mean())


def pick_rate(flags, cand_points, radius_mm: float = RADIUS_MM) -> float:
    """Hit rate of `flags` against a pin placed on a candidate anchor chosen
    uniformly at random: exact, the mean over all anchors (no draws)."""
    if not len(cand_points):
        return float("nan")
    return float(hits(cand_points, flags, radius_mm).mean())


def strength_auc(pin_strength: np.ndarray, rand_strength: np.ndarray) -> float:
    """P(pin's local strength > a random point's), ties half. 0.5 = chance."""
    a, b = np.asarray(pin_strength, float), np.sort(np.asarray(rand_strength, float))
    if not len(a) or not len(b):
        return float("nan")
    lo = np.searchsorted(b, a, "left")
    hi = np.searchsorted(b, a, "right")
    return float(((lo + (hi - lo) * 0.5) / len(b)).mean())


def item_score(pins: list[dict], flags: list[dict], mask: np.ndarray, px_per_mm: float,
               pad_mm: float, radii=(RADIUS_MM, *SENSITIVITY_MM), draws: int = CHANCE_DRAWS,
               seed: int = SEED, cand_mask: np.ndarray | None = None,
               cand_points: list | None = None) -> dict:
    """One item: hit and chance per radius, both nulls, strength AUC at RADIUS_MM.

    With a reader's candidate set (`cand_mask`, the pixels it could flag;
    `cand_points`, one anchor per feature it could flag) two more nulls and a
    precision: `chance_cand` (random points on the candidate pixels),
    `chance_pick` (random candidate anchors: picking the right members, not
    finding the region), `precision` (share of flags within reach of a pin)
    beside `precision_pick` (share of candidate anchors within reach of one).
    Pins carrying `note_pin` are also counted per note in `notes`."""
    band = edge_band(mask, px_per_mm)
    n = len(pins)
    row = {"pins": n, "flags": len(flags), "by_radius": {}}
    if cand_points is not None:
        row["candidates"] = len(cand_points)
    for r in radii:
        h = hits(pins, flags, r)
        b = row["by_radius"][str(r)] = {
            "hit": int(h.sum()), "hit_rate": float(h.mean()) if n else float("nan"),
            "chance_area": chance_rate(flags, mask, n, px_per_mm, pad_mm, r, draws, seed),
            "chance_edge": chance_rate(flags, band, n, px_per_mm, pad_mm, r, draws, seed)}
        if cand_mask is not None:
            b["chance_cand"] = (chance_rate(flags, cand_mask, n, px_per_mm, pad_mm, r, draws, seed)
                                if cand_mask.any() else float("nan"))
        if cand_points is not None:
            b["chance_pick"] = pick_rate(flags, cand_points, r)
            near = hits(flags, pins, r) if pins and flags else np.zeros(len(flags), bool)
            b["flags_near_pin"] = int(near.sum())
            b["precision"] = float(near.mean()) if flags else float("nan")
            b["precision_pick"] = (float(hits(cand_points, pins, r).mean())
                                   if pins and cand_points else float("nan"))
    if any("note_pin" in p for p in pins):
        notes: dict = {}
        for i, p in enumerate(pins):
            k = str(p.get("note_pin", p.get("pin")))
            notes.setdefault(k, []).append(i)
        row["notes"] = {k: {"pins": len(ix), "hit": {str(r): int(hits([pins[i] for i in ix], flags, r).sum())
                                                       for r in radii}}
                        for k, ix in notes.items()}
    if n:
        rng = np.random.default_rng(seed)
        rnd = mask_points_mm(mask, max(1000, draws), rng, px_per_mm, pad_mm)
        rndb = mask_points_mm(band, max(1000, draws), np.random.default_rng(seed + 1), px_per_mm, pad_mm)
        ps = local_strength(pins, flags)
        row["auc_area"] = strength_auc(ps, local_strength(rnd, flags))
        row["auc_edge"] = strength_auc(ps, local_strength(rndb, flags))
    d = nearest_mm(pins, flags)
    row["pin_nearest_mm"] = [None if not np.isfinite(v) else round(float(v), 2) for v in d]
    return row


def pool(rows: dict, radius_mm: float = RADIUS_MM, null: str = "chance_area",
         boots: int = BOOT_DRAWS, seed: int = SEED) -> dict:
    """Pooled hit and chance over items with pins, and a 95% bootstrap over
    ITEMS on (hit - chance). `rows` = item id -> `item_score` row."""
    keep = [r for r in rows.values() if r["pins"]]
    if not keep:
        return {"items": 0, "pins": 0}
    n = np.array([r["pins"] for r in keep], float)
    h = np.array([r["by_radius"][str(radius_mm)]["hit"] for r in keep], float)
    c = np.array([r["by_radius"][str(radius_mm)][null] for r in keep], float) * n

    def stat(ix):
        return (h[ix].sum() - c[ix].sum()) / n[ix].sum()

    rng = np.random.default_rng(seed)
    bs = np.array([stat(rng.integers(0, len(keep), len(keep))) for _ in range(boots)])
    hr, cr = h.sum() / n.sum(), c.sum() / n.sum()
    return {"items": len(keep), "pins": int(n.sum()), "hit_rate": round(float(hr), 4),
            "chance": round(float(cr), 4), "diff": round(float(hr - cr), 4),
            "kappa": round(float((hr - cr) / (1 - cr)), 4) if cr < 1 else None,
            "ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]}


def _boot_ci(stat, n_items: int, boots: int, seed: int) -> list:
    rng = np.random.default_rng(seed)
    bs = np.array([stat(rng.integers(0, n_items, n_items)) for _ in range(boots)])
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]


def pool_notes(rows: dict, radius_mm: float = RADIUS_MM, null: str = "chance_pick",
               boots: int = BOOT_DRAWS, seed: int = SEED) -> dict:
    """Each NOTE weighs one: its hit rate (hits / its pins) against its item's
    null, averaged over notes, with a 95% bootstrap over ITEMS (an item drawn
    brings all its notes). 28 pins written under one note are one judgement."""
    keep = [r for r in rows.values() if r["pins"] and r.get("notes")]
    if not keep:
        return {"items": 0, "notes": 0}
    per = [[(v["hit"][str(radius_mm)] / v["pins"], r["by_radius"][str(radius_mm)][null])
            for v in r["notes"].values()] for r in keep]

    def stat(ix):
        xs = [t for i in ix for t in per[i]]
        return float(np.mean([a - b for a, b in xs]))

    flat = [t for p in per for t in p]
    hr, cr = float(np.mean([a for a, _ in flat])), float(np.mean([b for _, b in flat]))
    return {"items": len(keep), "notes": len(flat), "hit_rate": round(hr, 4), "chance": round(cr, 4),
            "diff": round(hr - cr, 4), "kappa": round((hr - cr) / (1 - cr), 4) if cr < 1 else None,
            "notes_above_null": int(sum(a > b for a, b in flat)),
            "ci95": _boot_ci(stat, len(keep), boots, seed) if len(keep) > 1 else None}


def pool_precision(rows: dict, radius_mm: float = RADIUS_MM, boots: int = BOOT_DRAWS,
                   seed: int = SEED) -> dict:
    """Share of all flags (on items with pins) within reach of a pin, beside
    the share a reader picking the same number of candidates at random would
    get (`precision_pick`, flag-weighted), bootstrapped over items."""
    keep = [r for r in rows.values() if r["pins"] and r["flags"]
            and "precision" in r["by_radius"][str(radius_mm)]]
    if not keep:
        return {"items": 0, "flags": 0}
    f = np.array([r["flags"] for r in keep], float)
    near = np.array([r["by_radius"][str(radius_mm)]["flags_near_pin"] for r in keep], float)
    exp = np.array([r["by_radius"][str(radius_mm)]["precision_pick"] for r in keep], float) * f

    def stat(ix):
        return (near[ix].sum() - exp[ix].sum()) / f[ix].sum()

    pr, cr = near.sum() / f.sum(), exp.sum() / f.sum()
    return {"items": len(keep), "flags": int(f.sum()), "precision": round(float(pr), 4),
            "chance": round(float(cr), 4), "diff": round(float(pr - cr), 4),
            "ci95": _boot_ci(stat, len(keep), boots, seed) if len(keep) > 1 else None}


def unpinned_flags(flags: list[dict], pins: list[dict], radius_mm: float = RADIUS_MM) -> list[dict]:
    """Flags with no relevant pin within the radius, strongest first."""
    far = ~hits(flags, pins, radius_mm) if pins else np.ones(len(flags), bool)
    return sorted((f for f, x in zip(flags, far) if x), key=lambda f: -f.get("strength", 0))


# ---------------------------------------------------------------------- cli ----

def _load_mask(path: Path) -> np.ndarray:
    return np.load(path)["mask"].astype(bool)


def score_dir(marks: dict, flags_dir: Path, prefix: str = "L_", fault: str = "edge") -> dict:
    """Read `<flags_dir>/<item>.flags.json` (`{"flags": [...], "px_per_mm",
    "pad_mm"}`) and `<item>.mask.npz` for every item with that prefix,
    against the pins `FAULTS[fault]`'s rule selects. A reader that also
    writes its candidate set (`"candidates"` in the flags file, `cand` in the
    mask file) gets the candidate nulls and precision (`item_score`)."""
    return score_many([(marks, flags_dir, prefix)], fault)


def score_rows(marks: dict, flags_dir: Path, prefix: str, fault: str) -> dict:
    pins = FAULTS[fault][0](marks, prefix)
    rows = {}
    for iid in marks["items"]:
        if not iid.startswith(prefix):
            continue
        fj = flags_dir / f"{iid}.flags.json"
        if not fj.exists():
            continue
        rec = json.loads(fj.read_text(encoding="utf-8"))
        mine = [p for p in pins if p["item"] == iid]
        z = np.load(flags_dir / f"{iid}.mask.npz")
        cand = z["cand"].astype(bool) if "cand" in z.files else None
        row = item_score(mine, rec["flags"], z["mask"].astype(bool), rec["px_per_mm"], rec["pad_mm"],
                         cand_mask=cand, cand_points=rec.get("candidates"))
        row["unpinned"] = unpinned_flags(rec["flags"], mine)[:10]
        row["pin_ids"] = [p["pin"] for p in mine]
        rows[iid] = row
    return rows


def score_many(sources, fault: str = "edge") -> dict:
    """`score_dir` over several sittings at once: `sources` = [(marks,
    flags_dir, prefix), ...]; item ids must not repeat across them."""
    rows: dict = {}
    for marks, flags_dir, prefix in sources:
        got = score_rows(marks, flags_dir, prefix, fault)
        assert not set(got) & set(rows), "an item id repeats across sittings"
        rows.update(got)
    nulls = ["chance_area", "chance_edge"]
    any_row = next((r for r in rows.values() if r["pins"]), None)
    if any_row is not None:
        nulls += [k for k in ("chance_cand", "chance_pick") if k in any_row["by_radius"][str(RADIUS_MM)]]
    out = {"fault": fault, "radius_mm": RADIUS_MM, "items": rows,
           "pooled": {str(r): {null: pool(rows, r, null) for null in nulls}
                      for r in (RADIUS_MM, *SENSITIVITY_MM)}}
    if "chance_pick" in nulls:
        out["pooled_notes"] = {str(r): {null: pool_notes(rows, r, null) for null in nulls}
                               for r in (RADIUS_MM, *SENSITIVITY_MM)}
        out["precision"] = {str(r): pool_precision(rows, r) for r in (RADIUS_MM, *SENSITIVITY_MM)}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pins")
    p.add_argument("--marks", type=Path, required=True)
    p.add_argument("--out", type=Path)
    p.add_argument("--prefix", default="L_")
    p.add_argument("--fault", choices=sorted(FAULTS), default="edge")
    s = sub.add_parser("score", help="--marks/--flags/--prefix repeat together, one per sitting")
    s.add_argument("--marks", type=Path, action="append", required=True)
    s.add_argument("--flags", type=Path, action="append", required=True)
    s.add_argument("--prefix", action="append")
    s.add_argument("--json", type=Path)
    s.add_argument("--fault", choices=sorted(FAULTS), default="edge")
    a = ap.parse_args(argv)
    if a.cmd == "pins":
        marks = json.loads(a.marks.read_text(encoding="utf-8"))
        select, rule = FAULTS[a.fault]
        pins = select(marks, a.prefix)
        text = json.dumps({"rule": rule, "pins": pins}, indent=1)
        if a.out:
            a.out.write_text(text + "\n", encoding="utf-8")
        for p in pins:
            print(f"{p['item']:24s} {p['pin']:3d}  {p['rule']:14s} {p['what'] or '-':12s} {p['note'][:60]}")
        print(f"{len(pins)} pins on {len({p['item'] for p in pins})} items")
        return 0
    prefixes = a.prefix or ["L_"] * len(a.marks)
    if not len(a.marks) == len(a.flags) == len(prefixes):
        ap.error("--marks, --flags and --prefix must repeat together")
    res = score_many([(json.loads(m.read_text(encoding="utf-8")), f, px)
                      for m, f, px in zip(a.marks, a.flags, prefixes)], a.fault)
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    r = str(RADIUS_MM)
    for iid, row in res["items"].items():
        b = row["by_radius"][r]
        extra = "".join(f" {k[7:]} {b[k]:.3f}" for k in ("chance_cand", "chance_pick") if k in b)
        print(f"{iid:24s} pins {row['pins']:2d} flags {row['flags']:4d}  hit {b['hit']}/{row['pins']}"
              f"  chance area {b['chance_area']:.3f} edge {b['chance_edge']:.3f}{extra}"
              f"  auc {row.get('auc_area', float('nan')):.3f}/{row.get('auc_edge', float('nan')):.3f}")
    for key in ("pooled", "pooled_notes", "precision"):
        for rad, by in (res.get(key) or {}).items():
            print(f"{key} r={rad}: {by}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
