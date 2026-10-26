"""default_path_diff: did this change move what the Studio sews by default?

Digitizes a FIXED set of jobs through the Studio's own request
(`tools.pro_pair.request(width, garment)`, which wraps `fremont_triage.studio_request`
and swaps the garment) in two trees -- the merge-base of the branch and the
branch itself -- and reports, per job, the md5 of the plan's machine stream, the
md5 of the DST, and the stitch, colour-change and DST-trim counts. A job whose
five numbers match is *identical*; any other is `DIFFERS`.

WHAT IT IS FOR. The md5 pins in the suite say "OFF still equals main" against a
hash somebody captured on one machine, and 77 test files carry them. This runs
base and head on the SAME runner in the same minute, so a platform difference
cannot be mistaken for a regression and nothing is hard-coded. It SUPPLEMENTS
the pins -- it does not replace them (a pin also catches a drift that landed in
main between two PRs) -- and it is advisory: a moved default is information,
and a flip PR is supposed to move it. CI runs it on pull requests that touch
digitizer/ as a `continue-on-error` job that is not a required check.

  python -m tools.default_path_diff --base-ref origin/main            # merge-base vs this tree
  python -m tools.default_path_diff --base-tree DIR --head-tree DIR   # two trees (a `digitizer/` each)
      [--set KEY=JSON ...]   head only: a PipelineConfig field, a Studio request key
                             (`garment_rgb`), or any other key, which goes to cfg.extra;
                             `--set some_flag=false` proves "OFF equals base"
                             without a hard-coded hash
      [--only NAME,NAME] [--json OUT] [--md OUT] [--procs N] [--fail-on-diff]

THE JOBS (JOBS below): the committed fixtures testdata/logo_whitebg.png,
logo_alpha.png and ribbon_curve.png on hat_front at 60 mm, and
testdata/becker_marine_logo.png at 60 mm on left_chest and on hat_front (100 mm
takes ~3 minutes a digitize). The testdata/reference JPGs are the pro's previews
of his own stitch files and are never an input. Fixtures are read from the HEAD
tree for both sides, so a difference is the engine and not the picture.

REPEATABILITY. A comparison of two trees is only worth reading if one tree
agrees with itself. The three small jobs digitize head TWICE, in separate
processes; a job whose two runs differ is dropped from the verdict, marked
`unstable`, and listed. The runner sets OPENCV_IPP=avx2 and one thread per
native pool, as tests/conftest.py does, so the md5s do not follow the host's
SIMD class.

EXIT STATUS. 0 when the jobs ran, whatever they found. 1 when a job crashed or
timed out (the table would be lying), or with --fail-on-diff when one DIFFERS.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
REPO_ROOT = DIGITIZER.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

#: what two runs are compared on
FIELDS = ("plan_md5", "dst_md5", "stitches", "color_changes", "dst_trims")
#: seconds one digitize may take before it is an error (Becker at 60 mm is the slow one)
TIMEOUT_S = 1500
WIDTH_MM = 60.0

#: as tests/conftest.py and the CI shard step set them; a shell may override
RUNNER_ENV = {"OPENCV_IPP": "avx2", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
              "MKL_NUM_THREADS": "1", "OPENCV_FOR_THREADS_NUM": "1"}


@dataclass(frozen=True)
class Job:
    name: str
    art: str                    # relative to digitizer/, read from the head tree
    width: float
    garment: str
    stable_check: bool = False  # digitize head twice and drop the job if the runs differ


JOBS = (
    Job("becker_marine.60mm.left_chest", "testdata/becker_marine_logo.png", WIDTH_MM, "left_chest"),
    Job("becker_marine.60mm.hat_front", "testdata/becker_marine_logo.png", WIDTH_MM, "hat_front"),
    Job("logo_whitebg.60mm.hat_front", "testdata/logo_whitebg.png", WIDTH_MM, "hat_front", True),
    Job("logo_alpha.60mm.hat_front", "testdata/logo_alpha.png", WIDTH_MM, "hat_front", True),
    Job("ribbon_curve.60mm.hat_front", "testdata/ribbon_curve.png", WIDTH_MM, "hat_front", True),
)

#: Runs inside ONE tree (cwd = its digitizer/), so it imports THAT tree's
#: engine and THAT tree's Studio request -- the merge-base may not have this file.
#: argv[1] = {"art": absolute path, "width": mm, "garment": id, "sets": {...}}.
WORKER = r'''
import hashlib, json, os, sys, tempfile, time
spec = json.loads(sys.argv[1])
from tools import pro_pair
from digitizer_service.app import _CONFIG_FIELDS, _decode, _parse_config
from digitizer_core import PipelineConfig, export, stitches
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
import pystitch

data = open(spec["art"], "rb").read()
sets = spec["sets"]
in_request = {k: v for k, v in sets.items() if k in _CONFIG_FIELDS}
cfg = PipelineConfig(**_parse_config(json.dumps(
    pro_pair.request(spec["width"], spec["garment"], in_request))))
cfg.extra.update({k: v for k, v in sets.items() if k not in _CONFIG_FIELDS})
t = time.time()
gen = build_generation(_decode(data), cfg, exif_source=data)
result = finish_generation(gen.fork(), cfg)
plan = plan_stitches(result, cfg)
stream = [(c, None if p is None else (round(p[0], 6), round(p[1], 6)))
          for c, p in stitches.iter_machine_commands(plan)]
dst = export.export_dst(plan)
fd, path = tempfile.mkstemp(suffix=".dst")
os.close(fd)
try:
    open(path, "wb").write(dst)
    pattern = pystitch.read(path)
    trims = sum(1 for *_xy, c in pattern.stitches if (c & pystitch.COMMAND_MASK) == pystitch.TRIM)
finally:
    os.unlink(path)
print("RESULT " + json.dumps({
    "plan_md5": hashlib.md5(repr(stream).encode()).hexdigest(),
    "dst_md5": hashlib.md5(dst).hexdigest(),
    "stitches": plan.stats.stitch_count, "color_changes": plan.stats.color_changes,
    "dst_trims": trims, "secs": round(time.time() - t, 1), "sets": sets}))
'''

#: the merge-base sha `merge_base_tree` last archived (for the report and the tests)
last_merge_base = ""


# ------------------------------------------------------------------ trees
def _git(repo: Path, *args: str, binary: bool = False):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True,
                          text=not binary)
    return done.stdout if binary else done.stdout.strip()


@contextlib.contextmanager
def merge_base_tree(ref: str, repo: Path | None = None):
    """`digitizer/` as it was at the merge-base of HEAD and `ref`, in a temp dir
    that is removed on exit. `ref` that shares no history with HEAD (a shallow
    CI clone that did not fetch it) is used as the commit itself."""
    global last_merge_base
    repo = Path(repo or REPO_ROOT)
    try:
        sha = _git(repo, "merge-base", "HEAD", ref)
    except subprocess.CalledProcessError:
        sha = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    last_merge_base = sha
    tmp = Path(tempfile.mkdtemp(prefix="default_path_base_"))
    try:
        blob = _git(repo, "archive", "--format=tar", sha, "digitizer", binary=True)
        with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
            tar.extractall(tmp, filter="data")
        yield tmp / "digitizer"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ the runs
def run_one(tree, job: Job, sets: dict, worker_code: str = WORKER, art: str | None = None,
            timeout: float = TIMEOUT_S) -> dict:
    """One digitize in its own process, cwd = `tree`. {"plan_md5": ..., ...} or {"error": ...}."""
    spec = {"art": art or str(Path(tree) / job.art), "width": job.width,
            "garment": job.garment, "sets": sets}
    env = {**RUNNER_ENV, **os.environ}
    try:
        done = subprocess.run([sys.executable, "-c", worker_code, json.dumps(spec)], cwd=str(tree),
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"error": f"timed out after {timeout:.0f} s"}
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    if done.returncode != 0 or not lines:
        tail = (done.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        return {"error": f"exit {done.returncode}: {tail}"[:400]}
    return json.loads(lines[-1][len("RESULT "):])


def _differing(a: dict, b: dict) -> list[str]:
    return [f for f in FIELDS if a.get(f) != b.get(f)]


def run_jobs(base_tree, head_tree, jobs, sets: dict, worker_code: str = WORKER,
             procs: int | None = None, timeout: float = TIMEOUT_S) -> list[dict]:
    """Every job on base (no --set) and head (--set), jobs flagged `stable_check` on
    head twice, in parallel processes. One row per job, in `jobs` order."""
    head_tree = Path(head_tree)
    tasks = []                                   # (key, tree, job, sets)
    for job in jobs:
        art = str(head_tree / job.art)
        tasks.append((job.name, "base", base_tree, job, {}, art))
        tasks.append((job.name, "head", head_tree, job, sets, art))
        if job.stable_check:
            tasks.append((job.name, "head2", head_tree, job, sets, art))
    # the slow jobs first, so the pool does not end waiting on one of them
    order = sorted(range(len(tasks)), key=lambda i: -_cost(tasks[i][3]))
    out: dict = {}
    with ThreadPoolExecutor(max_workers=procs or os.cpu_count() or 2) as pool:
        futures = {i: pool.submit(run_one, tasks[i][2], tasks[i][3], tasks[i][4], worker_code,
                                  tasks[i][5], timeout) for i in order}
        for i, fut in futures.items():
            out[(tasks[i][0], tasks[i][1])] = fut.result()
    rows = []
    for job in jobs:
        base, head, head2 = (out.get((job.name, k)) for k in ("base", "head", "head2"))
        row = {"name": job.name, "art": job.art, "width": job.width, "garment": job.garment,
               "base": base, "head": head, "differs": [], "repeat_differs": [],
               "repeatable": None, "error": ""}
        errors = [f"{k}: {r['error']}" for k, r in (("base", base), ("head", head), ("repeat", head2))
                  if r and "error" in r]
        if errors:
            row["status"], row["error"] = "error", "; ".join(errors)
        else:
            if head2 is not None:
                row["repeat_differs"] = _differing(head, head2)
                row["repeatable"] = not row["repeat_differs"]
            if row["repeatable"] is False:
                row["status"] = "unstable"
            else:
                row["differs"] = _differing(base, head)
                row["status"] = "DIFFERS" if row["differs"] else "identical"
        rows.append(row)
    return rows


def _cost(job: Job) -> float:
    return 1.0 + ("becker" in job.art) * 3.0


def summarize(rows: list[dict]) -> dict:
    return {"total": len(rows),
            "identical": sum(r["status"] == "identical" for r in rows),
            "differs": sum(r["status"] == "DIFFERS" for r in rows),
            "dropped": [r["name"] for r in rows if r["status"] == "unstable"],
            "errors": [r["name"] for r in rows if r["status"] == "error"]}


# ------------------------------------------------------------------ output
def _cell(row: dict, field: str, short: bool = False) -> str:
    b, h = row["base"], row["head"]
    if not b or not h or "error" in b or "error" in h:
        return "-"
    fmt = (lambda v: str(v)[:12]) if short else str
    return fmt(h[field]) if b[field] == h[field] else f"{fmt(b[field])} -> {fmt(h[field])}"


def markdown(rows: list[dict], meta: dict) -> str:
    s = summarize(rows)
    sets = ", ".join(f"{k}={json.dumps(v)}" for k, v in meta.get("sets", {}).items()) or "none"
    out = ["## Default-path diff (advisory)", "",
           f"Merge-base `{meta['base']}` against head `{meta['head']}`, same runner, the Studio's "
           f"own request. `--set` on head: {sets}.", "",
           f"**{s['identical']} of {s['total']} jobs identical**"
           + (f", **{s['differs']} DIFFER**" if s["differs"] else "")
           + (f", dropped as unrepeatable: {', '.join(s['dropped'])}" if s["dropped"] else "")
           + (f", **errors: {', '.join(s['errors'])}**" if s["errors"] else "") + ".", "",
           "| job | verdict | plan md5 | DST md5 | stitches | colour changes | DST trims | repeat | secs |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        rep = {True: "same", False: "DIFFERS", None: "-"}[r["repeatable"]]
        secs = "-" if not r["head"] or "error" in r["head"] else r["head"].get("secs", "-")
        verdict = r["status"] + (f" ({', '.join(r['differs'])})" if r["differs"] else "") \
            + (f": {r['error']}" if r["error"] else "")
        out.append(f"| {r['name']} | {verdict} | {_cell(r, 'plan_md5', True)} | "
                   f"{_cell(r, 'dst_md5', True)} | {_cell(r, 'stitches')} | "
                   f"{_cell(r, 'color_changes')} | {_cell(r, 'dst_trims')} | {rep} | {secs} |")
    out += ["", "This job SUPPLEMENTS the suite's md5 pins; it does not replace them, and it is "
                "not a required check. A flip PR is meant to move these numbers: read the verdict "
                "against what the PR says it changes."]
    return "\n".join(out) + "\n"


def parse_sets(items) -> dict:
    out = {}
    for item in items:
        key, _, raw = item.partition("=")
        try:
            out[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            out[key.strip()] = raw
    return out


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.default_path_diff", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-ref", help="compare against the merge-base of HEAD and this ref")
    ap.add_argument("--base-tree", type=Path, help="digitizer/ of the base (instead of --base-ref)")
    ap.add_argument("--head-tree", type=Path, default=DIGITIZER, help="digitizer/ to test (default: this one)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=JSON",
                    help="set on the head runs only (repeatable)")
    ap.add_argument("--only", help="comma-separated job names to run")
    ap.add_argument("--json", type=Path, help="write the full report here")
    ap.add_argument("--md", type=Path, help="write the markdown table here ($GITHUB_STEP_SUMMARY)")
    ap.add_argument("--procs", type=int, help="parallel digitizes (default: the CPU count)")
    ap.add_argument("--timeout", type=float, default=TIMEOUT_S, help="seconds one digitize may take")
    ap.add_argument("--fail-on-diff", action="store_true", help="exit 1 when a job DIFFERS")
    args = ap.parse_args(argv)
    if bool(args.base_ref) == bool(args.base_tree):
        ap.error("give exactly one of --base-ref and --base-tree")
    return args


def main(argv=None, worker_code: str = WORKER, jobs=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    args = parse_args(argv)
    jobs = list(jobs if jobs is not None else JOBS)
    if args.only:
        wanted = set(args.only.split(","))
        jobs = [j for j in jobs if j.name in wanted]
        if not jobs:
            print(f"--only {args.only}: no such job; the jobs are {[j.name for j in JOBS]}")
            return 2
    sets = parse_sets(args.set)
    with contextlib.ExitStack() as stack:
        if args.base_ref:
            base = stack.enter_context(merge_base_tree(args.base_ref))
            base_label = last_merge_base[:12]
        else:
            base, base_label = args.base_tree, str(args.base_tree)
        try:
            head_label = _git(args.head_tree, "rev-parse", "--short=12", "HEAD")
        except (subprocess.CalledProcessError, OSError):
            head_label = str(args.head_tree)
        rows = run_jobs(base, args.head_tree, jobs, sets, worker_code, args.procs, args.timeout)
    meta = {"base": base_label, "head": head_label, "sets": sets}
    summary = summarize(rows)
    table = markdown(rows, meta)
    print(table)
    if args.json:
        args.json.write_text(json.dumps({**meta, "summary": summary, "jobs": rows}, indent=1) + "\n",
                             encoding="utf-8")
    if args.md:
        args.md.write_text(table, encoding="utf-8")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        if summary["differs"]:
            print(f"::warning title=Default path moved::{summary['differs']} of {summary['total']} "
                  f"jobs differ from the merge-base (advisory; see the job summary)")
        if summary["errors"] or summary["dropped"]:
            print(f"::warning title=Default-path diff incomplete::errors={summary['errors']} "
                  f"dropped={summary['dropped']}")
    if summary["errors"]:
        return 1
    return 1 if args.fail_on_diff and summary["differs"] else 0


if __name__ == "__main__":
    sys.exit(main())
