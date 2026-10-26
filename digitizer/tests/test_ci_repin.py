"""CI pin hygiene (W3-05): full hashes in failure logs, and the tool that reads them.

A red PR run is mostly a pin captured on another machine or gone stale, and the
fix is to copy the hash CI computed into the test. pytest's first line of a
failed hex comparison cuts both values to ~30 chars ('bc28d37bc555...9cca8aed4db69'),
so `tests/_hexrepr.py` prints them whole, and `tools/ci_repin.py` reads them back.
"""
from __future__ import annotations

import json
import subprocess
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests import _ci_shard
from tools import ci_repin, ci_shard_durations

pytest_plugins = ["pytester"]

DIGITIZER = Path(__file__).resolve().parent.parent

ACTUAL = "bc28d37bc5554e21dab9cca8aed4db69"
EXPECTED = "4793dc521a2e217dce6b8a80a7e5cb2f"
ACTUAL_256 = "a" * 20 + "b" * 20 + "c" * 24
EXPECTED_256 = "1" * 32 + "2" * 32


# ------------------------------------------------------------ tests/_hexrepr.py
def _run(pytester, monkeypatch, body, *extra):
    """The inner run is a clean subprocess, as CI is: `-q`, `CI` set (pytest trims
    the FAILED summary line to the terminal width everywhere else), the plugin by name."""
    monkeypatch.setenv("PYTHONPATH", str(DIGITIZER))
    monkeypatch.setenv("CI", "true")
    pytester.makepyfile(body)
    return pytester.runpytest_subprocess("-q", "-p", "no:cacheprovider",
                                         "-p", "tests._hexrepr", *extra)


def test_the_plugin_is_loaded_by_the_suite_itself(pytestconfig):
    # pyproject's addopts names it, so every run (CI's, a laptop's) has it.
    assert pytestconfig.pluginmanager.has_plugin("tests._hexrepr")


def test_failing_md5_assert_shows_both_full_hashes(pytester, monkeypatch):
    res = _run(pytester, monkeypatch, f"""
        def test_pin():
            md5 = "{ACTUAL}"
            assert md5 == "{EXPECTED}"
    """)
    res.assert_outcomes(failed=1)
    out = res.stdout.str()
    assert ACTUAL in out and EXPECTED in out
    # in the one-line summary too -- the line CI prints, and the line a log grep finds
    summary = [ln for ln in out.splitlines() if ln.startswith("FAILED ")]
    assert summary and ACTUAL in summary[0] and EXPECTED in summary[0]
    assert "..." not in summary[0]
    # pytest adds the leading `assert ` itself; the headline is pytest's own wording, whole
    assert f"AssertionError: assert '{ACTUAL}' == '{EXPECTED}'" in summary[0]
    assert "assert assert" not in out
    # which side is the pin is the source's business (tools/ci_repin.py reads it
    # there): the message only labels the sides as pytest's own would, in full
    lines = [ln.strip() for ln in out.splitlines()]
    assert f"left : {ACTUAL}" in lines and f"right: {EXPECTED}" in lines


def test_failing_sha256_assert_shows_both_full_hashes(pytester, monkeypatch):
    res = _run(pytester, monkeypatch, f"""
        def test_pin():
            assert "{ACTUAL_256}" == "{EXPECTED_256}"
    """)
    out = res.stdout.str()
    assert ACTUAL_256 in out and EXPECTED_256 in out


def test_other_strings_keep_pytests_own_output(pytester, monkeypatch):
    # one inner run for all the cases that must NOT be rewritten, a passing hex
    # compare and a `!=` among them (each inner run is a pytest start-up)
    res = _run(pytester, monkeypatch, f"""
        def test_words():
            assert "the quick brown fox" == "the quick brown dog"
        def test_hex_length_that_is_not_a_digest():
            assert "abcdef0123456789" == "abcdef0123456780"
        def test_hex_against_a_non_hex_string():
            assert "{ACTUAL}" == "not a hash at all, just words..."
        def test_a_passing_hex_assert():
            assert "{ACTUAL}" == "{ACTUAL}"
        def test_ne():
            assert "{ACTUAL}" != "{ACTUAL}"
    """)
    res.assert_outcomes(passed=1, failed=4)
    assert "hash mismatch" not in res.stdout.str()


