"""Re-capture ONE key of `testdata/flat_lane_golden.json`, safely.

Why this exists rather than re-running `capture_flat_lane_golden.py`: that
script regenerates the whole file, which would silently erase the pins on every
other fixture. `test_flat_lane_byte_identical`'s docstring is explicit that a
re-capture is a deliberate, per-key, documented act. This tool enforces that.

THE MACHINE MATTERS, and this is the part that is easy to get wrong. The
goldens are pinned to the original development machine. Other environments
differ by a handful of stitches in the numpy/opencv/shapely stack — the CI
workflow deselects three tests for exactly this reason, and the remote dev
container reproduces the drift (20 of 2363 coords on `enthusiast_logo`, up to
0.16 mm, unchanged by pinning numpy to the exact requirements version). A
capture taken on a drifting machine writes that machine's noise into the
golden and turns CI red for everyone else.

So this tool refuses to write unless the machine proves itself first, and the
proof has to be about THE TARGET KEY, not a convenient neighbour.

`--pre-change-tree` is the real guard, and the only one that is airtight. Point
it at a checkout of the engine as it stood BEFORE the change under review (a
git worktree at the previous commit). The tool runs the target key through that
tree and requires it to reproduce the golden exactly. That proves "this machine
+ old engine == golden", so every difference the new engine shows is the
change, not the machine. Use this whenever you can.

`--control` is the weaker fallback: keys the change does not touch, which must
still reproduce. Be careful — this proved insufficient in practice on
2026-08-14. `ribbon_curve.png` and `logo_whitebg.png` reproduced perfectly in
the remote dev container while `photo/enthusiast_logo.png` drifted by 20 of
2363 coords in that same container, because the drift lives in the PHOTO lane's
segmentation and the two controls only exercise the flat lane. A control only
vouches for a target it shares a code path with, and `flat_lane_golden.json`
currently holds exactly one photo-lane key — the very one you would be
re-capturing. So for a photo-lane target, `--control` cannot vouch for
anything: use `--pre-change-tree`.

Usage:
    python tools/recapture_flat_lane_key.py <key> \
        [--pre-change-tree PATH] [--control KEY ...] [--force]

Example (the 2026-08-14 pro-parity satin re-capture):
    python tools/recapture_flat_lane_key.py "photo/enthusiast_logo.png" \
        --pre-change-tree ../path/to/worktree/at/previous/commit

`--force` skips the machine check entirely. Do not use it to turn a red check
green — that is precisely the mistake this tool exists to prevent.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tests.test_flat_lane_byte_identical import _snapshot  # noqa: E402

GOLDEN = HERE.parent / "testdata" / "flat_lane_golden.json"
# Written by json.dumps(..., indent=1) with no trailing newline. Preserved
# exactly so the diff is the data that moved and nothing else.
INDENT = 1


def _fields_that_moved(old: dict, new: dict) -> list[str]:
    return [k for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)]


# Run in a subprocess so the other tree's `digitizer_core` is imported cleanly,
# rather than fighting this process's already-imported one.
_PRE_SNAP = """
import json, sys
sys.path.insert(0, sys.argv[1])
from tests.test_flat_lane_byte_identical import _snapshot
json.dump(_snapshot(sys.argv[2]), open(sys.argv[3], "w"))
"""


def _snapshot_in_tree(tree: Path, key: str, dest: Path) -> dict:
    runner = dest.parent / "_recap_pre.py"
    runner.write_text(_PRE_SNAP)
    subprocess.run([sys.executable, str(runner), str(tree.resolve()), key, str(dest)],
                   check=True, cwd=str(tree.resolve()))
    return json.loads(dest.read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("key", help="golden key to re-capture, e.g. photo/enthusiast_logo.png")
    ap.add_argument("--pre-change-tree", default=None,
                    help="checkout of the engine BEFORE the change; the airtight machine check")
    ap.add_argument("--control", action="append", default=[],
                    help="key the change under review must NOT alter; weaker, same-lane only")
    ap.add_argument("--force", action="store_true", help="skip the machine check (see docstring)")
    args = ap.parse_args()

    raw = GOLDEN.read_text(encoding="utf-8")
    data = json.loads(raw)

    if args.key not in data:
        print(f"ERROR: {args.key!r} is not a key in {GOLDEN.name}.")
        print("       Known keys: " + ", ".join(repr(k) for k in data))
        return 2

    if not args.control and not args.pre_change_tree and not args.force:
        print("ERROR: no --pre-change-tree and no --control, so this machine cannot")
        print("       prove itself. Prefer --pre-change-tree; it is the only check that")
        print("       vouches for the target key itself. See this file's docstring.")
        return 2

    # --- the machine check, strongest form ---------------------------------
    if args.pre_change_tree:
        tree = Path(args.pre_change_tree)
        if not (tree / "digitizer_core").is_dir():
            print(f"ERROR: {tree} does not look like a digitizer tree "
                  f"(no digitizer_core/ inside).")
            return 2
        pre = _snapshot_in_tree(tree, args.key, GOLDEN.parent / "_recap_pre.json")
        (GOLDEN.parent / "_recap_pre.json").unlink(missing_ok=True)
        (GOLDEN.parent / "_recap_pre.py").unlink(missing_ok=True)
        moved = _fields_that_moved(data[args.key], pre)
        if moved:
            print(f"REFUSING TO WRITE: with the PRE-CHANGE engine, this machine does not")
            print(f"  reproduce {args.key!r} (differs in: {', '.join(moved)}).")
            print("  So this machine already disagrees with the one that pinned the golden,")
            print("  and a capture taken here would write that disagreement into the file")
            print("  and turn CI red. Re-run on the golden machine, or in the environment")
            print("  whose CI has to go green.")
            return 1
        print(f"machine OK: pre-change engine reproduces {args.key} byte-for-byte")

    # --- the machine check, weaker fallback --------------------------------
    for ck in args.control:
        if ck not in data:
            print(f"ERROR: control key {ck!r} is not in {GOLDEN.name}.")
            return 2
        moved = _fields_that_moved(data[ck], _snapshot(ck))
        if moved:
            print(f"REFUSING TO WRITE: control fixture {ck!r} does not reproduce on this "
                  f"machine (differs in: {', '.join(moved)}).")
            print("  This machine disagrees with the one that pinned the goldens, so a")
            print("  capture taken here would bake in that disagreement. Re-run on the")
            print("  golden machine, or in the environment whose CI must go green.")
            return 1
        print(f"control OK: {ck} reproduces byte-for-byte")

    # --- the capture -------------------------------------------------------
    old = data[args.key]
    new = _snapshot(args.key)
    moved = _fields_that_moved(old, new)
    if not moved:
        print(f"nothing to do: {args.key} already matches this machine's output.")
        return 0

    for f in moved:
        if f == "stitch_count":
            print(f"  {f}: {old[f]} -> {new[f]}")
        elif f == "areas_mm2":
            pairs = [(a, b) for a, b in zip(old[f], new[f]) if a != b]
            print(f"  {f}: {len(pairs)} of {len(old[f])} areas moved"
                  + (f", largest {max((abs(b - a) for a, b in pairs), default=0):.4f} mm2" if pairs else ""))
        elif f == "stitch_coords":
            print(f"  {f}: {len(old[f])} -> {len(new[f])} coords")
        else:
            print(f"  {f}: {old[f]} -> {new[f]}")

    data[args.key] = new
    GOLDEN.write_text(json.dumps(data, indent=INDENT), encoding="utf-8")

    untouched = all(json.loads(raw)[k] == data[k] for k in data if k != args.key)
    print(f"\nwrote {GOLDEN}")
    print(f"every other key untouched: {untouched}")
    if not untouched:
        print("ERROR: other keys moved — this should be impossible. Revert and investigate.")
        return 1
    print("\nNow update the docstring in tests/test_flat_lane_byte_identical.py with a")
    print("dated note saying WHICH key moved and WHY — the file's own convention.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
