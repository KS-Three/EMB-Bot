"""The true-size switch's cap-height guard (`cfg.small_text_true_size_min_cap_mm`,
Kent's ruling 2026-10-14 21:55; `config.SMALL_TEXT_TRUE_SIZE_MIN_CAP_MM` 1.6,
a gate-1 CANDIDATE). Fremont's Hat at 65 mm read WORSE under the switch
(tagline OCR 10/11 -> 5/11), so a line under the guard takes today's path:
not restored, not tagged bean, byte for byte the engine before the flip.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, beanletters, digitize, small_text
from digitizer_core.config import SMALL_TEXT_TRUE_SIZE_MIN_CAP_MM, true_size_min_cap
from digitizer_core.ink_path import MemberInk

from .conftest import own_thread_only
from .test_small_text import _cap, _scene, _tag

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


def test_the_guard_is_read_only_while_the_switch_is_on():
    assert SMALL_TEXT_TRUE_SIZE_MIN_CAP_MM == 1.6
    assert PipelineConfig().small_text_true_size_min_cap_mm == 1.6
    assert true_size_min_cap(PipelineConfig()) == 1.6
    # switch OFF: explicit restore / bean values act at every size, as before
    assert true_size_min_cap(PipelineConfig(small_text_true_size=False)) is None
    assert true_size_min_cap(PipelineConfig(small_text_true_size_min_cap_mm=None)) is None


def test_restore_leaves_a_line_under_the_guard_untouched():
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    before = [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions]
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, min_cap_mm=_cap(regions) * 1.05)
    assert next(r for r in rep if r["cluster"] == "TCtest")["skipped"] == "below_min_cap"
    assert [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions] == before


def test_restore_still_restores_a_line_over_the_guard():
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, min_cap_mm=_cap(regions) * 0.95)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert "skipped" not in row and row.get("adopted") == 1, row


def test_line_cap_is_the_restore_steps_own_measure():
    regions, _p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    members = [r for r in regions if r.meta.get("text_cluster_id")]
    assert small_text.line_cap_mm(members) == pytest.approx(_cap(regions))


@pytest.mark.parametrize("scale, reads", [(1.05, False), (0.95, True)])
def test_bean_tagging_reads_no_ink_under_the_guard(monkeypatch, scale, reads):
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    calls = []

    def fake(_p, members, **_kw):
        calls.append(len(members))
        return [MemberInk(stroke_mm=None, spines=[]) for _ in members]

    monkeypatch.setattr(beanletters, "read_cluster_ink", own_thread_only(fake, beanletters.read_cluster_ink))
    cfg = PipelineConfig(small_text_true_size_min_cap_mm=_cap(regions) * scale)
    assert beanletters.tag_bean_letters(regions, p, cfg) == 0
    assert bool(calls) is reads
    assert not any(beanletters.BEAN_LETTER_KEY in r.meta or "ink_stroke_mm" in r.meta for r in regions)


# --- end to end: the small-print census's synthetic line ---------------------------
# md5 prefixes measured 2026-10-14. At a 1.55 mm cap the unguarded switch moves the
# design (202 -> 215 stitches); the guarded default is byte-identical to OFF. At 2.5 mm
# the guard does not bite: the default equals the unguarded switch (321 stitches, the
# corpus `sp_synthetic_2.5` switch cell, md5 a502e790).
MD5 = {1.55: {"off": "dbb6380a91", "unguarded": "1644330929"},
       2.5: {"off": "1ad15a6e07", "unguarded": "a502e7908a"}}


def _md5(cap, **kw):
    from tools import small_print
    ref = json.loads((TESTDATA / "small_print_synthetic_ref.json").read_text())
    _r, plan = digitize(small_print.load("synthetic"),
                        PipelineConfig(target_width_mm=round(cap / ref["cap"], 2), **kw))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()[:10]


def test_below_the_guard_the_default_is_the_engine_before_the_flip():
    off = _md5(1.55, small_text_true_size=False)
    assert off == MD5[1.55]["off"]
    assert _md5(1.55) == off
    assert _md5(1.55, small_text_true_size_min_cap_mm=None) == MD5[1.55]["unguarded"]


def test_over_the_guard_the_default_is_the_switch():
    assert _md5(2.5, small_text_true_size=False) == MD5[2.5]["off"]
    assert _md5(2.5) == MD5[2.5]["unguarded"]
