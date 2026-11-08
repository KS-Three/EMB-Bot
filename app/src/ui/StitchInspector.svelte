<script>
  // The stitch inspector's tooltip (2026-11-08): what the stitch under the
  // pointer is, while the field's Inspect toggle is on. The numbers come from
  // lib/stitchInspect.js strandInfo, which reads them the way the simulator
  // does, so "Stitch N of M" here is the counter SimBar shows once that
  // stitch is drawn, and "Thread K of B" is its thread readout.
  //
  // A DOM element, never a canvas (e2e locators assume `.hoop canvas` is the
  // one canvas), and `position: fixed` at the pointer, so it takes no layout
  // space in `.fieldwrap` and cannot move or resize the field. It ignores the
  // pointer (pointer-events: none): a tooltip that caught the pointer would
  // fire the canvas's pointerleave and close itself.
  export let info = null;  // stitchInspect.js strandInfo(), or null
  export let x = 0;        // pointer, client px
  export let y = 0;

  const GAP = 14;
  // Flipped to the pointer's other side near the window's right or bottom
  // edge, so it never runs off screen. Measured against the window, not the
  // field: the tooltip is fixed, so the window is what clips it.
  const FLIP_X = 240;
  const FLIP_Y = 110;

  $: vw = typeof window !== "undefined" ? window.innerWidth : 1e9;
  $: vh = typeof window !== "undefined" ? window.innerHeight : 1e9;
  $: flipX = x > vw - FLIP_X;
  $: flipY = y > vh - FLIP_Y;
  $: style = `left: ${x + (flipX ? -GAP : GAP)}px; top: ${y + (flipY ? -GAP : GAP)}px;`
    + ` transform: translate(${flipX ? "-100%" : "0"}, ${flipY ? "-100%" : "0"});`;
  $: rgb = info && info.rgb ? `rgb(${info.rgb[0]},${info.rgb[1]},${info.rgb[2]})` : "transparent";
  $: mm = info ? `${info.lengthMm.toFixed(1)} mm` : "";
</script>

{#if info}
  <div class="stitchinspect" role="tooltip" {style} data-testid="stitch-inspect" data-strand={info.strand}>
    <span class="si-n">Stitch {info.ordinal.toLocaleString()} of {info.total.toLocaleString()}</span>
    <span class="si-kind">{info.label} · {mm}</span>
    <span class="si-thread">
      <i class="si-swatch" style="background: {rgb}" aria-hidden="true"></i>
      <span>Thread {info.block} of {info.blocks}</span>
      {#if info.thread}<span class="si-name">{info.thread}</span>{/if}
    </span>
  </div>
{/if}

<style>
  .stitchinspect {
    position: fixed;
    z-index: 30;
    pointer-events: none;
    display: flex;
    flex-direction: column;
    gap: 2px;
    max-width: 260px;
    padding: var(--space-1, 4px) var(--space-2, 8px);
    background: var(--surface, #fff);
    color: var(--ink, #111);
    border: 1px solid var(--border, #ccc);
    border-radius: var(--radius-s, 4px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
    font-size: var(--fs-xs, 12px);
    line-height: 1.35;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .si-n { font-weight: var(--fw-medium, 500); }
  .si-kind { color: var(--muted, #555); }
  .si-thread { display: flex; align-items: center; gap: 6px; min-width: 0; }
  .si-swatch {
    flex: none;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    border: 1px solid var(--border, #ccc);
  }
  .si-name { overflow: hidden; text-overflow: ellipsis; color: var(--muted, #555); }
</style>
