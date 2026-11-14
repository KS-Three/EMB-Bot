"""A cancel -- or the job timeout -- lands INSIDE one shape's emission.

`digitizer_core.deadline` read at stage seams and once per shape in stage 7, so
a cancel waited out the shape in hand: 61 s on `owl_kent.jpg` at 200 mm (PR
#1400's measurement), the whole of one large fill. Since 2026-11-12 the same
`deadline.check` also sits inside the loops that make one shape: the fill's
angle search, order pricing, reorders and emit, the satin's rails, seam close
and rail push, the outline column builder, the stage 7 passes after emission,
and the preflight. A check reads a clock and moves no number, so a job that is
not cancelled is byte-identical (pinned below beside the cancel).

The service-level pair at the end is the point of it all: the worker is free
within one gap, and the next upload does not queue behind a shape nobody wants.
"""
from __future__ import annotations

import math
import threading
import time

import pytest
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from digitizer_core import (PipelineConfig, deadline, fill_section_travel, machine, stage6_fill,
                            stage6_satin, stitches)

from .conftest import own_thread_only, wait_idle

# What the loops in `stage6_fill` / `stage6_satin` call their checkpoints. A
# loop that loses its check fails `test_each_loop_has_its_checkpoint` by name.
# ("fill seam order" is on the shipped default path but not on the bare call
# `reference` makes, and "fill underlay" runs only with `underlay_all_pieces`:
# each has its own test below.)
FILL_SEAMS = ("fill angle search", "fill order pricing", "fill reorder for cover",
              "fill reorder", "fill emit")


def _field(holes: int = 18):
    """An 86 x 66 mm plate with `holes` counters: no big fill is cheap, and a
    holed one makes the order pricing and the covered bridges do real work.
    The seconds it takes depend on the box (the first version, 126 x 96 mm with
    30 counters, took 5-13 s on the laptop it was written on, not the "about
    3 s" its comment said), which is why every timing test below judges a lag
    against the same run's own length; this one is sized to keep at least
    1.5 s of fill for the 0.3 s sleeps that land a cancel inside it."""
    shell = box(0, 0, 80.0, 60.0).buffer(3)
    for i in range(holes):
        cx = 10 + (i * 37.0) % 60.0
        cy = 10 + (i * 53.0) % 40.0
        shell = shell.difference(Point(cx, cy).buffer(3 + (i % 3)))
    return shell


def _fill(poly):
    """One `stitch_shape` call the way stage 7's tatami rung makes it."""
    stage6_fill.clear_fill_reorder_memo()
    stage6_fill._FOOTPRINT_CACHE.clear()      # a cold shape every time, so timings compare
    return stage6_fill.stitch_shape(
        poly, "field", angle_deg=None, row_mm=machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style="edge_lattice",
        trim_at_mm=machine.TRIM_AT_MM, under_cover=True, cut_bridges=True)


def _satin(poly):
    return stage6_satin.satin_shape(poly, "stroke", underlay_style="none",
                                    trim_at_mm=machine.TRIM_AT_MM, art_poly=poly)


def _stroke():
    pts = [(i * 150.0 / 40, 12.0 * math.sin(i * 0.35) + 0.002 * i * i) for i in range(41)]
    return LineString(pts).buffer(2.0, cap_style=2)


def _fingerprint(result) -> list:
    runs, report = result
    return [[(r.kind, r.jump, r.trim, r.shape_id, tuple(r.points)) for r in runs], dict(report)]


class _Recorder:
    """Stands in for `deadline.check` and times every call; `trip` sets the
    flag the first time a named seam is reached (`nth` of its calls, counting
    only the visits where `when()` holds). `snapshot()` is read at the visit
    that trips, just before the raise: what the shape had set up by then."""

    def __init__(self, real, event: threading.Event | None = None,
                 trip: str | None = None, nth: int = 1, when=None, snapshot=None):
        self.real, self.event, self.trip, self.nth = real, event, trip, nth
        self.when, self.snapshot = when, snapshot
        self.calls: list[tuple[float, str]] = []
        self.seen = 0
        self.snap = None

    def __call__(self, stage: str) -> None:
        self.calls.append((time.perf_counter(), stage))
        if stage == self.trip and (self.when is None or self.when()):
            self.seen += 1
            if self.seen == self.nth:
                if self.snapshot is not None:
                    self.snap = self.snapshot()
                if self.event is not None:
                    self.event.set()
        self.real(stage)


