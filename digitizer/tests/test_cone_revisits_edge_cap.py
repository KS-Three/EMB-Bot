"""`tools/cone_revisits.py` — the edge cap's own route (defect 18 instrument).

Kept apart from `test_cone_revisits.py`, whose test count MASTER_SCOPE cites.
Stage 7 appends the design-silhouette cap after ALL the artwork, one block per
cone it stands against, so every cap block repeats a cone the artwork already
sewed. Before `edge_cap` was a route these read `plain` — "the fold's own
territory" — and sent a reader to `merge_duplicate_cones` for survivors it can
never see. Re-measured 2026-10-08: `logo_alpha`, `logo_whitebg`,
`bg_uncertain` and `region_blobs` duplicate ONLY through the cap.
"""

from tests.test_cone_revisits import _Region, _Result, _plan
from tools.cone_revisits import revisits


def test_a_cap_block_is_its_own_route_not_the_folds_territory():
    """Stage 7 appends the design-silhouette cap after ALL the artwork, one
    block per cone it stands against, so each cap block repeats a cone the
    artwork already sewed. Re-measured 2026-10-08, that is every duplicate on
    the corpus — and read as `plain`, it sent the reader to
    `merge_duplicate_cones` (defect 18) for a survivor that fold can never
    see. Its fix is a different flag (`edge_cap_fold_into_colour`)."""
    plan = _plan(("0020", ("Sa", "Sb")), ("0108", ("Sx",)),
                 ("0020", ("__edge_cap__",)))
    got = revisits(plan, _Result(_Region("Sa"), _Region("Sb"),
                                 _Region("Sx")))
    assert [r["route"] for r in got] == ["edge_cap"]


def test_an_artwork_block_that_also_sews_cap_is_not_a_cap_block():
    """`edge_cap_fold_into_colour` sews a cone's cap stretches at the end of
    that cone's own artwork block. Such a block has review shapes behind it,
    so it is read by its artwork, not as a cap block."""
    plan = _plan(("0182", ("Sa", "__edge_cap__")), ("0020", ("Sx",)),
                 ("0182", ("Sb",)))
    got = revisits(plan, _Result(_Region("Sa"), _Region("Sx"), _Region("Sb")))
    assert [r["route"] for r in got] == ["plain"]


def test_a_cap_beside_a_resnapped_block_is_the_caps_duplicate_alone():
    """`drone_render` 2026-10-08: the artwork sews `0134` once, from a
    re-snapped region, and the cap sews it again. The re-snap did not cause
    the second block — no `resnap` fix would remove it."""
    plan = _plan(("0134", ("Sa",)), ("0020", ("Sx",)),
                 ("0134", ("__edge_cap__",)))
    got = revisits(plan, _Result(_Region("Sa", resnapped=True),
                                 _Region("Sx")))
    assert [r["route"] for r in got] == ["edge_cap"]


def test_artwork_sewing_a_cone_twice_keeps_its_route_beside_a_cap():
    """Two artwork blocks AND a cap block: both causes are real, both print."""
    plan = _plan(("3574", ("Sa",)), ("0020", ("Sx",)), ("3574", ("Sb",)),
                 ("3574", ("__edge_cap__",)))
    got = revisits(plan, _Result(_Region("Sa", resnapped=True),
                                 _Region("Sx"), _Region("Sb")))
    assert [r["route"] for r in got] == ["edge_cap,resnap"]
    plan = _plan(("3574", ("Sa",)), ("0020", ("Sx",)), ("3574", ("Sb",)),
                 ("3574", ("__edge_cap__",)))
    got = revisits(plan, _Result(_Region("Sa"), _Region("Sx"), _Region("Sb")))
    assert [r["route"] for r in got] == ["edge_cap,plain"]
