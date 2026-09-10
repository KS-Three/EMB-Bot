"""Re-capture ONE key of `testdata/photo_lane_segment_golden.json`, safely.

The photo-lane twin of `recapture_flat_lane_key.py`, under the same doctrine.
`capture_photo_lane_golden.py` regenerates the whole file, which would
silently erase the pins on every other fixture, and
`tests/test_photo_lane_byte_identical.py`'s docstring is explicit that a
re-capture is a deliberate, per-key, documented act for a change that
knowingly moves stage 2's own output. This tool enforces that, one key at a
time, and refuses to write unless the machine proves itself first.

THE MACHINE MATTERS. The goldens are pinned to the machine that captured
them; other environments differ by platform-level numerics in the
numpy/opencv/scikit-image stack (CI deselects three flat-lane and stage-5
tests for exactly this reason, and the remote dev container reproduces that
drift on `photo/enthusiast_logo.png`). A capture taken on a drifting machine
writes that machine's noise into the golden and turns CI red for everyone
else. So: capture on the runner whose CI judges the golden (ubuntu-latest),
never on a Windows box or a dev container.

`--pre-change-tree` is the airtight guard. Point it at a checkout of the
engine as it stood BEFORE the change under review (a git worktree at the
previous commit). The tool runs the target key through that tree and
requires it to reproduce the golden exactly: "this machine + old engine ==
golden", so every difference the new engine shows is the change, not the
machine. Use this whenever you can.

`--control` is the weaker fallback: keys the change must NOT touch, which
still have to reproduce. Every key in this file is the SLIC+RAG lane, so a
control at least shares the code path with the target — but a control only
vouches for the numerics it exercises, and a change that moves the target's
region set can move numerics the control never reaches. Prefer
`--pre-change-tree`.

`--dry-run` prints what would move and writes nothing — for checking a
change's footprint on a machine that must not capture (see above).

Usage:
    python tools/recapture_photo_lane_key.py <key> \
        [--pre-change-tree PATH] [--control KEY ...] [--dry-run] [--force]

Example (the 2026-09-10 `robust_region_colour` flip, on ubuntu-latest):
    python tools/recapture_photo_lane_key.py "photo/drone_render.png" \
        --pre-change-tree ../pre/digitizer

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

from tests.test_photo_lane_byte_identical import GOLDEN_PATH, _snapshot  # noqa: E402

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
from tests.test_photo_lane_byte_identical import _snapshot
json.dump(_snapshot(sys.argv[2]), open(sys.argv[3], "w"))
"""


def _snapshot_in_tree(tree: Path, key: str, dest: Path) -> dict:
    runner = dest.parent / "_recap_pre.py"
    runner.write_text(_PRE_SNAP)
    subprocess.run([sys.executable, str(runner), str(tree.resolve()), key, str(dest)],
                   check=True, cwd=str(tree.resolve()))
    return json.loads(dest.read_text())


def _describe(field: str, old, new) -> str:
    if field == "labels_sha256":
        return f"{old[:12]} -> {new[:12]}"
    if field == "thread_indices":
        return f"{old} -> {new}"
    if field == "cluster_rgb":
        pairs = sum(1 for a, b in zip(old, new) if a != b)
        return f"{len(old)} -> {len(new)} rows, {pairs} of the shared rows moved"
    if field == "warnings":
        return f"{len(old)} -> {len(new)} warning dicts"
    return f"{old} -> {new}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("key", help="golden key to re-capture, e.g. photo/drone_render.png")
    ap.add_argument("--pre-change-tree", default=None,
                    help="checkout of the engine BEFORE the change; the airtight machine check")
    ap.add_argument("--control", action="append", default=[],
                    help="key the change under review must NOT alter; weaker, same-lane only")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would move and write nothing")
    ap.add_argument("--force", action="store_true", help="skip the machine check (see docstring)")
    args = ap.parse_args()

    raw = GOLDEN_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)

    if args.key not in data:
        print(f"ERROR: {args.key!r} is not a key in {GOLDEN_PATH.name}.")
        print("       Known keys: " + ", ".join(repr(k) for k in data))
        return 2

    if not args.control and not args.pre_change_tree and not args.force and not args.dry_run:
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
        pre = _snapshot_in_tree(tree, args.key, GOLDEN_PATH.parent / "_recap_pre.json")
        (GOLDEN_PATH.parent / "_recap_pre.json").unlink(missing_ok=True)
        (GOLDEN_PATH.parent / "_recap_pre.py").unlink(missing_ok=True)
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
            print(f"ERROR: control key {ck!r} is not in {GOLDEN_PATH.name}.")
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
        print(f"  {f}: {_describe(f, old.get(f), new.get(f))}")

    if args.dry_run:
        print(f"\ndry run: {args.key} WOULD move in {', '.join(moved)}; nothing written.")
        return 0

    data[args.key] = new
    GOLDEN_PATH.write_text(json.dumps(data, indent=INDENT), encoding="utf-8")

    untouched = all(json.loads(raw)[k] == data[k] for k in data if k != args.key)
    print(f"\nwrote {GOLDEN_PATH}")
    print(f"every other key untouched: {untouched}")
    if not untouched:
        print("ERROR: other keys moved — this should be impossible. Revert and investigate.")
        return 1
    print("\nNow update the docstring in tests/test_photo_lane_byte_identical.py with a")
    print("dated note saying WHICH key moved and WHY — the file's own convention.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
