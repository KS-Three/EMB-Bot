<script>
  // The "My designs" drawer's filter controls: name text, and three upper
  // bounds a design is measured against (lib/libraryFacts.js). Presentational
  // like the drawer itself — it owns the four inputs and hands out one
  // `criteria` object in the shape filterProjects() takes; the drawer does
  // the filtering. Engine-free: the hoop presets arrive as a prop.
  //
  // Every bound is "up to", including colors: the question a single-needle
  // owner is asking is how many re-threads at most, and "exactly two" is
  // still answered by the row's own facts line.
  export let hoops = [];
  export let criteria = {};

  const STITCH_STEPS = [2000, 4000, 6000, 10000, 15000, 25000];
  const COLOR_STEPS = [1, 2, 3, 4, 6];

  let text = "";
  let maxStitches = "";
  let maxColors = "";
  let hoopId = "";

  $: criteria = {
    text,
    maxStitches: maxStitches === "" ? null : Number(maxStitches),
    maxColors: maxColors === "" ? null : Number(maxColors),
    hoop: hoops.find((h) => h.id === hoopId) || null,
  };
  $: active = text.trim() !== "" || maxStitches !== "" || maxColors !== "" || hoopId !== "";

  function clear() {
    text = "";
    maxStitches = "";
    maxColors = "";
    hoopId = "";
  }
</script>

<div class="dfilter">
  <label class="dfilter-field dfilter-text">
    <span>Find a design</span>
    <input type="text" bind:value={text} placeholder="Search by name…" autocomplete="off" />
  </label>
  <label class="dfilter-field">
    <span>Stitches</span>
    <select bind:value={maxStitches}>
      <option value="">Any</option>
      {#each STITCH_STEPS as n}
        <option value={String(n)}>Up to {n.toLocaleString()}</option>
      {/each}
    </select>
  </label>
  <label class="dfilter-field">
    <span>Colors</span>
    <select bind:value={maxColors}>
      <option value="">Any</option>
      {#each COLOR_STEPS as n}
        <option value={String(n)}>Up to {n}</option>
      {/each}
    </select>
  </label>
  <label class="dfilter-field">
    <span>Fits hoop</span>
    <select bind:value={hoopId}>
      <option value="">Any</option>
      {#each hoops as h}
        <option value={h.id}>{h.label}</option>
      {/each}
    </select>
  </label>
  {#if active}
    <button type="button" class="dfilter-clear" on:click={clear}>Clear filters</button>
  {/if}
</div>
