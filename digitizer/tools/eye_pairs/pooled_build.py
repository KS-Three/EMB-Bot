"""Build docs/eye-pairs-2026-10-11/pooled-inputs.json from the sittings' exports.

    python -m tools.eye_pairs.pooled_build --flags-dir <eye_pairs_out of 09-18> \\
        --flags-recomputed <json> --columns-dir <density-1007 render dir> \\
        --priors-dir <letterform-priors render dir> --out ../docs/eye-pairs-2026-10-11/pooled-inputs.json

A ONE-OFF, kept so the committed inputs can be audited and rebuilt, not a
pipeline: three of the sources are gitignored render directories on Kent's
laptop (`digitizer/eye_pairs_out/` of 2026-09-18, and two worktrees'). What
those directories held is copied into the JSON as numbers, so the analysis in
`pooled.py` is reproducible from main alone.

What each label is paired with (see docs/yardstick-vs-kents-eye-2026-10-11.md
for the provenance and the caveats):

* 2026-09-18..09-28, 77 pairs: the 09-18 render directory's features, with
  the two lost_frac halves and uncovered_ink_frac RECOMPUTED from the stored
  designs (no digitize; `lost_frac` reproduces the stored value to 4 dp on
  every design). Not the cloud render Kent judged from 09-20 on, which was
  not kept: same engine, platform-level rounding, and tires (judged on a
  cutout render this directory does not hold) is left unscored on those.
* 09-30 .. 10-03 sittings: the committed price/corpus tables only.
* 10-07: the render directories of the page he judged.
* columns-flip-1008: the committed price table.
* full-density: nothing found; labels only.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tools.eye_pairs_price import changed_shapes, records, scoped

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
BASE = "base"
REF_ARMS = {"ref_0827", "ref_0930am"}              # `before` is the OLD engine
FEATURE_KEYS = ("lost_frac", "unsewn_frac", "overshoot_frac", "uncovered_ink_frac",
                "uncovered_total_mm2", "lost_elements", "ragged_mm", "hausdorff_mm",
                "artfid", "trims_per_1000", "stitches")
INK_REFUSABLE = {"lost_frac", "unsewn_frac", "overshoot_frac", "uncovered_ink_frac",
                 "lost_elements", "ragged_mm", "hausdorff_mm", "artfid"}


def _utf(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def num(cell) -> float | None:
    """'2,093' / '7.03' / '5.80%' -> float (a percent becomes a fraction)."""
    if cell is None:
        return None
    s = str(cell).strip()
    m = re.fullmatch(r"([0-9][0-9,]*\.?[0-9]*)\s*(%?)", s)
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    return v / 100.0 if m.group(2) else v


def split_cell(cell) -> tuple[float, float] | None:
    """'a -> b' (before, after) or one figure that holds on both sides."""
    if cell is None:
        return None
    parts = [x.strip() for x in str(cell).split("→")]
    vals = [num(x) for x in parts]
    if len(parts) == 1 and vals[0] is not None:
        return vals[0], vals[0]
    if len(parts) == 2 and None not in vals:
        return vals[0], vals[1]
    return None


def table_rows(table: dict, key_col: str) -> dict[str, dict]:
    cols = table["columns"]
    return {r[cols.index(key_col)]: dict(zip(cols, r)) for r in table["rows"]}


def _pair(sitting, arm, fixture, label, judged, before, after, refused=None, **extra) -> dict:
    """`refused` = {"before": [...], "after": [...]}: the ink metrics the
    instrument refused on that side (`refusal_for`: the row is not an engine
    result). Kept as a list, not as a blanked value, so the pool can show what
    reading the refusals costs."""
    p = {"id": f"{sitting}:{arm}:{fixture}", "arm": arm, "fixture": fixture,
         "label": label, "judged": judged,
         "before": {k: v for k, v in before.items() if v is not None},
         "after": {k: v for k, v in after.items() if v is not None}}
    if refused and (refused.get("before") or refused.get("after")):
        p["refused"] = refused
    p.update(extra)
    return p


def _from_cells(row: dict, spec: dict[str, tuple[str, float]]) -> tuple[dict, dict]:
    """spec: metric -> (column, scale). -> (before values, after values)."""
    b, a = {}, {}
    for metric, col in spec.items():
        pr = split_cell(row.get(col))
        if pr is not None:
            b[metric], a[metric] = pr
    return b, a


def _feature_values(row: dict | None, design: dict | None, recomputed: dict | None,
                    ) -> tuple[dict, list]:
    """-> (one arm's instrument values, the ink metrics it was refused on).
    The recomputed row's refusals win when there is one: it refuses every ink
    metric the instrument has today, including the ones a schema-1 row never
    carried, so `lost_frac` and its halves are refused together."""
    if row is None or "error" in row:
        return {}, []
    merged = dict(row)
    if recomputed:
        for k in ("unsewn_frac", "overshoot_frac", "uncovered_ink_frac"):
            if recomputed.get(k) is not None:
                merged[k] = recomputed[k]
    out = {k: merged.get(k) for k in FEATURE_KEYS}
    refusals = (recomputed or row).get("refusals") or {}
    refused = sorted(k for k in refusals if k in INK_REFUSABLE)
    if "lost_frac" in refused:                      # one reason covers the whole ink family
        refused = sorted(INK_REFUSABLE)
    if design is not None:
        out["trims"] = records(design)["trims"]
        out["stitches"] = records(design)["stitches"]
    return out, refused


def flags_sitting(notes: dict, fdir: Path, recomputed: dict) -> dict:
    feats = _utf(fdir / "features.json")
    pairs = []
    for key, v in sorted(notes["notes"].items()):
        arm, fixture = v["arm"], v["fixture"]
        judged = v["updated"][:10]
        rows = feats.get(fixture, {})
        if arm not in rows or "base" not in rows:
            pairs.append(_pair("flags-0918-0928", arm, fixture, v["verdict"], judged, {}, {},
                               unscored_why="arm not in the 09-18 render directory"))
            continue
        if fixture == "tires" and judged > "2026-09-18":
            pairs.append(_pair("flags-0918-0928", arm, fixture, v["verdict"], judged, {}, {},
                               unscored_why="judged on the cutout render; the 09-18 directory "
                                            "holds the no-cutout one"))
            continue

        def load(name):
            p = fdir / "designs" / f"{fixture}__{name}.json"
            return _utf(p) if p.exists() else None

        db, da = load(BASE), load(arm)
        vb, rb = _feature_values(rows[BASE], db, recomputed.get(fixture, {}).get(BASE))
        va, ra = _feature_values(rows[arm], da, recomputed.get(fixture, {}).get(arm))
        if db is not None and da is not None and arm not in REF_ARMS:
            ch = changed_shapes(db, da)
            vb["changed_trims"] = scoped(db, ch)["trims"]
            va["changed_trims"] = scoped(da, ch)["trims"]
        before, after = (va, vb) if arm in REF_ARMS else (vb, va)
        rf = {"before": ra, "after": rb} if arm in REF_ARMS else {"before": rb, "after": ra}
        pairs.append(_pair("flags-0918-0928", arm, fixture, v["verdict"], judged, before, after,
                           refused=rf, source="09-18 render directory + recomputed halves"))
    return {"date": "2026-09-18..2026-09-28", "labels": "docs/eye-pairs-2026-09-28/kent-notes.json",
            "instruments": "09-18 render directory (Kent's laptop, gitignored), recomputed from stored designs",
            "pairs": pairs}


def table_sitting(sid, date, labels_src, instruments_src, arm, label_pairs: dict, table: dict,
                  key_col: str, spec: dict, judged: str) -> dict:
    rows = table_rows(table, key_col)
    pairs = []
    for fixture, v in sorted(label_pairs.items()):
        row = rows.get(fixture)
        before, after = ({}, {}) if row is None else _from_cells(row, spec)
        pairs.append(_pair(sid, arm, fixture, v.get("verdict"), v.get("updated", judged)[:10],
                           before, after))
    return {"date": date, "labels": labels_src, "instruments": instruments_src, "pairs": pairs}


def render_dir_sitting(sid, date, labels_src, instruments_src, arm, labels: dict, rdir: Path) -> dict:
    feats = _utf(rdir / "features.json")
    pairs = []
    for fixture, label in sorted(labels.items()):
        rows = feats.get(fixture, {})

        def load(name):
            p = rdir / "designs" / f"{fixture}__{name}.json"
            return _utf(p) if p.exists() else None

        db, da = load(BASE), load(arm)
        vb, rb = _feature_values(rows.get(BASE), db, None)
        va, ra = _feature_values(rows.get(arm), da, None)
        if db is not None and da is not None:
            ch = changed_shapes(db, da)
            vb["changed_trims"], va["changed_trims"] = scoped(db, ch)["trims"], scoped(da, ch)["trims"]
        pairs.append(_pair(sid, arm, fixture, label, date, vb, va,
                           refused={"before": rb, "after": ra}))
    return {"date": date, "labels": labels_src, "instruments": instruments_src, "pairs": pairs}


def build(args) -> dict:
    n09 = _utf(DOCS / "eye-pairs-2026-09-28" / "kent-notes.json")
    n0930 = _utf(DOCS / "eye-pairs-2026-09-30" / "kent-notes.json")
    n1003 = _utf(DOCS / "eye-pairs-2026-10-03" / "kent-notes.json")
    n1007 = _utf(DOCS / "eye-pairs-2026-10-07" / "kent-notes.json")
    store = _utf(DOCS / "eye-pairs-2026-10-11" / "kent-notes-store-export.json")
    recomputed = _utf(args.flags_recomputed)
    sittings: dict[str, dict] = {}

    sittings["flags-0918-0928"] = flags_sitting(n09, args.flags_dir, recomputed)

    # ---- 2026-09-30 (store of 09-29/30): envelope, evening, texture, pro
    env = {k.split("__")[1]: v for k, v in n0930["notes"].items() if v["arm"] == "rail_envelope"}
    t = _utf(DOCS / "eye-pairs-2026-09-30" / "rail-envelope-corpus.json")["rail_envelope"]
    sittings["envelope-0930"] = table_sitting(
        "envelope-0930", "2026-09-30", "docs/eye-pairs-2026-09-30/kent-notes.json",
        "docs/eye-pairs-2026-09-30/rail-envelope-corpus.json (symmetric -> envelope)",
        "rail_envelope", env, t, "fixture",
        {"stitches": "stitches", "trims": "trims", "bare_satin_pct": "bare satin %"}, "2026-09-30")

    third = n0930["third_sitting"]["arms"]
    t = _utf(DOCS / "eye-pairs-2026-09-30" / "three-changes-corpus.json")["ref_0930am"]
    ev_ref = table_sitting(
        "evening-0930", "2026-09-30", "docs/eye-pairs-2026-09-30/kent-notes.json (third_sitting)",
        "docs/eye-pairs-2026-09-30/three-changes-corpus.json (morning engine -> today)",
        "ref_0930am", third["ref_0930am"]["pairs"], t, "fixture",
        {"stitches": "stitches", "trims": "trims"}, "2026-09-30")
    t = _utf(DOCS / "eye-pairs-2026-09-30" / "dissolve-corpus.json")["phantom_dissolve"]
    ev_dis = table_sitting(
        "evening-0930", "2026-09-30", "", "", "phantom_dissolve",
        third["phantom_dissolve"]["pairs"], t, "logo",
        {"stitches": "stitches", "trims": "trims"}, "2026-09-30")
    ev_ref["pairs"] += ev_dis["pairs"]
    sittings["evening-0930"] = ev_ref

    fourth = n0930["fourth_sitting"]["arms"]
    tex = _utf(DOCS / "eye-pairs-2026-09-30" / "texture-corpus.json")
    tx = table_sitting("texture-0930", "2026-10-01", "docs/eye-pairs-2026-09-30/kent-notes.json (fourth_sitting)",
                       "docs/eye-pairs-2026-09-30/texture-corpus.json", "split_7mm",
                       fourth["split_7mm"]["pairs"], tex["split_7mm"], "fixture",
                       {"stitches": "stitches"}, "2026-10-01")
    tx["pairs"] += table_sitting("texture-0930", "2026-10-01", "", "", "rails_symmetric",
                                 fourth["rails_symmetric"]["pairs"], tex["rails_symmetric"],
                                 "fixture", {"stitches": "stitches"}, "2026-10-01")["pairs"]
    sittings["texture-0930"] = tx

    # ---- 2026-10-03
    pt = _utf(DOCS / "eye-pairs-2026-10-03" / "price-tables.json")
    off = {"date": "2026-10-03", "labels": "docs/eye-pairs-2026-10-03/kent-notes.json",
           "instruments": "docs/eye-pairs-2026-10-03/price-tables.json (stitches, trims only)",
           "pairs": []}
    for arm in ("cap_recentre", "bean_letters", "split_off"):
        labels = {v["fixture"]: v for v in n1003["notes"].values() if v["arm"] == arm}
        off["pairs"] += table_sitting("off-flags-1003", "2026-10-03", "", "", arm, labels,
                                      pt[arm], "fixture",
                                      {"stitches": "stitches", "trims": "trims"}, "2026-10-03")["pairs"]
    sittings["off-flags-1003"] = off

    # ---- 2026-10-07
    cols = {p["fixture"]: p["verdict"] for p in n1007["columns_sitting"]["pairs"]}
    sittings["density-1007"] = render_dir_sitting(
        "density-1007", "2026-10-07", "docs/eye-pairs-2026-10-07/kent-notes.json (columns_sitting)",
        "render directory of the page he judged (columns-sitting worktree, gitignored)",
        "lettering_columns", cols, args.columns_dir)
    pri = {p["fixture"]: p["verdict"] for p in n1007["pairs"]}
    sittings["letterform-1007"] = render_dir_sitting(
        "letterform-1007", "2026-10-07", "docs/eye-pairs-2026-10-07/kent-notes.json (pairs)",
        "render directory of the page he judged (letterform-priors worktree, gitignored)",
        "letterform_priors", pri, args.priors_dir)

    # ---- 2026-10-08, from the store export
    flip_t = _utf(DOCS / "eye-pairs-2026-10-08" / "flip" / "price-tables.json")["columns_words"]
    flip_labels = {v["fixture"]: v for v in store["notes"].values() if v["arm"] == "columns_words"}
    sittings["columns-flip-1008"] = table_sitting(
        "columns-flip-1008", "2026-10-08", "docs/eye-pairs-2026-10-11/kent-notes-store-export.json",
        "docs/eye-pairs-2026-10-08/flip/price-tables.json", "columns_words", flip_labels,
        flip_t, "fixture",
        {"stitches": "stitches", "trims": "trims", "changed_trims": "their trims",
         "uncovered_ink_frac": "uncovered ink", "lost_frac": "lost_frac", "ragged_mm": "ragged mm"},
        "2026-10-08")
    fd = {"date": "2026-10-08", "labels": "docs/eye-pairs-2026-10-11/kent-notes-store-export.json",
          "instruments": "none found", "pairs": []}
    for v in sorted((v for v in store["notes"].values() if v["arm"] == "lettering_columns"),
                    key=lambda v: v["fixture"]):
        fd["pairs"].append(_pair("full-density-1008", "lettering_columns", v["fixture"],
                                 v["verdict"], v["updated"][:10], {}, {},
                                 unscored_why="no render directory or table for this page on main "
                                              "or on Kent's laptop"))
    sittings["full-density-1008"] = fd
    return {"schema": 1, "built": "2026-10-11", "sittings": sittings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--flags-dir", type=Path, required=True)
    ap.add_argument("--flags-recomputed", type=Path, required=True)
    ap.add_argument("--columns-dir", type=Path, required=True)
    ap.add_argument("--priors-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    data = build(args)
    args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    n = sum(len(s["pairs"]) for s in data["sittings"].values())
    print(f"{n} labelled pairs in {len(data['sittings'])} sittings -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
