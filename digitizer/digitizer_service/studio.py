"""The built Studio, served by the service itself. Opt-in, off by default.

Why this exists: the product is two servers on a developer's machine (Vite on
5173, this service on 8721) and a customer can install neither. Served from
here, the Studio and the digitizer are ONE process on ONE loopback port, which
is the shape a one-folder Windows build can ship
(`docs/packaging-freeze-spike-2026-11-10.md`).

Nothing changes unless a directory is named: `python -m digitizer_service
--studio <app/dist>` (or `EMBBOT_STUDIO_DIR`). Without it no route is added and
every response is what it was.

Three things a plain `StaticFiles` mount gets wrong for this job:

  - ORDER. The mount is at `/`, so it must be the LAST route or it answers for
    `/health`. `app.py` calls `mount_studio` on its final line for that reason.
  - CONTENT TYPE. Python reads `.js` -> type from the WINDOWS REGISTRY, and a
    machine where some installer set `.js` to `text/plain` gets a Studio whose
    every `<script type="module">` the browser refuses. The types the bundle
    needs are pinned here instead of trusted to the customer's registry.
  - CACHING. `engine/*.js` and `fonts/*` are copied into the bundle under
    their own names, not content-hashed, so a browser that heuristically
    caches them keeps running the OLD engine after an update. `no-cache` means
    "revalidate", not "never store": an unchanged file is a 304 on loopback.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from starlette.staticfiles import StaticFiles

#: Environment seam `app.py` reads at import; `__main__ --studio` sets it.
STUDIO_DIR_ENV = "EMBBOT_STUDIO_DIR"

#: Route name of the mount, so a test (or `/openapi`-style introspection) can
#: tell whether this process is serving a Studio.
MOUNT_NAME = "studio"

#: What the bundle is made of. Pinned, not guessed: see CONTENT TYPE above.
CONTENT_TYPES = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".woff2": "font/woff2",
    ".wasm": "application/wasm",
    ".txt": "text/plain",
}


class StudioMissing(ValueError):
    """The named directory is not a built Studio (no `index.html`)."""


class StudioFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


def studio_root(directory: str | Path) -> Path:
    """`directory` resolved, or `StudioMissing` naming what to run."""
    root = Path(directory).expanduser().resolve()
    if not (root / "index.html").is_file():
        raise StudioMissing(
            f"{root} is not a built Studio (no index.html). "
            "Build one with `cd app && npm run build` and pass app/dist."
        )
    return root


def is_mounted(app) -> bool:
    return any(getattr(r, "name", None) == MOUNT_NAME for r in app.routes)


def mount_studio(app, directory: str | Path) -> Path:
    """Serve the built Studio in `directory` at `/` on `app`. Call it AFTER
    every route is registered: the mount matches every path, and routes are
    tried in the order they were added.

    Mounting twice is a no-op, because there are two callers and which one
    runs first depends on how the process started: `app.py` (the variable was
    set before the import: a launcher, or uvicorn's `--reload` child) and
    `__main__` (the app was already built when the flag was parsed)."""
    root = studio_root(directory)
    if is_mounted(app):
        return root
    for ext, kind in CONTENT_TYPES.items():
        mimetypes.add_type(kind, ext)
    app.mount("/", StudioFiles(directory=root, html=True), name=MOUNT_NAME)
    return root
