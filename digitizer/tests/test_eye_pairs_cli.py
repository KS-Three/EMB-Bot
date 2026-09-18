import copy
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eye_pairs import __main__ as cli  # noqa: E402
from tools.eye_pairs.pairs import BASE, append_pick, design_hash  # noqa: E402

from .conftest import draw_tiny_logo  # noqa: E402

# Measured 2026-09-17 on this image: fill_angle_deg=45 changes the stitches,
# design_angle=True does not. The second is the identical-skip rule's test.
# TWO ref arms on different commits: review finding 6 (2026-09-17) — the
# runner used to be memoised on "any ref built", and the analysis picked the
# ref bucket by name.
ARMS = {"angle45": {"fill_angle_deg": 45.0}, "inert": {"design_angle": True},
        "ref_a": {"__ref__": "aaaaaaa"}, "ref_b": {"__ref__": "bbbbbbb"}}
DELTA = {"aaaaaaa": 7, "bbbbbbb": 9}
# What each fake ref engine "measured" about where it ran. `bbbbbbb` is an
# old commit whose requirements.txt no longer matches HEAD.
ENV = {c: {"ref": c, "rembg_venv_main": False, "rembg_venv_ref": False,
           "requirements_differ": c == "bbbbbbb"} for c in DELTA}


def fake_factory(out: Path, seen: dict):
    """A ref-engine factory that answers per COMMIT: the base design nudged
    by a commit-specific amount, so the two refs differ from the base and
    from each other."""
    def factory(commit: str):
        seen.setdefault("commits", []).append(commit)

        def runner(image, width_mm, garment, max_colors):
            seen["asked"] = (Path(image).name, width_mm, garment, max_colors)
            design = copy.deepcopy(json.loads(
                (out / "designs" / f"tiny__{BASE}.json").read_text()))
            design["stitches"][0]["x"] += DELTA[commit]
            return design

        def closer():
            seen.setdefault("closed", []).append(commit)

        return runner, closer, dict(ENV[commit])
    return factory


def fingerprint(out: Path) -> dict[str, bytes]:
    """Every file of a sitting that a test could disturb, by content."""
    return {p.relative_to(out).as_posix(): p.read_bytes()
            for p in sorted(out.rglob("*")) if p.is_file() and p.parent.name != "renders"}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory, tiny_logo):
    """ONE rendered + paired sitting for the whole module (it costs ~10 s).
    Shared, so READ-ONLY: a test that writes — a pick, an edited features
    row, a second `--pair` — copies it under `tmp_path` first. An early
    version cleaned its picks up with a bare `.unlink()` instead, which
    leaves them behind for every later test the moment an assert fails
    first (review 2026-09-17). The teardown below is the tripwire."""
    out = tmp_path_factory.mktemp("cli") / "out"
    seen: dict = {}
    n_arms = cli.render(out, cases=[("tiny", tiny_logo, 40.0, "left_chest")], arms=ARMS,
                        ref_factory=fake_factory(out, seen))
    n_pairs = cli.pair(out)
    before = fingerprint(out)
    yield out, tiny_logo, n_arms, n_pairs, seen
    after = fingerprint(out)
    assert sorted(after) == sorted(before), "a test added or removed a file in the SHARED sitting"
    assert after == before, "a test rewrote a file in the SHARED sitting; copy it to tmp_path"


def test_render_digitizes_and_pair_builds_the_sitting(rendered):
    out, _art, n_arms, n_pairs, seen = rendered
    assert n_arms == 5                                   # base + 4 arms
    sealed = json.loads((out / "arms.json").read_text())
    kinds = sorted(s["kind"] for s in sealed.values())
    # live: angle45, ref_a, ref_b. identical: 1 (one fixture). repeats: min(8, 3).
    assert kinds == ["identical", "live", "live", "live", "repeat", "repeat", "repeat"]
    assert n_pairs == 7
    assert json.loads((out / "skipped.json").read_text()) == [
        {"fixture": "tiny", "arm": "inert", "reason": "identical_to_base"}]
    assert seen["asked"] == ("tiny.png", 40.0, "left_chest", 6)
    public = json.loads((out / "pairs.json").read_text())
    for p in public:
        for k in ("left", "right", "art"):
            assert (out / "img" / p[k]).stat().st_size > 0
    assert "tiny" not in (out / "pairs.json").read_text()
    sitting = json.loads((out / "sitting.json").read_text())
    assert sitting["n_pairs"] == 7
    from datetime import datetime
    assert datetime.fromisoformat(sitting["built_ts"]).utcoffset() is not None


