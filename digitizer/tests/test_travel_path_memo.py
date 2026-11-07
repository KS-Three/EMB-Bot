"""`stage6_fill.travel_path`'s memo inside one `stitch_shape` (`_TravelMemo`).

Pinned here:

- the key covers EVERYTHING the body reads: an AST walk of `_travel_path`'s
  call graph inside stage6_fill finds exactly the globals and `machine`
  constants listed below, none of them a ContextVar -- so a new read (a
  knob, a ContextVar, another module) fails this file until it is either
  put in the key or shown to be a constant or a pure cache;
- every input moves the key, and an end that is not a tuple of two floats
  bypasses it;
- a hit is the miss: the route, an independent list, and the caller's ring
  cache left as the miss would have left it;
- `stitch_shape` sews the same runs with the memo as with the plain body, on
  a holed plate under every covered-routing switch, and the memo is dead
  outside `stitch_shape`, even after one raises.
"""
from __future__ import annotations

import ast
import builtins
import contextlib
import contextvars
import inspect
import random
import textwrap
from dataclasses import asdict
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon

from digitizer_core import fill_section_travel, machine, shape_memo
from digitizer_core import stage6_fill as F

SRC = Path(F.__file__).read_text()

# ------------------------------------------------------------- what the body reads

#: Module globals `_travel_path`'s call graph reads, by kind. A name here is
#: either in `_TravelMemo.key`'s inputs (none are: every input is an
#: argument), immutable for the process, or a cache whose hit is its miss.
CONSTANTS = {"_TRAVEL_DETOUR_FLOOR_MM", "_TRAVEL_DETOUR_FACTOR", "_TRAVEL_RING_CANDIDATES",
             "_TRAVEL_WINDOW_MARGIN_MM", "_EXPOSED_TOLERANCE_MM", "_UNSEWN_MAX"}
PURE_CACHES = {"_UNSEWN_MEMO"}           # `_ring_arc` is an lru_cache: a function below
FUNCTIONS = {"_densify", "_ring_ways", "_ring_route", "_ring_arc", "_exposed_mm",
             "_unsewn_ground", "_inset_ring", "_Sewn"}
LIBRARIES = {"math", "np", "shapely", "hashlib", "struct", "machine", "functools",
             "LineString", "Point", "Polygon", "box"}
#: `machine.X` read anywhere in the graph -- plain numbers, fixed for a process
MACHINE = {"TINY_STITCH_MM", "TRAVEL_STITCH_MM", "TRAVEL_INSET_MM", "FILL_ROW_MM"}
#: `_Sewn` methods reached through `sewn.<method>` (the class is walked whole)
SEWN_METHODS = {"clipped", "on_line", "_hits", "add", "digest"}


def _module_defs():
    tree = ast.parse(SRC)
    funcs, classes = {}, {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
        elif isinstance(node, ast.ClassDef):
            classes[node.name] = node
    return funcs, classes


def _bound(fn: ast.AST) -> set[str]:
    """Every name bound anywhere inside `fn`: its own and nested functions'
    parameters, assignment / loop / comprehension / with / except targets,
    nested defs."""
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = n.args
            for arg in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg]:
                if arg is not None:
                    out.add(arg.arg)
            if not isinstance(n, ast.Lambda):
                out.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
    return out


def _reads():
    """(module globals, `machine` attributes) read by `_travel_path`'s graph."""
    funcs, classes = _module_defs()
    globals_read, machine_attrs = set(), set()
    todo, done = ["_travel_path"], set()
    while todo:
        name = todo.pop()
        if name in done:
            continue
        done.add(name)
        node = funcs.get(name) or classes.get(name)
        assert node is not None, name
        local = _bound(node)
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in local \
                    and not hasattr(builtins, n.id):
                globals_read.add(n.id)
                if n.id in funcs or n.id in classes:
                    todo.append(n.id)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                    and n.value.id == "machine":
                machine_attrs.add(n.attr)
            if isinstance(n, ast.Attribute) and n.attr in SEWN_METHODS:
                todo.append("_Sewn")
    return globals_read, machine_attrs


def test_the_body_reads_only_what_the_key_covers():
    """If this fails, `_travel_path` (or something it calls) now reads a
    global it did not: put it in `_TravelMemo.key`, or -- if it truly is a
    constant or a pure cache -- add it to the right set above, with why."""
    globals_read, machine_attrs = _reads()
    assert globals_read == CONSTANTS | PURE_CACHES | FUNCTIONS | LIBRARIES
    assert machine_attrs == MACHINE


def test_no_contextvar_and_no_knob_is_read():
    for name in CONSTANTS:
        v = getattr(F, name)
        assert type(v) in (int, float), name
    for name in MACHINE:
        assert type(getattr(machine, name)) in (int, float), name
    globals_read, _ = _reads()
    for name in globals_read:
        assert not isinstance(getattr(F, name), contextvars.ContextVar), name


