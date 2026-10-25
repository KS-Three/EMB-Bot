---
name: download-stale-guard-2026-10-25
description: Download is DISABLED while a digitized element's stitches are behind its size/garment/settings (Kent 10-25 "block until re-digitized"); one rule in lib/staleness.js drives the run button, the field hatch and Download; no text
metadata:
  type: project
---

W3-10. A corner drag 80 -> 62 mm kept all 8,764 stitches (1.66x the thread per
mm2), and a garment switched after digitizing left a file carrying the first
garment's request (`garment_id` in the POSTed config). Download checked only
the hoop and preflight blocks, so both shipped without a word.

**Kent 2026-10-25 (AskUserQuestion): "Block until re-digitized"** — over the
confirm-and-run option (a) and over leaving it (c). The machine-file buttons
(machine button, DST, PES, EXP, JEF, XXX, VP3, SVG) are `disabled`; PNG and the
PDF worksheet are not files a machine stitches and stay open (same scope as the
hoop gate). The Digitize button is lit with a halo (`dgp-run-lit`,
`data-blocks-download`). **No words anywhere** (no-warnings ruling 10-02), and
nothing re-runs on its own (10-05): the run is the customer's click.

- **One rule:** `app/src/lib/staleness.js` `isElementStale(element, project,
  {baselineKey})` = resized (resizedTargetWidth) OR pending shape edits OR the
  config it would send now differs from `appliedConfig`. It is the panel's old
  rule moved out, so the panel did not change meaning; the field's hatch used
  to cover shape edits only and now covers all three.
- **Locks only what the customer can unlock:** `blocksDownload(project,
  health)` = stale AND `sourcePng` AND the service up. Without the service the
  button cannot run, and the panel's own offline note promises the saved result
  "still sews and exports".
- **Known gaps, deliberate:** (1) a design saved before `appliedConfig`
  existed (null) has nothing to compare the config with; only the panel, which
  has its mount key, sees a config change there. Resize and pending edits are
  seen everywhere. (2) The config includes `thread_brand`, `garment_rgb` and
  `fabric_profile`, so flipping the thread chart (the Download sheet has the
  selector) or the fabric colour makes the element stale, as it always made
  the button transparent. If Kent finds that too much, narrow it in
  `isElementStale` — one place.
- **`runDigitize` was NOT extracted** into `lib/runDigitize.js`: only the
  confirm-and-run option needed a run from an unmounted panel. Under "block",
  the customer selects the element and presses its button.
- No `Tee` garment exists in the engine's ten; the e2e goes Left Chest -> Hat
  Front (tee fabric -> structured cap).

**Why:** a stale file ships a physical job on the wrong density or fabric
preset, and the customer was told nothing.

**How to apply:** any new input to `buildDigitizeConfig` automatically counts
as "behind" through the config key. To make Download care about less, change
`isElementStale`, not the three consumers. Related: [[no-warnings-reaches-readouts]],
[[studio-configurator-pr1-2026-09-30]].