def test_the_picker_starts_on_exactly_what_pair_wrote(rendered):
    """`--serve` refuses a sitting whose sealed map is not the one
    `sitting.json` records; this is the other half — what `--pair` really
    writes must pass that check, images included."""
    from tools.eye_pairs.server import make_server
    out, _art, _n, _np, _seen = rendered
    httpd = make_server(out, port=0)
    httpd.server_close()


def test_each_ref_arm_runs_its_own_commit_and_is_marked_design_only(rendered):
    out, _art, _n, _np, seen = rendered
    assert sorted(seen["commits"]) == ["aaaaaaa", "bbbbbbb"]
    assert sorted(seen["closed"]) == ["aaaaaaa", "bbbbbbb"]
    feats = json.loads((out / "features.json").read_text())["tiny"]
    assert feats["ref_a"]["design_only"] is True and feats["ref_b"]["design_only"] is True
    assert not feats[BASE].get("design_only") and not feats["angle45"].get("design_only")
    da = json.loads((out / "designs" / "tiny__ref_a.json").read_text())
    db = json.loads((out / "designs" / "tiny__ref_b.json").read_text())
    assert da["stitches"][0]["x"] - db["stitches"][0]["x"] == DELTA["aaaaaaa"] - DELTA["bbbbbbb"]
    sealed = json.loads((out / "arms.json").read_text())
    for s in sealed.values():
        arm = s["right_arm"] if s["left_arm"] == BASE else s["left_arm"]
        assert s["design_only"] == (arm in ("ref_a", "ref_b"))


def test_features_are_sealed_per_arm_and_the_ref_arm_is_design_only(rendered):
    out, _art, _n, _np, _seen = rendered
    feats = json.loads((out / "features.json").read_text())["tiny"]
    assert "preflight_raw_score" in feats[BASE] and "wall_s" in feats[BASE]
    assert "preflight_raw_score" not in feats["ref_a"]
    assert feats["ref_a"]["stitches"] == feats[BASE]["stitches"]
    assert feats[BASE]["source_sha256"] == feats["ref_a"]["source_sha256"]
    assert feats[BASE]["schema"] == cli.FEATURES_SCHEMA


def test_a_second_render_is_all_cache(rendered, monkeypatch):
    out, art, n_arms, _np, _seen = rendered

    def boom(*_a, **_k):
        raise AssertionError("a finished arm must not be digitized again")

    monkeypatch.setattr(cli, "digitize_once", boom)
    assert cli.render(out, cases=[("tiny", art, 40.0, "left_chest")], arms=ARMS,
                      ref_factory=boom) == n_arms


def test_a_changed_source_image_is_a_cache_miss(rendered, tmp_path, monkeypatch):
    """Review finding 7 (2026-09-17): the cache was keyed on the fixture
    NAME alone, so a re-exported image under the same name stayed 'cached'."""
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out2"
    shutil.copytree(out, out2)
    art2 = draw_tiny_logo(tmp_path / "tiny.png", extra_dot=True)  # same NAME, new bytes
    calls = []
    real = cli.digitize_once

    def counting(image, cfg):
        calls.append(cfg)
        return real(image, cfg)

    monkeypatch.setattr(cli, "digitize_once", counting)
    seen: dict = {}
    cli.render(out2, cases=[("tiny", art2, 40.0, "left_chest")], arms=ARMS,
               ref_factory=fake_factory(out2, seen))
    assert len(calls) == 3                       # base + angle45 + inert, all redone
    assert sorted(seen["commits"]) == ["aaaaaaa", "bbbbbbb"]
    feats = json.loads((out2 / "features.json").read_text())["tiny"]
    old = json.loads((out / "features.json").read_text())["tiny"]
    assert feats[BASE]["source_sha256"] != old[BASE]["source_sha256"]


