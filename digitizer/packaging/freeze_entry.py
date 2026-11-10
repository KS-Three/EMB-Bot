"""Entry point PyInstaller freezes: the digitizer service as one Windows folder.

SPIKE (2026-11-10, docs/packaging-freeze-spike-2026-11-10.md). It proves the
engine survives freezing; it is not the launcher a customer gets (no window,
no single-instance check, no Studio). Build command: that doc, "Recipe".

Two things here are the whole point, and both are things `python -m
digitizer_service` cannot do inside a frozen folder:

  - `uvicorn.run` gets the app OBJECT. The service's own `__main__` passes the
    string "digitizer_service.app:app", which PyInstaller's import analysis
    cannot follow.
  - `TESSDATA_PREFIX` points at the `tessdata/` folder bundled beside the
    code. It is the first place `digitizer_core.ocr.tessdata_dir()` looks, so
    OCR needs no Tesseract install on the machine and no engine change.
"""
from __future__ import annotations

import os
import sys
import time

T0 = time.perf_counter()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("usage: freeze_entry [PORT]   (default 8732, loopback only)")
        return
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8732
    if getattr(sys, "frozen", False):
        bundled = os.path.join(sys._MEIPASS, "tessdata")
        if os.path.isdir(bundled):
            os.environ["TESSDATA_PREFIX"] = bundled

    import uvicorn

    from digitizer_service.app import app

    print(f"import_s={time.perf_counter() - T0:.2f}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