def test_the_walk_sees_a_new_read():
    """The checker itself: a ContextVar read added to the body is caught."""
    tree = ast.parse(textwrap.dedent("""
        def _travel_path(a):
            if _SEAM_AWARE.get():
                return machine.LINK_MAX_GAP_MM
            return a
    """))
    fn = tree.body[0]
    loads = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)
             and isinstance(n.ctx, ast.Load) and n.id not in _bound(fn)}
    assert "_SEAM_AWARE" in loads and "_SEAM_AWARE" not in CONSTANTS | PURE_CACHES | FUNCTIONS


def test_the_public_function_is_the_body_plus_the_memo():
    """Same signature, so every caller in the package is untouched."""
    assert inspect.signature(F.travel_path) == inspect.signature(F._travel_path)


# ------------------------------------------------------------- the key

ROW = 0.4
HOLED = Polygon([(0, 0), (40, 0), (40, 24), (0, 24)]).difference(
    Polygon([(14, 6), (26, 6), (26, 18), (14, 18)]))
RING = F._inset_ring(HOLED, machine.TRAVEL_INSET_MM)
SLACK = HOLED.buffer(0.01)


@pytest.fixture(autouse=True)
def _clean():
    F.clear_fill_reorder_memo()
    shape_memo.clear()
    yield
    F.clear_fill_reorder_memo()
    shape_memo.clear()
    assert F._TRAVEL_MEMO is None


def _paths():
    return [p for p in F._fill_paths(HOLED, 90.0, ROW, 3.0, 3) if len(p) > 1]


