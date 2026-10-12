"""tools.eye_pairs.fresh_sitting: the blinded fresh sitting's generator.

No engine runs here: a fake `render` writes small synthetic designs, and the
real `pair()` (the sealed map, opaque ids, controls) builds the sitting from
them. What is pinned: the pre-registered arms are real knobs and match
`pairs.ARMS`; the judge-facing surface (the page, the pair list, every image
name and byte, every URL the picker will answer) names no arm and no logo;
sides are reproducible for one seed and differ across seeds; Kent's art must
sit in a git-ignored folder; a corpus logo is refused unless the run says it is
a dry run; and the pre-registered analysis reads the directions it was
written with."""
from __future__ import annotations

import dataclasses
import json
import re
import shutil
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core.config import PipelineConfig  # noqa: E402
from tools.eye_pairs import fresh_sitting as fs  # noqa: E402
from tools.eye_pairs import pooled  # noqa: E402
from tools.eye_pairs import server as sv  # noqa: E402
from tools.eye_pairs.pairs import ARMS, BASE, append_pick, design_hash  # noqa: E402

from .test_eye_pairs_density_flow import _design, _rows  # noqa: E402

# Names no page or filename could contain by accident.
LOGOS = [f"Zq{n}x" for n in range(1, 9)]
SMALL = LOGOS[:4]                     # what the build tests use: fewer logos, same code path
ARM_NAMES = sorted(fs.FRESH_ARMS)


@pytest.fixture(autouse=True, scope="module")
def _cheap():
    """A builder test needs the bookkeeping, not eight logos or the raster
    underlay pass: the floor drops to four, `density_flow.measure` skips
    `support` (the dry run reads it for real)."""
    mp = pytest.MonkeyPatch()
    mp.setattr(fs, "MIN_LOGOS", 4)
    real = fs.df.measure
    mp.setattr(fs.df, "measure",
               lambda d, shapes=None, *, support=True: real(d, shapes, support=False))
    yield
    mp.undo()


# ------------------------------------------------------------ the arms ---

def test_every_arm_is_a_real_knob_of_the_right_type():
    fields = {f.name: f for f in dataclasses.fields(PipelineConfig)}
    for arm, cfg in fs.FRESH_ARMS.items():
        for knob, value in cfg.items():
            assert knob in fields, f"{arm}: PipelineConfig has no {knob!r}"
            default = fields[knob].default
            if isinstance(default, bool):
                assert isinstance(value, bool) and value != default, \
                    f"{arm}: {knob} must flip the shipped default {default!r}"
            else:                                    # split_satin_above_mm: float | None
                assert isinstance(value, float) and value != default


def test_the_arms_match_the_sitting_machinery_arms():
    """An edit to `pairs.ARMS` cannot move an arm under a pre-registration."""
    for arm, cfg in fs.FRESH_ARMS.items():
        if arm in fs.ALIASES:
            assert cfg == ARMS[fs.ALIASES[arm]]
        else:
            assert cfg == ARMS[arm], arm


def test_the_alias_arm_has_no_cfg_of_its_own():
    assert fs.ALIASES == {"equal_pitch_columns": "lettering_columns"}
    assert "equal_pitch_columns" not in fs.DEFAULT_ARMS
    assert set(fs.DEFAULT_ARMS) <= set(fs.FRESH_ARMS)


def test_the_long_share_direction_is_the_pre_registered_reverse():
    from tools.eye_pairs import density_flow as df

    assert df.CANDIDATES["long_share"][0] == "higher"          # the hypothesis as first written
    assert fs.directions()["long_share"][0] == "lower"         # the one this sitting tests
    assert fs.PRIMARY_DIRECTIONS == {
        "flow_circvar": "lower", "longest_jump_mm": "lower", "long_share": "lower",
        "trims_per_1000": "lower", "thread_density": "higher"}
    assert fs.directions()["flow_circvar"][0] == "lower"


# ------------------------------------------------------------ manifest ---

