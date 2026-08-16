<script lang="ts">
  import type { ReferenceVectorViewModel } from "$lib/adm/types";
  import ReferenceVectorProjection from "./ReferenceVectorProjection.svelte";
  import ReferenceVectorHeatmap from "./ReferenceVectorHeatmap.svelte";
  import ReferenceVectorDetails from "./ReferenceVectorDetails.svelte";
  import ReferenceVectorLegend from "./ReferenceVectorLegend.svelte";

  export let vectors: ReferenceVectorViewModel[] = [];
  export let objectives: string[] = [];

  let selectedId: string | null = null;

  $: selectedVector =
    vectors.find((v) => v.id === selectedId) ??
    vectors.find((v) => v.selected) ??
    vectors[0];

  function selectVector(id: string) {
    selectedId = id;
  }
</script>

<div class="grid">
  <section class="panel">
    <ReferenceVectorLegend />
    <ReferenceVectorProjection
      {vectors}
      selectedId={selectedVector?.id}
      onSelect={selectVector}
    />
  </section>

  <section class="panel">
    <ReferenceVectorHeatmap
      {vectors}
      {objectives}
      selectedId={selectedVector?.id}
      onSelect={selectVector}
    />
  </section>

  <section class="panel">
    {#if selectedVector}
      <ReferenceVectorDetails
        vector={selectedVector}
        {objectives}
      />
    {/if}
  </section>
</div>

<style>
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr 300px;
    gap: 1rem;
  }

  .panel {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 1rem;
    padding: 1rem;
  }

  @media (max-width: 1200px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
</style>