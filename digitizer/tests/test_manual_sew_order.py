"""MASTER_SCOPE "Waiting on Kent" 16, triaged: does a sew order the customer
sets by hand in the Studio reach the machine file?

The Studio's hand edits to a digitized design are NOT `/digitize-manual` —
nothing under `app/src` calls that route. They are `shape_overrides` on a
re-sent `/digitize` (`app/src/lib/digitizer.js` `canonicalShapeEdits`): a
block moved in the Sequencer is a `layer` integer on every shape of the two
blocks swapped (`DigitizePanel.svelte` `moveBlock`), a shape moved inside
its colour is a `sew_order` on every shape of that colour
(`reorderWithinLayer`), a tier is `tier`. The file is `/export` on the
`design` the job returned (`exportViaService`). This test drives exactly
that, with the Studio's own ordering rules ported below, and reads the
order back out of the DST bytes by geometry — the file carries no ids.

The verdict, three readings of one edit:

1. The file sews exactly what the review screen lists after "Apply layer
   changes" — `/export` is a transcription, and the review's `sew_index` is
   read off the same plan the design is built from. Holds.
2. A cold re-digitize of the same upload with the same edits (fresh job
   registry, empty generation cache: a restarted service) writes the same
   file. Holds.
3. The file sews in the order the customer ARRANGED — FAILS. Swap the red
   and blue blocks and set red's tier to satin, and red sews third, after
   the orange block, not second. `borders_last_layers` (pipeline.py) moves
   the now-satin red layer to the end and renumbers every layer between;
   `apply_layer_overrides` (regions.py, `r.meta["layer"] = int(ov["layer"])`)
   then writes the Studio's layer integers, minted in the PREVIOUS run's
   numbering, into the new one — red lands in orange's layer, and stage 7
   sews orange first. The review screen redraws to match the file, so the
   customer is shown the lost order rather than told.

Reading 3 is pinned to today's behaviour so CI stays green and a fix turns
this red on purpose. `EMBBOT_STRICT_MANUAL_SEW_ORDER=1` asserts the order
the customer arranged instead — the test a fix must make pass.
"""
from __future__ import annotations

import io
import json
import os
import time
from pathlib import Path

import numpy as np
import pystitch
import pytest
import shapely
from shapely.geometry import Polygon

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")

ART = Path(__file__).resolve().parents[1] / "testdata" / "logo_whitebg.png"
BASE = {"target_width_mm": 80.0, "preflight": False}
STRICT = os.environ.get("EMBBOT_STRICT_MANUAL_SEW_ORDER") == "1"
# A needle-down stitch within this distance of a shape's outline is that
# shape's: a run-tier shape sews ON its outline, and a satin's pull
# compensation stands a fraction of a millimetre outside it.
NEAR_MM = 0.3


def _digitize(client, config: dict) -> dict:
    with ART.open("rb") as f:
        r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps(config)})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    for _ in range(1200):
        state = client.get(f"/jobs/{job_id}").json()
        if state["state"] in ("done", "error"):
            break
        time.sleep(0.1)
    assert state["state"] == "done", state.get("detail") or state.get("error")
    return state


# --- the Studio's ordering rules, ported verbatim from app/src/lib/digitizer.js
# (effLayer, sortShapes, effSewOrder, layerSiblings) and DigitizePanel.svelte
# (effStitched, sewableShapes, moveBlock).

def _rows(review: dict) -> list[dict]:
    return [{"id": s["shape_id"], "layer": s["layer"], "sewIndex": s["sew_index"],
             "thread": s["thread_number"], "stitched": s["stitched"] is not False,
             "tier": s["tier"], "area": s["area_mm2"],
             "poly": Polygon(s["outline_mm"], s["holes_mm"])}
            for s in review["shapes"]]


def _idx(v):
    return 1e9 if v is None else v


def _eff_layer(row, ov):
    e = ov.get(row["id"], {})
    if isinstance(e.get("layer"), int):
        return e["layer"]
    return row["layer"] if row["layer"] is not None else _idx(row["sewIndex"])


def _eff_sew_order(row, ov):
    e = ov.get(row["id"], {})
    return e["sew_order"] if isinstance(e.get("sew_order"), int) else _idx(row["sewIndex"])


def _sewable(rows, ov):
    """sortShapes, then the sewableShapes filter (no deletions here)."""
    ordered = sorted(rows, key=lambda r: (_eff_layer(r, ov), _idx(r["sewIndex"]), r["id"]))
    return [r for r in ordered
            if (ov.get(r["id"], {}).get("stitched", r["stitched"])) is True]


def _shown_order(rows, ov) -> list[str]:
    """The sew order the Layers list shows: blocks by effective layer, and
    inside each the layerSiblings order its up/down buttons walk."""
    out, seen = [], set()
    sew = _sewable(rows, ov)
    for r in sew:
        layer = _eff_layer(r, ov)
        if layer in seen:
            continue
        seen.add(layer)
        sibs = [x for x in sew if _eff_layer(x, ov) == layer]
        out += [x["id"] for x in sorted(sibs, key=lambda x: (_eff_sew_order(x, ov), x["id"]))]
    return out


def _move_block(rows, ov, layer, other):
    for r in _sewable(rows, ov):
        rl = _eff_layer(r, ov)
        if rl == layer:
            ov.setdefault(r["id"], {})["layer"] = other
        elif rl == other:
            ov.setdefault(r["id"], {})["layer"] = layer