def test_a_schema_bump_is_a_cache_miss(rendered, tmp_path, monkeypatch):
    out, art, _n, _np, _seen = rendered
    out2 = tmp_path / "out3"
    shutil.copytree(out, out2)
    monkeypatch.setattr(cli, "FEATURES_SCHEMA", cli.FEATURES_SCHEMA + 1)
    calls = []
    real = cli.digitize_once
    monkeypatch.setattr(cli, "digitize_once",
                        lambda image, cfg: (calls.append(1), real(image, cfg))[1])
    cli.render(out2, cases=[("tiny", art, 40.0, "left_chest")], arms=ARMS,
               ref_factory=fake_factory(out2, {}))
    assert len(calls) == 3


def test_each_ref_row_carries_the_environment_it_was_made_under(rendered):
    """Review 2026-09-17: whether the old engine's arm was environment-
    confounded was INFERRED at reveal from today's design class. The facts
    are recorded on the row when it is rendered, so a resumed render cannot
    attribute one call's environment to another call's rows."""
    out, _art, _n, _np, _seen = rendered
    feats = json.loads((out / "features.json").read_text())["tiny"]
    assert feats["ref_a"]["env"] == ENV["aaaaaaa"]
    assert feats["ref_b"]["env"] == ENV["bbbbbbb"]
    assert "env" not in feats[BASE] and "env" not in feats["angle45"]


def test_a_ref_row_with_no_recorded_environment_is_rendered_again(rendered, tmp_path, monkeypatch):
    """A row rendered before the environment was recorded would read
    'unknown' forever. It is the only kind of row this costs a re-run —
    NOT a schema bump, which would re-digitize every flag arm too."""
    out, art, n_arms, _np, _seen = rendered
    out2 = tmp_path / "out_env"
    shutil.copytree(out, out2)
    feats = json.loads((out2 / "features.json").read_text())
    feats["tiny"]["ref_a"].pop("env")
    (out2 / "features.json").write_text(json.dumps(feats))

    def boom(*_a, **_k):
        raise AssertionError("a flag arm must stay cached")

    monkeypatch.setattr(cli, "digitize_once", boom)
    seen: dict = {}
    assert cli.render(out2, cases=[("tiny", art, 40.0, "left_chest")], arms=ARMS,
                      ref_factory=fake_factory(out2, seen)) == n_arms
    assert seen["commits"] == ["aaaaaaa"]                 # ref_b kept its row
    again = json.loads((out2 / "features.json").read_text())["tiny"]
    assert again["ref_a"]["env"] == ENV["aaaaaaa"]


def picked_copy(out: Path, dest: Path, edit=None) -> Path:
    """A finished sitting in a private copy; `edit(feats)` rewrites the
    sealed features first."""
    shutil.copytree(out, dest)
    if edit:
        feats = json.loads((dest / "features.json").read_text())
        edit(feats)
        (dest / "features.json").write_text(json.dumps(feats))
    for p in json.loads((dest / "pairs.json").read_text()):
        append_pick(dest / "picks.jsonl", p["pair"], "L", 100)
    return dest


def test_reveal_derives_confounded_from_recorded_facts_and_prints_which_fired(
        rendered, tmp_path, capsys):
    out, _art, _n, _np, _seen = rendered
    res = cli.reveal(picked_copy(out, tmp_path / "out_facts"))
    by_arm = {r["arm"]: r for r in res["ref_table"]}
    assert by_arm["ref_a"]["confounded"] is False and by_arm["ref_a"]["confounded_why"] == []
    assert by_arm["ref_b"]["confounded"] is True
    assert "requirements.txt" in by_arm["ref_b"]["confounded_why"][0]
    printed = capsys.readouterr().out
    assert "requirements.txt" in printed and "CONFOUNDED" in printed
    block_a = printed.split("TODAY vs ref_a")[1].split("TODAY vs")[0]
    assert "CONFOUNDED" not in block_a and "no recorded fact" in block_a


