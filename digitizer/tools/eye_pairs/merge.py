"""python -m tools.eye_pairs.merge <dest> <lane> [<lane> ...]

Merge several `--render --out <lane>` directories into one `eye_pairs_out/`,
so a run split across parallel lanes -- by `--fixtures`, with `ref_0827` on
a lane of its own because its worktree path is fixed -- can feed `--pair` or
`tools.eye_pairs_gallery --labelled` exactly as one long run would.

Rows are unioned per (fixture, arm) and the FIRST lane listed wins a key two
lanes both rendered (every lane digitizes `base`). That is safe only if both
lanes produced the same design, so the merge REFUSES when two lanes disagree
on a design file's bytes or on a fixture's source hash; a render whose JPEG
bytes differ for one design is kept from the first lane and noted. Rows that
carry an `error` are kept: the labelled page counts them as failed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

SOURCES = "__sources__"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge_lanes(dest: Path, lanes: list[Path], say=print) -> dict:
    """-> {"fixtures", "arm_runs", "renders", "designs"} counts in `dest`."""
    dest = Path(dest)
    lanes = [Path(p) for p in lanes]
    if not lanes:
        raise SystemExit("REFUSED: no lanes given")
    for lane in lanes:
        if not (lane / "features.json").exists():
            raise SystemExit(f"REFUSED: {lane / 'features.json'} is missing -- not a --render lane")
    for sub in ("renders", "designs"):
        (dest / sub).mkdir(parents=True, exist_ok=True)

    merged: dict = {SOURCES: {}}
    seen: dict[str, tuple[Path, str]] = {}          # "designs/x.json" -> (lane, digest)
    source_lane: dict[str, Path] = {}               # fixture -> the lane that set its hash
    for lane in lanes:
        feats = json.loads((lane / "features.json").read_text(encoding="utf-8"))
        for fx, digest in feats.pop(SOURCES, {}).items():
            if merged[SOURCES].get(fx, digest) != digest:
                raise SystemExit(f"REFUSED: {fx} was rendered from different source "
                                 f"images in {source_lane[fx]} and {lane}")
            merged[SOURCES].setdefault(fx, digest)
            source_lane.setdefault(fx, lane)
        for fx, rows in feats.items():
            for arm, row in rows.items():
                merged.setdefault(fx, {}).setdefault(arm, row)
        for sub in ("renders", "designs"):
            folder = lane / sub
            if not folder.exists():
                continue
            for f in sorted(folder.iterdir()):
                key = f"{sub}/{f.name}"
                digest = _digest(f)
                if key in seen and seen[key][1] != digest:
                    if sub == "designs":
                        raise SystemExit(f"REFUSED: {key} differs between {seen[key][0]} and "
                                         f"{lane} -- the same (fixture, arm) digitized to two "
                                         f"designs, so their rows cannot be pooled")
                    say(f"note: {key} differs between {seen[key][0]} and {lane}; "
                        f"keeping the first")
                    continue
                if key not in seen:
                    shutil.copyfile(f, dest / sub / f.name)
                    seen[key] = (lane, digest)
    tmp = dest / "features.json.tmp"
    tmp.write_text(json.dumps(merged, indent=1), encoding="utf-8")
    tmp.replace(dest / "features.json")
    return {"fixtures": len(merged) - 1,
            "arm_runs": sum(len(v) for k, v in merged.items() if k != SOURCES),
            "renders": sum(1 for k in seen if k.startswith("renders/")),
            "designs": sum(1 for k in seen if k.startswith("designs/"))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dest", type=Path, help="the merged eye_pairs_out directory")
    ap.add_argument("lanes", type=Path, nargs="+", help="--render --out directories, first wins")
    args = ap.parse_args(argv)
    n = merge_lanes(args.dest, args.lanes)
    print(f"merged {len(args.lanes)} lanes -> {args.dest}: {n['fixtures']} fixtures, "
          f"{n['arm_runs']} arm-runs, {n['renders']} renders, {n['designs']} designs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
