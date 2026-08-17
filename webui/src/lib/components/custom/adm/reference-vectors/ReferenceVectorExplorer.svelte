<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";

    import type {
    ADMLog,
    ReferenceVectorViewModel
  } from "$lib/adm/types";

  export let log: ADMLog;

  export let vectors:
    ReferenceVectorViewModel[] = [];

  export let objectives: string[] = [];

  export let selectedId:
    string | null = null;

  export let onSelectIteration:
    (iteration: number) => void =
      () => {};

  export let width = 720;
  export let height = 430;

  type AssignmentCell = {
    vectorId: string;
    iteration: number;
    phase: "learning" | "decision";
    count: number;
    assignedSolutionIds: string[];
  };


  let svgEl: SVGSVGElement;

  let tooltipVisible = false;
  let tooltipX = 0;
  let tooltipY = 0;

  let tooltipCell: AssignmentCell | null = null;

  /*
   * ------------------------------------------------------
   * Derived data
   * ------------------------------------------------------
   */

  $: vectorIds =
  log.reference_vectors.map(
    (vector) =>
      vector.vector_id
  );

  /*
   * Build a complete matrix, including zero-assignment cells.
   */
$: cells =
  log.iterations.flatMap(
    (iteration) =>
      log.reference_vectors.map(
        (vector): AssignmentCell => {

          const assignment =
            iteration.reference_vector_assignments
              ?.find(
                (item) =>
                  item.vector_id ===
                  vector.vector_id
              );

          return {
            vectorId:
              vector.vector_id,

            iteration:
              iteration.iteration,

            phase:
              iteration.phase,

            count:
              assignment?.assigned_count ?? 0,

            assignedSolutionIds:
              assignment?.assigned_solution_ids ?? []
          };
        }
      )
  );

  /*
   * Selected vector object.
   */
  $: selectedVector =
    selectedId
      ? vectors.find(
          (vector) =>
            vector.id === selectedId
        ) ?? null
      : null;

  /*
   * Assignment history for selected vector.
   */
  $: selectedHistory =
    selectedId
      ? cells.filter(
          (cell) =>
            cell.vectorId === selectedId
        )
      : [];

  $: totalAssignments =
    d3.sum(
      selectedHistory,
      (cell) => cell.count
    );

  $: peakAssignment =
    selectedHistory.length > 0
      ? d3.max(
          selectedHistory,
          (cell) => cell.count
        ) ?? 0
      : 0;

  $: peakInteraction =
    selectedHistory.find(
      (cell) =>
        cell.count === peakAssignment
    )?.iteration ?? null;

  /*
   * Identify interactions where the ADM itself selected
   * this reference vector as its preference context.
   */
  $: admSelectedIterations =
    selectedId
      ? log.iterations
          .filter(
            (iteration) =>
              iteration.preference_information
                .selected_reference_vector ===
              selectedId
          )
          .map(
            (iteration) =>
              iteration.iteration
          )
      : [];

  /*
   * Automatically choose the first ADM-selected vector
   * when none is selected.
   */
  $: if (
    selectedId === null &&
    log.iterations.length > 0
  ) {
    selectedId =
      log.iterations[0]
        .preference_information
        .selected_reference_vector;
  }

  /*
   * ------------------------------------------------------
   * Drawing
   * ------------------------------------------------------
   */

  function draw() {
    if (!svgEl) {
      return;
    }

    const svg =
      d3.select(svgEl);

    svg
      .selectAll("*")
      .remove();

    if (
      vectorIds.length === 0 ||
      log.iterations.length === 0
    ) {
      svg
        .attr(
          "viewBox",
          `0 0 ${width} ${height}`
        )
        .append("text")
        .attr(
          "x",
          width / 2
        )
        .attr(
          "y",
          height / 2
        )
        .attr(
          "text-anchor",
          "middle"
        )
        .attr(
          "fill",
          "#8a91a3"
        )
        .attr(
          "font-size",
          12
        )
        .text(
          "No reference-vector data available."
        );

      return;
    }

    /*
     * Increase chart height when there are many vectors.
     *
     * This means the surrounding wrapper can scroll vertically
     * instead of crushing 100+ vectors into unreadable rows.
     */
    const rowHeight =
      vectorIds.length <= 20
        ? 17
        : vectorIds.length <= 60
          ? 12
          : 9;

    const dynamicHeight =
      Math.max(
        height,
        vectorIds.length *
          rowHeight +
          80
      );

    const margin = {
      top: 34,
      right: 20,
      bottom: 40,
      left:
        vectorIds.length > 99
          ? 58
          : 50
    };

    const innerWidth =
      width -
      margin.left -
      margin.right;

    const innerHeight =
      dynamicHeight -
      margin.top -
      margin.bottom;

    /*
     * --------------------------------------------------
     * Categorical scales
     * --------------------------------------------------
     */

    const x =
      d3
        .scaleBand<number>()
        .domain(
          log.iterations.map(
            (iteration) =>
              iteration.iteration
          )
        )
        .range([
          0,
          innerWidth
        ])
        .paddingInner(0.08)
        .paddingOuter(0.03);

    const y =
      d3
        .scaleBand<string>()
        .domain(
          vectorIds
        )
        .range([
          0,
          innerHeight
        ])
        .paddingInner(0.08)
        .paddingOuter(0.02);

    /*
     * --------------------------------------------------
     * Assignment intensity
     * --------------------------------------------------
     */

    const maxCount =
      d3.max(
        cells,
        (cell) =>
          cell.count
      ) ?? 1;

    /*
     * Keep zero cells nearly white and increase
     * purple intensity with assignments.
     */
    const color =
      d3
        .scaleSequential(
          d3.interpolatePurples
        )
        .domain([
          0,
          Math.max(
            1,
            maxCount
          )
        ]);

    const root =
      svg
        .attr(
          "viewBox",
          `0 0 ${width} ${dynamicHeight}`
        )
        .attr(
          "preserveAspectRatio",
          "xMinYMin meet"
        )
        .append("g")
        .attr(
          "transform",
          `translate(${margin.left},${margin.top})`
        );

    /*
     * --------------------------------------------------
     * Phase background
     * --------------------------------------------------
     */

    const learningIterations =
      log.iterations.filter(
        (iteration) =>
          iteration.phase === "learning"
      );

    const decisionIterations =
      log.iterations.filter(
        (iteration) =>
          iteration.phase === "decision"
      );

    if (
      learningIterations.length > 0
    ) {
      const first =
        learningIterations[0]
          .iteration;

      const last =
        learningIterations[
          learningIterations.length -
            1
        ].iteration;

      const start =
        x(first) ?? 0;

      const end =
        (x(last) ?? 0) +
        x.bandwidth();

      root
        .append("rect")
        .attr(
          "x",
          start
        )
        .attr(
          "y",
          0
        )
        .attr(
          "width",
          end -
            start
        )
        .attr(
          "height",
          innerHeight
        )
        .attr(
          "fill",
          "#f7f4ff"
        );
    }

    if (
      decisionIterations.length > 0
    ) {
      const first =
        decisionIterations[0]
          .iteration;

      const last =
        decisionIterations[
          decisionIterations.length -
            1
        ].iteration;

      const start =
        x(first) ?? 0;

      const end =
        (x(last) ?? 0) +
        x.bandwidth();

      root
        .append("rect")
        .attr(
          "x",
          start
        )
        .attr(
          "y",
          0
        )
        .attr(
          "width",
          end -
            start
        )
        .attr(
          "height",
          innerHeight
        )
        .attr(
          "fill",
          "#fff8f2"
        );
    }

    /*
     * --------------------------------------------------
     * Heatmap cells
     * --------------------------------------------------
     */

    root
      .append("g")
      .selectAll("rect")
      .data(cells)
      .join("rect")
      .attr(
        "x",
        (cell) =>
          x(
            cell.iteration
          ) ?? 0
      )
      .attr(
        "y",
        (cell) =>
          y(
            cell.vectorId
          ) ?? 0
      )
      .attr(
        "width",
        x.bandwidth()
      )
      .attr(
        "height",
        y.bandwidth()
      )
      .attr(
        "rx",
        Math.min(
          2,
          y.bandwidth() /
            4
        )
      )
      .attr(
        "fill",
        (cell) =>
          cell.count === 0
            ? "#f3f4f7"
            : color(
                cell.count
              )
      )
      .attr(
        "stroke",
        (cell) =>
          cell.vectorId ===
          selectedId
            ? "#5535d8"
            : "transparent"
      )
      .attr(
        "stroke-width",
        (cell) =>
          cell.vectorId ===
          selectedId
            ? 1.4
            : 0
      )
      .style(
        "cursor",
        "pointer"
      )
      .on(
        "mouseenter",
        function (
          event,
          cell
        ) {
          tooltipCell =
            cell;

          d3
            .select(this)
            .attr(
              "stroke",
              "#4f35c9"
            )
            .attr(
              "stroke-width",
              2
            );

          const bounds =
            svgEl
              .getBoundingClientRect();

          tooltipX =
            event.clientX -
            bounds.left +
            12;

          tooltipY =
            event.clientY -
            bounds.top +
            10;

          tooltipVisible =
            true;
        }
      )
      .on(
        "mousemove",
        function (
          event
        ) {
          const bounds =
            svgEl
              .getBoundingClientRect();

          tooltipX =
            event.clientX -
            bounds.left +
            12;

          tooltipY =
            event.clientY -
            bounds.top +
            10;
        }
      )
      .on(
        "mouseleave",
        function (
          _event,
          cell
        ) {
          tooltipVisible =
            false;

          d3
            .select(this)
            .attr(
              "stroke",
              cell.vectorId ===
              selectedId
                ? "#5535d8"
                : "transparent"
            )
            .attr(
              "stroke-width",
              cell.vectorId ===
              selectedId
                ? 1.4
                : 0
            );
        }
      )
      .on(
        "click",
        (
          _event,
          cell
        ) => {
          selectedId =
            cell.vectorId;

          onSelectIteration(
            cell.iteration
          );
        }
      );

    /*
     * --------------------------------------------------
     * Mark the vector actually selected by the ADM
     * for each interaction.
     *
     * Small orange dot inside the corresponding cell.
     * --------------------------------------------------
     */

    const admSelections =
      log.iterations.map(
        (iteration) => ({
          iteration:
            iteration.iteration,

          vectorId:
            iteration
              .preference_information
              .selected_reference_vector
        })
      );

    root
      .append("g")
      .selectAll("circle")
      .data(
        admSelections
      )
      .join("circle")
      .attr(
        "cx",
        (item) =>
          (
            x(
              item.iteration
            ) ?? 0
          ) +
          x.bandwidth() -
          4
      )
      .attr(
        "cy",
        (item) =>
          (
            y(
              item.vectorId
            ) ?? 0
          ) +
          4
      )
      .attr(
        "r",
        Math.min(
          2.6,
          y.bandwidth() /
            3
        )
      )
      .attr(
        "fill",
        "#ef7d32"
      )
      .attr(
        "stroke",
        "white"
      )
      .attr(
        "stroke-width",
        0.8
      )
      .style(
        "pointer-events",
        "none"
      );

    /*
     * --------------------------------------------------
     * Axes
     * --------------------------------------------------
     */

    root
      .append("g")
      .attr(
        "transform",
        `translate(0,${innerHeight})`
      )
      .call(
        d3
          .axisBottom(x)
          .tickSize(0)
      )
      .call(
        (axis) =>
          axis
            .select(
              ".domain"
            )
            .attr(
              "stroke",
              "#cbd0da"
            )
      )
      .call(
        (axis) =>
          axis
            .selectAll(
              "text"
            )
            .attr(
              "fill",
              "#71798b"
            )
            .attr(
              "font-size",
              9
            )
      );

    /*
     * Hide some vector labels if there are hundreds,
     * but preserve all cells.
     */
    const labelStep =
      vectorIds.length <= 30
        ? 1
        : vectorIds.length <= 80
          ? 2
          : Math.ceil(
              vectorIds.length /
                40
            );

    const visibleYLabels =
      vectorIds.filter(
        (
          _,
          index
        ) =>
          index %
            labelStep ===
          0
      );

    root
      .append("g")
      .call(
        d3
          .axisLeft(y)
          .tickValues(
            visibleYLabels
          )
          .tickSize(0)
      )
      .call(
        (axis) =>
          axis
            .select(
              ".domain"
            )
            .remove()
      )
      .call(
        (axis) =>
          axis
            .selectAll(
              "text"
            )
            .attr(
              "fill",
              "#777f91"
            )
            .attr(
              "font-size",
              8
            )
      );

    /*
     * Axis labels.
     */
    root
      .append("text")
      .attr(
        "x",
        innerWidth /
          2
      )
      .attr(
        "y",
        innerHeight +
          34
      )
      .attr(
        "text-anchor",
        "middle"
      )
      .attr(
        "fill",
        "#7b8395"
      )
      .attr(
        "font-size",
        10
      )
      .text(
        "Interaction"
      );

    root
      .append("text")
      .attr(
        "transform",
        `translate(${-38},${innerHeight /
          2}) rotate(-90)`
      )
      .attr(
        "text-anchor",
        "middle"
      )
      .attr(
        "fill",
        "#7b8395"
      )
      .attr(
        "font-size",
        10
      )
      .text(
        "Reference vector"
      );
  }

  onMount(
    draw
  );

  $: if (
    svgEl &&
    selectedId !==
      undefined &&
    cells.length
  ) {
    draw();
  }
