<script lang="ts">
  import type { ADMLog, PopulationSolution } from "$lib/adm/types";
  import { getIteration, getObjectives, getReferenceVectorViewData } from "$lib/adm/adapters";
  import PhiEvolution from "../phi/PhiEvolution.svelte";
  import GenerationPhi from "../phi/GenerationPhi.svelte";
  import PreferenceTrajectory from "../preference/PreferenceTrajectory.svelte";
  import ReferenceVectorExplorer from "../reference-vectors/ReferenceVectorExplorer.svelte";
  import ParallelCoordinates from "../solutions/ParallelCoordinates.svelte";
  import ScatterPlot from "../solutions/ScatterPlot.svelte";
  import SolutionTable from "../solutions/SolutionTable.svelte";

  export let log: ADMLog;
  export let populationHistory: PopulationSolution[] = [];

  // One source of truth for coordinated selections.
  let selectedIteration = 1;
  let selectedGeneration: number | null = null;
  let selectedVector: string | null = null;
  let visibleMethods: string[] = [...log.methods];
  let showDetails = false;
  let showInteractionOverview = false;

  $: iteration = getIteration(log, selectedIteration);
  $: objectives = getObjectives(log);
  $: referenceVectors = getReferenceVectorViewData(log, selectedIteration);
  $: activeReferencePoint = iteration.preference_information.active_reference_point ??
    (selectedIteration === 1 ? log.initial_reference_point :
      getIteration(log, selectedIteration - 1).preference_information.next_reference_point ??
      getIteration(log, selectedIteration - 1).preference_information.reference_point);
  $: nextReferencePoint = iteration.preference_information.next_reference_point ??
    iteration.preference_information.reference_point;
  $: availableGenerations = Array.from(new Set(populationHistory
    .filter(row => row.adm_iteration === selectedIteration)
    .map(row => row.generation_in_iteration))).sort((a,b)=>a-b);
  $: currentGeneration = selectedGeneration ?? availableGenerations[availableGenerations.length - 1] ?? null;
  $: populationCount = populationHistory.filter(row =>
    row.adm_iteration === selectedIteration &&
    row.generation_in_iteration === currentGeneration &&
    visibleMethods.includes(row.method)).length;
  $: occupiedVectors = iteration.reference_vector_assignments.filter(item => item.assigned_count > 0).length;

  function selectIteration(next: number) {
    selectedIteration = Math.max(1, Math.min(log.iterations.length, next));
    selectedGeneration = null;
    selectedVector = null;
  }
  function toggleMethod(method: string) {
    if (visibleMethods.includes(method)) {
      if (visibleMethods.length > 1) visibleMethods = visibleMethods.filter(m => m !== method);
    } else {
      visibleMethods = [...visibleMethods, method];
    }
  }
  function selectGeneration(value: number) {
    if (availableGenerations.includes(value)) selectedGeneration = value;
  }
  function reset() {
    selectedGeneration = null;
    selectedVector = null;
    visibleMethods = [...log.methods];
  }
</script>

