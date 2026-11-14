"""The cancel signal is a `BaseException`, and every loop that can run long reads it.

Follow-up to PR #1408 (`deadline.check` inside the inner loops). A max-effort
review of that PR found that the pipeline's fail-open handlers (`except
Exception: return None`) could swallow the signal -- one of them sits under an
`lru_cache`, so a cancel became a cached `None` for the NEXT job -- and that
several loops, two subprocesses and one per-shape cleanup still ignored it.
`tests/test_cancel_in_fill.py` covers the fill and the satin; this file covers
the rest.
"""
from __future__ import annotations

import ast
import copy
import gc
import pickle
import subprocess
import sys
import threading
import time
import weakref
from pathlib import Path

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, deadline, machine, stage6_border, stage6_fill

from .conftest import own_thread_only, wait_idle

CORE = Path(__file__).resolve().parents[1] / "digitizer_core"


# --- A. the signal passes through every `except Exception` ---------------------

def test_abandoned_is_not_an_error():
    assert not issubclass(deadline.Abandoned, Exception)
    assert issubclass(deadline.Abandoned, BaseException)
    assert issubclass(deadline.Cancelled, deadline.Abandoned)


def test_a_fail_open_handler_cannot_swallow_it():
    def fail_open():
        try:
            deadline.check("somewhere")
        except Exception:                                # noqa: BLE001
            return "swallowed"
        return "finished"

    flag = threading.Event()
    flag.set()
    with deadline.scope(None, cancel=flag):
        with pytest.raises(deadline.Cancelled):
            fail_open()
    with deadline.scope(-1.0):
        with pytest.raises(deadline.Abandoned):
            fail_open()


@pytest.mark.parametrize("make", [lambda: deadline.Abandoned("stage 7", 1.5),
                                  lambda: deadline.Cancelled("stage 2")],
                         ids=["Abandoned", "Cancelled"])
@pytest.mark.parametrize("clone", [lambda e: pickle.loads(pickle.dumps(e)), copy.copy,
                                   copy.deepcopy], ids=["pickle", "copy", "deepcopy"])
def test_it_survives_a_pickle_and_a_copy(make, clone):
    """`Abandoned("s", 1.5)` once raised `TypeError: missing 'over_s'` on
    unpickle, and `Cancelled` came back with a doubled message."""
    original = make()
    again = clone(original)
    assert type(again) is type(original)
    assert (again.stage, again.over_s) == (original.stage, original.over_s)
    assert str(again) == str(original)


def test_a_cancel_inside_the_angle_search_is_not_cached_as_an_answer():
    """`_slant_for` is an `lru_cache` around `except Exception: return None`.
    Before the signal was a `BaseException` a cancel in the angle search came
    out as `None`, and that `None` stayed cached for the next job's shape."""
    shape = box(0, 0, 40.0, 12.0)
    stage6_fill._slant_for.cache_clear()
    flag = threading.Event()
    flag.set()
    with deadline.scope(None, cancel=flag):
        with pytest.raises(deadline.Cancelled):
            stage6_fill.pro_slant_angle(shape, None)
    assert stage6_fill._slant_for.cache_info().currsize == 0
    # the next job's answer is the real one
    assert stage6_fill.pro_slant_angle(shape, None) == 20.0
    stage6_fill._slant_for.cache_clear()


# --- B. every loop that can run long has its checkpoint ------------------------
# A behavioural cancel on each of these needs a photograph or a pathological
# design (the review measured 14 s in the streamline ordering at 4,000 lines);
# the PR body carries the measured gaps. What fails here, by name, is a loop
# that loses its check.

def _checked_loops(path: str, func: str) -> list[tuple[str, str, str]]:
    """(kind, iterable-or-test source, label) of every loop inside `func` whose
    FIRST statement is `deadline.check("<label>")`."""
    tree = ast.parse((CORE / path).read_text(encoding="utf-8"))
    found = []
    for fn in ast.walk(tree):
        if not (isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == func):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, (ast.For, ast.While)):
                continue
            first = node.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Call)
                    and ast.unparse(first.value.func) == "deadline.check"
                    and isinstance(first.value.args[0], ast.Constant)):
                src = ast.unparse(node.iter if isinstance(node, ast.For) else node.test)
                found.append((type(node).__name__, src, first.value.args[0].value))
    return found


