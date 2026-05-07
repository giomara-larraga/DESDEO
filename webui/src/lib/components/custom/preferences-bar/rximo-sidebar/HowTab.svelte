<script lang="ts">
  import TradeoffGraph from './TradeoffGraph.svelte';

  export let shapValues: any = {};
  export let objectiveNames: string[] = [];
  export let focusObjective: string | null = null;
  export let currentPreference: any = null;

  function matrixFromShap(values: any): number[][] {
    if (Array.isArray(values)) return values;
    if (Array.isArray(values?.values)) return values.values;
    if (Array.isArray(values?.shap_values)) return values.shap_values;
    if (Array.isArray(values?.matrix)) return values.matrix;
    return [];
  }

  $: matrix = matrixFromShap(shapValues);
  $: targetIndex = Math.max(0, objectiveNames.indexOf(focusObjective ?? ''));
  $: drivers = objectiveNames.map((name, i) => ({
    name,
    value: Number(matrix?.[i]?.[targetIndex] ?? 0),
    own: i === targetIndex
  })).sort((a, b) => a.value - b.value);

  $: rival = drivers.find((d) => d.value < 0 && !d.own) ?? drivers.find((d) => !d.own);
  $: bestHelper = [...drivers].reverse().find((d) => d.value > 0);
  $: estimatedGain = rival ? Math.abs(rival.value) * 0.4 : 0;
</script>

<section class="suggestion">
  <div class="icon">💡</div>
  <div>
    <h3>Suggested next step</h3>

    {#if rival}
      <p>
        To improve <strong>{focusObjective}</strong>, relax the aspiration for
        <strong>{rival.name}</strong>.
      </p>
      <p class="muted">
        Estimated local gain: about <strong>+{estimatedGain.toFixed(2)}</strong>
        in {focusObjective} for a small relaxation.
      </p>
    {:else}
      <p>No rival objective was detected.</p>
    {/if}
  </div>
</section>

<section class="card">
  <h3>Trade-off overview</h3>
  <TradeoffGraph {shapValues} {objectiveNames} {focusObjective} />
</section>

<section class="card compact">
  <h3>Interpretation</h3>

  {#if rival}
    <p>
      <strong>{rival.name}</strong> is the objective most likely to be sacrificed if you
      want to improve <strong>{focusObjective}</strong>.
    </p>
  {/if}

  {#if bestHelper}
    <p>
      <strong>{bestHelper.name}</strong> currently helps <strong>{focusObjective}</strong>.
    </p>
  {/if}
</section>

<style>
  .suggestion,
  .card {
    background: white;
    border: 1px solid #d8e0eb;
    border-radius: 0.65rem;
    padding: 0.8rem;
  }

  .suggestion {
    display: grid;
    grid-template-columns: 2rem 1fr;
    gap: 0.65rem;
    border-color: #f4c96b;
    background: #fffaf0;
  }

  .icon {
    font-size: 1.35rem;
    line-height: 1;
  }

  h3 {
    margin: 0 0 0.45rem;
    font-size: 0.86rem;
  }

  p {
    margin: 0;
    line-height: 1.4;
  }

  p + p {
    margin-top: 0.35rem;
  }

  .muted {
    color: #64748b;
    font-size: 0.78rem;
  }

  .card {
    margin-top: 0.8rem;
  }

  .compact {
    font-size: 0.82rem;
  }
</style>