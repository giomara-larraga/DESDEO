<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";
  import { getIteration, getObjectives } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;

  $: iteration = getIteration(log, selectedIteration);
  $: objectives = getObjectives(log);
</script>

<div class="parallel">
  {#each iteration.composite_front as solution}
    <div class="solution">
      <span>{solution.method}</span>

      {#each solution.objectives as value, i}
        <div class="objective">
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
  .parallel {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-height: 360px;
    overflow-y: auto;
  }

  .solution {
    display: grid;
    grid-template-columns: 90px repeat(5, 1fr);
    gap: 0.5rem;
    align-items: center;
  }

  span {
    font-size: 0.75rem;
    font-weight: 600;
  }

  small {
    color: #64748b;
    font-size: 0.7rem;
  }

  .bar {
    height: 7px;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
  }

  .fill {
    height: 100%;
    background: #0ea5e9;
  }
</style>