def write_manifest(folder: Path, *, names=SMALL, arms=None, seed=20261012, dry_run=False,
                   **extra) -> Path:
    logos = folder / "logos"
    logos.mkdir(parents=True, exist_ok=True)
    img = np.full((40, 60, 3), 255, np.uint8)
    cv2.rectangle(img, (10, 10), (50, 30), (0, 0, 0), -1)
    for n, name in enumerate(names):
        cv2.imwrite(str(logos / f"{name}.png"), np.roll(img, n, axis=0))      # distinct bytes
    m = {"tag": "fresh-test", "seed": seed, "dry_run": dry_run,
         "logos": [{"name": n, "file": f"{n}.png", "width_mm": 80, "garment": "left_chest"}
                   for n in names], **extra}
    if arms is not None:
        m["arms"] = arms
    path = folder / "manifest.json"
    path.write_text(json.dumps(m), encoding="utf-8")
    return path


def test_a_good_manifest_loads_with_the_default_arms(tmp_path):
    m = fs.load_manifest(write_manifest(tmp_path, names=LOGOS))
    assert m.arms == fs.DEFAULT_ARMS and len(m.logos) == 8 and m.seed == 20261012
    assert fs.problems(m) == []                 # a temp folder is outside any work tree


@pytest.mark.parametrize("edit,needle", [
    (lambda m: m.update(seed="x"), "seed"),
    (lambda m: m.update(seed=True), "seed"),
    (lambda m: m.update(arms=["nope"]), "arms"),
    (lambda m: m.update(arms=["equal_pitch_columns"]), "lettering_columns"),
    (lambda m: m.update(arms=["design_angle", "design_angle"]), "arms"),
    (lambda m: m.update(tag="bad tag"), "tag"),
    (lambda m: m["logos"][0].update(name="has_underscore"), "underscore"),
    (lambda m: m["logos"][0].update(name="screenshot"), "reserved"),
    (lambda m: m["logos"][1].update(name=m["logos"][0]["name"]), "repeats"),
    (lambda m: m["logos"][0].update(file="missing.png"), "missing"),
    (lambda m: m["logos"][0].update(width_mm=0), "width"),
    (lambda m: m.update(logos=[]), "no logos"),
    (lambda m: m.update(n_repeat=-1), "n_repeat"),
])
def test_a_bad_manifest_is_refused(tmp_path, edit, needle):
    path = write_manifest(tmp_path, names=LOGOS)
    m = json.loads(path.read_text())
    edit(m)
    path.write_text(json.dumps(m))
    with pytest.raises(SystemExit) as e:
        fs.load_manifest(path)
    assert needle in str(e.value)


def test_too_few_logos_is_refused_for_a_sitting_but_not_a_dry_run(tmp_path, monkeypatch):
    monkeypatch.setattr(fs, "MIN_LOGOS", 8)                     # the pre-registered floor
    m = fs.load_manifest(write_manifest(tmp_path, names=LOGOS[:3]))
    assert any("minimum" in p for p in fs.problems(m))
    d = fs.load_manifest(write_manifest(tmp_path / "d", names=LOGOS[:3], dry_run=True))
    assert fs.problems(d) == []


def test_a_corpus_logo_is_refused_unless_it_is_a_dry_run(tmp_path):
    from tools.thin_strokes import REAL_ART

    rel = REAL_ART["tires"][0]
    src = fs.DIGITIZER / "testdata" / rel
    path = write_manifest(tmp_path)
    shutil.copyfile(src, tmp_path / "logos" / f"{LOGOS[0]}.png")      # same bytes, new name
    bad = fs.problems(fs.load_manifest(path))
    assert any("blinding is spent" in p and "tires" in p for p in bad)
    # the same manifest as a dry run is allowed, and says so everywhere else
    raw = json.loads(path.read_text())
    raw["dry_run"] = True
    path.write_text(json.dumps(raw))
    assert fs.problems(fs.load_manifest(path)) == []


def test_art_outside_a_gitignored_folder_is_refused(tmp_path, monkeypatch):
    m = fs.load_manifest(write_manifest(tmp_path))
    monkeypatch.setattr(fs, "tracked_or_unignored", lambda p: True)
    assert sum("not in a git-ignored folder" in p for p in fs.problems(m)) == len(SMALL)
    monkeypatch.setattr(fs, "tracked_or_unignored", lambda p: False)
    assert fs.problems(m) == []


