<script lang="ts">
  import type { ReferenceVectorViewModel } from "$lib/adm/types";

  export let vector: ReferenceVectorViewModel;
  export let objectives: string[] = [];
</script>

<h3>{vector.id}</h3>

<div class="meta">
  <p>Assigned solutions: <strong>{vector.assignedSolutions}</strong></p>
  <p>Selected by ADM: <strong>{vector.selected ? "Yes" : "No"}</strong></p>
  <p>ROI candidate: <strong>{vector.roi ? "Yes" : "No"}</strong></p>
</div>

<div class="weights">
  {#each vector.weights as weight, i}
    <div class="row">
      <span>{objectives[i]}</span>
      <div class="bar">
        <div class="fill" style={`width: ${weight * 100}%`}></div>
      </div>
      <strong>{weight.toFixed(2)}</strong>
    </div>
  {/each}
</div>

<style>
  h3 {
    margin-top: 0;
  }

  .meta p {
    margin: 0.35rem 0;
    color: #475569;
  }

  .weights {
    margin-top: 1rem;
  }

  .row {
    display: grid;
    grid-template-columns: 32px 1fr 42px;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .bar {
    height: 8px;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
  }

  .fill {
    height: 100%;
    background: #7c3aed;
  }
</style>