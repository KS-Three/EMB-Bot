"""Compute an expensive module fixture (or `@shared_cache` helper) ONCE per
run, not once per xdist worker.

WHY. `-n auto` hands a module's tests to whichever of the four workers is
free (`--dist load`), and every worker that draws one of them builds its OWN
copy of the module's fixtures and `lru_cache`d pipeline runs. Measured
2026-10-08 on shard 1/6 (local 4-core box, same as a CI runner):
`test_thread_match_area_in_message.py` digitizes three fixtures and cost
406 s of test time under `--dist load` against 206 s with the whole file on
one worker (`--dist loadfile`) -- the difference is the same three pipeline
runs repeated on other workers. `--dist loadfile` removes the repeat but
serializes the big files, so a shard's wall becomes its largest file; this
removes the repeat and keeps the per-test spread.

WHAT IT PROMISES. Exactly what pytest already promises a single process: a
module-scoped fixture is computed once and every test of that module sees
that value. The first worker to need it computes it under a file lock; the
others wait on the lock (they would otherwise spend the same time
recomputing it) and then load a pickled COPY. A copy, never a shared object,
so no worker can see another's mutation -- strictly no looser than an
`lru_cache`, which hands the same object to every caller in the process.

WHAT IT SKIPS (computed natively, exactly as before):
  - generator (yield) fixtures -- their teardown belongs to whoever ran them;
  - fixtures that take any argument but `request` -- a `tmp_path_factory`
    path is a worker's private directory, and a dependency's value cannot be
    keyed on safely;
  - anything that finished in under CHEAP_S seconds -- not worth a pickle;
  - anything that will not pickle, or that raised (every worker then raises
    for itself, with its own traceback);
  - everything, when ``DIGITIZER_SHARED_CACHE=0`` or the platform has no
    ``fcntl`` (Windows) -- `shared_cache` then degrades to a per-process
    memo, which is what the `lru_cache` it replaced was.

The cache directory lives for one pytest invocation: the controlling process
creates it in `pytest_configure` and removes it in `pytest_unconfigure`, and
xdist workers inherit its path through the environment. Nothing persists
between runs, so there is no staleness to manage.
"""

import functools
import hashlib
import inspect
import os
import pickle
import shutil
import tempfile
import time
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows: no cross-process cache, per-process memo only.
    fcntl = None

ENV_DIR = "DIGITIZER_SHARED_CACHE_DIR"
ENV_SWITCH = "DIGITIZER_SHARED_CACHE"
CHEAP_S = 1.0

_NOCACHE = b"nocache"


def _enabled():
    return (fcntl is not None
            and os.environ.get(ENV_SWITCH, "1") != "0"
            and bool(os.environ.get(ENV_DIR)))


def configure(config):
    """Controller only: make the run's cache directory before workers spawn."""
    if hasattr(config, "workerinput") or os.environ.get(ENV_DIR):
        return
    if fcntl is None or os.environ.get(ENV_SWITCH, "1") == "0":
        return
    os.environ[ENV_DIR] = tempfile.mkdtemp(prefix="digitizer-shared-cache-")
    config._digitizer_shared_cache_owner = os.environ[ENV_DIR]


def unconfigure(config):
    owned = getattr(config, "_digitizer_shared_cache_owner", None)
    if owned:
        shutil.rmtree(owned, ignore_errors=True)
        os.environ.pop(ENV_DIR, None)


def _compute_once(key, compute):
    """`compute()` once across every process sharing ENV_DIR; returns its
    value (the computing process) or an unpickled copy (everyone else)."""
    if not _enabled():
        return compute()
    base = Path(os.environ[ENV_DIR])
    digest = hashlib.sha1(key.encode()).hexdigest()
    data = base / f"{digest}.pkl"
    with open(base / f"{digest}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if data.exists():
                blob = data.read_bytes()
                if blob != _NOCACHE:
                    return pickle.loads(blob)
                return compute()
            t0 = time.perf_counter()
            value = compute()  # raises -> no file, the next worker retries
            try:
                blob = (pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                        if time.perf_counter() - t0 >= CHEAP_S else _NOCACHE)
            except Exception:
                blob = _NOCACHE
            tmp = data.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_bytes(blob)
            tmp.replace(data)
            return value
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def shared_cache(fn):
    """Drop-in for `functools.lru_cache(maxsize=None)` on a test helper whose
    arguments have a stable `repr` (fixture names, numbers, flags). Same
    in-process behavior -- one object per argument tuple per process -- plus
    the cross-worker sharing above."""
    memo = {}
    name = f"{fn.__module__}.{fn.__qualname__}"

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        k = (args, tuple(sorted(kwargs.items())))
        if k not in memo:
            memo[k] = _compute_once(f"fn:{name}:{k!r}",
                                    lambda: fn(*args, **kwargs))
        return memo[k]

    wrapper.cache_clear = memo.clear
    return wrapper


def _eligible(fixturedef):
    if fixturedef.scope != "module" or not _enabled():
        return False
    func = fixturedef.func
    if inspect.isgeneratorfunction(func) or inspect.iscoroutinefunction(func):
        return False
    if not set(fixturedef.argnames) <= {"request"}:
        return False
    return fixturedef.baseid.startswith("tests/") and fixturedef.baseid.endswith(".py")


def fixture_setup(fixturedef, request):
    """`pytest_fixture_setup` body: None means "not mine, run it natively"."""
    if not _eligible(fixturedef):
        return None
    from _pytest.fixtures import pytest_fixture_setup as native

    param = (request.param_index, repr(getattr(request, "param", None)))
    key = f"fixture:{fixturedef.baseid}::{fixturedef.argname}:{param!r}"
    ran = []

    def compute():
        ran.append(True)
        return native(fixturedef, request)  # sets fixturedef.cached_result

    value = _compute_once(key, compute)
    if not ran:  # loaded from another worker's run: record it as pytest would
        fixturedef.cached_result = (value, fixturedef.cache_key(request), None)
    return value
