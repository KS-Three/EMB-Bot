"""A Cancel lands inside stage 4's lettering passes and stage 7's keyline,
not after them.

Measured 2026-11-13 (`docs/second-digitize-timing-2026-11-13.md`): on
`becker_marine_logo.png` at 96 mm the three longest stretches of a whole
digitize with no `deadline.check` were

* stage 4, "stage 4 thread revalidation" -> "stage 4 text clusters": 4.1-5.7 s
  quiet, 19.5 s loaded -- the text cluster round's neck cut
  (`textcluster._neck_split`'s loop over the pieces a neck leaves: 393 on
  Becker's ring border, 5 s) and the letterform-prior fit
  (`letterform_priors.plan_letterform_priors`, ~0.4 s per letter);
* stage 7, around a keyline (`stage6_border.keyline_runs` -> `_satin_loop`'s
  exact cross per ring sample, and `_bury_walks`): 1.8-5.3 s, twice per run.

A Cancel pressed in one kept the single worker for the rest of it (1.4-5.5 s
measured after Cancel returned), and the customer's next run queued behind
work nobody wanted. #1408 put seams in the loops that make a fill or a satin;
these were not among them.

A check reads a clock and moves no number, so a run that is not cancelled is
identical with or without a scope armed (pinned below for both halves).
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, deadline
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches

ART = Path(__file__).resolve().parents[1] / "testdata" / "becker_marine_logo.png"
WIDTH_MM = 96.0
STAGE4_SEAMS = ("text cluster neck splits", "letterform priors")
KEYLINE_SEAM = "keyline"


def _pixels():
    from digitizer_service.app import _decode_bounded
    return _decode_bounded(ART.read_bytes())


class _Recorder:
    """Stands in for `deadline.check`: times every call, and sets `event`
    at the `nth` visit to the `trip` seam."""

    def __init__(self, real, event=None, trip=None, nth=1):
        self.real, self.event, self.trip, self.nth = real, event, trip, nth
        self.calls: list[tuple[float, str]] = []
        self.seen = 0

    def __call__(self, stage: str) -> None:
        self.calls.append((time.perf_counter(), stage))
        if stage == self.trip:
            self.seen += 1
            if self.seen == self.nth and self.event is not None:
                self.event.set()
        self.real(stage)


def _max_gap(calls, t_end, end_label):
    calls = calls + [(t_end, end_label)]
    return max((b[0] - a[0], a[1], b[1]) for a, b in zip(calls, calls[1:]))


def _gen_fingerprint(gen) -> list:
    return sorted((r.shape_id, r.thread_number, r.polygon.wkb_hex,
                   r.meta.get("text_candidate"), str(r.meta.get("letterform_prior")))
                  for r in gen.regions)


def _plan_fingerprint(plan) -> list:
    return [(b.thread_number, [(r.kind, r.jump, r.trim, r.shape_id, tuple(r.points))
                               for r in b.runs]) for b in plan.blocks]


@pytest.fixture(scope="module")
def reference():
    """One generation and one plan, no scope armed, every seam timed.
    Patched by hand: a module fixture cannot take `monkeypatch`."""
    pixels = _pixels()
    cfg = PipelineConfig(target_width_mm=WIDTH_MM)
    real = deadline.check
    rec = _Recorder(real)
    deadline.check = rec
    try:
        gen = build_generation(pixels, cfg)
        t_gen = time.perf_counter()
        n_gen = len(rec.calls)
        result = finish_generation(gen.fork(), cfg)
        t_fin = time.perf_counter()
        n_fin = len(rec.calls)
        plan = plan_stitches(result, cfg)
        t_plan = time.perf_counter()
    finally:
        deadline.check = real
    gen_calls = rec.calls[:n_gen]
    labels = [s for _, s in gen_calls]
    after_s3 = gen_calls[labels.index("stage 3"):]
    plan_calls = rec.calls[n_fin:]
    return {"pixels": pixels, "cfg": cfg, "gen": gen, "plan": plan,
            "stages": {s for _, s in rec.calls},
            "stage4_seconds": t_gen - after_s3[0][0],
            "stage4_gap": _max_gap(after_s3, t_gen, "end of build_generation"),
            "plan_seconds": t_plan - t_fin,
            "plan_gap": _max_gap(plan_calls, t_plan, "end of plan_stitches")}


def test_the_fixture_still_reaches_every_guarded_loop(reference):
    """The art must exercise what is being guarded: lettering found, the
    letterform priors fitted at this size (they run on an upscaled upload),
    and a keyline sewn."""
    regions = reference["gen"].regions
    assert any(r.meta.get("text_candidate") for r in regions)
    assert any(r.meta.get("letterform_prior") for r in regions)
    missing = set(STAGE4_SEAMS + (KEYLINE_SEAM,)) - reference["stages"]
    assert not missing, f"no checkpoint reached in: {sorted(missing)}"


def test_no_long_gap_after_stage_3(reference):
    """The longest a cancel can wait in stage 4 and the rest of the
    generation. Before 2026-11-13 one gap was 0.6-0.7 of that stretch; judged
    against the same run's own length so a loaded runner moves both."""
    gap, a, b = reference["stage4_gap"]
    assert gap < 0.35 * reference["stage4_seconds"], (
        f"longest gap {gap:.2f}s ({a!r} -> {b!r}) of a "
        f"{reference['stage4_seconds']:.2f}s stretch")


def test_no_long_gap_in_the_plan(reference):
    """The same for stages 5-7. Before 2026-11-13 a keyline was 0.2-0.3 of
    the whole plan in one gap; after, the longest is a fraction of that."""
    gap, a, b = reference["plan_gap"]
    assert gap < 0.1 * reference["plan_seconds"], (
        f"longest gap {gap:.2f}s ({a!r} -> {b!r}) of a "
        f"{reference['plan_seconds']:.2f}s plan")


@pytest.mark.parametrize("seam", STAGE4_SEAMS)
def test_a_cancel_is_taken_inside_each_stage4_loop(reference, monkeypatch, seam):
    """The flag goes up at the second visit to `seam`; that very check raises,
    and nothing past it ran."""
    ev = threading.Event()
    rec = _Recorder(deadline.check, ev, trip=seam, nth=2)
    monkeypatch.setattr(deadline, "check", rec)
    with deadline.scope(None, cancel=ev):
        with pytest.raises(deadline.Cancelled) as caught:
            build_generation(reference["pixels"], reference["cfg"])
    assert caught.value.stage == seam
    assert rec.calls[-1][1] == seam


def test_a_cancel_is_taken_inside_the_keyline(reference, monkeypatch):
    ev = threading.Event()
    rec = _Recorder(deadline.check, ev, trip=KEYLINE_SEAM, nth=5)
    monkeypatch.setattr(deadline, "check", rec)
    result = finish_generation(reference["gen"].fork(), reference["cfg"])
    with deadline.scope(None, cancel=ev):
        with pytest.raises(deadline.Cancelled) as caught:
            plan_stitches(result, reference["cfg"])
    assert caught.value.stage == KEYLINE_SEAM
    assert rec.calls[-1][1] == KEYLINE_SEAM


def test_an_armed_but_unset_scope_changes_nothing(reference):
    cfg = reference["cfg"]
    with deadline.scope(600.0, cancel=threading.Event()):
        gen = build_generation(reference["pixels"], cfg)
        plan = plan_stitches(finish_generation(gen.fork(), cfg), cfg)
    assert _gen_fingerprint(gen) == _gen_fingerprint(reference["gen"])
    assert _plan_fingerprint(plan) == _plan_fingerprint(reference["plan"])
