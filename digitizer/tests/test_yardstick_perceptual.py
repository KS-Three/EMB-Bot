"""tools/yardstick_perceptual.py (repo root): the perceptual yardstick's
oracles hold on a committed pro file with whichever metrics are installed,
the score table is deterministic, a missing package is an `n/a` column and
not a crash, the pair-list schema is enforced, and the kappa is the textbook
one with no raw share anywhere (ROADMAP gate 4). The heavy metric packages
are NOT in the digitizer venv, so on CI only the `mse` control scores; a
laptop with `tools/requirements-yardstick.txt` installed runs the same
oracles over FLIP, LPIPS and DreamSim.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "yardstick_perceptual.py"
REF = REPO / "digitizer" / "testdata" / "reference"
DST = REF / "becker_hat_small_beckers_logo_hat_2_a.dst"
PES = REF / "becker_hat_small_beckers_logo_hat_2_a.pes"
OTHER = REF / "becker_hat_polo_large_beckers_logo_hat.dst"


@pytest.fixture(scope="module")
def yp():
    spec = importlib.util.spec_from_file_location("yardstick_perceptual", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def metrics(yp):
    ms = yp.make_metrics()
    yp.availability(ms)
    return ms


def _rows():
    return [{"id": "pes_vs_dst", "ours_path": str(PES), "ref_path": str(DST), "design": "hat_small"},
            {"id": "other_vs_dst", "ours_path": str(OTHER), "ref_path": str(DST), "design": "hat_small"}]


@pytest.fixture(scope="module")
def scored(yp, metrics):
    # 512 px long side: the oracles are about ORDER, not resolution, and the
    # full 1024 doubles the render for nothing here.
    return yp.score_rows(_rows(), metrics, oracles=True, max_px=512)


# --------------------------------------------------------------- oracles
def test_mse_control_always_scores(metrics):
    assert next(m for m in metrics if m.name == "mse").unavailable is None


def test_oracles_hold_on_every_installed_metric(yp, metrics, scored):
    """A render against itself reads 0 on every metric; a render against a
    blank canvas reads the worst of the set. Runs on whatever is installed."""
    res = yp.oracle_check(scored, metrics)
    ran = [n for n, o in res.items() if "unavailable" not in o]
    assert "mse" in ran
    for name in ran:
        assert res[name]["self_zero"], (name, res[name])
        assert res[name]["blank_worst"], (name, res[name])


def test_missing_package_is_an_na_column_with_the_reason(yp, metrics, scored):
    for m in metrics:
        col = [r[m.name] for r in scored]
        if m.unavailable:
            assert set(col) == {"n/a"} and m.unavailable
        else:
            assert all(c != "n/a" for c in col)


def test_a_loader_that_raises_degrades_not_crashes(yp):
    class Broken(yp.Metric):
        name = "broken"

        def _load(self):
            raise ImportError("No module named 'nothing_here'")

    m = Broken()
    import numpy as np
    img = np.zeros((8, 8, 3), np.uint8)
    assert m(img, img) is None
    assert m.unavailable.startswith("ImportError")
    assert yp.availability([m]) == {"broken": m.unavailable}


def test_the_near_identical_pair_scores_near_zero_and_the_other_design_higher(scored):
    """The pro's own PES and DST of one design are the same stitches in two
    formats: on the control they sit far under the blank and under a
    different design of the same logo at another size."""
    by = {r["id"]: float(r["mse"]) for r in scored}
    assert by["pes_vs_dst"] < 0.01
    assert by["pes_vs_dst"] < by["other_vs_dst"]


# ----------------------------------------------------------- determinism
def test_score_table_is_byte_identical_across_two_runs(yp, metrics, tmp_path):
    a = yp.score_rows(_rows()[:1], metrics, oracles=True, max_px=256)
    b = yp.score_rows(_rows()[:1], metrics, oracles=True, max_px=256)
    assert a == b
    m1 = yp.write_table(a, tmp_path / "one", metrics)
    m2 = yp.write_table(b, tmp_path / "two", metrics)
    assert m1 == m2 == hashlib.md5((tmp_path / "one" / "scores.csv").read_bytes()).hexdigest()


# --------------------------------------------------------------- schema
def test_pair_list_resolves_relative_paths_and_defaults(yp, tmp_path):
    p = tmp_path / "pairs.csv"
    p.write_text("ours_path,ref_path\nours.dst,ref.dst\n", encoding="utf-8")
    rows = yp.read_pairs(p)
    assert rows[0]["ours_path"] == str((tmp_path / "ours.dst").resolve())
    assert rows[0]["id"] == "ours~ref" and rows[0]["design"] == "ref"
    assert "label" not in rows[0]


def test_pair_list_json_form(yp, tmp_path):
    p = tmp_path / "pairs.json"
    p.write_text(json.dumps([{"ours_path": "/a/x.dst", "ref_path": "/b/y.dst", "label": "same",
                              "pair_id": "P1", "arm": "before"}]), encoding="utf-8")
    rows = yp.read_pairs(p)
    assert rows[0]["label"] == "same" and rows[0]["pair_id"] == "P1"


def test_ab_pairs_refuse_what_cannot_be_read(yp):
    base = {"ours_path": "x", "ref_path": "y", "design": "d"}
    with pytest.raises(SystemExit, match="no 'after' row"):
        yp.ab_pairs([{**base, "id": "a", "label": "after", "pair_id": "P", "arm": "before"}])
    with pytest.raises(SystemExit, match="not in"):
        yp.ab_pairs([{**base, "id": "a", "label": "better", "pair_id": "P", "arm": "before"},
                     {**base, "id": "b", "pair_id": "P", "arm": "after"}])
    with pytest.raises(SystemExit, match="disagree"):
        yp.ab_pairs([{**base, "id": "a", "label": "after", "pair_id": "P", "arm": "before"},
                     {**base, "id": "b", "label": "before", "pair_id": "P", "arm": "after"}])
    with pytest.raises(SystemExit, match="needs a pair_id"):
        yp.ab_pairs([{**base, "id": "a", "label": "after"}])
    pairs = yp.ab_pairs([{**base, "id": "a", "label": "both_bad", "pair_id": "P", "arm": "before"},
                         {**base, "id": "b", "pair_id": "P", "arm": "after"}])
    assert pairs[0]["kent"] == "tie" and pairs[0]["before"]["id"] == "a"


def test_labels_file_attaches_by_pair_id(yp, tmp_path):
    rows = [{"id": "a", "ours_path": "x", "ref_path": "y", "design": "d", "pair_id": "P", "arm": "before"},
            {"id": "b", "ours_path": "x2", "ref_path": "y", "design": "d", "pair_id": "P", "arm": "after"}]
    lab = tmp_path / "labels.csv"
    lab.write_text("pair_id,label,design\nP,after,becker\n", encoding="utf-8")
    out = yp.attach_labels(rows, lab)
    assert all(r["label"] == "after" and r["design"] == "becker" for r in out)


# ---------------------------------------------------------------- kappa
def test_instrument_pick_is_closer_wins_with_a_tie_band(yp):
    assert yp.instrument_pick(0.5, 0.4) == "after"
    assert yp.instrument_pick(0.4, 0.5) == "before"
    assert yp.instrument_pick(0.5, 0.5) == "tie"
    assert yp.instrument_pick(0.50, 0.48, tie_band=0.05) == "tie"
    assert yp.instrument_pick(0.50, 0.40, tie_band=0.05) == "after"


def _synthetic(spec):
    """spec: (kent, instrument pick, count) -> (pairs, scored rows) where the
    scored `mse` makes the instrument pick as asked."""
    pairs, scored, i = [], [], 0
    for kent, inst, n in spec:
        for _ in range(n):
            b, a = {"before": (0.1, 0.2), "after": (0.2, 0.1), "tie": (0.1, 0.1)}[inst]
            rb = {"id": f"{i}:before", "kind": "pair", "mse": f"{b:.6f}"}
            ra = {"id": f"{i}:after", "kind": "pair", "mse": f"{a:.6f}"}
            scored += [rb, ra]
            pairs.append({"pair_id": str(i), "design": f"fx{i % 3}", "kent": kent, "before": rb, "after": ra})
            i += 1
    return pairs, scored


def test_kappa_two_by_two_known_value_and_no_raw_share(yp):
    # Kent decided 10: the instrument matched 4 of 5 each way: po .8, pe .5, kappa .6
    pairs, scored = _synthetic([("after", "after", 4), ("after", "before", 1),
                                ("before", "before", 4), ("before", "after", 1)])
    k = yp.agreement(pairs, scored, "mse")
    assert k["n_scored"] == 10 and k["n_decided"] == 10
    assert k["kappa_decided"] == pytest.approx(0.6)
    assert k["kappa_3way"] == pytest.approx(0.6)
    assert sorted(k["worse_pairs"]) == sorted(["4", "9"])
    assert k["ci2_pairs"][0] is not None and k["reading_decided"] in (
        "above chance", "no evidence either way")
    assert not any("raw" in key or "percent" in key or "share" in key for key in k)


def test_kappa_three_way_counts_ties_and_reads_small_n(yp):
    pairs, scored = _synthetic([("tie", "tie", 3), ("after", "after", 2)])
    k = yp.agreement(pairs, scored, "mse")
    assert k["n_scored"] == 5 and k["n_kent_decided"] == 2
    assert k["kappa_3way"] == pytest.approx(1.0)
    assert k["reading_3way"] == "n too small (<10)"
    assert k["table_3way"][1][1] == 3 and k["table_3way"][2][2] == 2


def test_kappa_skips_a_pair_the_metric_could_not_score(yp):
    pairs, scored = _synthetic([("after", "after", 2)])
    scored[0]["mse"] = "n/a"
    k = yp.agreement(pairs, scored, "mse")
    assert k["n_scored"] == 1


# ------------------------------------------------------------------- CLI
def test_cli_oracle_on_a_committed_file_exits_zero_and_writes_the_report(yp, tmp_path):
    pairs = tmp_path / "pairs.csv"
    pairs.write_text(f"id,ours_path,ref_path\np,{PES},{DST}\n", encoding="utf-8")
    out = tmp_path / "out"
    code = yp.main(["oracle", str(pairs), "--out", str(out), "--metrics", "mse", "--max-px", "256", "--quiet"])
    assert code == 0
    rep = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert rep["oracles"]["mse"]["self_zero"] and rep["oracles"]["mse"]["blank_worst"]
    assert rep["kappa"] is None                        # no labels: no kappa, no share
    text = (out / "report.md").read_text(encoding="utf-8")
    assert "scores.csv md5" in text and "%" not in text
    header = (out / "scores.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",")[:2] == ["id", "kind"] and "mse" in header and "flip" not in header


def test_cli_labels_flag_refuses_a_list_without_labels(yp, tmp_path):
    pairs = tmp_path / "pairs.csv"
    pairs.write_text(f"id,ours_path,ref_path\np,{PES},{DST}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no labelled A/B pair"):
        yp.main(["score", str(pairs), "--labels", "--out", str(tmp_path / "o"), "--metrics", "mse", "--quiet"])


def test_cli_labelled_list_reports_kappa_and_no_share(yp, tmp_path):
    lines = ["id,ours_path,ref_path,label,pair_id,arm"]
    for i, lab in enumerate(["after", "before", "same"]):
        lines += [f"b{i},{OTHER},{DST},{lab},P{i},before", f"a{i},{PES},{DST},{lab},P{i},after"]
    pairs = tmp_path / "pairs.csv"
    pairs.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "o"
    assert yp.main(["score", str(pairs), "--labels", "--out", str(out), "--metrics", "mse",
                    "--max-px", "256", "--quiet"]) == 0
    rep = json.loads((out / "report.json").read_text(encoding="utf-8"))
    k = rep["kappa"]["mse"]
    assert rep["n_labelled_pairs"] == 3 and k["n_scored"] == 3
    assert k["table_3way"][0][2] == 1                  # Kent before, the closer arm (after) chosen
    assert k["reading_3way"] == "n too small (<10)"
    assert not any("raw" in key or "share" in key or "percent" in key for key in k)


def test_cli_metrics_lists_every_column(yp, capsys):
    assert yp.main(["metrics"]) == 0
    out = capsys.readouterr().out
    for name in yp.METRICS:
        assert name in out


# ------------------------------------------- blank is worst, same reference
def _oracle_rows(values):
    """values: {ref: (self, pair, blank)} -> scored `mse` rows as score_rows
    writes them (kind self / pair / blank, each carrying its ref_path)."""
    rows = []
    for ref, (s, p, b) in values.items():
        for kind, v in (("self", s), ("pair", p), ("blank", b)):
            rows.append({"id": f"{ref}~{kind}", "kind": kind, "ref_path": ref, "mse": f"{v:.6f}"})
    return rows


class _FakeMetric:
    name = "mse"
    unavailable = None


def test_same_ref_blank_worst_can_hold_where_the_global_one_fails(yp):
    """Design A's pair reads 0.40, above design B's blank at 0.30, so the
    global reading fails. Each pair is under its OWN blank (0.40 < 0.70,
    0.10 < 0.30), so the same-reference reading holds."""
    scored = _oracle_rows({"A": (0.0, 0.40, 0.70), "B": (0.0, 0.10, 0.30)})
    o = yp.oracle_check(scored, [_FakeMetric()])["mse"]
    assert o["blank_worst"] is False
    assert o["blank_worst_same_ref"] is True
    assert o["refs_checked"] == 2
    assert o["self_zero"] is True


def test_same_ref_blank_worst_fails_when_a_pair_beats_its_own_blank(yp):
    scored = _oracle_rows({"A": (0.0, 0.80, 0.70), "B": (0.0, 0.10, 0.30)})
    o = yp.oracle_check(scored, [_FakeMetric()])["mse"]
    assert o["blank_worst"] is False and o["blank_worst_same_ref"] is False


def test_both_readings_hold_on_a_well_behaved_set(yp):
    scored = _oracle_rows({"A": (0.0, 0.10, 0.70), "B": (0.0, 0.20, 0.30)})
    o = yp.oracle_check(scored, [_FakeMetric()])["mse"]
    assert o["blank_worst"] and o["blank_worst_same_ref"]


def test_same_ref_reading_is_in_report_md_and_not_in_scores_csv(yp, tmp_path):
    scored = _oracle_rows({"A": (0.0, 0.40, 0.70), "B": (0.0, 0.10, 0.30)})
    ms = [_FakeMetric()]
    md5 = yp.write_table(scored, tmp_path, ms)
    assert "same_ref" not in (tmp_path / "scores.csv").read_text()
    oracle = yp.oracle_check(scored, ms)
    md = yp.markdown(scored, ms, {"mse": None}, None, oracle, md5)
    assert "blank is worst, same reference" in md
    assert "| mse | yes | NO | yes |" in md


def _write_pairs(tmp_path):
    pairs = tmp_path / "pairs.csv"
    pairs.write_text("id,ours_path,ref_path\n" + f"p,{PES},{DST}\n", encoding="utf-8")
    return pairs


def test_cli_report_json_carries_both_blank_readings(yp, tmp_path):
    out = tmp_path / "o"
    code = yp.main(["oracle", str(_write_pairs(tmp_path)), "--out", str(out), "--metrics", "mse",
                    "--max-px", "256", "--quiet"])
    assert code == 0
    o = json.loads((out / "report.json").read_text(encoding="utf-8"))["oracles"]["mse"]
    assert o["blank_worst"] is True and o["blank_worst_same_ref"] is True and o["refs_checked"] == 1
    assert "same reference" in (out / "report.md").read_text(encoding="utf-8")
