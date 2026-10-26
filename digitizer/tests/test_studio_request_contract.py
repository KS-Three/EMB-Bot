"""The request every flip-sheet and pro_pair number runs on, pinned to the
request the Studio actually builds.

`tools.fremont_triage.studio_request()` is a hand-kept Python copy of
`app/src/lib/digitizer.js` `buildDigitizeConfig`. `test_fremont_triage.py`
pins it by grepping the JS source for each key; that catches a changed
default but not a new unconditional key or a branch that starts to fire for a
fresh upload. This pins the OUTPUT instead.

`app/src/lib/fixtures/studio-request.json` is `buildDigitizeConfig` run over a
fresh digitized element per garment and width (vitest writes it, and
`app/src/lib/studioRequest.contract.spec.js` asserts the live function still
equals it). This file reads the SAME fixture and asserts the Python copy
equals it, so a key changed on one side goes red on the other:

  * change `buildDigitizeConfig`: vitest is red; regenerate the fixture and
    THIS file is red until `studio_request` follows;
  * change `studio_request` alone: this file is red.

It is a superset of `test_fremont_triage.py::test_request_is_what_the_studio_
sends` and `test_service_accepts_the_request_unchanged` (same checks, over
three garments and two widths, from the function's output rather than the
source text). Once the PR that carries that test lands (#1057), its key-by-key
asserts are redundant with this file and can go.

The second half is one structural check: a `PipelineConfig` field read only
inside `pipeline.digitize` is inert for the Studio, because the service never
calls `digitize` (it runs `build_generation` -> `finish_generation` ->
`plan_stitches`). Such a field defaulting ON would read as shipped in config
and do nothing for a customer.
"""
from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import pytest

from digitizer_core.config import PipelineConfig
from tools import fremont_triage as ft
from tools import pro_pair

DIGITIZER = Path(__file__).resolve().parent.parent
FIXTURE = DIGITIZER.parent / "app" / "src" / "lib" / "fixtures" / "studio-request.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _cases() -> list[dict]:
    return _fixture()["cases"]


def _ids() -> list[str]:
    return [c["name"] for c in _cases()]


# ---------------------------------------------------------------- the request

def test_fixture_is_there_and_covers_the_garments_the_sheets_run_on():
    cases = _cases()
    assert {c["garment_id"] for c in cases} == {"hat_front", "left_chest", "beanie"}
    assert len(cases) == len({c["name"] for c in cases}), "a case name repeats"
    assert all(c["config"]["garment_id"] == c["garment_id"] for c in cases)


def test_studio_fabric_is_the_projects_default_fabric():
    assert _fixture()["fabric_rgb"] == ft.STUDIO_FABRIC_RGB


@pytest.mark.parametrize("case", _cases(), ids=_ids())
def test_pro_pair_request_is_what_buildDigitizeConfig_returns(case):
    """`pro_pair.request` is the one every flip sheet and pro pair sends."""
    got = pro_pair.request(case["target_width_mm"], case["garment_id"])
    assert got == case["config"], (
        f"{case['name']}: the Python request is not the Studio's. If "
        "buildDigitizeConfig changed on purpose, regenerate the fixture with "
        "UPDATE_STUDIO_REQUEST_FIXTURE=1 (see studioRequest.contract.spec.js) "
        "and bring studio_request in line; every earlier flip number was run "
        "on the old request and the PR body must say so.")


def test_studio_request_is_the_hat_case_at_its_own_width():
    """`studio_request()` with no argument is Kent's Fremont job: Hat, 81 mm."""
    hat81 = next(c for c in _cases() if c["name"] == "hat_front_81")
    assert ft.studio_request() == hat81["config"]
    for c in _cases():
        if c["garment_id"] == "hat_front":
            assert ft.studio_request(c["target_width_mm"]) == c["config"]


@pytest.mark.parametrize("case", _cases(), ids=_ids())
def test_service_accepts_the_request_unchanged(case):
    """`_parse_config` returns it as is (it 400s on an unknown key and
    re-canonicalises a value it does not take verbatim), and the engine's
    config takes it."""
    from digitizer_service.app import _parse_config
    req = pro_pair.request(case["target_width_mm"], case["garment_id"])
    parsed = _parse_config(json.dumps(req))
    assert parsed == req
    cfg = PipelineConfig(**parsed)
    assert cfg.garment_id == case["garment_id"]
    assert cfg.target_width_mm == case["target_width_mm"]


def test_a_thread_brand_the_customer_picked_is_the_only_added_key():
    """The default request carries no `thread_brand` (the Studio's own palette
    is omitted and the service resolves its default chart). A customer who
    picked a brand adds exactly that key; the flip sheets never run that arm."""
    base = pro_pair.request(81.0)
    assert "thread_brand" not in base
    with_brand = pro_pair.request(81.0, extra={"thread_brand": "madeira-rayon"})
    assert {k: v for k, v in with_brand.items() if k != "thread_brand"} == base
    from digitizer_service.app import _parse_config
    assert _parse_config(json.dumps(with_brand))["thread_brand"] == "madeira-rayon"


# ----------------------------------------------- fields the Studio cannot reach

#: What a default of "off" looks like when it is not a falsy value.
_OFF_STRINGS = {"off", "none"}


def _is_off(value) -> bool:
    return (not value) or (isinstance(value, str) and value.lower() in _OFF_STRINGS)


