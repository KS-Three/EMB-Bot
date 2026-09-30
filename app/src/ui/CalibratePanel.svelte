<script>
  // Closed-loop sew-out calibration, the customer flow
  // (docs/sewout-calibration-brief-2026-09-30.md §4). Three steps on the
  // Garment step: download the card for this machine, sew and photograph
  // it, drop the photo and accept the draft profile. Every number shown is
  // the service's (digitizer_core/calibration/profile.py); this panel only
  // carries it and writes `project.fabricProfile` on Accept.
  import { createEventDispatcher } from "svelte";
  import { triggerDownload } from "../lib/download.js";
  import { fabricInForce } from "../lib/generate.js";
  import {
    CARD_FORMATS, downloadCalibrationCard, readCalibrationPhoto,
    readingRows, fmtMm, fmtPct,
  } from "../lib/calibration.js";

  export let project;
  export let digitizerHealth = null;
  const d = createEventDispatcher();

  let busyFormat = "";
  let cardMsg = "";
  let photoBusy = false;
  let photoMsg = "";
  let reading = null;
  let checked = false;
  let fileInput;

  $: serviceUp = !!digitizerHealth;
  $: preset = fabricInForce(project.garmentId, null);
  $: after = reading && reading.profile ? fabricInForce(project.garmentId, reading.profile) : null;
  $: rows = readingRows(reading);
  $: canAccept = !!(reading && reading.profile && checked);

  async function download(format) {
    busyFormat = format;
    cardMsg = "";
    try {
      const out = await downloadCalibrationCard(format);
      triggerDownload(out);
      cardMsg = `Saved ${out.filename}` + (out.widthMm ? ` — ${out.widthMm.toFixed(0)} × ${out.heightMm.toFixed(0)} mm, sew it in a 5×7 hoop.` : ".");
    } catch (e) {
      cardMsg = "Could not build the card: " + (e && e.message ? e.message : String(e));
    } finally {
      busyFormat = "";
    }
  }

  async function onPhoto(e) {
    const file = e.currentTarget && e.currentTarget.files && e.currentTarget.files[0];
    if (!file) return;
    photoBusy = true;
    photoMsg = "";
    reading = null;
    checked = false;
    try {
      reading = await readCalibrationPhoto(file, project.garmentId);
    } catch (err) {
      photoMsg = err && err.message ? err.message : String(err);
    } finally {
      photoBusy = false;
      if (fileInput) fileInput.value = "";
    }
  }

  function accept() {
    if (!canAccept) return;
    d("update", { fabricProfile: reading.profile });
    d("close");
  }

  function discard() {
    reading = null;
    checked = false;
    photoMsg = "";
  }
</script>

<section class="calib" data-testid="calibrate-panel" aria-label="Calibrate for this fabric">
  <div class="calib-head">
    <h3>Calibrate for this fabric</h3>
    <button type="button" class="linklike" on:click={() => d("close")}>Close</button>
  </div>
  <p class="calib-intro">
    Sew one test card on a blank of the same goods, photograph it, and your
    <strong>{preset.label}</strong> preset is adjusted to how <em>your</em> machine,
    thread and stabilizer actually sew. Nothing changes until you accept the reading.
  </p>

  <h4>1 · Download the card</h4>
  {#if !serviceUp}
    <p class="calib-note">The digitizer service is not running, and the card comes from it. Start it and come back.</p>
  {/if}
  <div class="calib-formats" role="group" aria-label="Card format">
    {#each CARD_FORMATS as f (f)}
      <button
        type="button"
        data-testid={"card-" + f}
        disabled={!serviceUp || !!busyFormat}
        on:click={() => download(f)}
      >{busyFormat === f ? "Building…" : f.toUpperCase()}</button>
    {/each}
  </div>
  {#if cardMsg}<p class="calib-msg" data-testid="card-msg">{cardMsg}</p>{/if}
  <p class="calib-note">
    The first download builds the card and takes a few seconds. It fits a 5×7 hoop
    ({preset.assumedBacking === "tearaway" ? "tear-away" : preset.assumedBacking === "cap_buckram" ? "the cap's own buckram" : "cutaway"} backing{preset.needsTopper ? ", water-soluble topper" : ""}), and sews seven colours — any colours.
  </p>

  <h4>2 · Sew it, then photograph it</h4>
  <ul class="calib-steps">
    <li>Hoop a blank of this garment the way you always do, and sew the whole card.</li>
    <li>Lay it flat. Photograph it square-on in even daylight, no flash, with the whole card and its four corner marks in the frame.</li>
    <li>Tug the thread tails at the red bars. If a bar unravels, do not accept the reading — nothing in the photo can see that.</li>
  </ul>

  <h4>3 · Drop the photo</h4>
  <label class="calib-photo">
    <input
      bind:this={fileInput}
      type="file"
      accept="image/*"
      data-testid="calibrate-photo"
      disabled={!serviceUp || photoBusy}
      on:change={onPhoto}
    />
    {photoBusy ? "Reading the card…" : "Choose the photo"}
  </label>
  {#if photoMsg}<p class="calib-msg calib-err" role="alert">{photoMsg}</p>{/if}

  {#if reading}
    <div class="calib-reading" data-testid="calibrate-reading">
      {#if reading.overlay_jpeg_base64}
        <img class="calib-overlay" alt="Your card, registered, with each reading drawn on" src={"data:image/jpeg;base64," + reading.overlay_jpeg_base64} />
      {/if}
      <table class="calib-table">
        <thead><tr><th>On the card</th><th>What your cloth did</th></tr></thead>
        <tbody>
          {#each rows as r (r.kind + r.name)}
            <tr>
              <td>{r.name}</td>
              <td>
                {#if r.kind === "satin"}pulled in {fmtMm(r.pullIn)} across, {fmtMm(r.push)} along
                {:else if r.kind === "fill"}{fmtPct(r.showThrough)} cloth showing, pulled in {fmtMm(r.pullIn)}
                {:else}gap {fmtMm(r.gap)}{/if}
                {#if r.note}<span class="calib-note"> ({r.note})</span>{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
      <ul class="calib-notes">
        {#each reading.notes || [] as n}<li>{n}</li>{/each}
      </ul>
      {#if reading.profile && after}
        <p class="calib-draft" data-testid="calibrate-draft">
          <strong>Draft profile:</strong>
          pull comp {preset.pullCompMm} → <strong>{after.pullCompMm} mm</strong> ·
          rows ×{preset.densityAdjust} → <strong>×{after.densityAdjust}</strong> ·
          cut floats past {preset.trimAtMm} → <strong>{after.trimAtMm} mm</strong>
        </p>
        <label class="calib-check">
          <input type="checkbox" bind:checked={checked} data-testid="calibrate-check" />
          I tugged the red bars and nothing unravelled, and the columns did not float.
        </label>
      {:else}
        <p class="calib-draft">The reading changes nothing: your cloth sews like the preset already assumes.</p>
      {/if}
      <div class="calib-actions">
        <button type="button" class="primary" data-testid="calibrate-accept" disabled={!canAccept} on:click={accept}>
          Use this profile
        </button>
        <button type="button" on:click={discard}>Discard</button>
      </div>
    </div>
  {/if}
</section>