# --- the file, read back -------------------------------------------------

def _export_dst(client, design: dict) -> bytes:
    r = client.post("/export", json={"design": design, "format": "dst", "label": "SO16"})
    assert r.status_code == 200, r.text
    return r.content


def _sewn_order(dst: bytes, rows) -> list[str]:
    """Shape ids in the order the FILE first sews each one. Each colour block
    is given to the thread whose shapes hold most of its needle-down
    stitches; a shape is sewn at the first stitch of a block of its own
    thread that lands on it. Geometry only: a DST carries no ids, and the
    trailing design-edge blocks (borders, the edge cap) re-sew threads
    whose shapes are already placed, so they cannot move a first stitch."""
    pattern = pystitch.read_dst(io.BytesIO(dst))
    blocks: list[list[tuple[float, float]]] = [[]]
    for x, y, cmd in pattern.stitches:
        cmd &= pystitch.COMMAND_MASK
        if cmd == pystitch.COLOR_CHANGE:
            blocks.append([])
        elif cmd == pystitch.STITCH:
            blocks[-1].append((x / 10.0, y / 10.0))   # file: 0.1 mm, y-down = review frame
    sewn = [r for r in rows if r["stitched"] and r["sewIndex"] is not None]
    first: dict[str, int] = {}
    offset = 0
    for pts in (b for b in blocks if b):
        xy = np.asarray(pts)
        on = {r["id"]: shapely.dwithin(r["poly"], shapely.points(xy), NEAR_MM) for r in sewn}
        by_thread: dict[str, int] = {}
        for r in sewn:
            by_thread[r["thread"]] = by_thread.get(r["thread"], 0) + int(on[r["id"]].sum())
        thread = max(by_thread, key=by_thread.get)
        for r in sewn:
            hit = np.flatnonzero(on[r["id"]])
            if r["thread"] == thread and hit.size and r["id"] not in first:
                first[r["id"]] = offset + int(hit[0])
        offset += len(pts)
    return sorted(first, key=first.get)


def test_a_hand_set_sew_order_reaches_the_exported_file(client, monkeypatch):
    import importlib

    from digitizer_service.jobs import JobRegistry
    # The MODULE: `digitizer_service.app` as an attribute is the FastAPI object.
    service = importlib.import_module("digitizer_service.app")

    auto = _digitize(client, BASE)
    rows0 = _rows(auto["review"])
    by_thread: dict[str, list[dict]] = {}
    for r in rows0:
        by_thread.setdefault(r["thread"], []).append(r)
    red, blue = by_thread["1704"][0], by_thread["3902"][0]
    orange = sorted(by_thread["1305"], key=lambda r: _idx(r["sewIndex"]))
    assert len(orange) == 2 and orange[0]["layer"] == orange[1]["layer"], \
        "fixture must carry two shapes in one colour for the within-colour move"
    assert red["tier"] == "fill" and red["layer"] < blue["layer"], \
        "fixture: the big red circle is a fill that sews before blue"
    # Control: an unedited design's file sews what its review lists.
    assert _sewn_order(_export_dst(client, auto["design"]), rows0) == _shown_order(rows0, {})

    # The customer's edits, made the way the Studio makes them.
    ov: dict[str, dict] = {}
    _move_block(rows0, ov, red["layer"], blue["layer"])          # Sequencer: blue first
    ov.setdefault(orange[1]["id"], {})["sew_order"] = 0          # Layers: later orange up
    ov.setdefault(orange[0]["id"], {})["sew_order"] = 1
    ov[red["id"]]["tier"] = "satin"                              # tier select on red
    arranged = _shown_order(rows0, ov)
    assert arranged[:4] == [blue["id"], red["id"], orange[1]["id"], orange[0]["id"]]

    edited = _digitize(client, {**BASE, "shape_overrides": ov})
    rows1 = _rows(edited["review"])
    dst = _export_dst(client, edited["design"])
    sewn = _sewn_order(dst, rows1)

    # Reading 1: the file sews exactly what the review lists after Apply.
    assert sewn == _shown_order(rows1, ov)
    # The within-colour move survives either way.
    assert sewn.index(orange[1]["id"]) < sewn.index(orange[0]["id"])

    # Reading 2: a cold re-digitize of the same upload and edits — what a
    # restarted service does with the Studio's re-sent file — writes the
    # same bytes.
    cold_registry = JobRegistry(workers=1)
    monkeypatch.setattr(service, "registry", cold_registry)
    service.generations.clear()
    try:
        cold = _digitize(client, {**BASE, "shape_overrides": ov})
        assert cold["generation_cache"] == "miss"
        assert _export_dst(client, cold["design"]) == dst
    finally:
        cold_registry.shutdown()

    # Reading 3: the order the customer arranged.
    if STRICT:
        assert sewn == arranged, "the hand-set block order must reach the file"
    else:
        # PINNED DEFECT (item 16): red, swapped to sew second, sews after
        # the orange block — the only move. A fix makes this fail; then run
        # with EMBBOT_STRICT_MANUAL_SEW_ORDER=1 and drop this branch.
        lost = [x for x in arranged if x != red["id"]]
        lost.insert(lost.index(orange[0]["id"]) + 1, red["id"])
        assert sewn == lost, (sewn, arranged)
        layer_of = {r["id"]: r["layer"] for r in rows1}
        assert layer_of[red["id"]] == layer_of[orange[0]["id"]], \
            "the mechanism: red's pinned layer integer now names orange's layer"