@pytest.fixture(scope="module")
def reference():
    """The plate sewn once, no scope armed, every seam timed. A module fixture
    cannot take `monkeypatch`, so it holds its own; the patch is
    `own_thread_only` like every patch of a module global here (the service's
    pool thread may be sewing another test's job)."""
    poly = _field()
    real = deadline.check
    rec = _Recorder(real)
    mp = pytest.MonkeyPatch()
    mp.setattr(deadline, "check", own_thread_only(rec, real))
    try:
        t0 = time.perf_counter()
        result = _fill(poly)
        seconds = time.perf_counter() - t0
    finally:
        mp.undo()
    times = [t0] + [t for t, _ in rec.calls] + [t0 + seconds]
    return {"poly": poly, "result": result, "seconds": seconds,
            "stages": {s for _, s in rec.calls}, "calls": len(rec.calls),
            "max_gap": max(b - a for a, b in zip(times, times[1:]))}


def _patched(monkeypatch, event=None, trip=None, nth=1, when=None, snapshot=None) -> _Recorder:
    real = deadline.check
    rec = _Recorder(real, event, trip, nth, when, snapshot)
    monkeypatch.setattr(deadline, "check", own_thread_only(rec, real))
    return rec


# --- the checkpoints are there, and cheap enough to be everywhere --------------

def test_the_plate_is_still_sewn_as_fill_not_only_underlay(reference):
    """The `try`/`finally` around `stitch_shape`'s body must keep the final
    `emit` of the fill inside it, at the level the fill is sewn (a mis-indent
    once dropped it for every design with the seam-order switches off)."""
    runs, report = reference["result"]
    kinds = {r.kind for r in runs}
    assert stitches.FILL in kinds and stitches.UNDERLAY in kinds
    assert sum(len(r.points) for r in runs if r.kind == stitches.FILL) > 1000
    assert report["empty"] is False


def test_each_loop_has_its_checkpoint(reference):
    missing = set(FILL_SEAMS) - reference["stages"]
    assert not missing, f"no checkpoint reached in: {sorted(missing)}"
    assert reference["calls"] >= 100, reference["calls"]


def test_no_two_checkpoints_are_far_apart_inside_one_shape(reference):
    """The longest a cancel can wait here. Before 2026-11-12 this shape was one
    gap of its whole run (3.9 s on the box this was written on); with the
    checkpoints the longest is about a sixth of that. Judged against the same
    run's own length so a loaded runner moves both."""
    assert reference["max_gap"] < 0.5 * reference["seconds"], (
        f"longest gap {reference['max_gap']:.2f}s of a {reference['seconds']:.2f}s shape")


# --- a cancel lands inside the shape ------------------------------------------

def test_a_cancel_set_mid_shape_stops_within_a_bound(reference):
    ev = threading.Event()
    set_at: list[float] = []

    def flip():
        time.sleep(0.3)
        set_at.append(time.perf_counter())
        ev.set()

    threading.Thread(target=flip, daemon=True).start()
    with deadline.scope(None, cancel=ev):
        with pytest.raises(deadline.Cancelled):
            _fill(reference["poly"])
    lag = time.perf_counter() - set_at[0]
    assert lag < 0.5 * reference["seconds"], (
        f"the worker ran {lag:.2f}s past the cancel, of a {reference['seconds']:.2f}s shape")


@pytest.mark.parametrize("seam", FILL_SEAMS)
def test_a_cancel_is_taken_at_each_fill_loop(reference, monkeypatch, seam):
    """The flag goes up at the third visit to `seam`; that very check raises."""
    ev = threading.Event()
    rec = _patched(monkeypatch, ev, trip=seam, nth=3)
    with deadline.scope(None, cancel=ev):
        with pytest.raises(deadline.Cancelled) as caught:
            _fill(reference["poly"])
    assert caught.value.stage == seam
    # Nothing past the tripped seam ran: its is the last check made.
    assert rec.calls[-1][1] == seam