</script>


<div class="reference-vector-explorer">

  <!-- ==================================================
       Heatmap
       ================================================== -->

  <div class="heatmap-panel">

    <div class="heatmap-toolbar">

      <div>
        <strong>
          Assignment Heatmap
        </strong>

        <span>
          darker cells indicate more assigned solutions
        </span>
      </div>


      <div class="legend">

        <span>
          Low
        </span>

        <div class="gradient"></div>

        <span>
          High
        </span>

        <span class="adm-marker">
          <i></i>
          ADM selected
        </span>

      </div>

    </div>


    <div class="heatmap-scroll">

      <div class="chart-wrapper">

        <svg
          bind:this={svgEl}
        ></svg>


        {#if
          tooltipVisible &&
          tooltipCell
        }

          <div
            class="tooltip"
            style:left={`${tooltipX}px`}
            style:top={`${tooltipY}px`}
          >

            <div class="tooltip-header">

              <strong>
                {
                  tooltipCell.vectorId
                }
              </strong>

              <span>
                Interaction
                {
                  tooltipCell.iteration
                }
              </span>

            </div>


            <div class="tooltip-row">

              <span>
                Phase
              </span>

              <b class="capitalize">
                {
                  tooltipCell.phase
                }
              </b>

            </div>


            <div class="tooltip-row">

              <span>
                Assigned solutions
              </span>

              <b>
                {
                  tooltipCell.count
                }
              </b>

            </div>


            <div class="tooltip-row">

              <span>
                ADM-selected vector
              </span>

              <b>
                {
                  log.iterations.find(
                    (iteration) =>
                      iteration.iteration ===
                      tooltipCell?.iteration
                  )
                    ?.preference_information
                    .selected_reference_vector ===
                  tooltipCell.vectorId
                    ? "Yes"
                    : "No"
                }
              </b>

            </div>

          </div>

        {/if}

      </div>

    </div>

  </div>


  <!-- ==================================================
       Selected vector details
       ================================================== -->

  <aside class="details-panel">

    {#if selectedVector}
{#if selectedVector}

  <h3>{selectedVector.id}</h3>

  <div class="direction-bars">
    {#each selectedVector.weights as value, index}
      <div class="direction-row">

        <span>
          {objectives[index] ?? `f${index + 1}`}
        </span>

        <div class="bar-track">
          <div
            class="bar"
            style:width={`${value * 100}%`}
          ></div>
        </div>

        <strong>
          {value.toFixed(3)}
        </strong>

      </div>
    {/each}
  </div>

{/if}
  
    {:else}

      <div class="empty-details">

        Select a reference vector
        in the heatmap to inspect
        its direction and assignment
        history.

      </div>

    {/if}

  </aside>

</div>


<style>
  .reference-vector-explorer {
    display: grid;

    grid-template-columns:
      minmax(
        0,
        1.65fr
      )
      minmax(
        210px,
        0.7fr
      );

    gap: 0.8rem;

    min-width: 0;
  }


  /* --------------------------------------------------
     Heatmap
     -------------------------------------------------- */

  .heatmap-panel {
    min-width: 0;
  }

  .heatmap-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 0.7rem;

    margin-bottom:
      0.35rem;
  }

  .heatmap-toolbar > div:first-child {
    display: flex;
    flex-direction: column;
  }

  .heatmap-toolbar strong {
    color: #353b49;

    font-size: 0.64rem;
  }

  .heatmap-toolbar span {
    color: #9299a8;

    font-size: 0.52rem;
  }

  .legend {
    display: flex;
    align-items: center;

    gap: 0.3rem;
  }

  .gradient {
    width: 58px;
    height: 7px;

    border-radius:
      3px;

    background:
      linear-gradient(
        90deg,
        #f3f4f7,
        #d7cef5,
        #5d3dd2
      );
  }

  .adm-marker {
    display: flex;
    align-items: center;

    gap: 0.25rem;

    margin-left:
      0.35rem;
  }

  .adm-marker i {
    width: 6px;
    height: 6px;

    border-radius: 50%;

    background:
      #ef7d32;
  }

  .heatmap-scroll {
    max-height: 500px;

    overflow-y: auto;
    overflow-x: hidden;

    border:
      1px solid
      #eef0f4;

    border-radius:
      6px;

    background: white;
  }

  .chart-wrapper {
    position: relative;

    min-width: 0;
  }

  svg {
    display: block;

    width: 100%;
    height: auto;
  }


  /* --------------------------------------------------
     Tooltip
     -------------------------------------------------- */

  .tooltip {
    position: absolute;
    z-index: 50;

    min-width: 175px;

    padding:
      0.55rem
      0.65rem;

    pointer-events: none;

    border:
      1px solid
      #e1e4eb;

    border-radius:
      7px;

    background:
      rgba(
        255,
        255,
        255,
        0.98
      );

    box-shadow:
      0 9px 28px
      rgb(15 23 42 / 0.13);
  }

  .tooltip-header {
    display: flex;
    justify-content: space-between;

    gap: 0.5rem;

    margin-bottom:
      0.4rem;
  }

  .tooltip-header strong {
    color: #373d4b;

    font-size: 0.63rem;
  }

  .tooltip-header span {
    color: #8b92a2;

    font-size: 0.54rem;
  }

  .tooltip-row {
    display: flex;
    justify-content: space-between;

    gap: 0.7rem;

    margin-top:
      0.25rem;

    color: #858d9d;

    font-size: 0.55rem;
  }

  .tooltip-row b {
    color: #343a48;

    font-size: 0.55rem;
  }

  .capitalize {
    text-transform:
      capitalize;
  }


  /* --------------------------------------------------
     Details
     -------------------------------------------------- */

  .details-panel {
    min-width: 0;

    padding-left:
      0.75rem;

    border-left:
      1px solid
      #eceef3;
  }

  .details-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;

    gap: 0.5rem;
  }

  .details-header span {
    color: #969dac;

    font-size: 0.5rem;
  }

  .details-header h3 {
    margin:
      0.08rem
      0
      0;

    color: #312d42;

    font-size: 1rem;
  }

  .adm-count {
    padding:
      0.2rem
      0.35rem;

    border-radius:
      4px;

    background:
      #fff1e7;

    color:
      #d76e28 !important;

    font-weight:
      600;
  }

  .metrics {
    display: grid;

    grid-template-columns:
      repeat(
        3,
        1fr
      );

    gap: 0.25rem;

    margin:
      0.65rem
      0;
  }

  .metrics div {
    padding:
      0.4rem
      0.25rem;

    border-radius:
      5px;

    background:
      #f8f9fb;

    text-align: center;
  }

  .metrics span {
    display: block;

    color: #979dac;

    font-size: 0.46rem;
  }

  .metrics strong {
    display: block;

    margin-top:
      0.08rem;

    color: #343a48;

    font-size: 0.64rem;
  }

  .section-label {
    display: block;

    margin-bottom:
      0.35rem;

    color: #8e95a5;

    font-size: 0.52rem;

    text-transform:
      uppercase;

    letter-spacing:
      0.03em;
  }


  /* --------------------------------------------------
     Vector direction
     -------------------------------------------------- */

  .direction {
    margin-top:
      0.65rem;
  }

  .direction-bars {
    display: flex;
    flex-direction: column;

    gap: 0.28rem;
  }

  .direction-row {
    display: grid;

    grid-template-columns:
      28px
      1fr
      38px;

    align-items: center;

    gap: 0.35rem;
  }

  .direction-row > span {
    color: #737b8d;

    font-size: 0.52rem;
  }

  .direction-row strong {
    color: #474e5e;

    font-size: 0.51rem;

    text-align: right;

    font-variant-numeric:
      tabular-nums;
  }

  .bar-track {
    height: 6px;

    overflow: hidden;

    border-radius:
      3px;

    background:
      #eceef3;
  }

  .bar {
    height: 100%;

    border-radius:
      3px;

    background:
      #6a4bdf;
  }


  /* --------------------------------------------------
     Selected-vector history
     -------------------------------------------------- */

  .history {
    margin-top:
      0.8rem;
  }

  .history-list {
    display: flex;
    flex-direction: column;

    gap: 0.22rem;
  }

  .history-list button {
    width: 100%;

    display: grid;

    grid-template-columns:
      24px
      1fr
      28px
      8px;

    align-items: center;

    gap: 0.3rem;

    padding:
      0.27rem
      0.2rem;

    border: 0;

    background:
      transparent;

    cursor: pointer;
  }

  .history-list button:hover {
    background:
      #f8f7ff;

    border-radius:
      4px;
  }

  .history-list span {
    color: #777f90;

    font-size: 0.51rem;
  }

  .history-list strong {
    color: #424958;

    font-size: 0.52rem;

    text-align: right;
  }

  .mini-track {
    height: 5px;

    border-radius:
      3px;

    background:
      #eef0f4;
  }

  .mini-bar {
    height: 100%;

    border-radius:
      3px;

    background:
      #6c4ce0;
  }

  .history-list i {
    width: 6px;
    height: 6px;

    border-radius: 50%;

    background:
      #ef7d32;
  }

  .empty-details {
    display: grid;
    place-items: center;

    min-height: 250px;

    padding: 1rem;

    color: #9aa1b0;

    font-size: 0.62rem;

    text-align: center;
  }


  @media (
    max-width: 900px
  ) {

    .reference-vector-explorer {
      grid-template-columns:
        1fr;
    }

    .details-panel {
      padding-left: 0;
      padding-top:
        0.7rem;

      border-left: 0;

      border-top:
        1px solid
        #eceef3;
    }

  }
</style>