def test_a_photo_fixture_is_confounded_only_by_a_measured_rembg_asymmetry(
        rendered, tmp_path, capsys):
    """The old proxy's false positive, end to end: a photo-class fixture on
    a checkout where NEITHER engine had the rembg venv is not confounded."""
    out, _art, _n, _np, _seen = rendered

    def photo(main: bool):
        def edit(feats):
            feats["tiny"][BASE]["design_class"] = "photo_subject"
            feats["tiny"]["ref_a"]["env"]["rembg_venv_main"] = main
        return edit

    res = cli.reveal(picked_copy(out, tmp_path / "out_sym", photo(main=False)))
    assert {r["arm"]: r["confounded"] for r in res["ref_table"]}["ref_a"] is False
    capsys.readouterr()
    res = cli.reveal(picked_copy(out, tmp_path / "out_asym", photo(main=True)))
    row = {r["arm"]: r for r in res["ref_table"]}["ref_a"]
    assert row["confounded"] is True and "rembg" in row["confounded_why"][0]
    assert "rembg" in capsys.readouterr().out


def test_an_unrecorded_environment_is_reported_as_unknown(rendered, tmp_path, capsys):
    out, _art, _n, _np, _seen = rendered
    res = cli.reveal(picked_copy(out, tmp_path / "out_legacy",
                                 lambda feats: feats["tiny"]["ref_a"].pop("env")))
    assert {r["arm"]: r["confounded"] for r in res["ref_table"]}["ref_a"] is None
    assert "UNKNOWN" in capsys.readouterr().out


def test_a_scoped_render_never_rebuilds_the_sitting(rendered, tmp_path):
    """Review finding 3 (2026-09-17): a `--fixtures/--arms` smoke test used
    to reshuffle every pair in the sitting. Render now only digitizes."""
    out, art, _n, _np, _seen = rendered
    out2 = tmp_path / "out4"
    shutil.copytree(out, out2)
    before = (out2 / "arms.json").read_bytes()
    cli.render(out2, cases=[("tiny", art, 40.0, "left_chest")],
               arms={**ARMS, "angle30": {"fill_angle_deg": 30.0}}, only_arms=["angle30"],
               ref_factory=fake_factory(out2, {}))
    assert (out2 / "arms.json").read_bytes() == before
    feats = json.loads((out2 / "features.json").read_text())["tiny"]
    assert "angle30" in feats


# ---- pair() does each piece of work once (review 2026-09-17) ---------------
# It used to re-read and re-hash every design (0.8 MB of JSON each on a real
# logo) and rmtree + re-copy every image, on every call.

def test_render_records_what_would_be_sewn_on_the_row(rendered):
    out, _art, _n, _np, _seen = rendered
    feats = json.loads((out / "features.json").read_text())["tiny"]
    for arm in (BASE, "angle45", "inert", "ref_a", "ref_b"):
        on_disk = json.loads((out / "designs" / f"tiny__{arm}.json").read_text())
        assert feats[arm]["design_hash"] == design_hash(on_disk), arm


def test_pair_reads_the_recorded_hash_and_opens_no_design(rendered, tmp_path, monkeypatch):
    out, _art, _n, n_pairs, _seen = rendered
    out2 = tmp_path / "out_hash"
    shutil.copytree(out, out2)

    def boom(_design):
        raise AssertionError("pair() must not re-hash a design whose hash is on its row")

    monkeypatch.setattr(cli, "design_hash", boom)
    assert cli.pair(out2) == n_pairs
    assert (out2 / "arms.json").read_bytes() == (out / "arms.json").read_bytes()


def test_a_row_rendered_before_the_hash_was_recorded_is_hashed_from_its_design(rendered, tmp_path):
    """No FEATURES_SCHEMA bump came with `design_hash`, so such rows exist."""
    out, _art, _n, n_pairs, _seen = rendered
    out2 = tmp_path / "out_nohash"
    shutil.copytree(out, out2)
    feats = json.loads((out2 / "features.json").read_text())
    for row in feats["tiny"].values():
        row.pop("design_hash")
    (out2 / "features.json").write_text(json.dumps(feats))
    assert cli.pair(out2) == n_pairs
    assert (out2 / "arms.json").read_bytes() == (out / "arms.json").read_bytes()
    assert json.loads((out2 / "skipped.json").read_text()) == [
        {"fixture": "tiny", "arm": "inert", "reason": "identical_to_base"}]


