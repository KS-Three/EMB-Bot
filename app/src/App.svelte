<script>
  import { defaultProject, update } from "./lib/project.js";
  import { canAdvance, nextStep, prevStep } from "./lib/flow.js";
  import { saveLocal, loadLocal } from "./lib/save.js";
  import GarmentStep from "./ui/GarmentStep.svelte";
  import ContentStep from "./ui/ContentStep.svelte";
  import DownloadStep from "./ui/DownloadStep.svelte";
  import StepNav from "./ui/StepNav.svelte";
  import EmbroideryField from "./ui/EmbroideryField.svelte";
  import "./ui/theme.css";

  let project = loadLocal() || defaultProject();
  let step = "garment";
  // Runtime image state, owned here (not by ImagePanel) so it survives
  // ContentStep/ImagePanel being destroyed and recreated whenever the user
  // navigates steps or toggles Text/Image mode (both are {#if} blocks).
  // workImage is the prepped working source ({ rgba, w, h }, alpha-cut, at
  // WORK_MAX_PX) that ImagePanel re-flattens from; flat is the flattened
  // palette derived from it. Neither is persisted via saveLocal — only
  // project settings are.
  let workImage = null;
  let flat = null;

  function apply(patch) {
    project = update(project, patch);
    saveLocal(project);
  }

  function onImage(detail) {
    workImage = detail;
  }

  function onFlat(detail) {
    flat = detail;
    apply({ _hasImage: !!detail });
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
        <GarmentStep {project} on:update={(e) => apply(e.detail)} />
      {:else if step === "content"}
        <ContentStep
          {project}
          {workImage}
          {flat}
          on:update={(e) => apply(e.detail)}
          on:image={(e) => onImage(e.detail)}
          on:flat={(e) => onFlat(e.detail)}
        />
      {:else if step === "create"}
        <div class="createstep">
          <h2>Ready to stitch</h2>
          <p>Looks good? The field on the right is your stitch-out.</p>
          <dl class="summary">
            <div><dt>Garment</dt><dd>{readable(project.garmentId)}</dd></div>
            {#if project.mode === "image"}
              <div><dt>Content</dt><dd>Logo / image</dd></div>
              <div><dt>Colors</dt><dd>{project.nColors}{project.removeBg ? " · background removed" : ""}</dd></div>
            {:else}
              <div><dt>Content</dt><dd>Text — "{project.text}"</dd></div>
              <div><dt>Font</dt><dd>{readable(project.fontKey)}</dd></div>
            {/if}
          </dl>
          <p class="hint">Not quite right? Go back to adjust the garment or content — the field updates live.</p>
        </div>
      {:else}
        <DownloadStep {project} {flat} />
      {/if}
    </div>
    <StepNav {step} canNext={canAdvance(step, project)} on:back={() => go(-1)} on:next={() => go(1)} />
  </aside>

  <section class="field">
    <EmbroideryField {project} {flat} />
  </section>
</div>
