<script>
  import { defaultProject, update, updateElement, selectElement } from "./lib/project.js";
  import { applyTemplate } from "./lib/templates.js";
  import { canAdvance, nextStep, prevStep } from "./lib/flow.js";
  import { saveLocal, loadLocal } from "./lib/save.js";
  import GarmentStep from "./ui/GarmentStep.svelte";
  import ContentStep from "./ui/ContentStep.svelte";
  import DownloadStep from "./ui/DownloadStep.svelte";
  import StepNav from "./ui/StepNav.svelte";
  import EmbroideryField from "./ui/EmbroideryField.svelte";
  import SizePanel from "./ui/SizePanel.svelte";
  import "./ui/theme.css";

  // The image itself never survives a reload (see `runtime` below), so a
  // persisted `_hasImage` flag on any element would let the flow gate pass
  // with nothing actually loaded — strip it from every element at boot.
  function resetHasImage(p) {
    if (!p.elements.some((el) => el._hasImage)) return p;
    return { ...p, elements: p.elements.map((el) => (el._hasImage ? { ...el, _hasImage: false } : el)) };
  }

  let project = resetHasImage(loadLocal() || defaultProject());
  let step = "garment";
  // Runtime image state, owned here (not by ImagePanel) so it survives
  // ContentStep/ImagePanel being destroyed and recreated whenever the user
  // navigates steps or toggles Text/Image mode (both are {#if} blocks).
  // Keyed by element id (Task 4/Slice 5: was a single workImage/flat pair,
  // now a map so each image element in a multi-element project keeps its
  // own working image) -- see generate.js's generateAll(project, runtime).
  // workImages[id] is the prepped working source ({ rgba, w, h }, alpha-cut,
  // at WORK_MAX_PX) that ImagePanel re-flattens from; flats[id] is the
  // flattened palette derived from it. Neither is persisted via saveLocal —
  // only project settings are.
  let runtime = { flats: {}, workImages: {} };
  // Dims of the SELECTED element's last generated design ({ widthMM, heightMM })
  // or null on failure/no-content -- fed to SizePanel so its W/H display
  // (and the below-5mm warning) always reflects the real current design,
  // including while the user drags the field's resize handles.
  let designDims = null;

  // The currently-selected element (SizePanel/ContentStep/the "create" step
  // summary all key off this one, not project.elements[0], so they stay in
  // sync with whatever the user clicked on the field).
  $: selectedElement = project.elements.find((el) => el.id === project.selectedId) || project.elements[0];

  function apply(patch) {
    project = update(project, patch);
    saveLocal(project);
  }

  // Patches a single element (by id) — used by EmbroideryField's drag/resize/
  // reclamp "elupdate" events and by ContentStep's adapter for the
  // still-v1-shaped TextStep/ImagePanel/SizePanel controls (see ContentStep.svelte).
  function elUpdate(id, patch) {
    project = updateElement(project, id, patch);
    saveLocal(project);
  }

  function pickTemplate(template) {
    project = applyTemplate(project, template);
    saveLocal(project);
    step = "content";
  }

  function onSelect(id) {
    project = selectElement(project, id);
    saveLocal(project);
  }

  function onImage(elementId, workImage) {
    runtime = { ...runtime, workImages: { ...runtime.workImages, [elementId]: workImage } };
  }

  function onFlat(elementId, flat) {
    runtime = { ...runtime, flats: { ...runtime.flats, [elementId]: flat } };
    elUpdate(elementId, { _hasImage: !!flat });
  }

  function onDims(detail) {
    designDims = detail;
  }

  function go(dir) {
    const s = dir > 0 ? nextStep(step) : prevStep(step);
    if (s) step = s;
  }

  function readable(id) {
    return (id || "")
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }
</script>

<header class="topbar"><span class="logo">EMB&nbsp;Bot Studio</span></header>

<div class="studio">
  <aside class="panel">
    <div class="panel-body">
      {#if step === "garment"}
        <GarmentStep {project} on:update={(e) => apply(e.detail)} on:template={(e) => pickTemplate(e.detail)} />
      {:else if step === "content"}
        <ContentStep
          {project}
          workImage={runtime.workImages[project.selectedId]}
          flat={runtime.flats[project.selectedId]}
          {designDims}
          on:update={(e) => apply(e.detail)}
          on:elupdate={(e) => elUpdate(e.detail.id, e.detail.patch)}
          on:image={(e) => onImage(project.selectedId, e.detail)}
          on:flat={(e) => onFlat(project.selectedId, e.detail)}
        />
      {:else if step === "create"}
        <div class="createstep">
          <h2>Ready to stitch</h2>
          <p>Looks good? The field on the right is your stitch-out.</p>
          <dl class="summary">
            <div><dt>Garment</dt><dd>{readable(project.garmentId)}</dd></div>
            {#if selectedElement.type === "image"}
              <div><dt>Content</dt><dd>Logo / image</dd></div>
              <div><dt>Colors</dt><dd>{selectedElement.nColors}{selectedElement.removeBg ? " · background removed" : ""}</dd></div>
            {:else}
              <div><dt>Content</dt><dd>Text — "{selectedElement.text}"</dd></div>
              <div><dt>Font</dt><dd>{readable(selectedElement.fontKey)}</dd></div>
            {/if}
          </dl>
          <p class="hint">Not quite right? Go back to adjust the garment or content — the field updates live.</p>
          <SizePanel project={{ ...project, ...selectedElement }} {designDims} on:update={(e) => elUpdate(selectedElement.id, e.detail)} />
        </div>
      {:else}
        <DownloadStep {project} {runtime} />
      {/if}
    </div>
    <StepNav {step} canNext={canAdvance(step, project)} on:back={() => go(-1)} on:next={() => go(1)} />
  </aside>

  <section class="field">
    <EmbroideryField
      {project}
      {runtime}
      on:elupdate={(e) => elUpdate(e.detail.id, e.detail.patch)}
      on:select={(e) => onSelect(e.detail)}
      on:dims={(e) => onDims(e.detail)}
    />
  </section>
</div>
