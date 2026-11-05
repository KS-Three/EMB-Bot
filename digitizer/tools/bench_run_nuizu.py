#!/usr/bin/env python
"""Run Nuizu (Apache-2.0/MIT, a separate install) over the bench jobs at the pro's size.

    python -m tools.bench_run_nuizu --bench-dir DIR --engine nuizu [-- extra nuizu flags]

Reads `DIR/jobs.json` (written by `tools.bench_free_digitizers prep`) and the
ink-cropped art in `DIR/_art/`, runs `DIR/_tools/nuizu/venv`'s `nuizu dst -s <longest
side mm>` for each job and writes `DIR/<engine>/<slug>.dst`. Nuizu lives in its own
venv: nothing of it is imported or installed into ours, and its output is a
third-party file that stays under the gitignored `scratch_bench/`.
Extra flags after `--` are passed through (e.g. `--satin-outline --auto-angle`),
and recorded in `DIR/<engine>/manifest.json` next to the stitch counts it printed.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bench-dir", type=Path, required=True)
    ap.add_argument("--engine", default="nuizu")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    exe = a.bench_dir / "_tools" / "nuizu" / "venv" / "Scripts" / "nuizu.exe"
    if not exe.exists():
        exe = a.bench_dir / "_tools" / "nuizu" / "venv" / "bin" / "nuizu"
    jobs = json.loads((a.bench_dir / "jobs.json").read_text(encoding="utf-8"))
    out = a.bench_dir / a.engine
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    mpath = out / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    for s, j in jobs.items():
        if a.only and s not in a.only:
            continue
        cmd = [str(exe), "dst", str(a.bench_dir / "_art" / f"{s}.png"), str(out / f"{s}.dst"),
               "-s", str(j["longest_mm"]), "--preview", "none", *extra]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                           cwd=str(out), timeout=900)
        manifest[s] = {"asked_longest_mm": j["longest_mm"], "flags": extra, "returncode": r.returncode,
                       "stdout_tail": r.stdout.strip().splitlines()[-4:], "stderr_tail": r.stderr.strip().splitlines()[-3:]}
        print(s, r.returncode, flush=True)
    mpath.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