def digitize_only_fields(sources: dict[str, str], fields: set[str],
                         scope_file: str = "pipeline.py",
                         scope_root: str = "digitize") -> set[str]:
    """Config fields whose every read is inside `scope_root` (in `scope_file`)
    or inside a function that only it calls.

    `sources` maps a file name to its text. A read is an attribute load of a
    field's name (`cfg.x`, `self.x`, `result.cfg.x`), or `getattr(_, "x")`.
    The name test is deliberately loose: another object's attribute that
    shares a field's name counts as a read OUTSIDE the scope, which can only
    hide a field from this check, never accuse one that the Studio reaches.
    A helper counts as inside the scope only if no other function in any
    scanned file refers to its name."""
    trees = {name: ast.parse(text) for name, text in sources.items()}

    def owner_map(tree):
        """Node id -> name of its top-level function (or class method)."""
        owner = {}
        for top in tree.body:
            nodes = []
            if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nodes = [(top.name, top)]
            elif isinstance(top, ast.ClassDef):
                nodes = [(f"{top.name}.{n.name}", n) for n in top.body
                         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for label, fn in nodes:
                for sub in ast.walk(fn):
                    owner[id(sub)] = label
        return owner

    owners = {name: owner_map(t) for name, t in trees.items()}

    def loads(tree):
        """(identifier, node) for every Name/Attribute load and string
        argument of getattr."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                yield node.attr, node
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                yield node.id, node
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                  and node.func.id == "getattr" and len(node.args) >= 2
                  and isinstance(node.args[1], ast.Constant)
                  and isinstance(node.args[1].value, str)):
                yield node.args[1].value, node
            elif isinstance(node, (ast.ImportFrom,)):
                for alias in node.names:
                    yield alias.name, node

    # Which function (file, label) refers to each identifier.
    refs: dict[str, set[tuple[str, str | None]]] = {}
    for fname, tree in trees.items():
        for ident, node in loads(tree):
            refs.setdefault(ident, set()).add((fname, owners[fname].get(id(node))))

    scope: set[str] = {scope_root}
    changed = True
    scope_funcs = {n.name for n in trees[scope_file].body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    while changed:
        changed = False
        for fn in sorted(scope_funcs - scope):
            users = refs.get(fn, set())
            if users and all(f == scope_file and o in scope for f, o in users):
                scope.add(fn)
                changed = True

    reads_in: dict[str, bool] = {}
    for field in fields:
        sites = refs.get(field, set())
        # A def's own name or a dataclass field line is a Store/AnnAssign, not
        # a load, so every entry here is a real read.
        if sites and all(f == scope_file and o in scope for f, o in sites):
            reads_in[field] = True
    return set(reads_in)


def _product_sources() -> dict[str, str]:
    out = {}
    for pkg in ("digitizer_core", "digitizer_service"):
        for path in sorted((DIGITIZER / pkg).rglob("*.py")):
            out[f"{pkg}/{path.relative_to(DIGITIZER / pkg).as_posix()}"] = path.read_text(encoding="utf-8")
    # The scanner keys the scope file by its short name below.
    return {("pipeline.py" if k == "digitizer_core/pipeline.py" else k): v for k, v in out.items()}


def test_scanner_finds_a_digitize_only_field_in_a_toy_tree():
    """The scanner is alive: it flags a field only `digitize` (or a helper only
    it calls) reads, and leaves one a stage also reads."""
    pipeline = (
        "def digitize(cfg):\n"
        "    if cfg.only_here: pass\n"
        "    _helper(cfg)\n"
        "def _helper(cfg):\n"
        "    return cfg.only_in_helper\n"
        "def stage(cfg):\n"
        "    return cfg.shared\n"
        "def other(cfg):\n"
        "    return getattr(cfg, 'by_getattr')\n"
    )
    other = "def f(cfg):\n    return cfg.shared + cfg.by_getattr\n"
    got = digitize_only_fields({"pipeline.py": pipeline, "stage.py": other},
                               {"only_here", "only_in_helper", "shared", "by_getattr", "unused"})
    assert got == {"only_here", "only_in_helper"}


def test_a_helper_another_function_calls_is_outside_the_scope():
    pipeline = (
        "def digitize(cfg):\n    _helper(cfg)\n"
        "def _helper(cfg):\n    return cfg.f\n"
        "def stage(cfg):\n    _helper(cfg)\n"
    )
    assert digitize_only_fields({"pipeline.py": pipeline}, {"f"}) == set()


def test_no_field_only_pipeline_digitize_reads_defaults_on():
    """`pipeline.digitize` is not on the service's path, so a field read only
    there does nothing for a customer. It may exist (OFF, for the tools that
    call `digitize`); it may not default ON, because ON in config.py reads as a
    shipped behaviour that the Studio never gets.

    Latent today: `tonal_split_layer_cap` and `tonal_split_ceiling`, both OFF.
    If this fails, either wire the field into `finish_generation` /
    `plan_stitches` (the path the service runs) or put the default back OFF."""
    sources = _product_sources()
    assert "def digitize(" in sources["pipeline.py"], (
        "pipeline.digitize moved or was renamed: update digitize_only_fields' "
        "scope_root, or this check scans nothing")
    fields = {f.name: f for f in dataclasses.fields(PipelineConfig)}
    only = digitize_only_fields(sources, set(fields))
    on = {}
    for name in sorted(only):
        f = fields[name]
        default = (f.default if f.default is not dataclasses.MISSING
                   else f.default_factory() if f.default_factory is not dataclasses.MISSING
                   else None)
        if not _is_off(default):
            on[name] = default
    assert not on, (
        f"PipelineConfig fields read only inside pipeline.digitize (not on the "
        f"service path) that default ON: {on}")
