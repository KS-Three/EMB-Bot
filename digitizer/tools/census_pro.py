#!/usr/bin/env python
"""Corpus-wide census: every stitch classified, every element's layer recipe.

Where study_pro.py reads one file deeply, this reads the whole corpus and
answers structural questions: what layer stack does a professional put under
each technique, when does a column earn zigzag underlay, and what does every
stitch class measure across hundreds of thousands of stitches.

An ELEMENT is a group of runs whose extents overlap — the underlay walk, its
zigzag pass and the column over them all land on the same patch of fabric, so
spatial overlap in sew order recovers the layer stack without any knowledge of
the artwork.

Tokens: R running, Z sparse zigzag (underlay), S satin column, F fill,
L lock, O other. A recipe like R.Z.S reads "center walk, zigzag underlay,
then the column" — sew order, bottom to top.

Usage: .venv/Scripts/python tools/census_pro.py <file.dst> [...]
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from study_pro import classify, load_runs, satin_stats  # noqa: E402


def _bbox(pts, pad=0.3):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def _overlap(a, b) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _elements(runs):
    """Union-find over run bboxes -> list of elements (runs in sew order)."""
    n = len(runs)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    boxes = [_bbox(r["pts"]) for r in runs]
    for i in range(n):
        for j in range(i + 1, n):
            if runs[i]["block"] != runs[j]["block"]:
                continue        # a color change is always an element boundary
            if _overlap(boxes[i], boxes[j]):
                parent[find(j)] = find(i)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values()]


def _phases(pts) -> list[tuple[str, int, float]]:
    """Segment ONE needle-down run into technique phases.

    The corpus's long runs chain center walk + zigzag underlay + column with
    the needle down, so layer structure lives INSIDE runs — a per-run label
    reads the dominant phase and hides the stack (the first census printed
    'S x104' and no zigzag anywhere, which is how this function got written).

    Per 9-segment window: reversal fraction separates running from zigzag,
    and for zigzag the TWO-APART point distance separates a column (crosses
    0.4 mm apart: ~0.8) from sparse underlay (~2+): parity-safe, since two
    points apart always lands on the same rail. -> [(token, n_segs, med_len)].
    """
    n = len(pts)
    if n < 6:
        return [("O", max(n - 1, 0), 0.0)]
    seg = [(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(n - 1)]
    lens = [math.hypot(*s) for s in seg]
    revs = [False]
    for a, b in zip(seg, seg[1:]):
        la, lb = math.hypot(*a), math.hypot(*b)
        revs.append(la * lb > 1e-12 and (a[0] * b[0] + a[1] * b[1]) / (la * lb) < -0.2)
    two = [math.dist(pts[i], pts[i + 2]) for i in range(n - 2)]

    labels: list[str] = []
    W = 4
    for i in range(len(seg)):
        lo, hi = max(0, i - W), min(len(seg), i + W + 1)
        rf = sum(revs[lo:hi]) / max(hi - lo, 1)
        window = sorted(lens[lo:hi])
        med = window[len(window) // 2]
        t_lo, t_hi = max(0, i - W), min(len(two), i + W + 1)
        tw = sorted(two[t_lo:t_hi])
        step = tw[len(tw) // 2] if tw else 0.0
        if med <= 0.55 and rf >= 0.3:
            labels.append("L")
        elif rf >= 0.6 and med >= 0.6:
            labels.append("Z" if step > 1.4 else "S")
        elif rf <= 0.35:
            labels.append("R")
        else:
            labels.append("O")

    # absorb blips: a phase shorter than 5 segments joins its neighbour
    phases: list[tuple[str, int]] = []
    for t in labels:
        if phases and phases[-1][0] == t:
            phases[-1] = (t, phases[-1][1] + 1)
        else:
            phases.append((t, 1))
    merged: list[tuple[str, int]] = []
    for t, c in phases:
        if c < 5 and merged:
            merged[-1] = (merged[-1][0], merged[-1][1] + c)
        else:
            merged.append((t, c))
    out: list[tuple[str, int, float]] = []
    pos = 0
    for t, c in merged:
        chunk = sorted(lens[pos:pos + c])
        out.append((t, c, chunk[len(chunk) // 2] if chunk else 0.0))
        pos += c
    return out


def main() -> None:
    recipes: Counter[str] = Counter()
    widths_with_z: list[float] = []
    widths_without_z: list[float] = []
    lengths: dict[str, list[float]] = {}
    files = 0
    total = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        try:
            runs, _t, _j = load_runs(path)
        except Exception as exc:                       # noqa: BLE001
            print(f"{path.name}: unreadable ({type(exc).__name__})")
            continue
        files += 1
        for r in runs:
            r["phases"] = _phases(r["pts"])
            seg = [math.dist(a, b) for a, b in zip(r["pts"], r["pts"][1:])]
            pos = 0
            for t, c, _m in r["phases"]:
                lengths.setdefault(t, []).extend(
                    s for s in seg[pos:pos + c] if s > 0.03)
                pos += c
            total += len(r["pts"])
        for grp in _elements(runs):
            toks = [t for i in grp for t, _c, _m in runs[i]["phases"]]
            comp: list[str] = []
            for t in toks:
                if not comp or comp[-1] != t:
                    comp.append(t)
            recipe = ".".join(comp)
            recipes[recipe] += 1
            # underlay-vs-width: for elements whose top layer is a column,
            # measure the column's width and whether zigzag sits under it
            has_s = any(t == "S" for t in toks)
            if has_s:
                # width from the last S phase's points
                for i in reversed(grp):
                    pts = runs[i]["pts"]
                    pos = 0
                    w = None
                    for t, c, _m in runs[i]["phases"]:
                        if t == "S" and c >= 8:
                            w = satin_stats(pts[pos:pos + c + 1])["width_med"]
                        pos += c
                    if w is not None:
                        (widths_with_z if "Z" in toks else widths_without_z).append(w)
                        break

    print(f"files={files} stitches={total}")
    print("\n== ELEMENT RECIPES (layer stacks, sew order, count) ==")
    for recipe, cnt in recipes.most_common(18):
        print(f"  {recipe:<14} x{cnt}")
    print("\n== SATIN UNDERLAY vs COLUMN WIDTH ==")
    for name, arr in (("with zigzag", widths_with_z), ("no zigzag", widths_without_z)):
        if not arr:
            print(f"  {name}: none")
            continue
        arr.sort()
        n = len(arr)
        print(f"  {name:<12} n={n:<4} med={arr[n // 2]:.2f} "
              f"p10={arr[int(n * 0.10)]:.2f} p90={arr[int(n * 0.90)]:.2f}")
    print("\n== STITCH CENSUS (per class, mm) ==")
    for tok in ("S", "Z", "F", "R", "L", "O"):
        arr = sorted(lengths.get(tok, []))
        if not arr:
            continue
        n = len(arr)
        print(f"  {tok}: n={n:<7} med={arr[n // 2]:.2f} p90={arr[int(n * 0.90)]:.2f} "
              f"max={arr[-1]:.2f}")


if __name__ == "__main__":
    main()
