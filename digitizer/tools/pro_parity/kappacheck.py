#!/usr/bin/env python
"""Did a classifier change raise CORRECTED stitch-type agreement, or just
move the chance floor?

The satin-routing spec (2026-08-16 §4) bars raw agreement as evidence:
promotion shifts the satin/fill marginals, and sttype's chance floor is
computed from the two sides' own type mixes, so raw agreement can rise
while kappa falls. This reads the `score.json` files scorecard.py already
writes and lines the corrected component up before/after.

Usage: kappacheck.py <before_out/real> <after_out/real>
"""
import json
import sys
from pathlib import Path


def load(root):
    out = {}
    for d in sorted(Path(root).iterdir()):
        f = d / "score.json"
        if not f.exists():
            continue
        s = json.loads(f.read_text())
        out[d.name] = {
            "kappa": s["parts"]["sttype"],
            "raw": s["parts_raw"]["sttype"],
            "floor": s["detail"]["chance_floor"].get("sttype"),
            "score": s["score"],
        }
    return out


def _fmt_floor(v):
    return f"{v:>9.3f}" if v is not None else f"{'—':>9}"


def main():
    if len(sys.argv) != 3:
        print("Usage: kappacheck.py <before_out/real> <after_out/real>", file=sys.stderr)
        sys.exit(2)
    try:
        before = load(sys.argv[1])
        after = load(sys.argv[2])
    except FileNotFoundError:
        bad = sys.argv[1] if not Path(sys.argv[1]).is_dir() else sys.argv[2]
        print(f"no such run dir: {bad}", file=sys.stderr)
        sys.exit(2)
    shared = sorted(set(before) & set(after))
    missing = sorted(set(before) ^ set(after))
    if missing:
        print(f"NOT in both runs (excluded): {', '.join(missing)}")
    if not shared:
        print("no shared designs between the two runs — check paths point at .../real", file=sys.stderr)
        sys.exit(2)
    hdr = (f"{'design':<22}{'kappa_b':>9}{'kappa_a':>9}{'dkappa':>8}"
           f"{'raw_b':>8}{'raw_a':>8}{'floor_b':>9}{'floor_a':>9}")
    print(hdr)
    for name in shared:
        b, a = before[name], after[name]
        print(f"{name:<22}{b['kappa']:>9.3f}{a['kappa']:>9.3f}"
              f"{a['kappa'] - b['kappa']:>8.3f}{b['raw']:>8.3f}{a['raw']:>8.3f}"
              f"{_fmt_floor(b['floor'])}{_fmt_floor(a['floor'])}")
    mb = sum(before[n]["kappa"] for n in shared) / len(shared)
    ma = sum(after[n]["kappa"] for n in shared) / len(shared)
    sb = sum(before[n]["score"] for n in shared) / len(shared)
    sa = sum(after[n]["score"] for n in shared) / len(shared)
    print(f"\ncorpus mean kappa  {mb:.3f} -> {ma:.3f}  (delta {ma - mb:+.3f})")
    print(f"corpus mean score  {sb:.1f} -> {sa:.1f}")
    verdict = "KAPPA ROSE — gain is real" if ma > mb else \
              "KAPPA DID NOT RISE — published gain is the floor moving"
    print(f"\nVERDICT: {verdict}")


if __name__ == "__main__":
    main()
