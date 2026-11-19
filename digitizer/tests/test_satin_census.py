"""tools.satin_census: the satin-piece reader on synthetic columns (numbers only)."""
import math

from tools import satin_census as sc


def column(x0, y0, x1, y1, width, pitch=0.4, lean_deg=0.0):
    """A straight satin column from (x0, y0) to (x1, y1): alternate rails,
    `pitch` same-side, crosses square to the axis turned by `lean_deg`."""
    L = math.dist((x0, y0), (x1, y1))
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    a = math.atan2(ux, -uy) + math.radians(lean_deg)        # cross direction
    cx, cy = math.cos(a) * width / 2, math.sin(a) * width / 2
    n = int(L / (pitch / 2))
    pts = []
    for i in range(n + 1):
        t = i * pitch / 2
        mx, my = x0 + ux * t, y0 + uy * t
        s = 1 if i % 2 == 0 else -1
        pts.append((mx + s * cx, my + s * cy))
    return pts


def run(pts):
    return sc.Run(pts, "t", (255, 255, 255))


def test_one_column_is_one_piece():
    ps = sc.pieces([run(column(0, 0, 10, 0, 2.0))])
    assert len(ps) == 1
    p = ps[0]
    assert abs(p.width_mm - 2.0) < 0.05
    assert abs(p.length_mm - 10.0) < 0.5
    assert abs(p.pitch_mm - 0.4) < 0.05
    assert p.top
    assert abs(((p.cross_deg - 90) + 90) % 180 - 90) < 2      # crosses square to an x axis


def test_running_stitch_and_fill_rows_are_not_satin():
    walk = [(i * 2.0, 0.0) for i in range(10)]
    rows = []
    for k in range(6):                       # tatami: rows back and forth, each split
        xs = [0, 3, 6, 9] if k % 2 == 0 else [9, 6, 3, 0]
        rows += [(x, k * 0.4) for x in xs]
    assert sc.pieces([run(walk)]) == []
    assert all(not p.top or p.n < 6 for p in sc.pieces([run(rows)]))


def test_direction_change_and_reversal_split_pieces():
    a = column(0, 0, 8, 0, 2.0)
    b = column(8, 0, 8, 8, 3.0)                   # turns 90 deg and widens: a new piece
    back = column(8, 8, 8, 0, 3.0)[1:]            # the stem's second pass, reversed
    ps = sc.pieces([run(a + b + back)])
    assert len(ps) == 3
    assert [round(p.width_mm) for p in ps] == [2, 3, 3]


def test_interleaved_groups_read_as_their_own_pieces():
    """Two columns sewn in alternating groups of six throws inside one run."""
    a = column(0, 0, 12, 0, 2.0)
    b = column(0, 5, 12, 5, 3.0, lean_deg=30)
    pts = []
    for k in range(0, min(len(a), len(b)), 7):
        pts += a[k:k + 7] + b[k:k + 7]
    ps = sc.pieces([run(pts)])
    widths = sorted({round(p.width_mm, 1) for p in ps})
    assert widths == [2.0, 3.0]
    assert all(p.n >= sc.MIN_THROWS for p in ps)


def test_relate_butt_and_overlap():
    stem = sc.pieces([run(column(0, -5, 0, 5, 2.0))])[0]
    into = sc.pieces([run(column(-0.5, 0, 8, 0, 2.0))])[0]      # starts 0.5 inside the stem's centre
    short = sc.pieces([run(column(2.0, 3, 8, 3, 1.5))])[0]       # stops short of the stem
    r_into = sc.relate(stem, into)
    r_short = sc.relate(stem, short)
    assert r_into["start"] > 1.0                                 # 1.0 half width + 0.5 + thread
    assert r_short["start"] < -0.5
    assert r_into["shared_mm2"] > 0 and r_short["shared_mm2"] == 0


def test_layers_count_stacked_passes():
    one = run(column(0, 0, 6, 0, 2.0))
    two = run(column(0, 0, 6, 0, 2.0)[::-1])
    l1 = sc.layers([one], (3, 0), 0.8)
    l2 = sc.layers([one, two], (3, 0), 0.8)
    assert l1["max"] >= 1 and l2["mean"] > 1.6 * l1["mean"]
