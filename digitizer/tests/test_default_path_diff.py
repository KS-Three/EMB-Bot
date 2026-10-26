"""tools/default_path_diff.py on two tiny stand-in trees (W3-05 part D).

The real worker digitizes artwork for minutes; these trees hold a one-line
"engine" (the md5 of the artwork plus whatever `default.txt` says), so what is
under test is the machinery: archive the merge-base, run each job in its own
process, compare, drop a job that is not repeatable, and report.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools import default_path_diff as dpd

#: stands in for dpd.WORKER: reads `default.txt` from the tree it runs in, adds any
#: --set, and folds in its pid for a job named `*flaky*` so a repeat differs
TINY_WORKER = r'''
import hashlib, json, os, sys
spec = json.loads(sys.argv[1])
if "boom" in spec["art"]:
    sys.exit("engine exploded")
default = open("default.txt").read().strip()
body = open(spec["art"], "rb").read()
if "flaky" in spec["art"]:
    default += f"/pid{os.getpid()}"             # a different process, a different answer
sets = json.dumps(spec["sets"], sort_keys=True)
digest = hashlib.md5(body + default.encode() + sets.encode()).hexdigest()
print("noise on stdout before the result line")
print("RESULT " + json.dumps({"plan_md5": digest, "dst_md5": digest[::-1], "stitches": len(body),
                              "color_changes": 2, "dst_trims": 1, "secs": 0.1,
                              "sets": spec["sets"]}))
'''


def _tree(root: Path, default="A", arts=("alpha", "beta")):
    root.mkdir(parents=True)
    (root / "default.txt").write_text(default, encoding="utf-8")
    for a in arts:
        (root / f"{a}.png").write_bytes(a.encode() * 4)
    return root


def _jobs(*names, stable=()):
    return [dpd.Job(name=n, art=f"{n}.png", width=60.0, garment="hat_front", stable_check=n in stable)
            for n in names]


def _run(base, head, jobs, sets=None):
    return dpd.run_jobs(base, head, jobs, sets or {}, worker_code=TINY_WORKER, procs=2)


def test_identical_trees_report_every_job_identical(tmp_path):
    base, head = _tree(tmp_path / "b"), _tree(tmp_path / "h")
    rows = _run(base, head, _jobs("alpha", "beta"))
    assert [r["status"] for r in rows] == ["identical", "identical"]
    assert all(r["differs"] == [] for r in rows)


def test_a_changed_default_makes_that_job_differ(tmp_path):
    base, head = _tree(tmp_path / "b"), _tree(tmp_path / "h", default="B")
    rows = _run(base, head, _jobs("alpha", "beta"))
    assert [r["status"] for r in rows] == ["DIFFERS", "DIFFERS"]
    assert "plan_md5" in rows[0]["differs"] and "dst_md5" in rows[0]["differs"]
    assert "stitches" not in rows[0]["differs"]            # only what moved is named


def test_the_artwork_is_the_heads_for_both_sides_so_a_difference_is_the_engine(tmp_path):
    base, head = _tree(tmp_path / "b"), _tree(tmp_path / "h")
    (base / "beta.png").write_bytes(b"a different picture in the base tree")
    rows = {r["name"]: r for r in _run(base, head, _jobs("alpha", "beta"))}
    assert rows["alpha"]["status"] == rows["beta"]["status"] == "identical"


def test_set_repeats_head_with_the_flag_so_off_can_be_checked_against_base(tmp_path):
    base, head = _tree(tmp_path / "b"), _tree(tmp_path / "h")
    rows = _run(base, head, _jobs("alpha"), sets={"some_flag": False})
    assert rows[0]["status"] == "DIFFERS"                   # head + flag is not base (the tiny engine hashes sets)
    assert rows[0]["head"]["plan_md5"] != rows[0]["base"]["plan_md5"]


def test_the_set_goes_to_head_only(tmp_path):
    base, head = _tree(tmp_path / "b"), _tree(tmp_path / "h")
    (row,) = _run(base, head, _jobs("alpha"), sets={"x": 1})
    assert row["base"]["sets"] == {} and row["head"]["sets"] == {"x": 1}


def test_a_job_that_is_not_repeatable_is_dropped_and_listed(tmp_path):
    base, head = _tree(tmp_path / "b", arts=("flaky",)), _tree(tmp_path / "h", arts=("flaky",))
    rows = _run(base, head, _jobs("flaky", stable=("flaky",)))
    (row,) = rows
    assert row["status"] == "unstable"
    assert row["repeat_differs"]                              # which fields the two head runs disagreed on
    summary = dpd.summarize(rows)
    assert summary["dropped"] == ["flaky"] and summary["identical"] == 0 and summary["differs"] == 0


def test_a_repeatable_job_with_the_check_on_passes_it(tmp_path):
    base, head = _tree(tmp_path / "b"), _tree(tmp_path / "h")
    (row,) = _run(base, head, _jobs("alpha", stable=("alpha",)))
    assert row["status"] == "identical" and row["repeatable"] is True


def test_a_job_that_crashes_is_an_error_not_a_pass(tmp_path):
    base, head = _tree(tmp_path / "b", arts=("boom",)), _tree(tmp_path / "h", arts=("boom",))
    rows = _run(base, head, _jobs("boom"))
    assert rows[0]["status"] == "error" and "engine exploded" in rows[0]["error"]
    assert dpd.summarize(rows)["errors"] == ["boom"]


def test_the_markdown_table_has_a_row_per_job_and_a_verdict(tmp_path):
    base, head = _tree(tmp_path / "b"), _tree(tmp_path / "h", default="B")
    rows = _run(base, head, _jobs("alpha", "beta"))
    md = dpd.markdown(rows, meta={"base": "aaaa111", "head": "bbbb222", "sets": {}})
    assert md.count("\n| alpha") == 1 and md.count("\n| beta") == 1
    assert "DIFFERS" in md and "aaaa111" in md and "bbbb222" in md
    assert "advisory" in md.lower()


def test_main_writes_the_json_artifact_and_the_summary_and_is_advisory(tmp_path, capsys):
    base, head = _tree(tmp_path / "b"), _tree(tmp_path / "h", default="B")
    out_json, out_md = tmp_path / "r.json", tmp_path / "r.md"
    rc = dpd.main(["--base-tree", str(base), "--head-tree", str(head), "--json", str(out_json),
                   "--md", str(out_md), "--only", "alpha,beta"], worker_code=TINY_WORKER,
                  jobs=_jobs("alpha", "beta"))
    assert rc == 0                                           # a moved default is information, not a failure
    data = json.loads(out_json.read_text())
    assert [j["status"] for j in data["jobs"]] == ["DIFFERS", "DIFFERS"]
    assert data["summary"]["differs"] == 2
    assert "| alpha" in out_md.read_text()
    assert "DIFFERS" in capsys.readouterr().out
    rc = dpd.main(["--base-tree", str(base), "--head-tree", str(head), "--fail-on-diff"],
                  worker_code=TINY_WORKER, jobs=_jobs("alpha"))
    assert rc == 1


def test_main_exits_one_when_a_job_errors_even_though_diffs_are_advisory(tmp_path):
    base, head = _tree(tmp_path / "b", arts=("boom",)), _tree(tmp_path / "h", arts=("boom",))
    assert dpd.main(["--base-tree", str(base), "--head-tree", str(head)], worker_code=TINY_WORKER,
                    jobs=_jobs("boom")) == 1


# ---- the merge-base archive, on a real (tiny) git history
def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def test_the_merge_base_tree_is_the_fork_point_not_the_branch_tip(tmp_path):
    repo = tmp_path / "repo"
    (repo / "digitizer").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / "digitizer" / "default.txt").write_text("fork", encoding="utf-8")
    (repo / "elsewhere.txt").write_text("not in the archive", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "fork point")
    fork = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-qb", "feature")
    (repo / "digitizer" / "default.txt").write_text("feature tip", encoding="utf-8")
    _git(repo, "commit", "-qam", "feature")
    _git(repo, "checkout", "-q", "main")
    (repo / "digitizer" / "default.txt").write_text("main moved on", encoding="utf-8")
    _git(repo, "commit", "-qam", "main moves")
    _git(repo, "checkout", "-q", "feature")
    with dpd.merge_base_tree("main", repo=repo) as tree:
        assert (tree / "default.txt").read_text(encoding="utf-8") == "fork"
        assert not (tree.parent / "elsewhere.txt").exists()
        assert dpd.last_merge_base == fork
    assert not tree.exists()                                   # the temp dir is gone


def test_the_fixed_job_set_is_what_the_brief_names():
    names = [j.name for j in dpd.JOBS]
    assert [j.art for j in dpd.JOBS if j.stable_check] == [
        "testdata/logo_whitebg.png", "testdata/logo_alpha.png", "testdata/ribbon_curve.png"]
    becker = [j for j in dpd.JOBS if "becker" in j.art]
    assert {j.garment for j in becker} == {"left_chest", "hat_front"}
    assert all(j.width < 100 for j in becker)                  # reduced: 100 mm is ~3 minutes a digitize
    assert not any("reference" in j.art for j in dpd.JOBS)     # the pro's previews are not inputs
    assert len(names) == len(set(names))