LOOPS = [
    # (file, function, loop's iterable / test contains, label)
    ("stage3_segment.py", "resolve_small_regions", "sorted(small", "stage 3"),
    ("stage6_streamline.py", "_trace_layer", "remaining", "streamlines"),
    ("legibility.py", "measure", "clusters", "legibility"),
    ("stage4_vectorize.py", "vectorize", "region_masks", "stage 4"),
    ("stage7_sequence.py", "_chain", "runs[1:]", "stage 7 chain"),
    ("stage7_sequence.py", "_link_cover", "enumerate(runs)", "stage 7 link cover"),
    ("stage7_sequence.py", "_link_cover", "regions", "stage 7 link cover"),
    ("stage7_sequence.py", "_link_route", "heap", "stage 7 link route"),
    ("stage2_photo_segment.py", "segment", "np.unique(merged", "stage 2"),
    ("stage2_photo_segment.py", "enclosed_rim", "np.unique(labels[valid])", "stage 2"),
    ("thin_ink.py", "iter_thin_components", "range(n_labels)", "thin ink"),
    ("directionfield.py", "_etf_pass", "range(-radius", "direction field"),
]


@pytest.mark.parametrize("path,func,hint,label", LOOPS,
                         ids=[f"{p[:-3]}.{f}[{h}]" for p, f, h, _ in LOOPS])
def test_each_long_loop_reads_the_deadline_first(path, func, hint, label):
    loops = _checked_loops(path, func)
    assert any(hint in src and lab == label for _kind, src, lab in loops), (
        f"{path}:{func} has no loop over `{hint}` that starts with "
        f"deadline.check({label!r}); checked loops there: {loops}")