def hardlinks_work(where: Path) -> bool:
    probe, link = where / "probe", where / "probe_link"
    probe.write_text("x")
    try:
        os.link(probe, link)
    except OSError:
        return False
    return True


def test_paired_images_are_hardlinks_where_the_filesystem_allows(rendered, tmp_path):
    if not hardlinks_work(tmp_path):
        pytest.skip("this filesystem has no hardlinks; the copy fallback has its own test")
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out_link"
    shutil.copytree(out, out2)
    shutil.rmtree(out2 / "img")       # copytree brought COPIES, which pair() rightly keeps
    cli.pair(out2)
    sealed = json.loads((out2 / "arms.json").read_text())
    for p in json.loads((out2 / "pairs.json").read_text()):
        s = sealed[p["pair"]]
        assert os.path.samefile(out2 / "img" / p["left"],
                                out2 / "renders" / f"tiny__{s['left_arm']}.jpg")
        assert os.path.samefile(out2 / "img" / p["art"], out2 / "renders" / "tiny__art.png")


def test_images_are_copied_where_hardlinks_are_refused(rendered, tmp_path, monkeypatch):
    out, _art, _n, n_pairs, _seen = rendered
    out2 = tmp_path / "out_copy"
    shutil.copytree(out, out2)
    shutil.rmtree(out2 / "img")

    def refuse(*_a, **_k):
        raise OSError("hardlinks not supported here")

    monkeypatch.setattr(cli.os, "link", refuse)
    assert cli.pair(out2) == n_pairs
    sealed = json.loads((out2 / "arms.json").read_text())
    for p in json.loads((out2 / "pairs.json").read_text()):
        s = sealed[p["pair"]]
        assert (out2 / "img" / p["right"]).read_bytes() == \
            (out2 / "renders" / f"tiny__{s['right_arm']}.jpg").read_bytes()


def test_a_second_pair_places_nothing_again_and_clears_what_no_pair_names(
        rendered, tmp_path, monkeypatch):
    out, _art, _n, n_pairs, _seen = rendered
    out2 = tmp_path / "out_again"
    shutil.copytree(out, out2)
    cli.pair(out2)
    (out2 / "img" / "P999_L.jpg").write_bytes(b"left over from a larger sitting")
    before = {f.name: f.stat().st_mtime_ns for f in (out2 / "img").iterdir()}

    def boom(*_a, **_k):
        raise AssertionError("an image already in place must not be placed again")

    monkeypatch.setattr(cli.os, "link", boom)
    monkeypatch.setattr(cli.shutil, "copy2", boom)
    assert cli.pair(out2) == n_pairs
    after = {f.name: f.stat().st_mtime_ns for f in (out2 / "img").iterdir()}
    assert "P999_L.jpg" not in after
    before.pop("P999_L.jpg")
    assert after == before


def test_a_paired_image_is_a_snapshot_a_later_render_cannot_rewrite(rendered, tmp_path):
    """The price of a hardlink: `cv2.imwrite` rewrites a file IN PLACE, so
    re-rendering an arm would change the picture a live sitting is serving
    (and truncate it mid-write). Renders are replaced atomically instead,
    which leaves the paired link on the old bytes."""
    out, art, _n, _np, _seen = rendered
    out2 = tmp_path / "out_snap"
    shutil.copytree(out, out2)
    shutil.rmtree(out2 / "img")       # so pair() places links, not copytree's copies
    cli.pair(out2)
    sealed = json.loads((out2 / "arms.json").read_text())
    shown = None
    for p in json.loads((out2 / "pairs.json").read_text()):
        s = sealed[p["pair"]]
        if "angle45" in (s["left_arm"], s["right_arm"]):
            shown = out2 / "img" / (p["left"] if s["left_arm"] == "angle45" else p["right"])
            break
    before = shown.read_bytes()
    feats = json.loads((out2 / "features.json").read_text())
    feats["tiny"].pop("angle45")                              # force the arm to render again
    (out2 / "features.json").write_text(json.dumps(feats))
    cli.render(out2, cases=[("tiny", art, 40.0, "left_chest")],
               arms={"angle45": {"fill_angle_deg": 20.0}}, only_arms=["angle45"],
               ref_factory=fake_factory(out2, {}))
    assert (out2 / "renders" / "tiny__angle45.jpg").read_bytes() != before   # it did change
    assert shown.read_bytes() == before
    assert not list((out2 / "renders").glob("*.tmp.*"))


