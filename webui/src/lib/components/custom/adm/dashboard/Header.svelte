<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";
  import { getIteration } from "$lib/adm/adapters";
  import SummaryItem from "$lib/components/custom/adm/dashboard/SummaryItem.svelte";

  export let log: ADMLog;
  export let selectedIteration: number;

  export let onPrevious: () => void = () => {};
  export let onNext: () => void = () => {};

  let showSummary = false;

  $: iteration =
    getIteration(log, selectedIteration);
</script>

<div class="header">

  <div class="brand">
    <div>
      <h1>ADM Benchmark Explorer</h1>
      <p>
        Process-oriented analysis of interactive
        multiobjective optimization methods
      </p>
    </div>

    <button
      class="info-button"
      on:mouseenter={() => showSummary = true}
      on:mouseleave={() => showSummary = false}
      aria-label="Experiment information"
    >
      ?
    </button>

    {#if showSummary}
      <div class="summary-tooltip">
        <strong>Experiment summary</strong>

        <dl>
          <div>
            <dt>Experiment</dt>
            <dd>{log.experiment_id}</dd>
          </div>

          <div>
            <dt>Seed</dt>
            <dd>{log.adm_configuration.seed}</dd>
          </div>

          <div>
            <dt>Variables</dt>
            <dd>{log.problem.variables}</dd>
          </div>

          <div>
            <dt>Reference vectors</dt>
            <dd>{log.reference_vectors.length}</dd>
          </div>
        </dl>
      </div>
    {/if}
  </div>

  <div class="experiment-summary">

    <SummaryItem
      label="Problem"
      value={`${log.problem.name.toUpperCase()} (${log.problem.objectives} obj.)`}
    />

    <SummaryItem
      label="Methods"
      value={log.methods.join(", ")}
    />

    <SummaryItem
      label="Interactions"
      value={`${log.iterations.length} (${log.adm_configuration.learning_iterations} learn / ${log.adm_configuration.decision_iterations} decision)`}
    />

    <SummaryItem
      label="Generations / interaction"
      value={String(
        log.adm_configuration
          .generations_per_iteration
      )}
    />

    <SummaryItem
      label="Reference vectors"
      value={String(log.reference_vectors.length)}
    />

    <SummaryItem
      label="Indicator"
      value="Φ"
    />

  </div>

  <div class="iteration-control">

    <span>Interaction</span>

    <button
      on:click={onPrevious}
      disabled={selectedIteration === 1}
    >
      ‹
    </button>

    <strong>{selectedIteration}</strong>

    <button
      on:click={onNext}
      disabled={
        selectedIteration === log.iterations.length
      }
    >
      ›
    </button>

    <span
      class:learning={
        iteration.phase === "learning"
      }
      class:decision={
        iteration.phase === "decision"
      }
      class="phase"
    >
      {iteration.phase} phase
    </span>

  </div>

</div>

<style>
  .header {
    position: sticky;
    top: 0;
    z-index: 20;

    display: grid;
    grid-template-columns:
      minmax(230px, 0.85fr)
      minmax(600px, 2.2fr)
      auto;

    gap: 1rem;
    align-items: center;

    padding: 0.75rem 1.25rem;
    border-bottom: 1px solid #e9ebf2;

    background: rgba(255,255,255,0.97);
    backdrop-filter: blur(12px);
  }

  .brand {
    position: relative;
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
  }

  h1 {
    margin: 0;
    font-size: 1.1rem;
    color: #111827;
  }

  .brand p {
    margin: 0.18rem 0 0;
    color: #7f8799;
    font-size: 0.7rem;
  }

  .info-button {
    width: 20px;
    height: 20px;
    border: 1px solid #d8dce7;
    border-radius: 50%;
    background: white;
    color: #5d6678;
    cursor: pointer;
  }

  .summary-tooltip {
    position: absolute;
    top: calc(100% + 10px);
    left: 0;
    width: 280px;

    padding: 0.9rem;
    border-radius: 10px;
    border: 1px solid #e2e5ec;

    background: white;
    box-shadow: 0 12px 35px rgb(15 23 42 / 0.14);
  }

  .summary-tooltip dl {
    margin-bottom: 0;
  }

  .summary-tooltip dl div {
    display: flex;
    justify-content: space-between;
    margin-top: 0.45rem;
  }

  .summary-tooltip dt,
  .summary-tooltip dd {
    font-size: 0.7rem;
  }

  .summary-tooltip dd {
    margin: 0;
    font-weight: 600;
  }

  .experiment-summary {
    display: grid;
    grid-template-columns:
      repeat(6, minmax(100px, 1fr));
    border: 1px solid #eceef4;
    border-radius: 9px;
    background: #fff;
  }

  

  .iteration-control {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    white-space: nowrap;
  }

  .iteration-control > span:first-child {
    color: #687084;
    font-size: 0.67rem;
  }

  .iteration-control button,
  .iteration-control strong {
    min-width: 31px;
    height: 30px;
    display: grid;
    place-items: center;

    border: 1px solid #e1e4ec;
    border-radius: 6px;
    background: white;
  }

  .iteration-control button {
    cursor: pointer;
  }

  .iteration-control button:disabled {
    opacity: 0.35;
  }

  .iteration-control strong {
    font-size: 0.7rem;
  }

  .phase {
    margin-left: 0.35rem;
    padding: 0.42rem 0.58rem;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: capitalize;
  }

  .phase.learning {
    background: #f0ebff;
    color: #6242de;
  }

  .phase.decision {
    background: #fff1e9;
    color: #dc6a20;
  }

  @media(max-width: 1250px) {
    .header {
      grid-template-columns: 1fr auto;
    }

    .experiment-summary {
      grid-column: 1 / -1;
      grid-row: 2;
    }
  }
</style>