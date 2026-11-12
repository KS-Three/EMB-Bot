"""The 2026-11-12 letter-reader replication's pre-registration holds.

`docs/defect-marks-2026-11-12/letter-reader-replication-preregistration.md`
froze the reader of PR #1389, its pin rule, the nine items and the pass line
before any render. These tests fail if any of that moves: the detection
code's AST digest, the item table against the committed art, the inventory
of held-out pins the page reports, and the pass line's arithmetic.
"""
import ast
import hashlib
import importlib.util
import json
import re
from pathlib import Path

from tools import fault_reader_harness as h

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
REPL = DOCS / "defect-marks-2026-11-12"
PREREG = REPL / "letter-reader-replication-preregistration.md"
ART = ROOT / "digitizer" / "testdata" / "art" / "commons_lettering"

FROZEN_DIGEST = "b5211fb9477b76af731d235562d5761e4b8dd4c2ff78d92b26a8e4268ca92870"   # == 79fa7646
FUNCS = ("colour_classes", "to_mm", "_holes", "_deepest", "counter_events", "join_events",
         "bay_events", "read_class", "read_faults")
CONSTS = ("PXMM", "PAD_MM", "THREAD_MM", "MIN_CLEAR_MM", "KEEP_FRAC", "MIN_SHAPE_MM2", "OVERLAP",
          "SEWN_FRAC", "BRIDGE_MIN_MM", "TOUCH_MM2", "COLOUR_MERGE", "UNSEWN")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reader_detection_code_is_frozen():
    src = (ROOT / "digitizer" / "tools" / "letter_fault_reader.py").read_text(encoding="utf-8")
    parts = []
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in FUNCS:
            parts.append(ast.dump(node))
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) in CONSTS for t in node.targets):
            parts.append(ast.dump(node))
    assert len(parts) == len(FUNCS) + len(CONSTS)
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == FROZEN_DIGEST
    assert FROZEN_DIGEST in PREREG.read_text(encoding="utf-8")


def test_pin_rule_words_are_frozen():
    assert h.CLOSE_WORDS == ("spacing", "space between", "merg", "hole", "join", "touch", "intersect",
                             "closed up", "filled in")
    assert h.READ_RE.pattern == r"\bread|can'?t tell|cannot tell|can not tell"
    assert h.LETTER_RE.pattern == r"\"[a-z&]\"|\bletter|\bsymbol"
    assert h.LETTER_KINDS == ("letter_shape",)
    assert (h.RADIUS_MM, h.SENSITIVITY_MM, h.BOOT_DRAWS, h.SEED) == (3.0, (2.0, 5.0), 5000, 20261110)


def test_item_table_matches_committed_art():
    kit = _load("build_kit_1112", REPL / "build_kit.py")
    text = PREREG.read_text(encoding="utf-8")
    table = dict(re.findall(r"\| `C_(lt_[a-z_]+)` \| `([^`]+)` \|", text))
    assert table == kit.ITEMS
    manifest = json.loads((ART / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(table.values()) == sorted(manifest)
    for fname, m in manifest.items():
        assert (ART / fname).exists() and m["licence"] == "Public domain"


def test_held_out_inventory_as_reported():
    """The page's inventory: 11-10 gave the rule its 14 pins on 6 logos;
    11-11 gives 30 pins on one item; the new prefix selects nothing from
    either sitting."""
    m10 = json.loads((DOCS / "defect-marks-2026-11-10" / "marks.json").read_text(encoding="utf-8"))
    m11 = json.loads((DOCS / "defect-marks-2026-11-11" / "marks.json").read_text(encoding="utf-8"))
    p10, p11 = h.select_letter_pins(m10), h.select_letter_pins(m11, "C_")
    assert (len(p10), len({p["item"] for p in p10})) == (14, 6)
    assert (len(p11), {p["item"] for p in p11}) == (30, {"C_silhouette_logo"})
    assert not h.select_letter_pins(m10, "C_lt_") and not h.select_letter_pins(m11, "C_lt_")


def _row(pins, hit, chance):
    return {"pins": pins, "flags": 5,
            "by_radius": {str(r): {"hit": hit, "chance_area": chance} for r in (3.0, 2.0, 5.0)}}


def test_pass_line():
    sr = _load("score_replication_1112", REPL / "score_replication.py")
    strong = {f"C_lt_{i}": _row(3, 3, 0.2) for i in range(6)}
    assert sr.verdict(strong, strong)["verdict"] == "shown, robust"
    four = dict(list(strong.items())[:4])
    assert sr.verdict(four, four)["verdict"] == "no verdict"                 # under MIN_ITEMS
    null = {f"C_lt_{i}": _row(3, i % 2, 0.3) for i in range(6)}
    assert sr.verdict(null, null)["verdict"] == "not shown"
    # 2b fails when only the inherited pins carried it
    assert sr.verdict(strong, null)["verdict"] == "not shown"


def test_drop_inherited_removes_only_bare_pins():
    sr = _load("score_replication_1112b", REPL / "score_replication.py")
    marks = {"items": {"C_lt_x": {"pins": [
        {"x_mm": 1, "y_mm": 1, "what": "mushed", "note": "The letters merge, all the same issue"},
        {"x_mm": 2, "y_mm": 2, "what": None, "note": ""},
        {"x_mm": 3, "y_mm": 3, "what": "gap", "note": ""}]}}}
    assert len(h.select_letter_pins(marks, "C_lt_")) == 2                    # rule 1 + rule 4
    kept = sr.drop_inherited(marks)
    assert [p["x_mm"] for p in kept["items"]["C_lt_x"]["pins"]] == [1, 3]
    assert len(h.select_letter_pins(kept, "C_lt_")) == 1