def test_the_job_deadline_is_taken_inside_a_shape_too(reference):
    """The same checkpoint serves the 600 s timeout: a deadline that passes
    mid-shape is an `Abandoned`, the sibling of `Cancelled`."""
    t0 = time.perf_counter()
    with deadline.scope(0.3):
        with pytest.raises(deadline.Abandoned) as caught:
            _fill(reference["poly"])
    assert not isinstance(caught.value, deadline.Cancelled)
    assert caught.value.over_s < 0.5 * reference["seconds"]
    assert time.perf_counter() - t0 < reference["seconds"]


def test_a_cancel_mid_satin_is_taken(monkeypatch):
    poly = _stroke()
    ev = threading.Event()
    _patched(monkeypatch, ev, trip="satin rails", nth=10)
    with deadline.scope(None, cancel=ev):
        with pytest.raises(deadline.Cancelled) as caught:
            _satin(poly)
    assert caught.value.stage == "satin rails"


# --- a cancel leaves nothing behind -------------------------------------------

def test_a_cancelled_shape_leaves_no_state_for_the_next_job(reference, monkeypatch):
    """The cancel lands in the FILL phase of a shape sewn with section travel
    on, so the three things `stitch_shape` sets up are all live when it
    raises: the bridge memo, the unsewn-ground memo (filled once the fill has
    laid thread, `sewn` not None) and the section-travel memo. Each is read
    just before the raise -- an assertion on emptiness afterwards proves
    nothing about a memo that was never filled."""
    ev = threading.Event()
    rec = _patched(
        monkeypatch, ev, trip="fill emit", nth=1,
        when=lambda: bool(stage6_fill._UNSEWN_MEMO) and bool(fill_section_travel._MEMO),
        snapshot=lambda: {"bridge": stage6_fill._BRIDGE_MEMO.get() is not None,
                          "unsewn": len(stage6_fill._UNSEWN_MEMO),
                          "travel_on": fill_section_travel.active(),
                          "travel_memo": len(fill_section_travel._MEMO)})
    cfg = PipelineConfig(extra={fill_section_travel.KEY: True})
    with fill_section_travel.enabled(cfg), deadline.scope(None, cancel=ev):
        with pytest.raises(deadline.Cancelled):
            _fill(reference["poly"])
    monkeypatch.undo()                  # the worker thread's next job: no recorder
    assert rec.snap is not None, "the cancel never landed in the fill phase"
    assert rec.snap["bridge"] and rec.snap["travel_on"]
    assert rec.snap["unsewn"] > 0 and rec.snap["travel_memo"] > 0
    # `stitch_shape` sets a per-shape bridge memo, the unsewn-ground memo and
    # the section-travel plan; a cancel in `emit` must put all three back, on
    # this thread, for the next job.
    assert stage6_fill._BRIDGE_MEMO.get() is None
    assert fill_section_travel.active() is False
    assert not stage6_fill._UNSEWN_MEMO
    assert not fill_section_travel._MEMO
    # ... and the next job's shape is exactly the shape an unbroken run made --
    # sewn here under an armed-but-unset scope, which is also the proof that
    # a scope no one cancelled changes nothing in the fill.
    with deadline.scope(3600.0, cancel=threading.Event()):
        again = _fill(reference["poly"])
    assert _fingerprint(again) == _fingerprint(reference["result"])


def test_a_cancel_is_taken_in_the_seam_order_the_default_runs(reference, monkeypatch):
    """`stitch_shape` as the shipped config calls it: seam order, priced, and
    cut-exposed all ON (`config.py`'s defaults), which is the path every real
    job takes and `reference`'s bare call does not."""
    cfg = PipelineConfig()
    assert cfg.fill_seam_order and cfg.fill_seam_order_priced and cfg.fill_bridge_cut_exposed
    ev = threading.Event()
    rec = _patched(monkeypatch, ev, trip="fill seam order", nth=3)
    with (stage6_fill.seam_order_scope(cfg.fill_seam_order),
          stage6_fill.seam_priced_scope(cfg.fill_seam_order_priced),
          stage6_fill.cut_exposed_scope(cfg.fill_bridge_cut_exposed),
          deadline.scope(None, cancel=ev)):
        with pytest.raises(deadline.Cancelled) as caught:
            _fill(reference["poly"])
    assert caught.value.stage == "fill seam order"
    assert rec.calls[-1][1] == "fill seam order"
    monkeypatch.undo()
    assert stage6_fill._BRIDGE_MEMO.get() is None and not stage6_fill._UNSEWN_MEMO


