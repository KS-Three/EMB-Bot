"""tools/pro_baseline.py: the needle-up reader and the worst-gap ranking (no pro files needed)."""
import pystitch

from tools import pro_baseline as pb


def _dst(tmp_path, records):
    pat = pystitch.EmbPattern()
    for cmd, x, y in records:
        pat.add_stitch_absolute(cmd, x, y)
    pat.add_stitch_absolute(pystitch.END, 0, 0)
    path = tmp_path / "t.dst"
    pystitch.write_dst(pat, str(path))
    return path


def test_needle_up_sums_lifted_gaps_only(tmp_path):
    S, J, T = pystitch.STITCH, pystitch.JUMP, pystitch.TRIM
    path = _dst(tmp_path, [(S, 0, 0), (S, 50, 0),          # sewn: 5 mm, not counted
                           (T, 50, 0), (J, 50, 200), (S, 50, 300),   # lifted (5, 0) -> (5, 30) mm: 30 mm
                           (S, 60, 300)])
    nu = pb.needle_up(path)
    assert nu["hops"] == 1
    assert abs(nu["needle_up_mm"] - 30.0) < 0.2


def test_worst_counts_an_artwork_once_by_its_worst_job():
    res = {"jobs": {
        "becker_hat_large": {"ours": {"trims": 24}, "pro": {"trims": 10}},
        "becker_beanie": {"ours": {"trims": 18}, "pro": {"trims": 11}},
        "tires_hat_3d": {"ours": {"trims": 7}, "pro": {"trims": 10}},
    }}
    rows = pb.worst(res, "trims")
    assert [r[0] for r in rows] == ["becker", "tires"]
    assert rows[0][1] == "becker_hat_large" and rows[0][4] == 14
