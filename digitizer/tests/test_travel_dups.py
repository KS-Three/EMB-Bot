"""`tools/travel_dups.py`: the repeat counter for `stage6_fill.travel_path`.

A repeat count is only an upper bound on what a memo could save if its key
is EXACT, i.e. if two calls with equal keys really ask the same question.
Pinned here:

- the key covers everything `travel_path` reads. An AST walk of its call
  graph inside stage6_fill finds exactly the globals and `machine` constants
  listed below, and none of them is a ContextVar. A new read (a knob, a
  ContextVar, another module) fails this file until the key covers it or it
  is shown to be a constant or a pure cache;
- every input moves the key, and an end that is not a tuple of two floats
  is not keyed;
- equal keys get equal routes and leave the ring cache in the same state;
- counting changes nothing `stitch_shape` sews, and finds the repeats a
  covered fill asks.
"""
from __future__ import annotations

import ast
import builtins
import contextvars
import random
import textwrap
from dataclasses import asdict
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon

from digitizer_core import machine
from digitizer_core import stage6_fill as F
from tools import travel_dups

SRC = Path(F.__file__).read_text()

# ------------------------------------------------------------- what the function reads

#: Module globals `travel_path`'s call graph reads, by kind. Every input the
#: key covers is an ARGUMENT, so each name here must be immutable for the
#: process, or a cache whose hit is what its miss would build.
CONSTANTS = {"_TRAVEL_DETOUR_FLOOR_MM", "_TRAVEL_DETOUR_FACTOR", "_TRAVEL_RING_CANDIDATES",
             "_TRAVEL_WINDOW_MARGIN_MM", "_EXPOSED_TOLERANCE_MM", "_UNSEWN_MAX"}
PURE_CACHES = {"_UNSEWN_MEMO"}           # `_ring_arc` is an lru_cache: a function below
FUNCTIONS = {"_densify", "_ring_ways", "_ring_route", "_ring_arc", "_exposed_mm",
             "_unsewn_ground", "_inset_ring", "_Sewn"}
#: `functools` is `_ring_arc`'s decorator
LIBRARIES = {"math", "np", "shapely", "hashlib", "struct", "machine", "functools",
             "LineString", "Point", "Polygon", "box"}
#: `machine.X` read anywhere in the graph: plain numbers, fixed for a process
MACHINE = {"TINY_STITCH_MM", "TRAVEL_STITCH_MM", "TRAVEL_INSET_MM", "FILL_ROW_MM"}
#: `_Sewn` methods reached through `sewn.<method>` (the class is walked whole)
SEWN_METHODS = {"clipped", "on_line", "_hits", "add"}


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
    parameters and names, and assignment / loop / comprehension / with /
    except targets."""
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
    """(module globals, `machine` attributes) read by `travel_path`'s graph."""
    funcs, classes = _module_defs()
    globals_read, machine_attrs = set(), set()
    todo, done = ["travel_path"], set()
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


def test_travel_path_reads_only_what_the_key_covers():
    """If this fails, `travel_path` (or something it calls) now reads a global
    it did not: key it in `travel_dups.Key`, or, if it truly is a constant or
    a pure cache, add it to the right set above and say why."""
    globals_read, machine_attrs = _reads()
    assert globals_read == CONSTANTS | PURE_CACHES | FUNCTIONS | LIBRARIES
    assert machine_attrs == MACHINE


def test_no_contextvar_and_no_knob_is_read():
    for name in CONSTANTS:
        assert type(getattr(F, name)) in (int, float), name
    for name in MACHINE:
        assert type(getattr(machine, name)) in (int, float), name
    globals_read, _ = _reads()
    for name in globals_read:
        assert not isinstance(getattr(F, name), contextvars.ContextVar), name


def test_the_walk_sees_a_new_read():
    """The checker itself: a ContextVar read added to a function is a load it
    reports, and not one the sets above admit."""
    fn = ast.parse(textwrap.dedent("""
        def travel_path(a):
            if _SEAM_AWARE.get():
                return machine.LINK_MAX_GAP_MM
            return a
    """)).body[0]
    loads = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)
             and isinstance(n.ctx, ast.Load) and n.id not in _bound(fn)}
    assert "_SEAM_AWARE" in loads
    assert "_SEAM_AWARE" not in CONSTANTS | PURE_CACHES | FUNCTIONS | LIBRARIES


def test_the_key_reads_the_sewn_fields_that_exist():
    """`Key` reads `_Sewn._n` and `_Sewn._parts`; a renamed field breaks it here."""
    sewn = F._sewn_add(None, Polygon([(0, 0), (1, 0), (1, 1)]))
    assert sewn._n == 1 and sewn._parts[0].area == 0.5


# ------------------------------------------------------------- the key

ROW = 0.4
HOLED = Polygon([(0, 0), (40, 0), (40, 24), (0, 24)]).difference(
    Polygon([(14, 6), (26, 6), (26, 18), (14, 18)]))
RING = F._inset_ring(HOLED, machine.TRAVEL_INSET_MM)
SLACK = HOLED.buffer(0.01)


@pytest.fixture(autouse=True)
def _clean():
    F.clear_fill_reorder_memo()
    yield
    F.clear_fill_reorder_memo()


