<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";
  import {
    getObjectives,
    getReferenceVectorViewData
  } from "$lib/adm/adapters";

  import Header from "./Header.svelte";
  import Sidebar from "./Sidebar.svelte";
  import IterationTimeline from "./IterationTimeline.svelte";

  import PhiEvolution from "../phi/PhiEvolution.svelte";
  import GenerationPhi from "../phi/GenerationPhi.svelte";

  import PreferenceTrajectory from "../preference/PreferenceTrajectory.svelte";
  import PreferencePointHistory from "../preference/PreferencePointHistory.svelte";

  import ReferenceVectorExplorer from "../reference-vectors/ReferenceVectorExplorer.svelte";

  import ParallelCoordinates from "../solutions/ParallelCoordinates.svelte";
  import ScatterPlot from "../solutions/ScatterPlot.svelte";
  import SolutionTable from "../solutions/SolutionTable.svelte";

  import NarrativePanel from "../narrative/NarrativePanel.svelte";

  export let log: ADMLog;

  let selectedIteration = 1;

  $: objectives = getObjectives(log);
  $: referenceVectors = getReferenceVectorViewData(log, selectedIteration);
</script>

<div class="app">
  <Sidebar {log} />

  <main>
    <Header {log} {selectedIteration} />

    <div class="content">
      <IterationTimeline
        {log}
        {selectedIteration}
        onSelect={(it) => (selectedIteration = it)}
      />

      <section class="grid two">
        <div class="card">
          <h3>Φ Evolution</h3>
          <PhiEvolution {log} />
        </div>

        <div class="card">
          <h3>Generation-Level Φ</h3>
          <GenerationPhi {log} {selectedIteration} />
        </div>
      </section>

      <section class="grid two">
        <div class="card">
          <h3>Preference Trajectory</h3>
          <PreferenceTrajectory {log} />
        </div>

        <div class="card">
          <PreferencePointHistory {log} {selectedIteration} />
        </div>
      </section>

      <section class="card">
        <h3>Reference Vector Explorer</h3>
        <ReferenceVectorExplorer
          vectors={referenceVectors}
          {objectives}
        />
      </section>

      <section class="grid two">
        <div class="card">
          <h3>Composite Front Projection</h3>
          <ScatterPlot {log} {selectedIteration} />
        </div>

        <div class="card">
          <h3>Solution Profiles</h3>
          <ParallelCoordinates {log} {selectedIteration} />
        </div>
      </section>

      <section class="grid two">
        <div class="card">
          <h3>Solution Table</h3>
          <SolutionTable {log} {selectedIteration} />
        </div>

        <div class="card">
          <NarrativePanel {log} {selectedIteration} />
        </div>
      </section>
    </div>
  </main>
</div>

<style>
  .app {
    display: grid;
    grid-template-columns: 280px 1fr;
    min-height: 100vh;
    background: #f8fafc;
  }

  main {
    min-width: 0;
  }

  .content {
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .grid.two {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 1rem;
    padding: 1rem;
  }

  h3 {
    margin-top: 0;
    margin-bottom: 0.75rem;
  }

  @media (max-width: 1100px) {
    .app {
      grid-template-columns: 1fr;
    }

    .grid.two {
      grid-template-columns: 1fr;
    }
  }
</style>