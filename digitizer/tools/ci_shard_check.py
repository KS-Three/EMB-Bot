"""The `digitizer` aggregator's proof that sharding dropped nothing.

Reads the manifests each CI shard wrote (tests/_ci_shard.py) and fails unless:
  - there is exactly one manifest per shard 1..n,
  - every shard collected the identical list (same tree, same deselects),
  - the shards' selections are pairwise disjoint, and
  - together they are exactly that collected list.
A shard's own exit code already says its selection passed; this says the
selections add up to the whole suite. Stdlib only -- the aggregator installs
nothing.

    python digitizer/tools/ci_shard_check.py <dir-of-manifests>
"""

import json
import sys
from collections import Counter
from pathlib import Path


def check(manifests):
    errors = []
    if not manifests:
        return ["no shard manifests found"]
    n = manifests[0]["of"]
    shards = sorted(m["shard"] for m in manifests)
    if shards != list(range(1, n + 1)) or any(m["of"] != n for m in manifests):
        errors.append(f"expected one manifest per shard 1..{n}, got {shards}")
    full = manifests[0]["collected"]
    for m in manifests:
        if m["collected"] != full:
            errors.append(f"shard {m['shard']} collected a different list "
                          f"({len(m['collected'])} vs {len(full)})")
    seen = Counter(t for m in manifests for t in m["selected"])
    dup = [t for t, c in seen.items() if c > 1]
    missing = sorted(set(full) - set(seen))
    extra = sorted(set(seen) - set(full))
    for label, ids in (("in more than one shard", dup),
                       ("in no shard", missing), ("not collected", extra)):
        if ids:
            errors.append(f"{len(ids)} test(s) {label}, e.g. {ids[:3]}")
    return errors


def main(argv):
    manifests = [json.loads(p.read_text())
                 for p in sorted(Path(argv[1]).rglob("*.json"))]
    for m in sorted(manifests, key=lambda m: m["shard"]):
        print(f"shard {m['shard']}/{m['of']}: {len(m['selected'])} tests")
    errors = check(manifests)
    if errors:
        print("\n".join("FAIL: " + e for e in errors))
        return 1
    print(f"OK: {len(manifests[0]['collected'])} collected, every one in "
          f"exactly one shard")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
