"""The price table for a labelled sitting, built from the render it sits on.

    python -m tools.eye_pairs_price <eye_pairs_out> <arm> [--caption TEXT] [--out tables.json]

Reads a `tools.eye_pairs --render` output (one lane or a `merge`d one):
`designs/<fixture>__<arm>.json` and `features.json`, nothing else, and
writes the `{arm: {caption, columns, rows}}` file that
`tools.eye_pairs_gallery --labelled --tables` puts under the arm's head.

Until 2026-10-07 every sitting's price table was a scratch script (10-03's
was "counted from the stitch records", 10-06's `scratch_letterform_priors/
price.py`), and the 10-03 one priced a flag in stitches and trims while
leaving out the fidelity rows that then turned the coverage regression red
on the flip's first CI run. This carries both, from the same files the
pictures were drawn from, so the page and the numbers cannot describe two
different engines.

Columns: the whole design (stitches, trims, colour changes, cones), the
CHANGED shapes alone (the shapes whose runs differ between the two designs
-- for a lettering arm, the letters it rebuilt -- their stitches and the
trims that land on them), and three fidelity rows from `features.json`
(`uncovered_ink_frac`, `lost_frac`, `ragged_mm`). A cell reads
`base -> arm` where the two differ and one figure where they do not. It is
a price list, not a grade: nothing in it says which side is better.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = "base"
SOURCES = "__sources__"
COLUMNS = ["fixture", "on the page", "stitches", "trims", "colour changes", "cones",
           "changed shapes", "their stitches", "their trims",
           "uncovered ink", "lost_frac", "ragged mm"]
FIDELITY = (("uncovered_ink_frac", "pct"), ("lost_frac", "4dp"), ("ragged_mm", "3dp"))


def records(design: dict) -> dict:
    """Whole-design counts, the same definitions as `eye_pairs.features._records`
    (stitchCount when the Design states it, a `trim` record per trim, a
    `color` record per stop, distinct thread RGBs per cone)."""
    st = design.get("stitches") or []
    n = design.get("stitchCount")
    if n is None:
        n = sum(1 for s in st if s["type"] == "stitch")
    cones = {(c.get("r"), c.get("g"), c.get("b")) for c in design.get("colors") or []}
    return {"stitches": n,
            "trims": sum(1 for s in st if s["type"] == "trim"),
            "stops": sum(1 for s in st if s["type"] == "color"),
            "cones": len(cones)}


def _shape_signature(design: dict) -> dict[str, list]:
    """shape -> its runs as (kind, role, stitch coordinates), in sew order.
    Coordinates and not counts: a construction change that keeps a shape's
    count but moves its needles is a change."""
    st = design.get("stitches") or []
    sig: dict[str, list] = {}
    for r in design.get("runs") or []:
        pts = tuple((s["x"], s["y"]) for s in st[r["i0"]:r["i1"] + 1] if s["type"] == "stitch")
        sig.setdefault(r["shape"], []).append((r["kind"], r.get("role", ""), pts))
    return sig


def changed_shapes(base: dict, arm: dict) -> set[str]:
    """Shapes whose runs differ between the two designs, or that only one has."""
    a, b = _shape_signature(base), _shape_signature(arm)
    return {s for s in a.keys() | b.keys() if a.get(s) != b.get(s)}


def scoped(design: dict, shapes: set[str]) -> dict:
    """Stitches in `shapes`' runs, and the trims whose NEXT run is one of them
    (a trim belongs to the shape the needle is trimmed into)."""
    st = design.get("stitches") or []
    runs = sorted(design.get("runs") or [], key=lambda r: r["i0"])
    n = sum(1 for r in runs if r["shape"] in shapes
            for s in st[r["i0"]:r["i1"] + 1] if s["type"] == "stitch")
    trims, j = 0, 0
    for i, s in enumerate(st):
        if s["type"] != "trim":
            continue
        while j < len(runs) and runs[j]["i0"] <= i:
            j += 1
        if j < len(runs) and runs[j]["shape"] in shapes:
            trims += 1
    return {"stitches": n, "trims": trims}


def _fmt(v, how: str = "int") -> str:
    if v is None:
        return "n/a"
    if how == "pct":
        return f"{100.0 * v:.2f}%"
    if how == "4dp":
        return f"{v:.4f}"
    if how == "3dp":
        return f"{v:.3f}"
    return f"{v:,}"


def cell(a, b, how: str = "int") -> str:
    fa, fb = _fmt(a, how), _fmt(b, how)
    return fa if fa == fb else f"{fa} → {fb}"


def price_rows(src: Path, arm: str) -> list[list[str]]:
    src = Path(src)
    feats = json.loads((src / "features.json").read_text(encoding="utf-8"))
    rows = []
    for fx in sorted(k for k in feats if k != SOURCES):
        pb = src / "designs" / f"{fx}__{BASE}.json"
        pa = src / "designs" / f"{fx}__{arm}.json"
        if not (pb.exists() and pa.exists()):
            continue
        db = json.loads(pb.read_text(encoding="utf-8"))
        da = json.loads(pa.read_text(encoding="utf-8"))
        rb, ra = records(db), records(da)
        ch = changed_shapes(db, da)
        sb, sa = scoped(db, ch), scoped(da, ch)
        fb = feats[fx].get(BASE, {})
        fa = feats[fx].get(arm, {})
        row = [fx, "pair" if ch else "identical",
               cell(rb["stitches"], ra["stitches"]), cell(rb["trims"], ra["trims"]),
               cell(rb["stops"], ra["stops"]), cell(rb["cones"], ra["cones"]),
               str(len(ch)),
               cell(sb["stitches"], sa["stitches"]), cell(sb["trims"], sa["trims"])]
        row += [cell(fb.get(k), fa.get(k), how) for k, how in FIDELITY]
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src", type=Path, help="a --render (or merged) eye_pairs_out directory")
    ap.add_argument("arm", help="the arm id priced against base")
    ap.add_argument("--caption", default=(
        "The price the pictures cannot show, counted from the designs that drew "
        "these pairs: shipped → flag where they differ, one figure where they "
        "do not. 'Changed shapes' are the shapes whose runs differ; 'their trims' "
        "are trims into them. Nothing here says which side is better."))
    ap.add_argument("--out", type=Path, default=None, help="default: print")
    args = ap.parse_args(argv)
    rows = price_rows(args.src, args.arm)
    if not rows:
        raise SystemExit(f"REFUSED: no fixture in {args.src} has both {BASE} and {args.arm}")
    table = {args.arm: {"caption": args.caption, "columns": COLUMNS, "rows": rows}}
    text = json.dumps(table, indent=1, ensure_ascii=False)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
