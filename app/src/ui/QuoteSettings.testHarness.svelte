<script>
  import QuoteSettings from "./QuoteSettings.svelte";
  export let quote = {};
  export let onChange = () => {};
</script>

<QuoteSettings {quote} on:change={(e) => onChange(e.detail)} />
