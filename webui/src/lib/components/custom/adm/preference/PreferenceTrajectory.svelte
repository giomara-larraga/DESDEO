<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";
  import { getObjectives } from "$lib/adm/adapters";

  export let log: ADMLog;

  $: objectives = getObjectives(log);
</script>

<div class="trajectory">
  {#each log.iterations as it}
    <div class="row">
      <span class="label">It. {it.iteration}</span>

      {#each it.preference_information.reference_point as value, i}
        <div class="bar-wrap">
          <small>{objectives[i]}</small>
          <div class="bar">
            <div class="fill" style={`width: ${value * 100}%`}></div>
          </div>
        </div>
      {/each}
    </div>
  {/each}
</div>

<style>
  .trajectory {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .row {
    display: grid;
    grid-template-columns: 56px repeat(5, 1fr);
    gap: 0.5rem;
    align-items: center;
  }

  .label {
    font-size: 0.8rem;
    font-weight: 600;
  }

  small {
    color: #64748b;
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