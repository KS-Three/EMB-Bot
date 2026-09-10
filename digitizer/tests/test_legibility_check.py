"""`cfg.legibility_check` — preflight reading what the thread SAYS.

Quality review 2026-09-08 item 11, plan
`docs/superpowers/plans/2026-09-10-legibility-yardstick.md` §2c: the one
check that can see sewn-but-illegible (`dropped_elements` reads 0.2% on a
design whose tagline Kent calls "completely lost"). DEFAULT OFF until Kent
rules on `LEGIBILITY_BLOCK` / `LEGIBILITY_WARN`; the report says
`legibility_checked` either way, so off, no artwork and no tesseract are all
distinguishable from clean.

The fixture is `enthusiast_logo.png`: two text clusters that read at 96 on
the artwork and 94 / 88 on the render (scope-history 2026-09-08), so the
clean case is a real read and the lost case is the same plan with its
lettering runs cut down to a stitch each — the lettering still SEWS (not the
unsewn warnings' business) and says nothing.
"""
from __future__ import annotations

import copy
from functools import lru_cache

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

from .conftest import TESTDATA, requires_tesseract

ART = TESTDATA / "photo" / "enthusiast_logo.png"


@lru_cache(maxsize=None)
def _enthusiast():
    """One digitize, reused; every test here only reads it (or deep-copies
    the plan before touching it)."""
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(ART, cfg)
    return result, plan


def _on(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                          legibility_check=True, **kw)


def _cluster_ids(result) -> set[str]:
    return {r.shape_id for r in result.regions if r.meta.get("text_cluster_id")}


def _hits(report) -> list[dict]:
    return [f for f in report["findings"] if f["code"] == pf.LETTERING_ILLEGIBLE]


def test_default_off_and_the_thresholds_are_ordered():
    """Warn-only for now: the OCR crops showed no similarity band that
    separates lost lettering from damaged lettering (plan §4.2), so the
    block threshold sits at 0.0 — never — until Kent rules otherwise."""
    assert PipelineConfig().legibility_check is False
    assert 0.0 <= pf.LEGIBILITY_BLOCK < pf.LEGIBILITY_WARN < 1.0


def test_off_says_unchecked_and_emits_nothing():
    result, plan = _enthusiast()
    report = pf.run_preflight(result, plan, PipelineConfig(
        target_width_mm=80.0, garment_id="left_chest"), image=ART)
    m = report["metrics"]
    assert m["legibility_checked"] is False
    assert m["legibility"] is None and m["legibility_worst"] is None
    assert not _hits(report)


def test_no_artwork_means_unchecked_even_when_on():
    """The re-score path (`image=None`): nothing to read the art from, so the
    check is skipped and SAYS so — the thread-match contract."""
    result, plan = _enthusiast()
    report = pf.run_preflight(result, plan, _on(), image=None)
    assert report["metrics"]["legibility_checked"] is False
    assert not _hits(report)


def test_no_tesseract_means_unchecked_not_clean(monkeypatch):
    result, plan = _enthusiast()
    monkeypatch.setattr(pf._legibility, "tesseract_available", lambda: False)
    report = pf.run_preflight(result, plan, _on(), image=ART)
    assert report["metrics"]["legibility_checked"] is False
    assert not _hits(report)


@requires_tesseract
def test_lettering_that_reads_back_emits_nothing():
    result, plan = _enthusiast()
    report = pf.run_preflight(result, plan, _on(), image=ART)
    m = report["metrics"]
    assert m["legibility_checked"] is True
    assert m["legibility_clusters"] >= 1 and m["legibility_readable"] >= 1
    assert m["legibility"] >= pf.LEGIBILITY_WARN
    assert m["legibility_worst"] >= pf.LEGIBILITY_WARN
    assert not _hits(report)


def _lettering_cut_to_a_stitch(result, plan):
    """Every text-cluster run cut to its first two points: sewn, and silent."""
    ids = _cluster_ids(result)
    plan2 = copy.deepcopy(plan)
    cut = 0
    for b in plan2.blocks:
        for run in b.runs:
            if run.shape_id in ids and len(run.points) > 2:
                run.points = list(run.points[:2])
                cut += 1
    assert cut, "fixture drift: no text-cluster run to cut"
    return plan2


@requires_tesseract
def test_lettering_the_thread_no_longer_says_is_a_finding():
    result, plan = _enthusiast()
    report = pf.run_preflight(result, _lettering_cut_to_a_stitch(result, plan),
                              _on(), image=ART)
    hits = _hits(report)
    assert len(hits) == 1, "one finding per design, aggregated like the lettering check"
    f = hits[0]
    x = f["extra"]
    assert x["worst_similarity"] < pf.LEGIBILITY_WARN
    # The severity follows the thresholds as ruled: a block only when the
    # block band exists and the reading falls inside it.
    want = ("block" if x["worst_similarity"] < pf.LEGIBILITY_BLOCK else "warn")
    assert f["severity"] == want
    assert x["judged"] >= 1 and 1 <= x["lost"] <= x["judged"]
    assert x["worst_art_text"] and x["worst_art_text"] in f["message"]
    assert any("ENTHUSIAST" in r["art_text"] for r in x["rows"])
    assert report["metrics"]["legibility_worst"] == x["worst_similarity"]
    assert report["metrics"]["legibility_checked"] is True


@requires_tesseract
def test_lettering_nothing_sews_is_left_to_the_unsewn_warnings():
    """A cluster none of whose shapes sews is the unsewn / enclosed warnings'
    business: reported in the rows, never judged, so nothing fires here."""
    result, plan = _enthusiast()
    ids = _cluster_ids(result)
    plan2 = copy.deepcopy(plan)
    for b in plan2.blocks:
        b.runs = [run for run in b.runs if run.shape_id not in ids]
    assert sum(len(b.runs) for b in plan2.blocks) < sum(len(b.runs) for b in plan.blocks)
    report = pf.run_preflight(result, plan2, _on(), image=ART)
    assert report["metrics"]["legibility_checked"] is True
    assert report["metrics"]["legibility_worst"] is None
    assert not _hits(report)