def test_the_default_logo_folder_is_gitignored_and_the_code_is_not():
    assert fs.tracked_or_unignored(fs.DEFAULT_LOGOS_DIR / "logos" / "x.png") is False
    assert fs.tracked_or_unignored(fs.DIGITIZER / "eye_pairs_local" / "manifest.json") is False
    assert fs.tracked_or_unignored(Path(fs.__file__)) is True        # tracked or untracked-not-ignored


# ---------------------------------------------------------------- build ---

def fake_design(logo_n: int, arm: str) -> dict:
    """One shape; the arm changes its row pitch. A different logo is a
    different size, so no two logos share stitches."""
    k = {"design_angle": 1, "per_stroke": 2, "lettering_columns": 3, "columns_words": 4,
         "split_7mm": 5, "equal_pitch_columns": 3}.get(arm, 0)
    # the arm is TIGHTER than shipped on odd logos and looser on even ones
    pitch = 0.30 + (0.01 * k if logo_n % 2 == 0 else -0.01 * k)
    return _design([_rows(10 + logo_n, 10 + logo_n, pitch)], shapes=["S0"])


def make_fake_render(identical=(), refuse=()):
    """`render` that writes what `--pair` reads, without an engine."""
    def fake_render(out, cases=None, arms=None, **_kw):
        out = Path(out)
        for sub in ("designs", "renders"):
            (out / sub).mkdir(parents=True, exist_ok=True)
        feats = {"__sources__": {}}
        for n, (name, _path, _w, _g) in enumerate(cases):
            cv2.imwrite(str(out / "renders" / f"{name}__art.png"), np.full((8, 8, 3), 200, np.uint8))
            for arm in [BASE, *arms]:
                d = fake_design(n, BASE if (name, arm) in identical else arm)
                (out / "designs" / f"{name}__{arm}.json").write_text(json.dumps(d))
                px = np.full((8, 8, 3), (n * 20 + len(arm)) % 250, np.uint8)
                cv2.imwrite(str(out / "renders" / f"{name}__{arm}.jpg"), px)
                cv2.imwrite(str(out / "renders" / f"{name}__{arm}__holes.jpg"), px)
                feats.setdefault(name, {})[arm] = {"design_hash": design_hash(d), "schema": 2,
                                                   "stitches": d["stitchCount"], "refusals": {},
                                                   "trims_per_1000": 0.0, "lost_frac": 0.1}
                if (name, arm) in refuse:
                    feats[name][arm]["refusals"] = {"artfid": "ink ambiguous"}
        (out / "features.json").write_text(json.dumps(feats))
        return sum(len(a) for k, a in feats.items() if k != "__sources__")
    return fake_render


def real_pair():
    from tools.eye_pairs import __main__ as cli

    return cli.pair


def build(tmp_path, name="a", **manifest_kw):
    path = write_manifest(tmp_path / f"m_{name}", **manifest_kw)
    out = tmp_path / f"out_{name}"
    said = []
    key = fs.build(path, out, render_fn=make_fake_render(), pair_fn=real_pair(), say=said.append)
    return out, key, said


@pytest.fixture(scope="module")
def sitting(tmp_path_factory):
    return build(tmp_path_factory.mktemp("fresh"))


def test_build_writes_the_key_and_names_the_arms_only_there(sitting):
    out, key, _said = sitting
    assert set(key["arms"]) == set(fs.DEFAULT_ARMS)
    assert key["seed"] == 20261012 and key["n_live"] == 5 * len(SMALL)
    assert key["below_budget"] is True                         # 20 live < the pre-registered 48
    assert key["scorecard_refusals"] == {}
    assert key["primary_directions_at_build"] == fs.PRIMARY_DIRECTIONS
    assert key["sealed"] == json.loads((out / "arms.json").read_text())
    assert (out / fs.KEY_NAME).exists() and not (out / fs.DRY_MARKER).exists()


