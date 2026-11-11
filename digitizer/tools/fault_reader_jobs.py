"""Run a fault reader's worker on one stored design: a pro job or a corpus row.

    items:  L_<slug>  pro job, stored design `<pro_run>/<slug>.json`, art from
                      `pro_baseline.JOBS` (resolved INSIDE the worker, by the tree)
            C_<slug>  corpus row, stored design `<corpus_run>/<slug>.json`, art
                      `photo_corpus.photo_path(<photos>, slug)`

Every fault reader re-runs the job at `--tree` (the checkout the kit was built
on) and REFUSES the item unless the re-run's stitches equal the stored
design's, so its rasters belong to the design Kent marked. The worker is the
reader's own script (run with `python -c`, cwd = the tree, so it imports the
TREE's `digitizer_core`, not this lane's); this module only builds its spec,
runs it and enforces the refusal. Folded out of the sitting-2 driver
`docs/defect-marks-2026-11-11/run_reader_corpus.py` (PR #1390), which patched
one line of the letter reader's worker to read corpus art.

A worker reads `spec["art"]` and falls back to `pro_baseline` when it is
None, writes `spec["out"]` (JSON with at least `same_stitches`,
`stored_sha`, `rerun_sha`), and whatever rasters the reader needs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ENV = {"OPENCV_IPP": "avx2", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
       "MKL_NUM_THREADS": "1", "OPENCV_FOR_THREADS_NUM": "1", "PYTHONIOENCODING": "utf-8",
       "PYTHONDONTWRITEBYTECODE": "1"}


class WorkerFailed(RuntimeError):
    """The worker exited non-zero (last lines of its stderr in the message)."""


class Refused(RuntimeError):
    """The re-run's stitches differ from the stored design's."""


def split_item(iid: str) -> tuple[str, str]:
    """`L_bridge_hat` -> ("L", "bridge_hat"). Only L_ and C_ items have a job."""
    kind, sep, slug = iid.partition("_")
    if not sep or kind not in ("L", "C") or not slug:
        raise ValueError(f"{iid!r}: a fault reader runs on L_<pro slug> or C_<corpus slug> items")
    return kind, slug


def job_paths(iid: str, pro_run: Path | None, corpus_run: Path | None,
              photos: Path | None) -> tuple[Path, Path | None]:
    """-> (stored design json, art path or None = resolve from pro_baseline in the worker)."""
    kind, slug = split_item(iid)
    if kind == "L":
        if pro_run is None:
            raise ValueError(f"{iid}: --pro-run is required for pro jobs")
        return Path(pro_run) / f"{slug}.json", None
    if corpus_run is None or photos is None:
        raise ValueError(f"{iid}: --corpus-run and --photos are required for corpus rows")
    from tools import photo_corpus as pc
    art = pc.photo_path(Path(photos), slug)
    if art is None:
        raise ValueError(f"{iid}: no artwork for {slug!r} under {photos}")
    return Path(corpus_run) / f"{slug}.json", art


def tree_sha(tree: Path) -> str | None:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tree), capture_output=True, text=True)
    return r.stdout.strip() or None


def run_worker(worker: str, spec: dict, tree: Path, timeout: float = 1800.0) -> dict:
    """Run `worker` on `spec` in `tree`; -> its JSON report. Raises
    `WorkerFailed` on a crash and `Refused` when the stitches differ. The
    lane's PYTHONPATH is dropped so the worker imports the tree's code."""
    env = {**os.environ, **ENV}
    env.pop("PYTHONPATH", None)
    proc = subprocess.run([sys.executable, "-c", worker, json.dumps(spec)], cwd=str(tree), env=env,
                          capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise WorkerFailed("\n".join(proc.stderr.strip().splitlines()[-6:]))
    out = Path(spec["out"])
    rep = json.loads(out.read_text(encoding="utf-8"))
    out.unlink()
    if not rep.get("same_stitches"):
        raise Refused(f"re-run stitches {rep.get('rerun_sha')} != stored {rep.get('stored_sha')}")
    return rep


def main(argv: list[str] | None = None) -> int:
    """No command of its own: the readers run items through it."""
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=(
        "Library for the fault readers; run one of them instead: "
        "python -m tools.infill_fault_reader run ... / python -m tools.letter_fault_reader run ..."))
    ap.parse_args(argv)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
