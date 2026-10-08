<script>
  // The digitize pinwheel: four vanes that turn and throb over the embroidery
  // field while a digitize is in flight, fading out as the stitches land and
  // the outline pulse takes over. Kent, 2026-10-08: "My digitizing throbbing
  // pulsating pinwheel disappeared, bring that back."
  //
  // Pure SVG; the motion is CSS in theme.css's Motion section (`.pinwheel`).
  // With reduced motion it throbs but does not turn.
  import { fade } from "svelte/transition";
  export let label = "Digitizing your art";
</script>

<div class="pinwheel" role="status" aria-label={label} data-testid="digitize-pinwheel" out:fade={{ duration: 350 }}>
  <svg class="pinwheel-svg" viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
    <g class="pinwheel-vanes">
      {#each [0, 90, 180, 270] as deg, i}
        <path
          class="pinwheel-vane"
          class:alt={i % 2 === 1}
          transform="rotate({deg})"
          d="M0 0 L0 -44 Q22 -40 30 -18 Z"
        />
      {/each}
    </g>
    <circle class="pinwheel-hub" r="5" />
  </svg>
</div>
