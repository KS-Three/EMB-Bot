"""tools/tripwire.py: the nightly tripwire's population, ledger and compare (no digitize here).

The committed ledger (`testdata/tripwire_ledger.json`) is checked for shape; the
compare is driven with synthetic passes so each exit code is pinned to the one
condition that produces it: a wrong-way move PAST tolerance exits 1 and names
the job and figure, a wrong-way move INSIDE tolerance and a right-way move past
it both exit 0, a figure the run lost or a pro-side figure that moved (the reader
changed) exit 1. The raw agreement never appears anywhere (ROADMAP gate 4).
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

from tools import tripwire as tw

DIGITIZER = Path(__file__).resolve().parents[1]
JOB = "becker_hat_large"

BASE = {JOB: {"stitches": 10_000, "trims": 40, "hops": 120, "needle_up_mm": 900.0,
              "sttype_kappa": 0.42, "direction_kappa": 0.30, "word_cc": 0.85}}
PRO = {JOB: {"stitches": 5_000, "trims": 20, "hops": 60, "needle_up_mm": 400.0, "word_cc": 0.90}}
CHANCE = {JOB: 0.61}
WORDS = {JOB: 2}


def _pass(values=BASE, pro=PRO, chance=CHANCE, words=WORDS):
    return {"schema": 1, "values": copy.deepcopy(values), "pro": copy.deepcopy(pro), "chance": dict(chance),
            "words": dict(words), "jobs": sorted(values), "secs": {j: 1.0 for j in values},
            "env": {"platform": "test", "engine": {"head": "abcd1234", "tree": "x+y"}}}


def _second_pass():
    """The same tree run again: trims +1, needle-up +0.4 mm, kappa +0.005, the rest equal."""
    p = _pass()
    v = p["values"][JOB]
    v["trims"], v["needle_up_mm"], v["sttype_kappa"] = 41, 900.4, 0.425
    return p


@pytest.fixture
def ledger():
    return tw.build_ledger([_pass(), _second_pass()], run_url="https://example.invalid/run/1")


def _row(led, fig, job=JOB):
    return next(r for r in led["rows"] if r["job"] == job and r["figure"] == fig)


def _check(tmp_path, led, run, capsys, extra=()):
    lp, fp = tmp_path / "ledger.json", tmp_path / "figures.json"
    lp.write_text(json.dumps(led), encoding="utf-8")
    fp.write_text(json.dumps(run), encoding="utf-8")
    code = tw.main(["check", "--ledger", str(lp), "--figures", str(fp), *extra])
    return code, capsys.readouterr().out


# ------------------------------------------------------------------ the ledger
def test_build_ledger_seeds_each_tolerance_from_the_spread_rounded_up_to_its_resolution(ledger):
    assert ledger["captured"]["passes"] == 2
    assert _row(ledger, "trims")["tolerance"] == 1 and _row(ledger, "trims")["spread"] == 1
    assert _row(ledger, "needle_up_mm")["tolerance"] == pytest.approx(0.4)
    assert _row(ledger, "sttype_kappa")["tolerance"] == pytest.approx(0.01)   # 0.005 rounds UP to the 0.01 step
    assert _row(ledger, "stitches")["tolerance"] == 0                        # passes agreed: nothing to allow
    assert _row(ledger, "word_cc")["tolerance"] == 0
    # baseline is an observed value (the lower median), not a mean
    assert _row(ledger, "trims")["baseline"] == 40
    assert _row(ledger, "needle_up_mm")["baseline"] == 900.0
    # the pro's side rides along for the reader-drift check; kappa carries its chance floor
    assert _row(ledger, "trims")["pro"] == 20
    assert _row(ledger, "sttype_kappa")["chance"] == 0.61
    assert _row(ledger, "word_cc")["words"] == 2
    assert tw.validate_ledger(ledger) == []


def test_every_figure_has_a_direction_and_a_resolution():
    for fig, spec in tw.FIGURES.items():
        assert spec["worse"] in ("up", "down"), fig
        assert spec["res"] > 0, fig
    assert {f for f, s in tw.FIGURES.items() if s["worse"] == "up"} == {"stitches", "trims", "hops", "needle_up_mm"}
    assert {f for f, s in tw.FIGURES.items() if s["worse"] == "down"} == {"sttype_kappa", "direction_kappa", "word_cc"}


def test_validate_rejects_a_wrong_direction_a_negative_tolerance_and_a_raw_key(ledger):
    bad = copy.deepcopy(ledger)
    _row(bad, "trims")["worse"] = "down"
    assert any("worse" in b for b in tw.validate_ledger(bad))
    bad = copy.deepcopy(ledger)
    _row(bad, "hops")["tolerance"] = -1
    assert any("tolerance" in b for b in tw.validate_ledger(bad))
    bad = copy.deepcopy(ledger)
    _row(bad, "sttype_kappa")["raw_agreement"] = 0.9
    assert any("forbidden" in b for b in tw.validate_ledger(bad))
    bad = copy.deepcopy(ledger)
    del _row(bad, "sttype_kappa")["chance"]
    assert any("chance" in b for b in tw.validate_ledger(bad))
    assert tw.validate_ledger({"schema": 1, "rows": []}) == ["no rows"]


def test_the_table_prints_kappa_with_its_chance_floor_and_no_raw_agreement(ledger):
    text = tw.ledger_table(ledger)
    assert "0.42 (0.61)" in text
    assert "stitch-type kappa (chance)" in text
    assert "raw" not in text.lower() and "agreement" not in text.lower()
    assert "https://example.invalid/run/1" in text


def test_capture_from_passes_writes_a_valid_ledger(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(_pass()), encoding="utf-8")
    b.write_text(json.dumps(_second_pass()), encoding="utf-8")
    out = tmp_path / "ledger.json"
    assert tw.main(["capture", "--from", str(a), str(b), "--ledger", str(out)]) == 0
    led = json.loads(out.read_text(encoding="utf-8"))
    assert tw.validate_ledger(led) == []
    assert _row(led, "trims")["tolerance"] == 1
    assert "wrote" in capsys.readouterr().out


# ------------------------------------------------------------------ the compare
def test_a_wrong_way_move_past_tolerance_exits_1_and_names_the_job_and_figure(tmp_path, ledger, capsys):
    run = _pass()
    run["values"][JOB]["trims"] = 40 + 1 + 1          # tolerance is 1: one past it
    code, out = _check(tmp_path, ledger, run, capsys)
    assert code == 1
    assert JOB in out and "trims (cuts)" in out and "WORSE" in out
    assert "1 wrong-way past tolerance" in out and "FAIL" in out


def test_a_lower_kappa_past_tolerance_is_a_wrong_way_move(tmp_path, ledger, capsys):
    run = _pass()
    run["values"][JOB]["sttype_kappa"] = 0.42 - 0.05
    code, out = _check(tmp_path, ledger, run, capsys)
    assert code == 1
    assert "stitch-type kappa (chance)" in out and "0.37 (0.61)" in out
    assert "raw" not in out.lower()


def test_a_wrong_way_move_inside_tolerance_exits_0(tmp_path, ledger, capsys):
    run = _pass()
    run["values"][JOB]["trims"] = 41                  # exactly the tolerance
    run["values"][JOB]["needle_up_mm"] = 900.4
    run["values"][JOB]["sttype_kappa"] = 0.41
    code, out = _check(tmp_path, ledger, run, capsys)
    assert code == 0
    assert "0 wrong-way" in out and "No movers." in out


def test_a_right_way_move_past_tolerance_exits_0_and_is_listed(tmp_path, ledger, capsys):
    run = _pass()
    run["values"][JOB]["trims"] = 30
    run["values"][JOB]["word_cc"] = 0.95
    code, out = _check(tmp_path, ledger, run, capsys)
    assert code == 0
    assert "2 right-way past tolerance" in out and "better" in out and "pass" in out
    assert "WORSE" not in out


def test_a_figure_the_run_lost_exits_1(tmp_path, ledger, capsys):
    run = _pass()
    del run["values"][JOB]["word_cc"]                 # a word reading that stopped locating
    code, out = _check(tmp_path, ledger, run, capsys)
    assert code == 1
    assert "missing" in out and "word cc" in out


def test_a_pro_side_figure_that_moved_means_the_reader_changed_and_exits_1(tmp_path, ledger, capsys):
    run = _pass()
    run["pro"][JOB]["trims"] = 21                     # the pro file did not change; the reader did
    code, out = _check(tmp_path, ledger, run, capsys)
    assert code == 1
    assert "reader_moved" in out and "pro 20 -> 21" in out


def test_only_restricts_the_compare_to_the_named_jobs(tmp_path, ledger, capsys):
    run = _pass()
    run["values"][JOB]["hops"] = 500
    code, out = _check(tmp_path, ledger, run, capsys, extra=["--only", "tires_hat_3d"])
    assert code == 0 and "No movers." in out


def test_check_writes_its_table_and_json_when_asked(tmp_path, ledger, capsys):
    run = _pass()
    run["values"][JOB]["hops"] = 500
    code, _ = _check(tmp_path, ledger, run, capsys,
                     extra=["--table", str(tmp_path / "t.md"), "--json", str(tmp_path / "c.json")])
    assert code == 1
    assert "WORSE" in (tmp_path / "t.md").read_text(encoding="utf-8")
    cmp = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    assert cmp["fail"] is True and cmp["counts"]["WORSE"] == 1


# ------------------------------------------------------------------ the population
def test_the_population_is_the_pairs_whose_art_and_pro_file_are_in_the_repo():
    jobs = tw.committed_jobs()
    for s in ("becker_hat_large", "becker_lc_large", "becker_hat_small", "becker_chest_small", "becker_beanie",
              "hotel_fremont_hat", "gaulke_roofing_hat", "precision_drone", "tires_hat_3d", "goldentee_hat",
              "toat_beanie", "mfab_hat"):
        assert s in jobs
    for s in ("bridge_hat", "bridge_lc", "proseal_hat", "proseal_beanie"):   # files outside the repo / art not committed
        assert s not in jobs
    with zipfile.ZipFile(tw.ZIP) as z:
        names = {tw._renamed(n) for n in z.namelist()}
    for rel in tw.needed_members(jobs):
        assert rel in names, rel


def test_materialise_extracts_only_what_is_needed_and_renames_the_beanie_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("EMB_SCRATCH_KENT", str(tmp_path / "nowhere"))   # no scratch_kent: the zip is the source
    dest = tmp_path / "kent"
    root = tw.materialise(dest, ["becker_beanie"])
    assert root == dest and os.environ["EMB_SCRATCH_KENT"] == str(dest)
    assert (dest / "Embroidery Files" / "To a T-Becker Beanies" / "beckers beanie.DST").is_file()
    assert not (dest / "Embroidery Files" / "MFAB").exists()
    assert not list(dest.glob("__MACOSX*"))
    from tools.word_legibility import resolve
    assert resolve("kent:Embroidery Files/To a T-Becker Beanies/beckers beanie.DST").is_file()


def test_materialise_uses_a_scratch_kent_that_already_holds_the_files(tmp_path, monkeypatch):
    have = tmp_path / "have"
    for rel in tw.needed_members(["goldentee_hat"]):
        (have / rel).parent.mkdir(parents=True, exist_ok=True)
        (have / rel).write_bytes(b"x")
    monkeypatch.setenv("EMB_SCRATCH_KENT", str(have))
    assert tw.materialise(tmp_path / "unused", ["goldentee_hat"]) == have
    assert not (tmp_path / "unused").exists()


# ------------------------------------------------------------------ the committed ledger
def test_the_committed_ledger_is_well_formed_and_covers_every_committed_pair():
    assert tw.LEDGER.is_file(), f"{tw.LEDGER} is missing: capture it on the Linux runner (nightly-tripwire.yml, capture)"
    text = tw.LEDGER.read_text(encoding="utf-8")
    led = json.loads(text)
    assert tw.validate_ledger(led) == []
    assert led["captured"]["passes"] >= 2, "tolerances must come from the spread of 2+ passes, not a desk guess"
    assert (led.get("env") or {}).get("platform", "").startswith("Linux"), "the ledger is a cloud-Linux fact"
    jobs = {r["job"] for r in led["rows"]}
    assert jobs == set(tw.committed_jobs())
    for job in jobs:
        figs = {r["figure"] for r in led["rows"] if r["job"] == job}
        assert {"stitches", "trims", "hops", "needle_up_mm"} <= figs, job
    for key in ("raw", "agreement"):
        assert key not in text.lower().replace("direction", ""), key


# ------------------------------------------------------------------ --help
def test_help_answers_fast_without_importing_the_engine(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(DIGITIZER), PYTHONIOENCODING="utf-8")
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, "-m", "tools.tripwire", "--help"], cwd=tmp_path, env=env,
                       capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    assert r.returncode == 0 and "capture" in r.stdout and "check" in r.stdout
    assert time.monotonic() - t0 < 15
    r = subprocess.run([sys.executable, "-c", "import sys, tools.tripwire; print('digitizer_core' in sys.modules)"],
                       cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert r.stdout.strip() == "False", r.stderr[-500:]
