<script module>
  // Module-level cache (Slice 8 Task 3 / plan amendment B12): template id ->
  // rendered preview dataURL. A true module singleton (not per-instance state)
  // so navigating away from the Garment step and back doesn't regenerate the
  // same four previews — they're computed once for the page's lifetime.
  const templatePreviewCache = new Map();
</script>

<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { EMB } from "../lib/emb.js";
  import { renderRealistic } from "../lib/preview.js";
  import { ensureFont } from "../lib/fontLoader.js";
  import { TEMPLATES } from "../lib/templates.js";
  const d = createEventDispatcher();

  // Small mini stitch-preview canvas -- big enough to read the font/layout at
  // a glance, small enough to generate fast and stay a thumbnail in the card.
  const PREVIEW_W = 200;
  const PREVIEW_H = 72;

  function isTextTemplate(t) {
    return (t.patch.elements[0] || {}).type === "text";
  }

  // Renders template `t`'s first element as real satin stitches onto a small
  // offscreen canvas via the SAME engine path used everywhere else (
  // buildLetteringDesign -> renderRealistic), design-fit (no `hoop` opt), so
  // the card shows what the template will actually stitch -- not a mockup.
  // densityMm: 1.2 (plan amendment B12 -- buildLetteringDesign's option is
  // `densityMm`, there is no `spacingMm` at this layer) keeps generation fast
  // since these run off the idle queue, not on a user gesture.
  // Awaits the template's font (lib/fontLoader.js -- lazy-loaded, Slice 10A)
  // before building the preview design; buildLetteringDesign no longer reads
  // EMB.SATIN_FONTS[el.fontKey] directly since that entry may not exist yet
  // the first time a given template's font is needed.
  async function generatePreview(t) {
    if (templatePreviewCache.has(t.id)) return templatePreviewCache.get(t.id);
    let url = "";
    try {
      const el = t.patch.elements[0];
      const font = await ensureFont(el.fontKey);
      const c = document.createElement("canvas");
      c.width = PREVIEW_W;
      c.height = PREVIEW_H;
      const design = EMB.buildLetteringDesign(font, el.text, {
        garment: EMB.getGarment(t.patch.garmentId),
        pxPerMm: 8,
        densityMm: 1.2,
        underlay: false,
      });
      renderRealistic(c, design, { pad: 8, fabric: "#ffffff" });
      url = c.toDataURL();
    } catch (e) {
      url = "";
    }
    templatePreviewCache.set(t.id, url);
    return url;
  }

  // requestIdleCallback (with a setTimeout fallback for Safari, which never
  // shipped it) so four stitch-generation passes never compete with first
  // paint -- the plan explicitly calls this out: template preview generation
  // must not block first paint.
  function onIdle(fn) {
    if (typeof requestIdleCallback === "function") requestIdleCallback(fn);
    else setTimeout(fn, 0);
  }

  let previews = {}; // template id -> dataURL, reactive mirror of the cache above

  onMount(() => {
    for (const t of TEMPLATES) {
      if (!isTextTemplate(t)) continue;
      if (templatePreviewCache.has(t.id)) {
        previews = { ...previews, [t.id]: templatePreviewCache.get(t.id) };
        continue;
      }
      onIdle(async () => {
        const url = await generatePreview(t);
        previews = { ...previews, [t.id]: url };
      });
    }
  });
</script>

<h3>Quick start</h3>
<div class="templates">
  {#each TEMPLATES as t}
    <button class="tcard" on:click={() => d("pick", t)}>
      <span class="tcard-preview">
        {#if isTextTemplate(t)}
          {#if previews[t.id]}
            <img src={previews[t.id]} alt="" width={PREVIEW_W} height={PREVIEW_H} />
          {/if}
        {:else}
          <!-- Logo-patch template: no text to stitch-preview -- an upload
               glyph stands in for "bring your own artwork next". -->
          <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M24 30 L24 8 M15 17 L24 8 L33 17" />
            <path class="acc" d="M8 32 L8 38 Q8 40 10 40 L38 40 Q40 40 40 38 L40 32" />
          </svg>
        {/if}
      </span>
      <span class="tcard-label">{t.label}</span>
      <span class="tcard-hint">{t.hint}</span>
    </button>
  {/each}
</div>
