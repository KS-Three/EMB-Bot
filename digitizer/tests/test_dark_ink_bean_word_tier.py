"""`cfg.dark_ink_bean_keeps_word_tier`, `thin_ink.release_word_tier_dark_ink`,
built OFF 2026-11-17: a dark-ink piece that is a letter of a text cluster whose
dark-ink members are a minority is left out of the bean group and sews like
its word-mates. Synthetic strips only.
"""
from __future__ import annotations

from shapely.geometry import box

from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.thin_ink import (DARK_INK_GROUND_KEY, bean_dark_ink,
                                     release_word_tier_dark_ink)
from digitizer_core.threads import CHART

_IDX = {c.number: i for i, c in enumerate(CHART)}
TAN, BROWN = _IDX["0763"], _IDX["1233"]
GROUND = box(0, 0, 60, 40)


def _r(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=float(poly.area),
                  meta={"layer": layer, **meta})


def _strip(x):
    return box(x, 2.0, x + 0.46, 10.0)      # thin: mean width ~0.43 mm


def _design(n_letters, n_ink, cluster="C1"):
    """A ground, `n_ink` dark-ink strokes and `n_letters - n_ink` plain
    letters (not dark ink, wide), all in text cluster `cluster`."""
    rs = [_r("G", GROUND, TAN, 0)]
    for i in range(n_letters):
        if i < n_ink:
            rs.append(_r(f"K{i}", _strip(2 + 3 * i), BROWN, 1, dark_ink=True,
                         **({"text_cluster_id": cluster} if cluster else {})))
        else:
            rs.append(_r(f"L{i}", box(2 + 3 * i, 2, 4 + 3 * i, 10), BROWN, 1,
                         **({"text_cluster_id": cluster} if cluster else {})))
    return rs


def _tagged(rs):
    return {r.shape_id for r in rs if BEAN_LETTER_KEY in r.meta}


def _run(rs, on):
    bean_dark_ink(rs, by_width=True)
    if on:
        release_word_tier_dark_ink(rs, by_width=True)
    return rs


def test_flag_is_off_by_default():
    assert PipelineConfig().dark_ink_bean_keeps_word_tier is False


def test_minority_dark_ink_in_a_word_is_not_beaned_when_on():
    off, on = _run(_design(6, 2), False), _run(_design(6, 2), True)
    assert _tagged(off) == {"K0", "K1"}
    assert _tagged(on) == set()
    assert all(DARK_INK_GROUND_KEY not in r.meta for r in on)


def test_all_dark_ink_cluster_is_beaned_in_both_arms():
    off, on = _run(_design(6, 6), False), _run(_design(6, 6), True)
    assert _tagged(off) == _tagged(on) == {f"K{i}" for i in range(6)}


def test_exactly_half_is_not_a_minority():
    off, on = _run(_design(6, 3), False), _run(_design(6, 3), True)
    assert _tagged(off) == _tagged(on) == {"K0", "K1", "K2"}


def test_dark_ink_without_a_cluster_is_unchanged():
    off, on = _run(_design(6, 2, cluster=None), False), _run(_design(6, 2, cluster=None), True)
    assert _tagged(off) == _tagged(on) == {"K0", "K1"}


def test_off_is_byte_identical_to_the_plain_pass():
    a, b = _design(6, 2), _design(6, 2)
    bean_dark_ink(a, by_width=True)
    _run(b, False)
    assert [(r.shape_id, r.meta) for r in a] == [(r.shape_id, r.meta) for r in b]


def test_the_median_is_read_over_what_remains():
    # Cluster A: 1 of 4 is dark ink (released). The 3 ink strokes outside any
    # cluster are thin and still bean as a group.
    rs = _design(4, 1, cluster="A")
    rs += [_r(f"X{i}", _strip(30 + 3 * i), BROWN, 1, dark_ink=True) for i in range(3)]
    _run(rs, True)
    assert _tagged(rs) == {"X0", "X1", "X2"}