def test_pair_refuses_a_different_sealed_map_over_existing_picks(rendered, tmp_path):
    """Review finding 2 (2026-09-17): the guard compared the PUBLIC lists,
    which are identity-blind — an arm swap at equal count passed."""
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out5"
    shutil.copytree(out, out2)
    append_pick(out2 / "picks.jsonl", "P001", "L", 100)
    assert cli.pair(out2) == 7                              # same map: allowed
    # Swap one arm for another of the same shape: the public list is
    # byte-identical, the sealed map is not.
    feats = json.loads((out2 / "features.json").read_text())
    feats["tiny"]["angle46"] = feats["tiny"].pop("angle45")
    (out2 / "features.json").write_text(json.dumps(feats))
    (out2 / "designs" / "tiny__angle45.json").rename(out2 / "designs" / "tiny__angle46.json")
    (out2 / "renders" / "tiny__angle45.jpg").rename(out2 / "renders" / "tiny__angle46.jpg")
    with pytest.raises(SystemExit, match="REFUSED.*different"):
        cli.pair(out2)


def test_pair_refuses_picks_it_cannot_prove_belong_to_this_sitting(rendered, tmp_path):
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out6"
    shutil.copytree(out, out2)
    append_pick(out2 / "picks.jsonl", "P001", "L", 100)
    (out2 / "sitting.json").unlink()
    with pytest.raises(SystemExit, match="REFUSED.*sitting.json"):
        cli.pair(out2)


def test_reveal_refuses_until_every_pair_is_picked(rendered):
    out, _art, _n, _np, _seen = rendered
    with pytest.raises(SystemExit, match="REFUSED"):
        cli.reveal(out)


def test_reveal_reports_every_section_once_picked(rendered, tmp_path):
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out7"
    shutil.copytree(out, out2)
    for p in json.loads((out2 / "pairs.json").read_text()):
        append_pick(out2 / "picks.jsonl", p["pair"], "L", 100)
    res = cli.reveal(out2)
    assert set(res) >= {"n_pairs", "ceiling", "controls", "primary", "descriptive",
                        "exit_clause", "per_fixture", "flag_table", "ref_table",
                        "exploratory", "skipped"}
    assert res["exploratory"] is None                      # far under 40 pairs
    assert res["ceiling"]["n"] == 3
    assert {row["metric"] for row in res["primary"]} >= {"ragged_mm", "artfid"}
    assert all({"headline", "all_pairs"} <= set(row) for row in res["primary"])
    assert sorted({r["arm"] for r in res["ref_table"]}) == ["ref_a", "ref_b"]
    assert json.loads((out2 / "results.json").read_text())["n_pairs"] == res["n_pairs"]


def test_reveal_prints_the_per_fixture_count_and_the_descriptive_block(rendered, tmp_path, capsys):
    """Review finding 11 (2026-09-17): per_fixture and descriptive were
    computed into results.json and never printed; the spec puts the
    per-fixture count beside each pooled figure."""
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out9"
    shutil.copytree(out, out2)
    for p in json.loads((out2 / "pairs.json").read_text()):
        append_pick(out2 / "picks.jsonl", p["pair"], "L", 100)
    cli.reveal(out2)
    printed = capsys.readouterr().out
    assert "fixtures" in printed and "DESCRIPTIVE" in printed
    assert "kappa_m" in printed and "pe" in printed
    for metric in ("stitches", "cones", "stops"):
        assert metric in printed


