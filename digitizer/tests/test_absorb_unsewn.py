"""`cfg.lettering_columns_absorb_unsewn` (built OFF 2026-11-16 as a `cfg.extra` key; ON
since 2026-11-19, the review pack's flip): a
small bold letter's pieces that no construction fits merge into the column
they share the longest edge with, and the merge is kept only if the letter
sews better for it (`columns.absorb_gains`).

The case is Bukit Asam's tagline (`testdata/art/commons_lettering/
bukit_asam_logo_cmyk_01.png`) at 80.4 mm left chest: the 2.5 mm italic a of
"coal" is cut into a ring round its counter plus its stem's lower part and
its foot, both unsewn, so with `lettering_columns_ring_floor` it sewed as an
o and the word read "cool"."""
from shapely import wkt
from shapely.geometry import MultiPoint, box
from shapely.ops import unary_union

from digitizer_core import columns as C
from digitizer_core import outline_cut as oc

# The a as stage 7 hands it to the Column lane (mm, shifted to near the
# origin, 4 decimals -- 3 moves the cut): 75-point outline, one counter, 3.45 mm^2.
A_COAL = wkt.loads(
    "POLYGON ((1.2733 0.1627, 1.2309 0.2051, 1.1037 0.2051, 1.0614 0.2474, 0.9766 0.2474, 0.8918 0.3322, "
    "0.8494 0.3322, 0.5528 0.6289, 0.4680 0.8408, 0.3409 1.0527, 0.3409 1.1375, 0.2985 1.1799, 0.2985 1.3070, "
    "0.2561 1.3494, 0.2561 1.5613, 0.2137 1.6037, 0.2137 2.0699, 0.2561 2.1123, 0.2561 2.2394, 0.2985 2.2818, "
    "0.3409 2.4090, 0.5528 2.6209, 0.5952 2.6209, 0.6375 2.6633, 0.7647 2.6633, 0.8071 2.7056, 1.0190 2.7056, "
    "1.0614 2.6633, 1.1885 2.6633, 1.2309 2.6209, 1.3580 2.5785, 1.4428 2.4937, 1.4852 2.4937, 1.6547 2.3242, "
    "1.7395 2.4513, 1.7395 2.4937, 1.8666 2.6209, 1.9090 2.6209, 1.9514 2.6633, 2.3752 2.6633, 2.4176 2.6209, "
    "2.4176 2.4937, 2.4600 2.4513, 2.4600 2.3242, 2.5024 2.2818, 2.5024 2.1970, 2.2481 2.1970, 2.2057 2.1547, "
    "2.2057 1.8580, 2.2481 1.8156, 2.2481 1.6461, 2.2905 1.6037, 2.2905 1.4342, 2.3328 1.3918, 2.3328 1.2222, "
    "2.3752 1.1799, 2.3752 1.0103, 2.4176 0.9679, 2.4176 0.8408, 2.4600 0.7984, 2.4600 0.6289, 2.5024 0.5865, "
    "2.5024 0.4170, 2.5448 0.3746, 2.5448 0.2474, 2.0785 0.2474, 2.0362 0.3746, 1.9514 0.4594, 1.9090 0.4170, "
    "1.9090 0.3746, 1.8666 0.3746, 1.7395 0.2474, 1.5276 0.2051, 1.4852 0.1627, 1.2733 0.1627), "
    "(1.3157 0.6713, 1.3580 0.6289, 1.6123 0.6289, 1.6547 0.6713, 1.6971 0.6713, 1.8666 0.8408, 1.8666 0.9679, "
    "1.8242 1.0103, 1.8242 1.1375, 1.7819 1.1799, 1.7819 1.3494, 1.7395 1.3918, 1.7395 1.5189, 1.6971 1.5613, "
    "1.6971 1.6461, 1.5700 1.8580, 1.5700 1.9004, 1.2733 2.1970, 1.1885 2.1970, 1.1461 2.2394, 0.9766 2.2394, "
    "0.8071 2.0699, 0.8071 1.9428, 0.7647 1.9004, 0.7647 1.6885, 0.8071 1.6461, 0.8071 1.4342, 0.8494 1.3918, "
    "0.8494 1.2646, 0.9342 1.1375, 0.9342 1.0527, 1.0190 0.9679, 1.0190 0.9256, 1.2733 0.6713, 1.3157 0.6713))")
# stage 7's call for it (the shipped engine's lettering knobs)
A_KW = dict(trim_at_mm=3.0, spacing_mm=0.4, split_above_mm=None, pull_mm=0.3, pull_floor_mm=1.5,
            underlay_style="center_run", fold_cuts=True, square_ends=True, rail_axis=True,
            small_bold=True, short_columns=True, corner_fold=True, corner_fold_apex_side=True,
            inside_stagger=True, text_lean_deg=13.44, inside_connectors=True, edge_walk=True)


def _sew(absorb: bool, ring_floor: bool = True):
    with C.ring_floor_scope(ring_floor), oc.absorb_unsewn_scope(absorb):
        return C.lettering_columns_shape(A_COAL, "a_coal", **A_KW)


