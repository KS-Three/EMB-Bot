"""`tools/scope_flag_lint.py` — the scope docs' flag citations, checked.

Every assertion here runs on a SYNTHETIC doc snippet against a hand-built
`CodeIndex`, so nothing pins what the real docs happen to say today: a scope
refresh that changes MASTER_SCOPE must never turn this red. The two tests that
touch the real repo assert only that the tool runs, exits 0 and leaves the
docs byte-identical — the advisory, read-only contract — never what it finds.

Cheap by construction: text and a dataclass, nothing digitizes.
"""

import dataclasses
import hashlib
import textwrap

import pytest

from digitizer_core.config import PipelineConfig
from tools import scope_flag_lint as sfl


def _idx(**kw) -> sfl.CodeIndex:
    base = dict(fields={"flag_a": False, "flag_b": True, "width_mm": 8.0,
                        "tri_mode": None},
                extra={"xk": None}, js={"jsOn": True, "pxPerMm": None},
                text_names={"some_helper", "flag_a", "flag_b"})
    base.update(kw)
    return sfl.CodeIndex(**base)


def _lint(text: str, **kw) -> sfl.Report:
    return sfl.lint(sfl.extract(textwrap.dedent(text), "T.md"), _idx(**kw))


# ---------------------------------------------------------------- extraction

def test_three_citation_shapes_are_extracted():
    cits = sfl.extract(
        '`cfg.flag_a` here. `cfg.extra["xk"]` there. `flag_b` is ON.', "T.md")
    assert [(c.name, c.kind) for c in cits] == [
        ("flag_a", "cfg"), ("xk", "extra"), ("flag_b", "bare")]
    assert cits[2].claim == "ON"


def test_a_bare_name_without_on_off_is_not_a_citation():
    # Every identifier in the docs would be a "flag" otherwise.
    assert sfl.extract("calls `some_helper` to do it.", "T.md") == []


def test_lowercase_on_is_prose_not_a_claim():
    assert sfl.extract("`flag_a` on the left.", "T.md") == []


def test_each_name_takes_its_own_neighbouring_claim():
    cits = sfl.extract("`flag_a` is ON while `flag_b` is OFF.", "T.md")
    assert [(c.name, c.claim) for c in cits] == [("flag_a", "ON"), ("flag_b", "OFF")]


def test_a_claim_already_taken_is_not_reused_by_the_next_name():
    # `flag_a`'s "(ON)" sits before `flag_b` too; it belongs to `flag_a` only.
    cits = sfl.extract("`cfg.flag_a` (ON) and `cfg.flag_b` were added.", "T.md")
    assert [(c.name, c.claim) for c in cits] == [("flag_a", "ON"), ("flag_b", None)]


def test_default_before_the_name_is_read():
    (c,) = sfl.extract("DEFAULT OFF for `cfg.flag_b`.", "T.md")
    assert c.claim == "OFF"


def test_a_bare_on_before_the_name_is_prose():
    # The first-pass false positive: "ON can change `px_per_mm`".
    assert sfl.extract("and ON can change `px_per_mm` here", "T.md") == []


def test_clause_stop_bounds_the_claim():
    (c,) = sfl.extract("`cfg.flag_a` landed. The other one is ON", "T.md")
    assert c.claim is None


def test_default_true_false_spans_are_claims():
    (c,) = sfl.extract("`cfg.flag_a`, default `False` — see", "T.md")
    assert c.claim == "OFF"


def test_an_arrow_takes_the_state_after_it():
    (c,) = sfl.extract("`flag_a` flipped OFF → ON in #12", "T.md")
    assert (c.claim, c.ambiguous) == ("ON", False)


def test_both_states_without_an_arrow_are_ambiguous():
    (c,) = sfl.extract("`flag_a` ON or OFF per run", "T.md")
    assert c.ambiguous and c.claim is None


def test_line_numbers_point_at_the_name():
    cits = sfl.extract("intro\n\n`cfg.flag_a` is ON\n", "T.md")
    assert cits[0].line == 3