def test_every_input_moves_the_key():
    memo = F._TravelMemo()
    paths = _paths()
    sewn = F._sewn_add(None, F._footprint(paths[0], ROW))
    a, b = (1.0, 1.0), (30.0, 20.0)
    # HOLED's inset is ONE ring (holes are not guides), so the key's ring
    # list gets a second one here for slicing to change it
    RINGS = list(RING) + [LineString([(1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 1.0)])]
    base = memo.key(HOLED, RINGS, a, b, SLACK, sewn, {"unsewn_rings": list(RINGS)})
    variants = [
        memo.key(HOLED, RINGS, (1.0, 1.5), b, SLACK, sewn, {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED, RINGS, a, (30.0, 20.5), SLACK, sewn, {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED.buffer(0.001), RINGS, a, b, SLACK, sewn, {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED, RINGS, a, b, None, sewn, {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED, RINGS, a, b, SLACK.buffer(0.001), sewn, {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED, RINGS[:1], a, b, SLACK, sewn, {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED, None, a, b, SLACK, sewn, {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED, RINGS[1], a, b, SLACK, sewn, {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED, RINGS, a, b, SLACK, None, {"unsewn_rings": list(RINGS)}),
        # the same footprint as a plain geometry: a different kind of `sewn`
        memo.key(HOLED, RINGS, a, b, SLACK, F._footprint(paths[0], ROW),
                 {"unsewn_rings": list(RINGS)}),
        memo.key(HOLED, RINGS, a, b, SLACK, sewn, None),
        memo.key(HOLED, RINGS, a, b, SLACK, sewn, {}),
        memo.key(HOLED, RINGS, a, b, SLACK, sewn, {"unsewn_rings": RINGS[:1]}),
    ]
    assert None not in variants
    assert len(set(variants + [base])) == len(variants) + 1
    # a footprint more is a different sewn
    grown = memo.key(HOLED, RINGS, a, b, SLACK, sewn.add(F._footprint(paths[1], ROW)),
                     {"unsewn_rings": list(RINGS)})
    assert grown != base
    # equal content in a different object is the same key
    twin = F._sewn_add(F._sewn_add(None, F._footprint(paths[0], ROW)),
                       F._footprint(paths[1], ROW))
    assert memo.key(HOLED, RINGS, a, b, SLACK, twin, {"unsewn_rings": list(RINGS)}) == grown
    assert memo.key(Polygon(HOLED), list(RINGS), a, b, Polygon(SLACK), twin,
                    {"unsewn_rings": list(RINGS)}) == grown


def test_sewn_order_is_part_of_the_key():
    paths = _paths()
    memo = F._TravelMemo()
    f0, f1 = F._footprint(paths[0], ROW), F._footprint(paths[1], ROW)
    one = F._sewn_add(F._sewn_add(None, f0), f1)
    two = F._sewn_add(F._sewn_add(None, f1), f0)
    assert one.digest(memo.geom) != two.digest(memo.geom)


@pytest.mark.parametrize("a, b", [((1, 1.0), (30.0, 20.0)), ([1.0, 1.0], (30.0, 20.0)),
                                  ((1.0, 1.0), (30.0, 20)),
                                  ((1.0, 1.0, 0.0), (30.0, 20.0))])
def test_an_end_that_is_not_two_floats_bypasses(a, b):
    assert F._TravelMemo().key(HOLED, RING, a, b, SLACK, None, None) is None


# ------------------------------------------------------------- a hit is the miss

def _walk(paths, route, row_mm=ROW):
    """`_order_cost_walk`'s bridge sequence: one ring cache, footprints laid
    in order. -> [(route, cache rings after)]"""
    out, sewn, cache, cur = [], None, {}, (0.0, 0.0)
    for p in paths:
        bridge = route(HOLED, RING, cur, p[0], SLACK, sewn, cache)
        out.append((bridge, tuple(cache.get("unsewn_rings") or ())))
        sewn = F._sewn_add(sewn, F._footprint(p, row_mm))
        cur = p[-1]
    return out


def _with_memo(fn):
    """Run `fn` with a travel memo open, as `stitch_shape` does."""
    return F._with_travel_memo(fn)()


def test_repeated_walks_are_the_plain_walks():
    paths = _paths()
    rng = random.Random(5)
    orders = [paths, paths[::-1], rng.sample(paths, len(paths)), paths]
    want = [_walk(o, F._travel_path) for o in orders]
    before = dict(F.travel_memo_stats)

    def run():
        return [_walk(o, F.travel_path) for o in orders]
    got = _with_memo(run)
    assert got == want
    hits = F.travel_memo_stats["hit"] - before["hit"]
    assert hits >= len(paths) - 1, "the repeated order must be served from the memo"
    # the cache a hit leaves is the miss's: same rings, same objects
    for g, w in zip(got, want):
        for (_, rg), (_, rw) in zip(g, w):
            assert [r.wkb for r in rg] == [r.wkb for r in rw]


def test_a_hit_is_an_independent_list():
    paths = _paths()

    def run():
        first = F.travel_path(HOLED, RING, paths[0][-1], paths[3][0], SLACK)
        first.append((99.0, 99.0))
        return first, F.travel_path(HOLED, RING, paths[0][-1], paths[3][0], SLACK)
    first, second = _with_memo(run)
    assert first[:-1] == second and (99.0, 99.0) not in second


def test_dead_outside_stitch_shape_even_after_a_raise():
    def boom():
        assert F._TRAVEL_MEMO is not None
        raise RuntimeError("x")
    with pytest.raises(RuntimeError):
        F._with_travel_memo(boom)()
    assert F._TRAVEL_MEMO is None
    before = dict(F.travel_memo_stats)
    F.travel_path(HOLED, RING, (1.0, 1.0), (30.0, 20.0), SLACK)
    assert F.travel_memo_stats == before


def test_points_cap_stores_nothing_past_it(monkeypatch):
    monkeypatch.setattr(F, "_TRAVEL_MEMO_MAX_POINTS", 0)
    paths = _paths()

    def run():
        F.travel_path(HOLED, RING, paths[0][-1], paths[3][0], SLACK)
        return len(F._TRAVEL_MEMO.routes)
    assert _with_memo(run) == 0


# ------------------------------------------------------------- stitch_shape end to end

FIELD = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)],
                [[(4, 4), (8, 4), (8, 8), (4, 8)], [(12, 10), (18, 10), (18, 16), (12, 16)],
                 [(22, 3), (26, 3), (26, 9), (22, 9)]])
KW = dict(angle_deg=None, row_mm=machine.FILL_ROW_MM, stitch_mm=machine.FILL_STITCH_MM,
          underlay_style="edge_run", trim_at_mm=2.0, start_near=(0.0, 0.0))


def _sew(poly, plain: bool, monkeypatch, **kw):
    F.clear_fill_reorder_memo()
    with monkeypatch.context() as m:
        if plain:
            m.setattr(F, "travel_path", F._travel_path)
        runs, report = F.stitch_shape(poly, "s", **{**KW, **kw})
    return [asdict(r) for r in runs], report


@pytest.mark.parametrize("scopes", [(), ("seam",), ("seam", "priced"), ("seam", "one_pass"),
                                    ("seam", "seam_aware"), ("cut_exposed",)])
@pytest.mark.parametrize("kw", [dict(), dict(under_cover=True),
                                dict(under_cover=True, cut_bridges=True),
                                dict(under_cover=True, technique="crosshatch")])
def test_stitch_shape_sews_the_same_runs(monkeypatch, scopes, kw):
    with contextlib.ExitStack() as st:
        for s in scopes:
            st.enter_context({"seam": F.seam_order_scope, "priced": F.seam_priced_scope,
                              "one_pass": F.one_pass_scope, "seam_aware": F.seam_aware_scope,
                              "cut_exposed": F.cut_exposed_scope}[s](True))
        for poly in (FIELD, HOLED):
            want = _sew(poly, True, monkeypatch, **kw)
            before = F.travel_memo_stats["hit"]
            got = _sew(poly, False, monkeypatch, **kw)
            assert got == want
            if kw.get("under_cover") and poly is FIELD and not scopes:
                assert F.travel_memo_stats["hit"] > before, "the memo must be exercised"


def test_section_travel_sews_the_same_runs(monkeypatch):
    cfg = type("Cfg", (), {"extra": {fill_section_travel.KEY: True}})()
    with fill_section_travel.enabled(cfg):
        want = _sew(FIELD, True, monkeypatch, under_cover=True)
        got = _sew(FIELD, False, monkeypatch, under_cover=True)
    assert got == want
