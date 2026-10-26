---
name: request-contract-and-engine-stamp-2026-10-25
description: W3-14 -- Studio request pinned as a fixture both ways (vitest + pytest), /health carries engine {commit,dirty,started_at,defaults_sha} + capabilities, launcher flags a stale idle service (-ReplaceStale opt-in; auto-replace is Kent's call)
metadata:
  type: project
---

W3-14. Two ways a number, or a judgement Kent makes, can describe something other
than what the customer gets.

**1. The request every flip sheet and pro pair runs on.** `tools.fremont_triage.
studio_request()` is a hand-kept Python copy of `buildDigitizeConfig`
(`app/src/lib/digitizer.js`); `pro_pair.request(width, garment)` swaps the
garment in. It was pinned by source-TEXT checks only. Now
`app/src/lib/fixtures/studio-request.json` is `buildDigitizeConfig` run over a
fresh element on hat_front / left_chest / beanie at 80 and 81 mm (default
fabric, no brand); `studioRequest.contract.spec.js` asserts the live function
equals it and `tests/test_studio_request_contract.py` asserts `studio_request`
and `pro_pair.request` equal it and pass `_parse_config`. Regenerate on purpose
with `UPDATE_STUDIO_REQUEST_FIXTURE=1 npx vitest run
src/lib/studioRequest.contract.spec.js`. **Premise measured: no difference** on
any of the six cases, so no earlier flip number ran on a different request.
Done-test: `max_colors: p.max_colors + 1` in `buildDigitizeConfig` -> vitest red
(`max_colors` 6 vs 7); regenerate the fixture -> 7 pytest red. Neither side
passes alone.

- `thread_brand`: the Studio omits it for the default palette, so the service's
  default chart (isacord) applies. A customer who picked one adds exactly that
  key. Measured as an arm (text-cluster partition, `build_generation` only):
  **Fremont 81 mm hat -- identical under isacord, madeira-rayon, polyneon**
  (162 regions, 5 clusters, 33 tagged). **Becker hat 101.9 mm -- identical under
  isacord and madeira-rayon, DIFFERENT under polyneon** (24 -> 29 regions, 3 -> 4
  tagged letters, one cluster either way). So a flip number is the default-chart
  request; a polyneon customer can get a different Becker. The brand ids are the
  service's (`madeira-rayon`, not `madeira`: `_parse_config` 400s on the bare
  name).
- Structural check: a `PipelineConfig` field read only inside `pipeline.digitize`
  (or a helper only it calls) is inert for the Studio -- the service runs
  `build_generation` -> `finish_generation` -> `plan_stitches`, never `digitize`
  -- and may not default ON. Today exactly two: `tonal_split_layer_cap` and
  `tonal_split_ceiling`, both False. (`tonal_split_veto_mm` is also read in
  stage 2, so it is not digitize-only.)

**2. Which engine answered.** On 2026-10-15 four of Kent's five red circles were
a stale service on 8721 ([[the-80mm-ink-link-2026-10-15]]). `/health` now has
`engine` {commit, dirty, started_at, defaults_sha} and `capabilities`
{background_removal, ocr, face_priors, sam2}, from the pipeline's own probes.
`commit`/`dirty`/`started_at` are read ONCE at import: they name the code the
process loaded, not what the tree holds now. `dirty` = a tracked change under
`digitizer_core/` or `digitizer_service/`. `defaults_sha` = sha256 of
`asdict(PipelineConfig())`, per request, so it moves when a default does.
`ocr` is `shutil.which` and costs ~100 ms per /health on this laptop; the others
are sub-millisecond.

`tools/service-check.mjs` holds the launcher's decision. STALE = service is a
digitizer AND (engine commit != HEAD OR dirty at start); no `engine` block at all
= older than the stamp = stale; an `engine` with no commit = cannot tell = keep.
**Never stopped:** a service whose `jobs` shows running/queued/inflight work (or
that does not say), anything that is not a digitizer, anything on the port that
did not answer. `start-emb-bot.ps1` reports a stale idle one with both commits
and stops it only with `-ReplaceStale`, and then only after a second check that
the listener is a python process; it also waits for `/health` as well as Vite
before opening the browser. Driven end to end under Windows PowerShell 5.1
against a fake stale digitizer: no flag -> `report`; `-ReplaceStale` -> stopped
the child python (the venv stub's child owns the socket), port freed.

**Open for Kent:** should a stale idle service be replaced AUTOMATICALLY (no
flag)? Built opt-in. The catch either way: HEAD moving for a docs-only commit
reads as stale, and a service started on uncommitted edits is stale every launch.
