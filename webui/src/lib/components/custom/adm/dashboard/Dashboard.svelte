<script lang="ts">

  import type {
    ADMLog,
    PopulationSolution
  } from "$lib/adm/types";



  import {
    getObjectives,
    getIteration,
    getReferenceVectorViewData
  } from "$lib/adm/adapters";

  import Header from "./Header.svelte";
  import IterationTimeline from "./IterationTimeline.svelte";

  import PhiEvolution from "../phi/PhiEvolution.svelte";
  import GenerationPhi from "../phi/GenerationPhi.svelte";

  import PreferenceTrajectory from "../preference/PreferenceTrajectory.svelte";
  import PreferencePointHistory from "../preference/PreferencePointHistory.svelte";

  import ReferenceVectorExplorer from "../reference-vectors/ReferenceVectorExplorer.svelte";

  import ParallelCoordinates from "../solutions/ParallelCoordinates.svelte";
  import ScatterPlot from "../solutions/ScatterPlot.svelte";
  import SolutionTable from "../solutions/SolutionTable.svelte";

  export let log: ADMLog;
  export let populationHistory:
    PopulationSolution[] = [];

  /*
   * Coordinated dashboard state
   */
  let selectedIteration = 1;
  let selectedGeneration: number | null = null;
  let selectedVector: string | null = null;

  /*
   * Derived data
   */
  $: objectives = getObjectives(log);

  $: iteration =
    getIteration(log, selectedIteration);

  $: referenceVectors =
    getReferenceVectorViewData(
      log,
      selectedIteration
    );

  /*
   * Initialize the selected vector from
   * the ADM preference of the first interaction.
   */
  $: if (
    iteration &&
    selectedVector === null
  ) {
    selectedVector =
      iteration.preference_information
        .selected_reference_vector;
  }

  /*
   * Interaction navigation
   */
  function selectIteration(value: number) {
    const next = Math.max(
      1,
      Math.min(log.iterations.length, value)
    );

    selectedIteration = next;

    const nextIteration =
      getIteration(log, next);

    selectedVector =
      nextIteration.preference_information
        .selected_reference_vector;

    /*
     * Generation selection belongs to the
     * previously selected interaction, so clear it.
     */
    selectedGeneration = null;
  }

  function previousIteration() {
    selectIteration(selectedIteration - 1);
  }

  function nextIteration() {
    selectIteration(selectedIteration + 1);
  }

  function selectVector(vectorId: string | null) {
    selectedVector = vectorId;
  }
</script>

