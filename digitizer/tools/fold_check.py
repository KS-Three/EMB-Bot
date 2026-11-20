#!/usr/bin/env python
"""The byte-identical proof every flag-fold PR carries (docs/flag-audit-2026-11-19.md).

A fold (delete the `if cfg.x:` branch of a flag that is ON) or a delete (of one that is OFF)
must move no stitch anywhere. This digitizes the SAME 44 jobs `tools.flag_sweep` sweeps (the 18
tripwire placements + the 26 corpus fixtures, via `flag_sweep.population`) at the DEFAULT config
and writes `{job: md5 of the stitch stream}`; `--compare` then names every job that differs.

    # on origin/main (a scratch worktree) and on the branch, same machine:
    python -m tools.fold_check --out main.json
    python -m tools.fold_check --out branch.json
    python -m tools.fold_check --compare main.json branch.json      # exit 1 on any difference

The md5 is `flag_sweep.measure_dst`'s: the STITCH/JUMP/TRIM/COLOR records as pystitch reads the
written DST. A job that cannot digitize records `"ERROR: ..."`; the same error on both sides is
not a difference, a job present on one side only is. Defaults only: the config is the engine's
own, no `--set`. Needs the same inputs as the sweep (the tripwire's pro files:
`--kent-dir`, default a scratch dir under `--out`'s folder).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")   # the test env's IPP path (tests/conftest.py)

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

SCHEMA = 1


def run_jobs(only: list[str] | None, kent_dir: Path | None) -> dict[str, str]:
    """{slug: md5 or 'ERROR: ...'} for every flag_sweep job, at default config."""
    from tools import flag_sweep as fs
    pop = fs.population(True, True, only)
    tw_slugs = [r["slug"] for r in pop if r["kind"] == "tripwire"]
    scratch = Path(tempfile.mkdtemp(prefix="fold_check_"))
    if tw_slugs:
        from tools import tripwire as tw
        tw.materialise(kent_dir or scratch / "_kent", tw_slugs)
    out: dict[str, str] = {}
    for i, row in enumerate(pop, 1):
        t = time.time()
        safe = row["slug"].replace(":", "_").replace("/", "_")
        try:
            fig, _design = fs.run_arm(fs._resolve_art(row, None), row, {}, scratch / safe, "default")
            out[row["slug"]] = fig["md5"]
        except SystemExit as e:                                # a missing file is a row, not a crash
            out[row["slug"]] = f"ERROR: SystemExit: {e}"[:300]
        except Exception as e:                                 # noqa: BLE001
            out[row["slug"]] = f"ERROR: {type(e).__name__}: {e}"[:300]
        print(f"[{i}/{len(pop)}] {row['slug']}: {out[row['slug']][:12]} ({time.time() - t:.1f} s)", flush=True)
    return out


def compare(a: dict, b: dict) -> list[str]:
    """One line per job whose md5 differs, or that only one side has; [] when identical."""
    diffs = []
    for slug in sorted(set(a) | set(b)):
        if slug not in a or slug not in b:
            diffs.append(f"{slug}: only in {'B' if slug in b else 'A'}")
        elif a[slug] != b[slug]:
            diffs.append(f"{slug}: {a[slug][:12]} -> {b[slug][:12]}")
    return diffs


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["jobs"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.fold_check", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--out", type=Path, help="digitize every job at defaults and write this JSON")
    g.add_argument("--compare", nargs=2, type=Path, metavar=("A", "B"),
                   help="print every job whose md5 differs between two --out files; exit 1 if any")
    ap.add_argument("--only", nargs="*", help="a subset of slugs (as flag_sweep --only)")
    ap.add_argument("--kent-dir", type=Path, help="where the zip's pro files are extracted")
    a = ap.parse_args(argv)
    from tools._console import utf8_console
    utf8_console()

    if a.compare:
        ja, jb = _load(a.compare[0]), _load(a.compare[1])
        diffs = compare(ja, jb)
        for line in diffs:
            print("DIFF", line)
        n = len(set(ja) | set(jb))
        print(f"fold_check: {len(diffs)} of {n} jobs differ ({a.compare[0].name} vs {a.compare[1].name})")
        return 1 if diffs else 0

    t = time.time()
    jobs = run_jobs(a.only, a.kent_dir)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"schema": SCHEMA, "jobs": jobs}, indent=1, sort_keys=True), encoding="utf-8")
    errs = [s for s, v in jobs.items() if v.startswith("ERROR")]
    print(f"fold_check: {len(jobs)} jobs, {len(errs)} errored, {time.time() - t:.0f} s -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