def test_the_builders_terminal_names_no_arm_and_no_logo(sitting):
    _out, _key, said = sitting
    text = "\n".join(said)
    assert "WARNING" in text and "pre-registered" in text            # it still says it is short
    for word in ARM_NAMES + LOGOS:
        assert word not in text


def test_the_judge_never_sees_an_arm_or_a_logo_name(sitting):
    """The judge-facing surface is what the picker answers: the page, the pair
    list, every image it names, and what it refuses. Names appear on none."""
    out, _key, _said = sitting
    httpd = sv.make_server(out, port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        def get(path):
            with urllib.request.urlopen(base + path) as r:
                return r.read()

        surface = [get("/"), get("/pairs")]
        pairs = json.loads(get("/pairs"))["pairs"]
        names = [p[k] for p in pairs for k in ("left", "right", "art")]
        for name in names:
            assert re.fullmatch(r"P\d{3}_(L|R|art)\.(jpg|png)", name), name
            surface.append(get("/img/" + name))
        forbidden = [w.encode() for w in ARM_NAMES + LOGOS + ["KEY.json", "arms.json"]]
        for blob in surface:
            for word in forbidden:
                assert word not in blob, word
        for path in ("/KEY.json", "/arms.json", "/features.json", "/sitting.json",
                     "/designs/Zq1x__base.json", "/renders/Zq1x__base.jpg",
                     f"/img/Zq1x__{ARM_NAMES[0]}.jpg"):
            with pytest.raises(urllib.error.HTTPError) as e:
                get(path)
            assert e.value.code == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
    # and on disk, what the picker's folder holds under img/ is opaque too
    assert all(re.fullmatch(r"P\d{3}_(L|R|art)\.(jpg|png)", f.name)
               for f in (out / "img").iterdir())


def test_the_public_pair_list_carries_no_key_material(sitting):
    out, key, _ = sitting
    public = (out / "pairs.json").read_text()
    for word in ARM_NAMES + LOGOS + ["left_arm", "right_arm", "fixture"]:
        assert word not in public
    # whereas the key names every pair
    assert set(key["sealed"]) == {p["pair"] for p in json.loads(public)}


def test_one_seed_one_sitting_and_another_seed_another(tmp_path):
    a = build(tmp_path, "a", seed=7)[1]["sealed"]
    b = build(tmp_path, "b", seed=7)[1]["sealed"]
    c = build(tmp_path, "c", seed=8)[1]["sealed"]
    assert a == b
    sides = lambda s: {p: v["left_arm"] == BASE for p, v in s.items()}   # noqa: E731
    assert a != c and sides(a) != sides(c)


def test_sides_are_balanced_through_the_builder(sitting):
    _out, key, _ = sitting
    shown = [v for v in key["sealed"].values() if v["kind"] in ("live", "identical")]
    left = sum(1 for v in shown if v["left_arm"] == BASE and v["right_arm"] != BASE)
    right = sum(1 for v in shown if v["right_arm"] == BASE and v["left_arm"] != BASE)
    # `build_pairs` flips exactly half of live + identical entries; the identical
    # controls show the same picture twice, so the live pairs alone are balanced
    # to within their number (4 of 20 here), never more.
    assert left + right == sum(v["kind"] == "live" for v in shown)
    assert abs(left - right) <= key["controls"]["n_identical"]


def test_the_controls_follow_the_manifest(tmp_path):
    out, key, _ = build(tmp_path, "c", n_identical=2, n_repeat=3)
    kinds = [v["kind"] for v in key["sealed"].values()]
    assert kinds.count("identical") == 2 and kinds.count("repeat") == 3
    assert key["controls"] == {"n_identical": 2, "n_repeat": 3}


def test_the_alias_arm_re_presents_the_column_designs(tmp_path):
    out, key, _ = build(tmp_path, "al", arms=["lettering_columns", "equal_pitch_columns"],
                        n_repeat=0, n_identical=0)
    assert key["arms"]["equal_pitch_columns"]["alias_of"] == "lettering_columns"
    for lg in SMALL:
        a = (out / "designs" / f"{lg}__lettering_columns.json").read_bytes()
        b = (out / "designs" / f"{lg}__equal_pitch_columns.json").read_bytes()
        assert a == b
    assert key["n_live"] == 2 * len(SMALL)


def test_an_arm_identical_to_shipped_is_dropped_and_recorded_in_the_key(tmp_path):
    path = write_manifest(tmp_path / "m")
    out = tmp_path / "o"
    key = fs.build(path, out, render_fn=make_fake_render(identical={(LOGOS[0], "per_stroke")}),
                   pair_fn=real_pair(), say=lambda *_: None)
    assert key["n_live"] == 5 * len(SMALL) - 1
    assert key["skipped"] == [{"fixture": LOGOS[0], "arm": "per_stroke",
                               "reason": "identical_to_base"}]


def test_a_logo_the_scorecard_refuses_is_named_in_the_key_only(tmp_path):
    path = write_manifest(tmp_path / "m")
    key = fs.build(path, tmp_path / "o", render_fn=make_fake_render(refuse={(SMALL[1], BASE)}),
                   pair_fn=real_pair(), say=lambda *_: None)
    assert key["scorecard_refusals"] == {SMALL[1]: "ink ambiguous"}


def test_a_dry_run_is_stamped_not_blinded_everywhere(tmp_path):
    out, key, said = build(tmp_path, "d", dry_run=True, names=LOGOS[:2], arms=["design_angle"])
    assert key["dry_run"] is True
    assert "NOT BLINDED" in (out / fs.DRY_MARKER).read_text()
    assert any("DRY RUN" in s and "NOT BLINDED" in s for s in said)


def test_a_judged_sitting_is_never_rebuilt_in_place(tmp_path):
    out, _key, _ = build(tmp_path, "r")
    append_pick(out / "picks.jsonl", "P001", "L", 100)
    with pytest.raises(SystemExit) as e:
        fs.build(tmp_path / "m_r" / "manifest.json", out, render_fn=make_fake_render(),
                 pair_fn=real_pair(), say=lambda *_: None)
    assert "never rebuilt" in str(e.value)


def test_the_pitch_gate_marks_a_density_pair(tmp_path):
    out, _key, _ = build(tmp_path, "p", arms=["design_angle", "lettering_columns", "columns_words"])

    def measure(name, _path, _w, _g, arm):
        if not arm:
            return {"outer_p50": 0.45}
        if name == LOGOS[0]:
            return {"outer_p50": 0.82}                            # the 10-07 page: 0.80 mm a rail
        if name == LOGOS[1]:
            return {}                                             # no lettering: no satin to read
        return {"outer_p50": 0.52}

    gate = fs.pitch_gate(tmp_path / "m_p" / "manifest.json", out, measure=measure,
                         say=lambda *_: None)
    assert gate["logos"][LOGOS[0]]["lettering_columns"]["ok"] is False
    assert gate["logos"][LOGOS[1]]["columns_words"]["ok"] is None
    assert gate["logos"][LOGOS[2]]["columns_words"]["ok"] is True
    assert "design_angle" not in gate["logos"][LOGOS[0]]           # only the Column family
    assert json.loads((out / fs.KEY_NAME).read_text())["pitch_gate"]["tolerance_mm"] == 0.15


# -------------------------------------------------------------- scoring ---

def test_kent_label_is_in_the_shipped_arm_frame_not_the_page_frame():
    assert fs.kent_label("L", BASE, "x") == "before" and fs.kent_label("R", BASE, "x") == "after"
    assert fs.kent_label("L", "x", BASE) == "after" and fs.kent_label("R", "x", BASE) == "before"
    assert fs.kent_label("tie", "x", BASE) == "same" and fs.kent_label(None, "x", BASE) is None


def judge_everything(out: Path, rule) -> None:
    """Write a pick for every pair in `out`; `rule(pair_id, sealed_row)` -> L/R/tie."""
    sealed = json.loads((out / "arms.json").read_text())
    for pid in sorted(sealed):
        append_pick(out / "picks.jsonl", pid, rule(pid, sealed[pid]), 10)


def test_score_refuses_until_every_pair_is_picked(sitting, tmp_path):
    out = tmp_path / "half"
    shutil.copytree(sitting[0], out)
    append_pick(out / "picks.jsonl", "P001", "L", 10)
    with pytest.raises(SystemExit) as e:
        fs.score(out, say=lambda *_: None)
    assert "no pick" in str(e.value)


def test_score_runs_end_to_end_and_gets_the_label_frame_right(sitting, tmp_path, monkeypatch):
    monkeypatch.setattr(pooled, "B", 300)
    out = tmp_path / "scored"
    shutil.copytree(sitting[0], out)

    def prefers_denser(pid, s):
        """Kent picks the side with the TIGHTER pitch (more thread per area)."""
        if s["kind"] == "identical":
            return "tie"
        n = LOGOS.index(s["fixture"])
        arm = s["right_arm"] if s["left_arm"] == BASE else s["left_arm"]
        tighter_is_base = fake_design(n, BASE)["stitchCount"] > fake_design(n, arm)["stitchCount"]
        want = BASE if tighter_is_base else arm
        return "L" if s["left_arm"] == want else "R"

    judge_everything(out, prefers_denser)
    res = fs.score(out, say=lambda *_: None)
    assert res["n_logos"] == len(SMALL) and res["n_scored"] == 5 * len(SMALL)
    td = res["primary"]["thread_density"]
    assert td["direction"] == "higher" and td["kappa_decided"] == pytest.approx(1.0)
    assert (out / "score.json").exists() and "Primary readings" in (out / "score.md").read_text()
    assert res["controls_report"]["controls"]["identical_n"] == 4
    # the raw agreement rule: no field of the report is a bare agreement rate
    flat = json.dumps(res)
    assert "raw_agreement" not in flat and "agreement_rate" not in flat


def inputs_with(rows):
    """pooled-shaped inputs from (fixture, arm, label, before, after) rows."""
    pairs = [{"id": f"t:{arm}:{fx}", "arm": arm, "fixture": fx, "label": lab,
              "before": b, "after": a, "judged": "2026-10-12"} for fx, arm, lab, b, a in rows]
    return {"schema": 1, "sittings": {"t": {"date": "2026-10-12", "pairs": pairs}}}


def synthetic(n_logos=10, per_logo=3, seed=3, trims_follow=None):
    """`flow_circvar`/`long_share` built to agree with Kent (lower is better);
    `trims_per_1000` independent of them unless `trims_follow`."""
    rng = np.random.default_rng(seed)
    rows = []
    for L in range(n_logos):
        for k in range(per_logo):
            kent_after = bool(rng.integers(0, 2))
            lo, hi = 0.2, 0.6
            fc_b, fc_a = (hi, lo) if kent_after else (lo, hi)
            ls_b, ls_a = (0.05, 0.01) if kent_after else (0.01, 0.05)      # lower long_share = Kent's pick
            tr = (kent_after if trims_follow else bool(rng.integers(0, 2)))
            tr_b, tr_a = (9.0, 5.0) if tr else (5.0, 9.0)
            td_b, td_a = (6.0, 7.0) if kent_after else (7.0, 6.0)
            b = {"flow_circvar": fc_b, "long_share": ls_b, "trims_per_1000": tr_b,
                 "thread_density": td_b, "longest_jump_mm": 20 + rng.random()}
            a = {"flow_circvar": fc_a, "long_share": ls_a, "trims_per_1000": tr_a,
                 "thread_density": td_a, "longest_jump_mm": 20 + rng.random()}
            rows.append((f"Lg{L}", f"arm{k}", "after" if kent_after else "before", b, a))
    return inputs_with(rows)


def test_the_pre_registered_reading_confirms_a_real_non_trim_signal(monkeypatch):
    monkeypatch.setattr(pooled, "B", 400)
    res = fs.analyse(synthetic(), include_candidates=False)
    fc = res["primary"]["flow_circvar"]
    assert fc["verdict"].startswith("CONFIRMED"), fc["verdict"]
    assert fc["restates_trims"]["kappa"] < fs.RESTATES_TRIMS_KAPPA
    # long_share is read LOWER-is-better: Kent's picks sit on the lower side, so kappa > 0
    ls = res["primary"]["long_share"]
    assert ls["direction"] == "lower" and ls["kappa_decided"] > 0.9
    # the trim count is above chance too, but is named for what it is
    assert res["primary"]["trims_per_1000"]["kappa_decided"] is not None
    assert res["exit"]["clause_1_agrees"] is True
    assert res["exit"]["clause_2_never_worse"] is True


def test_a_signal_that_is_the_trims_is_not_called_new(monkeypatch):
    monkeypatch.setattr(pooled, "B", 400)
    res = fs.analyse(synthetic(trims_follow=True), include_candidates=False)
    assert res["primary"]["flow_circvar"]["verdict"] == "above chance but restates the trims"
    assert "price column" in res["primary"]["trims_per_1000"]["verdict"]
    assert res["exit"]["confirmed_primaries"] == []              # trims-only is not exit evidence
    assert res["exit"]["clause_1_agrees"] is False


def test_a_reversed_instrument_is_reported_reversed(monkeypatch):
    monkeypatch.setattr(pooled, "B", 400)
    inp = synthetic()
    for p in inp["sittings"]["t"]["pairs"]:
        p["label"] = "before" if p["label"] == "after" else "after"
    res = fs.analyse(inp, include_candidates=False)
    assert res["primary"]["flow_circvar"]["verdict"].startswith("REVERSED")


def test_too_few_decided_pairs_read_nothing(monkeypatch):
    monkeypatch.setattr(pooled, "B", 200)
    res = fs.analyse(synthetic(n_logos=2, per_logo=2), include_candidates=False)
    assert all(r["verdict"] == "n too small to read" for r in res["primary"].values())
    assert res["exit"]["clause_1_agrees"] is False


def test_one_logo_cannot_carry_a_reading():
    inp = synthetic(n_logos=6, per_logo=4)
    rows = pooled.select(pooled.pooled_pairs(inp))
    loo = fs.leave_one_logo_out(rows, "flow_circvar", fs.directions())
    assert loo["n_nonpositive"] == 0 and len(loo["drops"]) == 6
    # make Lg0 the only logo where flow agrees, everywhere else the label is a coin
    rng = np.random.default_rng(1)
    for p in inp["sittings"]["t"]["pairs"]:
        if p["fixture"] != "Lg0":
            p["label"] = "after" if rng.integers(0, 2) else "before"
    rows = pooled.select(pooled.pooled_pairs(inp))
    loo = fs.leave_one_logo_out(rows, "flow_circvar", fs.directions())
    # the logo that carries the signal is the one whose removal costs the most
    assert loo["drops"]["Lg0"] < loo["drops"]["Lg1"]


def test_the_manipulation_check_counts_moves_per_arm():
    rows = pooled.select(pooled.pooled_pairs(synthetic(n_logos=2, per_logo=2)))
    m = fs.arm_manipulation(rows)
    assert set(m) == {"arm0", "arm1"}
    cell = m["arm0"]["flow_circvar"]
    assert cell["arm_better"] + cell["base_better"] + cell["no_change"] == 2


def test_the_pitch_gate_and_the_retest_arm_keep_pairs_out_of_the_pool(sitting, tmp_path):
    out = tmp_path / "gated"
    shutil.copytree(sitting[0], out)
    key = json.loads((out / fs.KEY_NAME).read_text())
    key["pitch_gate"] = {"tolerance_mm": 0.15, "logos": {
        LOGOS[0]: {"lettering_columns": {"ok": False}}}}
    (out / fs.KEY_NAME).write_text(json.dumps(key))
    judge_everything(out, lambda pid, s: "tie")
    inputs = fs.sitting_inputs(out)
    pairs = inputs["sittings"]["fresh-test"]["pairs"]
    gated = [p for p in pairs if p["fixture"] == LOGOS[0] and p["arm"] == "lettering_columns"]
    assert gated and gated[0]["scorable"] is False and "pitch gate" in gated[0]["unscored_why"]
    assert len(pooled.select(pooled.pooled_pairs(inputs))) == len(pairs) - 1
