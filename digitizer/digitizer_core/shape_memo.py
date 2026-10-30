"""A per-job memo of stage 6's pure shape emitters, live only inside `scope()`.

Why. When the Column lane has a letter to take, stage 7 sews the design
TWICE (`stage7_sequence.sequence`): a lane-OFF pass first, read only for the
order its shapes first sew in, then the lane-ON pass that is the plan. Every
non-letter shape the ON pass sews the OFF pass already sewed -- same polygon,
same entry point, same knobs -- and `stitch_shape`, `satin_shape` and
`underfill_rim_runs` are pure functions of their arguments, so the second
answer is the first one. On `owl_kent.jpg` forced flat at 80 mm (2026-10-28,
a photograph whose small regions read as lettering) the ON pass repeated 26
of its 27 fill shapes, 85 of 108 satin shapes and 275 of 315 rim calls: 31 s
of a 143 s job spent re-deriving stitches already in hand.

Exact, not approximately so. A hit is what the miss returned, re-made from a
pickle taken BEFORE the caller touched it: fresh objects, so the ties, hop
burying and tier reports that mutate a shape's runs in one pass never leak
into the other. The key is the pickle of (tag, arguments, ambient) -- a
geometry pickles to its WKB, a float to its bits -- so equal keys mean equal
inputs; a value pickle refuses (a closure such as the blend tier's `keep_row`)
bypasses the memo and runs as before. `ambient` is every `ContextVar` in
`digitizer_core` that an emitter can read without it being an argument
(`_AMBIENT` below; `tests/test_shape_memo.py` checks the list against the
source), so a knob set with a `with` block is part of the question.

Process-wide, one job at a time. The scope and the memo are module state, not
per-job. The service runs one digitize at a time (`JobRegistry(workers=1)`),
so that is what this serves. Two jobs in flight at once would share the memo and
still get exact answers, since every key is the full input, but they would share
the byte cap as well.

Scoped and bounded. `pipeline._plan_stitches` opens the scope round one
stage-7 call and only when the lane is on (`cfg.lettering_columns` and
`cfg.satin`); outside a scope every emitter runs untouched, and the memo is
emptied when the outermost scope closes, so nothing is held between jobs.
Stored pickles stop at `MAX_BYTES` per scope (hits still serve); on owl_kent
the whole job stored about 3 MB.
"""
from __future__ import annotations

import contextlib
import dataclasses
import functools
import hashlib
import pickle
import sys
import threading

from shapely.prepared import PreparedGeometry

#: Stored pickles per scope. Past this a miss is computed and not kept.
MAX_BYTES = 256 * 2**20

#: (module under digitizer_core, name) of every ContextVar an emitter can
#: read. `outline_cut._MEMO` is left out on purpose: it is a cache, and a
#: hit there is what its miss would have built.
_AMBIENT: tuple[tuple[str, str], ...] = (
    ("fill_section_travel", "_ON"),
    ("fill_section_travel", "_CUTS_FIRST"),
    ("stage6_fill", "_CUT_EXPOSED"),
    ("stage6_fill", "_SEAM_ORDER"),
    ("outline_cut", "_APEX_CUT"),
    ("outline_cut", "_RAIL_AXIS"),
    ("outline_cut", "_SMALL_BOLD"),
    ("outline_cut", "_SMALL_BOLD_SIMPLIFY"),
    ("outline_cut", "_CORNER_FOLD"),
    ("stage6_border", "_LOOP_MITRE"),
    ("stage6_border", "_LOOP_CHAIN"),
    ("column_lean", "_ITALIC"),
)
#: ContextVars that are caches, not knobs.
_CACHES: frozenset[tuple[str, str]] = frozenset({("outline_cut", "_MEMO")})
#: ContextVars no emitter's OUTPUT depends on: `deadline._DEADLINE` is the
#: service's job budget, read by `deadline.check` to STOP a job, never to
#: shape a stitch -- a hit under one deadline is the miss under any other.
_INERT: frozenset[tuple[str, str]] = frozenset({("deadline", "_DEADLINE")})

_UNIMPORTED = "<unimported>"

_lock = threading.Lock()
_depth = 0
_memo: dict[bytes, bytes] = {}
_bytes = 0
stats = {"hit": 0, "miss": 0, "bypass": 0}


def active() -> bool:
    return _depth > 0


def reset_stats() -> None:
    for k in stats:
        stats[k] = 0


def clear() -> None:
    """Empty the memo (tests)."""
    global _bytes
    with _lock:
        _memo.clear()
        _bytes = 0


@contextlib.contextmanager
def scope(enabled: bool = True):
    """Memoize the emitters until this closes. Nested scopes share one memo,
    emptied when the outermost closes. `enabled=False` is a no-op."""
    global _depth
    if not enabled:
        yield
        return
    with _lock:
        _depth += 1
    try:
        yield
    finally:
        with _lock:
            _depth -= 1
            if _depth == 0:
                _memo.clear()
                global _bytes
                _bytes = 0


def _plain(v):
    """A picklable stand-in for a value: a prepared geometry by its source
    geometry (WKB), a dataclass by its fields, containers elementwise."""
    if isinstance(v, PreparedGeometry):
        return ("prepared", v.context.wkb)
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return (type(v).__qualname__,) + tuple(
            _plain(getattr(v, f.name)) for f in dataclasses.fields(v))
    if isinstance(v, (tuple, list)):
        return tuple(_plain(x) for x in v)
    if isinstance(v, dict):
        return tuple((k, _plain(x)) for k, x in v.items())
    return v


def _ambient() -> tuple:
    out = []
    for mod, name in _AMBIENT:
        m = sys.modules.get(f"digitizer_core.{mod}")
        out.append(_UNIMPORTED if m is None else _plain(getattr(m, name).get()))
    return tuple(out)


def _key(tag: str, args: tuple, kwargs: dict) -> bytes | None:
    try:
        blob = pickle.dumps((tag, _plain(args), _plain(sorted(kwargs.items())), _ambient()),
                            protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:  # noqa: BLE001 - anything pickle refuses means "run it"
        return None
    return hashlib.blake2b(blob, digest_size=32).digest()


def memoized(tag: str):
    """Decorate a pure emitter. Inactive outside `scope()`."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if _depth == 0:
                return fn(*args, **kwargs)
            key = _key(tag, args, kwargs)
            if key is None:
                stats["bypass"] += 1
                return fn(*args, **kwargs)
            hit = _memo.get(key)
            if hit is not None:
                stats["hit"] += 1
                return pickle.loads(hit)
            stats["miss"] += 1
            out = fn(*args, **kwargs)
            try:
                blob = pickle.dumps(out, protocol=pickle.HIGHEST_PROTOCOL)
            except Exception:  # noqa: BLE001 - not storable: still the right answer
                return out
            global _bytes
            with _lock:
                if _bytes + len(blob) <= MAX_BYTES:
                    _memo[key] = blob
                    _bytes += len(blob)
            return out
        wrapper.__shape_memo_tag__ = tag
        return wrapper
    return deco
