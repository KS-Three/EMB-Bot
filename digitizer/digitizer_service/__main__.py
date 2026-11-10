"""Run the service.

Binds 127.0.0.1 on purpose. The artwork on this machine is customer work and
the engine is the product; neither goes on a network until the shared-secret
seam in `app.py` is switched on and something in front of it is doing TLS.
"""
from __future__ import annotations

import argparse
import os
import sys

import uvicorn

from .studio import STUDIO_DIR_ENV, StudioMissing, mount_studio, studio_root


def main() -> None:
    ap = argparse.ArgumentParser(prog="digitizer_service", description=__doc__)
    ap.add_argument("--host", default="127.0.0.1", help="default 127.0.0.1 (loopback only)")
    ap.add_argument("--port", type=int, default=8721)
    ap.add_argument("--reload", action="store_true", help="dev autoreload")
    ap.add_argument("--studio", metavar="DIR", default=None,
                    help="also serve the built Studio in DIR (app/dist) at / on this port; "
                         "off by default")
    args = ap.parse_args()

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(
            f"WARNING: binding {args.host} exposes the digitizer beyond this machine.\n"
            "         Set EMBBOT_SERVICE_TOKEN and put TLS in front of it first."
        )

    if args.studio:
        # Checked HERE so a wrong path is one line and exit 2, not a traceback.
        try:
            root = studio_root(args.studio)
        except StudioMissing as exc:
            print(f"error: --studio: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        # TWO routes to the app, because `python -m digitizer_service` imports
        # the package first and `__init__.py` imports `app`: by the time this
        # line runs the app is already built and `app.py` has already looked
        # for the variable. So mount on that object for THIS process, and set
        # the variable for the one that imports afresh (uvicorn's --reload
        # child). Setting the variable alone printed the URL below and served
        # a 404 (2026-11-10, `test_the_command_line_really_serves_the_page`).
        os.environ[STUDIO_DIR_ENV] = str(root)
        from .app import app

        mount_studio(app, root)
        print(f"Studio: http://{args.host}:{args.port}/")

    uvicorn.run("digitizer_service.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