def _paths():
    return [p for p in F._fill_paths(HOLED, 90.0, ROW, 3.0, 3) if len(p) > 1]


def test_every_input_moves_the_key():
    key = travel_dups.Key()
    paths = _paths()
    sewn = F._sewn_add(None, F._footprint(paths[0], ROW))
    a, b = (1.0, 1.0), (30.0, 20.0)
    # HOLED's inset is ONE ring (holes are not guides), so the ring list gets
    # a second one for slicing to change it
    rings = list(RING) + [LineString([(1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 1.0)])]

    def k(poly=HOLED, ring=rings, a=a, b=b, slack=SLACK, sewn=sewn, cache=None):
        return key(poly, ring, a, b, slack, sewn,
                   {"unsewn_rings": list(rings)} if cache is None else cache)
    base = k()
    variants = [
        k(a=(1.0, 1.5)), k(b=(30.0, 20.5)), k(poly=HOLED.buffer(0.001)),
        k(slack=None), k(slack=SLACK.buffer(0.001)),
        k(ring=rings[:1]), k(ring=None), k(ring=rings[1]),
        k(sewn=None), k(sewn=F._footprint(paths[0], ROW)),   # a plain geometry
        key(HOLED, rings, a, b, SLACK, sewn, None),
        k(cache={}), k(cache={"unsewn_rings": rings[:1]}),
    ]
    assert None not in variants
    assert len(set(variants + [base])) == len(variants) + 1
    grown = k(sewn=sewn.add(F._footprint(paths[1], ROW)))
    assert grown != base
    # equal content in other objects is the same key
    twin = F._sewn_add(F._sewn_add(None, F._footprint(paths[0], ROW)),
                       F._footprint(paths[1], ROW))
    assert k(sewn=twin) == grown
    assert k(poly=Polygon(HOLED), ring=list(rings), slack=Polygon(SLACK), sewn=twin) == grown


def test_sewn_order_is_part_of_the_key():
    paths = _paths()
    key = travel_dups.Key()
    f0, f1 = F._footprint(paths[0], ROW), F._footprint(paths[1], ROW)
    one = F._sewn_add(F._sewn_add(None, f0), f1)
    two = F._sewn_add(F._sewn_add(None, f1), f0)
    a, b = (1.0, 1.0), (30.0, 20.0)
    assert key(HOLED, RING, a, b, SLACK, one, None) != key(HOLED, RING, a, b, SLACK, two, None)


@pytest.mark.parametrize("a, b", [((1, 1.0), (30.0, 20.0)), ([1.0, 1.0], (30.0, 20.0)),
                                  ((1.0, 1.0), (30.0, 20)), ((1.0, 1.0, 0.0), (30.0, 20.0))])
def test_an_end_that_is_not_two_floats_is_not_keyed(a, b):
    assert travel_dups.Key()(HOLED, RING, a, b, SLACK, None, None) is None


def test_equal_keys_get_equal_routes_and_leave_equal_caches():
    """Walk the plate's bridges in several orders, as `_order_cost_walk` does
    (one ring cache per walk, footprints laid in order), the first order
    twice. Every repeated key gets the route it got before and leaves the
    same rings in the cache."""
    paths = _paths()
    rng = random.Random(5)
    key = travel_dups.Key()
    seen: dict = {}
    repeats = 0
    for order in (paths, paths[::-1], rng.sample(paths, len(paths)), paths):
        sewn, cache, cur = None, {}, (0.0, 0.0)
        for p in order:
            k = key(HOLED, RING, cur, p[0], SLACK, sewn, cache)
            route = F.travel_path(HOLED, RING, cur, p[0], SLACK, sewn, cache)
            after = tuple(r.wkb for r in cache.get("unsewn_rings") or ())
            if k in seen:
                repeats += 1
                assert seen[k] == (route, after)
            seen[k] = (route, after)
            sewn = F._sewn_add(sewn, F._footprint(p, ROW))
            cur = p[-1]
    assert repeats >= len(paths) - 1, "the repeated order must repeat its keys"


# ------------------------------------------------------------- counting

FIELD = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)],
                [[(4, 4), (8, 4), (8, 8), (4, 8)], [(12, 10), (18, 10), (18, 16), (12, 16)],
                 [(22, 3), (26, 3), (26, 9), (22, 9)]])
KW = dict(angle_deg=None, row_mm=machine.FILL_ROW_MM, stitch_mm=machine.FILL_STITCH_MM,
          underlay_style="edge_run", trim_at_mm=2.0, start_near=(0.0, 0.0), under_cover=True)


def _sew():
    F.clear_fill_reorder_memo()
    runs, report = F.stitch_shape(FIELD, "s", **KW)
    return [asdict(r) for r in runs], report


def test_counting_changes_nothing_and_finds_the_repeats():
    want = _sew()
    original = F.travel_path
    with travel_dups.counting() as report:
        got = _sew()
        F.travel_path(HOLED, RING, (1.0, 1.0), (30.0, 20.0), SLACK)   # not under a shape
    assert F.travel_path is original
    assert got == want
    assert report["calls"] > 0 and report["unscoped"] == 1 and report["bypass"] == 0
    assert 0 < report["dups"] <= report["loose"]["no_cache"]["dups"] \
        <= report["loose"]["ends"]["dups"]
    assert report["dup_secs"] <= report["secs"]
