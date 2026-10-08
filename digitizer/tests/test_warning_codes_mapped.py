"""Every warning code the engine emits must have a customer-facing home.

`describeWarnings` falls back to the engine's own `message` for a code with no
`WARNING_TEXT` entry, so an unmapped code reaches the customer as build-log
prose. `test_code_wires.py` guards the opposite direction (a Studio key with no
code behind it); this guards the other: a code with no Studio key.

A code is "mapped" if it has a `WARNING_TEXT` line (a plain sentence) or is a
deliberate member of `SILENT_WARNINGS` (info the customer has nothing to do
with). "Emitted" means the code's constant is referenced as code, not in a
comment, anywhere in the engine or service other than `warnings_codes.py`
itself -- a deliberately generous reading, since a false "emitted" only asks
for a mapping that is harmless.
"""
from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
CORE = REPO / "digitizer"
DIGITIZER_JS = REPO / "app" / "src" / "lib" / "digitizer.js"
WARNINGS_CODES = CORE / "digitizer_core" / "warnings_codes.py"


def _constants() -> dict[str, str]:
    src = WARNINGS_CODES.read_text(encoding="utf-8")
    return dict(re.findall(r'^([A-Z_][A-Z_0-9]*)\s*=\s*"([^"]+)"', src, re.M))


def _emitted(constants: dict[str, str]) -> set[str]:
    code = ""
    for pkg in ("digitizer_core", "digitizer_service"):
        for path in (CORE / pkg).rglob("*.py"):
            if path.name == "warnings_codes.py":
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            code += "\n".join(ln for ln in lines if not ln.lstrip().startswith("#")) + "\n"
    return {v for k, v in constants.items() if re.search(rf"\b{k}\b", code)}


def _warning_text_keys(js: str) -> set[str]:
    m = re.search(r"^const WARNING_TEXT\b", js, re.M)
    end = re.search(r"^};", js[m.start():], re.M)
    return set(re.findall(r"^  ([A-Za-z_0-9]+)\s*:", js[m.start():m.start() + end.start()], re.M))


def _silent(js: str) -> set[str]:
    m = re.search(r"SILENT_WARNINGS\s*=\s*new Set\(\[(.*?)\]\)", js, re.S)
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def test_every_emitted_code_is_translated_or_deliberately_silent():
    constants = _constants()
    emitted = _emitted(constants)
    js = DIGITIZER_JS.read_text(encoding="utf-8")
    text, silent = _warning_text_keys(js), _silent(js)

    # Not vacuous: the parses found real things.
    assert len(constants) >= 55 and len(emitted) >= 50, (len(constants), len(emitted))
    assert "BACKGROUND_ENCLOSED" in emitted and "BACKGROUND_ENCLOSED" in text
    assert "PHOTO_SEGMENT_REGION_COUNT" in silent

    unmapped = sorted(emitted - text - silent)
    assert not unmapped, (
        "These codes are emitted but have no WARNING_TEXT entry in app/src/lib/"
        "digitizer.js, so the customer would read the engine's own message. Add a "
        "plain-words line, or add the code to SILENT_WARNINGS if there is "
        f"nothing for them to do: {unmapped}")
