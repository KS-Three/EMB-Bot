"""The `digitizer` aggregator's proof that sharding dropped nothing.

Reads the manifests each CI shard wrote (tests/_ci_shard.py) and fails unless:
  - there is exactly one manifest per shard 1..n,
  - every shard collected the identical list (same tree, same deselects),
  - the shards' selections are pairwise disjoint, and
  - together they are exactly that collected list.
A shard's own exit code already says its selection passed; this says the
selections add up to the whole suite. Stdlib only -- the aggregator installs
nothing.

WIRE SCOPE (a PR touching neither digitizer/ nor .github/; Kent's call
2026-10-08): shard 1 runs only tools/ci_wire_tests.py's subset as shard
1-of-1 and shards 2..n write a ``{"scope": "wire", "skipped": true}``
marker. Then every manifest must say wire, shards 1..n must all be present,
and shard 1 must have run its whole non-empty collected list. A mix of
scopes fails -- the shards disagreed about what the PR touched.

    python digitizer/tools/ci_shard_check.py <dir-of-manifests>
"""

import json
import sys
from collections import Counter
from pathlib import Path


def check_wire(manifests):
    errors = []
    if any(m.get("scope") != "wire" for m in manifests):
        return ["shards disagree on scope: "
                + str(sorted((m["shard"], m.get("scope", "full")) for m in manifests))]
    ran = [m for m in manifests if not m.get("skipped")]
    skipped = [m for m in manifests if m.get("skipped")]
    if len(ran) != 1 or ran[0]["shard"] != 1:
        return [f"wire scope wants exactly shard 1 to run, got {[m['shard'] for m in ran]}"]
    n = skipped[0]["of"] if skipped else 1
    shards = sorted(m["shard"] for m in manifests)
    if shards != list(range(1, n + 1)):
        errors.append(f"expected one manifest per shard 1..{n}, got {shards}")
    m = ran[0]
    if not m["collected"]:
        errors.append("wire scope collected no tests")
    if sorted(m["selected"]) != sorted(m["collected"]):
        errors.append("wire shard did not run its whole collected list")
    return errors


def check(manifests):
    errors = []
    if not manifests:
        return ["no shard manifests found"]
    if any(m.get("scope") == "wire" for m in manifests):
        return check_wire(manifests)
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
        print(f"shard {m['shard']}/{m['of']}: "
              f"{'skipped' if m.get('skipped') else len(m['selected'])} "
              f"tests, scope {m.get('scope', 'full')}")
    errors = check(manifests)
    if errors:
        print("\n".join("FAIL: " + e for e in errors))
        return 1
    if any(m.get("scope") == "wire" for m in manifests):
        ran = next(m for m in manifests if not m.get("skipped"))
        print(f"OK (wire scope): {len(ran['collected'])} wire tests ran. This "
              f"PR touches neither digitizer/ nor .github/; main runs the "
              f"full suite on merge.")
        return 0
    print(f"OK: {len(manifests[0]['collected'])} collected, every one in "
          f"exactly one shard")
    return 0


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    sys.exit(main(sys.argv))
