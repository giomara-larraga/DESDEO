<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";

  export let log: ADMLog;
  export let selectedIteration: number;
  export let onSelect: (iteration: number) => void = () => {};
</script>

<section class="timeline-card">
  <div class="title-row">
    <h3>Iteration Timeline</h3>
    <p>Learning and decision phases</p>
  </div>

  <div class="timeline">
    {#each log.iterations as it}
      <button
        class:active={it.iteration === selectedIteration}
        class:learning={it.phase === "learning"}
        class:decision={it.phase === "decision"}
        on:click={() => onSelect(it.iteration)}
      >
        <span>{it.iteration}</span>
        <small>{it.phase}</small>
      </button>
    {/each}
  </div>
</section>

<style>
  .timeline-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 1rem;
    padding: 1rem;
  }

  .title-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  h3 {
    margin: 0;
  }

  p {
    margin: 0;
    color: #64748b;
    font-size: 0.85rem;
  }

  .timeline {
    display: flex;
    justify-content: space-between;
    position: relative;
    margin-top: 1.5rem;
  }

  .timeline::before {
    content: "";
    position: absolute;
    top: 18px;
    left: 24px;
    right: 24px;
    height: 2px;
    background: #cbd5e1;
  }

  button {
    position: relative;
    z-index: 1;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: center;
  }

  span {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 999px;
    background: white;
    border: 2px solid #cbd5e1;
    font-weight: 700;
  }

  small {
    display: block;
    margin-top: 0.4rem;
    font-size: 0.7rem;
    color: #64748b;
  }

  .learning small {
    color: #2563eb;
  }

  .decision small {
    color: #ea580c;
  }

  .active span {
    background: #7c3aed;
    color: white;
    border-color: #7c3aed;
    box-shadow: 0 0 0 6px rgba(124, 58, 237, 0.14);
  }
</style>