def test_reveal_refuses_a_pick_for_a_pair_that_does_not_exist(rendered, tmp_path):
    out, _art, _n, _np, _seen = rendered
    out2 = tmp_path / "out8"
    shutil.copytree(out, out2)
    for p in json.loads((out2 / "pairs.json").read_text()):
        append_pick(out2 / "picks.jsonl", p["pair"], "R", 100)
    append_pick(out2 / "picks.jsonl", "P999", "L", 1)
    with pytest.raises(SystemExit, match="REFUSED.*P999"):
        cli.reveal(out2)


def bare_results(**over) -> dict:
    """The smallest dict `_print` accepts: every section present and empty."""
    res = {"n_pairs": 0, "decided_flag_pairs": 0,
           "ceiling": {"n": 0, "consistent": 0, "share": None},
           "controls": {"identical_n": 0, "identical_tie_rate": None,
                        "identical_left_share": None, "left_share_all": None},
           "primary": [], "descriptive": [], "exit_clause": {}, "per_fixture": {},
           "flag_table": {}, "ref_table": [], "exploratory": None, "skipped": []}
    res.update(over)
    return res


def test_the_exploratory_line_never_prints_a_raw_accuracy_alone(capsys):
    """ROADMAP gate 4 (review 2026-09-17): 'LOFO accuracy 0.93 vs best single
    0.91' was the whole line — no floor, no interval."""
    from tools.eye_pairs import analysis as an

    from .test_eye_pairs_analysis import fit_world, lean_world
    sealed, picks, feats = fit_world(9, 6)
    fit = an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats)
    cli._print(bare_results(exploratory=fit))
    printed = capsys.readouterr().out
    assert "EXPLORATORY" in printed
    assert f"majority baseline {fit['majority_baseline']:.2f}" in printed
    assert "[%.2f, %.2f]" % tuple(fit["lofo_wilson"]) in printed
    assert format(fit["lofo_above_baseline"], "+.2f") in printed
    assert "[%.2f, %.2f]" % tuple(fit["best_single"]["wilson"]) in printed
    assert format(fit["best_single"]["above_baseline"], "+.2f") in printed
    assert "not distinguishable" not in printed

    sealed, picks, feats = lean_world()
    fit = an.exploratory_fit(an.decided_rows(sealed, picks, ref=False), feats)
    cli._print(bare_results(exploratory=fit))
    assert "not distinguishable from the baseline" in capsys.readouterr().out


def test_verify_picks_its_fixture_by_name_not_by_position(monkeypatch, capsys):
    """Review 2026-09-17: `corpus_cases()[1]` happened to be "tires". That
    list is REAL_ART's dict order minus byte-duplicates found at runtime, so
    a new first row — or a duplicate ahead of it — silently moves the drift
    control onto another logo."""
    cases = [("becker", Path("b.png"), 100.0, "left_chest"),
             ("enthusiast", Path("e.png"), 80.0, "left_chest"),
             ("tires", Path("t.png"), 80.0, "left_chest")]
    monkeypatch.setattr(cli, "corpus_cases", lambda: cases)
    asked = []
    monkeypatch.setattr(cli, "verify", lambda image, w, g: asked.append((image, w, g)) or True)
    assert cli.main(["--verify"]) == 0
    assert asked == [(Path("t.png"), 80.0, "left_chest")]
    assert "verifying on tires" in capsys.readouterr().out


def test_verify_says_so_when_its_fixture_has_left_the_corpus(monkeypatch):
    monkeypatch.setattr(cli, "corpus_cases",
                        lambda: [("becker", Path("b.png"), 100.0, "left_chest")])
    monkeypatch.setattr(cli, "verify", lambda *_a: True)
    with pytest.raises(SystemExit, match="REFUSED.*tires"):
        cli.main(["--verify"])


def test_verify_finds_no_drift_on_the_synthetic_image(rendered, capsys):
    _out, art, _n, _np, _seen = rendered
    assert cli.verify(art, 40.0, "left_chest") is True
    printed = capsys.readouterr().out
    # Review finding 8: the artfid family and the refusal are checked too.
    assert "artfid" in printed and "refusal" in printed
