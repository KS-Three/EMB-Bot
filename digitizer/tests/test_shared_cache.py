"""tests/_shared_cache.py: once per run across processes, a copy per process,
and a clean fallback wherever it cannot help."""

import multiprocessing as mp
import os
import time

import pytest

from tests import _shared_cache as sc

pytestmark = pytest.mark.skipif(sc.fcntl is None, reason="needs fcntl (POSIX)")


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(sc.ENV_DIR, str(tmp_path))
    monkeypatch.delenv(sc.ENV_SWITCH, raising=False)
    monkeypatch.setattr(sc, "CHEAP_S", 0.0)
    return tmp_path


def _slow_square(n, log):
    with open(log, "a") as f:
        f.write(f"{os.getpid()}\n")
    time.sleep(0.3)
    return {"n": n * n}


def _worker(args):
    d, log = args
    os.environ[sc.ENV_DIR] = d
    sc.CHEAP_S = 0.0
    return sc._compute_once("k", lambda: _slow_square(7, log))


def test_four_processes_compute_once_and_all_get_the_value(cache_dir):
    log = cache_dir / "calls.log"
    with mp.get_context("spawn").Pool(4) as pool:
        got = pool.map(_worker, [(str(cache_dir), str(log))] * 4)
    assert got == [{"n": 49}] * 4
    assert len(log.read_text().split()) == 1


def test_a_hit_is_a_copy_not_the_computed_object(cache_dir):
    first = sc._compute_once("copy", lambda: {"a": [1]})
    second = sc._compute_once("copy", lambda: pytest.fail("recomputed"))
    assert second == first and second is not first
    second["a"].append(2)
    assert sc._compute_once("copy", lambda: None) == {"a": [1]}


def test_a_cheap_value_is_never_stored(cache_dir, monkeypatch):
    monkeypatch.setattr(sc, "CHEAP_S", 60.0)
    calls = []
    for _ in range(2):
        sc._compute_once("cheap", lambda: calls.append(1) or 5)
    assert calls == [1, 1]


def test_an_unpicklable_value_falls_back_to_computing(cache_dir):
    calls = []

    def make():
        calls.append(1)
        return lambda: None   # lambdas do not pickle
    sc._compute_once("lam", make)
    sc._compute_once("lam", make)
    assert len(calls) == 2


def test_a_raise_stores_nothing_and_the_next_caller_retries(cache_dir):
    with pytest.raises(ZeroDivisionError):
        sc._compute_once("boom", lambda: 1 / 0)
    assert sc._compute_once("boom", lambda: 3) == 3


def test_switched_off_it_is_a_plain_call(cache_dir, monkeypatch):
    monkeypatch.setenv(sc.ENV_SWITCH, "0")
    calls = []
    for _ in range(2):
        sc._compute_once("off", lambda: calls.append(1))
    assert calls == [1, 1]
    assert list(cache_dir.iterdir()) == []


def test_shared_cache_memoizes_per_argument_tuple_in_process(cache_dir):
    calls = []

    @sc.shared_cache
    def f(x, flag=False):
        calls.append((x, flag))
        return [x, flag]

    assert f("a") is f("a")          # lru_cache's in-process identity, kept
    assert f("a", flag=True) == ["a", True]
    assert calls == [("a", False), ("a", True)]


_built = []


@pytest.fixture(scope="module")
def module_value():
    _built.append(1)
    return {"built": len(_built)}


def test_a_module_fixture_still_reaches_its_tests(module_value):
    assert module_value == {"built": 1}


def test_and_is_built_once_per_process(module_value):
    assert module_value == {"built": 1} and len(_built) <= 1