@pytest.mark.parametrize("text,hist,cond", [
    ("`flag_a` is OFF now", False, False),
    ("PR #9 built `flag_a` OFF", True, False),
    ("~~`flag_a` OFF~~", True, False),
    ("switches `flag_a` ON for the arm", False, True),
    ("`flag_a` ON now leaves 8 mm", False, True),
])
def test_wording_buckets(text, hist, cond):
    (c,) = sfl.extract(text, "T.md")
    assert (c.historical, c.conditional) == (hist, cond)


# --------------------------------------------------------------------- lint

def test_agreement_is_cited_and_not_a_mismatch():
    r = _lint("`cfg.flag_a` is OFF. `flag_b` is ON.")
    assert set(r.cited) == {"flag_a", "flag_b"}
    assert r.mismatches_current == [] and r.orphans_absent == []


def test_current_mismatch_is_reported_with_its_location():
    r = _lint("intro\n`cfg.flag_a` is ON.")
    assert r.mismatches_current == [
        "T.md:2: cfg.flag_a [field] doc says ON, code default OFF"]


def test_historical_and_conditional_mismatches_are_separate_buckets():
    r = _lint("built `cfg.flag_b` OFF. switches `cfg.flag_a` ON.")
    assert r.mismatches_current == []
    assert len(r.mismatches_historical) == 1 and "flag_b" in r.mismatches_historical[0]
    assert len(r.mismatches_conditional) == 1 and "flag_a" in r.mismatches_conditional[0]


def test_orphans_split_absent_from_not_a_flag():
    r = _lint("`cfg.gone_flag` is ON. `some_helper` is OFF.")
    assert r.orphans_absent == ["cfg.gone_flag — T.md:1"]
    assert r.orphans_not_flag == ["some_helper — T.md:1"]
    assert "gone_flag" not in r.cited


def test_two_cites_on_one_line_are_one_location():
    r = _lint("`gone_x` OFF and again `gone_x` OFF")
    assert r.orphans_absent == ["gone_x — T.md:1"]


def test_extra_key_resolves_and_reads_unset_as_off():
    r = _lint('`cfg.extra["xk"]` (ON).')
    assert r.cited["xk"]["where"] == ["extra"]
    assert len(r.mismatches_current) == 1 and "code default OFF" in r.mismatches_current[0]


def test_extra_key_is_not_a_field_lookup():
    # `cfg.extra["flag_a"]` names a key nobody reads, even though `flag_a` is a field.
    r = _lint('`cfg.extra["flag_a"]` OFF')
    assert r.orphans_not_flag == ['cfg.extra["flag_a"] — T.md:1']


def test_bare_snake_name_finds_its_js_camelcase_twin():
    r = _lint("`js_on` is OFF")
    assert r.cited["js_on"]["where"] == ["js"]
    assert "code default ON" in r.mismatches_current[0]


@pytest.mark.parametrize("text,needle", [
    ("`width_mm` is ON", "default 8.0"),
    ("`tri_mode` is OFF", "default None"),
    ("`px_per_mm` is ON", "default None"),
    ("`flag_a` ON or OFF per run", "both ON and OFF"),
])
def test_every_unsettleable_claim_is_reported(text, needle):
    r = _lint(text)
    assert r.mismatches_current == []
    assert len(r.unsettled) == 1 and needle in r.unsettled[0], r.unsettled


def test_factory_default_is_unsettled_not_dropped():
    r = _lint("`cfg.fx` is ON", fields={"fx": dataclasses.MISSING})
    assert len(r.unsettled) == 1 and "default_factory" in r.unsettled[0]


# ------------------------------------------------------- the code-side index

def test_extra_readers_resolve_literals_constants_and_bound_names(tmp_path):
    (tmp_path / "m.py").write_text(textwrap.dedent('''
        KEY = "via_const"
        def a(cfg):
            return cfg.extra.get("literal_key")
        def b(cfg):
            extra = getattr(cfg, "extra", None) or {}
            return extra.get(KEY), extra.get("with_default", True)
        def c(cfg):
            return (getattr(cfg, "extra", None) or {}).get("wrapped")
        def not_cfg(warning):
            extra = warning["extra"]
            return extra.get("warning_field")
    '''))
    found, where = sfl.extra_readers([tmp_path / "m.py"])
    assert found == {"literal_key": None, "via_const": None,
                     "with_default": True, "wrapped": None}
    assert "warning_field" not in found
    assert where["via_const"].endswith("m.py:7")