<div class="dashboard">

  <!-- ======================================================
       TOP BAR
       ====================================================== -->

  <Header
    {log}
    {selectedIteration}
    onPrevious={previousIteration}
    onNext={nextIteration}
  />

  <main class="dashboard-content">

    <!-- ====================================================
         ROW 1 — EXPERIMENT OVERVIEW
         ==================================================== -->

    <section class="overview-grid">

      <!-- Interaction overview -->
      <article class="card interaction-overview-card">

        <div class="card-header">
          <div>
            <h2>Interaction Overview</h2>

            <p>
              Performance evolution across learning
              and decision phases
            </p>
          </div>

          <div
            class:learning={iteration.phase === "learning"}
            class:decision={iteration.phase === "decision"}
            class="phase-chip"
          >
            {iteration.phase}
          </div>
        </div>

        <IterationTimeline
          {log}
          {selectedIteration}
          onSelect={selectIteration}
        />

        <div class="overview-chart">
          <PhiEvolution
            {log}
            {selectedIteration}
            onSelect={selectIteration}
          />
        </div>

      </article>


      <!-- Selected interaction context -->
      <article class="card interaction-context-card">

        <div class="card-header">
          <div>
            <h2>
              Selected Interaction
              ({selectedIteration})
            </h2>

            <p>
              ADM context and benchmark state
            </p>
          </div>
        </div>

        <div class="context-list">

          <div class="context-row">
            <span>Phase</span>

            <strong class="capitalize">
              {iteration.phase}
            </strong>
          </div>

          <div class="context-row">
            <span>ADM selected vector</span>

            <button
              type="button"
              class="link-button"
              on:click={() =>
                selectVector(
                  iteration.preference_information
                    .selected_reference_vector
                )
              }
            >
              {
                iteration.preference_information
                  .selected_reference_vector
              }
            </button>
          </div>

          <div class="context-row vertical">
            <span>Selection rule</span>

            <strong>
              {
                iteration.preference_information
                  .selection_rule
              }
            </strong>
          </div>

          {#if iteration.max_assigned_vector}
            <div class="context-row">
              <span>Most assigned vector</span>

              <button
                type="button"
                class="link-button"
                on:click={() =>
                  selectVector(
                    iteration.max_assigned_vector
                      .vector_id
                  )
                }
              >
                {
                  iteration.max_assigned_vector
                    .vector_id
                }

                <small>
                  (
                  {
                    iteration.max_assigned_vector
                      .assigned_count
                  }
                  )
                </small>
              </button>
            </div>
          {/if}

          <div class="context-row">
            <span>Composite front</span>

            <strong>
              {iteration.composite_front.length}
              solutions
            </strong>
          </div>

          {#if selectedGeneration !== null}
            <div class="context-row selected-generation">
              <span>Selected generation</span>

              <strong>
                {selectedGeneration}
              </strong>
            </div>
          {/if}

        </div>

        <div class="reference-point-section">

          <div class="section-label">
            Current reference point
          </div>

          <div class="reference-point-grid">

            {#each iteration.preference_information.reference_point as value, index}

              <div class="reference-value">
                <span>
                  {objectives[index]}
                </span>

                <strong>
                  {value.toFixed(3)}
                </strong>
              </div>

            {/each}

          </div>

        </div>

      </article>


      <!-- Preference trajectory -->
      <article class="card preference-trajectory-card">

        <div class="card-header">
          <div>
            <h2>ADM Preference Trajectory</h2>

            <p>
              Evolution of reference points across
              interactions
            </p>
          </div>
        </div>

        <PreferenceTrajectory
          {log}
          {selectedIteration}
          onSelect={selectIteration}
        />

      </article>

    </section>


    <!-- ====================================================
         ROW 2 — WITHIN-INTERACTION BEHAVIOR
         ==================================================== -->

    <section class="behavior-grid">

      <!-- Generation performance -->
      <article class="card generation-card">

        <GenerationPhi
          {log}
          {selectedIteration}
          bind:selectedGeneration
        />

      </article>


      <!-- Preference / HV detail -->
      <article class="card preference-history-card">

        <div class="card-header">
          <div>
            <h2>Preference Context</h2>

            <p>
              Preference evolution and interaction
              history
            </p>
          </div>
        </div>

        <PreferencePointHistory
          {log}
          {selectedIteration}
        />

      </article>


      <!-- Parallel coordinates -->
      <article class="card solutions-card">

        <div class="card-header">
          <div>
            <h2>
              Solutions in Objective Space
            </h2>

            <p>
              Composite-front solution profiles
            </p>
          </div>

          <div class="solution-status">
            {#if selectedVector}
              <span>
                Vector:
                <strong>{selectedVector}</strong>
              </span>
            {/if}

            {#if selectedGeneration !== null}
              <span>
                Generation:
                <strong>
                  {selectedGeneration}
                </strong>
              </span>
            {/if}
          </div>
        </div>

        <ParallelCoordinates
          {log}
          {populationHistory}
          {selectedIteration}
          bind:selectedGeneration
          {selectedVector}
        />

      </article>

    </section>


    <!-- ====================================================
         ROW 3 — EXPLORATION / METHOD COMPARISON
         ==================================================== -->

    <section class="exploration-grid">

      <!-- Reference vector exploration -->
      <article class="card reference-vectors-card">

        <div class="card-header">
          <div>
            <h2>Reference Vector Exploration</h2>

            <p>
              Assignment patterns across the
              benchmark
            </p>
          </div>

          {#if selectedVector}
            <button
              type="button"
              class="clear-selection"
              on:click={() =>
                selectVector(null)
              }
            >
              Clear vector
            </button>
          {/if}
        </div>

       <ReferenceVectorExplorer
        {log}
        vectors={referenceVectors}
        {objectives}
        bind:selectedId={selectedVector}
        onSelectIteration={selectIteration}
      />

      </article>


      <!-- Composite front projection -->
      <article class="card front-map-card">

        <div class="card-header">

          <div>
            <h2>Composite Front Map</h2>

            <p>
              Low-dimensional projection for
              exploration
            </p>
          </div>

          <span class="projection-note">
            Projection only
          </span>

        </div>

        <ScatterPlot
          {log}
          {selectedIteration}
          {selectedVector}
          {selectedGeneration}
        />

      </article>


      <!-- Method comparison -->
      <article class="card comparison-card">

        <div class="card-header">
          <div>
            <h2>Method Comparison</h2>

            <p>
              Interaction
              {selectedIteration}
            </p>
          </div>
        </div>

        <SolutionTable
          {log}
          {selectedIteration}
        />

      </article>

    </section>


    <!-- ====================================================
         FOOTER / COORDINATION HINT
         ==================================================== -->

    <div class="coordination-hint">

      <span class="info-icon">i</span>

      <span>
        All views are linked. Select an interaction,
        generation, or reference vector to update the
        corresponding visualizations.
      </span>

      {#if
        selectedGeneration !== null ||
        selectedVector !== null
      }

        <button
          type="button"
          on:click={() => {
            selectedGeneration = null;

            selectedVector =
              iteration.preference_information
                .selected_reference_vector;
          }}
        >
          Reset filters
        </button>

      {/if}

    </div>

  </main>

</div>


<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(html) {
    background: #f7f8fb;
  }

  :global(body) {
    margin: 0;
    background: #f7f8fb;
    color: #171b26;
  }

  /*
   * ------------------------------------------------------
   * Main layout
   * ------------------------------------------------------
   */

  .dashboard {
    min-height: 100vh;

    background:
      linear-gradient(
        180deg,
        #fcfdff 0%,
        #f7f8fb 100%
      );
  }

  .dashboard-content {
    width: 100%;
    max-width: 1920px;

    margin: 0 auto;

    padding:
      0.9rem
      1rem
      1.4rem;

    display: flex;
    flex-direction: column;

    gap: 0.9rem;
  }


  /*
   * ------------------------------------------------------
   * Grids
   * ------------------------------------------------------
   */

  .overview-grid,
  .behavior-grid,
  .exploration-grid {
    display: grid;

    gap: 0.9rem;

    align-items: stretch;
  }

  .overview-grid {
    grid-template-columns:
      minmax(420px, 1.45fr)
      minmax(250px, 0.72fr)
      minmax(390px, 1.35fr);
  }

  .behavior-grid {
    grid-template-columns:
      minmax(420px, 1.06fr)
      minmax(350px, 0.92fr)
      minmax(460px, 1.25fr);
  }

  .exploration-grid {
    grid-template-columns:
      minmax(460px, 1.25fr)
      minmax(380px, 1fr)
      minmax(330px, 0.86fr);
  }


  /*
   * ------------------------------------------------------
   * Card styling
   * ------------------------------------------------------
   */

  .card {
    position: relative;

    min-width: 0;

    padding: 0.9rem;

    overflow: hidden;

    border:
      1px solid
      #e6e9f0;

    border-radius:
      11px;

    background:
      rgba(
        255,
        255,
        255,
        0.98
      );

    box-shadow:
      0 1px 2px
        rgb(15 23 42 / 0.018),
      0 8px 30px
        rgb(15 23 42 / 0.018);
  }

  .card-header {
    min-height: 39px;

    display: flex;
    justify-content: space-between;
    align-items: flex-start;

    gap: 0.8rem;

    margin-bottom: 0.55rem;
  }

  .card-header h2 {
    margin: 0;

    color: #171b27;

    font-size: 0.84rem;
    font-weight: 700;

    letter-spacing: -0.01em;
  }

  .card-header p {
    margin:
      0.18rem
      0
      0;

    color: #8991a4;

    font-size: 0.66rem;
    line-height: 1.35;
  }


  /*
   * ------------------------------------------------------
   * Overview card
   * ------------------------------------------------------
   */

  .overview-chart {
    margin-top: 0.2rem;
  }

  .phase-chip {
    padding:
      0.28rem
      0.55rem;

    border-radius: 5px;

    font-size: 0.62rem;
    font-weight: 700;

    text-transform:
      capitalize;
  }

  .phase-chip.learning {
    color: #6341db;
    background: #f0ebff;
  }

  .phase-chip.decision {
    color: #db681d;
    background: #fff1e7;
  }


  /*
   * ------------------------------------------------------
   * Interaction context
   * ------------------------------------------------------
   */

  .context-list {
    display: flex;
    flex-direction: column;

    gap: 0.04rem;
  }

  .context-row {
    min-height: 35px;

    display: flex;
    justify-content: space-between;
    align-items: center;

    gap: 0.75rem;

    padding:
      0.38rem
      0;

    border-bottom:
      1px solid
      #f0f2f6;
  }

  .context-row:last-child {
    border-bottom: 0;
  }

  .context-row.vertical {
    align-items: flex-start;
  }

  .context-row.vertical strong {
    max-width: 55%;

    text-align: right;

    overflow-wrap:
      anywhere;
  }

  .context-row span {
    color: #7e8699;

    font-size: 0.66rem;
  }

  .context-row strong {
    color: #282e3d;

    font-size: 0.68rem;
    font-weight: 600;
  }

  .capitalize {
    text-transform: capitalize;
  }

  .selected-generation {
    background: #faf9ff;
  }

  .link-button {
    padding: 0;

    border: 0;
    background: transparent;

    color: #6544df;

    font-size: 0.68rem;
    font-weight: 700;

    cursor: pointer;
  }

  .link-button:hover {
    text-decoration: underline;
  }

  .link-button small {
    color: #9198a8;
    font-weight: 500;
  }


  /*
   * ------------------------------------------------------
   * Reference point
   * ------------------------------------------------------
   */

  .reference-point-section {
    margin-top: 0.75rem;

    padding-top: 0.72rem;

    border-top:
      1px solid
      #edf0f5;
  }

  .section-label {
    margin-bottom:
      0.45rem;

    color: #7e8699;

    font-size: 0.63rem;
  }

  .reference-point-grid {
    display: grid;

    grid-template-columns:
      repeat(
        auto-fit,
        minmax(48px, 1fr)
      );

    gap: 0.24rem;
  }

  .reference-value {
    display: flex;
    flex-direction: column;

    gap: 0.08rem;

    padding:
      0.38rem
      0.2rem;

    text-align: center;

    border-radius:
      5px;

    background:
      #f7f8fb;
  }

  .reference-value span {
    color: #9299a9;

    font-size: 0.57rem;
    font-weight: 600;
  }

  .reference-value strong {
    color: #2e3443;

    font-size: 0.64rem;
    font-variant-numeric:
      tabular-nums;
  }


  /*
   * ------------------------------------------------------
   * Solution header
   * ------------------------------------------------------
   */

  .solution-status {
    display: flex;
    flex-wrap: wrap;

    justify-content: flex-end;

    gap: 0.25rem;
  }

  .solution-status span {
    padding:
      0.25rem
      0.42rem;

    border-radius: 4px;

    color: #777f92;
    background: #f6f7fa;

    font-size: 0.59rem;
  }

  .solution-status strong {
    color: #5d40d7;
  }


  /*
   * ------------------------------------------------------
   * Reference vectors
   * ------------------------------------------------------
   */

  .clear-selection {
    border: 0;

    padding: 0;

    background:
      transparent;

    color: #6545dc;

    font-size: 0.61rem;

    cursor: pointer;
  }

  .clear-selection:hover {
    text-decoration:
      underline;
  }


  /*
   * ------------------------------------------------------
   * Projection
   * ------------------------------------------------------
   */

  .projection-note {
    padding:
      0.25rem
      0.4rem;

    border-radius: 4px;

    color: #8a6a21;
    background: #fff8e8;

    font-size: 0.57rem;
    font-weight: 600;
  }


  /*
   * ------------------------------------------------------
   * Coordination hint
   * ------------------------------------------------------
   */

  .coordination-hint {
    min-height: 39px;

    display: flex;
    align-items: center;

    gap: 0.55rem;

    padding:
      0.55rem
      0.85rem;

    border:
      1px solid
      #e5e8ef;

    border-radius:
      8px;

    background:
      rgba(
        255,
        255,
        255,
        0.88
      );

    color: #737b8e;

    font-size: 0.64rem;
  }

  .coordination-hint .info-icon {
    width: 17px;
    height: 17px;

    flex: 0 0 auto;

    display: grid;
    place-items: center;

    border:
      1px solid
      #8e96a8;

    border-radius: 50%;

    color: #6d7587;

    font-size: 0.58rem;
    font-weight: 700;
  }

  .coordination-hint button {
    margin-left: auto;

    padding:
      0.31rem
      0.55rem;

    border:
      1px solid
      #dfe3eb;

    border-radius:
      5px;

    background: white;

    color: #596174;

    font-size: 0.61rem;

    cursor: pointer;
  }

  .coordination-hint button:hover {
    border-color: #c7bdf8;
    color: #5c40d4;
  }


  /*
   * ------------------------------------------------------
   * Responsive layout
   * ------------------------------------------------------
   */

  @media (
    max-width: 1450px
  ) {

    .overview-grid {
      grid-template-columns:
        1.4fr
        0.8fr;
    }

    .preference-trajectory-card {
      grid-column:
        1 / -1;
    }

    .behavior-grid {
      grid-template-columns:
        1fr
        1fr;
    }

    .solutions-card {
      grid-column:
        1 / -1;
    }

    .exploration-grid {
      grid-template-columns:
        1fr
        1fr;
    }

    .comparison-card {
      grid-column:
        1 / -1;
    }

  }


  @media (
    max-width: 950px
  ) {

    .dashboard-content {
      padding: 0.75rem;
    }

    .overview-grid,
    .behavior-grid,
    .exploration-grid {
      grid-template-columns:
        1fr;
    }

    .preference-trajectory-card,
    .solutions-card,
    .comparison-card {
      grid-column: auto;
    }

  }
</style>