"""Give each xdist worker DIFFERENT work: keep the tests that share an
expensive computation on one worker, spread everything else test by test,
heaviest first. Active only under ``--dist loadgroup`` (CI); a plain local
``pytest`` or ``-n auto`` is untouched.

WHY. Under ``--dist load`` (xdist's default) a module's tests go to whichever
worker is free, so up to four workers each build the same module fixture or
`lru_cache`d pipeline run AT THE SAME TIME. Measured 2026-10-08 on shard 1/6,
4-core box: 389 s under ``load`` against 300 s with every file on one worker
(``loadfile``) -- `test_thread_match_area_in_message.py` alone was 406 s of
test time under ``load`` and 206 s under ``loadfile``, the difference being
the same three digitizes run on several workers at once. But ``loadfile``
serializes the big files: shard 3/6 only went 506 -> 471 s because one file,
`test_duplicate_cone_layers.py` (417 s), held one worker for the whole run.
A cross-worker lock-and-pickle cache was tried first and measured ZERO wall
gain: the workers that lose the race wait exactly as long as recomputing
would have taken. The fix is to not hand them the same work in the first
place.

THE GROUPS (a test with no group is scheduled alone, as under ``load``):
  - tests that share a module-scoped fixture -- directly or through other
    fixtures -- are one group per connected set, so each such fixture is
    built once per run, on one worker, exactly as in a serial run;
  - a file with a module-level memo (``lru_cache``/``functools.cache``) is
    one group: what it shares is invisible to collection, so the whole file
    stays together, as under ``loadfile``. Splitting such a file by its
    string parameters (the fixture names its memo is keyed on) was measured
    and is WORSE -- shard 1/6 248 s -> 308 s -- because its unparametrized
    tests re-run every fixture the parametrized groups already ran;
  - everything else is ungrouped.
Scopes are then ordered heaviest-first (file duration from
``.shard_durations.json``, split by test count) so the long groups start at
t=0 instead of landing last and setting the tail. Run with
``--no-loadscope-reorder`` so xdist keeps this order rather than its own
by-test-count one.

Grouping changes WHERE a test runs, never WHETHER: every collected test is
still scheduled exactly once, and the `digitizer` aggregator's manifest
check still proves the shards together ran the whole suite.
"""

import json
import re
from pathlib import Path

import pytest

DURATIONS = Path(__file__).with_name(".shard_durations.json")
_MEMO = re.compile(r"lru_cache|functools\.cache\b|^@cache\b", re.M)


def _active(config):
    return (getattr(config.option, "loadgroup", False)
            or config.getoption("dist", default=None) == "loadgroup")


def _module_fixtures(item):
    info = getattr(item, "_fixtureinfo", None)
    if info is None:
        return ()
    names = []
    for name in item.fixturenames:
        defs = info.name2fixturedefs.get(name)
        if defs and defs[-1].scope == "module":
            names.append(name)
    return names


def groups_for(items, sources):
    """Map nodeid -> group name (absent = ungrouped). ``sources`` maps a file
    path to its text. Pure apart from reading item metadata."""
    by_file = {}
    for it in items:
        by_file.setdefault(it.nodeid.split("::", 1)[0], []).append(it)
    out = {}
    for path, its in by_file.items():
        if _MEMO.search(sources.get(path, "")):
            for it in its:
                out[it.nodeid] = path
            continue
        parent = {}

        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        uses = {it.nodeid: _module_fixtures(it) for it in its}
        for names in uses.values():
            for a, b in zip(names, names[1:]):
                parent[find(a)] = find(b)
        for nodeid, names in uses.items():
            if names:
                out[nodeid] = f"{path}:{find(names[0])}"
    return out


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    if not _active(config):
        return
    root = Path(str(config.rootpath))
    files = {it.nodeid.split("::", 1)[0] for it in items}
    sources = {}
    for f in files:
        try:
            sources[f] = (root / f).read_text(encoding="utf-8")
        except OSError:
            sources[f] = ""
    group = groups_for(items, sources)
    for it in items:
        if it.nodeid in group:
            it.add_marker(pytest.mark.xdist_group(group[it.nodeid]))

    durations = json.loads(DURATIONS.read_text()) if DURATIONS.exists() else {}
    per_file = {}
    for it in items:
        per_file[it.nodeid.split("::", 1)[0]] = per_file.get(
            it.nodeid.split("::", 1)[0], 0) + 1
    scope_cost = {}
    for it in items:
        f = it.nodeid.split("::", 1)[0]
        scope = group.get(it.nodeid, it.nodeid)
        scope_cost[scope] = scope_cost.get(scope, 0.0) + (
            durations.get(f, 0.0) / per_file[f])
    first_seen = {}
    for i, it in enumerate(items):
        first_seen.setdefault(group.get(it.nodeid, it.nodeid), i)
    # Stable: within a scope, and between equal costs, collection order holds.
    order = {id(it): (-scope_cost[group.get(it.nodeid, it.nodeid)],
                      first_seen[group.get(it.nodeid, it.nodeid)], i)
             for i, it in enumerate(items)}
    items.sort(key=lambda it: order[id(it)])