def test_the_region_merge_callback_reads_the_deadline_before_anything_else():
    tree = ast.parse((CORE / "stage2_photo_segment.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_weight_mean_color")
    body = [s for s in fn.body if not (isinstance(s, ast.Expr)
                                       and isinstance(s.value, ast.Constant))]
    assert ast.unparse(body[0].value) == "deadline.check('stage 2')"


def test_a_raise_inside_skimages_merge_comes_out_unchanged():
    """The merge runs 1-2 s inside skimage's own loop; `_weight_mean_color`
    checks the deadline there. Nothing in skimage may wrap or eat the signal."""
    import numpy as np
    from skimage import graph as skgraph

    labels = np.repeat(np.arange(6, dtype=np.int64)[None, :], 6, axis=0)
    image = np.random.default_rng(1).uniform(0, 100, (6, 6, 3))
    rag = skgraph.rag_mean_color(image, labels, connectivity=2, mode="distance")
    flag = threading.Event()
    flag.set()

    def weight(g, src, dst, n):
        deadline.check("stage 2")
        return {"weight": 0.0}

    def merge(g, src, dst):
        g.nodes[dst]["total color"] += g.nodes[src]["total color"]
        g.nodes[dst]["pixel count"] += g.nodes[src]["pixel count"]
        g.nodes[dst]["mean color"] = g.nodes[dst]["total color"] / g.nodes[dst]["pixel count"]

    with deadline.scope(None, cancel=flag):
        with pytest.raises(deadline.Cancelled) as caught:
            skgraph.merge_hierarchical(labels, rag, thresh=1e9, rag_copy=False,
                                       in_place_merge=True, merge_func=merge,
                                       weight_func=weight)
    assert caught.value.stage == "stage 2"


# --- B. the child processes (rembg, SAM2) --------------------------------------

SLEEPER = "import time, sys; time.sleep(float(sys.argv[1]))"


class _Spy:
    """Records every `Popen` the helper starts, so a test can ask whether the
    child is still alive without a pid (`os.kill(pid, 0)` terminates on Windows)."""

    def __init__(self, monkeypatch):
        self.procs: list[subprocess.Popen] = []
        real = subprocess.Popen
        spy = self

        class Recording(real):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                spy.procs.append(self)

        monkeypatch.setattr(deadline.subprocess, "Popen", own_thread_only(Recording, real))


def test_a_cancel_kills_the_child_and_frees_the_caller_within_a_second(monkeypatch):
    spy = _Spy(monkeypatch)
    flag = threading.Event()
    threading.Timer(0.3, flag.set).start()
    t0 = time.monotonic()
    with deadline.scope(None, cancel=flag):
        with pytest.raises(deadline.Cancelled) as caught:
            deadline.run_subprocess([sys.executable, "-c", SLEEPER, "30"], timeout=60.0)
    assert time.monotonic() - t0 < 1.5
    assert caught.value.stage == "subprocess"
    assert len(spy.procs) == 1 and spy.procs[0].poll() is not None     # reaped, not running


def test_the_job_deadline_kills_the_child_too(monkeypatch):
    spy = _Spy(monkeypatch)
    t0 = time.monotonic()
    with deadline.scope(0.3):
        with pytest.raises(deadline.Abandoned) as caught:
            deadline.run_subprocess([sys.executable, "-c", SLEEPER, "30"], timeout=60.0)
    assert not isinstance(caught.value, deadline.Cancelled)
    assert time.monotonic() - t0 < 1.5
    assert spy.procs[0].poll() is not None


@pytest.mark.parametrize("armed", [False, True], ids=["no scope", "scope armed"])
def test_the_timeout_and_the_result_are_subprocess_runs(monkeypatch, armed):
    """`TimeoutExpired` past the caller's own timeout, the child killed; a
    finished child's return code, stdout and stderr come back as text."""
    spy = _Spy(monkeypatch)

    def go():
        with pytest.raises(subprocess.TimeoutExpired):
            deadline.run_subprocess([sys.executable, "-c", SLEEPER, "30"], timeout=0.6)
        done = deadline.run_subprocess(
            [sys.executable, "-c",
             "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"],
            timeout=30.0)
        assert (done.returncode, done.stdout.strip(), done.stderr.strip()) == (3, "out", "err")

    if armed:
        with deadline.scope(3600.0, cancel=threading.Event()):
            go()
        assert spy.procs[0].poll() is not None
    else:
        go()                       # the unarmed path is `subprocess.run` itself


def test_an_oserror_from_the_launch_is_the_callers_to_handle():
    with deadline.scope(3600.0):
        with pytest.raises(OSError):
            deadline.run_subprocess([str(CORE / "no-such-binary")], timeout=5.0)


# --- C. state a cancel must not leave behind -----------------------------------

def test_border_runs_clears_its_unsewn_memo_when_a_cancel_lands_inside(monkeypatch):
    """`border_runs` empties `_UNSEWN_MEMO` as it returns under cut-exposed;
    the checkpoints let a cancel skip that line. The review measured one
    leftover entry after a cancel at the third "border" check."""
    visible = unary_union([box(0, 0, 20, 20), box(30, 0, 50, 20), box(60, 0, 80, 20)])

    def sew():
        # the needle starts mid-box, so the bridge to the ring crosses finished
        # fill and the unsewn-ground memo fills in the first part
        return stage6_border.border_runs(visible, "b", entry=(10.0, 10.0),
                                         trim_at_mm=machine.TRIM_AT_MM)

    with stage6_fill.cut_exposed_scope(True):
        stage6_fill._UNSEWN_MEMO.clear()
        sew()                                         # not cancelled: nothing left
        assert not stage6_fill._UNSEWN_MEMO

        flag = threading.Event()
        real = deadline.check
        seen = {"border": 0, "memo_before_raise": None}

        def check(stage):
            if stage == "border":
                seen["border"] += 1
                if seen["border"] == 3:
                    seen["memo_before_raise"] = len(stage6_fill._UNSEWN_MEMO)
                    flag.set()
            real(stage)

        monkeypatch.setattr(deadline, "check", own_thread_only(check, real))
        with deadline.scope(None, cancel=flag):
            with pytest.raises(deadline.Cancelled):
                sew()
        monkeypatch.undo()
        assert seen["memo_before_raise"], "the memo was empty at the cancel: nothing to prove"
        assert not stage6_fill._UNSEWN_MEMO


def test_a_cancelled_job_does_not_pin_the_frames_it_unwound():
    """The registry keeps a finished Job (32 of them) and its future holds the
    exception; a traceback on it would hold every unwound frame's locals --
    here a stand-in for a raster -- for as long as the Job is cached."""
    pytest.importorskip("fastapi", reason="service extra not installed")
    from digitizer_service.jobs import JobRegistry

    class Raster:
        pass

    refs: list = []
    inside = threading.Event()

    def work() -> dict:
        raster = Raster()                              # a local of the frame that unwinds
        refs.append(weakref.ref(raster))
        inside.set()
        while True:
            deadline.check("loop")
            time.sleep(0.01)

    registry = JobRegistry(workers=1, timeout_s=60.0)
    try:
        job, _ = registry.submit("pin", work)
        assert inside.wait(5)
        registry.cancel(job.id)
        exc = job._future.exception(timeout=10)
        wait_idle(registry, within_s=10.0)
        gc.collect()
        assert isinstance(exc, deadline.Cancelled)
        assert isinstance(job._future.exception(), deadline.Cancelled)
        assert job.id in registry._jobs                 # still in the registry
        assert refs[0]() is None, "the cancelled job's frame is still reachable"
    finally:
        registry.shutdown()