def _bare(runs, region) -> float:
    """Area of `region` outside every satin cross-to-cross quad."""
    quads = []
    for run in runs:
        if run.kind != "satin":
            continue
        p = [tuple(map(float, q)) for q in run.points]
        quads += [MultiPoint(p[i:i + 4]).convex_hull for i in range(len(p) - 3)]
    return region.difference(unary_union(quads)).area if quads else region.area


def test_config_default_is_on_and_false_is_the_old_engine():
    # ON since 2026-11-19; the ambient scope outside a plan stays False, so a bare call is the old lane
    from digitizer_core.config import PipelineConfig
    from tests.conftest import PRE_FLIP
    assert PipelineConfig().lettering_columns_absorb_unsewn is True
    assert PRE_FLIP["lettering_columns_absorb_unsewn"] is False
    assert PipelineConfig(lettering_columns_absorb_unsewn=False).lettering_columns_absorb_unsewn is False
    assert oc._ABSORB_UNSEWN.get() is False


def test_off_is_never_called(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("absorb ran with the flag off")
    monkeypatch.setattr(oc, "_absorb_unsewn", boom)
    _sew(absorb=False)


def test_the_coal_a_sews_its_stem_and_foot():
    runs_off, rep_off = _sew(absorb=False)
    runs_on, rep_on = _sew(absorb=True)
    # off: the stem's lower part (0.25 mm^2) and the foot (0.12 mm^2), sewn by nothing
    assert rep_off["columns_unsewn"] == 2 and "absorbed" not in rep_off
    assert rep_on["columns_unsewn"] == 0 and rep_on["absorbed"] == 2
    assert _bare(runs_off, A_COAL) - _bare(runs_on, A_COAL) > 0.15     # 0.75 -> 0.57 mm^2
    assert rep_on["thin_crosses"] == rep_off["thin_crosses"]          # nothing else dropped or kept
    assert C.absorb_gains(runs_off, runs_on, A_COAL)
    assert not C.absorb_gains(runs_on, runs_off, A_COAL)


def test_a_merge_that_sews_less_is_not_kept(monkeypatch):
    # K Line's D at 80 mm: the merge re-paired its ring across the counter and
    # column_runs dropped 20 crosses as thin -- it sewed as an I. Here the
    # merge loses the a's column outright; the sewn judge keeps the cut as it was.
    monkeypatch.setattr(oc, "_absorb_unsewn", lambda cols, cuts, unsewn, *_a: ([], cuts, []))
    runs_off, rep_off = _sew(absorb=False)
    runs_on, rep_on = _sew(absorb=True)
    assert [r.points for r in runs_on] == [r.points for r in runs_off]
    assert "absorbed" not in rep_on and rep_on["columns_unsewn"] == rep_off["columns_unsewn"]


def test_an_unsewn_piece_merges_into_the_column_it_touches():
    # a straight stroke and a short spur off its end that no construction fits
    stem, spur = box(0.0, 0.0, 0.5, 3.0), box(0.0, 3.0, 0.5, 3.3)
    cut = ((0.0, 3.0), (0.5, 3.0), "again", 0.5)
    lines = [oc.LineString([cut[0], cut[1]])]
    col = oc.build_column(stem, lines, 0.5, 0.4)
    assert col is not None and oc.build_column(spur, lines, 0.5, 0.4) is None
    cols, cuts, left = oc._absorb_unsewn([col], [cut], [spur], 0.5, 0.4, False)
    assert left == [] and cuts == []
    assert abs(cols[0].piece.area - (stem.area + spur.area)) < 1e-6
    assert max(max(a[1], b[1]) for a, b in cols[0].stations) > 3.0     # stationed into the spur


def test_a_merge_that_re_makes_the_column_is_refused():
    # Commons Bukit's e at 85.1 mm hat: its curved column, merged, came back
    # re-scanned straight. Here a straight stem plus a block off its foot
    # comes back curved round the corner: another construction, not an extension.
    stem, block = box(0.0, 0.0, 0.5, 3.0), box(0.5, 0.0, 1.5, 1.5)
    col = oc.build_column(stem, [], 0.5, 0.4)
    assert col.kind == "straight"
    assert oc.build_column(unary_union([stem, block]), [], 0.5, 0.4).kind == "curved"
    cols, cuts, left = oc._absorb_unsewn([col], [], [block], 0.5, 0.4, False)
    assert left == [block] and cols[0] is col


def test_a_piece_that_barely_touches_stays_unsewn():
    stem, crumb = box(0.0, 0.0, 0.5, 3.0), box(0.5, 1.0, 0.6, 1.05)   # 0.05 mm shared: under ABSORB_SHARE_W W
    col = oc.build_column(stem, [], 0.5, 0.4)
    cols, cuts, left = oc._absorb_unsewn([col], [], [crumb], 0.5, 0.4, False)
    assert left == [crumb] and cols[0] is col
