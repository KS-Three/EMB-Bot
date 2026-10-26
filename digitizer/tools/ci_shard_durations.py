"""Regenerate tests/.shard_durations.json (per-FILE seconds) from JUnit XML.

The shard plugin (tests/_ci_shard.py) balances files by these numbers. Stale
numbers cost balance, never correctness: every collected test still runs in
exactly one shard, and a file missing from the map weighs the 75th percentile
of the recorded ones (the median until W3-05), and more than 5% of files
missing is a warning in every shard's log.

Feed it the `digitizer-shard-*` artifacts of the LATEST GREEN MAIN run (a red
run lacks the time of every test it did not finish) or a local `--junitxml`
-- relative weights are what matter:

    gh run list --branch main --workflow CI --status success --limit 1 --json databaseId
    gh run download <id> --pattern 'digitizer-shard-*' --dir shards
    python tools/ci_shard_durations.py shards/*/junit.xml

It rewrites the map against the CURRENT file list (tests/test_*.py): entries
for files that are gone drop out, files the JUnit did not time stay out (they
weigh p75 until the next refresh). It prints the shard plan BEFORE and AFTER
with the predicted maximum shard -- both scored on the fresh timings, so
"before" is how long the old map's assignment would really take now -- and
warns when more than 5% of the files are unmeasured.

    python tools/ci_shard_durations.py --plan     # print the plan, change nothing
"""

import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "tests" / ".shard_durations.json"
SHARDS = 6          # the matrix in .github/workflows/python-package-conda.yml
WORKERS = 4         # `-n auto` on a 4-core runner: a shard's wall time ~ its load / 4


def file_of(classname, root=ROOT):
    # "tests.test_foo.TestBar" -> "tests/test_foo.py": the longest dotted
    # prefix that names a real file.
    parts = classname.split(".")
    for i in range(len(parts), 0, -1):
        rel = "/".join(parts[:i]) + ".py"
        if (root / rel).exists():
            return rel
    return None


def current_files(root=ROOT):
    """The test files pytest collects: tests/test_*.py, as _ci_shard names them."""
    return {p.relative_to(root).as_posix() for p in (root / "tests").glob("test_*.py")}


def plan(files, n, assign_with, truth):
    """Assign `files` to `n` shards by `assign_with` (a duration map, as
    tests/_ci_shard.py would) and score each shard by `truth`'s weights.
    {"loads": [seconds per shard], "max": the slowest, "mean": ...}."""
    from tests import _ci_shard
    shard_of = _ci_shard.assign(files, n, assign_with)
    truth_w = _ci_shard.weights(files, truth)
    loads = [0.0] * n
    for f, i in shard_of.items():
        loads[i] += truth_w[f]
    return {"loads": loads, "max": max(loads), "mean": sum(loads) / n}


def describe(label, p, n, workers=WORKERS):
    worst = p["loads"].index(p["max"]) + 1
    per = "  ".join(f"{i + 1}:{x / 60:.1f}" for i, x in enumerate(p["loads"]))
    return (f"  {label:<7} test-minutes per shard  {per}\n"
            f"          max shard {worst} = {p['max'] / 60:.1f} test-min "
            f"(~{p['max'] / 60 / workers:.1f} min wall at {workers} workers), "
            f"mean {p['mean'] / 60:.1f}, max/mean {p['max'] / p['mean']:.2f}")


def report(files, before, after, n):
    """The shard plan under the old map and the new one, both on the new timings."""
    from tests import _ci_shard
    out = [f"shard plan: {len(files)} files, {n} shards (scored on the fresh timings)"]
    for label, durations in (("before", before), ("after", after)):
        out.append(describe(label, plan(files, n, durations, after), n))
    missing = sorted(f for f in files if f not in after)
    out.append(f"  {len(missing)} of {len(files)} files unmeasured -> weigh "
               f"{_ci_shard.unknown_weight(after, files):.1f} s each (p75)")
    warning = _ci_shard.unmeasured_warning(after, files)
    if warning:
        out.append("WARNING: " + warning)
    return "\n".join(out)


def main(paths, root=ROOT, n=SHARDS):
    out = root / "tests" / ".shard_durations.json"
    files = current_files(root)
    before = json.loads(out.read_text()) if out.exists() else {}
    if paths == ["--plan"]:
        print(report(files, before, before, n))
        return 0
    totals = defaultdict(float)
    for p in paths:
        for case in ET.parse(p).getroot().iter("testcase"):
            f = file_of(case.get("classname", ""), root)
            if f:
                totals[f] += float(case.get("time") or 0)
    after = {f: round(s, 2) for f, s in sorted(totals.items())}
    out.write_text(json.dumps(after, indent=0) + "\n")
    print(f"{len(after)} files, {sum(after.values()) / 60:.1f} test-minutes -> {out}")
    print(report(files, before, after, n))
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    raise SystemExit(main(sys.argv[1:]))