# --------------------------------------------------------------- tools/ci_repin.py
# Real failed-shard output (run 40225844309, shard 4/6, PR #1057), as GitHub serves it:
# a timestamp on every line, pytest's own `-`/`+` diff block under each FAILED line.
# The headline is cut to ~30 characters; the diff lines are whole.
OLD = "4793dc521a2e217dce6b8a80a7e5cb2f"
NEW = "bc28d37bc5554e21dab9cca8aed4db69"
OLD2 = "45170ee7d9d549b8f63569b826175f0c"
NEW2 = "4bb53e8bc0ac6200203e410b9a4e3803"
N1 = "tests/test_outline_line_art_guard.py::test_guard_off_is_byte_identical_to_main"
N2 = "tests/test_outline_line_art_guard.py::test_guard_needs_the_outline_flag"
N_TRUNC = "tests/test_cut_every_jump.py::test_off_is_byte_identical_to_base[earlier-0]"
N_NUM = "tests/test_pro_measured_values.py::test_bean_pitch_on_the_output[pique_knit]"

T = "2026-10-25T19:40:22.42"
PRE_HEXREPR_LOG = f"""\
{T}81821Z =========================== short test summary info ============================
{T}86795Z FAILED {N1} - AssertionError: assert 'bc28d37bc555...9cca8aed4db69' == '4793dc521a2e...b8a80a7e5cb2f'
{T}87459Z
{T}87636Z   - {OLD}
{T}87863Z   + {NEW}
{T}88388Z FAILED {N2} - AssertionError: assert '4bb53e8bc0ac...e410b9a4e3803' == '45170ee7d9d5...569b826175f0c'
{T}89119Z
{T}89291Z   - {OLD2}
{T}89513Z   + {NEW2}
{T}90000Z FAILED {N_TRUNC} - AssertionError: assert 'bb44fe221baf...ca6832549a9b6' == 'd9cad9b85d5c...00be40642dd84'
{T}91000Z FAILED {N_NUM} - assert 0.8344623020614146 == 0.95 ± 0.095
{T}92770Z 4 failed, 899 passed, 3 skipped, 1 xfailed, 2 warnings in 754.45s (0:12:34)
"""


def _hexrepr_log(*entries):
    """What a shard prints once tests/_hexrepr.py is loaded: (node, left, right) each."""
    out = [f"{T}81821Z =========================== short test summary info ============================"]
    for node, left, right in entries:
        out += [f"{T}86795Z FAILED {node} - AssertionError: assert '{left}' == '{right}'",
                f"{T}87459Z   hash mismatch, both values in full:",
                f"{T}87636Z     left : {left}",
                f"{T}87863Z     right: {right}"]
    out.append(f"{T}92770Z {len(entries)} failed, 899 passed in 754.45s (0:12:34)")
    return "\n".join(out) + "\n"


def _lines(text):
    return ci_repin.clean_log(text)


def test_the_summary_entries_are_found_by_node_id():
    entries = ci_repin.summary_entries(_lines(PRE_HEXREPR_LOG))
    assert set(entries) == {N1, N2, N_TRUNC, N_NUM}


def test_pytests_own_diff_block_carries_both_whole_hashes():
    entry = ci_repin.summary_entries(_lines(PRE_HEXREPR_LOG))[N1]
    assert ci_repin.read_pair(entry) == ({OLD, NEW}, "")


def test_the_hexrepr_lines_carry_both_whole_hashes():
    entry = ci_repin.summary_entries(_lines(_hexrepr_log((N1, NEW, OLD))))[N1]
    assert ci_repin.read_pair(entry) == ({OLD, NEW}, "")


def test_a_truncated_headline_alone_is_refused_and_says_a_rerun_is_needed():
    entry = ci_repin.summary_entries(_lines(PRE_HEXREPR_LOG))[N_TRUNC]
    pair, why = ci_repin.read_pair(entry)
    assert pair is None
    assert "truncated" in why and "re-run" in why


def test_a_failure_that_is_not_a_hash_pair_is_refused():
    entry = ci_repin.summary_entries(_lines(PRE_HEXREPR_LOG))[N_NUM]
    pair, why = ci_repin.read_pair(entry)
    assert pair is None and "not a hash" in why


def test_ansi_and_timestamps_are_stripped():
    raw = "2026-10-25T19:40:22.4286795Z \x1b[31mFAILED\x1b[0m x::y - boom"
    assert _lines(raw) == ["FAILED x::y - boom"]


def _tests_dir(root, files):
    d = root / "tests"
    d.mkdir()
    for name, body in files.items():
        (d / name).write_bytes(body.encode("utf-8"))
    return d


