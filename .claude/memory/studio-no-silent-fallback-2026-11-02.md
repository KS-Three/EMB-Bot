---
name: studio-no-silent-fallback-2026-11-02
description: Studio no longer routes an uploaded image to the browser JS engine when the digitizer service is down; keeps the art, says so, offers Retry / Use browser engine instead, labels the result's engine
metadata:
  type: project
---

2026-11-02, architecture review item 8, cheap half. `resolveArtworkType` used
to send an image to the `image` (JS flatten) lane whenever `/health` failed,
and nothing told the customer. Now `routeArtwork(health, engineChoice)`
(`app/src/lib/project.js`): healthy -> `digitized`; down with no choice -> the
art is kept as a `digitized` element and `unreachable` is set; down with
`engineChoice === "browser"` -> `image`, `via: "browser"`.

The unreachable state already existed (DigitizePanel's `dgp-offline` block,
shown whenever `!health`); it was wired up, not duplicated. It now reads
"Digitizer service not reachable; retrying…" with Retry and "Use browser
engine instead" (`toBrowserEngineElement`, App `onUseBrowserEngine`), and
re-probes `/health` every 8 s while it shows. Results carry one label,
"Digitizer service" / "Browser engine" (DownloadStep's `out.via` words).
Typed text and drawn shapes still use the JS engine; that lane is theirs.

**Why:** Kent's 2026-10-02 no-warnings ruling bars customer text the customer
cannot act on. This line has two actions (Retry, take the browser engine
knowingly), and the engine label is a result descriptor, not a warning code.

**How to apply:** a new door that adds artwork calls `routeArtwork`, never
picks `image` itself. E2E specs that wanted the browser lane use
`uploadArtwork(..., { engine: "browser" })`. See [[studio-wait-600-2026-10-26]].
