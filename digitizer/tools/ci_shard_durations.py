"""Regenerate tests/.shard_durations.json (per-FILE seconds) from JUnit XML.

The shard plugin (tests/_ci_shard.py) balances files by these numbers. Stale
numbers cost balance, never correctness: every collected test still runs in
exactly one shard, and a file missing from the map gets the median.

Feed it the `junit-*` artifacts of one green CI run (download them from the
run page) or a local `--junitxml` -- relative weights are what matter:

    python tools/ci_shard_durations.py shard-1.xml shard-2.xml ...
"""

import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / ".shard_durations.json"


def file_of(classname):
    # "tests.test_foo.TestBar" -> "tests/test_foo.py": the longest dotted
    # prefix that names a real file.
    parts = classname.split(".")
    for i in range(len(parts), 0, -1):
        rel = "/".join(parts[:i]) + ".py"
        if (ROOT / rel).exists():
            return rel
    return None


def main(paths):
    totals = defaultdict(float)
    for p in paths:
        for case in ET.parse(p).getroot().iter("testcase"):
            f = file_of(case.get("classname", ""))
            if f:
                totals[f] += float(case.get("time") or 0)
    OUT.write_text(json.dumps({f: round(s, 2) for f, s in sorted(totals.items())},
                              indent=0) + "\n")
    print(f"{len(totals)} files, {sum(totals.values()) / 60:.1f} test-minutes -> {OUT}")


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    main(sys.argv[1:])