def _tree(root, **defaults):
    """A stand-in checkout: just enough `digitizer_core` for config_defaults()."""
    pkg = root / "digitizer_core"
    pkg.mkdir(parents=True)
    fields = "".join(f"    {k}: bool = {v}\n" for k, v in defaults.items()) or "    pass\n"
    (pkg / "__init__.py").write_text(
        "from dataclasses import dataclass\n\n@dataclass\nclass PipelineConfig:\n" + fields,
        encoding="utf-8")
    return root


PIN_FILE = f'''"""pins"""
BOWL_ON_MD5 = "{OLD}"      # captured on main
BOWL_OFF_MD5 = "{OLD2}"
NOTE = "café"
'''
PIN_NAME = "test_outline_line_art_guard.py"


def _plan(tmp_path, nodes, files=None, log=PRE_HEXREPR_LOG, **kw):
    tests = _tests_dir(tmp_path, files or {PIN_NAME: PIN_FILE})
    entries = ci_repin.summary_entries(_lines(log))
    return tests, ci_repin.plan(entries, nodes, tests, explained=kw.pop("explained", "flip"), **kw)


def test_the_ledger_row_is_old_new_and_explained_by(tmp_path):
    _tests, rows = _plan(tmp_path, [N1])
    (row,) = rows
    assert (row.node, row.old, row.new, row.explained_by, row.refused) == (N1, OLD, NEW, "flip", "")


def test_orientation_comes_from_the_source_not_from_which_side_pytest_put_it(tmp_path):
    # `assert PIN == computed`: the pin is on the left this time
    _tests, rows = _plan(tmp_path, [N1], log=_hexrepr_log((N1, OLD, NEW)))
    assert (rows[0].old, rows[0].new) == (OLD, NEW)


def test_neither_hash_in_the_tests_means_no_pin_to_move(tmp_path):
    _tests, rows = _plan(tmp_path, [N1], files={"test_other.py": "X = 1\n"})
    assert rows[0].refused and "neither" in rows[0].refused
    assert rows[0].old == rows[0].new == ""


def test_both_hashes_in_the_tests_cannot_be_oriented(tmp_path):
    body = PIN_FILE + f'ELSEWHERE = "{NEW}"\n'
    _tests, rows = _plan(tmp_path, [N1], files={PIN_NAME: body})
    assert rows[0].refused and "both" in rows[0].refused


def test_a_node_the_run_did_not_fail_is_refused(tmp_path):
    _tests, rows = _plan(tmp_path, ["tests/test_nope.py::test_x"])
    assert rows[0].refused and "did not fail" in rows[0].refused


def test_a_pin_held_in_two_places_is_not_moved_without_asking(tmp_path):
    files = {PIN_NAME: PIN_FILE + f'AGAIN = "{OLD}"\n'}
    _tests, rows = _plan(tmp_path, [N1], files=files)
    assert rows[0].refused and "2 occurrences" in rows[0].refused
    again = tmp_path / "again"
    again.mkdir()
    _tests, rows = _plan(again, [N1], files=files, all_occurrences=True)
    assert rows[0].refused == ""


def test_one_pin_cannot_take_two_values(tmp_path):
    # N1 moves OLD to NEW, N2 moves OLD to something else
    log = _hexrepr_log((N1, NEW, OLD), (N2, "1" * 32, OLD))
    _tests, rows = _plan(tmp_path, [N1, N2], log=log)
    assert all("two values" in r.refused for r in rows)


def test_two_nodes_sharing_a_pin_and_a_new_value_make_one_edit(tmp_path):
    log = _hexrepr_log((N1, NEW, OLD), (N2, NEW, OLD))
    _tests, rows = _plan(tmp_path, [N1, N2], log=log)
    assert [r.refused for r in rows] == ["", ""]
    edits = ci_repin.patch(rows)
    (path,) = edits
    assert edits[path][1].count(NEW.encode()) == 1


def _argv(tmp_path, trees, *nodes, extra=()):
    tests = _tests_dir(tmp_path, {PIN_NAME: PIN_FILE})
    log = tmp_path / "shard4.log"
    log.write_text(PRE_HEXREPR_LOG, encoding="utf-8")
    argv = ["12345", *nodes, "--log", str(log), "--tests-dir", str(tests),
            "--base-tree", str(trees[0]), "--head-tree", str(trees[1]), *extra]
    return tests / PIN_NAME, argv


@pytest.fixture
def same_trees(tmp_path):
    return (_tree(tmp_path / "base", flag_a=False), _tree(tmp_path / "head", flag_a=False))


