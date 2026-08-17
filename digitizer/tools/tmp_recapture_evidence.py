"""TEMPORARY — evidence pack for the enthusiast_logo golden re-capture.

Runs on the ubuntu-latest CI runner (the environment whose CI must go green;
goldens are never captured on Windows — ROADMAP standing item). Snapshots
`photo/enthusiast_logo.png` in three trees:

  PRE   = main before the PR #157 merge (0870c76). Must equal the committed
          golden byte-for-byte — that is the machine proof: this runner + old
          engine reproduces the golden, so whatever moves afterwards is the
          engine, not the machine.
  HEAD  = this checkout (main + nothing else). The value the re-capture will
          write. CI reads 2351 here against the golden's 2363.
  SATIN = claude/satin-gate-attribution tip (2729ea5) = HEAD + the promotion
          path (45d817a). SATIN == HEAD proves the promotion path is
          output-neutral on this fixture, i.e. the elongation floor keeps the
          benchmark star `Sff37b029` out, exactly as that commit's message and
          docs/satin-gate-attribution-2026-08-16.md §5 designed.

Also renders PRE and HEAD to per-stage debug PNGs for the legibility check the
2026-08-14 sanction (commit 0e84f0b) used.

Deleted in the same PR that commits the golden. Not imported by anything.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIGI = HERE.parent

KEY = "photo/enthusiast_logo.png"
PRE_TREE = Path("/tmp/pre/digitizer")
SATIN_TREE = Path("/tmp/satin/digitizer")
RENDER_OUT = Path("/tmp/renders")

# Same subprocess pattern as tools/recapture_flat_lane_key.py: the other
# tree's digitizer_core must be imported cleanly, not fight this process's.
SNAP_RUNNER = (
    "import json, sys; sys.path.insert(0, sys.argv[1]); "
    "from tests.test_flat_lane_byte_identical import _snapshot; "
    "json.dump(_snapshot(sys.argv[2]), open(sys.argv[3], 'w'))"
)
RENDER_RUNNER = (
    "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); "
    "from digitizer_core import PipelineConfig; "
    "from digitizer_core.pipeline import digitize; "
    "digitize(Path(sys.argv[1]) / 'testdata' / sys.argv[2], "
    "PipelineConfig(target_width_mm=80.0, debug_dir=Path(sys.argv[3])))"
)


def snap(tree: Path) -> dict:
    out = tree / "_tmp_snap.json"
    subprocess.run([sys.executable, "-c", SNAP_RUNNER, str(tree), KEY, str(out)],
                   check=True, cwd=str(tree))
    data = json.loads(out.read_text())
    out.unlink()
    return data


def render(tree: Path, tag: str) -> None:
    try:
        subprocess.run([sys.executable, "-c", RENDER_RUNNER, str(tree), KEY,
                        str(RENDER_OUT / tag)], check=True, cwd=str(tree))
    except subprocess.CalledProcessError as exc:  # evidence, not a gate
        print(f"render {tag}: FAILED ({exc}) — non-fatal, capture unaffected")


def moved_fields(a: dict, b: dict) -> list[str]:
    return [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


def main() -> int:
    golden = json.loads(
        (DIGI / "testdata" / "flat_lane_golden.json").read_text(encoding="utf-8")
    )[KEY]

    pre = snap(PRE_TREE)
    head = snap(DIGI)
    satin = snap(SATIN_TREE)

    print("== attribution ==")
    print(f"golden stitch_count: {golden['stitch_count']}")
    print(f"PRE    stitch_count: {pre['stitch_count']}; fields vs golden: "
          f"{moved_fields(golden, pre) or 'NONE — machine vouched'}")
    print(f"HEAD   stitch_count: {head['stitch_count']}; fields vs golden: "
          f"{moved_fields(golden, head)}")
    print(f"SATIN  stitch_count: {satin['stitch_count']}; fields vs HEAD: "
          f"{moved_fields(head, satin) or 'NONE — promotion path output-neutral on this fixture'}")

    print("== field detail, golden -> HEAD ==")
    print(f"shape_ids identical: {golden['shape_ids'] == head['shape_ids']}")
    print(f"warnings  identical: {golden['warnings'] == head['warnings']}")
    area_moves = [(a, b) for a, b in zip(golden["areas_mm2"], head["areas_mm2"])
                  if a != b]
    print(f"areas_mm2: {len(area_moves)} of {len(golden['areas_mm2'])} moved: "
          f"{area_moves}")
    zipped_diff = sum(1 for o, n in zip(golden["stitch_coords"], head["stitch_coords"])
                      if o != n)
    print(f"stitch_coords rows: {len(golden['stitch_coords'])} -> "
          f"{len(head['stitch_coords'])}; {zipped_diff} of the zipped prefix differ")
    kinds = lambda s: sorted({row[2] for row in s["stitch_coords"]})  # noqa: E731
    print(f"run kinds: golden {kinds(golden)} -> head {kinds(head)}")

    print("== renders ==")
    render(PRE_TREE, "pre")
    render(DIGI, "head")

    if pre != golden:
        print("FATAL: PRE does not reproduce the golden on this runner — the "
              "machine cannot vouch for itself; a capture here would be noise.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