def test_a_cancel_is_taken_between_underlay_pieces(monkeypatch):
    """`underlay_all_pieces` underlays every piece the inset splits the shape
    into, nearest first; a shape of many pieces loops there before any fill."""
    bars = [box(i * 12.0, 0, i * 12.0 + 10.0, 20.0) for i in range(6)]
    # 1 mm necks: under twice the 1 mm underlay inset, so the inset splits it
    necks = [box(i * 12.0 + 10.0, 9.5, i * 12.0 + 12.0, 10.5) for i in range(5)]
    poly = unary_union(bars + necks)
    assert poly.geom_type == "Polygon"
    assert poly.buffer(-machine.UNDERLAY_INSET_MM).geom_type == "MultiPolygon"
    ev = threading.Event()
    rec = _patched(monkeypatch, ev, trip="fill underlay", nth=2)
    with deadline.scope(None, cancel=ev):
        with pytest.raises(deadline.Cancelled) as caught:
            stage6_fill.stitch_shape(
                poly, "pieces", angle_deg=None, row_mm=machine.FILL_ROW_MM,
                stitch_mm=machine.FILL_STITCH_MM, underlay_style="edge_run",
                trim_at_mm=machine.TRIM_AT_MM, under_cover=True, underlay_all_pieces=True)
    assert caught.value.stage == "fill underlay"
    assert rec.calls[-1][1] == "fill underlay"


# --- a job that is not cancelled is byte-identical ----------------------------
# (the fill's identity under an armed scope is asserted by the next-job sew above)

def test_an_armed_but_unset_scope_changes_nothing_in_the_satin():
    poly = _stroke()
    bare = _satin(poly)
    with deadline.scope(3600.0, cancel=threading.Event()):
        armed = _satin(poly)
    assert _fingerprint(armed) == _fingerprint(bare)


# --- the worker is free, and the next upload does not wait ---------------------

def test_a_cancel_mid_fill_frees_the_worker_and_the_next_job_runs_at_once(reference):
    pytest.importorskip("fastapi", reason="service extra not installed")
    from digitizer_service.jobs import JobRegistry

    registry = JobRegistry(workers=1, timeout_s=300.0)
    try:
        entered = threading.Event()
        poly = reference["poly"]

        def work() -> dict:
            entered.set()
            _fill(poly)
            return {"finished": True}

        job, _ = registry.submit("big-fill", work)
        assert entered.wait(5)
        time.sleep(0.3)                     # well inside the shape, not at a seam
        t_cancel = time.monotonic()
        registry.cancel(job.id)
        assert job.state == "cancelled"
        freed = wait_idle(registry, within_s=reference["seconds"] + 5.0)
        assert time.monotonic() - t_cancel < 0.5 * reference["seconds"], (
            f"worker freed {freed:.2f}s after the cancel, of a {reference['seconds']:.2f}s shape")
        # It STOPPED; it did not run the shape out and drop the answer.
        assert isinstance(job._future.exception(timeout=10), deadline.Cancelled)

        t0 = time.monotonic()
        nxt, _ = registry.submit("next", lambda: {"ok": True})
        assert nxt._future.result(timeout=10) == {"ok": True}
        assert time.monotonic() - t0 < 1.0
    finally:
        registry.shutdown()


def test_the_job_timeout_frees_the_worker_inside_a_fill_too(reference):
    pytest.importorskip("fastapi", reason="service extra not installed")
    from digitizer_service.jobs import JobRegistry

    registry = JobRegistry(workers=1, timeout_s=0.3)
    try:
        poly = reference["poly"]
        t0 = time.monotonic()
        job, _ = registry.submit("big-fill-timeout", lambda: {"finished": bool(_fill(poly))})
        wait_idle(registry, within_s=reference["seconds"] + 5.0)
        past_deadline = (time.monotonic() - t0) - 0.3
        assert past_deadline < 0.5 * reference["seconds"], (
            f"worker freed {past_deadline:.2f}s after the 0.3 s timeout, "
            f"of a {reference['seconds']:.2f}s shape")
        assert isinstance(job._future.exception(timeout=10), deadline.Abandoned)
    finally:
        registry.shutdown()
