# SAM2 Studio seam — design

**Date:** 2026-08-11 · **Scope:** give the already-built SAM2 photo segmenter
a way to be switched on from Studio, for internal/advanced use only.

## Problem

The SAM2 photo region former landed complete on 2026-08-11 (merged from
`sam2-segmentation`): config gate, isolated-venv worker, never-raises seam,
silent fallback, full test coverage. But `PipelineConfig.photo_segment_sam2`
defaults to `False` and nothing in Studio ever sets it, so the whole lane is
unreachable from the real product — it can only be exercised by a Python
caller constructing its own `PipelineConfig`.

SAM2 is not a feature to put in front of customers: it needs a manually built
isolated venv (`digitizer/sam2_isolated/`, ~2-3 GB) plus a checkpoint download
that happens on first real use, and it adds real per-image latency on CPU.
Owner decision, 2026-08-11: **internal/advanced only, hidden by default** —
no customer-facing control, no setup guidance in the UI.

## What already works, verified not assumed

Three things that would otherwise have been built unnecessarily:

1. **The service already accepts the flag.** `digitizer_service/app.py:51`
   derives its allowlist dynamically:
   `_CONFIG_FIELDS = {f.name for f in dataclass_fields(PipelineConfig)} - {...}`,
   so all five `photo_segment_sam2*` fields validate today. Confirmed by
   parsing `{"photo_segment_sam2": true, ...}` through the real
   `_parse_config` — it round-trips. **No service-side change is needed.**
2. **The result is already observable.** `digitizer.js:1113`'s
   `describeWarnings` renders any warning it lacks a `WARNING_TEXT` entry for
   using the server's own `message` string. `PHOTO_SAM2_SEGMENTED` (emitted
   on success, `stage2_sam2_segment.py:319`) and
   `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE` (emitted on fallback,
   `pipeline.py:250`) both carry real messages, so the existing warnings list
   in `DigitizePanel.svelte` already tells you which segmenter actually ran.
   This matters more than it sounds: the seam's whole contract is *silent*
   fallback, so without this there would be no way to tell SAM2 output from
   SLIC+RAG output.
3. **There is an established precedent for a hidden dev toggle.**
   `DIGITIZER_URL_KEY = "embstudio:digitizerUrl"` (`digitizer.js:37`) is
   localStorage-only with no UI anywhere, and its own comment calls it "a
   dev/ops seam". This design copies that shape rather than inventing one.

## Design

Two additions to `app/src/lib/digitizer.js`, mirroring the `digitizerUrl`
precedent directly:

```js
export const SAM2_KEY = "embstudio:sam2";

export function sam2Enabled() {
  try { return localStorage.getItem(SAM2_KEY) === "1"; } catch (e) { return false; }
}
```

and one line inside `buildDigitizeConfig`, alongside the existing
`thread_brand` per-request context:

```js
if (sam2Enabled()) cfg.photo_segment_sam2 = true;
```

Turned on from devtools: `localStorage.setItem('embstudio:sam2','1')`.

### Why a global preference, not a per-element param

`buildDigitizeConfig`'s own docstring establishes the split: `element.params`
holds the design's own settings ("the persisted params ARE the request"),
while per-request context like `thread_brand` and `garment_id` is added here.
The SAM2 flag is context, not a property of a design — you switch it on to
evaluate the segmenter across designs, not to record a choice about one. It
also keeps the flag out of saved `.embproj` files, so a project built with it
on doesn't carry a stale flag to a machine with no SAM2 installed.

### Interaction with the job cache, deliberately

`content_key` hashes the config, so toggling the flag changes the cache key
and forces a re-digitize — correct, since it is a different pipeline. The
useful consequence: flipping the flag back is a cache *hit*, so A/B comparing
SAM2 against SLIC+RAG on one image costs one digitize, not two.

The flag is sent regardless of the design's class. The backend gates on
classification (`pipeline.py:240`: `photo_subject`/`photo_scene` only), so a
`flat` or `gradient` design ignores it entirely — but its cache key still
changes when the flag is toggled. Accepted: consistent and predictable beats
a Studio-side guess at a classification only the server computes.

### Absence of a UI

No component, no settings panel, no visible control anywhere — that IS the
design, per the owner decision above. `describeWarnings` already surfaces the
outcome, and `digitizerUrl` establishes that a localStorage-only seam is this
codebase's normal way to express "operator/dev knob, not a product feature."

## Testing

`app/src/lib/digitizer.spec.js` already covers `buildDigitizeConfig`
(including a test asserting a key is *omitted* when unset — same shape as
what's needed here). Two cases to add:

- flag unset → `photo_segment_sam2` absent from the config entirely
- flag set to `"1"` → `photo_segment_sam2: true` present

The `try/catch` fallback (localStorage throwing, e.g. disabled storage)
returns `false`, matching `digitizerUrl`'s own defensive posture; covered by
whichever mechanism that file already uses to stub storage.

## Non-goals

- No customer-facing control, no in-app setup guidance for building the
  isolated venv (the owner decision; `digitizer/sam2_isolated/README.md` is
  the documentation for that).
- No exposure of the other four `photo_segment_sam2_*` tuning fields
  (checkpoint tier, points-per-side, max side, timeout). They are already
  accepted by the service, so a future need is a small change on the same
  seam; nothing is designed for them now.
- No change to the fallback contract, warning codes, or anything in
  `digitizer/`.
