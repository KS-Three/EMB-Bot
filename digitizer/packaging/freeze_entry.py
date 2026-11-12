"""Entry point PyInstaller freezes: the digitizer service as one Windows folder.

Started as the 2026-11-10 spike (docs/packaging-freeze-spike-2026-11-10.md)
and is what `packaging/build_freeze.py` freezes today. It is NOT the launcher
a customer gets (no window, no single-instance check, no browser opened, no
fixed port): that is step 3, a separate module, and `build_freeze.py --entry`
is the one line that swaps it in.

Three things here are the whole point, and all are things `python -m
digitizer_service` cannot do inside a frozen folder:

  - `uvicorn.run` gets the app OBJECT. The service's own `__main__` passes the
    string "digitizer_service.app:app", which PyInstaller's import analysis
    cannot follow.
  - `TESSDATA_PREFIX` points at the `tessdata/` folder bundled beside the
    code. It is the first place `digitizer_core.ocr.tessdata_dir()` looks, so
    OCR needs no Tesseract install on the machine and no engine change.
  - `EMBBOT_STUDIO_DIR` points at the bundled `studio/` (the built Studio),
    set BEFORE `digitizer_service.app` is imported because that module reads
    it once, on its last line. So the folder is the product's one process on
    one loopback port: the Studio at `/`, the API beside it.
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
    studio = False
    if getattr(sys, "frozen", False):
        bundled = os.path.join(sys._MEIPASS, "tessdata")
        if os.path.isdir(bundled):
            os.environ["TESSDATA_PREFIX"] = bundled
        # The bundle's own Studio always wins: a variable left in the shell
        # must not make an installed app serve some other folder.
        bundled = os.path.join(sys._MEIPASS, "studio")
        os.environ.pop("EMBBOT_STUDIO_DIR", None)
        if os.path.isfile(os.path.join(bundled, "index.html")):
            os.environ["EMBBOT_STUDIO_DIR"] = bundled
            studio = True

    import uvicorn

    from digitizer_service.app import app

    print(f"import_s={time.perf_counter() - T0:.2f}", flush=True)
    if studio:
        print(f"Studio: http://127.0.0.1:{port}/", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
