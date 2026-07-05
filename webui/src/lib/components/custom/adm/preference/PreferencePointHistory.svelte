<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";
  import { getIteration } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;

  $: current = getIteration(log, selectedIteration);
</script>

<section>
  <h3>Current Preference Point</h3>

  <div class="values">
    {#each current.preference_information.reference_point as value, i}
      <div>
        <span>f{i + 1}</span>
        <strong>{value.toFixed(3)}</strong>
      </div>
    {/each}
  </div>

  <p>{current.preference_information.description}</p>
</section>

<style>
  .values {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.5rem;
  }

  .values div {
    background: #f8fafc;
    border-radius: 0.75rem;
    padding: 0.75rem;
  }

  span {
    display: block;
    color: #64748b;
    font-size: 0.75rem;
  }

  strong {
    font-size: 1.1rem;
  }

  p {
    color: #475569;
  }
</style>