---
name: digitizer-local-env
description: "Kent's-machine digitizer env facts — venv is editable-installed since 2026-08-17, and system tesseract is NOT installed so the real-read OCR tests skip locally (skipif since PR #165; CI has it)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 454c41ed-686f-44ec-97b3-9a1c6fd607a8
  modified: 2026-08-18T00:23:55.802Z
---

Two machine-local facts about `C:\Users\EE-LT-11030\Personal\EMB-Bot\digitizer` (Kent's Windows box), both confirmed 2026-08-17:

1. **Venv is editable now.** The venv had stale NON-editable copies of `digitizer_core`/`digitizer_service` in site-packages (installed 2026-08-15); from any cwd other than `digitizer/` they silently shadowed repo code. Fixed 2026-08-17: `pip uninstall digitizer-core` + `pip install -e ".[service,dev]"`. Verify with `pip show digitizer-core` — it must list `Editable project location: ...\EMB-Bot\digitizer`. If that line is missing, someone reran a non-editable install and the shadowing is back.

2. **System `tesseract` binary is not installed** (not on PATH). It is a separate non-pip install (`digitizer/README.md` Setup; pyproject comment near `pytesseract`). Consequence: the five real-read OCR tests SKIP locally — `skipif(shutil.which("tesseract") is None)` since PR #165 (2026-08-17). Before those markers they FAILED as unexplained local reds; the confirmed set (not "presumably") was the OCR-gate damaging case, both `test_ocr_suggest` real reads, and `test_pipeline`/`test_service`'s `saw_a_real_character` tests. CI apt-installs tesseract and runs all five. Reproduced on an untouched checkout, so it is environment, not code. Install tesseract on PATH to exercise OCR end-to-end — but don't install system software without asking Kent. Related local-failure memory: [[windows-goldens-fail-locally]].