def test_dry_run_changes_nothing_and_apply_changes_exactly_the_pin(tmp_path, same_trees, capsys):
    pin_file, argv = _argv(tmp_path, same_trees, N1)
    before = pin_file.read_bytes()
    assert ci_repin.main(argv) == 0
    out = capsys.readouterr().out
    assert OLD in out and NEW in out and "UNEXPLAINED" in out
    assert "--- " in out and "+++ " in out            # the patch is shown
    assert pin_file.read_bytes() == before            # never on its own
    assert ci_repin.main(argv + ["--apply"]) == 0
    after = pin_file.read_bytes()
    assert after == before.replace(OLD.encode(), NEW.encode())
    assert "café".encode() in after                    # bytes untouched, no mojibake / BOM


def test_a_refused_row_makes_the_exit_code_one_and_writes_nothing(tmp_path, same_trees, capsys):
    pin_file, argv = _argv(tmp_path, same_trees, N1, N_TRUNC, extra=["--apply"])
    before = pin_file.read_bytes()
    assert ci_repin.main(argv) == 1
    assert "re-run" in capsys.readouterr().out
    assert pin_file.read_bytes() == before            # all or nothing


def test_no_node_ids_lists_the_candidates_and_stops(tmp_path, capsys):
    log = tmp_path / "shard4.log"
    log.write_text(PRE_HEXREPR_LOG, encoding="utf-8")
    assert ci_repin.main(["12345", "--log", str(log), "--tests-dir", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert N1 in out and N2 in out and N_TRUNC in out
    assert N_NUM not in out                      # not a hash mismatch: nothing to re-pin


def test_explained_by_reads_flip_only_when_a_default_moved(tmp_path):
    base = _tree(tmp_path / "b", flag_a=False)
    same = _tree(tmp_path / "s", flag_a=False)
    flipped = _tree(tmp_path / "f", flag_a=True)
    label, moved = ci_repin.explain(base, same)
    assert label == "UNEXPLAINED: a regression until shown otherwise" and moved == {}
    label, moved = ci_repin.explain(base, flipped)
    assert label == "flip" and moved == {"flag_a": (False, True)}


def test_the_run_logs_come_from_the_failed_jobs_of_the_run():
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)
        out = ""
        if cmd[:3] == ["gh", "run", "view"]:
            out = json.dumps({"jobs": [
                {"databaseId": 11, "name": "digitizer shard 4/6", "conclusion": "failure"},
                {"databaseId": 12, "name": "digitizer shard 1/6", "conclusion": "success"},
                {"databaseId": 13, "name": "engine", "conclusion": "failure"}]})
        elif cmd[:2] == ["gh", "api"]:
            out = f"log of {cmd[-1]}"
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    logs = ci_repin.fetch_logs("999", "KS-Three/EMB-Bot", run=fake)
    assert len(logs) == 2 and any("/jobs/11/logs" in log for log in logs)
    assert not any("/jobs/12/logs" in " ".join(c) for c in calls)
    assert any("--allow-escape-sequences" in c for c in calls)


# ------------------------------------------------- shard plan (tests/_ci_shard.py)

def test_a_file_with_no_recorded_time_is_weighed_at_the_75th_percentile():
    durations = {"a.py": 1.0, "b.py": 2.0, "c.py": 3.0, "d.py": 4.0}
    files = set(durations) | {"new.py"}
    assert _ci_shard.unknown_weight(durations, files) == 3.0
    assert _ci_shard.weights(files, durations)["new.py"] == 3.0
    assert _ci_shard.weights(files, durations)["b.py"] == 2.0
    # a duration for a file that is no longer collected does not move the percentile
    assert _ci_shard.unknown_weight({**durations, "gone.py": 99.0}, files) == 3.0


def test_with_nothing_measured_every_file_weighs_one():
    assert _ci_shard.weights({"a.py", "b.py"}, {}) == {"a.py": 1.0, "b.py": 1.0}


def test_assign_still_covers_every_file_once():
    files = {f"t{i}.py" for i in range(20)}
    out = _ci_shard.assign(files, 6, {f"t{i}.py": float(i) for i in range(15)})
    assert set(out) == files and set(out.values()) <= set(range(6))


def test_more_than_five_percent_unmeasured_is_a_warning_with_the_fix():
    durations = {f"t{i}.py": 1.0 for i in range(19)}
    one_in_twenty = {f"t{i}.py" for i in range(20)}
    assert _ci_shard.unmeasured_warning(durations, one_in_twenty) is None       # 5.0%: at the line
    two_in_twenty = one_in_twenty | {"extra.py"}
    msg = _ci_shard.unmeasured_warning(durations, two_in_twenty)                 # 2 of 21: 9.5%
    assert msg and "2 of 21" in msg and "ci_shard_durations" in msg


def _items(*files):
    return [SimpleNamespace(nodeid=f"{f}::test_x") for f in files]


def _config(worker=False):
    return SimpleNamespace(hook=SimpleNamespace(pytest_deselected=lambda items: None))


def test_the_shard_hook_warns_when_the_durations_have_gone_stale(tmp_path, monkeypatch):
    stale = tmp_path / "durations.json"
    stale.write_text(json.dumps({"tests/test_a.py": 5.0}))
    monkeypatch.setattr(_ci_shard, "DURATIONS", stale)
    monkeypatch.setenv("DIGITIZER_SHARD", "1/2")
    items = _items("tests/test_a.py", "tests/test_b.py", "tests/test_c.py")
    with pytest.warns(UserWarning, match="unmeasured"):
        _ci_shard.pytest_collection_modifyitems(_config(), items)


def test_the_shard_hook_is_quiet_when_the_durations_are_fresh(tmp_path, monkeypatch):
    fresh = tmp_path / "durations.json"
    fresh.write_text(json.dumps({"tests/test_a.py": 5.0, "tests/test_b.py": 3.0}))
    monkeypatch.setattr(_ci_shard, "DURATIONS", fresh)
    monkeypatch.setenv("DIGITIZER_SHARD", "1/2")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _ci_shard.pytest_collection_modifyitems(_config(), _items("tests/test_a.py", "tests/test_b.py"))


# ----------------------------------------------- tools/ci_shard_durations.py
def _junit(path, times):
    cases = "".join(f'<testcase classname="{c}" name="t" time="{t}"/>' for c, t in times.items())
    path.write_text(f'<testsuites><testsuite>{cases}</testsuite></testsuites>', encoding="utf-8")
    return path


def _repo(tmp_path, names):
    (tmp_path / "tests").mkdir()
    for n in names:
        (tmp_path / "tests" / n).write_text("", encoding="utf-8")
    return tmp_path


def test_the_plan_scores_each_shard_by_the_timings_it_is_given():
    files = {"a.py", "b.py", "c.py", "d.py"}
    durations = {"a.py": 40.0, "b.py": 30.0, "c.py": 20.0, "d.py": 10.0}
    plan = ci_shard_durations.plan(files, 2, durations, durations)
    assert sorted(plan["loads"]) == [50.0, 50.0] and plan["max"] == 50.0
    # the same assignment judged by the truth: the worst shard is the one that was a bad guess
    truth = {"a.py": 40.0, "b.py": 30.0, "c.py": 20.0, "d.py": 60.0}
    wrong = ci_shard_durations.plan(files, 2, {"a.py": 40.0, "b.py": 30.0, "c.py": 20.0, "d.py": 10.0}, truth)
    assert wrong["max"] > plan["max"] and wrong["max"] == max(wrong["loads"])


def test_the_refresh_covers_the_current_files_and_prints_the_plan_before_and_after(tmp_path, capsys):
    root = _repo(tmp_path, ["test_a.py", "test_b.py", "test_c.py", "test_new.py"])
    out = root / "tests" / ".shard_durations.json"
    out.write_text(json.dumps({"tests/test_a.py": 10.0, "tests/test_gone.py": 99.0}))
    xml = _junit(tmp_path / "s1.xml", {"tests.test_a": 12.0, "tests.test_b": 8.0, "tests.test_c": 4.0})
    ci_shard_durations.main([str(xml)], root=root, n=2)
    written = json.loads(out.read_text())
    assert written == {"tests/test_a.py": 12.0, "tests/test_b.py": 8.0, "tests/test_c.py": 4.0}
    text = capsys.readouterr().out
    assert "before" in text and "after" in text and "max shard" in text
    assert "1 of 4" in text and "unmeasured" in text              # test_new.py has no timing yet


def test_a_refresh_that_leaves_more_than_five_percent_unmeasured_says_so(tmp_path, capsys):
    root = _repo(tmp_path, [f"test_{i}.py" for i in range(10)])
    xml = _junit(tmp_path / "s1.xml", {f"tests.test_{i}": 1.0 for i in range(9)})
    ci_shard_durations.main([str(xml)], root=root, n=2)
    assert "WARNING" in capsys.readouterr().out                    # 1 of 10 = 10%


def test_a_fresh_refresh_does_not_warn(tmp_path, capsys):
    root = _repo(tmp_path, ["test_a.py", "test_b.py"])
    xml = _junit(tmp_path / "s1.xml", {"tests.test_a": 1.0, "tests.test_b": 2.0})
    ci_shard_durations.main([str(xml)], root=root, n=2)
    assert "WARNING" not in capsys.readouterr().out