def test_js_option_defaults(tmp_path):
    (tmp_path / "e.js").write_text(textwrap.dedent('''
        if (o.counterGuard !== false) a();
        if (o.cutEveryJump) b();
        const k = o.pxPerMm * 2;
        const s = opts.slant ?? true;
    '''))
    js = sfl.js_options([tmp_path / "e.js"])
    assert js == {"counterGuard": True, "cutEveryJump": False,
                  "pxPerMm": None, "slant": True}


def test_camel():
    assert sfl.camel("cut_every_jump") == "cutEveryJump"


def test_real_index_sees_the_real_dataclass():
    idx = sfl.build_index()
    names = {f.name for f in dataclasses.fields(PipelineConfig)}
    assert set(idx.fields) == names
    assert idx.extra, "no cfg.extra reader found — the AST scan is broken"


# ------------------------------------------------- the advisory contract

def _hashes():
    return {d: hashlib.sha256((sfl.ROOT / d).read_bytes()).hexdigest()
            for d in sfl.scope_docs()}


def test_real_docs_run_exits_zero_and_writes_nothing(capsys):
    before = _hashes()
    assert sfl.main([]) == 0
    assert sfl.main(["--json"]) == 0
    assert _hashes() == before
    out = capsys.readouterr().out
    assert "Advisory only" in out and '"orphans_absent"' in out


def test_scope_docs_includes_roadmap_and_area_docs():
    docs = sfl.scope_docs()
    assert {"MASTER_SCOPE.md", "ROADMAP.md", "DOCTRINE.md"} <= set(docs)
    assert any(d.startswith("docs/scope/") for d in docs)


# ------------------------------------------------------------- --brief

def _section_count(text, title_start):
    for ln in text.splitlines():
        if ln.startswith(title_start):
            return int(ln.rsplit(":", 1)[1])
    raise AssertionError(f"no section {title_start!r}")


def test_brief_keeps_only_orphans_and_mismatches():
    r = sfl.Report(["A.md"], [], {"x": {"where": ["field"], "default": {},
                                        "cites": []}},
                   ["cfg.gone — A.md:1"], ["nf — A.md:2"], ["m1"], ["m2"],
                   ["m3"], ["u1"])
    full, brief = sfl.render(r), sfl.render_brief(r)
    assert "CITED FLAGS" not in brief and "UNSETTLED" not in brief
    assert "cfg.gone" in brief and "m1" in brief and "m3" in brief
    assert "u1" not in brief
    assert "Advisory only" in brief
    for t in ("ORPHANS — ABSENT", "ORPHANS — NOT A FLAG",
              "DEFAULT MISMATCHES — CURRENT", "DEFAULT MISMATCHES — HIST",
              "DEFAULT MISMATCHES — COND"):
        assert _section_count(brief, t) == _section_count(full, t)


def test_brief_json_is_trimmed():
    import json
    r = sfl.Report([], [], {}, ["a"], [], [], [], [], ["u"])
    d = json.loads(sfl.to_json(r, brief=True))
    assert set(d) == set(sfl.BRIEF_KEYS)
    assert "cited" not in d and "unsettled" not in d
    assert "cited" in json.loads(sfl.to_json(r))


def test_brief_on_real_docs_exits_zero_with_same_orphan_counts(capsys):
    assert sfl.main(["--brief"]) == 0
    brief = capsys.readouterr().out
    assert sfl.main([]) == 0
    full = capsys.readouterr().out
    assert sfl.main(["--brief", "--json"]) == 0
    capsys.readouterr()
    for t in ("ORPHANS — ABSENT", "ORPHANS — NOT A FLAG"):
        assert _section_count(brief, t) == _section_count(full, t)