<svelte:head><title>ADM · Coordinated Optimization Analysis</title></svelte:head>
<div class="workspace">
  <header class="topbar">
    <div>
      <div class="eyebrow">DESDEO · VISUAL ANALYTICS</div>
      <h1>Interactive optimization analysis</h1>
      <p>{log.problem.name} · {log.problem.objectives} objectives · {log.adm_configuration.learning_iterations} learning / {log.adm_configuration.decision_iterations} decision interactions</p>
    </div>
    <div class="summary-metrics" aria-label="Selected context">
      <span>{iteration.phase} phase</span>
      <span>{populationCount} selected solutions</span>
      <span>{occupiedVectors}/{log.reference_vectors.length} occupied vectors</span>
    </div>
  </header>

  <nav class="selection-bar" aria-label="Coordinated analysis controls">
    <label class="control">Interaction
      <select value={selectedIteration} on:change={e => selectIteration(Number(e.currentTarget.value))}>
        {#each log.iterations as entry}
          <option value={entry.iteration}>{entry.iteration} · {entry.phase}</option>
        {/each}
      </select>
    </label>
    <div class="control generation-control">
      <label for="generation-slider">Generation <strong>{currentGeneration ?? '—'}</strong></label>
      <input id="generation-slider" type="range"
        min={availableGenerations[0] ?? 2}
        max={availableGenerations[availableGenerations.length-1] ?? 2}
        step="1" value={currentGeneration ?? 2}
        disabled={availableGenerations.length === 0}
        on:input={e => selectGeneration(Number(e.currentTarget.value))} />
    </div>
    <div class="control method-control">
      <span>Methods</span>
      <div class="method-buttons">
        {#each log.methods as method}
          <button type="button" class:chosen={visibleMethods.includes(method)}
            aria-pressed={visibleMethods.includes(method)} on:click={() => toggleMethod(method)}>{method}</button>
        {/each}
      </div>
    </div>
    <label class="control vector-control">Reference vector
      <select value={selectedVector ?? ''} on:change={e => selectedVector = e.currentTarget.value || null}>
        <option value="">All vectors</option>
        {#each log.reference_vectors as vector}
          <option value={vector.vector_id}>{vector.vector_id}</option>
        {/each}
      </select>
    </label>
    <button type="button" class="reset-button" on:click={reset}>Reset filters</button>
  </nav>

  <main class="analysis-grid">
    <section class="pane populations">
      <div class="pane-head">
        <div><div class="pane-kicker">01 · ALGORITHM RESPONSE</div><h2>Population evolution</h2>
          <p>Compare selected populations at the same generation and active preference.</p></div>
      </div>
      <div class="rp-strip">
        <div><span>Active preference</span><strong>{activeReferencePoint.map(v => v.toFixed(3)).join(' · ')}</strong></div>
        <span class="rp-arrow">→</span>
        <div><span>ADM next preference</span><strong>{nextReferencePoint.map(v => v.toFixed(3)).join(' · ')}</strong></div>
      </div>
      <ParallelCoordinates {log} {populationHistory} {selectedIteration}
        bind:selectedGeneration bind:visibleMethods {selectedVector} width={850} height={380} />
    </section>

    <section class="pane preferences">
      <div class="pane-head"><div><div class="pane-kicker">02 · PREFERENCE DYNAMICS</div>
        <h2>Where ADM redirects the search</h2>
        <p>Select a preference transition to inspect its interaction.</p></div></div>
      <PreferenceTrajectory {log} {selectedIteration} onSelect={selectIteration} width={580} height={335} />
      <div class="inline-context">Selected ADM direction <button type="button"
        on:click={() => selectedVector = iteration.preference_information.selected_reference_vector}>
        {iteration.preference_information.selected_reference_vector}</button>
        <span>· {iteration.preference_information.selection_rule.replaceAll('_',' ')}</span></div>
    </section>

    <section class="pane temporal">
      <div class="pane-head"><div><div class="pane-kicker">03 · TEMPORAL PERFORMANCE</div>
        <h2>What changes within the interaction?</h2>
        <p>Click a PHI sample to update the population view above.</p></div>
        <button class="subtle-button" type="button" on:click={() => showInteractionOverview = !showInteractionOverview}>
          {showInteractionOverview ? 'Hide' : 'Show'} across-interaction overview
        </button>
      </div>
      {#if showInteractionOverview}
        <div class="secondary-chart"><PhiEvolution {log} {selectedIteration} selectedMethods={visibleMethods} onSelect={selectIteration} width={1000} height={195} /></div>
      {/if}
      <GenerationPhi {log} {selectedIteration} selectedMethods={visibleMethods} bind:selectedGeneration width={1000} height={315} />
    </section>

    <section class="pane vectors">
      <div class="pane-head"><div><div class="pane-kicker">04 · ADM DIAGNOSTICS</div>
        <h2>Which regions are represented?</h2>
        <p>Vector occupancy and the accumulated ADM front are end-of-interaction diagnostics.</p></div>
      </div>
      <div class="diagnostic-grid">
        <div class="vector-panel"><ReferenceVectorExplorer {log} vectors={referenceVectors} {objectives}
          bind:selectedId={selectedVector} onSelectIteration={selectIteration}/></div>
        <div class="front-panel"><h3>Composite-front projection</h3>
          <ScatterPlot {log} {selectedIteration} {selectedVector} onSelectVector={id => selectedVector = id}/></div>
      </div>
      <button class="subtle-button details-toggle" type="button" on:click={() => showDetails = !showDetails}>
        {showDetails ? 'Hide' : 'Inspect'} composite-front solution details
      </button>
      {#if showDetails}<div class="details-panel"><SolutionTable {log} {selectedIteration}/></div>{/if}
    </section>
  </main>
  <footer>Coordinated selections: interaction and generation control the optimization history; vector selections highlight end-of-interaction ADM assignments. PHI is a metric, not a substitute for spatial inspection.</footer>
</div>

<style>
  :global(body){margin:0;background:#f5f7fb;color:#172033}
  .workspace{max-width:1920px;margin:auto;padding:1.1rem 1.4rem 2rem;font-family:inherit}
  .topbar{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:1rem}
  .eyebrow,.pane-kicker{font-size:.66rem;letter-spacing:.105em;color:#6676a1;font-weight:800}
  h1{font-size:1.55rem;letter-spacing:-.035em;margin:.2rem 0}.topbar p,.pane-head p{font-size:.8rem;color:#718096;margin:.3rem 0}
  .summary-metrics{display:flex;gap:.4rem;flex-wrap:wrap;justify-content:flex-end}.summary-metrics span{font-size:.75rem;background:#eaf0fa;border:1px solid #dde6f3;border-radius:5px;padding:.4rem .55rem;text-transform:capitalize}
  .selection-bar{display:flex;flex-wrap:wrap;gap:1rem;align-items:end;background:#fff;border:1px solid #dfe5ef;border-radius:10px;padding:.8rem 1rem;margin-bottom:1rem;box-shadow:0 1px 7px #17203308}
  .control{display:flex;flex-direction:column;gap:.35rem;font-size:.72rem;font-weight:650;color:#59677e}
  .control select{padding:.48rem;border:1px solid #d3dceb;background:#fff;border-radius:6px;color:#172033;min-width:135px}
  .generation-control{flex:1;min-width:160px}.generation-control label{display:flex;justify-content:space-between}.generation-control input{width:100%;accent-color:#5b52ca;margin:.55rem 0}
  .method-buttons{display:flex;gap:.2rem}.method-buttons button{padding:.49rem .65rem;border:1px solid #d3dceb;background:#f8faff;border-radius:5px;color:#68768d;cursor:pointer}.method-buttons button.chosen{background:#e9e5ff;color:#5140c1;border-color:#b7adf4;font-weight:700}
  .reset-button,.subtle-button{cursor:pointer;padding:.5rem .7rem;background:#f8faff;border:1px solid #d5deea;border-radius:6px;color:#495976;font-size:.75rem;font-weight:650}
  .analysis-grid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(0,1fr);gap:1rem;align-items:stretch}
  .pane{background:white;border:1px solid #dfe5ef;border-radius:11px;padding:1rem;min-width:0;overflow:hidden}
  .pane-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.6rem;margin-bottom:.6rem}.pane-head h2{font-size:1rem;letter-spacing:-.015em;margin:.22rem 0}.pane-head p{line-height:1.45}
  .populations{grid-column:1}.preferences{grid-column:2}.temporal{grid-column:1}.vectors{grid-column:2}
  .rp-strip{background:#f6f8fd;border:1px solid #e3e8f1;border-radius:7px;padding:.65rem .8rem;display:flex;justify-content:space-between;gap:.6rem;align-items:center;flex-wrap:wrap;margin:.5rem 0}
  .rp-strip div{display:flex;flex-direction:column;gap:.2rem}.rp-strip span{color:#718096;font-size:.68rem}.rp-strip strong{color:#303a53;font-size:.82rem;font-variant-numeric:tabular-nums}.rp-arrow{font-size:1.2rem!important;color:#a0aec0!important}
  .inline-context{border-top:1px solid #e8edf3;padding-top:.7rem;font-size:.74rem;color:#64748b;margin-top:.5rem}.inline-context button{border:0;background:#edeaff;color:#5d40ca;padding:.28rem .45rem;border-radius:5px;font-weight:700;cursor:pointer;margin-left:.3rem}
  .secondary-chart{border-bottom:1px solid #e9eef5;margin-bottom:.8rem;padding-bottom:.8rem}
  .diagnostic-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:.65rem;align-items:start}.front-panel{border-left:1px solid #e9edf4;padding-left:.75rem;min-width:0}.front-panel h3{font-size:.8rem;color:#334155;margin:.4rem 0 .6rem}
  .details-toggle{margin-top:.75rem;width:100%;text-align:left}.details-panel{margin-top:.8rem;overflow-x:auto;border-top:1px solid #e9eef5;padding-top:.6rem}
  footer{color:#8993a7;font-size:.72rem;margin-top:1rem;line-height:1.6}
  @media(max-width:1180px){.analysis-grid{grid-template-columns:minmax(0,1fr)}.populations,.preferences,.temporal,.vectors{grid-column:1}.topbar{align-items:flex-start}.summary-metrics{max-width:350px}}
  @media(max-width:650px){.workspace{padding:.7rem}.topbar{flex-direction:column;align-items:flex-start}.summary-metrics{justify-content:flex-start}.diagnostic-grid{grid-template-columns:minmax(0,1fr)}.front-panel{border-left:0;border-top:1px solid #e9edf4;padding-left:0;padding-top:.7rem}.pane-head{flex-wrap:wrap}}
</style>
