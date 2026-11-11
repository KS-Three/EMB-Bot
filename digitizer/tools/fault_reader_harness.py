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
    """Thread pixels within `band_mm` of a non-thread pixel."""
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
               seed: int = SEED) -> dict:
    """One item: hit and chance per radius, both nulls, strength AUC at RADIUS_MM."""
    band = edge_band(mask, px_per_mm)
    n = len(pins)
    row = {"pins": n, "flags": len(flags), "by_radius": {}}
    for r in radii:
        h = hits(pins, flags, r)
        row["by_radius"][str(r)] = {
            "hit": int(h.sum()), "hit_rate": float(h.mean()) if n else float("nan"),
            "chance_area": chance_rate(flags, mask, n, px_per_mm, pad_mm, r, draws, seed),
            "chance_edge": chance_rate(flags, band, n, px_per_mm, pad_mm, r, draws, seed)}
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


def unpinned_flags(flags: list[dict], pins: list[dict], radius_mm: float = RADIUS_MM) -> list[dict]:
    """Flags with no relevant pin within the radius, strongest first."""
    far = ~hits(flags, pins, radius_mm) if pins else np.ones(len(flags), bool)
    return sorted((f for f, x in zip(flags, far) if x), key=lambda f: -f.get("strength", 0))


# ---------------------------------------------------------------------- cli ----

def _load_mask(path: Path) -> np.ndarray:
    return np.load(path)["mask"].astype(bool)


def score_dir(marks: dict, flags_dir: Path, prefix: str = "L_") -> dict:
    """Read `<flags_dir>/<item>.flags.json` (`{"flags": [...], "px_per_mm",
    "pad_mm"}`) and `<item>.mask.npz` for every item with that prefix."""
    pins = select_edge_pins(marks, prefix)
    rows = {}
    for iid in marks["items"]:
        if not iid.startswith(prefix):
            continue
        fj = flags_dir / f"{iid}.flags.json"
        if not fj.exists():
            continue
        rec = json.loads(fj.read_text(encoding="utf-8"))
        mine = [p for p in pins if p["item"] == iid]
        mask = _load_mask(flags_dir / f"{iid}.mask.npz")
        row = item_score(mine, rec["flags"], mask, rec["px_per_mm"], rec["pad_mm"])
        row["unpinned"] = unpinned_flags(rec["flags"], mine)[:10]
        row["pin_ids"] = [p["pin"] for p in mine]
        rows[iid] = row
    out = {"radius_mm": RADIUS_MM, "items": rows,
           "pooled": {str(r): {null: pool(rows, r, null) for null in ("chance_area", "chance_edge")}
                      for r in (RADIUS_MM, *SENSITIVITY_MM)}}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pins")
    p.add_argument("--marks", type=Path, required=True)
    p.add_argument("--out", type=Path)
    s = sub.add_parser("score")
    s.add_argument("--marks", type=Path, required=True)
    s.add_argument("--flags", type=Path, required=True)
    s.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    marks = json.loads(a.marks.read_text(encoding="utf-8"))
    if a.cmd == "pins":
        pins = select_edge_pins(marks)
        text = json.dumps({"rule": "docs/defect-marks-2026-11-10/edge-reader-preregistration.md",
                           "pins": pins}, indent=1)
        if a.out:
            a.out.write_text(text + "\n", encoding="utf-8")
        for p in pins:
            print(f"{p['item']:24s} {p['pin']:3d}  {p['rule']:14s} {p['what'] or '-':12s} {p['note'][:60]}")
        print(f"{len(pins)} pins on {len({p['item'] for p in pins})} items")
        return 0
    res = score_dir(marks, a.flags)
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    r = str(RADIUS_MM)
    for iid, row in res["items"].items():
        b = row["by_radius"][r]
        print(f"{iid:24s} pins {row['pins']:2d} flags {row['flags']:4d}  hit {b['hit']}/{row['pins']}"
              f"  chance area {b['chance_area']:.3f} edge {b['chance_edge']:.3f}"
              f"  auc {row.get('auc_area', float('nan')):.3f}/{row.get('auc_edge', float('nan')):.3f}")
    for rad, by in res["pooled"].items():
        for null, pr in by.items():
            print(f"pooled r={rad} {null}: {pr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
