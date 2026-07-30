"""Run the service.

Binds 127.0.0.1 on purpose. The artwork on this machine is customer work and
the engine is the product; neither goes on a network until the shared-secret
seam in `app.py` is switched on and something in front of it is doing TLS.
"""
from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    ap = argparse.ArgumentParser(prog="digitizer_service", description=__doc__)
    ap.add_argument("--host", default="127.0.0.1", help="default 127.0.0.1 (loopback only)")
    ap.add_argument("--port", type=int, default=8721)
    ap.add_argument("--reload", action="store_true", help="dev autoreload")
    args = ap.parse_args()

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(
            f"WARNING: binding {args.host} exposes the digitizer beyond this machine.\n"
            "         Set EMBBOT_SERVICE_TOKEN and put TLS in front of it first."
        )

    uvicorn.run("digitizer_service.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
